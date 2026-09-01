"""Functional teacher/admin interface for managing the assessment question bank."""
import shutil
import uuid
from copy import deepcopy
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename

from .models import Question, Test, ContentBlock
from .storage import storage

admin_bp = Blueprint("admin", __name__, url_prefix="/teacher")
QUESTION_ASSET_DIR = Path(__file__).parent.parent / "uploads" / "question_assets"
QUESTION_ASSET_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
SUBJECTS = ["Mathematics", "Physics", "Chemistry", "Computer"]
BOARDS = ["CBSE", "ICSE"]
QUESTION_TYPES = [("mcq", "MCQ"), ("vsaq", "VSAQ"), ("saq", "SAQ"), ("laq", "LAQ")]
DIFFICULTIES = ["Easy", "Moderate", "Difficult"]


def _next_question_id():
    numbers=[int(qid[1:]) for qid in storage.questions if qid.startswith("Q") and qid[1:].isdigit()]
    return f"Q{max(numbers,default=0)+1:04d}"

def _next_test_id():
    numbers=[int(tid[4:]) for tid in storage.tests if tid.startswith("TEST") and tid[4:].isdigit()]
    return f"TEST{max(numbers,default=0)+1:03d}"

def _form_value(name,default=""): return request.form.get(name,default).strip()

def _save_uploaded_question_image(question_id):
    file=request.files.get("question_image")
    if not file or not file.filename: return None
    ext=Path(file.filename).suffix.lower().lstrip(".")
    if ext not in ALLOWED_IMAGE_EXTENSIONS: raise ValueError("Question image must be JPG, JPEG, PNG or WEBP.")
    filename=f"{question_id}_{uuid.uuid4().hex[:10]}.{ext}"; path=QUESTION_ASSET_DIR/filename; path.parent.mkdir(parents=True,exist_ok=True); file.save(path)
    asset_id=f"QASSET{uuid.uuid4().hex[:12].upper()}"
    return asset_id,f"/uploads/question_assets/{filename}",str(path),secure_filename(file.filename)

def _copy_question_assets(source,new_question_id):
    blocks=[]
    for block in source.question_content:
        block=deepcopy(block)
        if block.type=="image" and block.metadata.get("local_asset_path"):
            old_path=Path(block.metadata["local_asset_path"])
            if old_path.exists():
                new_path=QUESTION_ASSET_DIR/f"{new_question_id}_{uuid.uuid4().hex[:10]}{old_path.suffix.lower()}"; shutil.copy2(old_path,new_path)
                block.asset_id=f"QASSET{uuid.uuid4().hex[:12].upper()}"; block.value=f"/uploads/question_assets/{new_path.name}"; block.metadata["local_asset_path"]=str(new_path)
        blocks.append(block)
    return blocks

def _persist_question_assets(q):
    for block in q.question_content:
        if block.type=="image" and block.asset_id and block.metadata.get("local_asset_path"):
            storage.create_question_asset(block.asset_id,q.question_id,"image",Path(block.metadata["local_asset_path"]).name,block.metadata["local_asset_path"])

def _question_from_form(question_id,existing=None,preserve_images=True):
    question_type=_form_value("question_type","mcq").lower()
    if question_type not in {x[0] for x in QUESTION_TYPES}: question_type="mcq"
    answer_mode="option_selection" if question_type=="mcq" else "final_answer_selection_and_handwritten_upload"
    choices=[_form_value(f"choice_{letter}") for letter in "ABCD"]; choices=[c for c in choices if c]
    correct=_form_value("correct_answer").upper() or None; content=[ContentBlock("text",_form_value("question_text"))]
    if preserve_images and existing and not any(v=="1" for v in request.form.getlist("remove_existing_image")):
        content.extend(deepcopy([c for c in existing.question_content if c.type=="image"]))
    source_year=_form_value("source_year")
    return Question(question_id=question_id,question_type=question_type,answer_mode=answer_mode,question_content=content,answer_choices=choices,correct_answer=correct,marks=float(request.form.get("marks","1") or 1),handwritten_upload_mode=_form_value("handwritten_upload_mode","none"),subject=_form_value("subject","Mathematics") or "Mathematics",board=_form_value("board") or None,class_level=int(request.form["class_level"]) if request.form.get("class_level") else None,chapter=_form_value("chapter") or None,topic=_form_value("topic") or None,subtopic=_form_value("subtopic") or None,difficulty=_form_value("difficulty") or None,competency=_form_value("competency") or None,source=_form_value("source") or None,source_year=int(source_year) if source_year.isdigit() else None,status=_form_value("status","active") or "active")

