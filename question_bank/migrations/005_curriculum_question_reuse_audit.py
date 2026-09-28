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
from collections import Counter
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

        for table, required in REQUIRED_LEGACY_COLUMNS.items():
            if table not in tables:
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
            report["students"]["expected_enrollment_inserts"] = report["students"]["eligible_registration_rows"]

        if "questions" in tables and not report["schema"]["missing_columns"].get("questions"):
            rows = db.execute(text("""
                SELECT question_id, subject, board, class_level, chapter
                FROM questions
                WHERE board IS NOT NULL AND class_level IS NOT NULL AND chapter IS NOT NULL
            """)).mappings().all()

            official = set()
            for c in data["curricula"]:
                for u in c["units"]:
                    for ch in u["chapters"]:
                        official.add((
                            c["board"], int(c["class_level"]), c["subject_id"],
                            c["subject_code"], ch["official_chapter_name"]
                        ))

            # The migration joins subject_catalog by subject_name. Mirror that behavior.
            subject_ids_by_name = {
                s["name"]: s["subject_id"] for s in data["subjects"]
            }
            exact = []
            unmatched = Counter()
            for r in rows:
                sid = subject_ids_by_name.get(r["subject"])
                key = (r["board"], int(r["class_level"]), sid, None, r["chapter"])
                if sid and any(
                    x[0] == key[0] and x[1] == key[1] and x[2] == key[2] and x[4] == key[4]
                    for x in official
                ):
                    exact.append(dict(r))
                else:
                    unmatched[(r["board"], int(r["class_level"]), r["subject"], r["chapter"])] += 1

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
    for r in report["students"].get("by_curriculum", []):
        print(f"  {r['board']} {r['class_level']} {r['subject']}: {r['count']}")
    print()
    print("Question mapping backfill")
    print("-------------------------")
    print(f"Eligible question rows: {report['questions'].get('eligible_rows', 0)}")
    print(f"Exact mappings predicted: {report['questions'].get('exact_mapping_rows', 0)}")
    print(f"Unmatched question rows: {report['questions'].get('unmatched_rows', 0)}")
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
