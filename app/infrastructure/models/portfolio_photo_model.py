from __future__ import annotations
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class PortfolioPhotoRow(Base):
    __tablename__ = "portfolio_photos"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    lesson_id: Mapped[str] = mapped_column(String, ForeignKey("lessons.id"), index=True)
    filename: Mapped[str] = mapped_column(String)
    file_path: Mapped[str] = mapped_column(String)
    file_size: Mapped[int] = mapped_column(Integer)
    mime_type: Mapped[str] = mapped_column(String, default="image/jpeg")
    caption: Mapped[str | None] = mapped_column(String, nullable=True)
    tags: Mapped[str | None] = mapped_column(String, nullable=True)  # comma-separated
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
