"""Deployment adapter for the temporary zero-cost hosted test environment.

The local Flask application remains unchanged. This module adds only deployment
concerns: a Render-safe secret, temporary teacher protection, and cloud-backed
handwritten answer images when CLOUDINARY_URL is configured.
"""

import hmac
import os
from datetime import datetime
from pathlib import Path
import uuid

from flask import Response, jsonify, request, send_from_directory, url_for
from PIL import Image
from werkzeug.utils import secure_filename

from exam_platform.app import app, ensure_attempt_access
from exam_platform.db_source import storage
from exam_platform.media import delete_image as delete_stored_image
from exam_platform.media import store_image
from exam_platform.models import AnswerImage


# ---------------------------------------------------------------------------
# Deployment-only application settings
# ---------------------------------------------------------------------------

secret_key = os.getenv("SECRET_KEY")
if os.getenv("RENDER") and not secret_key:
    raise RuntimeError("SECRET_KEY must be configured on the hosted service.")
if secret_key:
    app.secret_key = secret_key


@app.before_request
def protect_teacher_routes():
    """Use temporary HTTP Basic Auth for every teacher-side route."""
    if not request.path.startswith("/teacher"):
        return None

    password = os.getenv("TEACHER_ACCESS_PASSWORD")
    username = os.getenv("TEACHER_ACCESS_USERNAME", "teacher")

    if not password:
        if os.getenv("RENDER"):
            return Response("Teacher access is not configured.", status=503)
        return None

    auth = request.authorization
    if (
        not auth
        or not hmac.compare_digest(auth.username or "", username)
        or not hmac.compare_digest(auth.password or "", password)
    ):
        return Response(
            "Teacher access required.",
            status=401,
            headers={"WWW-Authenticate": 'Basic realm="Improvia Teacher"'},
        )

    return None


# ---------------------------------------------------------------------------
# Deployment-safe answer-image handlers
# ---------------------------------------------------------------------------


def _cloud_answer_filename(filename):
    """Map an answer-image filename to the Cloudinary public-id convention."""
    return f"improvia/answers/{Path(filename).stem}"


def hosted_uploaded_file(filename):
    """Serve public question assets, never raw student answer-image URLs."""
    requested_stem = Path(filename).stem
    for image in storage.images.values():
        stored_path = str(image.file_path or "")
        stored_name = Path(stored_path).name
        if filename == stored_name or requested_stem == stored_name:
            return Response(
                "Answer images must be accessed through an authenticated assessment route.",
                status=403,
            )

    local_path = Path(app.config["UPLOAD_FOLDER"]) / filename
    if local_path.exists():
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    return "File not found", 404


def hosted_upload_answer_image(attempt_id):
    """Store handwritten answers using persistent cloud media when configured."""
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
        return jsonify({"error": "Handwritten upload is not enabled for this question"}), 400

    allowed_extensions = {"jpg", "jpeg", "png"}
    if "." not in file.filename or file.filename.rsplit(".", 1)[1].lower() not in allowed_extensions:
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
    filename = (
        f"{attempt_id}_{question_id}_page_{page_number}_"
        f"{uuid.uuid4().hex[:8]}.{file.filename.rsplit('.', 1)[1].lower()}"
    )

    file_path = store_image(file, filename)
    image = AnswerImage(
        image_id=f"IMG{uuid.uuid4().hex[:12].upper()}",
        attempt_id=attempt_id,
        question_id=question_id,
        page_number=page_number,
        original_filename=secure_filename(file.filename),
        file_path=file_path,
        uploaded_at=datetime.now(),
    )
    try:
        storage.create_image(image)
    except Exception:
        # Avoid orphaned files when persistent metadata cannot be written.
        try:
            delete_stored_image(file_path)
        except Exception:
            app.logger.exception("Failed to clean up answer image after metadata write failure")
        raise

    return jsonify(
        {
            "image_id": image.image_id,
            "page_number": page_number,
            "filename": filename,
        }
    )


def hosted_get_question_images(attempt_id, question_id):
    attempt, error = ensure_attempt_access(attempt_id)
    if error:
        return error

    result = []
    for image in storage.get_attempt_images(attempt_id, question_id):
        result.append(
            {
                "image_id": image.image_id,
                "page_number": image.page_number,
                "filename": image.original_filename,
                "url": url_for(
                    "student_answer_image",
                    attempt_id=attempt_id,
                    image_id=image.image_id,
                ),
            }
        )
    return jsonify(result)


def hosted_delete_image(attempt_id, image_id):
    attempt, error = ensure_attempt_access(attempt_id)
    if error:
        return error

    image = next(
        (
            item
            for item in storage.images.values()
            if item.image_id == image_id and item.attempt_id == attempt_id
        ),
        None,
    )
    if not image:
        return jsonify({"error": "Image not found"}), 404

    delete_stored_image(image.file_path)
    storage.delete_image(image_id)
    return jsonify({"status": "deleted"})


# Replace only the deployment-sensitive view functions. The local app's routes,
# timers, evaluation, diagnosis, and reports remain untouched.
app.view_functions["uploaded_file"] = hosted_uploaded_file
app.view_functions["upload_answer_image"] = hosted_upload_answer_image
app.view_functions["get_question_images"] = hosted_get_question_images
app.view_functions["delete_image"] = hosted_delete_image

application = app
