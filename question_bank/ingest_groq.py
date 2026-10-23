"""Local-only Groq PDF extraction proof of concept.

Example:
    python -m question_bank.ingest_groq pdf sample-paper.pdf --max-pages 2

The command never writes to the question database or publishes candidates.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import fitz

from question_bank.extraction.ai_json_bulk_import import AIJSONBulkImporter
from question_bank.extraction.groq_provider import GroqExtractionError, GroqProvider


MAX_PAGE_TEXT_CHARS = 12_000


def extract_pdf_text_pages(path: Path, *, max_pages: int) -> list[tuple[int, str]]:
    """Read a bounded number of pages and retain 1-based source page numbers."""
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError("Input must be a .pdf file.")
    if max_pages < 1:
        raise ValueError("max_pages must be at least 1")

    with fitz.open(path) as document:
        if document.is_encrypted:
            raise ValueError("Encrypted PDFs are not supported by this proof of concept.")
        selected = []
        for page_index in range(min(len(document), max_pages)):
            text = (document[page_index].get_text("text") or "").strip()
            if not text:
                raise ValueError(
                    f"Page {page_index + 1} has no extractable text. "
                    "Scanned/image-only pages need an OCR/vision workflow."
                )
            if len(text) > MAX_PAGE_TEXT_CHARS:
                raise ValueError(
                    f"Page {page_index + 1} has {len(text)} characters, exceeding the "
                    f"safe per-page limit of {MAX_PAGE_TEXT_CHARS}. Reduce or crop the sample."
                )
            selected.append((page_index + 1, text))
        if not selected:
            raise ValueError("PDF has no pages.")
        return selected


def run_extraction(
    pdf_path: Path,
    *,
    output_path: Path,
    max_pages: int,
    board: str | None = None,
    class_level: int | None = None,
    subject: str = "Mathematics",
    provider: GroqProvider | None = None,
) -> dict:
    """Extract, persist local JSON, and validate without publishing."""
    if output_path.exists():
        raise FileExistsError(
            f"Output already exists: {output_path}. Choose a new --output path to avoid overwriting it."
        )
    pages = extract_pdf_text_pages(pdf_path, max_pages=max_pages)
    client = provider or GroqProvider()
    run_id = str(uuid4())
    questions: list[dict] = []

    for page_number, page_text in pages:
        page_payload = client.extract_page(
            page_text,
            source_file=pdf_path.name,
            source_page=page_number,
            board=board,
            class_level=class_level,
            subject=subject,
        )
        questions.extend(page_payload["questions"])

    payload = {
        "schema_version": "1.0",
        "source": {
            "source_type": "pdf",
            "source_file": pdf_path.name,
            "rights_status": "unknown",
        },
        "metadata": {
            "subject": subject,
            "board": board,
            "class_level": class_level,
        },
        "extraction_provider": "groq",
        "extraction_model": client.model,
        "extraction_run_id": run_id,
        "extraction_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "questions": questions,
    }

    # Write only to the explicitly chosen local path; never touch database storage.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    summary = AIJSONBulkImporter(existing_questions=[]).prepare(payload)
    return {
        "output_path": str(output_path),
        "run_id": run_id,
        "pages_processed": len(pages),
        "extracted_questions": len(questions),
        "candidates_total": summary.total,
        "review_required": summary.review_required,
        "validation_pending": summary.validation_pending,
        "duplicates": summary.duplicates,
        "invalid": summary.invalid,
        "publication": "NOT PUBLISHED — human review and rights confirmation required",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract question candidates from a local PDF using Groq.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    pdf_parser = subparsers.add_parser("pdf", help="Extract from a text-based local PDF.")
    pdf_parser.add_argument("pdf_path", type=Path)
    pdf_parser.add_argument("--output", type=Path)
    pdf_parser.add_argument("--max-pages", type=int, default=2)
    pdf_parser.add_argument("--board", choices=("CBSE", "ICSE"))
    pdf_parser.add_argument("--class-level", type=int, choices=(10, 11, 12))
    pdf_parser.add_argument("--subject", default="Mathematics")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "pdf":
        output = args.output or args.pdf_path.with_name(f"{args.pdf_path.stem}.groq_candidates.json")
        try:
            summary = run_extraction(
                args.pdf_path,
                output_path=output,
                max_pages=args.max_pages,
                board=args.board,
                class_level=args.class_level,
                subject=args.subject,
            )
        except (GroqExtractionError, OSError, ValueError) as exc:
            print(f"Extraction failed: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
