"""V1.2 visual QA artifacts for question-boundary extraction.

This module does not interpret question content or change detected boundaries.
It renders source pages/question crops and writes a human-review manifest plus
an HTML index for quick visual inspection.
"""
from __future__ import annotations

import csv
import html
from pathlib import Path
from typing import Any

import fitz

from question_bank.extraction.page_renderer import render_page
from question_bank.extraction.question_cropper import extract_page_questions
from question_bank.extraction.question_continuation import review_document_sequences


def _review_priority(review: dict[str, Any], boundaries: list[dict[str, Any]]) -> str:
    """Return HIGH for pages with structural or boundary-review signals."""
    if review.get("severity") != "ok":
        return "HIGH"
    if any(
        asset
        for boundary in boundaries
        for asset in boundary.get("assets", [])
    ):
        return "NORMAL"
    return "NORMAL"


def _safe_pdf_dir(pdf_name: str) -> str:
    return Path(pdf_name).stem.replace(" ", "_")


def generate_visual_review(
    pdf_path: str | Path,
    english_pages: list[tuple[int, list[int]]],
    sequence_reviews: list[dict[str, Any]],
    output_root: str | Path,
    dpi: int = 180,
) -> dict[str, Any]:
    """Render all detected question crops and review-priority source pages."""
    pdf_path = Path(pdf_path)
    output_root = Path(output_root)
    pdf_output = output_root / _safe_pdf_dir(pdf_path.name)
    pdf_output.mkdir(parents=True, exist_ok=True)

    reviews_by_page = {review["page"]: review for review in sequence_reviews}
    manifest_rows: list[dict[str, Any]] = []
    page_rows: list[dict[str, Any]] = []

    with fitz.open(str(pdf_path)) as document:
        for page_number, expected_numbers in english_pages:
            review = reviews_by_page.get(page_number, {})
            page_dir = pdf_output / f"page_{page_number:02d}"
            boundaries = extract_page_questions(
                pdf_path,
                page_number,
                page_dir,
                dpi=dpi,
            )

            priority = _review_priority(review, boundaries)
            full_page_path = ""
            if priority == "HIGH":
                full_page = pdf_output / f"page_{page_number:02d}_full.png"
                render_page(document[page_number - 1], full_page, dpi=dpi)
                full_page_path = str(full_page)

            page_rows.append(
                {
                    "pdf": pdf_path.name,
                    "page": page_number,
                    "question_numbers": expected_numbers,
                    "question_count": len(expected_numbers),
                    "severity": review.get("severity", "unknown"),
                    "issues": review.get("issues", []),
                    "review_priority": priority,
                    "full_page_path": full_page_path,
                }
            )

            detected_by_number = {item["question_number"]: item for item in boundaries}
            for question_number in expected_numbers:
                item = detected_by_number.get(question_number)
                if item is None:
                    manifest_rows.append(
                        {
                            "pdf": pdf_path.name,
                            "page": page_number,
                            "question_number": question_number,
                            "bbox_x0": "",
                            "bbox_y0": "",
                            "bbox_x1": "",
                            "bbox_y1": "",
                            "confidence": "",
                            "sequence_status": review.get("severity", "unknown"),
                            "issues": ";".join(review.get("issues", [])),
                            "review_priority": "HIGH",
                            "crop_path": "",
                            "continuation_flag": "possible_continuation"
                            if "no_top_level_question_marker" in review.get("issues", [])
                            else "",
                            "human_status": "PENDING",
                        }
                    )
                    continue

                bbox = item["bbox"]
                manifest_rows.append(
                    {
                        "pdf": pdf_path.name,
                        "page": page_number,
                        "question_number": question_number,
                        "bbox_x0": bbox[0],
                        "bbox_y0": bbox[1],
                        "bbox_x1": bbox[2],
                        "bbox_y1": bbox[3],
                        "confidence": item["confidence"],
                        "sequence_status": review.get("severity", "unknown"),
                        "issues": ";".join(review.get("issues", [])),
                        "review_priority": priority,
                        "crop_path": str(Path(item["crop_path"]).relative_to(output_root)),
                        "continuation_flag": "possible_continuation"
                        if "no_top_level_question_marker" in review.get("issues", [])
                        else "",
                        "human_status": "PENDING",
                    }
                )

    return {
        "pdf": pdf_path.name,
        "question_crop_count": sum(
            1 for row in manifest_rows if row["crop_path"]
        ),
        "high_priority_page_count": sum(
            1 for row in page_rows if row["review_priority"] == "HIGH"
        ),
        "manifest_rows": manifest_rows,
        "page_rows": page_rows,
        "output_dir": str(pdf_output),
    }


