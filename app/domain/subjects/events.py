from dataclasses import dataclass


@dataclass(frozen=True)
class SubjectCreated:
    subject_id: str
    name: str
