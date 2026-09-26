#!/usr/bin/env python
"""
Improvia canonical mathematics taxonomy migration.

Safe workflow:
  1. Validate only:
       python 003_canonical_math_taxonomy.py --database-url <URL> --taxonomy canonical_math_taxonomy_2026_27.json --dry-run
  2. Apply only after reviewing the dry-run:
       python 003_canonical_math_taxonomy.py --database-url <URL> --taxonomy canonical_math_taxonomy_2026_27.json --apply

The migration is deliberately additive:
- does NOT delete/rename the existing `chapters` table;
- does NOT modify existing questions;
- creates canonical_chapters, syllabus_units and syllabus_chapters;
- records board/class/unit mappings;
- reports existing question chapter values that still need mapping.

Run the same migration independently against local MySQL and Aiven MySQL.
Do not put credentials in command history; load the URL from .env where possible.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from sqlalchemy import (
    Boolean, Column, Integer, MetaData, String, Table, Text,
    UniqueConstraint, create_engine, select, func, inspect
)

SCHEMA_VERSION = "2026.27.4"

def load_taxonomy(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {"taxonomy_version", "subjects", "canonical_chapters", "units", "mappings"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Taxonomy missing keys: {sorted(missing)}")
    return data

def validate_taxonomy(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    chapters = data["canonical_chapters"]
    units = data["units"]
    mappings = data["mappings"]

    chapter_ids = [x["id"] for x in chapters]
    if len(chapter_ids) != len(set(chapter_ids)):
        errors.append("Duplicate canonical chapter IDs.")

    unit_ids = [x["unit_id"] for x in units]
    if len(unit_ids) != len(set(unit_ids)):
        errors.append("Duplicate unit IDs.")

    chapter_set = set(chapter_ids)
    unit_set = set(unit_ids)

    seen = set()
    for m in mappings:
        key = (m["board"], m["class_level"], m["unit_id"], m["canonical_chapter_id"])
        if key in seen:
            errors.append(f"Duplicate mapping: {key}")
        seen.add(key)
        if m["unit_id"] not in unit_set:
            errors.append(f"Mapping references missing unit: {m['unit_id']}")
        if m["canonical_chapter_id"] not in chapter_set:
            errors.append(f"Mapping references missing chapter: {m['canonical_chapter_id']}")

    return errors

def build_tables(metadata: MetaData):
    subjects = Table(
        "canonical_subjects", metadata,
        Column("subject_id", String(50), primary_key=True),
        Column("subject_name", String(150), nullable=False),
        Column("status", String(30), nullable=False),
        Column("taxonomy_version", String(30), nullable=False),
    )

    canonical = Table(
        "canonical_chapters", metadata,
        Column("canonical_chapter_id", String(100), primary_key=True),
        Column("canonical_name", String(150), nullable=False),
        Column("subject_id", String(50), nullable=False),
        Column("active", Boolean, nullable=False, default=True),
        Column("taxonomy_version", String(30), nullable=False),
    )

    units = Table(
        "syllabus_units", metadata,
        Column("unit_id", String(100), primary_key=True),
        Column("board", String(20), nullable=False),
        Column("class_level", Integer, nullable=False),
        Column("subject_id", String(50), nullable=False),
        Column("academic_year", String(20), nullable=False),
        Column("unit_order", Integer, nullable=False),
        Column("unit_name", String(200), nullable=False),
        Column("section", String(10), nullable=True),
        Column("status", String(30), nullable=False),
        Column("taxonomy_version", String(30), nullable=False),
        UniqueConstraint("board", "class_level", "subject_id", "academic_year", "unit_order",
                         name="uq_syllabus_unit_order"),
    )

    syllabus = Table(
        "syllabus_chapters", metadata,
        Column("syllabus_chapter_id", String(140), primary_key=True),
        Column("unit_id", String(100), nullable=False),
        Column("canonical_chapter_id", String(100), nullable=False),
        Column("board", String(20), nullable=False),
        Column("class_level", Integer, nullable=False),
        Column("academic_year", String(20), nullable=False),
        Column("chapter_order", Integer, nullable=False),
        Column("status", String(30), nullable=False),
        Column("taxonomy_version", String(30), nullable=False),
        UniqueConstraint("unit_id", "canonical_chapter_id",
                         name="uq_syllabus_chapter_mapping"),
    )
    return subjects, canonical, units, syllabus

def existing_question_audit(conn) -> dict[str, Any]:
    insp = inspect(conn)
    if "questions" not in insp.get_table_names():
        return {"questions_table": False, "distinct_values": [], "null_count": 0}

    q = Table("questions", MetaData(), autoload_with=conn)
    cols = set(q.c.keys())
    if not {"board", "class_level", "chapter", "question_id"} <= cols:
        return {"questions_table": True, "distinct_values": [], "null_count": None}

    rows = conn.execute(
        select(q.c.board, q.c.class_level, q.c.chapter, func.count(q.c.question_id))
        .group_by(q.c.board, q.c.class_level, q.c.chapter)
        .order_by(q.c.board, q.c.class_level, q.c.chapter)
    ).all()
    return {
        "questions_table": True,
        "distinct_values": [
            {
                "board": r[0], "class_level": r[1],
                "chapter": r[2], "question_count": int(r[3])
            } for r in rows
        ],
        "null_count": sum(
            x["question_count"]
            for x in (
                {"question_count": r[3], "chapter": r[2]}
                for r in rows
            )
            if x["chapter"] is None
        )
    }

def run(url: str, taxonomy_path: Path, apply: bool, allow_review_required: bool = False) -> int:
    data = load_taxonomy(taxonomy_path)
    errors = validate_taxonomy(data)
    if errors:
        print("TAXONOMY VALIDATION: FAIL")
        for e in errors:
            print(" -", e)
        return 2

    engine = create_engine(url)
    metadata = MetaData()
    subjects, canonical, units, syllabus = build_tables(metadata)

    with engine.begin() as conn:
        existing = existing_question_audit(conn)
        print(f"Database dialect: {engine.dialect.name}")
        print(f"Taxonomy version: {data['taxonomy_version']}")
        print(f"Subjects: {len(data['subjects'])}")
        print(f"Canonical chapters: {len(data['canonical_chapters'])}")
        print(f"Syllabus units: {len(data['units'])}")
        print(f"Syllabus mappings: {len(data['mappings'])}")
        print(f"Existing question chapter groups: {len(existing['distinct_values'])}")

        review_units = sum(1 for u in data["units"] if u["status"] == "REVIEW_REQUIRED")
        review_mappings = sum(1 for m in data["mappings"] if m["status"] == "REVIEW_REQUIRED")
        print(f"Review-required units: {review_units}")
        print(f"Review-required mappings: {review_mappings}")

        if not apply:
            print("DRY RUN: no schema or data changes were made.")
            return 0

        # Additive creation only. Existing tables are not dropped or altered.
        metadata.create_all(conn, checkfirst=True)

        academic_year = data["scope"]["academic_year"]

        for row in data["subjects"]:
            exists = conn.execute(
                select(subjects.c.subject_id).where(subjects.c.subject_id == row["subject_id"])
            ).first()
            if exists is None:
                conn.execute(subjects.insert(), [{
                    "subject_id": row["subject_id"],
                    "subject_name": row["name"],
                    "status": row.get("status", "VERIFIED"),
                    "taxonomy_version": data["taxonomy_version"]
                }])

        for row in data["canonical_chapters"]:
            exists = conn.execute(
                select(canonical.c.canonical_chapter_id).where(
                    canonical.c.canonical_chapter_id == row["id"]
                )
            ).first()
            if exists is None:
                conn.execute(canonical.insert(), [{
                    "canonical_chapter_id": row["id"],
                    "canonical_name": row["name"],
                    "subject_id": row.get("subject_id", "maths"),
                    "active": True,
                    "taxonomy_version": data["taxonomy_version"]
                }])

        for row in data["units"]:
            conn.execute(units.insert(), [{
                "unit_id": row["unit_id"],
                "board": row["board"],
                "class_level": row["class_level"],
                "subject_id": row["subject_id"],
                "academic_year": academic_year,
                "unit_order": row["unit_order"],
                "unit_name": row["unit_name"],
                "section": row.get("section"),
                "status": row["status"],
                "taxonomy_version": data["taxonomy_version"]
            }])

        for row in data["mappings"]:
            mapping_id = f"{row['unit_id']}__{row['canonical_chapter_id']}"
            conn.execute(syllabus.insert(), [{
                "syllabus_chapter_id": mapping_id,
                "unit_id": row["unit_id"],
                "canonical_chapter_id": row["canonical_chapter_id"],
                "board": row["board"],
                "class_level": row["class_level"],
                "academic_year": academic_year,
                "chapter_order": row["chapter_order"],
                "status": row["status"],
                "taxonomy_version": data["taxonomy_version"]
            }])

        print("APPLY: canonical taxonomy tables created/populated.")
        print("IMPORTANT: existing questions were NOT modified.")
        return 0

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    p.add_argument("--taxonomy", default="canonical_math_taxonomy_2026_27.json")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--allow-review-required", action="store_true")
    args = p.parse_args()

    if args.dry_run == args.apply:
        p.error("Specify exactly one of --dry-run or --apply.")
    if not args.database_url:
        p.error("No database URL supplied and DATABASE_URL is not set.")

    raise SystemExit(run(
        args.database_url,
        Path(args.taxonomy),
        args.apply,
        args.allow_review_required
    ))