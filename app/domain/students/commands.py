from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class CreateStudent:
    student_id: str
    name: str
    grade_level: str
    enrollment_date: date
