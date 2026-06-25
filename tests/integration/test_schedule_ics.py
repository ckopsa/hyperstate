"""Integration test for GET /weekplans/{id}/schedule.ics.

Drives the real FastAPI app over ASGI against an in-memory SQLite database
(``get_db`` is overridden), seeds a plan with one frozen and one fresh dinner,
then parses the downloaded calendar with the ``icalendar`` library to assert the
VEVENT count, the floating-time DTSTARTs, and that event UIDs are stable across
regenerations.

ASGITransport does not run the app's lifespan, so the Postgres ``startup``
seeding never fires — the test owns its schema and data end to end.
"""
from datetime import date, datetime

import httpx
import pytest
import pytest_asyncio
from icalendar import Calendar
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
WEDNESDAY = date(2026, 6, 24)
PLAN_ID = "WP-2026-06-23"  # WeekPlan.create derives this from the Tuesday start.
SCHEDULE_URL = f"/weekplans/{PLAN_ID}/schedule.ics"


class _StubOIDCClient:
    """Stand-in for the Keycloak client: any token resolves to a parent actor."""

    async def actor_from_token(self, token: str) -> ActorContext:
        return ActorContext(id="USER-1", username="Test Parent", roles=["parent"])


async def _seed(session) -> None:
    """Two recipes (frozen + fresh) and a plan with both dinners decided."""
    recipes = RecipeRepository(session)
    await recipes.save(
        Recipe.create(
            id="REC-FROZEN",
            name="Frozen Stew",
            theme=Theme.MEXICAN,
            uses_frozen_meat=True,
            thaw_lead_hours=12,
            prep_minutes=45,
        )
    )
    await recipes.save(
        Recipe.create(
            id="REC-FRESH",
            name="Quick Tacos",
            theme=Theme.AMERICAN,
            uses_frozen_meat=False,
            prep_minutes=30,
        )
    )
    plan = WeekPlan.create(TUESDAY)
    plan.decide_dinner(TUESDAY, "REC-FROZEN")
    plan.decide_dinner(WEDNESDAY, "REC-FRESH")
    await WeekPlanRepository(session).save(plan)
    await session.commit()


@pytest_asyncio.fixture
async def api():
    """Yield a factory that builds httpx clients against the seeded app.

    ``api()`` returns an authenticated client; ``api(authenticated=False)`` one
    with no auth cookie. All clients and the engine are torn down afterwards.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # one shared connection so the in-memory DB persists
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async with sessionmaker() as session:
        await _seed(session)

    async def _override_get_db():
        async with sessionmaker() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_oidc_client] = lambda: _StubOIDCClient()
    transport = httpx.ASGITransport(app=app)
    clients: list[httpx.AsyncClient] = []

    def _make(authenticated: bool = True) -> httpx.AsyncClient:
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


def _vevents(body: bytes) -> list:
    return list(Calendar.from_ical(body).walk("VEVENT"))


@pytest.mark.asyncio
async def test_serves_calendar_with_one_vevent_per_thaw_and_cook_start(api):
    resp = await api().get(SCHEDULE_URL)

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/calendar")
    assert "attachment" in resp.headers["content-disposition"]
    assert f"schedule-{PLAN_ID}.ics" in resp.headers["content-disposition"]

    vevents = _vevents(resp.content)
    # Frozen dinner → thaw + cook-start; fresh dinner → cook-start only.
    assert len(vevents) == 3

    summaries = sorted(str(e.get("summary")) for e in vevents)
    assert summaries == [
        "Start cooking: Frozen Stew",
        "Start cooking: Quick Tacos",
        "Thaw: Frozen Stew",
    ]


@pytest.mark.asyncio
async def test_event_times_match_computed_schedule(api):
    resp = await api().get(SCHEDULE_URL)
    vevents = _vevents(resp.content)

    starts = sorted(e.get("dtstart").dt for e in vevents)
    assert starts == [
        datetime(2026, 6, 23, 4, 45),   # Tue thaw: 16:45 − 12h
        datetime(2026, 6, 23, 16, 0),   # Tue cook: 16:45 − 45m
        datetime(2026, 6, 24, 16, 15),  # Wed cook: 16:45 − 30m
    ]
    # Reminders are floating local wall-clock times, not tied to a timezone.
    assert all(e.get("dtstart").dt.tzinfo is None for e in vevents)


@pytest.mark.asyncio
async def test_uids_are_stable_across_regenerations(api):
    client = api()
    first = _vevents((await client.get(SCHEDULE_URL)).content)
    second = _vevents((await client.get(SCHEDULE_URL)).content)

    uids_first = sorted(str(e.get("uid")) for e in first)
    uids_second = sorted(str(e.get("uid")) for e in second)
    assert uids_first == uids_second

    # UIDs key on (kind, slot date, plan) — not the volatile target time — so a
    # calendar client reconciles rather than duplicates on refresh.
    assert uids_first == [
        f"cook_start-2026-06-23-{PLAN_ID}@hyperstate.dinner",
        f"cook_start-2026-06-24-{PLAN_ID}@hyperstate.dinner",
        f"thaw-2026-06-23-{PLAN_ID}@hyperstate.dinner",
    ]


@pytest.mark.asyncio
async def test_requires_authentication(api):
    resp = await api(authenticated=False).get(SCHEDULE_URL)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unknown_plan_returns_404(api):
    resp = await api().get("/weekplans/WP-1999-01-01/schedule.ics")
    assert resp.status_code == 404
