# app/web/auth/users.py
"""Demo user store.

In a real application, this would be a database-backed user repository.
For the reference implementation, we use a static dict of demo users
so the auth pattern is clear without needing user registration.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DemoUser:
    id: str
    name: str
    roles: list[str]
    password: str  # plaintext for demo only — hash in production


# Demo users for the homeschool planner
DEMO_USERS: dict[str, DemoUser] = {
    "parent": DemoUser(
        id="parent-1",
        name="Sarah",
        roles=["parent", "manager"],
        password="demo",
    ),
    "student": DemoUser(
        id="student-1",
        name="Emma",
        roles=["student"],
        password="demo",
    ),
    "teacher": DemoUser(
        id="teacher-1",
        name="Mr. Thompson",
        roles=["teacher"],
        password="demo",
    ),
}


def authenticate(username: str, password: str) -> DemoUser | None:
    """Verify credentials and return the user, or None."""
    user = DEMO_USERS.get(username)
    if user is None:
        return None
    if user.password != password:
        return None
    return user


def get_user_by_id(user_id: str) -> DemoUser | None:
    """Look up a user by their ID."""
    for user in DEMO_USERS.values():
        if user.id == user_id:
            return user
    return None


def list_switchable_users() -> list[dict[str, str]]:
    """Return user list for the switch-user action."""
    return [
        {"value": u.id, "label": f"{u.name} ({', '.join(u.roles)})"}
        for u in DEMO_USERS.values()
    ]
