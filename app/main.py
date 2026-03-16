# app/main.py

from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
import os

from app.hyperstate.middleware import HyperStateMiddleware
from app.hyperstate.response import HyperStateResponse
from app.hyperstate.sections import ContentSection
from app.hyperstate.nav import NavLink
from app.web.orders.routes import router as orders_router
from app.web.orders.options import router as options_router
from app.application.orders.cancel_order import OrderNotFound

from app.infrastructure.database import engine, Base, async_session
from app.infrastructure.models.order_model import OrderRow, LineItemRow

app = FastAPI(title="HyperState Example", version="0.1.0")
app.add_middleware(HyperStateMiddleware)
app.include_router(orders_router)
app.include_router(options_router)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create sample order if none exists
    async with async_session() as session:
        from sqlalchemy import select
        stmt = select(OrderRow).limit(1)
        result = await session.execute(stmt)
        if not result.scalar_one_or_none():
            from decimal import Decimal
            from datetime import datetime, UTC
            order = OrderRow(
                id="ORD-001",
                customer_id="CUST-7",
                state="pending",
                placed_at=datetime.now(UTC),
                items=[
                    LineItemRow(
                        product_id="PROD-1",
                        product_name="Standard Widget",
                        quantity=2,
                        unit_price=Decimal("25.00"),
                        currency="USD"
                    )
                ]
            )
            session.add(order)
            await session.commit()


@app.get("/", response_class=HTMLResponse)
async def get_client():
    path = os.path.join(os.path.dirname(__file__), "web", "client.html")
    with open(path, "r") as f:
        return f.read()


@app.exception_handler(OrderNotFound)
async def order_not_found_handler(request, exc: OrderNotFound):
    response = HyperStateResponse(
        view="error",
        title="Not Found",
        self_=str(request.url.path),
        sections=[
            ContentSection(
                body=f"Order {exc.order_id} was not found.",
                format="plain",
            ),
        ],
        nav=[NavLink(label="All Orders", href="/orders", rel="collection")],
    )
    return JSONResponse(
        status_code=404,
        content=response.model_dump(by_alias=True, exclude_none=True),
    )
