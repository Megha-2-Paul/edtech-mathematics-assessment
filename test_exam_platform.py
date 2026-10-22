import io
import sys
from pathlib import Path

import requests
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))

BASE_URL = "http://127.0.0.1:5000"
TEACHER_AUTH = ("teacher", "ci-only-teacher-password")
REGISTRATION_SECRET = "ci-only-registration-secret"
HTTP = requests.Session()


def test_homepage():
    """The public landing route should redirect to the student workflow."""
    response = HTTP.get(f"{BASE_URL}/", allow_redirects=False, timeout=10)
    assert response.status_code == 302, f"Homepage failed: {response.status_code}"
    login_page = HTTP.get(f"{BASE_URL}/student/login", timeout=10)
    assert login_page.status_code == 200
    assert b"Student ID" in login_page.content
    print("[OK] Homepage and student login page load")


def test_teacher_access_is_protected():
    """Teacher pages must reject unauthenticated requests."""
    response = requests.get(f"{BASE_URL}/teacher/tests", timeout=10)
    assert response.status_code == 401, (
        f"Expected unauthenticated teacher access to return 401, got {response.status_code}"
    )
    print("[OK] Teacher route rejects unauthenticated access")


def test_registration_and_student_activation():
    """A registration receives a permanent ID and access requires a one-time activation."""
    row = {
        "Full name": "CI Registered Student",
        "Email": "ci.student@example.com",
        "Phone number": "9876501234",
        "Class": "10",
        "Board": "CBSE",
        "Subject": "Mathematics",
        "Enrollment Status": "APPROVED",
    }
    denied = requests.post(
        f"{BASE_URL}/api/registrations/google-form",
        json={"row": row},
        headers={"X-Improvia-Webhook-Secret": "wrong-secret"},
        timeout=10,
    )
    assert denied.status_code == 401, "Registration webhook must reject an invalid secret"

    response = requests.post(
        f"{BASE_URL}/api/registrations/google-form",
        json={"row": row},
        headers={"X-Improvia-Webhook-Secret": REGISTRATION_SECRET},
        timeout=10,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload.get("status") == "ENROLLED", payload
    student_id = payload.get("student_id")
    assert student_id and student_id.startswith("STU")

    repeated = requests.post(
        f"{BASE_URL}/api/registrations/google-form",
        json={"row": row},
        headers={"X-Improvia-Webhook-Secret": REGISTRATION_SECRET},
        timeout=10,
    )
    assert repeated.status_code == 200, repeated.text
    assert repeated.json().get("student_id") == student_id, (
        "Retrying the same registration must reuse the permanent Student ID"
    )

    link_response = requests.post(
        f"{BASE_URL}/teacher/students/{student_id}/access-link",
        auth=TEACHER_AUTH,
        timeout=10,
    )
    assert link_response.status_code == 201, link_response.text
    activation_url = link_response.json().get("activation_url")
    assert activation_url

    activation_page = HTTP.get(activation_url, timeout=10)
    assert activation_page.status_code == 200, activation_page.text
    password = "CI-Only-Strong-Password-2026!"
    activated = HTTP.post(
        activation_url,
        data={"password": password, "confirm_password": password},
        allow_redirects=True,
        timeout=10,
    )
    assert activated.status_code == 200, activated.text
    assert "/tests" in activated.url

    reused = HTTP.post(
        activation_url,
        data={"password": password, "confirm_password": password},
        timeout=10,
    )
    assert reused.status_code == 400, "Activation token must be single-use"

    # Log out and prove that credentials authenticate the registered student.
    HTTP.post(f"{BASE_URL}/student/logout", timeout=10)
    login = HTTP.post(
        f"{BASE_URL}/student/login",
        data={"student_id": student_id, "password": password},
        allow_redirects=True,
        timeout=10,
    )
    assert login.status_code == 200, login.text
    assert "/tests" in login.url
    print("[OK] Registration, permanent ID, one-time activation and student login work")
    return student_id, password


def test_test_listing():
    """Test the student assessment listing."""
    response = HTTP.get(f"{BASE_URL}/tests", timeout=10)
    assert response.status_code == 200
    assert b"Available Tests" in response.content or b"Interface Demo" in response.content
    print("[OK] Test listing page works")


def test_instructions():
    """Test the test instructions page."""
    response = HTTP.get(f"{BASE_URL}/test/TEST001/instructions", timeout=10)
    assert response.status_code == 200, response.text
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
    response = HTTP.post(
        f"{BASE_URL}/api/attempt/{attempt_id}/response",
        json={"question_id": "Q001", "selected_answer": "B"},
        timeout=10,
    )
    assert response.status_code == 200, response.text
    print("[OK] MCQ response saved")


def test_save_subjective_response(attempt_id):
    response = HTTP.post(
        f"{BASE_URL}/api/attempt/{attempt_id}/response",
        json={"question_id": "Q005", "selected_answer": "A"},
        timeout=10,
    )
    assert response.status_code == 200, response.text
    print("[OK] Subjective response saved")


def test_upload_required_images(attempt_id, questions):
    """Upload valid image bytes for every question requiring handwritten work."""
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
    response = HTTP.get(f"{BASE_URL}/api/attempt/{attempt_id}/submit-preview", timeout=10)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert "total_questions" in payload
    assert "answered" in payload
    assert payload.get("required_uploads_complete") is True
    print(f"[OK] Submission preview works (Answered: {payload['answered']}/{payload['total_questions']})")


def test_submit_attempt(attempt_id):
    response = HTTP.post(f"{BASE_URL}/api/attempt/{attempt_id}/submit", timeout=10)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "submitted"
    print("[OK] Test submitted successfully")


def test_confirmation_page(attempt_id):
    response = HTTP.get(f"{BASE_URL}/submission/{attempt_id}", timeout=10)
    assert response.status_code == 200, response.text
    assert b"submitted" in response.content.lower()
    print("[OK] Confirmation page works")


def test_duplicate_submission_is_rejected(attempt_id):
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
        f"Expected post-submission edit to return 409, got {response.status_code}: {response.text}"
    )
    print("[OK] Duplicate submission and post-submission edits are rejected")


