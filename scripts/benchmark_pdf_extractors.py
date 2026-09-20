"""Benchmark MarkItDown against the existing PyMuPDF PDF question extractor.

Usage:
    python scripts/benchmark_pdf_extractors.py path/to/paper.pdf
    python scripts/benchmark_pdf_extractors.py math_question_bank/raw_pdfs/**/*.pdf

This is deliberately a read-only benchmark. It does not modify production
ingestion behavior or publish questions.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

from exam_platform.ingestion.adapters.pdf import extract_pdf_questions
from question_bank.extraction.markitdown_extractor import MarkItDownPDFExtractor


MATH_SYMBOLS = ("²", "³", "√", "∑", "∫", "≤", "≥", "≠", "π", "θ", "α", "β", "∞")


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def benchmark_pdf(path: Path) -> dict:
    source, pymupdf_questions = extract_pdf_questions(
        str(path),
        source_id=f"benchmark-{path.stem}",
        name=path.name,
    )
    markitdown = MarkItDownPDFExtractor().extract(path)

    pymupdf_text = "\n".join(q.raw_text for q in pymupdf_questions)
    md_text = markitdown.text

    return {
        "file": str(path),
        "pages": source.metadata.get("page_count"),
        "pymupdf_question_count": len(pymupdf_questions),
        "pymupdf_text_chars": len(pymupdf_text),
        "pymupdf_mcq_count": sum(bool(q.raw_options) for q in pymupdf_questions),
        "pymupdf_asset_count": sum(len(q.raw_assets) for q in pymupdf_questions),
        "markitdown_text_chars": len(md_text),
        "markitdown_empty": markitdown.is_empty,
        "markitdown_math_symbols": [s for s in MATH_SYMBOLS if s in md_text],
        "pymupdf_math_symbols": [s for s in MATH_SYMBOLS if s in pymupdf_text],
        "normalised_text_overlap": _token_overlap(pymupdf_text, md_text),
    }


def _token_overlap(left: str, right: str) -> float:
    a = set(_normalise(left).split())
    b = set(_normalise(right).split())
    if not a or not b:
        return 0.0
    return round(len(a & b) / len(a | b), 4)


def iter_pdfs(paths: Iterable[str]) -> Iterable[Path]:
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            yield from sorted(path.rglob("*.pdf"))
        elif path.exists() and path.suffix.lower() == ".pdf":
            yield path
        else:
            matches = sorted(Path(".").glob(raw))
            yield from (p for p in matches if p.suffix.lower() == ".pdf")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", help="PDF files, directories, or glob patterns")
    parser.add_argument("--output", default="pdf_extraction_benchmark.json")
    args = parser.parse_args()

    pdfs = list(dict.fromkeys(iter_pdfs(args.paths)))
    if not pdfs:
        raise SystemExit("No PDF files found.")

    results = [benchmark_pdf(path) for path in pdfs]
    output = Path(args.output)
    output.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nWrote benchmark results to {output}")


if __name__ == "__main__":
    main()
