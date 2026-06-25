from enum import StrEnum


class ItemStatus(StrEnum):
    """Where a shopping-list line stands relative to the trip to the store.

    The three statuses are a free toggle, not a workflow: a line can move
    directly between any of them as the cook updates what they have and what
    they have purchased. ``mark_have``/``mark_needed``/``mark_bought`` on the
    aggregate set these directly rather than walking a transition table.
    """

    NEEDED = "needed"   # on the buy list — we must acquire it
    HAVE = "have"       # already in the pantry — drop it from the buy list
    BOUGHT = "bought"   # purchased on this trip — checked off the buy list


# Only NEEDED lines are still outstanding; HAVE and BOUGHT are both "off the
# list" for the purpose of what remains to be bought.
ON_BUY_LIST: frozenset[ItemStatus] = frozenset({ItemStatus.NEEDED})
