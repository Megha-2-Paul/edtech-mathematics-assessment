from flask import Flask

from exam_platform import admin as admin_module
from exam_platform.models import ContentBlock, Question
from exam_platform.teacher_csrf import register_teacher_csrf


def _question(question_id, subject, text):
    return Question(
        question_id=question_id,
        question_type="mcq",
        answer_mode="option_selection",
        question_content=[ContentBlock("text", text)],
        answer_choices=["A", "B"],
        correct_answer="A",
        marks=1,
        subject=subject,
        board="CBSE",
        class_level=10,
        chapter="Algebra",
        difficulty="Easy",
    )


def test_teacher_questions_page_renders_subjects_and_preserves_filters(monkeypatch):
    app = Flask(
        __name__,
        template_folder=str(
            admin_module.Path(__file__).resolve().parents[1]
            / "exam_platform"
            / "templates"
        ),
    )
    app.secret_key = "teacher-questions-test-secret"
    admin_module.register_admin(app)
    register_teacher_csrf(app)

    questions = [
        _question("Q-MATH", "Mathematics", "Solve this linear equation."),
        _question("Q-APPLIED", "Applied Mathematics", "Calculate compound interest."),
    ]
    monkeypatch.setattr(
        admin_module.storage,
        "get_all_questions",
        lambda: questions,
    )
    monkeypatch.setattr(
        admin_module.storage,
        "get_subjects",
        lambda: [
            {"name": "Mathematics"},
            {"name": "Applied Mathematics"},
        ],
    )

    response = app.test_client().get(
        "/teacher/questions?subject=Mathematics&q=linear"
    )

    assert response.status_code == 200
    assert b'value="Mathematics" selected' in response.data
    assert b'value="Applied Mathematics"' in response.data
    assert b"Q-MATH" in response.data
    assert b"Q-APPLIED" not in response.data
