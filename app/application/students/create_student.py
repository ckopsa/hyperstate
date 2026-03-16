import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.students.aggregate import Student
from app.domain.students.errors import StudentNotFound
from app.infrastructure.repositories.student_repo import StudentRepository
from app.hyperstate.response import HyperStateResponse, ActorContext
from app.hyperstate.flash import Flash
from app.projection.students.detail import StudentDetailProjection


class CreateStudent:
    def __init__(self, session: AsyncSession):
        self.repo = StudentRepository(session)
        self.session = session

    async def execute(
        self,
        name: str,
        grade_level: str,
        enrollment_date: date | None,
        actor: ActorContext,
    ) -> HyperStateResponse:
        student_id = f"STU-{uuid.uuid4().hex[:6].upper()}"
        if enrollment_date is None:
            enrollment_date = date.today()

        student = Student.create(
            id=student_id,
            name=name,
            grade_level=grade_level,
            enrollment_date=enrollment_date,
        )
        await self.repo.save(student)
        await self.session.commit()

        return StudentDetailProjection(student, actor).build(
            flash=Flash(type="success", title="Student Added", body=f"{name} has been enrolled.")
        )
