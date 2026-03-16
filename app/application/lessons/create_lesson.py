import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.lessons.aggregate import Lesson
from app.infrastructure.repositories.lesson_repo import LessonRepository
from app.hyperstate.response import HyperStateResponse, ActorContext
from app.hyperstate.flash import Flash
from app.projection.lessons.detail import LessonDetailProjection


class CreateLesson:
    def __init__(self, session: AsyncSession):
        self.repo = LessonRepository(session)
        self.session = session

    async def create_lesson_entity(
        self,
        subject_id: str,
        student_id: str,
        title: str,
        description: str | None,
        scheduled_date: date | None,
        time_slot: str,
    ) -> Lesson:
        lesson_id = f"LES-{uuid.uuid4().hex[:6].upper()}"
        lesson = Lesson.create(
            id=lesson_id,
            subject_id=subject_id,
            student_id=student_id,
            title=title,
            description=description,
            scheduled_date=scheduled_date,
            time_slot=time_slot,
        )
        await self.repo.save(lesson)
        return lesson

    async def execute(
        self,
        subject_id: str,
        student_id: str,
        title: str,
        description: str | None,
        scheduled_date: date | None,
        time_slot: str,
        actor: ActorContext,
    ) -> HyperStateResponse:
        lesson = await self.create_lesson_entity(
            subject_id=subject_id,
            student_id=student_id,
            title=title,
            description=description,
            scheduled_date=scheduled_date,
            time_slot=time_slot,
        )
        await self.session.commit()

        return LessonDetailProjection(lesson, actor).build(
            flash=Flash(type="success", title="Lesson Created", body=f"'{title}' has been scheduled.")
        )