def test_cross_student_access_is_rejected():
    """A different authenticated student must not access another student's attempt."""
    other_row = {
        "Full name": "CI Second Student",
        "Email": "ci.student2@example.com",
        "Phone number": "9876501235",
        "Class": "10",
        "Board": "CBSE",
        "Subject": "Mathematics",
        "Enrollment Status": "APPROVED",
    }
    registration = requests.post(
        f"{BASE_URL}/api/registrations/google-form",
        json={"row": other_row},
        headers={"X-Improvia-Webhook-Secret": REGISTRATION_SECRET},
        timeout=10,
    )
    assert registration.status_code == 200, registration.text
    second_id = registration.json().get("student_id")
    assert second_id

    link = requests.post(
        f"{BASE_URL}/teacher/students/{second_id}/access-link",
        auth=TEACHER_AUTH,
        timeout=10,
    )
    assert link.status_code == 201, link.text

    second_session = requests.Session()
    activation_url = link.json()["activation_url"]
    assert second_session.get(activation_url, timeout=10).status_code == 200
    password = "CI-Only-Second-Strong-Password-2026!"
    assert second_session.post(
        activation_url,
        data={"password": password, "confirm_password": password},
        allow_redirects=True,
        timeout=10,
    ).status_code == 200

    # The first student's attempt ID is provided by the caller through module state.
    response = second_session.get(
        f"{BASE_URL}/api/attempt/{CURRENT_ATTEMPT_ID}/questions", timeout=10
    )
    assert response.status_code == 403, (
        f"Expected cross-student access to return 403, got {response.status_code}"
    )
    print("[OK] Cross-student attempt access is rejected")


CURRENT_ATTEMPT_ID = None


def run_all_tests():
    global CURRENT_ATTEMPT_ID
    print("\n=== IMPROVIA END-TO-END SMOKE SUITE ===\n")
    try:
        test_homepage()
        test_teacher_access_is_protected()
        test_registration_and_student_activation()
        test_test_listing()
        test_instructions()
        CURRENT_ATTEMPT_ID = test_start_test()
        questions = test_get_questions(CURRENT_ATTEMPT_ID)
        test_save_mcq_response(CURRENT_ATTEMPT_ID)
        test_save_subjective_response(CURRENT_ATTEMPT_ID)
        test_upload_required_images(CURRENT_ATTEMPT_ID, questions)
        test_submission_preview(CURRENT_ATTEMPT_ID)
        test_submit_attempt(CURRENT_ATTEMPT_ID)
        test_confirmation_page(CURRENT_ATTEMPT_ID)
        test_duplicate_submission_is_rejected(CURRENT_ATTEMPT_ID)
        test_cross_student_access_is_rejected()
        print("\n=== ALL END-TO-END SMOKE TESTS PASSED ===\n")
        return True
    except Exception as exc:
        print(f"\n[FAIL] End-to-end smoke test failed: {exc}\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    sys.exit(0 if run_all_tests() else 1)
