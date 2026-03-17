from app.domain.errors import DomainError


class SubjectError(DomainError):
    """Base for domain-level subject errors."""
    pass


class SubjectNotFound(DomainError):
    def __init__(self, subject_id: str):
        self.subject_id = subject_id
        super().__init__(f"Subject {subject_id} not found")
