class SubjectError(Exception):
    """Base for domain-level subject errors."""
    pass


class SubjectNotFound(Exception):
    def __init__(self, subject_id: str):
        self.subject_id = subject_id
        super().__init__(f"Subject {subject_id} not found")
