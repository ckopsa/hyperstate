from app.domain.errors import DomainError


class StudentError(DomainError):
    """Base for domain-level student errors."""
    pass


class StudentNotFound(DomainError):
    def __init__(self, student_id: str):
        self.student_id = student_id
        super().__init__(f"Student {student_id} not found")
