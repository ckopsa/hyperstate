from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime, UTC

from app.domain.shared.aggregate import AggregateRoot
from .states import LessonState, next_state, InvalidTransition, TRANSITIONS
from .errors import LessonError
from .events import LessonCreated, LessonStarted, LessonCompleted, LessonReset


@dataclass(kw_only=True)
class Lesson(AggregateRoot):
    """Aggregate root for a scheduled lesson."""

    id: str
    subject_id: str
    student_id: str
    title: str
    description: str | None = None
    scheduled_date: date | None = None
    time_slot: str = "morning"
    state: LessonState = LessonState.PENDING
    completed_at: datetime | None = None
    completed_by: str | None = None

    @classmethod
    def create(
        cls,
        id: str,
        subject_id: str,
        student_id: str,
        title: str,
        description: str | None = None,
        scheduled_date: date | None = None,
        time_slot: str = "morning",
    ) -> "Lesson":
        if not title.strip():
            raise LessonError("Lesson title cannot be empty.")
        lesson = cls(
            id=id,
            subject_id=subject_id,
            student_id=student_id,
            title=title,
            description=description,
            scheduled_date=scheduled_date,
            time_slot=time_slot,
        )
        lesson._events.append(LessonCreated(lesson_id=id, student_id=student_id, subject_id=subject_id))
        return lesson

    def start(self) -> None:
        """Transition pending → in_progress."""
        self._transition("start")
        self._events.append(LessonStarted(lesson_id=self.id))

    def complete(self, completed_by: str | None = None) -> None:
        """Transition in_progress → completed."""
        self._transition("complete")
        self.completed_at = datetime.now(UTC)
        self.completed_by = completed_by
        self._events.append(LessonCompleted(lesson_id=self.id))

    def reset(self) -> None:
        """Transition in_progress|completed → pending."""
        self._transition("reset")
        self.completed_at = None
        self.completed_by = None
        self._events.append(LessonReset(lesson_id=self.id))

    def available_actions(self) -> set[str]:
        return set(TRANSITIONS.get(self.state, {}).keys())

    def _transition(self, action: str) -> None:
        self.state = next_state(self.state, action)
