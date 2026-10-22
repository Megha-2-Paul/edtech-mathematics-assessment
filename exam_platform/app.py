import hashlib
import hmac
import os
import secrets
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from PIL import Image
from sqlalchemy import text
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

sys.path.insert(0, str(Path(__file__).parent.parent))

from exam_platform.admin import register_admin
from database import engine
from exam_platform.db_source import storage
from exam_platform.mock_data import load_mock_data
from exam_platform.eligibility import is_test_eligible
from exam_platform.models import (
    AnswerImage,
    AnswerStatus,
    Attempt,
    AttemptStatus,
    Response,
    Student,
)
from question_bank.extraction.review_app import register_extraction_review


# ---------------------------------------------------------------------------
# Application configuration
# ---------------------------------------------------------------------------

app = Flask(__name__)
_configured_secret = os.getenv("SECRET_KEY")
if os.getenv("RENDER") and not _configured_secret:
    raise RuntimeError("SECRET_KEY must be configured on the hosted service.")
app.secret_key = _configured_secret or secrets.token_hex(32)
app.config.update(
    MAX_CONTENT_LENGTH=50 * 1024 * 1024,
    MAX_IMAGE_SIZE=10 * 1024 * 1024,
    UPLOAD_FOLDER=str(Path(__file__).parent.parent / "uploads"),
    EXAM_MONITORING_MODES={"off", "optional", "required"},
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(os.getenv("RENDER")),
)
app.permanent_session_lifetime = timedelta(hours=12)
Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

register_admin(app)
register_extraction_review(app)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}


# ---------------------------------------------------------------------------
# Student/session helpers
# ---------------------------------------------------------------------------


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_or_create_student_id():
    """Return the authenticated Student_ID; never invent an anonymous identity."""
    return session.get("student_id")


def ensure_student_record(student_id):
    """Look up an enrolled student without creating a guest account."""
    return storage.get_student(student_id)


STUDENT_PROTECTED_PREFIXES = (
    "/tests",
    "/test/",
    "/api/test/",
    "/api/attempt/",
    "/submission/",
    "/report/",
    "/result/",
    "/student/report/",
    "/student/result/",
)


@app.before_request
def enforce_student_access():
    """Require a real active student account for every student assessment route."""
    if request.path.startswith("/teacher"):
        return None
    if request.endpoint in {
        "index",
        "student_login",
        "student_activate",
        "student_logout",
        "google_form_registration_webhook",
        "static",
    }:
        return None
    if not request.path.startswith(STUDENT_PROTECTED_PREFIXES):
        return None

    student_id = session.get("student_id")
    if not student_id:
        if request.path.startswith("/api/"):
            return jsonify({"error": "Student login required"}), 401
        return redirect(url_for("student_login"))

    student = storage.get_student(student_id)
    if not student or str(student.status or "").lower() != "active":
        session.clear()
        if request.path.startswith("/api/"):
            return jsonify({"error": "Student account is unavailable"}), 401
        return redirect(url_for("student_login"))
    return None