def write_visual_review_index(
    visual_reports: list[dict[str, Any]],
    output_root: str | Path,
) -> Path:
    """Write a simple browser-based review index for all benchmark artifacts."""
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    index_path = output_root / "visual_review_index.html"

    parts = [
        "<!doctype html>",
        "<html><head><meta charset='utf-8'><title>V1.2 Visual Review</title>",
        "<style>body{font-family:Arial,sans-serif;margin:24px}"
        "table{border-collapse:collapse;width:100%}"
        "th,td{border:1px solid #ccc;padding:6px;text-align:left;vertical-align:top}"
        "img{max-width:360px;max-height:260px;border:1px solid #ddd}"
        ".high{font-weight:bold}</style></head><body>",
        "<h1>V1.2 Visual Boundary Review</h1>",
        "<p>Artifacts are source-derived renders. Human status is initially PENDING. "
        "This page does not modify or auto-correct boundaries.</p>",
    ]

    for report in visual_reports:
        parts.append(f"<h2>{html.escape(report['pdf'])}</h2>")
        parts.append("<table><tr><th>Page</th><th>Questions</th><th>Priority</th>"
                     "<th>Issues</th><th>Source page</th><th>Question crops</th></tr>")
        for page in report["page_rows"]:
            priority_class = " class='high'" if page["review_priority"] == "HIGH" else ""
            full_page = ""
            if page["full_page_path"]:
                relative = Path(page["full_page_path"]).relative_to(output_root)
                rel = relative.as_posix()
                full_page = f"<a href='{html.escape(rel)}'><img src='{html.escape(rel)}'></a>"
            crops = []
            for row in report["manifest_rows"]:
                if row["page"] != page["page"] or not row["crop_path"]:
                    continue
                rel = Path(row["crop_path"]).as_posix()
                crops.append(
                    f"<div><strong>Q{row['question_number']}</strong><br>"
                    f"<a href='{html.escape(rel)}'><img src='{html.escape(rel)}'></a></div>"
                )
            crop_html = "<div style='display:flex;flex-wrap:wrap;gap:12px'>" + "".join(crops) + "</div>"
            parts.append(
                f"<tr{priority_class}><td>{page['page']}</td>"
                f"<td>{html.escape(','.join(map(str, page['question_numbers'])))}</td>"
                f"<td>{html.escape(page['review_priority'])}</td>"
                f"<td>{html.escape(';'.join(page['issues']))}</td>"
                f"<td>{full_page}</td><td>{crop_html}</td></tr>"
            )
        parts.append("</table>")

    parts.append("</body></html>")
    index_path.write_text("\n".join(parts), encoding="utf-8")
    return index_path


def write_visual_review_manifests(
    visual_reports: list[dict[str, Any]],
    output_root: str | Path,
) -> tuple[Path, Path]:
    """Write CSV manifests for question-level and page-level visual review."""
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    question_csv = output_root / "visual_review_manifest.csv"
    page_csv = output_root / "visual_review_pages.csv"

    question_rows = [row for report in visual_reports for row in report["manifest_rows"]]
    page_rows = [row for report in visual_reports for row in report["page_rows"]]

    question_fields = [
        "pdf", "page", "question_number", "bbox_x0", "bbox_y0", "bbox_x1", "bbox_y1",
        "confidence", "sequence_status", "issues", "review_priority", "crop_path",
        "continuation_flag", "human_status",
    ]
    with question_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=question_fields)
        writer.writeheader()
        writer.writerows(question_rows)

    page_fields = [
        "pdf", "page", "question_numbers", "question_count", "severity", "issues",
        "review_priority", "full_page_path",
    ]
    with page_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=page_fields)
        writer.writeheader()
        for row in page_rows:
            row = dict(row)
            row["question_numbers"] = ",".join(map(str, row["question_numbers"]))
            row["issues"] = ";".join(row["issues"])
            writer.writerow(row)

    return question_csv, page_csv
