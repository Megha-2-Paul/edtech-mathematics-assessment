import os
import sys
from pathlib import Path
from datetime import datetime
import uuid
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.utils import secure_filename
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from exam_platform.models import (
    Test, Question, Student, Attempt, Response, AnswerImage,
    AttemptStatus, AnswerStatus, ContentBlock
)
from exam_platform.storage import storage
from exam_platform.mock_data import load_mock_data

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload
app.config['UPLOAD_FOLDER'] = str(Path(__file__).parent.parent / "uploads")

# Create upload directory
Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Load mock data on startup
load_mock_data()


@app.route('/')
def index():
    """Homepage - redirect to test listing"""
    return redirect(url_for('test_listing'))


@app.route('/tests')
def test_listing():
    """List available tests"""
    tests = list(storage.tests.values())
    return render_template('test_listing.html', tests=tests)


@app.route('/test/<test_id>/instructions')
def test_instructions(test_id):
    """Show test instructions before starting"""
    test = storage.get_test(test_id)
    if not test:
        return "Test not found", 404
    
    questions = storage.get_questions(test.questions)
    total_questions = len(questions)
    
    return render_template('test_instructions.html', test=test, total_questions=total_questions)


@app.route('/api/test/<test_id>/start', methods=['POST'])
def start_test(test_id):
    """Start a test and create an attempt"""
    test = storage.get_test(test_id)
    if not test:
        return jsonify({"error": "Test not found"}), 404
    
    # Create a new attempt
    attempt_id = f"ATT{uuid.uuid4().hex[:12].upper()}"
    student_id = session.get('student_id', f"STU{uuid.uuid4().hex[:8].upper()}")
    
    attempt = Attempt(
        attempt_id=attempt_id,
        student_id=student_id,
        test_id=test_id,
        started_at=datetime.now(),
        status=AttemptStatus.IN_PROGRESS.value
    )
    
    storage.create_attempt(attempt)
    session['student_id'] = student_id
    session['attempt_id'] = attempt_id
    
    return jsonify({
        "attempt_id": attempt_id,
        "student_id": student_id,
        "redirect_url": url_for('exam_interface', test_id=test_id, attempt_id=attempt_id)
    })


@app.route('/test/<test_id>/attempt/<attempt_id>')
def exam_interface(test_id, attempt_id):
    """Main exam interface"""
    test = storage.get_test(test_id)
    attempt = storage.get_attempt(attempt_id)
    
    if not test or not attempt:
        return "Test or Attempt not found", 404
    
    if attempt.status != AttemptStatus.IN_PROGRESS.value:
        return "Attempt is not in progress", 400
    
    questions = storage.get_questions(test.questions)
    
    return render_template('exam_interface.html', 
                         test=test, 
                         attempt=attempt,
                         questions=questions)


@app.route('/api/attempt/<attempt_id>/questions', methods=['GET'])
def get_attempt_questions(attempt_id):
    """Get all questions for an attempt with current responses"""
    attempt = storage.get_attempt(attempt_id)
    if not attempt:
        return jsonify({"error": "Attempt not found"}), 404
    
    test = storage.get_test(attempt.test_id)
    questions = storage.get_questions(test.questions)
    
    question_data = []
    responses = storage.get_attempt_responses(attempt_id)
    response_map = {r.question_id: r for r in responses}
    
    for q in questions:
        resp = response_map.get(q.question_id)
        question_data.append({
            "question_id": q.question_id,
            "question_type": q.question_type,
            "answer_mode": q.answer_mode,
            "question_content": [
                {
                    "type": c.type,
                    "value": c.value,
                }
                for c in q.question_content
            ],
            "answer_choices": q.answer_choices,
            "marks": q.marks,
            "requires_handwritten_upload": q.requires_handwritten_upload,
            "selected_answer": resp.selected_answer if resp else None,
            "answer_status": resp.answer_status if resp else AnswerStatus.UNANSWERED.value,
        })
    
    return jsonify(question_data)


@app.route('/api/attempt/<attempt_id>/response', methods=['POST'])
def save_response(attempt_id):
    """Save a response for a question"""
    attempt = storage.get_attempt(attempt_id)
    if not attempt:
        return jsonify({"error": "Attempt not found"}), 404
    
    data = request.get_json()
    question_id = data.get('question_id')
    selected_answer = data.get('selected_answer')
    
    if not question_id:
        return jsonify({"error": "Missing question_id"}), 400
    
    # Check if response already exists
    existing = storage.get_response(attempt_id, question_id)
    
    if existing:
        existing.selected_answer = selected_answer
        existing.answer_status = AnswerStatus.ANSWERED.value if selected_answer else AnswerStatus.UNANSWERED.value
        storage.update_response(existing)
    else:
        response = Response(
            response_id=f"RESP{uuid.uuid4().hex[:12].upper()}",
            attempt_id=attempt_id,
            question_id=question_id,
            selected_answer=selected_answer,
            answer_status=AnswerStatus.ANSWERED.value if selected_answer else AnswerStatus.UNANSWERED.value
        )
        storage.create_response(response)
    
    return jsonify({"status": "saved"})


