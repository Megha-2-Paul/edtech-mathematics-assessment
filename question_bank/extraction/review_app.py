"""Local human-verification interface for AI question extraction."""
from __future__ import annotations
import json, os, re
from datetime import datetime
from pathlib import Path
from typing import Any
import fitz
from flask import Blueprint, abort, jsonify, redirect, render_template, request, send_file, url_for
from exam_platform.models import ContentBlock, Question
from exam_platform.storage import storage
from question_bank.extraction.extraction_contract import ALLOWED_QUESTION_TYPES, ALLOWED_UPLOAD_MODES, INFERRED_FIELDS_REQUIRE_HUMAN_VERIFICATION
from question_bank.extraction.question_cropper import extract_page_questions
from question_bank.extraction.question_asset_persistence import persist_source_visuals

review_bp=Blueprint("extraction_review",__name__,url_prefix="/teacher/extraction-review")
PROJECT_ROOT=Path(__file__).resolve().parents[2]; INBOX_DIR=Path(os.getenv("EXTRACTION_INBOX_DIR",PROJECT_ROOT/"extraction_inbox")); REVIEW_DIR=Path(os.getenv("EXTRACTION_REVIEW_DIR",PROJECT_ROOT/"extraction_reviews")); SOURCE_DIR=Path(os.getenv("SOURCE_PDF_DIR",PROJECT_ROOT/"source_pdfs")); PAGE_DIR=REVIEW_DIR/"page_renders"; CROP_DIR=REVIEW_DIR/"question_crops"
for d in (INBOX_DIR,REVIEW_DIR,PAGE_DIR,CROP_DIR):d.mkdir(parents=True,exist_ok=True)
def _safe_id(v):return re.sub(r"[^A-Za-z0-9_.-]+","_",v)
def _load_json(p):
    try:d=json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError,json.JSONDecodeError) as e:raise ValueError(f"Cannot read extraction JSON: {p.name}: {e}") from e
    if not isinstance(d,dict) or not isinstance(d.get("questions"),list):raise ValueError(f"Extraction file must contain a top-level 'questions' list: {p.name}")
    return d
def _extraction_files():return sorted(INBOX_DIR.glob("*.json"))
def _review_path(i):return REVIEW_DIR/f"{_safe_id(i)}.json"
def _load_review(i):
    p=_review_path(i)
    if not p.exists():return {"status":"PENDING","updated_at":None,"note":""}
    try:return json.loads(p.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError):return {"status":"PENDING","updated_at":None,"note":""}
def _save_review(i,status,note="",question_id=None,question_snapshot=None,human_verified_values=None):
    p={"status":status,"updated_at":datetime.now().isoformat(),"note":note}
    if question_id:p["question_id"]=question_id
    if question_snapshot is not None:p["extraction_snapshot"]=question_snapshot
    if human_verified_values is not None:p["human_verified_values"]=human_verified_values
    _review_path(i).write_text(json.dumps(p,indent=2,ensure_ascii=False),encoding="utf-8")
def _field(q,n,*aliases,default=None):
    if n in q and q[n] is not None:return q[n]
    for a in aliases:
        if a in q and q[a] is not None:return q[a]
    return default
def _normalise_list(v):return [] if v is None else v if isinstance(v,list) else [v]
def _normalise_pages(q):
    vals=_field(q,"source_pages",default=[]);vals=vals if isinstance(vals,list) else [vals];first=_field(q,"source_page","page_number","page")
    if first is not None:vals=[first,*vals]
    out=[]
    for v in vals:
        try:p=int(v)
        except (TypeError,ValueError):continue
        if p>=1 and p not in out:out.append(p)
    return out or [1]
def _question_text(q):
    v=q.get("question_text",q.get("text",q.get("question")));return "\n".join(str(x) for x in v) if isinstance(v,list) else str(v or "").strip()
def _source_year(pdf):
    m=re.search(r"(?:19|20)\d{2}",pdf);return int(m.group()) if m else None
def _parse_json_field(raw,label,default):
    if not raw.strip():return default
    try:return json.loads(raw)
    except json.JSONDecodeError as e:raise ValueError(f"{label} must contain valid JSON") from e
def _next_question_id():
    nums=[int(x[1:]) for x in storage.questions if x.startswith("Q") and x[1:].isdigit()];return f"Q{max(nums,default=0)+1:04d}"
