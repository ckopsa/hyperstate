from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models.instruction_day_model import InstructionDayRow


class InstructionDayRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, day: date) -> InstructionDayRow | None:
        stmt = select(InstructionDayRow).where(InstructionDayRow.date == day)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_all(self) -> list[InstructionDayRow]:
        stmt = select(InstructionDayRow).order_by(InstructionDayRow.date)
        return list((await self.session.execute(stmt)).scalars().all())

    async def count(self) -> int:
        rows = await self.list_all()
        return len(rows)

    async def ensure_day(
        self,
        day: date,
        *,
        lessons_delta: int = 0,
        subject_name: str | None = None,
    ) -> InstructionDayRow:
        """Upsert an instruction day. Increments lesson count, adds subject if new."""
        row = await self.get(day)
        if row is None:
            row = InstructionDayRow(
                date=day,
                is_manual=False,
                lessons_completed=lessons_delta,
                subjects_covered=subject_name or "",
            )
            self.session.add(row)
        else:
            row.lessons_completed = (row.lessons_completed or 0) + lessons_delta
            if subject_name:
                existing = set(filter(None, (row.subjects_covered or "").split(",")))
                existing.add(subject_name)
                row.subjects_covered = ",".join(sorted(existing))
        await self.session.flush()
        return row

    async def create_manual(self, day: date, notes: str | None) -> InstructionDayRow:
        """Create or update a manually-entered instruction day."""
        row = await self.get(day)
        if row is None:
            row = InstructionDayRow(
                date=day,
                is_manual=True,
                lessons_completed=0,
                subjects_covered="",
                notes=notes,
            )
            self.session.add(row)
        else:
            row.is_manual = True
            row.notes = notes
        await self.session.flush()
        return row
