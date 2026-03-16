from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.repositories.lesson_repo import LessonRepository
from app.hyperstate.response import HyperStateResponse, ActorContext
from app.hyperstate.flash import Flash


class ShiftWeek:
    def __init__(self, session: AsyncSession):
        self.repo = LessonRepository(session)
        self.session = session

    async def execute(
        self,
        week_start: date,
        direction: str,
        days: int,
        student_id: str | None,
        actor: ActorContext,
    ) -> HyperStateResponse:
        week_end = date.fromordinal(week_start.toordinal() + 6)
        lessons = await self.repo.list_by_date_range(week_start, week_end, student_id=student_id)

        delta = timedelta(days=days) if direction == "forward" else timedelta(days=-days)
        for lesson in lessons:
            if lesson.scheduled_date is not None:
                lesson.scheduled_date = lesson.scheduled_date + delta
            await self.repo.save(lesson)

        await self.session.commit()

        # Reload lessons for the same week
        lessons = await self.repo.list_by_date_range(week_start, week_end, student_id=student_id)

        from app.projection.calendar.week import CalendarWeekProjection
        from app.infrastructure.repositories.subject_repo import SubjectRepository
        subject_repo = SubjectRepository(self.session)
        subjects = await subject_repo.list_all()
        subject_map = {s.id: s for s in subjects}

        moved_count = len(lessons)
        direction_label = "forward" if direction == "forward" else "backward"
        return CalendarWeekProjection(lessons, subject_map, week_start, actor).build(
            flash=Flash(
                type="success",
                title="Week Shifted",
                body=f"{moved_count} lessons moved {direction_label} by {days} day(s).",
            )
        )
