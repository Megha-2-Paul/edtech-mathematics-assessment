"""Optional primary -> secondary (Aiven) sync for question-bank data."""
import os
from typing import Mapping
from sqlalchemy import create_engine, text

SYNC_DATABASE_URL = os.getenv("QUESTION_BANK_SYNC_DATABASE_URL", "").strip()
SYNC_ENABLED = bool(SYNC_DATABASE_URL)
_SYNC_ENGINE = create_engine(SYNC_DATABASE_URL, pool_pre_ping=True, future=True) if SYNC_ENABLED else None

QUESTION_UPSERT_SQL = """
INSERT INTO questions(question_id, subject, board, class_level, chapter, topic, subtopic, question_type, answer_mode, difficulty, competency, question_content_json, answer_choices_json, correct_answer, marks, handwritten_upload_mode, source, source_year, status, source_type, verification_status, canonical_question_id)
VALUES(:id, :subject, :board, :class, :chapter, :topic, :subtopic, :type, :mode, :difficulty, :competency, :content, :choices, :correct, :marks, :upload, :source, :year, :status, :source_type, :verification_status, :canonical_question_id)
ON DUPLICATE KEY UPDATE subject=VALUES(subject), board=VALUES(board), class_level=VALUES(class_level), chapter=VALUES(chapter), topic=VALUES(topic), subtopic=VALUES(subtopic), question_type=VALUES(question_type), answer_mode=VALUES(answer_mode), difficulty=VALUES(difficulty), competency=VALUES(competency), question_content_json=VALUES(question_content_json), answer_choices_json=VALUES(answer_choices_json), correct_answer=VALUES(correct_answer), marks=VALUES(marks), handwritten_upload_mode=VALUES(handwritten_upload_mode), source=VALUES(source), source_year=VALUES(source_year), status=VALUES(status), source_type=VALUES(source_type), verification_status=VALUES(verification_status), canonical_question_id=VALUES(canonical_question_id)
"""

def is_sync_configured() -> bool:
    return SYNC_ENABLED and _SYNC_ENGINE is not None

def sync_question_payload(payload: Mapping, *, engine=None) -> None:
    target = engine or _SYNC_ENGINE
    if target is None:
        return
    with target.begin() as db:
        db.execute(text(QUESTION_UPSERT_SQL), dict(payload))

def sync_question_solution(question_id: str, solution=None, marking_scheme=None, *, verified=False, source_type="extracted", version=1, engine=None) -> None:
    target = engine or _SYNC_ENGINE
    if target is None:
        return
    with target.begin() as db:
        db.execute(text("INSERT INTO question_solutions(question_id, solution_content, marking_scheme, version, verified, source_type) VALUES(:question, :solution, :scheme, :version, :verified, :source_type) ON DUPLICATE KEY UPDATE solution_content=VALUES(solution_content), marking_scheme=VALUES(marking_scheme), verified=VALUES(verified), source_type=VALUES(source_type), updated_at=CURRENT_TIMESTAMP"), {"question": question_id, "solution": solution, "scheme": marking_scheme, "version": version, "verified": 1 if verified else 0, "source_type": source_type})

def deactivate_question(question_id: str, *, engine=None) -> None:
    target = engine or _SYNC_ENGINE
    if target is None:
        return
    with target.begin() as db:
        db.execute(text("UPDATE questions SET status='inactive' WHERE question_id=:id"), {"id": question_id})
