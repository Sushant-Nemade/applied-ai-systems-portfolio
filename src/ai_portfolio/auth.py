"""Single-tenant API authentication for self-hosted deployments."""

from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, status

from .settings import settings


def require_api_token(x_api_key: str | None = Header(default=None)) -> None:
    if settings.environment == "test":
        return
    if not settings.api_token or not x_api_key or not hmac.compare_digest(x_api_key, settings.api_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API token")
