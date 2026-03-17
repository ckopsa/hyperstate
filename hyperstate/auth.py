# hyperstate/auth.py
"""Authentication and authorization primitives for HyperState applications.

These are framework-level helpers. The actual auth mechanism (JWT, sessions, etc.)
is an application concern — this module provides the protocol-level pieces:
role checking, auth exceptions, and login/logout action builders.
"""

from __future__ import annotations

from .response import ActorContext
from .sections import ActionSection, ActionCondition
from .fields import TextField


# ──────────────────────────────────────────────
# Exceptions
# ──────────────────────────────────────────────

class NotAuthenticated(Exception):
    """Raised when a request has no valid identity.

    Maps to HTTP 401. The HyperState error response should include
    a login action so the client can authenticate.
    """

    def __init__(self, message: str = "Authentication required."):
        self.message = message
        super().__init__(message)


class NotAuthorized(Exception):
    """Raised when an authenticated actor lacks permission.

    Maps to HTTP 403. The HyperState error response should explain
    what role is required.
    """

    def __init__(self, message: str = "You don't have permission to do this.", required_roles: list[str] | None = None):
        self.message = message
        self.required_roles = required_roles or []
        super().__init__(message)


# ──────────────────────────────────────────────
# Role checking
# ──────────────────────────────────────────────

def has_role(actor: ActorContext | None, role: str) -> bool:
    """Check if an actor has a specific role."""
    if actor is None:
        return False
    return role in actor.roles


def has_any_role(actor: ActorContext | None, roles: list[str]) -> bool:
    """Check if an actor has any of the specified roles."""
    if actor is None:
        return False
    return bool(set(actor.roles) & set(roles))


def require_role(actor: ActorContext | None, role: str) -> None:
    """Raise NotAuthorized if the actor lacks the specified role."""
    if actor is None:
        raise NotAuthenticated()
    if role not in actor.roles:
        raise NotAuthorized(
            message=f"Requires '{role}' role.",
            required_roles=[role],
        )


def require_any_role(actor: ActorContext | None, roles: list[str]) -> None:
    """Raise NotAuthorized if the actor lacks all of the specified roles."""
    if actor is None:
        raise NotAuthenticated()
    if not set(actor.roles) & set(roles):
        raise NotAuthorized(
            message=f"Requires one of: {', '.join(roles)}.",
            required_roles=roles,
        )


# ──────────────────────────────────────────────
# Action condition helpers
# ──────────────────────────────────────────────

def role_condition(actor: ActorContext | None, role: str) -> ActionCondition | None:
    """Return an ActionCondition if the actor lacks the role, else None.

    Use this to disable actions in projections based on role:

        ActionSection(
            key="delete", label="Delete",
            ...,
            condition=role_condition(actor, "admin"),
        )
    """
    if has_role(actor, role):
        return None  # action is available
    return ActionCondition(met=False, explain=f"Requires '{role}' role.")


# ──────────────────────────────────────────────
# Login/logout action builders
# ──────────────────────────────────────────────

def login_action(
    href: str = "/auth/login",
    username_field: str = "username",
    password_field: str = "password",
) -> ActionSection:
    """Build a standard login form action."""
    return ActionSection(
        key="login",
        label="Sign In",
        method="POST",
        href=href,
        style="primary",
        fields=[
            TextField(name=username_field, label="Username", required=True, placeholder="Enter your username"),
            TextField(name=password_field, label="Password", required=True, placeholder="Enter your password"),
        ],
    )


def logout_action(href: str = "/auth/logout") -> ActionSection:
    """Build a standard logout button action."""
    return ActionSection(
        key="logout",
        label="Sign Out",
        method="POST",
        href=href,
        style="subtle",
    )


def switch_user_action(
    users: list[dict[str, str]],
    href: str = "/auth/switch",
) -> ActionSection:
    """Build a user-switcher action for demo/dev environments.

    Each user dict should have 'value' and 'label' keys:
        [{"value": "parent-1", "label": "Parent (Sarah)"},
         {"value": "student-1", "label": "Student (Emma)"}]
    """
    from .fields import SelectField, FieldOption

    return ActionSection(
        key="switch-user",
        label="Switch User",
        method="POST",
        href=href,
        style="default",
        fields=[
            SelectField(
                name="user_id",
                label="Sign in as",
                required=True,
                options=[FieldOption(value=u["value"], label=u["label"]) for u in users],
            ),
        ],
    )