@app.route("/student/login", methods=["GET", "POST"])
def student_login():
    """Authenticate an enrolled student with a founder-issued activation password."""
    if request.method == "GET":
        return render_template("student_login.html", error=None)

    student_id = str(request.form.get("student_id") or "").strip().upper()
    password = str(request.form.get("password") or "")
    authenticated_student_id = None
    now = datetime.now()

    if student_id and password:
        with engine.begin() as db:
            row = db.execute(
                text(
                    "SELECT c.password_hash,c.failed_login_count,c.locked_until,s.status "
                    "FROM student_access_credentials c "
                    "JOIN students s ON s.student_id=c.student_id "
                    "WHERE c.student_id=:student_id FOR UPDATE"
                ),
                {"student_id": student_id},
            ).mappings().first()

            if row and str(row["status"] or "").lower() == "active":
                locked_until = row["locked_until"]
                if locked_until and locked_until > now:
                    authenticated_student_id = None
                elif check_password_hash(row["password_hash"], password):
                    db.execute(
                        text(
                            "UPDATE student_access_credentials "
                            "SET failed_login_count=0,locked_until=NULL,last_login_at=:now,updated_at=:now "
                            "WHERE student_id=:student_id"
                        ),
                        {"student_id": student_id, "now": now},
                    )
                    authenticated_student_id = student_id
                else:
                    failures = int(row["failed_login_count"] or 0) + 1
                    lock = now + timedelta(minutes=15) if failures >= 5 else None
                    db.execute(
                        text(
                            "UPDATE student_access_credentials "
                            "SET failed_login_count=:failures,locked_until=:locked,updated_at=:now "
                            "WHERE student_id=:student_id"
                        ),
                        {
                            "student_id": student_id,
                            "failures": failures,
                            "locked": lock,
                            "now": now,
                        },
                    )

    if not authenticated_student_id:
        return render_template(
            "student_login.html",
            error="Login failed. Check your Student ID and password, or contact Improvia for a new access link.",
        ), 401

    session.clear()
    session["student_id"] = authenticated_student_id
    session.permanent = True
    return redirect(url_for("test_listing"))


@app.route("/student/logout", methods=["POST"])
def student_logout():
    session.clear()
    return redirect(url_for("student_login"))


def _access_token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@app.route("/student/activate", methods=["GET", "POST"])
def student_activate():
    """Set an initial password using a single-use, expiring teacher-issued link."""
    token = str(request.values.get("token") or "").strip()
    if not token or len(token) > 256:
        return render_template("student_activate.html", token="", error="This activation link is invalid or expired."), 400

    if request.method == "GET":
        now = datetime.now()
        with engine.connect() as db:
            row = db.execute(
                text(
                    "SELECT student_id FROM student_access_tokens "
                    "WHERE token_hash=:token_hash AND used_at IS NULL AND expires_at>:now"
                ),
                {"token_hash": _access_token_hash(token), "now": now},
            ).mappings().first()
        if not row:
            return render_template("student_activate.html", token="", error="This activation link is invalid or expired."), 400
        return render_template("student_activate.html", token=token, error=None)

    password = str(request.form.get("password") or "")
    confirmation = str(request.form.get("confirm_password") or "")
    if len(password) < 12:
        return render_template("student_activate.html", token=token, error="Use a password with at least 12 characters."), 400
    if password != confirmation:
        return render_template("student_activate.html", token=token, error="The passwords do not match."), 400

    now = datetime.now()
    token_hash = _access_token_hash(token)
    password_hash = generate_password_hash(password)
    activated_student_id = None
    with engine.begin() as db:
        row = db.execute(
            text(
                "SELECT student_id,expires_at,used_at FROM student_access_tokens "
                "WHERE token_hash=:token_hash FOR UPDATE"
            ),
            {"token_hash": token_hash},
        ).mappings().first()
        if row and row["used_at"] is None and row["expires_at"] > now:
            student = db.execute(
                text("SELECT status FROM students WHERE student_id=:student_id"),
                {"student_id": row["student_id"]},
            ).mappings().first()
            if student and str(student["status"] or "").lower() == "active":
                db.execute(
                    text(
                        "INSERT INTO student_access_credentials "
                        "(student_id,password_hash,failed_login_count,locked_until,created_at,updated_at) "
                        "VALUES(:student_id,:password_hash,0,NULL,:now,:now) "
                        "ON DUPLICATE KEY UPDATE password_hash=:password_hash,"
                        "failed_login_count=0,locked_until=NULL,updated_at=:now"
                    ),
                    {
                        "student_id": row["student_id"],
                        "password_hash": password_hash,
                        "now": now,
                    },
                )
                db.execute(
                    text("UPDATE student_access_tokens SET used_at=:now WHERE token_hash=:token_hash AND used_at IS NULL"),
                    {"token_hash": token_hash, "now": now},
                )
                activated_student_id = row["student_id"]

    if not activated_student_id:
        return render_template("student_activate.html", token="", error="This activation link is invalid, expired, or already used."), 400

    session.clear()
    session["student_id"] = activated_student_id
    session.permanent = True
    return redirect(url_for("test_listing"))


