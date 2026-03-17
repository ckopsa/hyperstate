# app/web/auth/tokens.py
"""JWT token encoding/decoding for cookie-based auth.

HyperState apps use httponly cookies for auth tokens — the client never
touches tokens directly. This keeps the SPA client simple: it just sends
cookies with every fetch() automatically.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import base64
from dataclasses import dataclass

# In production, load from environment. This default is for development only.
_SECRET = "hyperstate-dev-secret-change-in-production"
_ALGORITHM = "HS256"
_TOKEN_LIFETIME = 86400  # 24 hours


@dataclass
class TokenPayload:
    sub: str             # user ID
    roles: list[str]     # role list
    name: str            # display name
    exp: int             # expiration timestamp


def create_token(user_id: str, roles: list[str], name: str, lifetime: int = _TOKEN_LIFETIME) -> str:
    """Create a signed JWT token."""
    payload = {
        "sub": user_id,
        "roles": roles,
        "name": name,
        "exp": int(time.time()) + lifetime,
    }
    return _encode(payload)


def decode_token(token: str) -> TokenPayload | None:
    """Decode and verify a JWT token. Returns None if invalid or expired."""
    payload = _decode(token)
    if payload is None:
        return None
    if payload.get("exp", 0) < time.time():
        return None
    return TokenPayload(
        sub=payload["sub"],
        roles=payload.get("roles", []),
        name=payload.get("name", ""),
        exp=payload["exp"],
    )


# ──────────────────────────────────────────────
# Minimal JWT implementation (HS256)
# No external dependency needed for this simple case.
# In production, use PyJWT or python-jose.
# ──────────────────────────────────────────────

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def _encode(payload: dict) -> str:
    header = {"alg": _ALGORITHM, "typ": "JWT"}
    h = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    sig_input = f"{h}.{p}".encode()
    sig = hmac.new(_SECRET.encode(), sig_input, hashlib.sha256).digest()
    return f"{h}.{p}.{_b64url_encode(sig)}"


def _decode(token: str) -> dict | None:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        h, p, s = parts
        sig_input = f"{h}.{p}".encode()
        expected_sig = hmac.new(_SECRET.encode(), sig_input, hashlib.sha256).digest()
        actual_sig = _b64url_decode(s)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        return json.loads(_b64url_decode(p))
    except Exception:
        return None
