"""Batch benchmark for CBSE question-boundary extraction.

This tool scans all PDFs in a directory, applies the existing CBSE Board Paper
agent, detects top-level questions on English pages, and writes a JSON/CSV
review report. It reports *suspected* boundary problems; it does not claim
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
from question_bank.extraction.question_boundary import detect_question_boundaries
from question_bank.extraction.question_continuation import review_document_sequences


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


def benchmark_pdf(pdf_path: Path) -> dict[str, Any]:
    """Benchmark one PDF and return a JSON-serializable report."""
    agent = CBSEBoardPaperAgent()
    result = agent.analyze(str(pdf_path))

    page_rows: list[dict[str, Any]] = []
    english_pages: list[tuple[int, list[int]]] = []
    asset_count = 0

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

    for row in page_rows:
        if row["question_count"]:
            # Asset counting is intentionally deferred to the crop stage. V1.1
            # focuses on boundary quality and does not reinterpret diagrams.
            continue

    detected_numbers = [n for _, numbers in english_pages for n in numbers]
    unique_numbers = sorted(set(detected_numbers))

    return {
        "pdf": pdf_path.name,
        "document_type": result.document_type,
        "agent_confidence": result.confidence,
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


def write_reports(reports: list[dict[str, Any]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "boundary_benchmark.json"
    csv_path = output_dir / "boundary_page_review.csv"

    json_path.write_text(json.dumps(reports, indent=2), encoding="utf-8")

    rows: list[dict[str, Any]] = []
    for report in reports:
        reviews_by_page = {review["page"]: review for review in report["sequence_reviews"]}
        for page in report["pages"]:
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
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["pdf", "page"])
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "pdf_count": len(reports),
        "total_english_pages": sum(r["english_page_count"] for r in reports),
        "total_detected_markers": sum(r["detected_question_marker_count"] for r in reports),
        "total_suspicious_pages": sum(r["suspicious_page_count"] for r in reports),
        "pdfs_with_suspicious_pages": [r["pdf"] for r in reports if r["suspicious_page_count"]],
    }
    (output_dir / "boundary_benchmark_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    print(json.dumps(summary, indent=2))
    print(f"Detailed JSON: {json_path}")
    print(f"Page review CSV: {csv_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark CBSE question-boundary extraction")
    parser.add_argument("--source-dir", default="source_pdfs", type=Path)
    parser.add_argument("--output-dir", default="extraction_benchmark", type=Path)
    args = parser.parse_args()

    pdfs = sorted(args.source_dir.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDF files found in {args.source_dir}")

    reports: list[dict[str, Any]] = []
    for pdf_path in pdfs:
        try:
            report = benchmark_pdf(pdf_path)
            reports.append(report)
            print(
                f"{pdf_path.name}: {report['detected_question_marker_count']} markers, "
                f"{report['suspicious_page_count']} suspicious pages"
            )
        except Exception as exc:
            reports.append({
                "pdf": pdf_path.name,
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
            })
            print(f"{pdf_path.name}: ERROR: {exc}")

    write_reports(reports, args.output_dir)


if __name__ == "__main__":
    main()
