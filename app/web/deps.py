# app/web/deps.py
"""FastAPI dependencies for actor resolution.

The actor is resolved from the JWT cookie set during login. Two dependency
variants are provided:

- get_current_actor: Requires authentication (raises NotAuthenticated if missing)
- get_current_actor_optional: Returns None if not authenticated

Routes that need auth use the first. Routes that render differently for
anonymous vs authenticated users (like the login page) use the second.
"""

from fastapi import Request

from hyperstate.response import ActorContext
from hyperstate.auth import NotAuthenticated
from app.web.auth.tokens import decode_token

_COOKIE_NAME = "hs_token"


async def get_current_actor_optional(request: Request) -> ActorContext | None:
    """Resolve the actor from the auth cookie, or return None."""
    token = request.cookies.get(_COOKIE_NAME)
    if not token:
        return None
    payload = decode_token(token)
    if payload is None:
        return None
    return ActorContext(id=payload.sub, roles=payload.roles)


async def get_current_actor(request: Request) -> ActorContext:
    """Resolve the actor from the auth cookie, or raise NotAuthenticated."""
    actor = await get_current_actor_optional(request)
    if actor is None:
        raise NotAuthenticated()
    return actor
