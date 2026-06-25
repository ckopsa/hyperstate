from __future__ import annotations

from datetime import date, time

from sqlalchemy import String, Integer, Date, Time, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class WeekPlanRow(Base):
    __tablename__ = "week_plans"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    # One plan per week: the Tuesday start is a natural key.
    week_start: Mapped[date] = mapped_column(Date, unique=True, index=True)
    state: Mapped[str] = mapped_column(String, index=True, default="planning")

    slots: Mapped[list[DinnerSlotRow]] = relationship(
        back_populates="week_plan",
        cascade="all, delete-orphan",
        order_by="DinnerSlotRow.slot_date",
    )


class DinnerSlotRow(Base):
    __tablename__ = "dinner_slots"

    # Surrogate key: a slot's domain identity is its (week_plan, date) pair, but
    # the collection is replaced wholesale on save, so the PK is a storage detail.
    # The column is ``slot_date`` rather than ``date`` to avoid shadowing the
    # datetime.date type during SQLAlchemy annotation resolution.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    week_plan_id: Mapped[str] = mapped_column(String, ForeignKey("week_plans.id"), index=True)
    slot_date: Mapped[date] = mapped_column(Date)
    weekday: Mapped[int] = mapped_column(Integer)
    theme: Mapped[str] = mapped_column(String)
    recipe_id: Mapped[str | None] = mapped_column(String, ForeignKey("recipes.id"), nullable=True)
    target_time: Mapped[time] = mapped_column(Time)

    week_plan: Mapped[WeekPlanRow] = relationship(back_populates="slots")
