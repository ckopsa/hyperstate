from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.lessons.aggregate import next_weekday
from app.domain.lessons.states import LessonState
from hyperstate.flash import Flash
from hyperstate.response import ActorContext, HyperStateResponse
from app.infrastructure.repositories.lesson_repo import LessonRepository
from app.infrastructure.repositories.subject_repo import SubjectRepository
from app.projection.dashboard.view import DashboardProjection


class DeferAllLessons:
    """Push all of today's incomplete lessons to tomorrow."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = LessonRepository(session)
        self.subject_repo = SubjectRepository(session)

    async def execute(self, actor: ActorContext) -> HyperStateResponse:
        today = date.today()
        today_lessons = await self.repo.list_by_date(today)
        incomplete = [
            lesson for lesson in today_lessons
            if lesson.state != LessonState.COMPLETED
        ]

        deferred = 0
        for lesson in incomplete:
            if lesson.scheduled_date is not None:
                lesson.scheduled_date = next_weekday(lesson.scheduled_date)
                await self.repo.save(lesson)
                deferred += 1

        await self.session.commit()

        updated_today = await self.repo.list_by_date(today)
        recently_completed = await self.repo.list_recently_completed(5)
        instruction_days = await self.repo.count_instruction_days()
        all_subjects = await self.subject_repo.list_all()

        flash_body = f"{deferred} lesson{'s' if deferred != 1 else ''} moved to tomorrow"
        return DashboardProjection(
            today_lessons=updated_today,
            recently_completed=recently_completed,
            instruction_days=instruction_days,
            subjects={s.id: s for s in all_subjects},
            actor=actor,
            flash=Flash(type="info", title="Pushed all to tomorrow", body=flash_body),
        ).build()
