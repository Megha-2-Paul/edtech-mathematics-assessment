"""Teacher evaluation workflow, diagnosis, and student result calculations."""
import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, session
from sqlalchemy import text
from database import engine
from .db_source import storage
from .diagnosis import diagnose_attempt
from .reporting import build_report

evaluation_bp = Blueprint("evaluation", __name__)
ERROR_CODES = [("C01", "Calculation"),("C02", "Conceptual"),("C03", "Formula"),("C04", "Sign"),("C05", "Incomplete steps"),("C06", "Wrong method"),("C07", "Missing justification"),("C08", "Misunderstood question"),("C09", "Time/attempt")]

def _attempt_or_404(attempt_id):
    attempt=storage.get_attempt(attempt_id)
    if not attempt: abort(404)
    return attempt

def _evaluation_errors(response_id):
    with engine.connect() as db:
        return db.execute(text("SELECT error_code, comment, marks_lost FROM evaluation_errors WHERE response_id=:id ORDER BY evaluation_error_id"),{"id":response_id}).mappings().all()

def _evaluate_attempt(attempt_id):
    attempt=_attempt_or_404(attempt_id); test=storage.get_test(attempt.test_id); questions=storage.get_questions(test.questions); responses=storage.get_attempt_responses(attempt_id)
    total=sum(float(q.marks) for q in questions); awarded=sum(float(r.marks_awarded or 0) for r in responses); attempted=sum(1 for r in responses if r.answer_status=="answered"); correct=sum(1 for r in responses if r.is_correct is True)
    attempt.score=round(awarded,2); attempt.percentage=round(awarded/total*100,2) if total else 0; attempt.attempt_rate=round(attempted/len(questions)*100,2) if questions else 0; attempt.accuracy=round(correct/attempted*100,2) if attempted else 0
    if attempt.submitted_at: attempt.time_taken_seconds=max(0,int((attempt.submitted_at-attempt.started_at).total_seconds()))
    return attempt

def _save_response_evaluation(response,question,marks,error_codes,comment):
    marks=max(0.0,min(float(marks),float(question.marks)))
    is_correct=(response.selected_answer==question.correct_answer) if question.question_type=="mcq" and response.selected_answer else (marks>=float(question.marks) if question.question_type!="mcq" else False)
    with engine.begin() as db:
        db.execute(text("UPDATE responses SET marks_awarded=:marks,is_correct=:correct WHERE response_id=:id"),{"marks":marks,"correct":is_correct,"id":response.response_id})
        db.execute(text("DELETE FROM evaluation_errors WHERE response_id=:id"),{"id":response.response_id})
        lost=max(0.0,float(question.marks)-marks)
        for code in error_codes:
            db.execute(text("INSERT INTO evaluation_errors(response_id,error_code,comment,marks_lost) VALUES(:response,:code,:comment,:lost)"),{"response":response.response_id,"code":code,"comment":comment or None,"lost":lost if len(error_codes)==1 else None})

def _update_question_history(attempt_id):
    attempt=storage.get_attempt(attempt_id); responses=storage.get_attempt_responses(attempt_id)
    with engine.begin() as db:
        for response in responses:
            errors=db.execute(text("SELECT error_code FROM evaluation_errors WHERE response_id=:id ORDER BY evaluation_error_id"),{"id":response.response_id}).scalars().all(); summary=", ".join(errors) if errors else None
            db.execute(text("""INSERT INTO question_history(student_id,question_id,attempt_count,correct_count,last_attempted_at,last_correct_at,last_marks_awarded,last_error_summary)
VALUES(:student,:question,1,:correct,:attempted,:correct_at,:marks,:summary)
ON DUPLICATE KEY UPDATE attempt_count=attempt_count+1,correct_count=correct_count+VALUES(correct_count),last_attempted_at=VALUES(last_attempted_at),last_correct_at=IF(VALUES(correct_count)=1,VALUES(last_correct_at),last_correct_at),last_marks_awarded=VALUES(last_marks_awarded),last_error_summary=VALUES(last_error_summary)"""),{"student":attempt.student_id,"question":response.question_id,"correct":1 if response.is_correct else 0,"attempted":attempt.submitted_at or datetime.now(),"correct_at":attempt.submitted_at if response.is_correct else None,"marks":response.marks_awarded,"summary":summary})

