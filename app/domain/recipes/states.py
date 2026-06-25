from enum import StrEnum

from app.domain.errors import DomainError


class RecipeState(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


TRANSITIONS: dict[RecipeState, dict[str, RecipeState]] = {
    RecipeState.ACTIVE: {
        "archive": RecipeState.ARCHIVED,
    },
    RecipeState.ARCHIVED: {
        "restore": RecipeState.ACTIVE,
    },
}


def can_transition(current: RecipeState, action: str) -> bool:
    return action in TRANSITIONS.get(current, {})


def next_state(current: RecipeState, action: str) -> RecipeState:
    transitions = TRANSITIONS.get(current, {})
    if action not in transitions:
        raise InvalidTransition(current, action)
    return transitions[action]


class InvalidTransition(DomainError):
    def __init__(self, state: RecipeState, action: str):
        self.state = state
        self.action = action
        super().__init__(f"Cannot '{action}' from state '{state}'")
