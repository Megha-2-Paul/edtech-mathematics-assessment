"""Utilities for safely separating explicit internal-choice questions."""
from __future__ import annotations

import re
from typing import Any


def _part_text(part: dict[str, Any]) -> str:
    return str(part.get("part_text") or part.get("text") or "").strip()


def _part_identifier(part: dict[str, Any], index: int) -> str:
    raw = str(
        part.get("part_identifier")
        or part.get("identifier")
        or part.get("label")
        or ""
    ).strip()
    raw = raw.strip("()[] ").lower()
    return raw or chr(ord("a") + index)


def is_explicit_or_question(question_text: str, parts: Any) -> bool:
    """Return True only for a clear two-alternative (a)/(b) OR question.

    This deliberately does NOT treat ordinary subquestions such as (i)/(ii),
    or case-study parts such as (i), (ii), (iii)(a), (iii)(b), as independent
    questions. We require the source question text to contain an explicit OR
    and the extracted parts to be exactly the two alternatives a and b.
    """
    if not isinstance(parts, list) or len(parts) != 2:
        return False

    dict_parts = [p for p in parts if isinstance(p, dict) and _part_text(p)]
    if len(dict_parts) != 2:
        return False

    has_or_word = bool(re.search(r"\bOR\b", str(question_text or ""), flags=re.IGNORECASE))
    identifiers = [_part_identifier(p, i) for i, p in enumerate(dict_parts)]
    return has_or_word and identifiers == ["a", "b"]


def split_or_parts(question_text: str, parts: Any) -> list[dict[str, Any]]:
    """Return two normalized independent alternatives, or [] when unsafe."""
    if not is_explicit_or_question(question_text, parts):
        return []

    result: list[dict[str, Any]] = []
    for index, part in enumerate(parts):
        if not isinstance(part, dict):
            continue
        text = _part_text(part)
        if not text:
            continue
        result.append(
            {
                "part_identifier": _part_identifier(part, index),
                "question_text": text,
                "marks": part.get("marks"),
                "question_type": part.get("question_type") or part.get("type"),
                "answer_mode": part.get("answer_mode"),
                "handwritten_upload_mode": part.get("handwritten_upload_mode"),
                "answer_choices": part.get("answer_choices") or part.get("options") or [],
                "correct_answer": part.get("correct_answer"),
                "diagram_reference": part.get("diagram_reference"),
                "assets": part.get("assets") or [],
                "raw_part": part,
            }
        )
    return result
