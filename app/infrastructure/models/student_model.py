from __future__ import annotations
from datetime import date

from sqlalchemy import String, Date
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class StudentRow(Base):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)
    grade_level: Mapped[str] = mapped_column(String)
    enrollment_date: Mapped[date] = mapped_column(Date)
