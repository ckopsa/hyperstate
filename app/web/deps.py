# app/web/deps.py
"""FastAPI dependencies for actor resolution.

The actor is resolved from the JWT cookie set during the OIDC login callback.
The cookie carries a Keycloak-issued access token; it is validated against the
issuer's JWKS by the F1 OIDC client (``app.infrastructure.auth.oidc``). Two
dependency variants are provided:

- get_current_actor: Requires authentication (raises NotAuthenticated if the
  cookie is missing or the token is invalid/expired).
- get_current_actor_optional: Returns None instead of raising.

Routes that need auth use the first. Routes that render differently for
anonymous vs authenticated users (like the login page) use the second.

The OIDC client is injected via ``Depends(get_oidc_client)`` so tests can
override it the same way they override ``get_db``.
"""

from fastapi import Depends, Request

from hyperstate.auth import NotAuthenticated
from hyperstate.response import ActorContext

from app.infrastructure.auth.oidc import OIDCClient, get_oidc_client

# Name of the httponly cookie holding the Keycloak access token.
_COOKIE_NAME = "hs_token"


async def get_current_actor_optional(
    request: Request,
    client: OIDCClient = Depends(get_oidc_client),
) -> ActorContext | None:
    """Resolve the actor from the auth cookie, or return None.

    Returns None when no cookie is present or the token fails validation, so
    callers can branch on anonymous vs authenticated without handling 401s.
    """
    token = request.cookies.get(_COOKIE_NAME)
    if not token:
        return None
    try:
        return await client.actor_from_token(token)
    except NotAuthenticated:
        return None


async def get_current_actor(
    actor: ActorContext | None = Depends(get_current_actor_optional),
) -> ActorContext:
    """Resolve the actor from the auth cookie, or raise NotAuthenticated.

    The NotAuthenticated handler in ``app.main`` maps this to a 401 response
    carrying the login action.
    """
    if actor is None:
        raise NotAuthenticated()
    return actor
