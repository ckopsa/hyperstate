from __future__ import annotations

from sqlalchemy import String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class RecipeRow(Base):
    __tablename__ = "recipes"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    theme: Mapped[str] = mapped_column(String, index=True)
    uses_frozen_meat: Mapped[bool] = mapped_column(Boolean, default=False)
    thaw_lead_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prep_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    state: Mapped[str] = mapped_column(String, index=True, default="active")

    ingredients: Mapped[list[IngredientRow]] = relationship(
        back_populates="recipe",
        cascade="all, delete-orphan",
        order_by="IngredientRow.position",
    )


class IngredientRow(Base):
    __tablename__ = "ingredients"

    # Surrogate key: ingredients are value objects with no domain identity, so
    # the primary key is a storage detail and the collection is replaced wholesale.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recipe_id: Mapped[str] = mapped_column(String, ForeignKey("recipes.id"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    name: Mapped[str] = mapped_column(String)
    quantity: Mapped[str | None] = mapped_column(String, nullable=True)

    recipe: Mapped[RecipeRow] = relationship(back_populates="ingredients")
