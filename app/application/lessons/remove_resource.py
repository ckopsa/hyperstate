from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.lessons.errors import LessonNotFound
from hyperstate.response import HyperStateResponse, ActorContext
from hyperstate.flash import Flash
from app.infrastructure.repositories.lesson_repo import LessonRepository
from app.projection.lessons.detail import LessonDetailProjection


class RemoveResource:
    def __init__(self, session: AsyncSession):
        self.repo = LessonRepository(session)
        self.session = session

    async def execute(
        self,
        lesson_id: str,
        resource_id: str,
        actor: ActorContext,
    ) -> HyperStateResponse:
        lesson = await self.repo.get(lesson_id)
        if lesson is None:
            raise LessonNotFound(lesson_id)

        lesson.remove_resource(resource_id)
        await self.repo.save(lesson)
        await self.session.commit()

        return LessonDetailProjection(lesson, actor).build(
            flash=Flash(type="success", title="Resource Removed", body="The resource has been removed.")
        )
