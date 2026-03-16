from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.subjects.errors import SubjectNotFound
from app.infrastructure.repositories.subject_repo import SubjectRepository
from app.infrastructure.repositories.lesson_repo import LessonRepository
from app.hyperstate.response import HyperStateResponse, ActorContext
from app.hyperstate.flash import Flash
from app.projection.subjects.list import SubjectListProjection


class DeleteSubject:
    def __init__(self, session: AsyncSession):
        self.repo = SubjectRepository(session)
        self.lesson_repo = LessonRepository(session)
        self.session = session

    async def execute(self, subject_id: str, actor: ActorContext) -> HyperStateResponse:
        subject = await self.repo.get(subject_id)
        if subject is None:
            raise SubjectNotFound(subject_id)

        lessons = await self.lesson_repo.list_all(subject_id=subject_id)
        if lessons:
            from app.domain.subjects.errors import SubjectError
            raise SubjectError("Move or delete lessons before deleting this subject.")

        subject_name = subject.name
        await self.repo.delete(subject_id)
        await self.session.commit()

        subjects = await self.repo.list_all()
        return SubjectListProjection(subjects, actor).build(
            flash=Flash(type="success", title="Subject Deleted", body=f"{subject_name} has been deleted.")
        )
