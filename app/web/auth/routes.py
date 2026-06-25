# app/web/auth/routes.py
"""Authentication routes for the Keycloak / OIDC authorization-code flow.

Login is a browser redirect, not a form the SPA renders: the server bounces
the browser to Keycloak, Keycloak authenticates the user, then redirects back
to ``/auth/callback`` with an authorization code. The callback exchanges the
code for tokens, stores the access token in an httponly cookie, and redirects
to the dashboard. Logout clears the cookie and ends the Keycloak SSO session.

``/auth/me`` remains a normal HyperState response so the SPA can show the
signed-in profile.

The OIDC client is injected via ``Depends(get_oidc_client)`` so tests can
swap in a stub without a live Keycloak.
"""

from __future__ import annotations

import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import RedirectResponse

from hyperstate.auth import NotAuthenticated, logout_action
from hyperstate.display import PropertyItem
from hyperstate.nav import NavLink
from hyperstate.response import ActorContext, HyperStateResponse, ViewContext
from hyperstate.sections import ActionSection, ContentSection, PropertiesSection

from app.infrastructure.auth.config import OIDCConfig
from app.infrastructure.auth.oidc import OIDCClient, get_oidc_client
from app.web.deps import get_current_actor_optional

router = APIRouter(prefix="/auth", tags=["auth"])

# Cookie holding the Keycloak access token (see app/web/deps.py).
_COOKIE_NAME = "hs_token"
# Short-lived cookie holding the OAuth `state` value for CSRF protection.
_STATE_COOKIE = "oidc_state"
_STATE_MAX_AGE = 300  # 5 minutes — long enough to log in at Keycloak.

_DASHBOARD = "/dashboard"


def keycloak_login_action() -> ActionSection:
    """A 'Sign In' affordance that starts the OIDC redirect (GET /auth/login).

    Unlike the demo username/password form, login here is a browser navigation
    to Keycloak, so the action is a GET button rather than a credentials form.
    """
    return ActionSection(
        key="login",
        label="Sign In",
        method="GET",
        href="/auth/login",
        style="primary",
    )


@router.get("/login")
async def login(
    request: Request,
    client: OIDCClient = Depends(get_oidc_client),
    actor: ActorContext | None = Depends(get_current_actor_optional),
) -> Response:
    """Begin the OIDC login: redirect the browser to Keycloak.

    Already-authenticated callers are bounced straight to the dashboard. A
    random `state` is stored in a short-lived cookie and echoed back by
    Keycloak so the callback can reject forged or replayed redirects.
    """
    if actor is not None:
        return RedirectResponse(_DASHBOARD, status_code=303)

    state = secrets.token_urlsafe(32)
    authorize_url = await client.authorization_url(state)
    response = RedirectResponse(authorize_url, status_code=302)
    response.set_cookie(
        key=_STATE_COOKIE,
        value=state,
        max_age=_STATE_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/callback")
async def callback(
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    client: OIDCClient = Depends(get_oidc_client),
) -> Response:
    """Handle Keycloak's redirect: validate state, exchange code, set cookie.

    On success, stores the access token in an httponly cookie and redirects to
    the dashboard. Any failure (Keycloak error, missing code, or mismatched
    state) raises NotAuthenticated → 401 login response.
    """
    if error:
        raise NotAuthenticated(f"Login failed: {error}.")
    if not code:
        raise NotAuthenticated("Login response was missing the authorization code.")

    expected_state = request.cookies.get(_STATE_COOKIE)
    if not expected_state or not state or not secrets.compare_digest(state, expected_state):
        raise NotAuthenticated("Login state did not match; please try again.")

    token = await client.exchange_code(code)
    access_token = token.get("access_token")
    if not access_token:
        raise NotAuthenticated("Keycloak did not return an access token.")

    response = RedirectResponse(_DASHBOARD, status_code=303)
    expires_in = token.get("expires_in")
    response.set_cookie(
        key=_COOKIE_NAME,
        value=access_token,
        max_age=int(expires_in) if isinstance(expires_in, (int, float)) else None,
        httponly=True,
        samesite="lax",
    )
    response.delete_cookie(_STATE_COOKIE)
    return response


@router.post("/logout")
async def logout(
    request: Request,
    client: OIDCClient = Depends(get_oidc_client),
) -> Response:
    """Clear the auth cookie and end the Keycloak SSO session.

    Redirects to Keycloak's end-session endpoint (discovered from the issuer)
    so the SSO session is terminated, then back to the login page. Falls back
    to the local login page if the issuer advertises no end-session endpoint.
    """
    post_logout = f"{str(request.base_url).rstrip('/')}/auth/login"
    target = post_logout
    try:
        meta = await client.discover()
        end_session = meta.get("end_session_endpoint")
    except Exception:
        end_session = None
    if end_session:
        params = urlencode(
            {
                "client_id": OIDCConfig.from_env().client_id,
                "post_logout_redirect_uri": post_logout,
            }
        )
        target = f"{end_session}?{params}"

    response = RedirectResponse(target, status_code=303)
    response.delete_cookie(_COOKIE_NAME)
    return response


@router.get("/me", response_model=HyperStateResponse)
async def current_user(
    actor: ActorContext | None = Depends(get_current_actor_optional),
):
    """Show the signed-in user's profile, or a sign-in prompt if anonymous."""
    if actor is None:
        return HyperStateResponse(
            view="form",
            title="Not Signed In",
            self_="/auth/me",
            sections=[
                ContentSection(body="You are not signed in."),
                keycloak_login_action(),
            ],
            nav=[NavLink(label="Home", href=_DASHBOARD)],
        )

    return HyperStateResponse(
        view="detail",
        title="Your Profile",
        self_="/auth/me",
        context=ViewContext(domain="auth", aggregate="session", state="authenticated", actor=actor),
        sections=[
            PropertiesSection(data=[
                PropertyItem(key="id", label="User ID", value=actor.id),
                PropertyItem(key="username", label="Username", value=actor.username or "—"),
                PropertyItem(key="roles", label="Roles", value=", ".join(actor.roles) or "—", display="badge"),
            ]),
            logout_action(),
        ],
        nav=[NavLink(label="Dashboard", href=_DASHBOARD)],
    )
