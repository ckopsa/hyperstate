from enum import StrEnum

from app.domain.errors import DomainError


class WeekPlanState(StrEnum):
    PLANNING = "planning"
    PLANNED = "planned"
    SHOPPING = "shopping"
    ACTIVE = "active"
    COMPLETED = "completed"


# Forward path:
#   PLANNING --finalize--> PLANNED --start_shopping--> SHOPPING
#            --finish_shopping--> ACTIVE --complete--> COMPLETED
#
# `reopen` is the escape hatch back to PLANNING so dinners can be re-decided;
# it is available from every state past PLANNING and always lands on PLANNING.
TRANSITIONS: dict[WeekPlanState, dict[str, WeekPlanState]] = {
    WeekPlanState.PLANNING: {
        "finalize": WeekPlanState.PLANNED,
    },
    WeekPlanState.PLANNED: {
        "start_shopping": WeekPlanState.SHOPPING,
        "reopen": WeekPlanState.PLANNING,
    },
    WeekPlanState.SHOPPING: {
        "finish_shopping": WeekPlanState.ACTIVE,
        "reopen": WeekPlanState.PLANNING,
    },
    WeekPlanState.ACTIVE: {
        "complete": WeekPlanState.COMPLETED,
        "reopen": WeekPlanState.PLANNING,
    },
    WeekPlanState.COMPLETED: {
        "reopen": WeekPlanState.PLANNING,
    },
}


def can_transition(current: WeekPlanState, action: str) -> bool:
    return action in TRANSITIONS.get(current, {})


def next_state(current: WeekPlanState, action: str) -> WeekPlanState:
    transitions = TRANSITIONS.get(current, {})
    if action not in transitions:
        raise InvalidTransition(current, action)
    return transitions[action]


class InvalidTransition(DomainError):
    def __init__(self, state: WeekPlanState, action: str):
        self.state = state
        self.action = action
        super().__init__(f"Cannot '{action}' from state '{state}'")
