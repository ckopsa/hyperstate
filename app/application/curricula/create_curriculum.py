import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.curricula.aggregate import Curriculum
from app.infrastructure.repositories.curriculum_repo import CurriculumRepository
from hyperstate.response import HyperStateResponse, ActorContext
from hyperstate.flash import Flash
from app.projection.curricula.detail import CurriculumDetailProjection


class CreateCurriculum:
    def __init__(self, session: AsyncSession):
        self.repo = CurriculumRepository(session)
        self.session = session

    async def execute(
        self,
        name: str,
        description: str | None,
        grade_level: str | None,
        actor: ActorContext,
    ) -> HyperStateResponse:
        curriculum_id = f"CUR-{uuid.uuid4().hex[:6].upper()}"
        curriculum = Curriculum.create(
            id=curriculum_id,
            name=name,
            description=description,
            grade_level=grade_level,
        )
        await self.repo.save(curriculum)
        await self.session.commit()

        return CurriculumDetailProjection(curriculum, actor).build(
            flash=Flash(type="success", title="Curriculum Created", body=f"'{name}' has been created.")
        )
