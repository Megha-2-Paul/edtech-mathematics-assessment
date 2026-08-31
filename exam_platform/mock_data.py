from .models import Test, Question, ContentBlock, Student
from .storage import storage


def load_mock_data() -> None:
    """Load realistic Class 10 Mathematics demo data for UI testing."""
    questions = [
        Question("Q001", "mcq", "option_selection", [ContentBlock("text", "If the zeroes of the quadratic polynomial x² − 7x + 12 are α and β, then α + β is:")], ["A) 5", "B) 7", "C) 12", "D) −7"], "B", 1),
        Question("Q002", "mcq", "option_selection", [ContentBlock("text", "The value of tan 45° / (1 + tan² 45°) is:")], ["A) 1/2", "B) 1", "C) 2", "D) 0"], "A", 1),
        Question("Q003", "mcq", "option_selection", [ContentBlock("text", "Find the distance between the points A(2, 3) and B(−1, −1).")], ["A) 4", "B) 5", "C) √13", "D) 6"], "B", 1),
        Question("Q004", "mcq", "option_selection", [ContentBlock("text", "Two fair dice are thrown simultaneously. What is the probability of obtaining a sum of 8?")], ["A) 1/6", "B) 5/36", "C) 1/9", "D) 7/36"], "B", 1),
        Question("Q005", "subjective", "final_answer_selection_and_handwritten_upload", [ContentBlock("text", "Solve the quadratic equation x² − 5x + 6 = 0. Show all necessary steps in your handwritten solution and then select the final answer below.")], ["A) x = 1, 6", "B) x = 2, 3", "C) x = −2, −3", "D) x = 3, 5"], "B", 4, "required"),
        Question("Q006", "subjective", "final_answer_selection_and_handwritten_upload", [ContentBlock("text", "The first term of an arithmetic progression is 3 and its common difference is 4. Find the 20th term. Show your working and select the final answer.")], ["A) 75", "B) 79", "C) 80", "D) 83"], "B", 3, "optional"),
        Question("Q007", "subjective", "final_answer_selection_and_handwritten_upload", [ContentBlock("text", "From an external point P, two tangents PA and PB are drawn to a circle with centre O. If PA = 8 cm, find PB. Show the relevant theorem/reasoning in your handwritten solution.")], ["A) 4 cm", "B) 8 cm", "C) 16 cm", "D) Cannot be determined"], "B", 3, "optional"),
        Question("Q008", "subjective", "final_answer_selection_and_handwritten_upload", [ContentBlock("text", "If sin A = 3/5 and A is an acute angle, find cos A + tan A. Show the calculation in your handwritten solution.")], ["A) 7/20", "B) 31/20", "C) 17/20", "D) 5/4"], "B", 4, "required"),
        Question("Q009", "subjective", "final_answer_selection_and_handwritten_upload", [ContentBlock("text", "Solve the pair of linear equations: 2x + 3y = 13 and 3x − 2y = 4. Use any suitable method. Upload all pages of your working before selecting the final answer.")], ["A) x = 2, y = 3", "B) x = 3, y = 2", "C) x = 1, y = 4", "D) x = 4, y = 1"], "A", 5, "required"),
    ]
    for question in questions:
        storage.create_question(question)
    test = Test("TEST001", "Class 10 Mathematics — Interface Demo", "Mathematics", 10, 45, sum(q.marks for q in questions), [q.question_id for q in questions], "active")
    storage.create_test(test)
    storage.create_student(Student("STU001", "Demo Student", "student@example.com", "9876543210"))
