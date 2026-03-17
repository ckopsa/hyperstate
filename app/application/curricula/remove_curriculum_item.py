from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.curricula.errors import CurriculumNotFound
from app.infrastructure.repositories.curriculum_repo import CurriculumRepository
from hyperstate.response import HyperStateResponse, ActorContext
from hyperstate.flash import Flash
from app.projection.curricula.detail import CurriculumDetailProjection


class RemoveCurriculumItem:
    def __init__(self, session: AsyncSession):
        self.repo = CurriculumRepository(session)
        self.session = session

    async def execute(
        self,
        curriculum_id: str,
        item_id: str,
        actor: ActorContext,
    ) -> HyperStateResponse:
        curriculum = await self.repo.get_by_id(curriculum_id)
        if not curriculum:
            raise CurriculumNotFound(curriculum_id)

        curriculum.remove_item(item_id)
        await self.repo.save(curriculum)
        await self.session.commit()

        return CurriculumDetailProjection(curriculum, actor).build(
            flash=Flash(type="success", title="Item Removed", body="Item removed from curriculum.")
        )
