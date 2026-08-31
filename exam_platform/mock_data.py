from .models import Test, Question, ContentBlock, Student
from .storage import storage


def load_mock_data() -> None:
    """Load realistic Class 10 Mathematics demo data for UI testing."""

    # These are demonstration questions only. They are intentionally kept
    # separate from the question-bank/extraction pipeline, which is on hold.
    questions = [
        Question(
            question_id="Q001",
            question_type="mcq",
            answer_mode="option_selection",
            question_content=[
                ContentBlock("text", "If the zeroes of the quadratic polynomial x² − 7x + 12 are α and β, then α + β is:")
            ],
            answer_choices=["A) 5", "B) 7", "C) 12", "D) −7"],
            correct_answer="B",
            marks=1,
        ),
        Question(
            question_id="Q002",
            question_type="mcq",
            answer_mode="option_selection",
            question_content=[
                ContentBlock("text", "The value of tan 45° / (1 + tan² 45°) is:")
            ],
            answer_choices=["A) 1/2", "B) 1", "C) 2", "D) 0"],
            correct_answer="A",
            marks=1,
        ),
        Question(
            question_id="Q003",
            question_type="mcq",
            answer_mode="option_selection",
            question_content=[
                ContentBlock("text", "Find the distance between the points A(2, 3) and B(−1, −1).")
            ],
            answer_choices=["A) 4", "B) 5", "C) √13", "D) 6"],
            correct_answer="B",
            marks=1,
        ),
        Question(
            question_id="Q004",
            question_type="mcq",
            answer_mode="option_selection",
            question_content=[
                ContentBlock("text", "Two fair dice are thrown simultaneously. What is the probability of obtaining a sum of 8?")
            ],
            answer_choices=["A) 1/6", "B) 5/36", "C) 1/9", "D) 7/36"],
            correct_answer="B",
            marks=1,
        ),
        Question(
            question_id="Q005",
            question_type="subjective",
            answer_mode="final_answer_selection_and_handwritten_upload",
            question_content=[
                ContentBlock("text", "Solve the quadratic equation x² − 5x + 6 = 0. Show all necessary steps in your handwritten solution and then select the final answer below.")
            ],
            answer_choices=[
                "A) x = 1, 6",
                "B) x = 2, 3",
                "C) x = −2, −3",
                "D) x = 3, 5",
            ],
            correct_answer="B",
            marks=4,
            requires_handwritten_upload=True,
        ),
        Question(
            question_id="Q006",
            question_type="subjective",
            answer_mode="final_answer_selection_and_handwritten_upload",
            question_content=[
                ContentBlock("text", "The first term of an arithmetic progression is 3 and its common difference is 4. Find the 20th term. Show your working and select the final answer.")
            ],
            answer_choices=[
                "A) 75",
                "B) 79",
                "C) 80",
                "D) 83",
            ],
            correct_answer="B",
            marks=3,
            requires_handwritten_upload=True,
        ),
        Question(
            question_id="Q007",
            question_type="subjective",
            answer_mode="final_answer_selection_and_handwritten_upload",
            question_content=[
                ContentBlock("text", "From an external point P, two tangents PA and PB are drawn to a circle with centre O. If PA = 8 cm, find PB. Show the relevant theorem/reasoning in your handwritten solution.")
            ],
            answer_choices=[
                "A) 4 cm",
                "B) 8 cm",
                "C) 16 cm",
                "D) Cannot be determined",
            ],
            correct_answer="B",
            marks=3,
            requires_handwritten_upload=True,
        ),
        Question(
            question_id="Q008",
            question_type="subjective",
            answer_mode="final_answer_selection_and_handwritten_upload",
            question_content=[
                ContentBlock("text", "If sin A = 3/5 and A is an acute angle, find cos A + tan A. Show the calculation in your handwritten solution.")
            ],
            answer_choices=[
                "A) 7/20",
                "B) 31/20",
                "C) 17/20",
                "D) 5/4",
            ],
            correct_answer="B",
            marks=4,
            requires_handwritten_upload=True,
        ),
        Question(
            question_id="Q009",
            question_type="subjective",
            answer_mode="final_answer_selection_and_handwritten_upload",
            question_content=[
                ContentBlock("text", "Solve the pair of linear equations: 2x + 3y = 13 and 3x − 2y = 4. Use any suitable method. This question is intended to test a longer handwritten solution, so upload all pages of your working before selecting the final answer.")
            ],
            answer_choices=[
                "A) x = 2, y = 3",
                "B) x = 3, y = 2",
                "C) x = 1, y = 4",
                "D) x = 4, y = 1",
            ],
            correct_answer="A",
            marks=5,
            requires_handwritten_upload=True,
        ),
    ]

    for question in questions:
        storage.create_question(question)

    test = Test(
        test_id="TEST001",
        title="Class 10 Mathematics — Interface Demo",
        subject="Mathematics",
        class_level=10,
        duration_minutes=45,
        total_marks=sum(q.marks for q in questions),
        questions=[q.question_id for q in questions],
        status="active",
    )
    storage.create_test(test)

    student = Student(
        student_id="STU001",
        name="Demo Student",
        email="student@example.com",
        phone="9876543210",
    )
    storage.create_student(student)