@app.route("/teacher/students/<student_id>/access-link", methods=["POST"])
def create_student_access_link(student_id):
    """Issue a single-use activation link for an enrolled student.

    This endpoint is intended for the authenticated teacher/operator. The raw
    token is returned once so the founder can deliver it through the approved
    communication channel; only its SHA-256 hash is stored in MySQL.
    """
    student = storage.get_student(student_id)
    if not student or str(student.status or "").lower() != "active":
        return jsonify({"error": "Active student not found"}), 404

    token = secrets.token_urlsafe(32)
    now = datetime.now()
    expires_at = now + timedelta(hours=24)
    with engine.begin() as db:
        db.execute(
            text(
                "INSERT INTO student_access_tokens "
                "(token_hash,student_id,expires_at,used_at,created_at) "
                "VALUES(:token_hash,:student_id,:expires_at,NULL,:now)"
            ),
            {
                "token_hash": _access_token_hash(token),
                "student_id": student_id,
                "expires_at": expires_at,
                "now": now,
            },
        )

    return jsonify(
        {
            "student_id": student_id,
            "activation_url": url_for("student_activate", token=token, _external=True),
            "expires_at": expires_at.isoformat(),
            "message": "Send this one-time link privately to the student. It expires in 24 hours.",
        }
    ), 201


# ---------------------------------------------------------------------------
# Google registration webhook
# ---------------------------------------------------------------------------

