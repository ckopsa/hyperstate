from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.lessons.entities import PortfolioPhoto
from app.infrastructure.models.portfolio_photo_model import PortfolioPhotoRow


class PortfolioPhotoRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, photo_id: str) -> PortfolioPhoto | None:
        row = await self.session.get(PortfolioPhotoRow, photo_id)
        if row is None:
            return None
        return self._to_domain(row)

    async def list_by_lesson(self, lesson_id: str) -> list[PortfolioPhoto]:
        stmt = (
            select(PortfolioPhotoRow)
            .where(PortfolioPhotoRow.lesson_id == lesson_id)
            .order_by(PortfolioPhotoRow.uploaded_at.desc())
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]

    async def list_all(self) -> list[PortfolioPhoto]:
        stmt = select(PortfolioPhotoRow).order_by(PortfolioPhotoRow.uploaded_at.desc())
        rows = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]

    async def save(self, photo: PortfolioPhoto) -> None:
        row = await self.session.get(PortfolioPhotoRow, photo.id)
        if row is None:
            row = PortfolioPhotoRow(id=photo.id)
            self.session.add(row)
        row.lesson_id = photo.lesson_id
        row.filename = photo.filename
        row.file_path = photo.file_path
        row.file_size = photo.file_size
        row.mime_type = photo.mime_type
        row.caption = photo.caption
        row.tags = ",".join(photo.tags) if photo.tags else None
        row.uploaded_at = photo.uploaded_at
        await self.session.flush()

    async def delete(self, photo_id: str) -> None:
        row = await self.session.get(PortfolioPhotoRow, photo_id)
        if row:
            await self.session.delete(row)
            await self.session.flush()

    def _to_domain(self, row: PortfolioPhotoRow) -> PortfolioPhoto:
        return PortfolioPhoto(
            id=row.id,
            lesson_id=row.lesson_id,
            filename=row.filename,
            file_path=row.file_path,
            file_size=row.file_size,
            mime_type=row.mime_type,
            caption=row.caption,
            tags=[t.strip() for t in row.tags.split(",") if t.strip()] if row.tags else [],
            uploaded_at=row.uploaded_at,
        )
