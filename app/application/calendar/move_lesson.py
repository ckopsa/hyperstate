from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.lessons.errors import LessonNotFound
from app.infrastructure.repositories.lesson_repo import LessonRepository
from app.hyperstate.response import HyperStateResponse, ActorContext
from app.hyperstate.flash import Flash


class MoveLesson:
    def __init__(self, session: AsyncSession):
        self.repo = LessonRepository(session)
        self.session = session

    async def execute(
        self,
        lesson_id: str,
        target_date: date,
        time_slot: str,
        actor: ActorContext,
        week_start: date,
    ) -> HyperStateResponse:
        lesson = await self.repo.get(lesson_id)
        if lesson is None:
            raise LessonNotFound(lesson_id)

        lesson.scheduled_date = target_date
        lesson.time_slot = time_slot
        await self.repo.save(lesson)
        await self.session.commit()

        from app.projection.calendar.week import CalendarWeekProjection
        from app.infrastructure.repositories.subject_repo import SubjectRepository
        subject_repo = SubjectRepository(self.session)
        subjects = await subject_repo.list_all()
        subject_map = {s.id: s for s in subjects}

        lessons = await self.repo.list_by_date_range(
            week_start,
            date.fromordinal(week_start.toordinal() + 6),
            student_id=lesson.student_id,
        )
        return CalendarWeekProjection(lessons, subject_map, week_start, actor).build(
            flash=Flash(type="success", title="Lesson Moved", body=f"'{lesson.title}' rescheduled to {target_date}.")
        )
