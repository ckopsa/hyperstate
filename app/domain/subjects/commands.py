from dataclasses import dataclass


@dataclass(frozen=True)
class CreateSubject:
    subject_id: str
    name: str
    color: str
    icon: str
    is_custom: bool = True
    description: str | None = None
