from __future__ import annotations
import os

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.repositories.portfolio_photo_repo import PortfolioPhotoRepository


from app.domain.errors import DomainError


class PhotoNotFound(DomainError):
    def __init__(self, photo_id: str):
        self.photo_id = photo_id
        super().__init__(f"Photo {photo_id} not found")


class DeletePhoto:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def execute(self, photo_id: str) -> str:
        """Delete a photo, return its lesson_id."""
        repo = PortfolioPhotoRepository(self.session)
        photo = await repo.get(photo_id)
        if photo is None:
            raise PhotoNotFound(photo_id)

        lesson_id = photo.lesson_id

        # Remove file from disk
        if os.path.exists(photo.file_path):
            os.remove(photo.file_path)

        await repo.delete(photo_id)
        await self.session.commit()

        return lesson_id