def _question_from_extraction(q,data,o):
    source_pdf=str(data.get("source_pdf") or data.get("source_paper") or q.get("source_pdf") or "");qt=str(o.get("question_type") or "saq").lower();upload=str(o.get("handwritten_upload_mode") or "none").lower()
    if qt not in ALLOWED_QUESTION_TYPES:raise ValueError("Invalid question type")
    if upload not in ALLOWED_UPLOAD_MODES:raise ValueError("Invalid handwritten upload mode")
    try:marks=float(o.get("marks") or 0);cls=int(o.get("class_level") or 12)
    except (TypeError,ValueError) as e:raise ValueError("Marks and class must be valid numbers") from e
    if marks<0:raise ValueError("Marks cannot be negative")
    content=[ContentBlock("text",str(o.get("question_text") or "").strip())]
    for part in _normalise_list(o.get("question_parts")):
        if isinstance(part,dict):
            t=str(part.get("part_text") or part.get("text") or "").strip()
            if t:content.append(ContentBlock("text",t,metadata={"question_part":part}))
    ref=str(o.get("diagram_reference") or "").strip()
    if ref:content.append(ContentBlock("image",ref,metadata={"source_reference":ref}))
    for a in _normalise_list(o.get("assets")):
        ref=str(a.get("asset_id") or a.get("reference") or a.get("name") or "").strip() if isinstance(a,dict) else str(a).strip()
        if ref:content.append(ContentBlock("image",ref,metadata={"source_asset_reference":ref}))
    return Question(question_id=_next_question_id(),question_type=qt,answer_mode=str(o.get("answer_mode") or "manual_written_answer").strip(),question_content=content,answer_choices=[str(x) for x in _normalise_list(o.get("answer_choices"))],correct_answer=o.get("correct_answer") or None,marks=marks,handwritten_upload_mode=upload,subject=str(o.get("subject") or "Mathematics").strip(),board=str(o.get("board") or "CBSE").strip(),class_level=cls,chapter=str(o.get("chapter") or "").strip() or None,topic=str(o.get("topic") or "").strip() or None,subtopic=str(o.get("subtopic") or "").strip() or None,difficulty=str(o.get("difficulty") or "").strip() or None,competency=str(o.get("competency") or "").strip() or None,source=source_pdf or None,source_year=o.get("source_year") or _source_year(source_pdf),status="active")
def _review_form_values(q,data,review):
    source_pdf=str(data.get("source_pdf") or data.get("source_paper") or q.get("source_pdf") or "");v={n:_field(q,n) for n in ("answer_mode","handwritten_upload_mode","subject","board","class_level","chapter","topic","subtopic","difficulty","competency","source_year","correct_answer","diagram_reference")}
    v.update(question_text=_question_text(q),answer_choices=_field(q,"answer_choices","options",default=[]),question_parts=_field(q,"question_parts",default=[]),source=_field(q,"source",default=source_pdf),source_pdf=source_pdf,source_page=_field(q,"source_page","page_number","page"),source_pages=_normalise_pages(q),source_question_number=_field(q,"source_question_number","question_number","number"),source_occurrence_id=_field(q,"source_occurrence_id"),assets=_field(q,"assets",default=[]),extraction_provider=_field(q,"extraction_provider",default=data.get("extraction_provider")),extraction_model=_field(q,"extraction_model",default=data.get("extraction_model")),extraction_run_id=_field(q,"extraction_run_id",default=data.get("extraction_run_id")),extraction_confidence=_field(q,"extraction_confidence",default=data.get("extraction_confidence")),extraction_warnings=_field(q,"extraction_warnings",default=data.get("extraction_warnings",[])),question_type=str(_field(q,"question_type","type",default="saq")).lower())
    if review.get("status")=="APPROVED" and review.get("question_id"):
        canonical=storage.get_question(review["question_id"])
        if canonical:
            blocks=canonical.question_content;text=[b for b in blocks if getattr(b,"type","")=="text"];images=[b for b in blocks if getattr(b,"type","")=="image"]
            if text:v["question_text"]=str(text[0].value or "");v["question_parts"]=[getattr(b,"metadata",{}).get("question_part") for b in text[1:] if getattr(b,"metadata",{}).get("question_part")]
            refs=[]
            for b in images:
                m=getattr(b,"metadata",{}) or {};r=m.get("source_asset_reference") or m.get("source_reference") or b.value
                if r and r not in refs:refs.append(r)
            v["assets"]=refs;v["diagram_reference"]=next((str(b.value) for b in images if (getattr(b,"metadata",{}) or {}).get("source_reference")),v.get("diagram_reference"))
            for n in ("answer_mode","handwritten_upload_mode","subject","board","class_level","chapter","topic","subtopic","difficulty","competency","correct_answer","source_year"):
                if hasattr(canonical,n):v[n]=getattr(canonical,n)
            v["marks"]=canonical.marks;v["question_type"]=canonical.question_type;v["source"]=canonical.source or v["source"];v["answer_choices"]=list(canonical.answer_choices or [])
    if review.get("human_verified_values"):v.update(review["human_verified_values"])
    return v
