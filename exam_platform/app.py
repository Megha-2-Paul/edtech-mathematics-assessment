import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import uuid
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.utils import secure_filename
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))

from exam_platform.models import Attempt, Response, AnswerImage, Student, AttemptStatus, AnswerStatus
from exam_platform.storage import storage
from exam_platform.mock_data import load_mock_data
from exam_platform.admin import register_admin
from question_bank.extraction.review_app import register_extraction_review

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['MAX_IMAGE_SIZE'] = 10 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = str(Path(__file__).parent.parent / "uploads")
Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
register_admin(app)
register_extraction_review(app)

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_or_create_student_id():
    student_id = session.get('student_id')
    if not student_id:
        student_id = f"STU{uuid.uuid4().hex[:8].upper()}"
        session['student_id'] = student_id
    return student_id

def ensure_student_record(student_id):
    if not storage.get_student(student_id):
        storage.create_student(Student(student_id=student_id,name="Guest Student",email="",registration_source="prototype"))

def attempt_is_expired(attempt):
    test = storage.get_test(attempt.test_id)
    if not test or attempt.status != AttemptStatus.IN_PROGRESS.value:
        return attempt.status == AttemptStatus.EXPIRED.value
    return datetime.now() >= attempt.started_at + timedelta(minutes=test.duration_minutes)

def ensure_attempt_access(attempt_id):
    attempt = storage.get_attempt(attempt_id)
    if not attempt: return None, (jsonify({"error":"Attempt not found"}),404)
    if attempt.student_id != session.get('student_id'): return None, (jsonify({"error":"You do not have access to this attempt"}),403)
    if attempt_is_expired(attempt):
        attempt.status=AttemptStatus.EXPIRED.value; attempt.submitted_at=attempt.submitted_at or datetime.now(); storage.update_attempt(attempt)
        return None, (jsonify({"error":"Time is up","status":"expired"}),410)
    return attempt,None

load_mock_data()

@app.route('/')
def index(): return redirect(url_for('test_listing'))

@app.route('/tests')
def test_listing():
    student_id=get_or_create_student_id(); tests=list(storage.tests.values()); test_status={}
    for test in tests:
        attempt=storage.get_student_test_attempt(student_id,test.test_id)
        if attempt and attempt.status==AttemptStatus.SUBMITTED.value: test_status[test.test_id]='taken'
        elif attempt and attempt.status==AttemptStatus.EXPIRED.value: test_status[test.test_id]='expired'
        elif attempt and attempt.status==AttemptStatus.IN_PROGRESS.value:
            if attempt_is_expired(attempt): attempt.status=AttemptStatus.EXPIRED.value; attempt.submitted_at=datetime.now(); storage.update_attempt(attempt); test_status[test.test_id]='expired'
            else: test_status[test.test_id]='in_progress'
        else: test_status[test.test_id]='available'
    return render_template('test_listing.html',tests=tests,test_status=test_status)

@app.route('/test/<test_id>/instructions')
def test_instructions(test_id):
    test=storage.get_test(test_id)
    if not test: return "Test not found",404
    student_id=get_or_create_student_id(); existing=storage.get_student_test_attempt(student_id,test_id)
    if existing and existing.status==AttemptStatus.SUBMITTED.value: return redirect(url_for('test_listing'))
    if existing and existing.status==AttemptStatus.IN_PROGRESS.value and not attempt_is_expired(existing): return redirect(url_for('exam_interface',test_id=test_id,attempt_id=existing.attempt_id))
    return render_template('test_instructions.html',test=test,total_questions=len(storage.get_questions(test.questions)))

@app.route('/api/test/<test_id>/start',methods=['POST'])
def start_test(test_id):
    test=storage.get_test(test_id)
    if not test: return jsonify({"error":"Test not found"}),404
    student_id=get_or_create_student_id(); ensure_student_record(student_id); existing=storage.get_student_test_attempt(student_id,test_id)
    if existing:
        if existing.status==AttemptStatus.SUBMITTED.value: return jsonify({"error":"Test already taken","status":"taken"}),409
        if existing.status==AttemptStatus.IN_PROGRESS.value and not attempt_is_expired(existing): session['attempt_id']=existing.attempt_id; return jsonify({"attempt_id":existing.attempt_id,"student_id":student_id,"resumed":True,"redirect_url":url_for('exam_interface',test_id=test_id,attempt_id=existing.attempt_id)})
        if existing.status==AttemptStatus.EXPIRED.value or attempt_is_expired(existing): return jsonify({"error":"Test time has expired","status":"expired"}),410
    attempt_id=f"ATT{uuid.uuid4().hex[:12].upper()}"; storage.create_attempt(Attempt(attempt_id=attempt_id,student_id=student_id,test_id=test_id,started_at=datetime.now())); session['attempt_id']=attempt_id
    return jsonify({"attempt_id":attempt_id,"student_id":student_id,"resumed":False,"redirect_url":url_for('exam_interface',test_id=test_id,attempt_id=attempt_id)})

