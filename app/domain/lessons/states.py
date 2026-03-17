from enum import StrEnum

from app.domain.errors import DomainError


class LessonState(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


TRANSITIONS: dict[LessonState, dict[str, LessonState]] = {
    LessonState.PENDING: {
        "start": LessonState.IN_PROGRESS,
    },
    LessonState.IN_PROGRESS: {
        "complete": LessonState.COMPLETED,
        "reset": LessonState.PENDING,
    },
    LessonState.COMPLETED: {
        "reset": LessonState.PENDING,
    },
}


def can_transition(current: LessonState, action: str) -> bool:
    return action in TRANSITIONS.get(current, {})


def next_state(current: LessonState, action: str) -> LessonState:
    transitions = TRANSITIONS.get(current, {})
    if action not in transitions:
        raise InvalidTransition(current, action)
    return transitions[action]


class InvalidTransition(DomainError):
    def __init__(self, state: LessonState, action: str):
        self.state = state
        self.action = action
        super().__init__(f"Cannot '{action}' from state '{state}'")