def _find_item(i):
    try:fn,idx=i.rsplit(":",1);idx=int(idx)
    except ValueError:abort(404)
    p=INBOX_DIR/f"{fn}.json"
    if not p.exists():abort(404)
    d=_load_json(p)
    if idx<0 or idx>=len(d["questions"]):abort(404)
    q=d["questions"][idx]
    if not isinstance(q,dict):abort(404)
    return p,d,q
def _source_pdf(d,q):
    fn=str(d.get("source_pdf") or d.get("source_paper") or q.get("source_pdf") or "");p=SOURCE_DIR/Path(fn).name
    if not p.exists():abort(404,description=f"Source PDF not found: {fn}")
    return p
def _render_page(pdf,pn):
    out=PAGE_DIR/_safe_id(pdf.stem);out.mkdir(parents=True,exist_ok=True);p=out/f"page_{pn}.png"
    if p.exists():return p
    with fitz.open(str(pdf)) as d:d[pn-1].get_pixmap(dpi=150,alpha=False).save(str(p))
    return p
def _render_question_crop(pdf,pn,qn,item):
    try:rows=extract_page_questions(pdf,pn,CROP_DIR/_safe_id(item),dpi=180)
    except Exception:return None
    for r in rows:
        if str(r.get("question_number"))==str(qn).strip():
            p=Path(r.get("crop_path","") )
            if p.exists():return p
    return None
@review_bp.route("/")
def dashboard():
    items=[]
    for p in _extraction_files():
        try:d=_load_json(p)
        except ValueError:continue
        for i,q in enumerate(d["questions"]):
            if not isinstance(q,dict):continue
            rid=f"{p.stem}:{i}";r=_load_review(rid);items.append({"item_id":rid,"file":p.name,"source_pdf":str(d.get("source_pdf") or d.get("source_paper") or ""),"index":i,"question_number":str(_field(q,"question_number","number",default=i+1)),"page_number":_field(q,"source_page","page_number","page",default=1),"marks":q.get("marks"),"question_type":q.get("question_type") or q.get("type") or "","status":r.get("status","PENDING"),"chapter_missing":not str(q.get("chapter") or "").strip()})
    stats={s:sum(x["status"]==s for x in items) for s in ("PENDING","APPROVED","REJECTED","NEEDS_REVIEW")};stats["CHAPTER_REVIEW"]=sum(x["chapter_missing"] and x["status"] not in {"APPROVED","REJECTED"} for x in items)
    return render_template("extraction_review_dashboard.html",items=items,stats=stats)
@review_bp.route("/<path:item_id>")
def item(item_id):
    path,data,q=_find_item(item_id);pdf=_source_pdf(data,q);review=_load_review(item_id);v=_review_form_values(q,data,review);stored_assets=[]
    if review.get("status")=="APPROVED" and review.get("question_id"):
        try:
            stored_assets=[dict(x) for x in storage.get_question_assets(review["question_id"])]
            if not stored_assets:stored_assets=persist_source_visuals(pdf,int(v["source_pages"][0]),str(v["source_question_number"]),str(review["question_id"]))
        except Exception:stored_assets=[]
    ids=[]
    for p in _extraction_files():
        try:d=_load_json(p)
        except ValueError:continue
        ids += [f"{p.stem}:{i}" for i,x in enumerate(d["questions"]) if isinstance(x,dict)]
    pos=ids.index(item_id) if item_id in ids else 0;pages=v["source_pages"];urls=[{"number":p,"url":url_for("extraction_review.page_image_numbered",item_id=item_id,page_number=p)} for p in pages];crop=_render_question_crop(pdf,pages[0],str(v["source_question_number"]),item_id) if pages else None;missing=[n for n in INFERRED_FIELDS_REQUIRE_HUMAN_VERIFICATION if not str(v.get(n) or "").strip()]
    return render_template("extraction_review_item.html",item_id=item_id,filename=path.name,data=data,question=q,values=v,review=review,missing_inferred_fields=missing,stored_assets=stored_assets,source_pdf=pdf.name,page_number=pages[0] if pages else 1,source_page_urls=urls,question_crop_url=url_for("extraction_review.question_crop",item_id=item_id) if crop else None,previous_url=url_for("extraction_review.item",item_id=ids[pos-1]) if pos>0 else None,next_url=url_for("extraction_review.item",item_id=ids[pos+1]) if pos+1<len(ids) else None,position=pos+1,total=len(ids))
