# app/main.py

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.hyperstate.middleware import HyperStateMiddleware
from app.hyperstate.response import HyperStateResponse
from app.hyperstate.sections import ContentSection
from app.hyperstate.nav import NavLink
from app.web.orders.routes import router as orders_router
from app.web.orders.options import router as options_router
from app.application.orders.cancel_order import OrderNotFound

from app.infrastructure.database import engine, Base
from app.infrastructure.models.order_model import OrderRow, LineItemRow

app = FastAPI(title="HyperState Example", version="0.1.0")
app.add_middleware(HyperStateMiddleware)
app.include_router(orders_router)
app.include_router(options_router)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


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
