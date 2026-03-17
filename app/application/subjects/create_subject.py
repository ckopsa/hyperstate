import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.subjects.aggregate import Subject
from app.infrastructure.repositories.subject_repo import SubjectRepository
from hyperstate.response import HyperStateResponse, ActorContext
from hyperstate.flash import Flash
from app.projection.subjects.detail import SubjectDetailProjection


class CreateSubject:
    def __init__(self, session: AsyncSession):
        self.repo = SubjectRepository(session)
        self.session = session

    async def execute(
        self,
        name: str,
        color: str,
        icon: str,
        description: str | None,
        actor: ActorContext,
    ) -> HyperStateResponse:
        subject_id = f"SUB-{uuid.uuid4().hex[:6].upper()}"
        subject = Subject.create(
            id=subject_id,
            name=name,
            color=color,
            icon=icon,
            is_custom=True,
            description=description,
        )
        await self.repo.save(subject)
        await self.session.commit()

        return SubjectDetailProjection(subject, [], actor).build(
            flash=Flash(type="success", title="Subject Created", body=f"{name} has been created.")
        )
