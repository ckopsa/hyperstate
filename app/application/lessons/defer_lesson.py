from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.lessons.aggregate import next_weekday
from app.domain.lessons.errors import LessonError, LessonNotFound
from hyperstate.flash import Flash
from hyperstate.response import ActorContext, HyperStateResponse
from app.infrastructure.repositories.lesson_repo import LessonRepository
from app.infrastructure.repositories.subject_repo import SubjectRepository
from app.projection.dashboard.view import DashboardProjection


class DeferLesson:
    """Push a single lesson to tomorrow, cascading subsequent incomplete lessons forward."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = LessonRepository(session)
        self.subject_repo = SubjectRepository(session)

    async def execute(self, lesson_id: str, actor: ActorContext) -> HyperStateResponse:
        lesson = await self.repo.get(lesson_id)
        if lesson is None:
            raise LessonNotFound(lesson_id)

        original_date = lesson.scheduled_date

        try:
            lesson.defer()
        except LessonError as exc:
            return await self._dashboard(actor, Flash(type="error", title="Cannot Defer", body=str(exc)))

        await self.repo.save(lesson)

        # Cascade: shift all other incomplete lessons after original_date one weekday forward
        shifted = 0
        if original_date is not None:
            cascade_lessons = await self.repo.list_incomplete_after_date(original_date)
            for other in cascade_lessons:
                if other.id == lesson_id:
                    continue
                if other.scheduled_date is not None:
                    other.scheduled_date = next_weekday(other.scheduled_date)
                    await self.repo.save(other)
                    shifted += 1

        await self.session.commit()

        flash_body = f"{shifted} other lesson{'s' if shifted != 1 else ''} shifted forward" if shifted else None
        return await self._dashboard(actor, Flash(type="info", title="Pushed to tomorrow", body=flash_body))

    async def _dashboard(self, actor: ActorContext, flash: Flash) -> HyperStateResponse:
        today = date.today()
        today_lessons = await self.repo.list_by_date(today)
        recently_completed = await self.repo.list_recently_completed(5)
        instruction_days = await self.repo.count_instruction_days()
        all_subjects = await self.subject_repo.list_all()
        return DashboardProjection(
            today_lessons=today_lessons,
            recently_completed=recently_completed,
            instruction_days=instruction_days,
            subjects={s.id: s for s in all_subjects},
            actor=actor,
            flash=flash,
        ).build()
