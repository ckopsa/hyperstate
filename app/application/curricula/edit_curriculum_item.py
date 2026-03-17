from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.curricula.errors import CurriculumNotFound
from app.infrastructure.repositories.curriculum_repo import CurriculumRepository
from app.hyperstate.response import HyperStateResponse, ActorContext
from app.hyperstate.flash import Flash
from app.projection.curricula.detail import CurriculumDetailProjection


class EditCurriculumItem:
    def __init__(self, session: AsyncSession):
        self.repo = CurriculumRepository(session)
        self.session = session

    async def execute(
        self,
        curriculum_id: str,
        item_id: str,
        title: str,
        subject_id: str,
        description: str | None,
        day_offset: int | None,
        actor: ActorContext,
    ) -> HyperStateResponse:
        curriculum = await self.repo.get_by_id(curriculum_id)
        if not curriculum:
            raise CurriculumNotFound(curriculum_id)

        curriculum.update_item(item_id, title=title, subject_id=subject_id, description=description, day_offset=day_offset)
        await self.repo.save(curriculum)
        await self.session.commit()

        return CurriculumDetailProjection(curriculum, actor).build(
            flash=Flash(type="success", title="Item Updated", body=f"'{title}' has been updated.")
        )
