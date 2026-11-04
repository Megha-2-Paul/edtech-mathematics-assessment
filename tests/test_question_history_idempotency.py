from contextlib import contextmanager
from types import SimpleNamespace

from exam_platform import evaluation


class FakeResult:
    def __init__(self, row=None, values=None):
        self.row = row
        self.values = values or []

    def mappings(self):
        return self

    def one(self):
        return self.row

    def first(self):
        return self.row

    def scalars(self):
        return self

    def all(self):
        return self.values


class FakeConnection:
    def __init__(self):
        self.upserts = []
        self.upsert_sql = None

    def execute(self, statement, params=None):
        sql = str(statement)
        if "COUNT(*) AS attempt_count" in sql:
            return FakeResult(row={
                "attempt_count": 2,
                "correct_count": 1,
                "last_attempted_at": "2026-10-01 10:00:00",
                "last_correct_at": "2026-09-01 10:00:00",
            })
        if "SELECT r.response_id, r.marks_awarded" in sql:
            return FakeResult(row={"response_id": "R2", "marks_awarded": 1})
        if "SELECT error_code FROM evaluation_errors" in sql:
            return FakeResult(values=["C01"])
        if "INSERT INTO question_history" in sql:
            self.upserts.append(params)
            self.upsert_sql = sql
            return FakeResult()
        raise AssertionError(f"Unexpected SQL in test: {sql}")


class FakeEngine:
    def __init__(self):
        self.connection = FakeConnection()

    @contextmanager
    def begin(self):
        yield self.connection


def test_re_evaluating_attempt_writes_absolute_history_counts(monkeypatch):
    engine = FakeEngine()
    monkeypatch.setattr(evaluation, "engine", engine)
    monkeypatch.setattr(
        evaluation.storage, "get_attempt",
        lambda _attempt_id: SimpleNamespace(student_id="STUDENT-1"),
    )
    monkeypatch.setattr(
        evaluation.storage, "get_attempt_responses",
        lambda _attempt_id: [
            SimpleNamespace(question_id="Q1", response_id="R1")
        ],
    )

    evaluation._update_question_history("ATTEMPT-1")
    evaluation._update_question_history("ATTEMPT-1")

    assert len(engine.connection.upserts) == 2
    assert engine.connection.upserts[0] == engine.connection.upserts[1]
    assert engine.connection.upserts[0]["attempt_count"] == 2
    assert engine.connection.upserts[0]["correct_count"] == 1
    assert engine.connection.upserts[0]["last_marks_awarded"] == 1
    assert engine.connection.upserts[0]["last_error_summary"] == "C01"
    assert "attempt_count=:attempt_count" in engine.connection.upsert_sql
    assert "attempt_count=attempt_count+1" not in engine.connection.upsert_sql
