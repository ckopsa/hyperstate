from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class CreateWeekPlan:
    week_start: date


@dataclass(frozen=True)
class DecideDinner:
    week_plan_id: str
    slot_date: date
    recipe_id: str


@dataclass(frozen=True)
class ClearDinner:
    week_plan_id: str
    slot_date: date


@dataclass(frozen=True)
class TransitionWeekPlan:
    week_plan_id: str
    action: str
