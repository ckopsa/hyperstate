from __future__ import annotations
from datetime import date, datetime

from sqlalchemy import String, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    resources: Mapped[list[LessonResourceRow]] = relationship(
        back_populates="lesson", cascade="all, delete-orphan"
    )


class LessonResourceRow(Base):
    __tablename__ = "lesson_resources"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    lesson_id: Mapped[str] = mapped_column(String, ForeignKey("lessons.id"), index=True)
    resource_type: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    url: Mapped[str] = mapped_column(String)

    lesson: Mapped[LessonRow] = relationship(back_populates="resources")
