from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.subjects.aggregate import Subject
from app.infrastructure.models.subject_model import SubjectRow


class SubjectRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, subject_id: str) -> Subject | None:
        row = await self.session.get(SubjectRow, subject_id)
        if row is None:
            return None
        return self._to_domain(row)

    async def list_all(self) -> list[Subject]:
        stmt = select(SubjectRow).order_by(SubjectRow.name)
        rows = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]

    async def save(self, subject: Subject) -> None:
        row = await self.session.get(SubjectRow, subject.id)
        if row is None:
            row = SubjectRow(id=subject.id)
            self.session.add(row)
        row.name = subject.name
        row.color = subject.color
        row.icon = subject.icon
        row.is_custom = subject.is_custom
        row.description = subject.description
        await self.session.flush()

    async def delete(self, subject_id: str) -> None:
        row = await self.session.get(SubjectRow, subject_id)
        if row is not None:
            await self.session.delete(row)
            await self.session.flush()

    def _to_domain(self, row: SubjectRow) -> Subject:
        return Subject(
            id=row.id,
            name=row.name,
            color=row.color,
            icon=row.icon,
            is_custom=row.is_custom,
            description=row.description,
        )
