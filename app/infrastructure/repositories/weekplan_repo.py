from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.weekplan.aggregate import WeekPlan
from app.domain.weekplan.entities import DinnerSlot
from app.domain.weekplan.states import WeekPlanState
from app.domain.shared.themes import Theme
from app.infrastructure.models.weekplan_model import WeekPlanRow, DinnerSlotRow


class WeekPlanRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, week_plan_id: str) -> WeekPlan | None:
        stmt = (
            select(WeekPlanRow)
            .where(WeekPlanRow.id == week_plan_id)
            .options(selectinload(WeekPlanRow.slots))
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(row) if row is not None else None

    async def get_by_week_start(self, week_start: date) -> WeekPlan | None:
        stmt = (
            select(WeekPlanRow)
            .where(WeekPlanRow.week_start == week_start)
            .options(selectinload(WeekPlanRow.slots))
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(row) if row is not None else None

    async def list_all(self, state: str | None = None) -> list[WeekPlan]:
        stmt = select(WeekPlanRow).options(selectinload(WeekPlanRow.slots))
        if state:
            stmt = stmt.where(WeekPlanRow.state == state)
        stmt = stmt.order_by(WeekPlanRow.week_start.desc())
        rows = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]

    async def save(self, plan: WeekPlan) -> None:
        stmt = (
            select(WeekPlanRow)
            .where(WeekPlanRow.id == plan.id)
            .options(selectinload(WeekPlanRow.slots))
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            row = WeekPlanRow(id=plan.id)
            self.session.add(row)
        row.week_start = plan.week_start
        row.state = plan.state.value

        # Slots are owned wholesale by the plan: replace the whole collection so
        # decide/clear round-trip deterministically. The delete-orphan cascade
        # removes the previous rows on flush.
        row.slots = [
            DinnerSlotRow(
                week_plan_id=plan.id,
                slot_date=slot.date,
                weekday=slot.weekday,
                theme=slot.theme.value,
                recipe_id=slot.recipe_id,
                target_time=slot.target_time,
            )
            for slot in plan.slots
        ]

        await self.session.flush()

    def _to_domain(self, row: WeekPlanRow) -> WeekPlan:
        slots = [
            DinnerSlot(
                date=r.slot_date,
                weekday=r.weekday,
                theme=Theme(r.theme),
                recipe_id=r.recipe_id,
                target_time=r.target_time,
            )
            for r in sorted(row.slots, key=lambda x: x.slot_date)
        ]
        return WeekPlan(
            id=row.id,
            week_start=row.week_start,
            state=WeekPlanState(row.state),
            slots=slots,
        )
