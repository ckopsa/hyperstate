# app/infrastructure/models/order_model.py

from __future__ import annotations
from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, Numeric, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class OrderRow(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(String, index=True)
    state: Mapped[str] = mapped_column(String, index=True)
    shipping_street: Mapped[str | None] = mapped_column(String)
    shipping_city: Mapped[str | None] = mapped_column(String)
    shipping_state: Mapped[str | None] = mapped_column(String)
    shipping_country: Mapped[str | None] = mapped_column(String)
    shipping_postal: Mapped[str | None] = mapped_column(String)
    expedited: Mapped[bool] = mapped_column(Boolean, default=False)
    placed_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime)

    items: Mapped[list[LineItemRow]] = relationship(back_populates="order", cascade="all, delete-orphan")


class LineItemRow(Base):
    __tablename__ = "line_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"))
    product_id: Mapped[str] = mapped_column(String)
    product_name: Mapped[str] = mapped_column(String)
    quantity: Mapped[int]
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String, default="USD")

    order: Mapped[OrderRow] = relationship(back_populates="items")
