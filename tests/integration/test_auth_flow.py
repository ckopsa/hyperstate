"""Integration test for the Keycloak / OIDC auth flow.

Drives the real FastAPI app over ASGI with a stub OIDC client in place of a
live Keycloak (``get_oidc_client`` is overridden, mirroring how the other
integration tests override ``get_db``). Covers the four behaviours the auth
bead promises:

- An unauthenticated request to a protected route returns a 401 login response.
- ``GET /auth/login`` redirects the browser to Keycloak and plants a state cookie.
- ``GET /auth/callback`` exchanges the code, sets the auth cookie, and redirects
  to the dashboard.
- ``get_current_actor`` resolves the Keycloak-derived ActorContext from a valid
  cookie.

Plus the adversarial edges: a mismatched callback state is rejected, and logout
clears the cookie and bounces to Keycloak's end-session endpoint.

ASGITransport does not run the app's lifespan, so startup seeding never fires —
the stub OIDC client is the only Keycloak dependency these tests touch.
"""

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.infrastructure.auth.oidc import get_oidc_client
from app.infrastructure.database import Base, get_db
from app.main import app
from hyperstate.auth import NotAuthenticated
from hyperstate.response import ActorContext

AUTHORIZE_BASE = "https://keycloak.test/realms/mealplan/protocol/openid-connect/auth"
END_SESSION = "https://keycloak.test/realms/mealplan/protocol/openid-connect/logout"
ACCESS_TOKEN = "kc-access-token"

# The actor the stub maps the access token to — the "Keycloak-derived" identity.
ACTOR = ActorContext(id="kc-sub-123", username="alice", roles=["parent", "manager"])


class _FakeOIDCClient:
    """Stub Keycloak client: deterministic authorize/exchange/discover/validate."""

    async def authorization_url(self, state: str, scope: str = "openid profile email") -> str:
        return f"{AUTHORIZE_BASE}?state={state}&scope={scope.replace(' ', '+')}"

    async def exchange_code(self, code: str) -> dict:
        # A real client would POST the code to Keycloak's token endpoint.
        return {"access_token": ACCESS_TOKEN, "expires_in": 300, "token_type": "Bearer"}

    async def discover(self) -> dict:
        return {"end_session_endpoint": END_SESSION}

    async def actor_from_token(self, token: str) -> ActorContext:
        if token == ACCESS_TOKEN:
            return ACTOR
        raise NotAuthenticated("Invalid or expired authentication token.")


@pytest_asyncio.fixture
async def make_client():
    """Yield a factory building httpx clients against the app, no redirects followed.

    The OIDC client is stubbed and ``get_db`` points at an empty in-memory
    database so dependency resolution on protected routes never reaches a real
    Postgres. ``make_client(cookies=...)`` seeds the cookie jar.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_get_db():
        async with sessionmaker() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_oidc_client] = lambda: _FakeOIDCClient()
    transport = httpx.ASGITransport(app=app)
    clients: list[httpx.AsyncClient] = []

    def _make(cookies: dict | None = None) -> httpx.AsyncClient:
        client = httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
            cookies=cookies or {},
            follow_redirects=False,
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


def _sections(body: dict, kind: str) -> list[dict]:
    return [s for s in body["sections"] if s["kind"] == kind]


@pytest.mark.asyncio
async def test_unauthenticated_protected_route_returns_401_login(make_client):
    resp = await make_client().get("/dashboard")

    assert resp.status_code == 401
    body = resp.json()
    assert body["view"] == "form"
    assert body["self"] == "/auth/login"
    # The 401 carries a way to start login: a GET action pointing at /auth/login.
    actions = _sections(body, "action")
    assert any(a["href"] == "/auth/login" and a["method"] == "GET" for a in actions)


@pytest.mark.asyncio
async def test_login_redirects_to_keycloak_with_state(make_client):
    resp = await make_client().get("/auth/login")

    assert resp.status_code == 302
    assert resp.headers["location"].startswith(AUTHORIZE_BASE)
    # A state cookie is planted so the callback can detect forged redirects.
    assert resp.cookies.get("oidc_state")


@pytest.mark.asyncio
async def test_callback_sets_cookie_and_redirects_to_dashboard(make_client):
    client = make_client()

    # 1. Start login → grab the state the server planted.
    login = await client.get("/auth/login")
    state = login.cookies.get("oidc_state")
    assert state

    # 2. Keycloak redirects back with a code; the jar replays the state cookie.
    callback = await client.get("/auth/callback", params={"code": "auth-code", "state": state})

    assert callback.status_code == 303
    assert callback.headers["location"] == "/dashboard"
    assert callback.cookies.get("hs_token") == ACCESS_TOKEN


@pytest.mark.asyncio
async def test_authenticated_request_resolves_keycloak_actor(make_client):
    client = make_client(cookies={"hs_token": ACCESS_TOKEN})

    resp = await client.get("/auth/me")

    assert resp.status_code == 200
    body = resp.json()
    props = {p["key"]: p["value"] for p in _sections(body, "properties")[0]["data"]}
    assert props["id"] == ACTOR.id
    assert props["username"] == ACTOR.username
    assert props["roles"] == "parent, manager"


@pytest.mark.asyncio
async def test_callback_rejects_mismatched_state(make_client):
    # No prior /auth/login, so there is no state cookie to match against.
    resp = await make_client().get("/auth/callback", params={"code": "auth-code", "state": "forged"})

    assert resp.status_code == 401
    assert resp.json()["view"] == "form"


@pytest.mark.asyncio
async def test_logout_clears_cookie_and_ends_session(make_client):
    client = make_client(cookies={"hs_token": ACCESS_TOKEN})

    resp = await client.post("/auth/logout")

    assert resp.status_code == 303
    assert resp.headers["location"].startswith(END_SESSION)
    # The response instructs the browser to clear the auth cookie (expired Set-Cookie).
    set_cookies = resp.headers.get_list("set-cookie")
    assert any(
        c.startswith("hs_token=") and ("max-age=0" in c.lower() or "expires=" in c.lower())
        for c in set_cookies
    )
