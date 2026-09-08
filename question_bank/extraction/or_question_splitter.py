"""Utilities for turning explicit internal-choice (OR) items into separate questions."""
from __future__ import annotations

import re
from typing import Any


def _part_text(part: dict[str, Any]) -> str:
    return str(part.get("part_text") or part.get("text") or "").strip()


def _part_identifier(part: dict[str, Any], index: int) -> str:
    raw = str(part.get("part_identifier") or part.get("identifier") or part.get("label") or "").strip()
    raw = raw.strip("()[] ")
    return raw or chr(ord("a") + index)


def is_explicit_or_question(question_text: str, parts: Any) -> bool:
    """Return True only for a question with multiple explicit alternatives."""
    if not isinstance(parts, list) or len(parts) < 2:
        return False
    dict_parts = [p for p in parts if isinstance(p, dict) and _part_text(p)]
    if len(dict_parts) < 2:
        return False
    text = str(question_text or "")
    has_or_word = bool(re.search(r"\bOR\b", text, flags=re.IGNORECASE))
    identifiers = [_part_identifier(p, i).lower() for i, p in enumerate(dict_parts)]
    has_alternative_labels = len(set(identifiers)) >= 2 and all(len(x) <= 3 for x in identifiers)
    return has_or_word or has_alternative_labels


def split_or_parts(question_text: str, parts: Any) -> list[dict[str, Any]]:
    """Return normalized independent alternatives while preserving source structure."""
    if not is_explicit_or_question(question_text, parts):
        return []
    result: list[dict[str, Any]] = []
    for index, part in enumerate(parts):
        if not isinstance(part, dict):
            continue
        text = _part_text(part)
        if not text:
            continue
        result.append({
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
        })
    return result
