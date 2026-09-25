"""Single canonical builder from normalized ingestion records to production questions."""

from __future__ import annotations

from typing import Any

from exam_platform.models import ContentBlock, Question
from .models import IngestionCandidate, NormalizedQuestion


QUESTION_TYPE_ALIASES = {
    "mcq": "mcq",
    "multiple_choice": "mcq",
    "multiple_choice_question": "mcq",
    "very_short": "vsaq",
    "very_short_answer": "vsaq",
    "vsaq": "vsaq",
    "short": "saq",
    "short_answer": "saq",
    "saq": "saq",
    "long": "laq",
    "long_answer": "laq",
    "laq": "laq",
    "subjective": "saq",
}


def normalize_question_type(value: Any) -> str:
    """Normalize transport/source labels without silently changing unsupported types."""
    key = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if key not in QUESTION_TYPE_ALIASES:
        raise ValueError(
            f"Unsupported question type {value!r}. "
            f"Supported canonical types: mcq, vsaq, saq, laq."
        )
    return QUESTION_TYPE_ALIASES[key]


def _content_blocks(question: NormalizedQuestion) -> list[ContentBlock]:
    blocks = [ContentBlock("text", question.question_text)]

    for part in question.metadata.get("question_parts") or []:
        if not isinstance(part, dict):
            continue
        value = str(
            part.get("part_text") or part.get("text") or part.get("question_text") or ""
        ).strip()
        if value:
            blocks.append(ContentBlock("text", value, metadata={"question_part": part}))

    diagram_reference = question.metadata.get("diagram_reference")
    if diagram_reference:
        blocks.append(
            ContentBlock(
                "image",
                str(diagram_reference),
                metadata={"source_reference": str(diagram_reference)},
            )
        )

    for asset in question.assets:
        if isinstance(asset, dict):
            reference = (
                asset.get("asset_id")
                or asset.get("reference")
                or asset.get("name")
                or asset.get("path")
            )
            metadata = {"source_asset_reference": reference}
        else:
            reference = asset
            metadata = {"source_asset_reference": reference}
        if reference:
            blocks.append(ContentBlock("image", str(reference), metadata=metadata))

    return blocks


def build_question(
    question: NormalizedQuestion,
    *,
    question_id: str,
    verification_status: str = "VERIFIED",
) -> Question:
    """Build the one canonical production Question object used by all publishers."""
    return Question(
        question_id=question_id,
        question_type=normalize_question_type(question.question_type),
        answer_mode=str(question.answer_mode or "").strip(),
        question_content=_content_blocks(question),
        answer_choices=[
            f"{choice.get('label')}) {choice.get('text')}"
            if isinstance(choice, dict) and choice.get("label")
            else str(choice.get("text") or choice.get("value") or "")
            if isinstance(choice, dict)
            else str(choice)
            for choice in question.answer_choices
        ],
        correct_answer=question.correct_answer,
        marks=question.marks,
        handwritten_upload_mode=question.handwritten_upload_mode,
        subject=question.subject,
        board=question.board,
        class_level=question.class_level,
        chapter=question.chapter,
        topic=question.topic,
        subtopic=question.subtopic,
        difficulty=question.difficulty,
        competency=question.competency,
        source=question.source,
        source_year=question.source_year,
        status="active",
        source_type=question.source_type,
        verification_status=verification_status,
        canonical_question_id=question_id,
    )


def build_question_from_candidate(
    candidate: IngestionCandidate,
    *,
    question_id: str,
) -> Question:
    return build_question(
        candidate.question,
        question_id=question_id,
        verification_status="VERIFIED",
    )


def solution_payload(question: NormalizedQuestion) -> dict[str, Any] | None:
    """Return solution/marking data without forcing it into the core Question row."""
    metadata = question.metadata
    solution = metadata.get("solution")
    marking_scheme = metadata.get("marking_scheme")

    if solution in (None, "") and marking_scheme in (None, ""):
        return None

    return {
        "solution": solution,
        "marking_scheme": marking_scheme,
        "source_type": question.source_type,
        "verified": True,
    }
