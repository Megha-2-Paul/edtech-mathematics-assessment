#!/usr/bin/env python
"""Read-only audit/dry-run for migration 005.

This command never creates, alters, inserts, updates, or deletes database data.

Usage:
  python question_bank/migrations/005_curriculum_question_reuse_audit.py \
      --database-url <URL> --taxonomy curriculum_taxonomy_2026_27.json
"""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

VERSION = "2026.27.7"
TARGET_TABLES = [
    "subject_catalog",
    "curriculum_catalog",
    "curriculum_units",
    "canonical_concepts",
    "curriculum_chapters",
    "question_curriculum_map",
    "student_subject_enrollments",
]
REQUIRED_LEGACY_COLUMNS = {
    "students": {"student_id", "board", "class_level", "subject", "status"},
    "questions": {"question_id", "subject", "board", "class_level", "chapter"},
}

REQUIRED_TARGET_COLUMNS = {
    "subject_catalog": {"subject_id", "subject_name", "subject_code", "active"},
    "curriculum_catalog": {"curriculum_id", "board", "class_level", "subject_id", "subject_code", "academic_year", "status"},
    "curriculum_units": {"unit_id", "curriculum_id", "unit_order", "unit_name"},
    "canonical_concepts": {"concept_id", "concept_name", "subject_id", "active"},
    "curriculum_chapters": {"curriculum_chapter_id", "unit_id", "chapter_order", "official_chapter_name", "canonical_concept_id", "status"},
    "question_curriculum_map": {"question_id", "curriculum_chapter_id", "compatibility_status", "notes", "reviewed_by", "reviewed_at"},
    "student_subject_enrollments": {"enrollment_id", "student_id", "board", "class_level", "subject_id", "subject_code", "academic_year", "status", "created_at", "updated_at"},
}

def load_taxonomy(path: str) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("taxonomy_version") != VERSION:
        raise ValueError(
            f"Unexpected taxonomy version: {data.get('taxonomy_version')!r}; expected {VERSION!r}"
        )
    return data

def expected_curriculum_counts(data: dict) -> tuple[int, int]:
    curricula = len(data["curricula"])
    chapters = sum(
        len(unit["chapters"])
        for curriculum in data["curricula"]
        for unit in curriculum["units"]
    )
    return curricula, chapters


def subject_context_index(data: dict) -> dict:
    """Map (board, class, display name) to all possible canonical subject IDs."""
    names_by_id = {s["subject_id"]: s["name"] for s in data["subjects"]}
    index = defaultdict(set)
    for curriculum in data["curricula"]:
        subject_id = curriculum["subject_id"]
        name = names_by_id.get(subject_id)
        if name:
            index[(curriculum["board"], int(curriculum["class_level"]), name)].add(subject_id)
    return dict(index)


def resolve_subject_id(index: dict, board: str, class_level: int, subject_name: str):
    """Return a subject ID only when board/class/name identify exactly one subject."""
    candidates = index.get((board, int(class_level), subject_name), set())
    return next(iter(candidates)) if len(candidates) == 1 else None


def expected_enrollment_inserts(db, eligible_rows: int, tables: set, missing_columns: dict):
    """Count eligible active registrations without a matching 2026-27 enrollment."""
    table = "student_subject_enrollments"
    if table not in tables:
        return eligible_rows
    if missing_columns.get(table):
        return None
    return int(db.execute(text("""
        SELECT COUNT(*)
        FROM students s
        WHERE s.status='active'
          AND s.board IS NOT NULL AND s.class_level IS NOT NULL
          AND s.subject IN ('Mathematics','Applied Mathematics')
          AND NOT EXISTS (
              SELECT 1
              FROM student_subject_enrollments e
              WHERE e.student_id=s.student_id
                AND e.board=s.board
                AND e.class_level=s.class_level
                AND e.subject_id=CASE
                    WHEN s.subject='Applied Mathematics' THEN 'applied_mathematics'
                    ELSE 'mathematics'
                END
                AND e.academic_year='2026-27'
          )
    """)).scalar_one())

