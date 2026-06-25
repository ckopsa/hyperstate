# app/infrastructure/auth/config.py
"""OIDC / Keycloak configuration, read from the environment.

Mirrors the env-driven config pattern in app/infrastructure/database.py: the
same code runs against a local docker-compose Keycloak and a managed instance
in deploy, switching purely on environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class OIDCConfig:
    """Settings for talking to a Keycloak / OIDC issuer."""

    issuer: str
    client_id: str
    client_secret: str
    redirect_uri: str

    @classmethod
    def from_env(cls) -> "OIDCConfig":
        """Build config from OIDC_* environment variables.

        Defaults target the local docker-compose Keycloak realm so the app
        boots in development without extra configuration.
        """
        return cls(
            issuer=os.environ.get(
                "OIDC_ISSUER", "http://localhost:8080/realms/mealplan"
            ).rstrip("/"),
            client_id=os.environ.get("OIDC_CLIENT_ID", "mealplan"),
            client_secret=os.environ.get("OIDC_CLIENT_SECRET", ""),
            redirect_uri=os.environ.get(
                "OIDC_REDIRECT_URI", "http://localhost:8000/auth/callback"
            ),
        )

    @property
    def discovery_url(self) -> str:
        """The OIDC discovery document URL for this issuer."""
        return f"{self.issuer.rstrip('/')}/.well-known/openid-configuration"
