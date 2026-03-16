from __future__ import annotations
from datetime import date, datetime

from sqlalchemy import String, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class LessonRow(Base):
    __tablename__ = "lessons"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    subject_id: Mapped[str] = mapped_column(String, ForeignKey("subjects.id"), index=True)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.id"), index=True)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    time_slot: Mapped[str] = mapped_column(String, default="morning")
    state: Mapped[str] = mapped_column(String, index=True, default="pending")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_by: Mapped[str | None] = mapped_column(String, nullable=True)
