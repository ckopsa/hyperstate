from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class CreateLesson:
    lesson_id: str
    subject_id: str
    student_id: str
    title: str
    description: str | None = None
    scheduled_date: date | None = None
    time_slot: str = "morning"


@dataclass(frozen=True)
class StartLesson:
    lesson_id: str


@dataclass(frozen=True)
class CompleteLesson:
    lesson_id: str
    completed_by: str | None = None


@dataclass(frozen=True)
class ResetLesson:
    lesson_id: str
