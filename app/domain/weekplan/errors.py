from app.domain.errors import DomainError


class WeekPlanError(DomainError):
    """Base for domain-level week-plan errors."""
    pass


class WeekPlanNotFound(DomainError):
    def __init__(self, week_plan_id: str):
        self.week_plan_id = week_plan_id
        super().__init__(f"WeekPlan {week_plan_id} not found")