def audit(url: str, taxonomy_path: str) -> dict:
    data = load_taxonomy(taxonomy_path)
    engine = create_engine(url, pool_pre_ping=True, future=True)
    inspector = inspect(engine)

    report = {
        "taxonomy_version": VERSION,
        "database": {},
        "schema": {"missing_tables": [], "missing_columns": {}},
        "targets": {},
        "students": {},
        "questions": {},
        "exact_matches": [],
    }

    with engine.connect() as db:
        tables = set(inspector.get_table_names())
        report["database"]["tables"] = len(tables)
        report["schema"]["missing_tables"] = sorted(TARGET_TABLES and (set(TARGET_TABLES) - tables))

        for table, required in {**REQUIRED_LEGACY_COLUMNS, **REQUIRED_TARGET_COLUMNS}.items():
            if table not in tables:
                if table in REQUIRED_LEGACY_COLUMNS:
                    report["schema"]["missing_columns"][table] = sorted(required)
                continue
            actual = {c["name"] for c in inspector.get_columns(table)}
            missing = required - actual
            if missing:
                report["schema"]["missing_columns"][table] = sorted(missing)

        for table in TARGET_TABLES:
            if table in tables:
                report["targets"][table] = {
                    "exists": True,
                    "rows": int(db.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar_one()),
                }
            else:
                report["targets"][table] = {"exists": False, "rows": 0}

        if "students" in tables and not report["schema"]["missing_columns"].get("students"):
            rows = db.execute(text("""
                SELECT board, class_level, subject, COUNT(*) AS n
                FROM students
                WHERE status='active' AND board IS NOT NULL AND class_level IS NOT NULL
                  AND subject IN ('Mathematics','Applied Mathematics')
                GROUP BY board, class_level, subject
                ORDER BY board, class_level, subject
            """)).mappings().all()
            report["students"]["eligible_registration_rows"] = int(sum(r["n"] for r in rows))
            report["students"]["by_curriculum"] = [
                {"board": r["board"], "class_level": int(r["class_level"]),
                 "subject": r["subject"], "count": int(r["n"])}
                for r in rows
            ]
            report["students"]["expected_enrollment_inserts"] = expected_enrollment_inserts(
                db,
                report["students"]["eligible_registration_rows"],
                tables,
                report["schema"]["missing_columns"],
            )

        if "questions" in tables and not report["schema"]["missing_columns"].get("questions"):
            rows = db.execute(text("""
                SELECT question_id, subject, board, class_level, chapter
                FROM questions
                WHERE board IS NOT NULL AND class_level IS NOT NULL AND chapter IS NOT NULL
            """)).mappings().all()

            official = {
                (c["board"], int(c["class_level"]), c["subject_id"], ch["official_chapter_name"])
                for c in data["curricula"]
                for u in c["units"]
                for ch in u["chapters"]
            }
            subject_ids_by_context = subject_context_index(data)
            exact = []
            unmatched = Counter()
            ambiguous_subject_contexts = Counter()
            for r in rows:
                context = (r["board"], int(r["class_level"]), r["subject"])
                candidates = subject_ids_by_context.get(context, set())
                sid = resolve_subject_id(
                    subject_ids_by_context, r["board"], int(r["class_level"]), r["subject"]
                )
                if len(candidates) > 1:
                    ambiguous_subject_contexts[context] += 1
                if sid and (context[0], context[1], sid, r["chapter"]) in official:
                    exact.append(dict(r))
                else:
                    unmatched[(r["board"], int(r["class_level"]), r["subject"], r["chapter"])] += 1
            report["questions"]["ambiguous_subject_contexts"] = [
                {"board": k[0], "class_level": k[1], "subject": k[2], "count": n}
                for k, n in sorted(ambiguous_subject_contexts.items(), key=lambda x: str(x[0]))
            ]

            report["questions"]["eligible_rows"] = len(rows)
            report["questions"]["exact_mapping_rows"] = len(exact)
            report["questions"]["unmatched_rows"] = sum(unmatched.values())
            report["questions"]["unmatched_groups"] = [
                {"board": k[0], "class_level": k[1], "subject": k[2],
                 "chapter": k[3], "count": n}
                for k, n in sorted(unmatched.items(), key=lambda x: (-x[1], str(x[0])))
            ]
            report["exact_matches"] = [
                {"question_id": r["question_id"], "subject": r["subject"],
                 "board": r["board"], "class_level": int(r["class_level"]),
                 "chapter": r["chapter"]}
                for r in exact
            ]

    expected_curricula, expected_chapters = expected_curriculum_counts(data)
    report["targets"]["expected_curriculum_catalog_rows"] = expected_curricula
    report["targets"]["expected_curriculum_chapter_rows"] = expected_chapters
    return report

