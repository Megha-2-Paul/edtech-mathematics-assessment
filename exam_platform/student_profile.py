"""Build a cumulative, deterministic student performance profile."""
from collections import Counter, defaultdict
from sqlalchemy import text
from database import engine
from .diagnosis import ERROR_LABELS, _num


def build_student_profile(student_id):
    with engine.connect() as db:
        attempts = db.execute(text("""
            SELECT attempt_id,test_id,submitted_at,score,percentage,attempt_rate,accuracy
            FROM attempts WHERE student_id=:student_id AND status='submitted'
            ORDER BY submitted_at
        """), {"student_id": student_id}).mappings().all()
        errors = db.execute(text("""
            SELECT a.attempt_id,a.submitted_at,e.error_code
            FROM evaluation_errors e JOIN responses r ON r.response_id=e.response_id
            JOIN attempts a ON a.attempt_id=r.attempt_id
            WHERE a.student_id=:student_id AND a.status='submitted'
            ORDER BY a.submitted_at
        """), {"student_id": student_id}).mappings().all()
        chapters = db.execute(text("""
            SELECT a.attempt_id,a.submitted_at,q.chapter,q.topic,q.competency,q.marks,r.marks_awarded
            FROM responses r JOIN attempts a ON a.attempt_id=r.attempt_id
            JOIN questions q ON q.question_id=r.question_id
            WHERE a.student_id=:student_id AND a.status='submitted'
            ORDER BY a.submitted_at
        """), {"student_id": student_id}).mappings().all()
        history = db.execute(text("""
            SELECT question_id,attempt_count,correct_count,last_attempted_at,last_correct_at,last_marks_awarded,last_error_summary
            FROM question_history WHERE student_id=:student_id ORDER BY last_attempted_at DESC
        """), {"student_id": student_id}).mappings().all()

    error_counts = Counter(row["error_code"] for row in errors)
    chapter_totals = defaultdict(lambda: [0.0, 0.0, 0])
    topic_totals = defaultdict(lambda: [0.0, 0.0, 0])
    competency_totals = defaultdict(lambda: [0.0, 0.0, 0])
    for row in chapters:
        max_marks = _num(row["marks"]); awarded = _num(row["marks_awarded"])
        for bucket, name in ((chapter_totals, row["chapter"] or "Unclassified"), (topic_totals, row["topic"] or "Unclassified"), (competency_totals, row["competency"] or "Unclassified")):
            bucket[name][0] += max_marks; bucket[name][1] += awarded; bucket[name][2] += 1

    def summarize(bucket):
        result=[]
        for name,(maximum,awarded,count) in bucket.items():
            result.append({"name":name,"max_marks":round(maximum,2),"marks":round(awarded,2),"percentage":round(awarded/maximum*100,1) if maximum else 0,"questions":count})
        return sorted(result,key=lambda x:x["percentage"],reverse=True)

    score_history=[{"attempt_id":a["attempt_id"],"test_id":a["test_id"],"submitted_at":a["submitted_at"],"score":_num(a["score"]),"percentage":_num(a["percentage"]),"attempt_rate":_num(a["attempt_rate"]),"accuracy":_num(a["accuracy"])} for a in attempts]
    latest=score_history[-1] if score_history else None
    previous=score_history[-2] if len(score_history)>1 else None
    recurring=[{"code":code,"label":ERROR_LABELS.get(code,code),"count":count} for code,count in error_counts.most_common() if count>=2]
    return {
        "student_id": student_id, "tests_taken": len(attempts), "score_history": score_history,
        "latest": latest, "previous": previous,
        "score_change": round(latest["score"]-previous["score"],2) if latest and previous else None,
        "percentage_change": round(latest["percentage"]-previous["percentage"],2) if latest and previous else None,
        "attempt_rate_change": round(latest["attempt_rate"]-previous["attempt_rate"],2) if latest and previous else None,
        "accuracy_change": round(latest["accuracy"]-previous["accuracy"],2) if latest and previous else None,
        "error_counts":[{"code":c,"label":ERROR_LABELS.get(c,c),"count":n} for c,n in error_counts.most_common()],
        "recurring_errors":recurring, "chapter_performance":summarize(chapter_totals),
        "topic_performance":summarize(topic_totals), "competency_performance":summarize(competency_totals),
        "question_history":[dict(row) for row in history],
        "strongest_chapters":summarize(chapter_totals)[:3],
        "weakest_chapters":sorted(summarize(chapter_totals),key=lambda x:x["percentage"])[:3],
    }
