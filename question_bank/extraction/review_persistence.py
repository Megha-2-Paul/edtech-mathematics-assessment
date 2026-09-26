"""Persistent storage for the teacher extraction review queue.

The review queue is intentionally separate from the canonical questions table:
uploaded external-AI JSON and human review state must survive application
restarts/redeploys without making unapproved questions live.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import text

from database import engine


def _questions_from_payload(payload: dict[str, Any] | list[Any]) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload.get("questions") or []
    raise ValueError("JSON batch payload must be an object or array.")


def save_batch(*, batch_id: str, filename: str, payload: dict[str, Any] | list[Any]) -> list[str]:
    """Persist one uploaded JSON batch and return stable item IDs."""
    questions = _questions_from_payload(payload)
    now = datetime.now()
    with engine.begin() as db:
        db.execute(
            text(
                """INSERT INTO extraction_review_batches
                   (batch_id, filename, payload_json, created_at, updated_at)
                   VALUES (:batch_id, :filename, :payload, :created_at, :updated_at)
                   ON DUPLICATE KEY UPDATE
                     filename=VALUES(filename),
                     payload_json=VALUES(payload_json),
                     updated_at=VALUES(updated_at)"""
            ),
            {
                "batch_id": batch_id,
                "filename": filename,
                "payload": json.dumps(payload, ensure_ascii=False),
                "created_at": now,
                "updated_at": now,
            },
        )
        item_ids: list[str] = []
        for index, question in enumerate(questions):
            if not isinstance(question, dict):
                continue
            item_id = f"{batch_id}:{index}"
            item_ids.append(item_id)
            db.execute(
                text(
                    """INSERT INTO extraction_review_items
                       (item_id, batch_id, question_index, question_json, status,
                        note, question_id, extraction_snapshot_json,
                        human_verified_values_json, created_at, updated_at)
                       VALUES (:item_id, :batch_id, :question_index, :question_json,
                               'PENDING', '', NULL, NULL, NULL, :created_at, :updated_at)
                       ON DUPLICATE KEY UPDATE
                         question_json=VALUES(question_json),
                         updated_at=VALUES(updated_at)"""
                ),
                {
                    "item_id": item_id,
                    "batch_id": batch_id,
                    "question_index": index,
                    "question_json": json.dumps(question, ensure_ascii=False),
                    "created_at": now,
                    "updated_at": now,
                },
            )
    return item_ids


def get_item(item_id: str) -> dict[str, Any] | None:
    with engine.connect() as db:
        row = db.execute(
            text(
                """SELECT i.*, b.filename, b.payload_json
                   FROM extraction_review_items i
                   JOIN extraction_review_batches b ON b.batch_id=i.batch_id
                   WHERE i.item_id=:item_id"""
            ),
            {"item_id": item_id},
        ).mappings().first()
    if not row:
        return None
    return _decode_row(row)


def list_items() -> list[dict[str, Any]]:
    with engine.connect() as db:
        rows = db.execute(
            text(
                """SELECT i.*, b.filename, b.payload_json
                   FROM extraction_review_items i
                   JOIN extraction_review_batches b ON b.batch_id=i.batch_id
                   ORDER BY i.created_at, i.question_index"""
            )
        ).mappings().all()
    return [_decode_row(row) for row in rows]


def save_review(
    item_id: str,
    status: str,
    note: str = "",
    question_id: str | None = None,
    question_snapshot: dict[str, Any] | None = None,
    human_verified_values: dict[str, Any] | None = None,
) -> None:
    now = datetime.now()
    with engine.begin() as db:
        db.execute(
            text(
                """UPDATE extraction_review_items
                   SET status=:status,
                       note=:note,
                       question_id=:question_id,
                       extraction_snapshot_json=:snapshot,
                       human_verified_values_json=:verified,
                       updated_at=:updated_at
                   WHERE item_id=:item_id"""
            ),
            {
                "item_id": item_id,
                "status": status,
                "note": note,
                "question_id": question_id,
                "snapshot": json.dumps(question_snapshot, ensure_ascii=False) if question_snapshot is not None else None,
                "verified": json.dumps(human_verified_values, ensure_ascii=False) if human_verified_values is not None else None,
                "updated_at": now,
            },
        )


def _decode_row(row) -> dict[str, Any]:
    item = dict(row)
    for field in ("question_json", "payload_json", "extraction_snapshot_json", "human_verified_values_json"):
        value = item.get(field)
        if value:
            try:
                item[field] = json.loads(value)
            except (TypeError, json.JSONDecodeError):
                pass
        elif field.endswith("_json"):
            item[field] = None
    item["question"] = item.get("question_json") or {}
    item["payload"] = item.get("payload_json") or {}
    item["status"] = item.get("status") or "PENDING"
    item["note"] = item.get("note") or ""
    return item
