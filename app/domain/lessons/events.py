from dataclasses import dataclass


@dataclass(frozen=True)
class LessonCreated:
    lesson_id: str
    student_id: str
    subject_id: str


@dataclass(frozen=True)
class LessonStarted:
    lesson_id: str


@dataclass(frozen=True)
class LessonCompleted:
    lesson_id: str


@dataclass(frozen=True)
class LessonReset:
    lesson_id: str
