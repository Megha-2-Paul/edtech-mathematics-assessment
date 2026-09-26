"""Canonical curriculum resolver for extracted question metadata.

This resolver is deliberately conservative:
- exact/normalized canonical chapter names only;
- board + class + subject context is required;
- no fuzzy guessing;
- unresolved or ambiguous mappings remain review-required;
- the original extracted chapter label is preserved.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


SUBJECT_ALIASES = {
    "mathematics": "maths",
    "maths": "maths",
    "applied mathematics": "applied_mathematics",
    "applied maths": "applied_mathematics",
}

BOARD_ALIASES = {
    "cbse": "CBSE",
    "icse": "ICSE",
    "isc": "ISC",
}


def normalize_label(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def canonical_subject_id(value: Any) -> str | None:
    key = normalize_label(value)
    return SUBJECT_ALIASES.get(key)


def canonical_board(value: Any) -> str | None:
    key = normalize_label(value)
    return BOARD_ALIASES.get(key)


@dataclass(frozen=True)
class CurriculumMapping:
    status: str
    original_chapter: str | None = None
    canonical_chapter_id: str | None = None
    canonical_chapter_name: str | None = None
    syllabus_unit_id: str | None = None
    syllabus_unit_name: str | None = None
    board: str | None = None
    class_level: int | None = None
    subject_id: str | None = None
    candidates: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    reason: str | None = None


class CanonicalTaxonomyResolver:
    MATCHED = "MATCHED"
    UNRESOLVED = "UNRESOLVED"
    AMBIGUOUS = "AMBIGUOUS"

    def __init__(
        self,
        taxonomy_path: str | Path = "canonical_math_taxonomy_2026_27.json",
        *,
        taxonomy_data: Mapping[str, Any] | None = None,
    ):
        if taxonomy_data is not None:
            self.data = dict(taxonomy_data)
        else:
            path = Path(taxonomy_path)
            self.data = json.loads(path.read_text(encoding="utf-8"))

        self._chapters = {
            row["id"]: row
            for row in self.data.get("canonical_chapters", [])
            if isinstance(row, dict) and row.get("id") and row.get("name")
        }
        self._units = {
            row["unit_id"]: row
            for row in self.data.get("units", [])
            if isinstance(row, dict) and row.get("unit_id")
        }
        self._mappings = [
            row for row in self.data.get("mappings", [])
            if isinstance(row, dict)
        ]

    def resolve(
        self,
        *,
        subject: Any,
        board: Any,
        class_level: Any,
        chapter: Any,
    ) -> CurriculumMapping:
        original = str(chapter).strip() if chapter is not None else None
        subject_id = canonical_subject_id(subject)
        board_name = canonical_board(board)

        try:
            class_number = int(class_level) if class_level is not None else None
        except (TypeError, ValueError):
            class_number = None

        if not original:
            return CurriculumMapping(
                status=self.UNRESOLVED,
                original_chapter=original,
                board=board_name,
                class_level=class_number,
                subject_id=subject_id,
                reason="missing_chapter",
            )

        if not subject_id:
            return CurriculumMapping(
                status=self.UNRESOLVED,
                original_chapter=original,
                board=board_name,
                class_level=class_number,
                reason="unsupported_subject",
            )

        if not board_name or class_number is None:
            return CurriculumMapping(
                status=self.UNRESOLVED,
                original_chapter=original,
                board=board_name,
                class_level=class_number,
                subject_id=subject_id,
                reason="missing_board_or_class",
            )

        candidates: list[dict[str, Any]] = []
        label = normalize_label(original)

        for mapping in self._mappings:
            if normalize_label(mapping.get("board")) != normalize_label(board_name):
                continue
            if mapping.get("class_level") != class_number:
                continue

            unit = self._units.get(mapping.get("unit_id"), {})
            if unit.get("subject_id") != subject_id:
                continue

            chapter = self._chapters.get(mapping.get("canonical_chapter_id"), {})
            if normalize_label(chapter.get("name")) != label:
                continue

            candidates.append({
                "canonical_chapter_id": chapter.get("id"),
                "canonical_chapter_name": chapter.get("name"),
                "syllabus_unit_id": unit.get("unit_id"),
                "syllabus_unit_name": unit.get("unit_name"),
                "chapter_order": mapping.get("chapter_order"),
                "mapping_status": mapping.get("status"),
            })

        if len(candidates) == 1:
            match = candidates[0]
            if match.get("mapping_status") != "VERIFIED":
                return CurriculumMapping(
                    status=self.UNRESOLVED,
                    original_chapter=original,
                    board=board_name,
                    class_level=class_number,
                    subject_id=subject_id,
                    candidates=(match,),
                    reason="taxonomy_mapping_not_verified",
                )
            return CurriculumMapping(
                status=self.MATCHED,
                original_chapter=original,
                canonical_chapter_id=match["canonical_chapter_id"],
                canonical_chapter_name=match["canonical_chapter_name"],
                syllabus_unit_id=match["syllabus_unit_id"],
                syllabus_unit_name=match["syllabus_unit_name"],
                board=board_name,
                class_level=class_number,
                subject_id=subject_id,
                candidates=(match,),
            )

        if not candidates:
            return CurriculumMapping(
                status=self.UNRESOLVED,
                original_chapter=original,
                board=board_name,
                class_level=class_number,
                subject_id=subject_id,
                reason="no_exact_canonical_mapping",
            )

        return CurriculumMapping(
            status=self.AMBIGUOUS,
            original_chapter=original,
            board=board_name,
            class_level=class_number,
            subject_id=subject_id,
            candidates=tuple(candidates),
            reason="multiple_exact_canonical_mappings",
        )
