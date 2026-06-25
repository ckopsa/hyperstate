from datetime import date
from enum import StrEnum


class Theme(StrEnum):
    ITALIAN = "italian"
    MEXICAN = "mexican"
    AMERICAN = "american"
    ASIAN = "asian"
    PIZZA = "pizza"
    BBQ = "bbq"
    ROTATING = "rotating"


# Keyed by date.weekday(): Monday == 0 ... Sunday == 6.
WEEKDAY_THEMES: dict[int, Theme] = {
    0: Theme.ITALIAN,   # Monday
    1: Theme.MEXICAN,   # Tuesday
    2: Theme.AMERICAN,  # Wednesday
    3: Theme.ASIAN,     # Thursday
    4: Theme.PIZZA,     # Friday
    5: Theme.BBQ,       # Saturday
    6: Theme.ROTATING,  # Sunday
}


def theme_for(day: date) -> Theme:
    """Return the dinner Theme assigned to the weekday of ``day``."""
    return WEEKDAY_THEMES[day.weekday()]
