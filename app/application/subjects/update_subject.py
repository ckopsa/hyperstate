from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.subjects.errors import SubjectNotFound
from app.infrastructure.repositories.subject_repo import SubjectRepository
from app.infrastructure.repositories.lesson_repo import LessonRepository
from app.hyperstate.response import HyperStateResponse, ActorContext
from app.hyperstate.flash import Flash
from app.projection.subjects.detail import SubjectDetailProjection


class UpdateSubject:
    def __init__(self, session: AsyncSession):
        self.repo = SubjectRepository(session)
        self.lesson_repo = LessonRepository(session)
        self.session = session

    async def execute(
        self,
        subject_id: str,
        name: str,
        color: str,
        icon: str,
        description: str | None,
        actor: ActorContext,
    ) -> HyperStateResponse:
        subject = await self.repo.get(subject_id)
        if subject is None:
            raise SubjectNotFound(subject_id)
        subject.update(name=name, color=color, icon=icon, description=description)
        await self.repo.save(subject)
        await self.session.commit()

        lessons = await self.lesson_repo.list_all(subject_id=subject_id)
        return SubjectDetailProjection(subject, lessons, actor).build(
            flash=Flash(type="success", title="Subject Updated", body=f"{name} has been updated.")
        )
