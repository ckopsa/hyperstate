"""Unit tests for the Keycloak / OIDC client (dp-ial).

Uses an in-memory RSA keypair and an httpx.MockTransport standing in for
Keycloak's discovery + JWKS endpoints, so no network or live Keycloak is
needed. Covers valid-token claim mapping and rejection of malformed,
expired, wrongly-signed, and wrong-issuer tokens.
"""

from __future__ import annotations

import json
import time

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from hyperstate.auth import NotAuthenticated
from hyperstate.response import ActorContext
from app.infrastructure.auth.config import OIDCConfig
from app.infrastructure.auth.oidc import OIDCClient, _actor_from_claims

ISSUER = "https://keycloak.test/realms/mealplan"
JWKS_URI = "https://keycloak.test/realms/mealplan/protocol/openid-connect/certs"
TOKEN_ENDPOINT = "https://keycloak.test/realms/mealplan/protocol/openid-connect/token"
AUTH_ENDPOINT = "https://keycloak.test/realms/mealplan/protocol/openid-connect/auth"
KID = "test-key-1"


@pytest.fixture
def keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


@pytest.fixture
def jwk(keypair):
    _, public_key = keypair
    data = json.loads(RSAAlgorithm.to_jwk(public_key))
    data.update({"kid": KID, "use": "sig", "alg": "RS256"})
    return data


@pytest.fixture
def call_log():
    return []


@pytest.fixture
def mock_transport(jwk, call_log):
    discovery = {
        "issuer": ISSUER,
        "authorization_endpoint": AUTH_ENDPOINT,
        "token_endpoint": TOKEN_ENDPOINT,
        "jwks_uri": JWKS_URI,
    }
    jwks = {"keys": [jwk]}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        call_log.append(url)
        if url.endswith("/.well-known/openid-configuration"):
            return httpx.Response(200, json=discovery)
        if url == JWKS_URI:
            return httpx.Response(200, json=jwks)
        return httpx.Response(404, json={"error": "not found"})

    return httpx.MockTransport(handler)


@pytest.fixture
def client(mock_transport):
    config = OIDCConfig(
        issuer=ISSUER,
        client_id="mealplan",
        client_secret="secret",
        redirect_uri="http://localhost:8000/auth/callback",
    )
    http = httpx.AsyncClient(transport=mock_transport)
    return OIDCClient(config, http_client=http)


def make_token(private_key, *, kid: str = KID, **overrides) -> str:
    now = int(time.time())
    claims = {
        "sub": "user-123",
        "preferred_username": "sarah",
        "realm_access": {"roles": ["parent", "manager"]},
        "iss": ISSUER,
        "aud": "account",
        "iat": now,
        "exp": now + 300,
    }
    claims.update(overrides)
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": kid})


class TestActorFromToken:
    @pytest.mark.asyncio
    async def test_valid_token_maps_claims_to_actor(self, client, keypair):
        private_key, _ = keypair
        actor = await client.actor_from_token(make_token(private_key))
        assert isinstance(actor, ActorContext)
        assert actor.id == "user-123"
        assert actor.username == "sarah"
        assert actor.roles == ["parent", "manager"]

    @pytest.mark.asyncio
    async def test_expired_token_raises(self, client, keypair):
        private_key, _ = keypair
        token = make_token(private_key, exp=int(time.time()) - 10)
        with pytest.raises(NotAuthenticated):
            await client.actor_from_token(token)

    @pytest.mark.asyncio
    async def test_token_signed_by_unknown_key_raises(self, client):
        # Signed by a different keypair than the JWKS advertises (same kid).
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        token = make_token(other_key)
        with pytest.raises(NotAuthenticated):
            await client.actor_from_token(token)

    @pytest.mark.asyncio
    async def test_unknown_kid_raises(self, client, keypair):
        private_key, _ = keypair
        token = make_token(private_key, kid="does-not-exist")
        with pytest.raises(NotAuthenticated):
            await client.actor_from_token(token)

    @pytest.mark.asyncio
    async def test_wrong_issuer_raises(self, client, keypair):
        private_key, _ = keypair
        token = make_token(private_key, iss="https://evil.test/realms/x")
        with pytest.raises(NotAuthenticated):
            await client.actor_from_token(token)

    @pytest.mark.asyncio
    async def test_malformed_token_raises(self, client):
        with pytest.raises(NotAuthenticated):
            await client.actor_from_token("this.is.not-a-jwt")

    @pytest.mark.asyncio
    async def test_token_without_kid_raises(self, client, keypair):
        private_key, _ = keypair
        now = int(time.time())
        # Encode without a kid header.
        token = jwt.encode(
            {"sub": "x", "iss": ISSUER, "exp": now + 300},
            private_key,
            algorithm="RS256",
        )
        with pytest.raises(NotAuthenticated):
            await client.actor_from_token(token)

    @pytest.mark.asyncio
    async def test_missing_realm_access_yields_empty_roles(self, client, keypair):
        private_key, _ = keypair
        token = make_token(private_key, realm_access=None)
        actor = await client.actor_from_token(token)
        assert actor.roles == []
        assert actor.id == "user-123"

    @pytest.mark.asyncio
    async def test_jwks_fetched_once_and_cached(self, client, keypair, call_log):
        private_key, _ = keypair
        await client.actor_from_token(make_token(private_key))
        await client.actor_from_token(make_token(private_key))
        # Discovery and JWKS each fetched exactly once across two validations.
        assert call_log.count(client._config.discovery_url) == 1
        assert call_log.count(JWKS_URI) == 1


class TestActorFromClaims:
    """Pure-function tests for the claim → ActorContext mapping."""

    def test_maps_all_fields(self):
        actor = _actor_from_claims(
            {
                "sub": "abc",
                "preferred_username": "emma",
                "realm_access": {"roles": ["student"]},
            }
        )
        assert actor.id == "abc"
        assert actor.username == "emma"
        assert actor.roles == ["student"]

    def test_missing_sub_raises(self):
        with pytest.raises(NotAuthenticated):
            _actor_from_claims({"preferred_username": "nobody"})

    def test_missing_optional_claims_are_tolerated(self):
        actor = _actor_from_claims({"sub": "abc"})
        assert actor.id == "abc"
        assert actor.username is None
        assert actor.roles == []


class TestDiscovery:
    @pytest.mark.asyncio
    async def test_discover_returns_endpoints(self, client):
        meta = await client.discover()
        assert meta["jwks_uri"] == JWKS_URI
        assert meta["token_endpoint"] == TOKEN_ENDPOINT
