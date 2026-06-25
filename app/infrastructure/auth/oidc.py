# app/infrastructure/auth/oidc.py
"""Keycloak / OIDC client: discovery, JWKS validation, and actor mapping.

This module is the bridge between Keycloak-issued JWTs and the application's
ActorContext. It performs:

- OIDC discovery against the configured issuer (cached).
- Authorization-code exchange via authlib (for the login callback).
- Cached JWKS fetching with refresh-on-miss (Keycloak rotates signing keys).
- actor_from_token(): signature + expiry validation, mapping claims to
  ActorContext(id=sub, username=preferred_username, roles=realm_access.roles).

Invalid or expired tokens raise NotAuthenticated (HTTP 401).
"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx
import jwt
from jwt.algorithms import RSAAlgorithm

from hyperstate.auth import NotAuthenticated
from hyperstate.response import ActorContext

from app.infrastructure.auth.config import OIDCConfig

# Keycloak signs realm tokens with RS256 by default.
_ALLOWED_ALGORITHMS = ["RS256"]
_JWKS_TTL_SECONDS = 3600


class _SigningKeyNotFound(Exception):
    """Internal: no JWKS key matched the token's `kid`, even after a refresh."""


class OIDCClient:
    """Stateful OIDC client with cached discovery metadata and JWKS.

    A single instance is meant to be shared across requests. The HTTP client
    is injectable so tests can drive it with httpx.MockTransport instead of a
    live Keycloak.
    """

    def __init__(
        self,
        config: OIDCConfig,
        *,
        http_client: httpx.AsyncClient | None = None,
        jwks_ttl: int = _JWKS_TTL_SECONDS,
    ) -> None:
        self._config = config
        self._http = http_client or httpx.AsyncClient(timeout=10.0)
        self._jwks_ttl = jwks_ttl
        self._metadata: dict[str, Any] | None = None
        self._keys_by_kid: dict[str, Any] = {}
        self._jwks_fetched_at = 0.0

    # ── Discovery ─────────────────────────────────────────────────

    async def discover(self) -> dict[str, Any]:
        """Fetch and cache the OIDC discovery document."""
        if self._metadata is None:
            resp = await self._http.get(self._config.discovery_url)
            resp.raise_for_status()
            self._metadata = resp.json()
        return self._metadata

    # ── JWKS ──────────────────────────────────────────────────────

    def _jwks_stale(self) -> bool:
        return (time.time() - self._jwks_fetched_at) > self._jwks_ttl

    async def _refresh_jwks(self) -> None:
        meta = await self.discover()
        resp = await self._http.get(meta["jwks_uri"])
        resp.raise_for_status()
        keys: dict[str, Any] = {}
        for jwk in resp.json().get("keys", []):
            kid = jwk.get("kid")
            if not kid:
                continue
            try:
                keys[kid] = RSAAlgorithm.from_jwk(json.dumps(jwk))
            except Exception:
                # Skip keys we can't parse (e.g. non-RSA EC keys).
                continue
        self._keys_by_kid = keys
        self._jwks_fetched_at = time.time()

    async def _signing_key(self, kid: str) -> Any:
        """Return the public key for `kid`, refreshing JWKS on a miss or when stale."""
        if kid not in self._keys_by_kid or self._jwks_stale():
            await self._refresh_jwks()
        key = self._keys_by_kid.get(kid)
        if key is None:
            raise _SigningKeyNotFound(kid)
        return key

    # ── Token validation ──────────────────────────────────────────

    async def actor_from_token(self, token: str) -> ActorContext:
        """Validate a JWT and map its claims to an ActorContext.

        Verifies the RS256 signature against the issuer's JWKS and the `exp`
        claim. Raises NotAuthenticated for any malformed, unverifiable, or
        expired token.
        """
        try:
            header = jwt.get_unverified_header(token)
        except jwt.InvalidTokenError as exc:
            raise NotAuthenticated("Malformed authentication token.") from exc

        kid = header.get("kid")
        if not kid:
            raise NotAuthenticated("Token is missing a key id (kid).")

        try:
            key = await self._signing_key(kid)
        except _SigningKeyNotFound as exc:
            raise NotAuthenticated("Token signed by an unknown key.") from exc

        try:
            claims = jwt.decode(
                token,
                key=key,
                algorithms=_ALLOWED_ALGORITHMS,
                issuer=self._config.issuer or None,
                options={
                    "require": ["exp", "sub"],
                    # Keycloak access tokens carry aud="account", not the
                    # client_id, so audience is not verified here.
                    "verify_aud": False,
                },
            )
        except jwt.InvalidTokenError as exc:
            raise NotAuthenticated("Invalid or expired authentication token.") from exc

        return _actor_from_claims(claims)

    # ── Authorization-code flow (authlib) ─────────────────────────

    async def authorization_url(
        self, state: str, scope: str = "openid profile email"
    ) -> str:
        """Build the Keycloak authorization URL to redirect the user to."""
        from authlib.integrations.httpx_client import AsyncOAuth2Client

        meta = await self.discover()
        async with AsyncOAuth2Client(
            client_id=self._config.client_id,
            client_secret=self._config.client_secret,
            redirect_uri=self._config.redirect_uri,
            scope=scope,
        ) as client:
            url, _ = client.create_authorization_url(
                meta["authorization_endpoint"], state=state
            )
        return url

    async def exchange_code(self, code: str) -> dict[str, Any]:
        """Exchange an authorization code for a token set via authlib."""
        from authlib.integrations.httpx_client import AsyncOAuth2Client

        meta = await self.discover()
        async with AsyncOAuth2Client(
            client_id=self._config.client_id,
            client_secret=self._config.client_secret,
            redirect_uri=self._config.redirect_uri,
        ) as client:
            token = await client.fetch_token(
                meta["token_endpoint"],
                grant_type="authorization_code",
                code=code,
            )
        return dict(token)

    async def aclose(self) -> None:
        await self._http.aclose()


def _actor_from_claims(claims: dict[str, Any]) -> ActorContext:
    """Map validated Keycloak claims to an ActorContext."""
    sub = claims.get("sub")
    if not sub:
        raise NotAuthenticated("Token is missing the subject (sub) claim.")
    realm_access = claims.get("realm_access")
    roles = realm_access.get("roles", []) if isinstance(realm_access, dict) else []
    return ActorContext(
        id=sub,
        username=claims.get("preferred_username"),
        roles=list(roles),
    )


# ── Module-level singleton (for app wiring) ───────────────────────

_client: OIDCClient | None = None


def get_oidc_client() -> OIDCClient:
    """Return the process-wide OIDC client, building it from env on first use."""
    global _client
    if _client is None:
        _client = OIDCClient(OIDCConfig.from_env())
    return _client


async def actor_from_token(token: str) -> ActorContext:
    """Convenience wrapper over the singleton client's actor_from_token."""
    return await get_oidc_client().actor_from_token(token)
