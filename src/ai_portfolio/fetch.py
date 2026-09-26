"""Constrained HTML fetching for the article service."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit

import httpx

from .settings import settings


class FetchRejected(ValueError):
    pass


def validate_url(url: str) -> str:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower().rstrip(".")
    try:
        port = parts.port
    except ValueError as exc:
        raise FetchRejected("Invalid URL port") from exc
    if parts.scheme != "https" or not host or parts.username or parts.password or port not in (None, 443):
        raise FetchRejected("Only ordinary HTTPS article URLs are allowed")
    if not settings.allowed_fetch_hosts or not any(
        host == allowed or host.endswith("." + allowed) for allowed in settings.allowed_fetch_hosts
    ):
        raise FetchRejected("Host is not in ALLOWED_FETCH_HOSTS")
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise FetchRejected("Host could not be resolved") from exc
    if not addresses or any(not ipaddress.ip_address(entry[4][0]).is_global for entry in addresses):
        raise FetchRejected("Host does not resolve exclusively to public addresses")
    return url


async def fetch_html(url: str, max_bytes: int = 2_000_000) -> str:
    validate_url(url)
    async with httpx.AsyncClient(follow_redirects=False, timeout=15.0) as client:
        async with client.stream("GET", url, headers={"User-Agent": "AppliedAIPortfolio/0.1 (+self-hosted article analysis)"}) as response:
            if response.is_redirect:
                raise FetchRejected("Redirects are disabled")
            response.raise_for_status()
            if "html" not in response.headers.get("content-type", "").lower():
                raise FetchRejected("URL did not return HTML")
            chunks = []
            size = 0
            async for chunk in response.aiter_bytes():
                size += len(chunk)
                if size > max_bytes:
                    raise FetchRejected("Article exceeds the size limit")
                chunks.append(chunk)
    return b"".join(chunks).decode("utf-8", errors="replace")
