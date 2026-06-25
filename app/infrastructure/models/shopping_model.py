from __future__ import annotations

from sqlalchemy import String, Integer, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class ShoppingListRow(Base):
    __tablename__ = "shopping_lists"

    # One list per week plan: the plan id is the natural primary key.
    week_plan_id: Mapped[str] = mapped_column(
        String, ForeignKey("week_plans.id"), primary_key=True
    )

    items: Mapped[list[ShoppingItemRow]] = relationship(
        back_populates="shopping_list",
        cascade="all, delete-orphan",
        order_by="ShoppingItemRow.position",
    )


class ShoppingItemRow(Base):
    __tablename__ = "shopping_items"

    # Surrogate key: items are merged value lines with no domain identity of
    # their own, so the collection is replaced wholesale on save and the PK is a
    # storage detail. The (name, unit) pair is the domain-level identity.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    week_plan_id: Mapped[str] = mapped_column(
        String, ForeignKey("shopping_lists.week_plan_id"), index=True
    )
    position: Mapped[int] = mapped_column(Integer, default=0)
    name: Mapped[str] = mapped_column(String)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, index=True, default="needed")

    shopping_list: Mapped[ShoppingListRow] = relationship(back_populates="items")
