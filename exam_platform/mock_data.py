from pathlib import Path
from .models import Test, Question, ContentBlock, Student
from .storage import storage
from datetime import datetime
import uuid


def load_mock_data() -> None:
    """Load mock questions and test data"""
    
    # Create mock questions
    questions = [
        # MCQ 1
        Question(
            question_id="Q001",
            question_type="mcq",
            answer_mode="option_selection",
            question_content=[
                ContentBlock("text", "What is 2 + 2?")
            ],
            answer_choices=["A) 3", "B) 4", "C) 5", "D) 6"],
            correct_answer="B",
            marks=1,
            requires_handwritten_upload=False,
        ),
        # MCQ 2
        Question(
            question_id="Q002",
            question_type="mcq",
            answer_mode="option_selection",
            question_content=[
                ContentBlock("text", "What is the square root of 16?")
            ],
            answer_choices=["A) 2", "B) 3", "C) 4", "D) 8"],
            correct_answer="C",
            marks=1,
            requires_handwritten_upload=False,
        ),
        # MCQ 3
        Question(
            question_id="Q003",
            question_type="mcq",
            answer_mode="option_selection",
            question_content=[
                ContentBlock("text", "What is the value of π (pi) approximately?")
            ],
            answer_choices=["A) 2.14", "B) 3.14", "C) 4.14", "D) 5.14"],
            correct_answer="B",
            marks=1,
            requires_handwritten_upload=False,
        ),
        # MCQ 4
        Question(
            question_id="Q004",
            question_type="mcq",
            answer_mode="option_selection",
            question_content=[
                ContentBlock("text", "Solve: 3x = 12")
            ],
            answer_choices=["A) x = 2", "B) x = 3", "C) x = 4", "D) x = 6"],
            correct_answer="C",
            marks=1,
            requires_handwritten_upload=False,
        ),
        # Subjective 1
        Question(
            question_id="Q005",
            question_type="subjective",
            answer_mode="final_answer_selection_and_handwritten_upload",
            question_content=[
                ContentBlock("text", "Solve the quadratic equation: x² - 5x + 6 = 0")
            ],
            answer_choices=["A) x = 2, 3", "B) x = 1, 6", "C) x = 2, 4", "D) x = 3, 4"],
            correct_answer="A",
            marks=4,
            requires_handwritten_upload=True,
        ),
        # Subjective 2
        Question(
            question_id="Q006",
            question_type="subjective",
            answer_mode="final_answer_selection_and_handwritten_upload",
            question_content=[
                ContentBlock("text", "Find the derivative of f(x) = x³ + 2x²")
            ],
            answer_choices=["A) 3x² + 4x", "B) 3x + 4", "C) 2x² + 2x", "D) x² + x"],
            correct_answer="A",
            marks=3,
            requires_handwritten_upload=True,
        ),
        # Subjective 3
        Question(
            question_id="Q007",
            question_type="subjective",
            answer_mode="final_answer_selection_and_handwritten_upload",
            question_content=[
                ContentBlock("text", "Prove that the sum of angles in a triangle is 180°")
            ],
            answer_choices=["A) Proven using parallel lines", "B) Proven using properties", "C) Cannot be proven", "D) Depends on triangle type"],
            correct_answer="A",
            marks=5,
            requires_handwritten_upload=True,
        ),
        # Subjective 4 (requires multiple pages)
        Question(
            question_id="Q008",
            question_type="subjective",
            answer_mode="final_answer_selection_and_handwritten_upload",
            question_content=[
                ContentBlock("text", "Solve the system of equations using any method:\n2x + 3y = 8\n3x + 2y = 7")
            ],
            answer_choices=["A) x = 2, y = 1", "B) x = 1, y = 2", "C) x = 3, y = 1/3", "D) x = 2/3, y = 2"],
            correct_answer="A",
            marks=4,
            requires_handwritten_upload=True,
        ),
    ]
    
    for q in questions:
        storage.create_question(q)
    
    # Create mock test
    test = Test(
        test_id="TEST001",
        title="Mock Mathematics Assessment",
        subject="Mathematics",
        class_level=10,
        duration_minutes=120,
        total_marks=19,
        questions=["Q001", "Q002", "Q003", "Q004", "Q005", "Q006", "Q007", "Q008"],
        status="active"
    )
    storage.create_test(test)
    
    # Create a sample student
    student = Student(
        student_id="STU001",
        name="Student Name",
        email="student@example.com",
        phone="9876543210"
    )
    storage.create_student(student)
