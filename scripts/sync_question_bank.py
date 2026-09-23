"""Pull approved/public question-bank records from cloud into local MySQL.

Usage:
    python scripts/sync_question_bank.py
"""
from __future__ import annotations

from exam_platform.question_bank_sync import sync_questions_from_cloud


def main() -> int:
    result = sync_questions_from_cloud()
    print("Question bank cloud -> local sync complete.")
    print(f"Cloud questions: {result['cloud_questions']}")
    print(f"Inserted locally: {result['inserted']}")
    print(f"Updated locally: {result['updated']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