def _form_context(question=None,is_edit=False):
    subject=question.subject if question else "Mathematics"; board=question.board if question else "CBSE"; class_level=question.class_level if question else 10
    return {"question":question,"is_edit":is_edit,"subjects":storage.get_subjects(),"boards":BOARDS,"question_types":QUESTION_TYPES,"difficulties":DIFFICULTIES,"chapters":storage.get_chapters(board,class_level,subject),"competencies":storage.get_competencies(subject)}

def _validate_question(q):
    if not q.question_content or not q.question_content[0].value: return "Question text is required."
    if not q.answer_choices or not q.correct_answer or q.correct_answer not in {chr(65+i) for i in range(len(q.answer_choices))}: return "Add answer choices and select a valid correct answer."
    if not q.subject or not q.class_level or not q.board or not q.chapter: return "Subject, board, class and chapter are required."
    return None

@admin_bp.route("/")
def dashboard(): return render_template("teacher_dashboard.html",questions=list(storage.questions.values()),tests=list(storage.tests.values()))

@admin_bp.route("/api/chapters")
def api_chapters():
    return jsonify([dict(x) for x in storage.get_chapters(request.args.get("board","CBSE"),int(request.args.get("class_level","10")),request.args.get("subject","Mathematics"))])

@admin_bp.route("/api/competencies")
def api_competencies(): return jsonify([dict(x) for x in storage.get_competencies(request.args.get("subject","Mathematics"))])

@admin_bp.route("/questions")
def questions():
    query=request.args.get("q","").strip().lower(); question_type=request.args.get("type","").strip(); board=request.args.get("board","").strip(); class_level=request.args.get("class_level","").strip(); subject=request.args.get("subject","").strip(); chapter=request.args.get("chapter","").strip(); difficulty=request.args.get("difficulty","").strip(); competency=request.args.get("competency","").strip(); status=request.args.get("status","active").strip(); items=list(storage.questions.values())
    if query: items=[q for q in items if query in q.question_id.lower() or query in (q.chapter or "").lower() or query in (q.topic or "").lower() or query in str(q.question_content[0].value).lower()]
    if question_type: items=[q for q in items if q.question_type==question_type]
    if board: items=[q for q in items if (q.board or "")==board]
    if class_level: items=[q for q in items if str(q.class_level or "")==class_level]
    if subject: items=[q for q in items if q.subject==subject]
    if chapter: items=[q for q in items if (q.chapter or "")==chapter]
    if difficulty: items=[q for q in items if (q.difficulty or "")==difficulty]
    if competency: items=[q for q in items if (q.competency or "")==competency]
    if status!="all": items=[q for q in items if q.status==status]
    return render_template("teacher_questions.html",questions=items,query=query,question_type=question_type,board=board,class_level=class_level,subject=subject,chapter=chapter,difficulty=difficulty,competency=competency,status=status,subjects=SUBJECTS,boards=BOARDS,difficulties=DIFFICULTIES)

@admin_bp.route("/questions/new",methods=["GET","POST"])
def add_question():
    clone_id=request.args.get("clone_from"); source=storage.get_question(clone_id) if clone_id else None
    if request.method=="POST":
        question_id=_next_question_id(); q=_question_from_form(question_id,source,preserve_images=False)
        try:
            if source: q.question_content=[q.question_content[0]]+_copy_question_assets(source,question_id)
            uploaded=_save_uploaded_question_image(question_id)
            if uploaded:
                asset_id,url,path,original=uploaded; q.question_content.append(ContentBlock("image",url,asset_id=asset_id,metadata={"local_asset_path":path,"original_filename":original}))
            error=_validate_question(q)
            if error: flash(error,"error"); return render_template("teacher_question_form.html",**_form_context(q,False))
            storage.create_question(q); _persist_question_assets(q); flash(f"Question {question_id} saved.","success"); return redirect(url_for("admin.questions"))
        except ValueError as exc:
            flash(str(exc),"error"); return render_template("teacher_question_form.html",**_form_context(q,False))
    if source: source=deepcopy(source); source.question_id="NEW"
    return render_template("teacher_question_form.html",**_form_context(source,False))

