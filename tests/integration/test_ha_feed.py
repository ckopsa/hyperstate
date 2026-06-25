"""Integration test for GET /calendar/feed/{feed_token}.ics — the Home Assistant feed.

Drives the real FastAPI app over ASGI against an in-memory SQLite database
(``get_db`` is overridden), seeds two upcoming (non-completed) weeks plus one
COMPLETED week, then parses the downloaded calendar with the ``icalendar``
library to assert that the feed aggregates every upcoming week's prep reminders,
excludes completed weeks, and is guarded purely by the household ``FEED_TOKEN``.

``FEED_TOKEN`` is set on the environment via monkeypatch; the route reads it at
request time. ASGITransport does not run the app's lifespan, so the Postgres
``startup`` seeding never fires — the test owns its schema and data end to end.
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
from app.domain.weekplan.states import WeekPlanState
from app.infrastructure.database import Base, get_db
from app.infrastructure.repositories.recipe_repo import RecipeRepository
from app.infrastructure.repositories.weekplan_repo import WeekPlanRepository
from app.main import app
from app.web.auth.tokens import create_token

FEED_TOKEN = "household-secret-token"
FEED_URL = f"/calendar/feed/{FEED_TOKEN}.ics"

# Two upcoming weeks — both must appear in the feed.
WEEK_A_TUE = date(2026, 6, 23)
WEEK_A_WED = date(2026, 6, 24)
WEEK_A_ID = "WP-2026-06-23"
WEEK_B_TUE = date(2026, 6, 30)
WEEK_B_ID = "WP-2026-06-30"
# An earlier, COMPLETED week — its reminders must NOT appear.
WEEK_DONE_TUE = date(2026, 6, 16)
WEEK_DONE_ID = "WP-2026-06-16"


async def _seed(session) -> None:
    """Two non-completed weeks (with dinners) and one completed week."""
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
    await recipes.save(
        Recipe.create(
            id="REC-ROAST",
            name="Sunday Roast",
            theme=Theme.AMERICAN,
            uses_frozen_meat=False,
            prep_minutes=60,
        )
    )
    await recipes.save(
        Recipe.create(
            id="REC-DONE",
            name="Last Week Casserole",
            theme=Theme.AMERICAN,
            uses_frozen_meat=False,
            prep_minutes=30,
        )
    )

    plans = WeekPlanRepository(session)

    # Week A: PLANNING (the default) with a frozen + a fresh dinner → 3 events.
    week_a = WeekPlan.create(WEEK_A_TUE)
    week_a.decide_dinner(WEEK_A_TUE, "REC-FROZEN")
    week_a.decide_dinner(WEEK_A_WED, "REC-FRESH")
    await plans.save(week_a)

    # Week B: a later week in ACTIVE with one dinner → 1 event. Proves the feed
    # aggregates across weeks and across non-completed states, not just PLANNING.
    week_b = WeekPlan.create(WEEK_B_TUE)
    week_b.decide_dinner(WEEK_B_TUE, "REC-ROAST")
    week_b.state = WeekPlanState.ACTIVE  # seed straight to state; skip the transition chain
    await plans.save(week_b)

    # Completed week: a decided dinner whose reminders must be filtered out.
    week_done = WeekPlan.create(WEEK_DONE_TUE)
    week_done.decide_dinner(WEEK_DONE_TUE, "REC-DONE")
    week_done.state = WeekPlanState.COMPLETED
    await plans.save(week_done)

    await session.commit()


@pytest_asyncio.fixture
async def api(monkeypatch):
    """Yield a factory that builds httpx clients against the seeded app.

    Configures ``FEED_TOKEN`` for the run. ``api()`` returns an authenticated
    client; ``api(authenticated=False)`` one with no auth cookie — the latter
    models Home Assistant, which subscribes by URL with no cookie at all.
    """
    monkeypatch.setenv("FEED_TOKEN", FEED_TOKEN)

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
    transport = httpx.ASGITransport(app=app)
    clients: list[httpx.AsyncClient] = []

    def _make(authenticated: bool = True) -> httpx.AsyncClient:
        cookies = (
            {"hs_token": create_token("USER-1", ["parent"], "Test Parent")}
            if authenticated
            else {}
        )
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
async def test_correct_token_serves_aggregated_calendar(api):
    resp = await api().get(FEED_URL)

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/calendar")

    vevents = _vevents(resp.content)
    # Week A: frozen → thaw + cook; fresh → cook (3). Week B: one fresh cook (1).
    assert len(vevents) == 4

    summaries = sorted(str(e.get("summary")) for e in vevents)
    assert summaries == [
        "Start cooking: Frozen Stew",   # week A, Tue
        "Start cooking: Quick Tacos",   # week A, Wed
        "Start cooking: Sunday Roast",  # week B, Tue
        "Thaw: Frozen Stew",            # week A, Tue
    ]


@pytest.mark.asyncio
async def test_feed_aggregates_both_upcoming_weeks(api):
    uids = {str(e.get("uid")) for e in _vevents((await api().get(FEED_URL)).content)}

    # Reminders from both upcoming weeks are present (UIDs embed the plan id)...
    assert any(WEEK_A_ID in uid for uid in uids)
    assert any(WEEK_B_ID in uid for uid in uids)


@pytest.mark.asyncio
async def test_completed_weeks_are_excluded(api):
    resp = await api().get(FEED_URL)
    vevents = _vevents(resp.content)

    uids = [str(e.get("uid")) for e in vevents]
    summaries = [str(e.get("summary")) for e in vevents]
    # ...but nothing from the completed week leaks into the feed.
    assert all(WEEK_DONE_ID not in uid for uid in uids)
    assert "Start cooking: Last Week Casserole" not in summaries


@pytest.mark.asyncio
async def test_event_times_are_floating_local(api):
    starts = [e.get("dtstart").dt for e in _vevents((await api().get(FEED_URL)).content)]
    # Reminders are floating wall-clock times, not tied to a timezone.
    assert all(s.tzinfo is None for s in starts)
    # Week B's fresh dinner cooks 60 min before the 16:45 default target.
    assert datetime(2026, 6, 30, 15, 45) in starts


@pytest.mark.asyncio
async def test_feed_does_not_require_a_login_cookie(api):
    # Home Assistant polls the URL with no cookie; the path token is the auth.
    resp = await api(authenticated=False).get(FEED_URL)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/calendar")


@pytest.mark.asyncio
async def test_wrong_token_is_not_found(api):
    resp = await api().get("/calendar/feed/not-the-token.ics")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_feed_disabled_when_token_unset(api, monkeypatch):
    # With no FEED_TOKEN configured the feed is off — even a blank token is rejected.
    monkeypatch.delenv("FEED_TOKEN", raising=False)
    assert (await api().get(FEED_URL)).status_code == 404
