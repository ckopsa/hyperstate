from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.curricula.errors import CurriculumNotFound
from app.infrastructure.repositories.curriculum_repo import CurriculumRepository
from app.hyperstate.response import HyperStateResponse, ActorContext
from app.projection.curricula.item_detail import CurriculumItemDetailProjection
from app.hyperstate.flash import Flash

class RemoveCurriculumItemResource:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CurriculumRepository(db)

    async def execute(
        self,
        curriculum_id: str,
        item_id: str,
        resource_id: str,
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
            raise ValueError(f"Item {item_id} not found in curriculum {curriculum_id}")

        target_item.resources = [res for res in target_item.resources if res.id != resource_id]

        await self.repo.save(curriculum)
        await self.db.commit()

        return CurriculumItemDetailProjection(curriculum, target_item, actor).build(
            flash=Flash(type="success", title="Resource Removed", body="Resource removed successfully.")
        )
