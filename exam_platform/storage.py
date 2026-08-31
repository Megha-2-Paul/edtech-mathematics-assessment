import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from .models import (
    Test, Question, Student, Attempt, Response, AnswerImage,
    ContentBlock
)


class InMemoryStorage:
    """Simple in-memory storage for MVP"""
    
    def __init__(self):
        self.tests: Dict[str, Test] = {}
        self.questions: Dict[str, Question] = {}
        self.students: Dict[str, Student] = {}
        self.attempts: Dict[str, Attempt] = {}
        self.responses: Dict[str, Response] = {}
        self.images: Dict[str, AnswerImage] = {}

    def create_test(self, test: Test) -> None:
        self.tests[test.test_id] = test

    def get_test(self, test_id: str) -> Optional[Test]:
        return self.tests.get(test_id)

    def create_question(self, question: Question) -> None:
        self.questions[question.question_id] = question

    def get_question(self, question_id: str) -> Optional[Question]:
        return self.questions.get(question_id)

    def get_questions(self, question_ids: List[str]) -> List[Question]:
        return [self.questions[qid] for qid in question_ids if qid in self.questions]

    def create_student(self, student: Student) -> None:
        self.students[student.student_id] = student

    def get_student(self, student_id: str) -> Optional[Student]:
        return self.students.get(student_id)

    def create_attempt(self, attempt: Attempt) -> None:
        self.attempts[attempt.attempt_id] = attempt

    def get_attempt(self, attempt_id: str) -> Optional[Attempt]:
        return self.attempts.get(attempt_id)

    def update_attempt(self, attempt: Attempt) -> None:
        self.attempts[attempt.attempt_id] = attempt

    def create_response(self, response: Response) -> None:
        self.responses[response.response_id] = response

    def get_response(self, attempt_id: str, question_id: str) -> Optional[Response]:
        for resp in self.responses.values():
            if resp.attempt_id == attempt_id and resp.question_id == question_id:
                return resp
        return None

    def get_attempt_responses(self, attempt_id: str) -> List[Response]:
        return [r for r in self.responses.values() if r.attempt_id == attempt_id]

    def update_response(self, response: Response) -> None:
        self.responses[response.response_id] = response

    def create_image(self, image: AnswerImage) -> None:
        self.images[image.image_id] = image

    def get_attempt_images(self, attempt_id: str, question_id: str) -> List[AnswerImage]:
        return sorted(
            [img for img in self.images.values() 
             if img.attempt_id == attempt_id and img.question_id == question_id],
            key=lambda x: x.page_number
        )


# Global storage instance
storage = InMemoryStorage()
