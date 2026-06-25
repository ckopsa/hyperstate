from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.weekplan.aggregate import WeekPlan
from app.domain.weekplan.errors import WeekPlanError, WeekPlanNotFound
from app.infrastructure.repositories.weekplan_repo import WeekPlanRepository

# Lifecycle transitions a plan can be driven through. Each maps 1:1 to an
# aggregate method of the same name, so the use case is generic.
_ACTIONS = {"finalize", "start_shopping", "finish_shopping", "complete", "reopen"}


class TransitionWeekPlan:
    """Generic use case for week-plan lifecycle transitions."""

    def __init__(self, session: AsyncSession):
        self.repo = WeekPlanRepository(session)
        self.session = session

    async def execute(self, week_plan_id: str, action: str) -> WeekPlan:
        if action not in _ACTIONS:
            raise WeekPlanError(f"Unknown week-plan action: {action}")
        plan = await self.repo.get(week_plan_id)
        if plan is None:
            raise WeekPlanNotFound(week_plan_id)
        getattr(plan, action)()
        await self.repo.save(plan)
        await self.session.commit()
        return plan
