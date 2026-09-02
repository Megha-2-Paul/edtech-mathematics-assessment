"""V1.2.1 diagnostic artifacts for suspicious PDF page layouts.

This module is diagnostic-only. It does not change question-boundary detection,
CBSE page routing, question ordering, merging, OCR, or database behavior.
It records marker coordinates and nearby text-language signals and renders
annotated copies of suspicious source pages for human inspection.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

import fitz

from question_bank.extraction.question_boundary import (
    LEFT_MARKER_TOLERANCE_PT,
    LEFT_MARGIN_RATIO,
    QUESTION_INLINE_RE,
    QUESTION_RE,
    _candidate_markers,
    _question_markers,
)


def _language_signal(page: fitz.Page, marker_y: float, marker_x: float) -> dict[str, Any]:
    """Return a local, non-authoritative language signal near a marker."""
    words = page.get_text("words") or []
    window_top = max(0.0, marker_y - 3.0)
    window_bottom = marker_y + 55.0
    nearby = [
        str(word[4]).strip()
        for word in words
        if window_top <= float(word[1]) <= window_bottom
        and float(word[0]) >= marker_x
    ]
    devanagari_count = sum(bool(re.search(r"[\u0900-\u097F]", word)) for word in nearby)
    latin_count = sum(bool(re.search(r"[A-Za-z]", word)) for word in nearby)
    if devanagari_count and latin_count:
        signal = "mixed_or_unknown"
    elif devanagari_count:
        signal = "devanagari_present"
    elif latin_count:
        signal = "english_signal_present"
    else:
        signal = "no_language_signal"
    return {
        "nearby_word_count": len(nearby),
        "devanagari_word_count": devanagari_count,
        "latin_word_count": latin_count,
        "signal": signal,
    }


def diagnose_page(
    pdf_path: str | Path,
    page_number: int,
    output_dir: str | Path,
    dpi: int = 180,
) -> dict[str, Any]:
    """Diagnose candidate/accepted question markers on one suspicious page."""
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    annotated_path = output_dir / f"page_{page_number:02d}_annotated.png"

    with fitz.open(str(pdf_path)) as document:
        page = document[page_number - 1]
        candidates = _candidate_markers(page)
        accepted = _question_markers(page)
        accepted_keys = {(number, round(y0, 1)) for number, y0 in accepted}
        marker_x = min((x0 for _number, _y0, x0 in candidates), default=None)

        rows: list[dict[str, Any]] = []
        for number, y0, x0 in candidates:
            is_accepted = (number, round(y0, 1)) in accepted_keys
            signal = _language_signal(page, y0, x0)
            rows.append(
                {
                    "pdf": pdf_path.name,
                    "page": page_number,
                    "question_number": number,
                    "x0": round(x0, 2),
                    "y0": round(y0, 2),
                    "accepted_by_v1_1": is_accepted,
                    "marker_x_reference": round(marker_x, 2) if marker_x is not None else "",
                    "left_margin_limit": round(page.rect.width * LEFT_MARGIN_RATIO, 2),
                    "marker_tolerance_pt": LEFT_MARKER_TOLERANCE_PT,
                    "nearby_word_count": signal["nearby_word_count"],
                    "devanagari_word_count": signal["devanagari_word_count"],
                    "latin_word_count": signal["latin_word_count"],
                    "nearby_text_language_signal": signal["signal"],
                }
            )

        # Draw diagnostics only on the in-memory page. The source PDF is never saved.
        for row in rows:
            rect = fitz.Rect(
                row["x0"] - 2,
                row["y0"] - 2,
                row["x0"] + 42,
                row["y0"] + 13,
            )
            page.draw_rect(rect, width=1.2, color=(0, 0.6, 0) if row["accepted_by_v1_1"] else (0.8, 0, 0))
            label = f"Q{row['question_number']} {'A' if row['accepted_by_v1_1'] else 'C'} x={row['x0']:.0f} y={row['y0']:.0f}"
            page.insert_text(
                fitz.Point(max(0, row["x0"]), max(10, row["y0"] - 4)),
                label,
                fontsize=7,
                color=(0, 0.45, 0) if row["accepted_by_v1_1"] else (0.7, 0, 0),
            )

        pix = page.get_pixmap(dpi=dpi, alpha=False)
        pix.save(str(annotated_path))

    return {
        "pdf": pdf_path.name,
        "page": page_number,
        "candidate_count": len(candidates),
        "accepted_count": len(accepted),
        "annotated_path": str(annotated_path),
        "markers": rows,
    }


def write_layout_diagnostics(
    reports: list[dict[str, Any]],
    output_root: str | Path,
) -> tuple[Path, Path]:
    """Write JSON and CSV marker diagnostics."""
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "marker_diagnostics.json"
    csv_path = output_root / "marker_diagnostics.csv"

    json_path.write_text(json.dumps(reports, indent=2), encoding="utf-8")
    rows = [marker for report in reports for marker in report["markers"]]
    fields = [
        "pdf", "page", "question_number", "x0", "y0", "accepted_by_v1_1",
        "marker_x_reference", "left_margin_limit", "marker_tolerance_pt",
        "nearby_word_count", "devanagari_word_count", "latin_word_count",
        "nearby_text_language_signal",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return json_path, csv_path