@evaluation_bp.route("/teacher/submissions")
def submissions():
    with engine.connect() as db:
        rows=db.execute(text("""SELECT a.attempt_id,a.student_id,a.test_id,a.started_at,a.submitted_at,a.status,a.score,a.percentage,t.title,s.name AS student_name FROM attempts a JOIN tests t ON t.test_id=a.test_id JOIN students s ON s.student_id=a.student_id WHERE a.status='submitted' ORDER BY COALESCE(a.submitted_at,a.started_at) DESC""")).mappings().all()
    return render_template("teacher_submissions.html",submissions=rows)

@evaluation_bp.route("/teacher/evaluate/<attempt_id>",methods=["GET","POST"])
def evaluate(attempt_id):
    attempt=_attempt_or_404(attempt_id); test=storage.get_test(attempt.test_id); questions=storage.get_questions(test.questions); responses={r.question_id:r for r in storage.get_attempt_responses(attempt_id)}
    if request.method=="POST":
        for q in questions:
            r=responses.get(q.question_id)
            if not r: continue
            if q.question_type=="mcq": marks=float(q.marks) if r.selected_answer==q.correct_answer else 0.0; codes=[]
            else: marks=request.form.get(f"marks_{q.question_id}","0") or "0"; codes=[c for c,_ in ERROR_CODES if c in request.form.getlist(f"errors_{q.question_id}")]
            _save_response_evaluation(r,q,marks,codes,request.form.get(f"comment_{q.question_id}","").strip())
        attempt=_evaluate_attempt(attempt_id); storage.update_attempt(attempt); _update_question_history(attempt_id); flash("Evaluation saved and result calculated.","success")
        return redirect(url_for("evaluation.evaluate",attempt_id=attempt_id))
    response_data=[]
    for q in questions:
        r=responses.get(q.question_id); images=storage.get_attempt_images(attempt_id,q.question_id) if r else []
        response_data.append({"question":q,"response":r,"errors":_evaluation_errors(r.response_id) if r else [],"images":[{"url":url_for("uploaded_file",filename=os.path.basename(image.file_path)),"page_number":image.page_number,"name":image.original_filename} for image in images]})
    return render_template("teacher_evaluation.html",attempt=attempt,test=test,response_data=response_data,error_codes=ERROR_CODES)

def _student_report(attempt_id):
    attempt=_attempt_or_404(attempt_id); test=storage.get_test(attempt.test_id); questions=storage.get_questions(test.questions); responses=storage.get_attempt_responses(attempt_id); student=storage.get_student(attempt.student_id)
    diagnosis=diagnose_attempt(attempt,test,questions,responses)
    return build_report(diagnosis,student,test,attempt)

@evaluation_bp.route("/result/<attempt_id>")
def student_result(attempt_id):
    attempt=_attempt_or_404(attempt_id)
    if attempt.student_id!=session.get("student_id"): return "Access denied",403
    if attempt.status!="submitted": return redirect(url_for("test_listing"))
    test=storage.get_test(attempt.test_id); questions=storage.get_questions(test.questions); responses=storage.get_attempt_responses(attempt_id); response_map={r.question_id:r for r in responses}; error_map={}
    with engine.connect() as db:
        rows=db.execute(text("SELECT r.question_id,e.error_code,e.comment FROM evaluation_errors e JOIN responses r ON r.response_id=e.response_id WHERE r.attempt_id=:attempt ORDER BY e.evaluation_error_id"),{"attempt":attempt_id}).mappings().all()
    for row in rows: error_map.setdefault(row["question_id"],[]).append(row)
    report=_student_report(attempt_id)
    diagnosis=report["diagnosis"]
    attempt.score=diagnosis["score"]; attempt.percentage=diagnosis["percentage"]; attempt.attempt_rate=diagnosis["attempt_rate"]
    return render_template("student_result.html",attempt=attempt,test=test,questions=questions,response_map=response_map,error_map=error_map,diagnosis=diagnosis,report=report)

@evaluation_bp.route("/report/<attempt_id>")
def student_report(attempt_id):
    attempt=_attempt_or_404(attempt_id)
    if attempt.student_id!=session.get("student_id"): return "Access denied",403
    if attempt.status!="submitted": return redirect(url_for("test_listing"))
    report=_student_report(attempt_id)
    if not report["diagnosis"]["evaluation_complete"]: return render_template("student_report.html",report=report,awaiting=True)
    return render_template("student_report.html",report=report,awaiting=False)

def register_evaluation(app): app.register_blueprint(evaluation_bp)
