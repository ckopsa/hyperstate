"""Household calendar-feed token, read from the environment.

Mirrors the env-driven config pattern in app/infrastructure/database.py and
app/infrastructure/auth/config.py. A single shared secret (``FEED_TOKEN``) guards
the cookieless Home Assistant feed URL: the token carried in the request path
must match it exactly. The value is read at call time, not import time, so the
process picks up the configured secret without a special import order.
"""
from __future__ import annotations

import hmac
import os

_FEED_TOKEN_ENV = "FEED_TOKEN"


def configured_feed_token() -> str:
    """Return the configured household feed token (``""`` when unset)."""
    return os.environ.get(_FEED_TOKEN_ENV, "")


def feed_token_matches(candidate: str) -> bool:
    """Whether ``candidate`` matches the configured token, in constant time.

    Returns ``False`` when no token is configured, so an unset (or blank)
    ``FEED_TOKEN`` disables the feed entirely rather than accepting a blank
    token. ``hmac.compare_digest`` keeps the comparison timing-independent.
    """
    configured = configured_feed_token()
    if not configured:
        return False
    return hmac.compare_digest(candidate, configured)
