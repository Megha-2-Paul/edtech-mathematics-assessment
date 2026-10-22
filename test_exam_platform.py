import io
import re
import sys
from pathlib import Path

import requests
from PIL import Image
from pypdf import PdfReader
from sqlalchemy import text
from database import engine

sys.path.insert(0, str(Path(__file__).parent))

BASE_URL = "http://127.0.0.1:5000"
TEACHER_AUTH = ("teacher", "ci-only-teacher-password")
REGISTRATION_SECRET = "ci-only-registration-secret"
HTTP = requests.Session()
CURRENT_STUDENT_ID = None
CURRENT_ATTEMPT_ID = None
UPLOADS_BY_ATTEMPT = {}


def test_homepage():
    response = HTTP.get(f"{BASE_URL}/", allow_redirects=False, timeout=10)
    assert response.status_code == 302, f"Homepage failed: {response.status_code}"
    login_page = HTTP.get(f"{BASE_URL}/student/login", timeout=10)
    assert login_page.status_code == 200
    assert b"Student ID" in login_page.content
    anonymous = requests.Session()
    protected = anonymous.get(f"{BASE_URL}/tests", allow_redirects=False, timeout=10)
    assert protected.status_code == 302 and "/student/login" in protected.headers.get("Location", "")
    api = anonymous.post(f"{BASE_URL}/api/test/TEST001/start", timeout=10)
    assert api.status_code == 401
    print("[OK] Homepage loads and anonymous assessment access is blocked")


def test_teacher_access_is_protected():
    response = requests.get(f"{BASE_URL}/teacher/tests", timeout=10)
    assert response.status_code == 401, (
        f"Expected unauthenticated teacher access to return 401, got {response.status_code}"
    )
    print("[OK] Teacher route rejects unauthenticated access")