@app.route('/test/<test_id>/attempt/<attempt_id>')
def exam_interface(test_id,attempt_id):
    test=storage.get_test(test_id); attempt=storage.get_attempt(attempt_id)
    if not test or not attempt: return "Test or Attempt not found",404
    if attempt.student_id!=session.get('student_id'): return "Access denied",403
    if attempt.status!=AttemptStatus.IN_PROGRESS.value: return redirect(url_for('test_listing'))
    if attempt_is_expired(attempt): attempt.status=AttemptStatus.EXPIRED.value; attempt.submitted_at=datetime.now(); storage.update_attempt(attempt); return redirect(url_for('test_listing'))
    remaining_seconds=max(0,int((attempt.started_at+timedelta(minutes=test.duration_minutes)-datetime.now()).total_seconds()))
    return render_template('exam_interface.html',test=test,attempt=attempt,questions=storage.get_questions(test.questions),remaining_seconds=remaining_seconds)

@app.route('/api/attempt/<attempt_id>/questions',methods=['GET'])
def get_attempt_questions(attempt_id):
    attempt,error=ensure_attempt_access(attempt_id)
    if error: return error
    test=storage.get_test(attempt.test_id); responses=storage.get_attempt_responses(attempt_id); response_map={r.question_id:r for r in responses}; question_data=[]
    for q in storage.get_questions(test.questions):
        resp=response_map.get(q.question_id)
        question_data.append({"question_id":q.question_id,"question_type":q.question_type,"answer_mode":q.answer_mode,"question_content":[{"type":c.type,"value":c.value} for c in q.question_content],"answer_choices":q.answer_choices,"marks":q.marks,"handwritten_upload_mode":q.handwritten_upload_mode,"requires_handwritten_upload":q.requires_handwritten_upload,"selected_answer":resp.selected_answer if resp else None,"answer_status":resp.answer_status if resp else AnswerStatus.UNANSWERED.value})
    remaining_seconds=max(0,int((attempt.started_at+timedelta(minutes=test.duration_minutes)-datetime.now()).total_seconds()))
    return jsonify({"questions":question_data,"remaining_seconds":remaining_seconds})

@app.route('/api/attempt/<attempt_id>/response',methods=['POST'])
def save_response(attempt_id):
    attempt,error=ensure_attempt_access(attempt_id)
    if error: return error
    data=request.get_json(silent=True) or {}; question_id=data.get('question_id'); selected_answer=data.get('selected_answer'); test=storage.get_test(attempt.test_id); question=storage.get_question(question_id) if question_id else None
    if not question or question_id not in test.questions: return jsonify({"error":"Invalid question"}),400
    if selected_answer not in {None,*[chr(65+i) for i in range(len(question.answer_choices))]}: return jsonify({"error":"Invalid answer choice"}),400
    existing=storage.get_response(attempt_id,question_id); status=AnswerStatus.ANSWERED.value if selected_answer else AnswerStatus.UNANSWERED.value
    if existing: existing.selected_answer=selected_answer; existing.answer_status=status; storage.update_response(existing)
    else: storage.create_response(Response(response_id=f"RESP{uuid.uuid4().hex[:12].upper()}",attempt_id=attempt_id,question_id=question_id,selected_answer=selected_answer,answer_status=status))
    return jsonify({"status":"saved"})

