from enum import StrEnum


class OrderState(StrEnum):
    DRAFT = "draft"
    PENDING = "pending"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


# Explicit transition table — the single source of truth
TRANSITIONS: dict[OrderState, dict[str, OrderState]] = {
    OrderState.DRAFT: {
        "place": OrderState.PENDING,
    },
    OrderState.PENDING: {
        "ship": OrderState.SHIPPED,
        "cancel": OrderState.CANCELLED,
    },
    OrderState.SHIPPED: {
        "deliver": OrderState.DELIVERED,
        # notably: no "cancel" here
    },
    OrderState.DELIVERED: {},
    OrderState.CANCELLED: {},
}


def can_transition(current: OrderState, action: str) -> bool:
    return action in TRANSITIONS.get(current, {})


def next_state(current: OrderState, action: str) -> OrderState:
    transitions = TRANSITIONS.get(current, {})
    if action not in transitions:
        raise InvalidTransition(current, action)
    return transitions[action]


class InvalidTransition(Exception):
    def __init__(self, state: OrderState, action: str):
        self.state = state
        self.action = action
        super().__init__(f"Cannot '{action}' from state '{state}'")