@app.route("/api/registrations/google-form", methods=["POST"])
def google_form_registration_webhook():
    """Receive a reviewed Google Form/Sheet row and enroll only approved rows."""
    expected_secret = os.getenv("GOOGLE_REGISTRATION_WEBHOOK_SECRET", "").strip()
    supplied_secret = request.headers.get("X-Improvia-Webhook-Secret", "").strip()

    if not expected_secret:
        return jsonify({"error": "Google registration webhook is not configured"}), 503
    if not supplied_secret or not hmac.compare_digest(supplied_secret, expected_secret):
        return jsonify({"error": "Unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    row = payload.get("row")
    if not isinstance(row, dict):
        return jsonify({"error": "Expected JSON object field 'row'"}), 400

    from exam_platform.registration_pipeline import (
        DEFAULT_ENROLLMENT_STATUSES,
        _value,
        enroll_student,
        extract_registration,
    )

    enrollment_status = _value(row, "enrollment_status").upper()
    if not enrollment_status:
        return jsonify({
            "status": "PENDING",
            "message": "No Enrollment Status; student was not written.",
        }), 200

    if enrollment_status not in DEFAULT_ENROLLMENT_STATUSES:
        return jsonify({
            "status": "SKIPPED",
            "message": f"Enrollment Status={enrollment_status!r}; student was not written.",
        }), 200

    student, error = extract_registration(row, payload.get("row_number", 0))
    if error:
        return jsonify({"status": "ERROR", "message": error}), 400

    try:
        student = enroll_student(student)
    except Exception:
        app.logger.exception("Google registration enrollment failed")
        return jsonify({
            "status": "ERROR",
            "message": "Student enrollment failed.",
        }), 500

    return jsonify({
        "status": "ENROLLED",
        "student_id": student.student_id,
        "message": f"{student.name} enrolled successfully.",
    }), 200



# ---------------------------------------------------------------------------
# Attempt and timer helpers
# ---------------------------------------------------------------------------


def attempt_is_expired(attempt):
    test = storage.get_test(attempt.test_id)
    if not test or attempt.status != AttemptStatus.IN_PROGRESS.value:
        return attempt.status == AttemptStatus.EXPIRED.value

    return datetime.now() >= attempt.started_at + timedelta(
        minutes=test.duration_minutes
    )


def ensure_attempt_access(attempt_id):
    attempt = storage.get_attempt(attempt_id)
    if not attempt:
        return None, (jsonify({"error": "Attempt not found"}), 404)

    if attempt.student_id != session.get("student_id"):
        return None, (
            jsonify({"error": "You do not have access to this attempt"}),
            403,
        )

    # Submitted attempts are immutable. Apply this guard in the shared access
    # helper so both local routes and the deployment adapter reject late writes.
    if attempt.status == AttemptStatus.SUBMITTED.value and request.method in {
        "POST", "PUT", "PATCH", "DELETE"
    }:
        return None, (
            jsonify({
                "error": "This assessment has already been submitted and cannot be changed.",
                "status": "submitted",
            }),
            409,
        )

    if attempt_is_expired(attempt):
        attempt.status = AttemptStatus.EXPIRED.value
        attempt.submitted_at = attempt.submitted_at or datetime.now()
        storage.update_attempt(attempt)
        return None, (jsonify({"error": "Time is up", "status": "expired"}), 410)

    return attempt, None


load_mock_data()


# ---------------------------------------------------------------------------
# Student test listing and instructions
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    return redirect(url_for("test_listing"))


@app.route("/tests")
def test_listing():
    student_id = get_or_create_student_id()
    student = storage.get_student(student_id)
    all_tests = storage.get_all_tests()
    tests = [test for test in all_tests if is_test_eligible(student, test)]
    test_status = {}

    for test in tests:
        attempt = storage.get_student_test_attempt(student_id, test.test_id)

        if attempt and attempt.status == AttemptStatus.SUBMITTED.value:
            test_status[test.test_id] = "taken"
        elif attempt and attempt.status == AttemptStatus.EXPIRED.value:
            test_status[test.test_id] = "expired"
        elif attempt and attempt.status == AttemptStatus.IN_PROGRESS.value:
            if attempt_is_expired(attempt):
                attempt.status = AttemptStatus.EXPIRED.value
                attempt.submitted_at = datetime.now()
                storage.update_attempt(attempt)
                test_status[test.test_id] = "expired"
            else:
                test_status[test.test_id] = "in_progress"
        else:
            test_status[test.test_id] = "available"

    return render_template(
        "test_listing.html",
        tests=tests,
        test_status=test_status,
    )


@app.route("/test/<test_id>/instructions")
def test_instructions(test_id):
    test = storage.get_test(test_id)
    if not test:
        return "Test not found", 404

    student_id = get_or_create_student_id()
    student = storage.get_student(student_id)
    if not is_test_eligible(student, test):
        return "You are not eligible for this assessment.", 403

    existing = storage.get_student_test_attempt(student_id, test_id)

    if existing and existing.status == AttemptStatus.SUBMITTED.value:
        return redirect(url_for("test_listing"))

    if (
        existing
        and existing.status == AttemptStatus.IN_PROGRESS.value
        and not attempt_is_expired(existing)
    ):
        return redirect(
            url_for(
                "exam_interface",
                test_id=test_id,
                attempt_id=existing.attempt_id,
            )
        )

    return render_template(
        "test_instructions.html",
        test=test,
        total_questions=len(storage.get_questions(test.questions)),
    )


@app.route("/api/test/<test_id>/start", methods=["POST"])
def start_test(test_id):
    test = storage.get_test(test_id)
    if not test:
        return jsonify({"error": "Test not found"}), 404

    student_id = get_or_create_student_id()
    ensure_student_record(student_id)
    student = storage.get_student(student_id)
    if not is_test_eligible(student, test):
        return jsonify({"error": "You are not eligible for this assessment"}), 403
    existing = storage.get_student_test_attempt(student_id, test_id)

    if existing:
        if existing.status == AttemptStatus.SUBMITTED.value:
            return jsonify(
                {"error": "Test already taken", "status": "taken"}
            ), 409

        if (
            existing.status == AttemptStatus.IN_PROGRESS.value
            and not attempt_is_expired(existing)
        ):
            session["attempt_id"] = existing.attempt_id
            return jsonify(
                {
                    "attempt_id": existing.attempt_id,
                    "student_id": student_id,
                    "resumed": True,
                    "redirect_url": url_for(
                        "exam_interface",
                        test_id=test_id,
                        attempt_id=existing.attempt_id,
                    ),
                }
            )

        if (
            existing.status == AttemptStatus.EXPIRED.value
            or attempt_is_expired(existing)
        ):
            return jsonify(
                {"error": "Test time has expired", "status": "expired"}
            ), 410

    attempt_id = f"ATT{uuid.uuid4().hex[:12].upper()}"
    storage.create_attempt(
        Attempt(
            attempt_id=attempt_id,
            student_id=student_id,
            test_id=test_id,
            started_at=datetime.now(),
        )
    )
    session["attempt_id"] = attempt_id

    return jsonify(
        {
            "attempt_id": attempt_id,
            "student_id": student_id,
            "resumed": False,
            "redirect_url": url_for(
                "exam_interface",
                test_id=test_id,
                attempt_id=attempt_id,
            ),
        }
    )


# ---------------------------------------------------------------------------
# Exam interface and question/response APIs
# ---------------------------------------------------------------------------


@app.route("/test/<test_id>/attempt/<attempt_id>")
def exam_interface(test_id, attempt_id):
    test = storage.get_test(test_id)
    attempt = storage.get_attempt(attempt_id)

    if not test or not attempt:
        return "Test or Attempt not found", 404
    if attempt.student_id != session.get("student_id"):
        return "Access denied", 403
    if attempt.status != AttemptStatus.IN_PROGRESS.value:
        return redirect(url_for("test_listing"))

    if attempt_is_expired(attempt):
        attempt.status = AttemptStatus.EXPIRED.value
        attempt.submitted_at = datetime.now()
        storage.update_attempt(attempt)
        return redirect(url_for("test_listing"))

    remaining_seconds = max(
        0,
        int(
            (
                attempt.started_at
                + timedelta(minutes=test.duration_minutes)
                - datetime.now()
            ).total_seconds()
        ),
    )

    return render_template(
        "exam_interface.html",
        test=test,
        attempt=attempt,
        questions=storage.get_questions(test.questions),
        remaining_seconds=remaining_seconds,
    )


@app.route("/api/attempt/<attempt_id>/questions", methods=["GET"])
def get_attempt_questions(attempt_id):
    attempt, error = ensure_attempt_access(attempt_id)
    if error:
        return error

    test = storage.get_test(attempt.test_id)
    responses = storage.get_attempt_responses(attempt_id)
    response_map = {response.question_id: response for response in responses}
    question_data = []

    for question in storage.get_questions(test.questions):
        response = response_map.get(question.question_id)
        question_data.append(
            {
                "question_id": question.question_id,
                "question_type": question.question_type,
                "answer_mode": question.answer_mode,
                "question_content": [
                    {"type": block.type, "value": block.value}
                    for block in question.question_content
                ],
                "answer_choices": question.answer_choices,
                "marks": question.marks,
                "handwritten_upload_mode": question.handwritten_upload_mode,
                "requires_handwritten_upload": question.requires_handwritten_upload,
                "selected_answer": response.selected_answer if response else None,
                "answer_status": (
                    response.answer_status
                    if response
                    else AnswerStatus.UNANSWERED.value
                ),
            }
        )

    remaining_seconds = max(
        0,
        int(
            (
                attempt.started_at
                + timedelta(minutes=test.duration_minutes)
                - datetime.now()
            ).total_seconds()
        ),
    )

    return jsonify(
        {
            "questions": question_data,
            "remaining_seconds": remaining_seconds,
        }
    )


@app.route("/api/attempt/<attempt_id>/response", methods=["POST"])
def save_response(attempt_id):
    attempt, error = ensure_attempt_access(attempt_id)
    if error:
        return error

    data = request.get_json(silent=True) or {}
    question_id = data.get("question_id")
    selected_answer = data.get("selected_answer")
    test = storage.get_test(attempt.test_id)
    question = storage.get_question(question_id) if question_id else None

    if not question or question_id not in test.questions:
        return jsonify({"error": "Invalid question"}), 400

    if selected_answer not in {
        None,
        *[chr(65 + i) for i in range(len(question.answer_choices))],
    }:
        return jsonify({"error": "Invalid answer choice"}), 400

    existing = storage.get_response(attempt_id, question_id)
    status = (
        AnswerStatus.ANSWERED.value
        if selected_answer
        else AnswerStatus.UNANSWERED.value
    )

    if existing:
        existing.selected_answer = selected_answer
        existing.answer_status = status
        storage.update_response(existing)
    else:
        storage.create_response(
            Response(
                response_id=f"RESP{uuid.uuid4().hex[:12].upper()}",
                attempt_id=attempt_id,
                question_id=question_id,
                selected_answer=selected_answer,
                answer_status=status,
            )
        )

    return jsonify({"status": "saved"})


# ---------------------------------------------------------------------------
# Handwritten answer-image APIs
# ---------------------------------------------------------------------------


@app.route("/api/attempt/<attempt_id>/upload", methods=["POST"])
def upload_answer_image(attempt_id):
    attempt, error = ensure_attempt_access(attempt_id)
    if error:
        return error
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    question_id = request.form.get("question_id")

    if not file or not question_id:
        return jsonify({"error": "Missing file or question_id"}), 400

    test = storage.get_test(attempt.test_id)
    question = storage.get_question(question_id)

    if (
        not question
        or question_id not in test.questions
        or question.handwritten_upload_mode == "none"
    ):
        return jsonify(
            {"error": "Handwritten upload is not enabled for this question"}
        ), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Only JPG/JPEG/PNG allowed"}), 400

    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)

    if size > app.config["MAX_IMAGE_SIZE"]:
        return jsonify({"error": "Image exceeds the 10 MB per-file limit"}), 413

    try:
        image_check = Image.open(file)
        image_check.verify()
        file.seek(0)
    except Exception:
        return jsonify({"error": "Invalid image file"}), 400

    existing_images = storage.get_attempt_images(attempt_id, question_id)
    page_number = len(existing_images) + 1
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = (
        f"{attempt_id}_{question_id}_page_{page_number}_"
        f"{uuid.uuid4().hex[:8]}.{ext}"
    )
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    storage.create_image(
        AnswerImage(
            image_id=f"IMG{uuid.uuid4().hex[:12].upper()}",
            attempt_id=attempt_id,
            question_id=question_id,
            page_number=page_number,
            original_filename=secure_filename(file.filename),
            file_path=filepath,
            uploaded_at=datetime.now(),
        )
    )

    return jsonify(
        {
            "image_id": storage.get_attempt_images(attempt_id, question_id)[-1].image_id,
            "page_number": page_number,
            "filename": filename,
        }
    )


@app.route("/api/attempt/<attempt_id>/images/<question_id>", methods=["GET"])
def get_question_images(attempt_id, question_id):
    attempt, error = ensure_attempt_access(attempt_id)
    if error:
        return error

    return jsonify(
        [
            {
                "image_id": image.image_id,
                "page_number": image.page_number,
                "filename": image.original_filename,
                "url": f"/uploads/{Path(image.file_path).name}",
            }
            for image in storage.get_attempt_images(attempt_id, question_id)
        ]
    )


@app.route("/api/attempt/<attempt_id>/delete-image/<image_id>", methods=["DELETE"])
def delete_image(attempt_id, image_id):
    attempt, error = ensure_attempt_access(attempt_id)
    if error:
        return error

    image = next(
        (
            image
            for image in storage.images.values()
            if image.image_id == image_id and image.attempt_id == attempt_id
        ),
        None,
    )

    if not image:
        return jsonify({"error": "Image not found"}), 404

    if os.path.exists(image.file_path):
        os.remove(image.file_path)

    storage.delete_image(image_id)
    return jsonify({"status": "deleted"})


# ---------------------------------------------------------------------------
# Submission preview and final submission
# ---------------------------------------------------------------------------


@app.route("/api/attempt/<attempt_id>/submit-preview", methods=["GET"])
def get_submission_preview(attempt_id):
    attempt, error = ensure_attempt_access(attempt_id)
    if error:
        return error

    test = storage.get_test(attempt.test_id)
    questions = storage.get_questions(test.questions)
    responses = storage.get_attempt_responses(attempt_id)
    answered = sum(
        1
        for response in responses
        if response.answer_status == AnswerStatus.ANSWERED.value
    )
    required_uploads = []
    optional_uploads = 0

    for index, question in enumerate(questions, 1):
        images = storage.get_attempt_images(attempt_id, question.question_id)

        if question.handwritten_upload_mode == "required" and not images:
            required_uploads.append(index)
        elif question.handwritten_upload_mode == "optional" and images:
            optional_uploads += 1

    return jsonify(
        {
            "total_questions": len(questions),
            "answered": answered,
            "unanswered": len(questions) - answered,
            "required_uploads_missing": required_uploads,
            "required_uploads_complete": not required_uploads,
            "optional_uploads": optional_uploads,
        }
    )


@app.route("/api/attempt/<attempt_id>/submit", methods=["POST"])
def submit_attempt(attempt_id):
    attempt, error = ensure_attempt_access(attempt_id)
    if error:
        return error

    test = storage.get_test(attempt.test_id)
    questions = storage.get_questions(test.questions)
    missing = [
        index
        for index, question in enumerate(questions, 1)
        if question.handwritten_upload_mode == "required"
        and not storage.get_attempt_images(attempt_id, question.question_id)
    ]

    if missing:
        return jsonify(
            {
                "error": "Required handwritten work is missing",
                "missing_questions": missing,
            }
        ), 400

    submitted_at = datetime.now()
    finalization = storage.finalize_attempt(
        attempt_id,
        attempt.student_id,
        [question.question_id for question in questions],
        submitted_at,
    )
    if finalization == "not_found":
        return jsonify({"error": "Attempt not found"}), 404
    if finalization == "forbidden":
        return jsonify({"error": "You do not have access to this attempt"}), 403
    if finalization == "already_submitted":
        return jsonify({"error": "This assessment has already been submitted", "status": "submitted"}), 409
    if finalization != "submitted":
        return jsonify({"error": "Attempt cannot be submitted in its current state", "status": finalization}), 409

    return jsonify(
        {
            "status": "submitted",
            "submitted_at": submitted_at.isoformat(),
            "redirect_url": url_for(
                "submission_confirmation",
                attempt_id=attempt_id,
            ),
        }
    )


@app.route("/submission/<attempt_id>")
def submission_confirmation(attempt_id):
    attempt = storage.get_attempt(attempt_id)
    if not attempt:
        return "Attempt not found", 404
    if attempt.student_id != session.get("student_id"):
        return "Access denied", 403

    return render_template(
        "submission_confirmation.html",
        attempt=attempt,
        test=storage.get_test(attempt.test_id),
    )


# ---------------------------------------------------------------------------
# Uploaded-file serving and local development entry point
# ---------------------------------------------------------------------------


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