@app.route('/api/attempt/<attempt_id>/upload',methods=['POST'])
def upload_answer_image(attempt_id):
    attempt,error=ensure_attempt_access(attempt_id)
    if error: return error
    if 'file' not in request.files: return jsonify({"error":"No file provided"}),400
    file=request.files['file']; question_id=request.form.get('question_id')
    if not file or not question_id: return jsonify({"error":"Missing file or question_id"}),400
    test=storage.get_test(attempt.test_id); question=storage.get_question(question_id)
    if not question or question_id not in test.questions or question.handwritten_upload_mode=='none': return jsonify({"error":"Handwritten upload is not enabled for this question"}),400
    if not allowed_file(file.filename): return jsonify({"error":"Only JPG/JPEG/PNG allowed"}),400
    file.seek(0,os.SEEK_END); size=file.tell(); file.seek(0)
    if size>app.config['MAX_IMAGE_SIZE']: return jsonify({"error":"Image exceeds the 10 MB per-file limit"}),413
    try: image_check=Image.open(file); image_check.verify(); file.seek(0)
    except Exception: return jsonify({"error":"Invalid image file"}),400
    existing_images=storage.get_attempt_images(attempt_id,question_id); page_number=len(existing_images)+1; ext=file.filename.rsplit('.',1)[1].lower(); filename=f"{attempt_id}_{question_id}_page_{page_number}_{uuid.uuid4().hex[:8]}.{ext}"; filepath=os.path.join(app.config['UPLOAD_FOLDER'],filename); file.save(filepath)
    storage.create_image(AnswerImage(image_id=f"IMG{uuid.uuid4().hex[:12].upper()}",attempt_id=attempt_id,question_id=question_id,page_number=page_number,original_filename=secure_filename(file.filename),file_path=filepath,uploaded_at=datetime.now()))
    return jsonify({"image_id":storage.get_attempt_images(attempt_id,question_id)[-1].image_id,"page_number":page_number,"filename":filename})

@app.route('/api/attempt/<attempt_id>/images/<question_id>',methods=['GET'])
def get_question_images(attempt_id,question_id):
    attempt,error=ensure_attempt_access(attempt_id)
    if error: return error
    return jsonify([{"image_id":img.image_id,"page_number":img.page_number,"filename":img.original_filename,"url":f"/uploads/{Path(img.file_path).name}"} for img in storage.get_attempt_images(attempt_id,question_id)])

@app.route('/api/attempt/<attempt_id>/delete-image/<image_id>',methods=['DELETE'])
def delete_image(attempt_id,image_id):
    attempt,error=ensure_attempt_access(attempt_id)
    if error: return error
    image=next((img for img in storage.images.values() if img.image_id==image_id and img.attempt_id==attempt_id),None)
    if not image: return jsonify({"error":"Image not found"}),404
    if os.path.exists(image.file_path): os.remove(image.file_path)
    storage.delete_image(image_id); return jsonify({"status":"deleted"})

@app.route('/api/attempt/<attempt_id>/submit-preview',methods=['GET'])
def get_submission_preview(attempt_id):
    attempt,error=ensure_attempt_access(attempt_id)
    if error: return error
    test=storage.get_test(attempt.test_id); questions=storage.get_questions(test.questions); responses=storage.get_attempt_responses(attempt_id); answered=sum(1 for r in responses if r.answer_status==AnswerStatus.ANSWERED.value); required_uploads=[]; optional_uploads=0
    for index,q in enumerate(questions,1):
        images=storage.get_attempt_images(attempt_id,q.question_id)
        if q.handwritten_upload_mode=='required' and not images: required_uploads.append(index)
        elif q.handwritten_upload_mode=='optional' and images: optional_uploads+=1
    return jsonify({"total_questions":len(questions),"answered":answered,"unanswered":len(questions)-answered,"required_uploads_missing":required_uploads,"required_uploads_complete":not required_uploads,"optional_uploads":optional_uploads})

@app.route('/api/attempt/<attempt_id>/submit',methods=['POST'])
def submit_attempt(attempt_id):
    attempt,error=ensure_attempt_access(attempt_id)
    if error: return error
    test=storage.get_test(attempt.test_id); questions=storage.get_questions(test.questions); missing=[i for i,q in enumerate(questions,1) if q.handwritten_upload_mode=='required' and not storage.get_attempt_images(attempt_id,q.question_id)]
    if missing: return jsonify({"error":"Required handwritten work is missing","missing_questions":missing}),400
    attempt.submitted_at=datetime.now(); attempt.status=AttemptStatus.SUBMITTED.value; storage.update_attempt(attempt)
    return jsonify({"status":"submitted","submitted_at":attempt.submitted_at.isoformat(),"redirect_url":url_for('submission_confirmation',attempt_id=attempt_id)})

@app.route('/submission/<attempt_id>')
def submission_confirmation(attempt_id):
    attempt=storage.get_attempt(attempt_id)
    if not attempt: return "Attempt not found",404
    if attempt.student_id!=session.get('student_id'): return "Access denied",403
    return render_template('submission_confirmation.html',attempt=attempt,test=storage.get_test(attempt.test_id))

@app.route('/uploads/<path:filename>')
def uploaded_file(filename): return app.send_from_directory(app.config['UPLOAD_FOLDER'],filename)

if __name__=='__main__': app.run(debug=True,port=5000)
