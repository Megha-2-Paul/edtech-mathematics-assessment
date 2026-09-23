"""Opt-in dual-write support for approved question-bank records.

The primary application database remains authoritative. When
QUESTION_BANK_SYNC_DATABASE_URL is configured and a question is explicitly
published with sync_to_secondary=True, the same canonical question record is
written to the secondary database as well.

This is intentionally limited to question records; student attempts,
evaluations, payments and other production data are not mirrored.
"""
from __future__ import annotations

import os
from typing import Any

from sqlalchemy import create_engine, text

_SYNC_URL = os.getenv("QUESTION_BANK_SYNC_DATABASE_URL", "").strip()
_SYNC_ENGINE = (
    create_engine(_SYNC_URL, pool_pre_ping=True, future=True)
    if _SYNC_URL
    else None
)


def sync_question_to_secondary(params: dict[str, Any]) -> None:
    """Write one canonical question to the configured secondary database.

    Raises RuntimeError when dual-write is requested but no secondary database
    is configured, or when the secondary write fails. The caller can then
    prevent a false impression that both databases were updated.
    """
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
