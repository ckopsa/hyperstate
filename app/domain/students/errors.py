class StudentError(Exception):
    """Base for domain-level student errors."""
    pass


class StudentNotFound(Exception):
    def __init__(self, student_id: str):
        self.student_id = student_id
        super().__init__(f"Student {student_id} not found")
