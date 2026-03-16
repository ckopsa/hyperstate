from __future__ import annotations
from datetime import date

from sqlalchemy import String, Date, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class InstructionDayRow(Base):
    __tablename__ = "instruction_days"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False)
    lessons_completed: Mapped[int] = mapped_column(Integer, default=0)
    subjects_covered: Mapped[str | None] = mapped_column(String, nullable=True)