def print_report(report: dict) -> None:
    print("=== AIVEN PRE-MIGRATION / MIGRATION 005 DRY-RUN AUDIT ===")
    print(f"Taxonomy version: {report['taxonomy_version']}")
    print()
    missing = report["schema"]["missing_tables"]
    print("Schema")
    print("------")
    print(f"Missing target tables: {len(missing)}")
    if missing:
        for name in missing:
            print(f"  - {name}")
    if report["schema"]["missing_columns"]:
        print("Missing required legacy columns:")
        for table, cols in report["schema"]["missing_columns"].items():
            print(f"  - {table}: {', '.join(cols)}")
    else:
        print("Required legacy columns: OK")
    print()
    print("Migration targets")
    print("-----------------")
    for name, info in report["targets"].items():
        if isinstance(info, dict) and "exists" in info:
            print(f"{name}: {'EXISTS' if info['exists'] else 'NOT EXISTS'}; rows={info['rows']}")
    print(f"Expected curriculum_catalog rows: {report['targets']['expected_curriculum_catalog_rows']}")
    print(f"Expected curriculum_chapters rows: {report['targets']['expected_curriculum_chapter_rows']}")
    print()
    print("Student enrollment backfill")
    print("---------------------------")
    print(f"Eligible legacy registrations: {report['students'].get('eligible_registration_rows', 0)}")
    expected_inserts = report["students"].get("expected_enrollment_inserts")
    if expected_inserts is None:
        print("Expected new enrollment inserts: UNAVAILABLE (enrollment schema incomplete)")
    else:
        print(f"Expected new enrollment inserts: {expected_inserts}")
    for r in report["students"].get("by_curriculum", []):
        print(f"  {r['board']} {r['class_level']} {r['subject']}: {r['count']}")
    print()
    print("Question mapping backfill")
    print("-------------------------")
    print(f"Eligible question rows: {report['questions'].get('eligible_rows', 0)}")
    print(f"Exact mappings predicted: {report['questions'].get('exact_mapping_rows', 0)}")
    print(f"Unmatched question rows: {report['questions'].get('unmatched_rows', 0)}")
    if report["questions"].get("ambiguous_subject_contexts"):
        print("Ambiguous board/class/subject contexts (not mapped):")
        for r in report["questions"]["ambiguous_subject_contexts"]:
            print(f"  {r['board']} {r['class_level']} {r['subject']}: {r['count']}")
    if report["questions"].get("unmatched_groups"):
        print("Largest unmatched groups:")
        for r in report["questions"]["unmatched_groups"][:25]:
            print(f"  {r['board']} {r['class_level']} {r['subject']} | {r['chapter']} : {r['count']}")
    print()
    print("SAFETY: This audit is read-only. No schema or data changes were made.")

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    p.add_argument("--taxonomy", default="curriculum_taxonomy_2026_27.json")
    p.add_argument("--json-out", help="Optional path for machine-readable audit output.")
    args = p.parse_args()
    if not args.database_url:
        p.error("No database URL supplied.")
    report = audit(args.database_url, args.taxonomy)
    print_report(report)
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

if __name__ == "__main__":
    main()
