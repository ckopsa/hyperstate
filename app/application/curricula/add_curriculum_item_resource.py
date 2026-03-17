import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.curricula.entities import CurriculumItemResource
from app.domain.curricula.errors import CurriculumNotFound
from app.infrastructure.repositories.curriculum_repo import CurriculumRepository
from hyperstate.response import HyperStateResponse, ActorContext
from hyperstate.flash import Flash
from app.projection.curricula.detail import CurriculumDetailProjection


class AddCurriculumItemResource:
    def __init__(self, session: AsyncSession):
        self.repo = CurriculumRepository(session)
        self.session = session

    async def execute(
        self,
        curriculum_id: str,
        item_id: str,
        resource_type: str,
        title: str,
        url: str,
        actor: ActorContext,
    ) -> HyperStateResponse:
        curriculum = await self.repo.get_by_id(curriculum_id)
        if not curriculum:
            raise CurriculumNotFound(curriculum_id)

        target_item = None
        for item in curriculum.items:
            if item.id == item_id:
                target_item = item
                break

        if not target_item:
            return CurriculumDetailProjection(curriculum, actor).build(
                flash=Flash(type="error", title="Item Not Found", body="Curriculum item not found.")
            )

        resource_id = f"RES-{uuid.uuid4().hex[:6].upper()}"
        res = CurriculumItemResource(
            id=resource_id,
            item_id=item_id,
            resource_type=resource_type,  # type: ignore
            title=title,
            url=url,
        )

        target_item.resources.append(res)
        await self.repo.save(curriculum)
        await self.session.commit()

        return CurriculumDetailProjection(curriculum, actor).build(
            flash=Flash(type="success", title="Resource Added", body=f"'{title}' resource added.")
        )
