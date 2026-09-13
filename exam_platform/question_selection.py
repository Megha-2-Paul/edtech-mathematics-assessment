"""Deterministic question candidate ranking for future assessments."""
from collections import Counter
from sqlalchemy import text
from database import engine
from .diagnosis import ERROR_LABELS


def rank_question_candidates(student_id, candidate_questions, limit=None):
    """Rank question objects without changing or creating a test."""
    with engine.connect() as db:
        history = db.execute(text("""
            SELECT question_id,attempt_count,correct_count,last_marks_awarded,last_error_summary
            FROM question_history WHERE student_id=:student_id
        """), {"student_id": student_id}).mappings().all()
        errors = db.execute(text("""
            SELECT e.error_code,COUNT(*) AS n FROM evaluation_errors e
            JOIN responses r ON r.response_id=e.response_id JOIN attempts a ON a.attempt_id=r.attempt_id
            WHERE a.student_id=:student_id AND a.status='submitted' GROUP BY e.error_code
        """), {"student_id": student_id}).mappings().all()
    history_map={r["question_id"]:r for r in history}
    error_counts=Counter({r["error_code"]:int(r["n"]) for r in errors})
    weak_chapters=set()
    weak_topics=set()
    for q in candidate_questions:
        # Populated below from optional metadata; repeated questions are still retained
        # when they are useful for reassessment.
        pass
    ranked=[]
    for q in candidate_questions:
        h=history_map.get(q.question_id); score=0; reasons=[]
        if not h:
            score += 50; reasons.append("new question")
        else:
            score -= min(30,int(h["attempt_count"])*10)
            if h["last_marks_awarded"] is not None and float(h["last_marks_awarded"] or 0) < float(q.marks):
                score += 25; reasons.append("reassess previous gap")
            if h["last_error_summary"]:
                score += 15; reasons.append("targets previous error")
        if q.chapter in weak_chapters:
            score += 20; reasons.append("weak chapter")
        if q.topic in weak_topics:
            score += 15; reasons.append("weak topic")
        for code in error_counts:
            if code in (h["last_error_summary"] or "") if h else False:
                score += 5
        if getattr(q,"status","active") != "active":
            score -= 100
        ranked.append((score, q, reasons))
    ranked.sort(key=lambda item:(item[0], getattr(item[1],"marks",0)), reverse=True)
    if limit is not None: ranked=ranked[:limit]
    return [{"question":q,"score":score,"reasons":reasons} for score,q,reasons in ranked]
