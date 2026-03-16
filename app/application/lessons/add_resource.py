import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.lessons.entities import ResourceType
from app.domain.lessons.errors import LessonNotFound
from app.hyperstate.response import HyperStateResponse, ActorContext
from app.hyperstate.flash import Flash
from app.infrastructure.repositories.lesson_repo import LessonRepository
from app.projection.lessons.detail import LessonDetailProjection


class AddResource:
    def __init__(self, session: AsyncSession):
        self.repo = LessonRepository(session)
        self.session = session

    async def add_resource_to_entity(
        self,
        lesson_id: str,
        resource_type: ResourceType,
        title: str,
        url: str,
    ) -> None:
        lesson = await self.repo.get(lesson_id)
        if lesson is None:
            raise LessonNotFound(lesson_id)

        resource_id = f"RES-{uuid.uuid4().hex[:6].upper()}"
        lesson.add_resource(resource_id, resource_type, title, url)
        await self.repo.save(lesson)

    async def execute(
        self,
        lesson_id: str,
        resource_type: ResourceType,
        title: str,
        url: str,
        actor: ActorContext,
    ) -> HyperStateResponse:
        await self.add_resource_to_entity(
            lesson_id=lesson_id,
            resource_type=resource_type,
            title=title,
            url=url,
        )
        await self.session.commit()

        lesson = await self.repo.get(lesson_id)
        return LessonDetailProjection(lesson, actor).build(
            flash=Flash(type="success", title="Resource Added", body=f"'{title}' has been attached.")
        )
