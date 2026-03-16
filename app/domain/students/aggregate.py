from __future__ import annotations
from dataclasses import dataclass
from datetime import date

from app.domain.shared.aggregate import AggregateRoot
from .errors import StudentError
from .events import StudentCreated


@dataclass(kw_only=True)
class Student(AggregateRoot):
    """Aggregate root for a student enrolled in homeschool."""

    id: str
    name: str
    grade_level: str
    enrollment_date: date

    @classmethod
    def create(cls, id: str, name: str, grade_level: str, enrollment_date: date) -> "Student":
        if not name.strip():
            raise StudentError("Student name cannot be empty.")
        student = cls(id=id, name=name, grade_level=grade_level, enrollment_date=enrollment_date)
        student._events.append(StudentCreated(student_id=id, name=name))
        return student

    def update(self, name: str, grade_level: str) -> None:
        if not name.strip():
            raise StudentError("Student name cannot be empty.")
        self.name = name
        self.grade_level = grade_level