@review_bp.route("/<path:item_id>/review",methods=["POST"])
def review(item_id):
    _path,data,q=_find_item(item_id);status=request.form.get("status","NEEDS_REVIEW").upper();note=request.form.get("note","").strip();current=_load_review(item_id)
    if status not in {"APPROVED","REJECTED","NEEDS_REVIEW","PENDING"}:return jsonify({"error":"Invalid review status"}),400
    if status=="APPROVED":
        if current.get("status")=="APPROVED" and current.get("question_id"):return redirect(url_for("extraction_review.item",item_id=item_id))
        names=("question_text","marks","question_type","answer_mode","handwritten_upload_mode","subject","board","class_level","chapter","topic","subtopic","difficulty","competency","correct_answer","source_year","diagram_reference");o={n:request.form.get(n,"") for n in names}
        try:o["answer_choices"]=_parse_json_field(request.form.get("answer_choices","[]"),"Answer choices",[]);o["question_parts"]=_parse_json_field(request.form.get("question_parts","[]"),"Question parts",[]);o["assets"]=_parse_json_field(request.form.get("assets","[]"),"Assets",[])
        except ValueError as e:return jsonify({"error":str(e)}),400
        if not o["question_text"].strip():return jsonify({"error":"Question text cannot be empty"}),400
        if not o["chapter"].strip():return jsonify({"error":"Chapter must be verified before approval."}),400
        if o["question_type"].strip().lower()=="mcq" and not o["correct_answer"].strip():return jsonify({"error":"Correct answer must be verified before approving an MCQ."}),400
        try:qobj=_question_from_extraction(q,data,o);storage.create_question(qobj)
        except ValueError as e:return jsonify({"error":str(e)}),400
        try:persist_source_visuals(_source_pdf(data,q),int(_normalise_pages(q)[0]),str(_field(q,"source_question_number","question_number","number",default="")),qobj.question_id)
        except Exception as e:note=f"{note + ' ' if note else ''}Visual asset persistence warning: {e}"
        _save_review(item_id,"APPROVED",note or f"Imported as {qobj.question_id}",qobj.question_id,question_snapshot=q,human_verified_values=o)
    else:_save_review(item_id,status,note,question_snapshot=q)
    return redirect(url_for("extraction_review.item",item_id=item_id))
@review_bp.route("/<path:item_id>/page.png")
def page_image(item_id):
    _p,d,q=_find_item(item_id);return send_file(_render_page(_source_pdf(d,q),_normalise_pages(q)[0]),mimetype="image/png",max_age=0)
@review_bp.route("/<path:item_id>/page/<int:page_number>.png")
def page_image_numbered(item_id,page_number):
    _p,d,q=_find_item(item_id);pdf=_source_pdf(d,q)
    if page_number not in _normalise_pages(q):abort(404)
    return send_file(_render_page(pdf,page_number),mimetype="image/png",max_age=0)
@review_bp.route("/<path:item_id>/question-crop.png")
def question_crop(item_id):
    _p,d,q=_find_item(item_id);pdf=_source_pdf(d,q);v=_review_form_values(q,d,_load_review(item_id));p=_render_question_crop(pdf,v["source_pages"][0],str(v["source_question_number"]),item_id)
    if not p:abort(404)
    return send_file(p,mimetype="image/png",max_age=0)
@review_bp.route("/<path:item_id>/stored-asset/<asset_id>.png")
def stored_asset(item_id,asset_id):
    _p,_d,_q=_find_item(item_id);r=_load_review(item_id)
    if r.get("status")!="APPROVED" or not r.get("question_id"):abort(404)
    row=next((dict(x) for x in storage.get_question_assets(r["question_id"]) if str(x.get("asset_id"))==asset_id),None)
    if not row:abort(404)
    p=Path(str(row.get("file_path") or ""))
    if not p.exists():abort(404,description="Stored visual asset file is missing")
    return send_file(p,mimetype="image/png",max_age=0)
def register_extraction_review(app):app.register_blueprint(review_bp)
