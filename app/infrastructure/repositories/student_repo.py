from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.students.aggregate import Student
from app.infrastructure.models.student_model import StudentRow


class StudentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, student_id: str) -> Student | None:
        row = await self.session.get(StudentRow, student_id)
        if row is None:
            return None
        return self._to_domain(row)

    async def list_all(self) -> list[Student]:
        stmt = select(StudentRow).order_by(StudentRow.name)
        rows = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]

    async def save(self, student: Student) -> None:
        row = await self.session.get(StudentRow, student.id)
        if row is None:
            row = StudentRow(id=student.id)
            self.session.add(row)
        row.name = student.name
        row.grade_level = student.grade_level
        row.enrollment_date = student.enrollment_date
        await self.session.flush()

    def _to_domain(self, row: StudentRow) -> Student:
        return Student(
            id=row.id,
            name=row.name,
            grade_level=row.grade_level,
            enrollment_date=row.enrollment_date,
        )
