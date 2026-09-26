from exam_platform.eligibility import is_test_eligible, registration_required
from exam_platform.models import Student, Test


def student(subject="Mathematics", class_level=12, board="CBSE"):
    return Student(
        student_id="STU001",
        name="Test Student",
        email="student@example.com",
        class_level=class_level,
        board=board,
        subject=subject,
    )


def test_mathematics_student_can_access_matching_test():
    test = Test("T1", "CBSE XII Mathematics", "Mathematics", 12, 60, 80, board="CBSE")
    assert is_test_eligible(student(), test)


def test_applied_mathematics_student_cannot_access_mathematics_test():
    test = Test("T1", "CBSE XII Mathematics", "Mathematics", 12, 60, 80, board="CBSE")
    assert not is_test_eligible(student(subject="Applied Mathematics"), test)


def test_mathematics_student_cannot_access_applied_mathematics_test():
    test = Test("T1", "CBSE XII Applied Mathematics", "Applied Mathematics", 12, 60, 80, board="CBSE")
    assert not is_test_eligible(student(), test)


def test_board_and_class_are_part_of_eligibility():
    test = Test("T1", "CBSE XII Mathematics", "Mathematics", 12, 60, 80, board="CBSE")
    assert not is_test_eligible(student(class_level=11), test)
    assert not is_test_eligible(student(board="ICSE"), test)


def test_unregistered_student_is_not_eligible():
    guest = Student("STU002", "Guest Student", "", subject=None)
    test = Test("T1", "CBSE XII Mathematics", "Mathematics", 12, 60, 80, board="CBSE")
    assert not is_test_eligible(guest, test)
    assert registration_required(guest)
