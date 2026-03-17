# app/web/auth/routes.py
"""Authentication routes returning HyperState responses.

Login and logout are actions within the hypermedia protocol — they return
HyperStateResponse like everything else. The client doesn't need special
auth handling; it just renders whatever the server sends.
"""

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from hyperstate.response import HyperStateResponse, ViewContext
from hyperstate.sections import ContentSection, PropertiesSection
from hyperstate.display import PropertyItem
from hyperstate.flash import Flash
from hyperstate.nav import NavLink
from hyperstate.auth import login_action, logout_action, switch_user_action

from app.web.auth.tokens import create_token
from app.web.auth.users import authenticate, get_user_by_id, list_switchable_users
from app.web.deps import get_current_actor_optional
from hyperstate.response import ActorContext

router = APIRouter(prefix="/auth", tags=["auth"])

_COOKIE_NAME = "hs_token"
_COOKIE_MAX_AGE = 86400  # 24 hours


class LoginBody(BaseModel):
    username: str
    password: str


class SwitchBody(BaseModel):
    user_id: str


@router.get("/login", response_model=HyperStateResponse)
async def login_page(
    actor: ActorContext | None = Depends(get_current_actor_optional),
):
    """Show login form, or redirect to dashboard if already authenticated."""
    if actor is not None:
        return _already_authenticated_response(actor)

    return HyperStateResponse(
        view="form",
        title="Sign In",
        self_="/auth/login",
        sections=[
            ContentSection(
                title="Welcome",
                body="Sign in to access the homeschool planner. Demo accounts: parent/demo, student/demo, teacher/demo.",
            ),
            login_action(),
        ],
        nav=[NavLink(label="Home", href="/dashboard")],
    )


@router.post("/login", response_model=HyperStateResponse)
async def login(body: LoginBody, response: Response):
    """Authenticate and set the auth cookie."""
    user = authenticate(body.username, body.password)
    if user is None:
        return HyperStateResponse(
            view="form",
            title="Sign In",
            self_="/auth/login",
            flash=Flash(type="error", title="Invalid credentials", body="Check your username and password."),
            sections=[
                login_action(),
            ],
            nav=[NavLink(label="Home", href="/dashboard")],
        )

    token = create_token(user_id=user.id, roles=user.roles, name=user.name)
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        max_age=_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
    )

    return HyperStateResponse(
        view="detail",
        title="Signed In",
        self_="/auth/me",
        flash=Flash(type="success", title=f"Welcome, {user.name}!"),
        context=ViewContext(domain="auth", aggregate="session", state="authenticated"),
        sections=[
            PropertiesSection(data=[
                PropertyItem(key="name", label="Name", value=user.name),
                PropertyItem(key="roles", label="Roles", value=", ".join(user.roles), display="badge"),
            ]),
            logout_action(),
        ],
        nav=[NavLink(label="Dashboard", href="/dashboard")],
    )


@router.post("/logout", response_model=HyperStateResponse)
async def logout(response: Response):
    """Clear the auth cookie and show the login form."""
    response.delete_cookie(key=_COOKIE_NAME)

    return HyperStateResponse(
        view="form",
        title="Signed Out",
        self_="/auth/login",
        flash=Flash(type="info", title="You have been signed out."),
        sections=[
            login_action(),
        ],
        nav=[NavLink(label="Home", href="/dashboard")],
    )


@router.get("/me", response_model=HyperStateResponse)
async def current_user(
    actor: ActorContext | None = Depends(get_current_actor_optional),
):
    """Show the current user's profile."""
    if actor is None:
        return HyperStateResponse(
            view="form",
            title="Not Signed In",
            self_="/auth/login",
            sections=[
                ContentSection(body="You are not signed in."),
                login_action(),
            ],
            nav=[NavLink(label="Home", href="/dashboard")],
        )

    return HyperStateResponse(
        view="detail",
        title="Your Profile",
        self_="/auth/me",
        context=ViewContext(domain="auth", aggregate="session", state="authenticated", actor=actor),
        sections=[
            PropertiesSection(data=[
                PropertyItem(key="id", label="User ID", value=actor.id),
                PropertyItem(key="roles", label="Roles", value=", ".join(actor.roles), display="badge"),
            ]),
            switch_user_action(list_switchable_users()),
            logout_action(),
        ],
        nav=[NavLink(label="Dashboard", href="/dashboard")],
    )


@router.post("/switch", response_model=HyperStateResponse)
async def switch_user(body: SwitchBody, response: Response):
    """Switch to a different demo user (dev/demo convenience)."""
    user = get_user_by_id(body.user_id)
    if user is None:
        return HyperStateResponse(
            view="error",
            title="User Not Found",
            self_="/auth/me",
            flash=Flash(type="error", title="Unknown user."),
            sections=[ContentSection(body=f"No user with ID '{body.user_id}'.")],
            nav=[NavLink(label="Dashboard", href="/dashboard")],
        )

    token = create_token(user_id=user.id, roles=user.roles, name=user.name)
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        max_age=_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
    )

    return HyperStateResponse(
        view="detail",
        title="Switched User",
        self_="/auth/me",
        flash=Flash(type="success", title=f"Now signed in as {user.name}."),
        context=ViewContext(
            domain="auth", aggregate="session", state="authenticated",
            actor=ActorContext(id=user.id, roles=user.roles),
        ),
        sections=[
            PropertiesSection(data=[
                PropertyItem(key="name", label="Name", value=user.name),
                PropertyItem(key="roles", label="Roles", value=", ".join(user.roles), display="badge"),
            ]),
            switch_user_action(list_switchable_users()),
            logout_action(),
        ],
        nav=[NavLink(label="Dashboard", href="/dashboard")],
    )


def _already_authenticated_response(actor: ActorContext) -> HyperStateResponse:
    return HyperStateResponse(
        view="detail",
        title="Already Signed In",
        self_="/auth/me",
        context=ViewContext(domain="auth", aggregate="session", state="authenticated", actor=actor),
        sections=[
            PropertiesSection(data=[
                PropertyItem(key="id", label="User ID", value=actor.id),
                PropertyItem(key="roles", label="Roles", value=", ".join(actor.roles), display="badge"),
            ]),
            logout_action(),
        ],
        nav=[NavLink(label="Dashboard", href="/dashboard")],
    )
