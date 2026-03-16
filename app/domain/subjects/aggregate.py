from __future__ import annotations
from dataclasses import dataclass

from app.domain.shared.aggregate import AggregateRoot
from .errors import SubjectError
from .events import SubjectCreated


@dataclass(kw_only=True)
class Subject(AggregateRoot):
    """Aggregate root for an academic subject."""

    id: str
    name: str
    color: str
    icon: str
    is_custom: bool
    description: str | None = None

    @classmethod
    def create(
        cls,
        id: str,
        name: str,
        color: str,
        icon: str,
        is_custom: bool = True,
        description: str | None = None,
    ) -> "Subject":
        if not name.strip():
            raise SubjectError("Subject name cannot be empty.")
        subject = cls(id=id, name=name, color=color, icon=icon, is_custom=is_custom, description=description)
        subject._events.append(SubjectCreated(subject_id=id, name=name))
        return subject

    def update(self, name: str, color: str, icon: str, description: str | None) -> None:
        if not name.strip():
            raise SubjectError("Subject name cannot be empty.")
        self.name = name
        self.color = color
        self.icon = icon
        self.description = description