def register_student(name, email, phone):
    row = {
        "Full name": name,
        "Email": email,
        "Phone number": phone,
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
    with engine.connect() as db:
        enrollment = db.execute(
            text(
                "SELECT 1 FROM student_subject_enrollments "
                "WHERE student_id=:student_id AND board='CBSE' AND class_level=10 "
                "AND academic_year='2026-27' AND status='ACTIVE' LIMIT 1"
            ),
            {"student_id": student_id},
        ).first()
    assert enrollment, "Approved registration must persist the verified curriculum enrollment"

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
    return student_id


def activate_student(student_id, session, password):
    link_response = requests.post(
        f"{BASE_URL}/teacher/students/{student_id}/access-link",
        auth=TEACHER_AUTH,
        timeout=10,
    )
    assert link_response.status_code == 201, link_response.text
    activation_url = link_response.json().get("activation_url")
    assert activation_url

    activation_page = session.get(activation_url, timeout=10)
    assert activation_page.status_code == 200, activation_page.text
    activated = session.post(
        activation_url,
        data={"password": password, "confirm_password": password},
        allow_redirects=True,
        timeout=10,
    )
    assert activated.status_code == 200, activated.text
    assert "/tests" in activated.url

    reused = session.post(
        activation_url,
        data={"password": password, "confirm_password": password},
        timeout=10,
    )
    assert reused.status_code == 400, "Activation token must be single-use"


def test_registration_and_student_activation():
    global CURRENT_STUDENT_ID
    student_id = register_student(
        "CI Registered Student", "ci.student@example.com", "9876501234"
    )
    password = "CI-Only-Strong-Password-2026!"
    activate_student(student_id, HTTP, password)

    HTTP.post(f"{BASE_URL}/student/logout", timeout=10)
    login = HTTP.post(
        f"{BASE_URL}/student/login",
        data={"student_id": student_id, "password": "incorrect-password"},
        timeout=10,
    )
    assert login.status_code == 401, "Invalid student credentials must be rejected"

    login = HTTP.post(
        f"{BASE_URL}/student/login",
        data={"student_id": student_id, "password": password},
        allow_redirects=True,
        timeout=10,
    )
    assert login.status_code == 200, login.text
    assert "/tests" in login.url
    CURRENT_STUDENT_ID = student_id
    print("[OK] Registration, permanent ID, one-time activation and login work")
    return student_id


def test_test_listing():
    response = HTTP.get(f"{BASE_URL}/tests", timeout=10)
    assert response.status_code == 200
    assert b"Available Tests" in response.content or b"Interface Demo" in response.content
    print("[OK] Test listing page works")


def test_instructions(test_id="TEST001"):
    response = HTTP.get(f"{BASE_URL}/test/{test_id}/instructions", timeout=10)
    assert response.status_code == 200, response.text
    assert b"Before you start" in response.content
    print(f"[OK] Instructions page works for {test_id}")


def test_start_test(test_id):
    response = HTTP.post(f"{BASE_URL}/api/test/{test_id}/start", timeout=10)
    assert response.status_code == 200, response.text
    data = response.json()
    assert "attempt_id" in data and "redirect_url" in data
    print(f"[OK] Test start works for {test_id}")
    return data["attempt_id"]


def test_get_questions(attempt_id):
    response = HTTP.get(f"{BASE_URL}/api/attempt/{attempt_id}/questions", timeout=10)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert isinstance(payload, dict) and "questions" in payload
    questions = payload["questions"]
    assert len(questions) > 0
    assert questions[0]["question_type"] in ("mcq", "subjective", "vsaq", "saq", "laq")
    print(f"[OK] Questions loaded ({len(questions)} questions)")
    return questions


def save_sample_answers(attempt_id, questions):
    question_ids = {q["question_id"] for q in questions}
    assert "Q001" in question_ids and "Q005" in question_ids
    response = HTTP.post(
        f"{BASE_URL}/api/attempt/{attempt_id}/response",
        json={"question_id": "Q001", "selected_answer": "B"},
        timeout=10,
    )
    assert response.status_code == 200, response.text
    response = HTTP.post(
        f"{BASE_URL}/api/attempt/{attempt_id}/response",
        json={"question_id": "Q005", "selected_answer": "A"},
        timeout=10,
    )
    assert response.status_code == 200, response.text
    print("[OK] MCQ and subjective answers saved")


def upload_required_images(attempt_id, questions):
    required = [
        question for question in questions
        if question.get("handwritten_upload_mode") == "required"
    ]
    assert required, "Demo assessment must exercise required handwritten uploads"

    missing_submission = HTTP.post(
        f"{BASE_URL}/api/attempt/{attempt_id}/submit", timeout=10
    )
    assert missing_submission.status_code == 400, (
        "Submission must be blocked while required handwritten work is missing"
    )

    question_id = required[0]["question_id"]
    unsupported = HTTP.post(
        f"{BASE_URL}/api/attempt/{attempt_id}/upload",
        data={"question_id": question_id},
        files={"file": ("answer.txt", b"not an image", "text/plain")},
        timeout=10,
    )
    assert unsupported.status_code == 400, "Unsupported upload extensions must be rejected"

    invalid_image = HTTP.post(
        f"{BASE_URL}/api/attempt/{attempt_id}/upload",
        data={"question_id": question_id},
        files={"file": ("fake.png", b"not a valid PNG image", "image/png")},
        timeout=10,
    )
    assert invalid_image.status_code == 400, "Invalid image content must be rejected"

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
        payload = response.json()
        assert payload.get("image_id")
        UPLOADS_BY_ATTEMPT.setdefault(attempt_id, []).append(
            {"image_id": payload["image_id"], "filename": payload["filename"], "question_id": question["question_id"]}
        )
        student_image = HTTP.get(
            f"{BASE_URL}/api/attempt/{attempt_id}/image/{payload['image_id']}", timeout=10
        )
        assert student_image.status_code == 200, (
            f"Owner could not retrieve uploaded image: {student_image.status_code}"
        )
        assert student_image.headers.get("Content-Type", "").startswith("image/")
    print(f"[OK] Required handwritten uploads persisted ({len(required)} questions)")


def test_submission_preview(attempt_id):
    response = HTTP.get(f"{BASE_URL}/api/attempt/{attempt_id}/submit-preview", timeout=10)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert "total_questions" in payload and "answered" in payload
    assert payload.get("required_uploads_complete") is True
    print("[OK] Submission preview works")


def test_submit_attempt(attempt_id):
    response = HTTP.post(f"{BASE_URL}/api/attempt/{attempt_id}/submit", timeout=10)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "submitted"
    print("[OK] Test submitted successfully")


def test_confirmation_page(attempt_id):
    response = HTTP.get(f"{BASE_URL}/submission/{attempt_id}", timeout=10)
    assert response.status_code == 200, response.text
    assert b"submitted" in response.content.lower()
    print("[OK] Submission confirmation works")


def test_duplicate_submission_is_rejected(attempt_id):
    response = HTTP.post(f"{BASE_URL}/api/attempt/{attempt_id}/submit", timeout=10)
    assert response.status_code == 409, (
        f"Expected duplicate submission 409, got {response.status_code}: {response.text}"
    )
    response = HTTP.post(
        f"{BASE_URL}/api/attempt/{attempt_id}/response",
        json={"question_id": "Q001", "selected_answer": "A"},
        timeout=10,
    )
    assert response.status_code == 409, (
        f"Expected post-submission edit 409, got {response.status_code}: {response.text}"
    )
    print("[OK] Duplicate submission and post-submission edits are rejected")


def teacher_evaluate(attempt_id, marks, error_codes):
    """Verify teacher image access and evaluate a submitted attempt."""
    response = requests.get(
        f"{BASE_URL}/teacher/submissions",
        auth=TEACHER_AUTH,
        timeout=10,
    )
    assert response.status_code == 200, response.text
    assert attempt_id.encode() in response.content

    evaluation_page = requests.get(
        f"{BASE_URL}/teacher/evaluate/{attempt_id}",
        auth=TEACHER_AUTH,
        timeout=10,
    )
    assert evaluation_page.status_code == 200, evaluation_page.text
    attempt_uploads = UPLOADS_BY_ATTEMPT.get(attempt_id, [])
    if attempt_uploads:
        image_id = attempt_uploads[0]["image_id"]
        protected_image_url = f"{BASE_URL}/teacher/attempt/{attempt_id}/image/{image_id}"
        assert f"/teacher/attempt/{attempt_id}/image/{image_id}".encode() in evaluation_page.content
        unauthenticated = requests.get(protected_image_url, timeout=10)
        assert unauthenticated.status_code == 401, (
            "Teacher answer-image proxy must reject unauthenticated access"
        )
        authorized = requests.get(protected_image_url, auth=TEACHER_AUTH, timeout=10)
        assert authorized.status_code == 200, authorized.text[:200]
        assert authorized.headers.get("Content-Type", "").startswith("image/")

        raw_url = f"{BASE_URL}/uploads/{attempt_uploads[0]['filename']}"
        raw_response = requests.get(raw_url, timeout=10)
        assert raw_response.status_code == 403, (
            f"Raw answer-image URL must not be public, got {raw_response.status_code}"
        )

    manual_question_ids = re.findall(r'name="marks_([^"]+)"', evaluation_page.text)
    assert manual_question_ids, "Expected manual-mark fields for written-response questions"

    # Omit at least one written-response mark. The two-question follow-up test
    # has only one manual field, so submit no manual marks for that case.
    partial_ids = manual_question_ids[:-1] if len(manual_question_ids) > 1 else []
    partial = [
        (f"marks_{question_id}", str(marks.get(question_id, 0)))
        for question_id in partial_ids
    ]
    rejected = requests.post(
        f"{BASE_URL}/teacher/evaluate/{attempt_id}",
        auth=TEACHER_AUTH,
        data=partial,
        allow_redirects=False,
        timeout=15,
    )
    assert rejected.status_code == 302, (
        f"Incomplete evaluation should redirect with a validation message, got {rejected.status_code}: {rejected.text[:300]}"
    )
    with engine.connect() as db:
        saved_before_complete = sum(
            db.execute(
                text(
                    "SELECT COUNT(*) FROM responses "
                    "WHERE attempt_id=:attempt_id AND question_id=:question_id "
                    "AND marks_awarded IS NOT NULL"
                ),
                {"attempt_id": attempt_id, "question_id": question_id},
            ).scalar_one()
            for question_id in manual_question_ids
        )
    assert saved_before_complete == 0, (
        "A rejected partial evaluation must not save marks for any written response"
    )

    form_data = [
        (f"marks_{question_id}", str(marks.get(question_id, 0)))
        for question_id in manual_question_ids
    ]
    for question_id in manual_question_ids:
        for code in error_codes.get(question_id, []):
            form_data.append((f"errors_{question_id}", code))
        form_data.append((f"comment_{question_id}", "CI evaluation evidence"))
    response = requests.post(
        f"{BASE_URL}/teacher/evaluate/{attempt_id}",
        auth=TEACHER_AUTH,
        data=form_data,
        allow_redirects=True,
        timeout=15,
    )
    assert response.status_code == 200, response.text
    print(f"[OK] Teacher evaluation saved for {attempt_id}")


def test_report_and_pdf(attempt_id, student_id):
    report = HTTP.get(f"{BASE_URL}/report/{attempt_id}", timeout=15)
    assert report.status_code == 200, report.text
    assert b"Recorded error patterns" in report.content
    pdf_response = HTTP.get(f"{BASE_URL}/report/{attempt_id}/pdf", timeout=15)
    assert pdf_response.status_code == 200, pdf_response.text[:500]
    assert pdf_response.headers.get("Content-Type", "").startswith("application/pdf")
    reader = PdfReader(io.BytesIO(pdf_response.content))
    assert len(reader.pages) == 2, f"Expected exactly two pages, got {len(reader.pages)}"
    pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert student_id in pdf_text, "PDF does not identify the intended student"
    assert "CI Second Student" not in pdf_text, "PDF contains another student's identity"
    print("[OK] Report is ready and the student receives the correct two-page PDF")


def create_second_test():
    """Create a distinct follow-up test through the teacher test-creation route."""
    response = requests.post(
        f"{BASE_URL}/teacher/tests/new",
        auth=TEACHER_AUTH,
        data=[
            ("title", "CI Follow-up Mathematics Assessment"),
            ("subject", "Mathematics"),
            ("class_level", "10"),
            ("board", "CBSE"),
            ("duration_minutes", "20"),
            ("test_type", "weekly"),
            ("status", "active"),
            ("question_ids", "Q001"),
            ("question_ids", "Q005"),
        ],
        allow_redirects=True,
        timeout=15,
    )
    assert response.status_code == 200, response.text
    assert b"TEST002" in response.content, "Follow-up test was not created"
    print("[OK] Teacher created and published a second assessment")
    return "TEST002"


def test_reissued_access_link_invalidates_old_link(student_id):
    """Only the newest outstanding account activation/reset link may be used."""
    first = requests.post(
        f"{BASE_URL}/teacher/students/{student_id}/access-link",
        auth=TEACHER_AUTH,
        timeout=10,
    )
    second = requests.post(
        f"{BASE_URL}/teacher/students/{student_id}/access-link",
        auth=TEACHER_AUTH,
        timeout=10,
    )
    assert first.status_code == 201 and second.status_code == 201
    old_page = HTTP.get(first.json()["activation_url"], timeout=10)
    assert old_page.status_code == 400, "Reissuing access must invalidate the older link"

    new_url = second.json()["activation_url"]
    new_page = HTTP.get(new_url, timeout=10)
    assert new_page.status_code == 200
    password = "CI-Only-Strong-Password-2026!"
    reset = HTTP.post(
        new_url,
        data={"password": password, "confirm_password": password},
        allow_redirects=True,
        timeout=10,
    )
    assert reset.status_code == 200
    print("[OK] Reissued access link invalidates stale links")


def test_cross_student_access_is_rejected():
    """A second authenticated student must not read the first student's attempt or report."""
    second_id = register_student(
        "CI Second Student", "ci.student2@example.com", "9876501235"
    )
    second_session = requests.Session()
    activate_student(
        second_id,
        second_session,
        "CI-Only-Second-Strong-Password-2026!",
    )
    response = second_session.get(
        f"{BASE_URL}/api/attempt/{CURRENT_ATTEMPT_ID}/questions", timeout=10
    )
    assert response.status_code == 403, (
        f"Expected cross-student attempt access 403, got {response.status_code}"
    )
    for uploaded in UPLOADS_BY_ATTEMPT.get(CURRENT_ATTEMPT_ID, []):
        image_response = second_session.get(
            f"{BASE_URL}/api/attempt/{CURRENT_ATTEMPT_ID}/image/{uploaded['image_id']}",
            timeout=10,
        )
        assert image_response.status_code == 403, (
            "Another student must not retrieve handwritten answer images"
        )
        raw_response = requests.get(
            f"{BASE_URL}/uploads/{uploaded['filename']}", timeout=10
        )
        assert raw_response.status_code == 403, "Raw answer-image URL must not be public"
    response = second_session.get(
        f"{BASE_URL}/report/{CURRENT_ATTEMPT_ID}", timeout=10
    )
    assert response.status_code == 403, (
        f"Expected cross-student report access 403, got {response.status_code}"
    )
    print("[OK] Cross-student attempt and report access are rejected")


def run_all_tests():
    global CURRENT_ATTEMPT_ID
    print("\n=== IMPROVIA END-TO-END SMOKE SUITE ===\n")
    try:
        test_homepage()
        test_teacher_access_is_protected()
        student_id = test_registration_and_student_activation()
        test_test_listing()
        test_instructions("TEST001")

        CURRENT_ATTEMPT_ID = test_start_test("TEST001")
        questions = test_get_questions(CURRENT_ATTEMPT_ID)
        save_sample_answers(CURRENT_ATTEMPT_ID, questions)
        upload_required_images(CURRENT_ATTEMPT_ID, questions)
        test_submission_preview(CURRENT_ATTEMPT_ID)
        test_submit_attempt(CURRENT_ATTEMPT_ID)
        test_confirmation_page(CURRENT_ATTEMPT_ID)
        test_duplicate_submission_is_rejected(CURRENT_ATTEMPT_ID)
        teacher_evaluate(CURRENT_ATTEMPT_ID, {"Q005": 2}, {"Q005": ["C01", "C04"]})
        test_report_and_pdf(CURRENT_ATTEMPT_ID, student_id)

        second_test_id = create_second_test()
        test_instructions(second_test_id)
        second_attempt_id = test_start_test(second_test_id)
        second_questions = test_get_questions(second_attempt_id)
        save_sample_answers(second_attempt_id, second_questions)
        upload_required_images(second_attempt_id, second_questions)
        test_submission_preview(second_attempt_id)
        test_submit_attempt(second_attempt_id)
        teacher_evaluate(second_attempt_id, {"Q005": 2}, {"Q005": ["C01"]})
        second_report = HTTP.get(f"{BASE_URL}/report/{second_attempt_id}", timeout=15)
        assert second_report.status_code == 200, second_report.text
        assert b"Recurring patterns" in second_report.content, (
            "Second assessment did not surface recurring-error history"
        )
        test_report_and_pdf(second_attempt_id, student_id)
        test_reissued_access_link_invalidates_old_link(student_id)
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
