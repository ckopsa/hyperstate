"""Integration test for the shopping routes.

Drives the real FastAPI app over ASGI against an in-memory SQLite database
(``get_db`` is overridden), seeds two recipes and a finalized (PLANNED) plan,
then exercises the full flow end to end: build the list, toggle items between
needed / have / bought, and read it back. Also covers the auth gate and the
not-found / invalid-state error mappings.

ASGITransport does not run the app's lifespan, so the startup seeding never
fires — the test owns its schema and data end to end.
"""
from datetime import date

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.domain.recipes.aggregate import Recipe
from app.domain.shared.themes import Theme
from app.domain.weekplan.aggregate import WeekPlan
from app.infrastructure.auth.oidc import get_oidc_client
from app.infrastructure.database import Base, get_db
from app.infrastructure.repositories.recipe_repo import RecipeRepository
from app.infrastructure.repositories.weekplan_repo import WeekPlanRepository
from app.main import app
from hyperstate.response import ActorContext

TUESDAY = date(2026, 6, 23)


class _StubOIDCClient:
    """Stand-in for the Keycloak client: any token resolves to a parent actor.

    Auth here turns purely on cookie presence (the ``authenticated`` flag), so
    the tests stay decoupled from the real JWKS/token validation in F1.
    """

    async def actor_from_token(self, token: str) -> ActorContext:
        return ActorContext(id="USER-1", username="Test Parent", roles=["parent"])
PLAN_ID = "WP-2026-06-23"  # WeekPlan.create derives this from the Tuesday start.
SHOPPING_URL = f"/shopping/{PLAN_ID}"


async def _make_plan(session, *, finalized: bool) -> None:
    """Two recipes sharing an ingredient, and a plan with every dinner decided.

    Spaghetti (beef + onion) and Tacos (beef + tortillas) both call for ground
    beef, so the built list merges it into one summed line. When ``finalized``
    the plan is advanced to PLANNED so the list can be built.
    """
    recipes = RecipeRepository(session)
    spaghetti = Recipe.create(id="REC-SPAG", name="Spaghetti", theme=Theme.ITALIAN)
    spaghetti.add_ingredient("Ground beef", "1 lb")
    spaghetti.add_ingredient("Onion", "1")
    await recipes.save(spaghetti)

    tacos = Recipe.create(id="REC-TACO", name="Tacos", theme=Theme.MEXICAN)
    tacos.add_ingredient("Ground beef", "1 lb")
    tacos.add_ingredient("Tortillas", "8")
    await recipes.save(tacos)

    plan = WeekPlan.create(TUESDAY)
    for i, slot in enumerate(plan.slots):
        plan.decide_dinner(slot.date, "REC-SPAG" if i % 2 == 0 else "REC-TACO")
    if finalized:
        plan.finalize()
    await WeekPlanRepository(session).save(plan)
    await session.commit()


