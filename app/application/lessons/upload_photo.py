from __future__ import annotations
import os
import uuid
from datetime import datetime, UTC

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.lessons.entities import PortfolioPhoto
from app.domain.lessons.errors import LessonNotFound
from app.hyperstate.response import ActorContext
from app.infrastructure.repositories.lesson_repo import LessonRepository
from app.infrastructure.repositories.portfolio_photo_repo import PortfolioPhotoRepository

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads", "portfolio")


class UploadPhoto:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def execute(
        self,
        lesson_id: str,
        filename: str,
        file_content: bytes,
        mime_type: str,
        caption: str | None,
        tags: list[str],
        actor: ActorContext,  # noqa: ARG002
    ) -> tuple[PortfolioPhoto, str]:
        """Upload a photo and return (photo, lesson_id)."""
        lesson_repo = LessonRepository(self.session)
        lesson = await lesson_repo.get(lesson_id)
        if lesson is None:
            raise LessonNotFound(lesson_id)

        os.makedirs(UPLOAD_DIR, exist_ok=True)

        photo_id = f"PHOTO-{uuid.uuid4().hex[:8].upper()}"
        ext = os.path.splitext(filename)[1] or ".jpg"
        stored_filename = f"{photo_id}{ext}"
        file_path = os.path.join(UPLOAD_DIR, stored_filename)

        with open(file_path, "wb") as f:
            f.write(file_content)

        photo = PortfolioPhoto(
            id=photo_id,
            lesson_id=lesson_id,
            filename=filename,
            file_path=file_path,
            file_size=len(file_content),
            mime_type=mime_type,
            caption=caption or None,
            tags=tags,
            uploaded_at=datetime.now(UTC),
        )

        photo_repo = PortfolioPhotoRepository(self.session)
        await photo_repo.save(photo)
        await self.session.commit()

        return photo, lesson_id
