"""Question-bank synchronization helpers.

There are two supported directions:

* local -> cloud: used by the existing opt-in dual-write path.
* cloud -> local: used after questions are approved through the public
  Render teacher UI. The cloud database is the source of truth for this
  direction.

Only the question-bank tables are synchronized. Student attempts,
evaluations, payments and other production data are deliberately excluded.
"""
from __future__ import annotations

import os
from typing import Any

# Import database first so its .env loader runs before we read the cloud URL.
from database import engine
from sqlalchemy import create_engine, text

_SYNC_URL = os.getenv("QUESTION_BANK_SYNC_DATABASE_URL", "").strip()
_SYNC_ENGINE = (
    create_engine(_SYNC_URL, pool_pre_ping=True, future=True)
    if _SYNC_URL
    else None
)

QUESTION_COLUMNS = (
    "question_id,subject,board,class_level,chapter,topic,subtopic,"
    "question_type,answer_mode,difficulty,competency,question_content_json,"
    "answer_choices_json,correct_answer,marks,handwritten_upload_mode,"
    "source,source_year,status,created_at,updated_at"
)


def sync_question_to_secondary(params: dict[str, Any]) -> None:
    """Write one canonical question to the configured secondary database."""
    if _SYNC_ENGINE is None:
        raise RuntimeError(
            "QUESTION_BANK_SYNC_DATABASE_URL is not configured; "
            "secondary question-bank sync cannot be completed."
        )

    statement = text(
        """INSERT INTO questions(
            question_id,subject,board,class_level,chapter,topic,subtopic,
            question_type,answer_mode,difficulty,competency,
            question_content_json,answer_choices_json,correct_answer,marks,
            handwritten_upload_mode,source,source_year,status
        ) VALUES(
            :id,:subject,:board,:class,:chapter,:topic,:subtopic,
            :type,:mode,:difficulty,:competency,
            :content,:choices,:correct,:marks,:upload,:source,:year,:status
        )
        ON DUPLICATE KEY UPDATE
            question_content_json=VALUES(question_content_json),
            answer_choices_json=VALUES(answer_choices_json),
            correct_answer=VALUES(correct_answer),
            marks=VALUES(marks),
            handwritten_upload_mode=VALUES(handwritten_upload_mode),
            chapter=VALUES(chapter),
            topic=VALUES(topic),
            subtopic=VALUES(subtopic),
            difficulty=VALUES(difficulty),
            competency=VALUES(competency),
            subject=VALUES(subject),
            board=VALUES(board),
            class_level=VALUES(class_level),
            answer_mode=VALUES(answer_mode),
            question_type=VALUES(question_type),
            source=VALUES(source),
            source_year=VALUES(source_year),
            status=VALUES(status)"""
    )
    with _SYNC_ENGINE.begin() as db:
        db.execute(statement, params)


def secondary_sync_configured() -> bool:
    return _SYNC_ENGINE is not None


def sync_questions_from_cloud() -> dict[str, int]:
    """Pull the cloud question bank into the local MySQL database.

    Cloud is authoritative for this operation. Existing local questions with
    matching question_id are updated; local-only questions are left untouched.
    Inactive questions are also copied so deletions/deactivations made in the
    public UI are reflected locally.

    Returns counts suitable for CLI output.
    """
    if _SYNC_ENGINE is None:
        raise RuntimeError(
            "QUESTION_BANK_SYNC_DATABASE_URL is not configured. "
            "Set it to the Aiven/Render MySQL URL in your local .env."
        )

    select_sql = text(f"SELECT {QUESTION_COLUMNS} FROM questions")
    upsert_sql = text(
        """INSERT INTO questions(
            question_id,subject,board,class_level,chapter,topic,subtopic,
            question_type,answer_mode,difficulty,competency,
            question_content_json,answer_choices_json,correct_answer,marks,
            handwritten_upload_mode,source,source_year,status,created_at,updated_at
        ) VALUES(
            :question_id,:subject,:board,:class_level,:chapter,:topic,:subtopic,
            :question_type,:answer_mode,:difficulty,:competency,
            :question_content_json,:answer_choices_json,:correct_answer,:marks,
            :handwritten_upload_mode,:source,:source_year,:status,
            :created_at,:updated_at
        )
        ON DUPLICATE KEY UPDATE
            subject=VALUES(subject),
            board=VALUES(board),
            class_level=VALUES(class_level),
            chapter=VALUES(chapter),
            topic=VALUES(topic),
            subtopic=VALUES(subtopic),
            question_type=VALUES(question_type),
            answer_mode=VALUES(answer_mode),
            difficulty=VALUES(difficulty),
            competency=VALUES(competency),
            question_content_json=VALUES(question_content_json),
            answer_choices_json=VALUES(answer_choices_json),
            correct_answer=VALUES(correct_answer),
            marks=VALUES(marks),
            handwritten_upload_mode=VALUES(handwritten_upload_mode),
            source=VALUES(source),
            source_year=VALUES(source_year),
            status=VALUES(status),
            created_at=VALUES(created_at),
            updated_at=VALUES(updated_at)"""
    )

    with _SYNC_ENGINE.connect() as cloud:
        rows = [dict(row) for row in cloud.execute(select_sql).mappings()]

    inserted = updated = 0
    with engine.begin() as local:
        for row in rows:
            existing = local.execute(
                text("SELECT question_id FROM questions WHERE question_id=:id"),
                {"id": row["question_id"]},
            ).scalar_one_or_none()
            local.execute(upsert_sql, row)
            if existing is None:
                inserted += 1
            else:
                updated += 1

    return {"cloud_questions": len(rows), "inserted": inserted, "updated": updated}
