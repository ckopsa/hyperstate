from dataclasses import dataclass


@dataclass(frozen=True)
class StudentCreated:
    student_id: str
    name: str
