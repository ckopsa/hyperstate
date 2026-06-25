from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.weekplan.aggregate import WeekPlan
from app.domain.weekplan.errors import WeekPlanError
from app.infrastructure.repositories.weekplan_repo import WeekPlanRepository


class CreateWeekPlan:
    def __init__(self, session: AsyncSession):
        self.repo = WeekPlanRepository(session)
        self.session = session

    async def execute(self, week_start: date) -> WeekPlan:
        # One plan per week: reject a duplicate up front so the natural-key
        # collision surfaces as a domain error rather than a DB integrity error.
        existing = await self.repo.get_by_week_start(week_start)
        if existing is not None:
            raise WeekPlanError(
                f"A week plan already exists for the week of {week_start.isoformat()}."
            )
        plan = WeekPlan.create(week_start=week_start)
        await self.repo.save(plan)
        await self.session.commit()
        return plan
