"""Batch benchmark for CBSE question-boundary extraction.

This tool scans all PDFs in a directory, applies the existing CBSE Board Paper
agent, detects top-level questions on English pages, and writes JSON/CSV
review reports. It can also generate V1.2 visual review artifacts and V1.2.1
layout diagnostics for suspicious pages.

The reports identify *suspected* boundary problems; they do not claim
ground-truth accuracy without human comparison to the source PDFs.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import fitz

from question_bank.agents.cbse_board_paper.agent import CBSEBoardPaperAgent
from question_bank.extraction.layout_diagnostics import diagnose_page
from question_bank.extraction.question_boundary import detect_question_boundaries
from question_bank.extraction.question_continuation import review_document_sequences
from question_bank.extraction.visual_review import (
    generate_visual_review,
    write_visual_review_index,
    write_visual_review_manifests,
)


def _page_row(pdf_path: Path, page_number: int, boundaries: list[Any]) -> dict[str, Any]:
    numbers = [int(boundary.question_number) for boundary in boundaries]
    return {
        "pdf": pdf_path.name,
        "page": page_number,
        "question_numbers": numbers,
        "question_count": len(numbers),
        "bbox_count": len(boundaries),
        "max_confidence": max((b.confidence for b in boundaries), default=0.0),
    }


def benchmark_pdf(
    pdf_path: Path,
    visual_output_dir: Path | None = None,
    layout_diagnostics_dir: Path | None = None,
    dpi: int = 180,
) -> dict[str, Any]:
    """Benchmark one PDF and return a JSON-serializable report."""
    agent = CBSEBoardPaperAgent()
    result = agent.analyze(str(pdf_path))
    layout = result.metadata.get("layout", {})

    if not layout.get("validated", False):
        return {
            "pdf": pdf_path.name,
            "status": "manual_review_required",
            "document_type": result.document_type,
            "agent_confidence": result.confidence,
            "layout_validation": layout,
            "english_page_count": 0,
            "pages_with_question_markers": 0,
            "pages_without_question_markers": 0,
            "detected_question_marker_count": 0,
            "unique_question_numbers": [],
            "duplicate_marker_count": 0,
            "suspicious_page_count": 0,
            "pages": [],
            "sequence_reviews": [],
        }

    page_rows: list[dict[str, Any]] = []
    english_pages: list[tuple[int, list[int]]] = []

    with fitz.open(str(pdf_path)) as document:
        for decision in result.pages:
            if decision.routing != "extract":
                continue
            page = document[decision.page - 1]
            boundaries = detect_question_boundaries(page, decision.page)
            row = _page_row(pdf_path, decision.page, boundaries)
            page_rows.append(row)
            english_pages.append((decision.page, row["question_numbers"]))

    reviews = review_document_sequences(english_pages)
    review_rows = [review.to_dict() for review in reviews]
    suspicious_pages = [row for row in review_rows if row["severity"] != "ok"]
    detected_numbers = [n for _, numbers in english_pages for n in numbers]
    unique_numbers = sorted(set(detected_numbers))

    report: dict[str, Any] = {
        "pdf": pdf_path.name,
        "status": "ok" if not suspicious_pages else "review_flags",
        "document_type": result.document_type,
        "agent_confidence": result.confidence,
        "layout_validation": layout,
        "english_page_count": len(english_pages),
        "pages_with_question_markers": sum(bool(numbers) for _, numbers in english_pages),
        "pages_without_question_markers": sum(not numbers for _, numbers in english_pages),
        "detected_question_marker_count": len(detected_numbers),
        "unique_question_numbers": unique_numbers,
        "duplicate_marker_count": len(detected_numbers) - len(unique_numbers),
        "suspicious_page_count": len(suspicious_pages),
        "pages": page_rows,
        "sequence_reviews": review_rows,
    }

    if visual_output_dir is not None:
        visual_report = generate_visual_review(
            pdf_path,
            english_pages,
            review_rows,
            visual_output_dir,
            dpi=dpi,
        )
        report["visual_review"] = {
            "question_crop_count": visual_report["question_crop_count"],
            "high_priority_page_count": visual_report["high_priority_page_count"],
            "output_dir": visual_report["output_dir"],
        }
        report["_visual_report"] = visual_report

    if layout_diagnostics_dir is not None and suspicious_pages:
        pdf_diagnostics_dir = layout_diagnostics_dir / pdf_path.stem.replace(" ", "_")
        diagnostics: list[dict[str, Any]] = []
        for review in suspicious_pages:
            diagnostics.append(
                diagnose_page(
                    pdf_path,
                    review["page"],
                    pdf_diagnostics_dir,
                    dpi=dpi,
                )
            )
        report["layout_diagnostics"] = {
            "page_count": len(diagnostics),
            "output_dir": str(pdf_diagnostics_dir),
            "pages": [item["page"] for item in diagnostics],
        }
        report["_layout_diagnostics"] = diagnostics

    return report


def write_reports(
    reports: list[dict[str, Any]],
    output_dir: Path,
    visual_reports: list[dict[str, Any]] | None = None,
    layout_diagnostics: list[dict[str, Any]] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "boundary_benchmark.json"
    csv_path = output_dir / "boundary_page_review.csv"

    serializable_reports = []
    for report in reports:
        clean = {
            key: value
            for key, value in report.items()
            if key not in {"_visual_report", "_layout_diagnostics"}
        }
        serializable_reports.append(clean)
    json_path.write_text(json.dumps(serializable_reports, indent=2), encoding="utf-8")

    rows: list[dict[str, Any]] = []
    for report in serializable_reports:
        reviews_by_page = {review["page"]: review for review in report.get("sequence_reviews", [])}
        for page in report.get("pages", []):
            review = reviews_by_page.get(page["page"], {})
            rows.append(
                {
                    "pdf": report["pdf"],
                    "page": page["page"],
                    "question_numbers": ",".join(map(str, page["question_numbers"])),
                    "question_count": page["question_count"],
                    "severity": review.get("severity", "unknown"),
                    "issues": ";".join(review.get("issues", [])),
                    "previous_last_question": review.get("previous_last_question"),
                }
            )

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "pdf",
            "page",
            "question_numbers",
            "question_count",
            "severity",
            "issues",
            "previous_last_question",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    valid = [r for r in serializable_reports if r.get("status") in {"ok", "review_flags"}]
    summary = {
        "pdf_count": len(serializable_reports),
        "validated_cbse_pdf_count": len(valid),
        "manual_review_pdf_count": sum(
            r.get("status") == "manual_review_required" for r in serializable_reports
        ),
        "total_english_pages": sum(r.get("english_page_count", 0) for r in valid),
        "total_detected_markers": sum(
            r.get("detected_question_marker_count", 0) for r in valid
        ),
        "total_suspicious_pages": sum(r.get("suspicious_page_count", 0) for r in valid),
        "pdfs_with_suspicious_pages": [
            r["pdf"] for r in valid if r.get("suspicious_page_count", 0)
        ],
        "manual_review_pdfs": [
            r["pdf"]
            for r in serializable_reports
            if r.get("status") == "manual_review_required"
        ],
    }
    if visual_reports is not None:
        summary["visual_review"] = {
            "question_crop_count": sum(r["question_crop_count"] for r in visual_reports),
            "high_priority_page_count": sum(r["high_priority_page_count"] for r in visual_reports),
            "output_dir": str(output_dir / "visual_review"),
            "index": str(output_dir / "visual_review" / "visual_review_index.html"),
        }
    if layout_diagnostics is not None:
        summary["layout_diagnostics"] = {
            "suspicious_page_count": len(layout_diagnostics),
            "output_dir": str(output_dir / "layout_diagnostics"),
            "json": str(output_dir / "layout_diagnostics" / "marker_diagnostics.json"),
            "csv": str(output_dir / "layout_diagnostics" / "marker_diagnostics.csv"),
        }
    (output_dir / "boundary_benchmark_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    if visual_reports is not None:
        visual_root = output_dir / "visual_review"
        write_visual_review_manifests(visual_reports, visual_root)
        write_visual_review_index(visual_reports, visual_root)

    if layout_diagnostics is not None:
        write_layout_diagnostics(
            layout_diagnostics,
            output_dir / "layout_diagnostics",
        )

    print(json.dumps(summary, indent=2))
    print(f"Detailed JSON: {json_path}")
    print(f"Page review CSV: {csv_path}")
    if visual_reports is not None:
        print(f"Visual review index: {output_dir / 'visual_review' / 'visual_review_index.html'}")
    if layout_diagnostics is not None:
        print(f"Layout diagnostics: {output_dir / 'layout_diagnostics'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark CBSE question-boundary extraction")
    parser.add_argument("--source-dir", default="source_pdfs", type=Path)
    parser.add_argument("--output-dir", default="extraction_benchmark", type=Path)
    parser.add_argument("--dpi", default=180, type=int, help="Rendering DPI for visual review artifacts")
    parser.add_argument(
        "--no-visual-review",
        action="store_true",
        help="Skip V1.2 question crops and visual review artifacts",
    )
    parser.add_argument(
        "--no-layout-diagnostics",
        action="store_true",
        help="Skip V1.2.1 diagnostics for suspicious pages",
    )
    args = parser.parse_args()

    pdfs = sorted(args.source_dir.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDF files found in {args.source_dir}")

    reports: list[dict[str, Any]] = []
    visual_reports: list[dict[str, Any]] = []
    layout_diagnostics: list[dict[str, Any]] = []
    visual_output_dir = None if args.no_visual_review else args.output_dir / "visual_review"
    layout_diagnostics_dir = None if args.no_layout_diagnostics else args.output_dir / "layout_diagnostics"

    for pdf_path in pdfs:
        try:
            report = benchmark_pdf(
                pdf_path,
                visual_output_dir=visual_output_dir,
                layout_diagnostics_dir=layout_diagnostics_dir,
                dpi=args.dpi,
            )
            visual_report = report.pop("_visual_report", None)
            diagnostics = report.pop("_layout_diagnostics", None)
            reports.append(report)
            if visual_report is not None:
                visual_reports.append(visual_report)
            if diagnostics is not None:
                layout_diagnostics.extend(diagnostics)
            print(
                f"{pdf_path.name}: status={report['status']}, "
                f"{report['detected_question_marker_count']} markers, "
                f"{report['suspicious_page_count']} suspicious pages"
            )
        except Exception as exc:
            reports.append({
                "pdf": pdf_path.name,
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
            })
            print(f"{pdf_path.name}: ERROR: {exc}")

    write_reports(
        reports,
        args.output_dir,
        visual_reports=None if args.no_visual_review else visual_reports,
        layout_diagnostics=None if args.no_layout_diagnostics else layout_diagnostics,
    )


if __name__ == "__main__":
    main()
