"""Authoritative inventory of executable schema/data migrations."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Migration:
    migration_id: str
    filename: str
    execution_type: str
    dependencies: tuple[str, ...] = ()

    @property
    def path(self) -> Path:
        return MIGRATIONS_DIR / self.filename

    def checksum(self) -> str:
        return hashlib.sha256(self.path.read_bytes()).hexdigest()


MIGRATIONS = (
    Migration("001_question_bank_foundation", "001_question_bank_foundation.sql", "mysql_client"),
    Migration("002_canonical_question_ingestion", "002_canonical_question_ingestion.sql", "mysql_client",
              ("001_question_bank_foundation",)),
    Migration("003_canonical_math_taxonomy", "003_canonical_math_taxonomy.py", "python"),
    Migration("004_student_registration_subject", "004_student_registration_subject.sql", "mysql"),
    Migration("005_curriculum_question_reuse", "005_curriculum_question_reuse.py", "python",
              ("004_student_registration_subject",)),
    Migration("006_exam_monitoring_mode", "006_exam_monitoring_mode.py", "python"),
    Migration("008_migration_ledger_upgrade", "008_migration_ledger_upgrade.py", "python"),
)


def validate_manifest() -> None:
    ids = [migration.migration_id for migration in MIGRATIONS]
    if len(ids) != len(set(ids)):
        raise ValueError("Migration manifest contains duplicate migration IDs.")
    known = set(ids)
    for migration in MIGRATIONS:
        missing = set(migration.dependencies) - known
        if missing:
            raise ValueError(
                f"{migration.migration_id} has unknown dependencies: {sorted(missing)}"
            )
        if not migration.path.is_file():
            raise FileNotFoundError(migration.path)
