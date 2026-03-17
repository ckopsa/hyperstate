from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.curricula.errors import CurriculumNotFound
from app.infrastructure.repositories.curriculum_repo import CurriculumRepository
from hyperstate.response import HyperStateResponse, ActorContext
from hyperstate.flash import Flash
from app.projection.curricula.detail import CurriculumDetailProjection


class ReorderCurriculumItems:
    def __init__(self, session: AsyncSession):
        self.repo = CurriculumRepository(session)
        self.session = session

    async def execute(
        self,
        curriculum_id: str,
        item_ids: list[str],
        actor: ActorContext,
    ) -> HyperStateResponse:
        curriculum = await self.repo.get_by_id(curriculum_id)
        if not curriculum:
            raise CurriculumNotFound(curriculum_id)

        curriculum.reorder_items(item_ids)
        await self.repo.save(curriculum)
        await self.session.commit()

        return CurriculumDetailProjection(curriculum, actor).build(
            flash=Flash(type="success", title="Items Reordered", body="Curriculum items have been reordered.")
        )
