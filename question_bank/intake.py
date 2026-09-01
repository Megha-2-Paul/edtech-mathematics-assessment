"""Source-PDF intake and resumable page-job queue helpers.

This module deliberately does not call any external extraction API. It only
registers a source PDF, inspects its page count, and creates one resumable
extraction job per page.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

from database import engine
from sqlalchemy import text


def _source_id(file_path: Path) -> str:
    """Create a stable source ID from the file path and size/mtime."""
    stat = file_path.stat()
    raw = f"{file_path.resolve()}|{stat.st_size}|{stat.st_mtime_ns}".encode("utf-8")
    return "SRC-" + hashlib.sha256(raw).hexdigest()[:24]


def inspect_pdf(file_path: str) -> int:
    """Return the PDF page count without performing extraction."""
    from pypdf import PdfReader

    return len(PdfReader(file_path).pages)


def register_source(
    file_path: str,
    *,
    board: Optional[str] = None,
    class_level: Optional[int] = None,
    subject: Optional[str] = None,
    paper_year: Optional[int] = None,
    paper_set: Optional[str] = None,
    qp_code: Optional[str] = None,
) -> str:
    """Register a source PDF and enqueue exactly one job per page."""
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() != ".pdf":
        raise ValueError("Source file must be a PDF")

    page_count = inspect_pdf(str(path))
    source_id = _source_id(path)

    with engine.begin() as connection:
        connection.execute(
            text(
                """INSERT INTO source_papers
                (source_id, filename, board, class_level, subject, paper_year,
                 paper_set, qp_code, file_path, page_count, status)
                VALUES (:id, :filename, :board, :class_level, :subject,
                        :paper_year, :paper_set, :qp_code, :file_path,
                        :page_count, 'queued')
                ON DUPLICATE KEY UPDATE
                    filename=VALUES(filename), file_path=VALUES(file_path),
                    page_count=VALUES(page_count), updated_at=CURRENT_TIMESTAMP"""
            ),
            {
                "id": source_id,
                "filename": path.name,
                "board": board,
                "class_level": class_level,
                "subject": subject,
                "paper_year": paper_year,
                "paper_set": paper_set,
                "qp_code": qp_code,
                "file_path": str(path),
                "page_count": page_count,
            },
        )

        for page_number in range(1, page_count + 1):
            connection.execute(
                text(
                    """INSERT INTO extraction_jobs
                    (job_id, source_id, page_number, status)
                    VALUES (:job_id, :source_id, :page_number, 'queued')
                    ON DUPLICATE KEY UPDATE source_id=VALUES(source_id)"""
                ),
                {
                    "job_id": f"JOB-{source_id[4:]}-{page_number:04d}",
                    "source_id": source_id,
                    "page_number": page_number,
                },
            )

    return source_id


def queue_summary() -> dict[str, int]:
    """Return counts useful for a future review dashboard/worker."""
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT status, COUNT(*) AS n FROM extraction_jobs GROUP BY status")
        ).all()
    return {row.status: int(row.n) for row in rows}
