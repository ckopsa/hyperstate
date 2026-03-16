from datetime import date

from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.lessons.aggregate import Lesson
from app.domain.lessons.states import LessonState
from app.infrastructure.models.lesson_model import LessonRow

_SLOT_ORDER = {"morning": 0, "afternoon": 1, "evening": 2}


class LessonRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, lesson_id: str) -> Lesson | None:
        row = await self.session.get(LessonRow, lesson_id)
        if row is None:
            return None
        return self._to_domain(row)

    async def list_by_date(self, scheduled_date: date) -> list[Lesson]:
        stmt = (
            select(LessonRow)
            .where(LessonRow.scheduled_date == scheduled_date)
            .order_by(LessonRow.time_slot, LessonRow.title)
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        lessons = [self._to_domain(r) for r in rows]
        lessons.sort(key=lambda l: (_SLOT_ORDER.get(l.time_slot, 99), l.title))
        return lessons

    async def list_recently_completed(self, limit: int = 5) -> list[Lesson]:
        stmt = (
            select(LessonRow)
            .where(LessonRow.state == LessonState.COMPLETED)
            .order_by(LessonRow.completed_at.desc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]

    async def count_instruction_days(self) -> int:
        stmt = select(func.count(distinct(LessonRow.scheduled_date))).where(
            LessonRow.state == LessonState.COMPLETED,
            LessonRow.scheduled_date.is_not(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0

    async def list_all(
        self,
        student_id: str | None = None,
        subject_id: str | None = None,
        state: str | None = None,
    ) -> list[Lesson]:
        stmt = select(LessonRow).order_by(LessonRow.scheduled_date, LessonRow.title)
        if student_id:
            stmt = stmt.where(LessonRow.student_id == student_id)
        if subject_id:
            stmt = stmt.where(LessonRow.subject_id == subject_id)
        if state:
            stmt = stmt.where(LessonRow.state == state)
        rows = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]

    async def save(self, lesson: Lesson) -> None:
        row = await self.session.get(LessonRow, lesson.id)
        if row is None:
            row = LessonRow(id=lesson.id)
            self.session.add(row)
        row.subject_id = lesson.subject_id
        row.student_id = lesson.student_id
        row.title = lesson.title
        row.description = lesson.description
        row.scheduled_date = lesson.scheduled_date
        row.time_slot = lesson.time_slot
        row.state = lesson.state.value
        row.completed_at = lesson.completed_at
        row.completed_by = lesson.completed_by
        await self.session.flush()

    def _to_domain(self, row: LessonRow) -> Lesson:
        return Lesson(
            id=row.id,
            subject_id=row.subject_id,
            student_id=row.student_id,
            title=row.title,
            description=row.description,
            scheduled_date=row.scheduled_date,
            time_slot=row.time_slot,
            state=LessonState(row.state),
            completed_at=row.completed_at,
            completed_by=row.completed_by,
        )
