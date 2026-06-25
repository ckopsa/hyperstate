from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.weekplan.aggregate import WeekPlan
from app.domain.weekplan.errors import WeekPlanNotFound
from app.infrastructure.repositories.weekplan_repo import WeekPlanRepository


class ClearDinner:
    def __init__(self, session: AsyncSession):
        self.repo = WeekPlanRepository(session)
        self.session = session

    async def execute(self, week_plan_id: str, slot_date: date) -> WeekPlan:
        plan = await self.repo.get(week_plan_id)
        if plan is None:
            raise WeekPlanNotFound(week_plan_id)
        plan.clear_dinner(slot_date)
        await self.repo.save(plan)
        await self.session.commit()
        return plan