@app.route('/api/attempt/<attempt_id>/upload', methods=['POST'])
def upload_answer_image(attempt_id):
    """Upload handwritten answer image"""
    attempt = storage.get_attempt(attempt_id)
    if not attempt:
        return jsonify({"error": "Attempt not found"}), 404
    
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    question_id = request.form.get('question_id')
    page_number = int(request.form.get('page_number', 1))
    
    if not file or not question_id:
        return jsonify({"error": "Missing file or question_id"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"error": "Only JPG/JPEG/PNG allowed"}), 400
    
    # Generate safe filename
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{attempt_id}_{question_id}_page_{page_number}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    file.save(filepath)
    
    # Create AnswerImage record
    image = AnswerImage(
        image_id=f"IMG{uuid.uuid4().hex[:12].upper()}",
        attempt_id=attempt_id,
        question_id=question_id,
        page_number=page_number,
        original_filename=secure_filename(file.filename),
        file_path=filepath,
        uploaded_at=datetime.now()
    )
    storage.create_image(image)
    
    return jsonify({
        "image_id": image.image_id,
        "page_number": page_number,
        "filename": filename
    })


@app.route('/api/attempt/<attempt_id>/images/<question_id>', methods=['GET'])
def get_question_images(attempt_id, question_id):
    """Get uploaded images for a question"""
    images = storage.get_attempt_images(attempt_id, question_id)
    return jsonify([{
        "image_id": img.image_id,
        "page_number": img.page_number,
        "filename": img.original_filename,
        "url": f"/uploads/{Path(img.file_path).name}"
    } for img in images])


@app.route('/api/attempt/<attempt_id>/delete-image/<image_id>', methods=['DELETE'])
def delete_image(attempt_id, image_id):
    """Delete an uploaded image"""
    image = None
    for img in storage.images.values():
        if img.image_id == image_id and img.attempt_id == attempt_id:
            image = img
            break
    
    if not image:
        return jsonify({"error": "Image not found"}), 404
    
    # Delete file
    if os.path.exists(image.file_path):
        os.remove(image.file_path)
    
    # Remove from storage
    del storage.images[image_id]
    
    return jsonify({"status": "deleted"})


@app.route('/api/attempt/<attempt_id>/submit-preview', methods=['GET'])
def get_submission_preview(attempt_id):
    """Get preview data for submission confirmation"""
    attempt = storage.get_attempt(attempt_id)
    if not attempt:
        return jsonify({"error": "Attempt not found"}), 404
    
    test = storage.get_test(attempt.test_id)
    questions = storage.get_questions(test.questions)
    responses = storage.get_attempt_responses(attempt_id)
    
    response_map = {r.question_id: r for r in responses}
    
    total_questions = len(questions)
    answered = sum(1 for r in responses if r.answer_status == AnswerStatus.ANSWERED.value)
    unanswered = total_questions - answered
    
    # Check subjective questions with/without uploads
    subjective_with_upload = 0
    subjective_without_upload = 0
    
    for q in questions:
        if q.question_type == "subjective":
            images = storage.get_attempt_images(attempt_id, q.question_id)
            if images:
                subjective_with_upload += 1
            else:
                subjective_without_upload += 1
    
    return jsonify({
        "total_questions": total_questions,
        "answered": answered,
        "unanswered": unanswered,
        "subjective_with_upload": subjective_with_upload,
        "subjective_without_upload": subjective_without_upload,
    })


@app.route('/api/attempt/<attempt_id>/submit', methods=['POST'])
def submit_attempt(attempt_id):
    """Submit the test"""
    attempt = storage.get_attempt(attempt_id)
    if not attempt:
        return jsonify({"error": "Attempt not found"}), 404
    
    if attempt.status != AttemptStatus.IN_PROGRESS.value:
        return jsonify({"error": "Attempt already submitted"}), 400
    
    attempt.submitted_at = datetime.now()
    attempt.status = AttemptStatus.SUBMITTED.value
    storage.update_attempt(attempt)
    
    return jsonify({
        "status": "submitted",
        "submitted_at": attempt.submitted_at.isoformat(),
        "redirect_url": url_for('submission_confirmation', attempt_id=attempt_id)
    })


@app.route('/submission/<attempt_id>')
def submission_confirmation(attempt_id):
    """Show submission confirmation"""
    attempt = storage.get_attempt(attempt_id)
    if not attempt:
        return "Attempt not found", 404
    
    test = storage.get_test(attempt.test_id)
    
    return render_template('submission_confirmation.html', attempt=attempt, test=test)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return app.send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
