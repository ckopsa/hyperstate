import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.curricula.entities import CurriculumItem
from app.domain.curricula.errors import CurriculumNotFound
from app.infrastructure.repositories.curriculum_repo import CurriculumRepository
from hyperstate.response import HyperStateResponse, ActorContext
from hyperstate.flash import Flash
from app.projection.curricula.detail import CurriculumDetailProjection


class AddCurriculumItem:
    def __init__(self, session: AsyncSession):
        self.repo = CurriculumRepository(session)
        self.session = session

    async def execute(
        self,
        curriculum_id: str,
        subject_id: str,
        title: str,
        description: str | None,
        day_offset: int | None,
        actor: ActorContext,
    ) -> HyperStateResponse:
        curriculum = await self.repo.get_by_id(curriculum_id)
        if not curriculum:
            raise CurriculumNotFound(curriculum_id)

        item_id = f"CUI-{uuid.uuid4().hex[:6].upper()}"
        item = CurriculumItem(
            id=item_id,
            curriculum_id=curriculum_id,
            sequence=len(curriculum.items) + 1,
            subject_id=subject_id,
            title=title,
            description=description,
            day_offset=day_offset,
        )

        curriculum.add_item(item)
        await self.repo.save(curriculum)
        await self.session.commit()

        return CurriculumDetailProjection(curriculum, actor).build(
            flash=Flash(type="success", title="Item Added", body=f"'{title}' added to curriculum.")
        )
