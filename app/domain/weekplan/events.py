from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class WeekPlanCreated:
    week_plan_id: str
    week_start: date


@dataclass(frozen=True)
class WeekPlanFinalized:
    week_plan_id: str


@dataclass(frozen=True)
class ShoppingStarted:
    week_plan_id: str


@dataclass(frozen=True)
class ShoppingFinished:
    week_plan_id: str


@dataclass(frozen=True)
class WeekPlanCompleted:
    week_plan_id: str


@dataclass(frozen=True)
class WeekPlanReopened:
    week_plan_id: str
