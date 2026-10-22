import io
import sys
from pathlib import Path

import requests
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))

BASE_URL = "http://127.0.0.1:5000"
HTTP = requests.Session()


def test_homepage():
    """Test that homepage loads and establishes a browser session."""
    response = HTTP.get(f"{BASE_URL}/", allow_redirects=False, timeout=10)
    assert response.status_code in (200, 302), f"Homepage failed: {response.status_code}"
    assert HTTP.cookies, "Homepage did not establish a session cookie"
    print("[OK] Homepage loads and establishes a session")


def test_teacher_access_is_protected():
    """Teacher pages must reject unauthenticated requests in the deployment adapter."""
    response = requests.get(f"{BASE_URL}/teacher/tests", timeout=10)
    assert response.status_code == 401, (
        f"Expected unauthenticated teacher access to return 401, got {response.status_code}"
    )
    print("[OK] Teacher route rejects unauthenticated access")


def test_test_listing():
    """Test the student assessment listing."""
    response = HTTP.get(f"{BASE_URL}/tests", timeout=10)
    assert response.status_code == 200
    assert b"Available Tests" in response.content or b"Mock Mathematics" in response.content or b"Interface Demo" in response.content
    print("[OK] Test listing page works")


def test_instructions():
    """Test the test instructions page."""
    response = HTTP.get(f"{BASE_URL}/test/TEST001/instructions", timeout=10)
    assert response.status_code == 200
    assert b"Instructions" in response.content
    print("[OK] Test instructions page works")


def test_start_test():
    """Test starting a test."""
    response = HTTP.post(f"{BASE_URL}/api/test/TEST001/start", timeout=10)
    assert response.status_code == 200, response.text
    data = response.json()
    assert "attempt_id" in data
    assert "redirect_url" in data
    print(f"[OK] Test start works (Attempt ID: {data['attempt_id'][:8]}...)")
    return data["attempt_id"]


def test_get_questions(attempt_id):
    """Test loading questions and validating the response contract."""
    response = HTTP.get(f"{BASE_URL}/api/attempt/{attempt_id}/questions", timeout=10)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert isinstance(payload, dict) and "questions" in payload
    questions = payload["questions"]
    assert len(questions) > 0
    assert questions[0]["question_type"] in ("mcq", "subjective", "vsaq", "saq", "laq")
    print(f"[OK] Questions loaded ({len(questions)} questions)")
    return questions


def test_save_mcq_response(attempt_id):
    """Test saving an MCQ response."""
    response = HTTP.post(
        f"{BASE_URL}/api/attempt/{attempt_id}/response",
        json={"question_id": "Q001", "selected_answer": "B"},
        timeout=10,
    )
    assert response.status_code == 200, response.text
    print("[OK] MCQ response saved")


def test_save_subjective_response(attempt_id):
    """Test saving a subjective final-answer selection."""
    response = HTTP.post(
        f"{BASE_URL}/api/attempt/{attempt_id}/response",
        json={"question_id": "Q005", "selected_answer": "A"},
        timeout=10,
    )
    assert response.status_code == 200, response.text
    print("[OK] Subjective response saved")


def test_upload_required_images(attempt_id, questions):
    """Upload valid image bytes for every question that requires handwritten work."""
    required = [
        question for question in questions
        if question.get("handwritten_upload_mode") == "required"
    ]
    assert required, "Demo test must exercise required handwritten uploads"

    image_bytes = io.BytesIO()
    Image.new("RGB", (3, 3), (255, 255, 255)).save(image_bytes, format="PNG")
    image_content = image_bytes.getvalue()

    for question in required:
        response = HTTP.post(
            f"{BASE_URL}/api/attempt/{attempt_id}/upload",
            data={"question_id": question["question_id"]},
            files={"file": ("answer.png", image_content, "image/png")},
            timeout=15,
        )
        assert response.status_code == 200, (
            f"Upload failed for {question['question_id']}: {response.status_code} {response.text}"
        )
        assert response.json().get("image_id")
    print(f"[OK] Required handwritten uploads persisted ({len(required)} questions)")


def test_submission_preview(attempt_id):
    """Test submission preview and required-upload completeness."""
    response = HTTP.get(
        f"{BASE_URL}/api/attempt/{attempt_id}/submit-preview", timeout=10
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert "total_questions" in payload
    assert "answered" in payload
    assert payload.get("required_uploads_complete") is True
    print(
        f"[OK] Submission preview works "
        f"(Answered: {payload['answered']}/{payload['total_questions']})"
    )


def test_submit_attempt(attempt_id):
    """Test final submission."""
    response = HTTP.post(f"{BASE_URL}/api/attempt/{attempt_id}/submit", timeout=10)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "submitted"
    print("[OK] Test submitted successfully")


def test_confirmation_page(attempt_id):
    """Test the confirmation page."""
    response = HTTP.get(f"{BASE_URL}/submission/{attempt_id}", timeout=10)
    assert response.status_code == 200, response.text
    assert b"submitted" in response.content.lower()
    print("[OK] Confirmation page works")


def test_duplicate_submission_is_rejected(attempt_id):
    """A submitted attempt must not be submitted or edited again."""
    response = HTTP.post(f"{BASE_URL}/api/attempt/{attempt_id}/submit", timeout=10)
    assert response.status_code == 409, (
        f"Expected duplicate submission to return 409, got {response.status_code}: {response.text}"
    )

    response = HTTP.post(
        f"{BASE_URL}/api/attempt/{attempt_id}/response",
        json={"question_id": "Q001", "selected_answer": "A"},
        timeout=10,
    )
    assert response.status_code == 409, (
        f"Expected post-submission response edit to return 409, got {response.status_code}: {response.text}"
    )
    print("[OK] Duplicate submission and post-submission edits are rejected")


def test_cross_student_access_is_rejected(attempt_id):
    """A separate browser session must not be able to access another student's attempt."""
    other_student = requests.Session()
    homepage = other_student.get(f"{BASE_URL}/", timeout=10)
    assert homepage.status_code in (200, 302)

    response = other_student.get(
        f"{BASE_URL}/api/attempt/{attempt_id}/questions", timeout=10
    )
    assert response.status_code == 403, (
        f"Expected cross-student access to return 403, got {response.status_code}"
    )
    print("[OK] Cross-student attempt access is rejected")


def run_all_tests():
    """Run the complete HTTP smoke workflow against an isolated CI database."""
    print("\n=== IMPROVIA END-TO-END SMOKE SUITE ===\n")
    try:
        test_homepage()
        test_teacher_access_is_protected()
        test_test_listing()
        test_instructions()

        attempt_id = test_start_test()
        questions = test_get_questions(attempt_id)
        test_save_mcq_response(attempt_id)
        test_save_subjective_response(attempt_id)
        test_upload_required_images(attempt_id, questions)
        test_submission_preview(attempt_id)
        test_submit_attempt(attempt_id)
        test_confirmation_page(attempt_id)
        test_duplicate_submission_is_rejected(attempt_id)
        test_cross_student_access_is_rejected(attempt_id)

        print("\n=== ALL END-TO-END SMOKE TESTS PASSED ===\n")
        return True
    except Exception as exc:
        print(f"\n[FAIL] End-to-end smoke test failed: {exc}\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    sys.exit(0 if run_all_tests() else 1)