@pytest_asyncio.fixture
async def api():
    """Yield a factory that builds httpx clients against the app.

    ``api()`` returns an authenticated client; ``api(authenticated=False)`` one
    with no auth cookie. ``api(finalized=False)`` seeds a still-PLANNING plan.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # one shared connection so the in-memory DB persists
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_get_db():
        async with sessionmaker() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_oidc_client] = lambda: _StubOIDCClient()
    transport = httpx.ASGITransport(app=app)
    clients: list[httpx.AsyncClient] = []
    seeded = False

    async def _make(authenticated: bool = True, finalized: bool = True) -> httpx.AsyncClient:
        nonlocal seeded
        if not seeded:
            async with sessionmaker() as session:
                await _make_plan(session, finalized=finalized)
            seeded = True
        cookies = {"hs_token": "test-token"} if authenticated else {}
        client = httpx.AsyncClient(
            transport=transport, base_url="http://test", cookies=cookies
        )
        clients.append(client)
        return client

    try:
        yield _make
    finally:
        for client in clients:
            await client.aclose()
        app.dependency_overrides.clear()
        await engine.dispose()


def _lists(body: dict) -> dict[str, dict]:
    """Map list-section title -> section for the flat shopping detail view."""
    return {s["title"]: s for s in body["sections"] if s["kind"] == "list"}


def _item(section: dict, name: str) -> dict:
    return next(i for i in section["items"] if i["data"]["item"] == name)


@pytest.mark.asyncio
async def test_get_before_build_is_404(api):
    resp = await (await api()).get(SHOPPING_URL)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_build_then_toggle_then_read_back(api):
    client = await api()

    # Build: every line starts on the buy list, with beef merged + summed.
    built = await client.post(SHOPPING_URL)
    assert built.status_code == 200
    body = built.json()
    to_buy = _lists(body)["To Buy"]
    names = {i["data"]["item"] for i in to_buy["items"]}
    assert names == {"Ground beef", "Onion", "Tortillas"}
    # Beef appears in 4 spaghetti + 3 taco slots (alternating across 7) → 7 lb.
    assert _item(to_buy, "Ground beef")["data"]["quantity"] == "7 lb"

    # The buy-it action carries the slugged item key in its href.
    have_action = next(
        a for a in _item(to_buy, "Ground beef")["actions"] if a["key"] == "mark-have"
    )
    assert have_action["href"] == f"{SHOPPING_URL}/items/ground-beef-lb/have"

    # Toggle: have the beef, buy the tortillas.
    await client.post(f"{SHOPPING_URL}/items/ground-beef-lb/have")
    marked = (await client.post(f"{SHOPPING_URL}/items/tortillas/bought")).json()

    groups = _lists(marked)
    assert {i["data"]["item"] for i in groups["To Buy"]["items"]} == {"Onion"}
    assert {i["data"]["item"] for i in groups["Already Have"]["items"]} == {"Ground beef"}
    assert {i["data"]["item"] for i in groups["Bought"]["items"]} == {"Tortillas"}

    summary = next(s for s in marked["sections"] if s["kind"] == "summary")
    counts = {i["label"]: i["value"] for i in summary["items"]}
    assert counts == {"To Buy": 1, "Have": 1, "Bought": 1}

    # Read back: the toggles persisted.
    reread = (await client.get(SHOPPING_URL)).json()
    assert {i["data"]["item"] for i in _lists(reread)["Already Have"]["items"]} == {"Ground beef"}


@pytest.mark.asyncio
async def test_weekplan_detail_links_to_list_once_built(api):
    client = await api()

    before = (await client.get(f"/weekplans/{PLAN_ID}")).json()
    keys_before = {s["key"] for s in before["sections"][0]["sections"][0]["sections"] if s["kind"] == "action"}
    assert "build-shopping-list" in keys_before

    await client.post(SHOPPING_URL)  # build it

    after = (await client.get(f"/weekplans/{PLAN_ID}")).json()
    actions = [
        s for s in after["sections"][0]["sections"][0]["sections"] if s["kind"] == "action"
    ]
    keys_after = {a["key"] for a in actions}
    assert "view-shopping-list" in keys_after
    assert "build-shopping-list" not in keys_after
    view = next(a for a in actions if a["key"] == "view-shopping-list")
    assert view["href"] == SHOPPING_URL


@pytest.mark.asyncio
async def test_marking_unknown_item_is_422(api):
    client = await api()
    await client.post(SHOPPING_URL)
    resp = await client.post(f"{SHOPPING_URL}/items/does-not-exist/have")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_invalid_action_is_422(api):
    client = await api()
    await client.post(SHOPPING_URL)
    resp = await client.post(f"{SHOPPING_URL}/items/onion/frobnicate")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_build_requires_authentication(api):
    resp = await (await api(authenticated=False)).post(SHOPPING_URL)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_build_while_planning_is_422(api):
    # A plan that was never finalized has nothing to shop for yet.
    resp = await (await api(finalized=False)).post(SHOPPING_URL)
    assert resp.status_code == 422
