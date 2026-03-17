from app.domain.errors import DomainError


class LessonError(DomainError):
    """Base for domain-level lesson errors."""
    pass


class LessonNotFound(DomainError):
    def __init__(self, lesson_id: str):
        self.lesson_id = lesson_id
        super().__init__(f"Lesson {lesson_id} not found")