@admin_bp.route("/questions/<question_id>/edit",methods=["GET","POST"])
def edit_question(question_id):
    q=storage.get_question(question_id)
    if not q: return "Question not found",404
    if request.method=="POST":
        save_as_new=request.form.get("save_as_new")=="1"; new_id=_next_question_id() if save_as_new else question_id; updated=_question_from_form(new_id,q,preserve_images=not save_as_new)
        try:
            if save_as_new: updated.question_content=[updated.question_content[0]]+_copy_question_assets(q,new_id)
            uploaded=_save_uploaded_question_image(new_id)
            if uploaded:
                asset_id,url,path,original=uploaded; updated.question_content.append(ContentBlock("image",url,asset_id=asset_id,metadata={"local_asset_path":path,"original_filename":original}))
            error=_validate_question(updated)
            if error: flash(error,"error"); return render_template("teacher_question_form.html",**_form_context(updated,not save_as_new))
            if not save_as_new: storage.delete_question_assets(question_id)
            storage.create_question(updated); _persist_question_assets(updated); flash(f"Question {new_id} {'created as a new question' if save_as_new else 'updated'}.","success")
            return redirect(url_for("admin.edit_question",question_id=new_id) if save_as_new else url_for("admin.questions"))
        except ValueError as exc:
            flash(str(exc),"error"); return render_template("teacher_question_form.html",**_form_context(updated,not save_as_new))
    return render_template("teacher_question_form.html",**_form_context(q,True))

@admin_bp.route("/questions/<question_id>/duplicate",methods=["POST"])
def duplicate_question(question_id):
    if not storage.get_question(question_id): return "Question not found",404
    return redirect(url_for("admin.add_question",clone_from=question_id))

@admin_bp.route("/questions/<question_id>/delete",methods=["POST"])
def delete_question(question_id):
    if not storage.get_question(question_id): return "Question not found",404
    storage.delete_question(question_id); flash(f"Question {question_id} deactivated.","success"); return redirect(url_for("admin.questions"))

@admin_bp.route("/questions/<question_id>/activate",methods=["POST"])
def activate_question(question_id):
    if not storage.get_question(question_id): return "Question not found",404
    storage.activate_question(question_id); flash(f"Question {question_id} activated.","success"); return redirect(url_for("admin.questions"))

@admin_bp.route("/tests")
def tests(): return render_template("teacher_tests.html",tests=list(storage.tests.values()),questions=list(storage.questions.values()))

@admin_bp.route("/tests/new",methods=["GET","POST"])
def add_test():
    if request.method=="POST":
        selected=[qid for qid in request.form.getlist("question_ids") if qid in storage.questions and storage.questions[qid].status=="active"]
        if not selected: flash("Select at least one active question.","error"); return render_template("teacher_test_form.html",questions=list(storage.questions.values()),form=request.form)
        test_id=_next_test_id(); test=Test(test_id=test_id,title=_form_value("title") or test_id,subject=_form_value("subject","Mathematics") or "Mathematics",class_level=int(request.form.get("class_level","10")),duration_minutes=int(request.form.get("duration_minutes","60")),total_marks=sum(storage.questions[qid].marks for qid in selected),questions=selected,status=_form_value("status","active") or "active",board=_form_value("board") or None,test_date=request.form.get("test_date") or None,test_type=_form_value("test_type","weekly") or "weekly")
        storage.create_test(test); flash(f"Test {test_id} created with {len(selected)} questions.","success"); return redirect(url_for("admin.tests"))
    return render_template("teacher_test_form.html",questions=[q for q in storage.questions.values() if q.status=="active"],form={})

def register_admin(app): app.register_blueprint(admin_bp)
