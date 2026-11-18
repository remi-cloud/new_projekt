"""Block server-side fetches to loopback, private networks, and link-local metadata."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx

_BLOCKED_SUFFIXES = (
    ".local",
    ".internal",
    ".localhost",
    ".trycloudflare.com",
    ".ngrok.io",
    ".ngrok.app",
    ".ngrok-free.app",
    ".ngrok-free.dev",
    ".loca.lt",
    ".localhost.run",
    ".lhr.life",
    ".serveo.net",
    ".cfargotunnel.com",
    ".nip.io",
    ".sslip.io",
    ".xip.io",
)


def _routable(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    mapped = getattr(ip, "ipv4_mapped", None)
    if mapped is not None:
        return _routable(mapped)
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _literal_ips(host: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        return [ipaddress.ip_address(host)]
    except ValueError:
        pass
    if host.isdigit():
        try:
            return [ipaddress.ip_address(int(host))]
        except ValueError:
            return []
    if host.lower().startswith("0x"):
        try:
            return [ipaddress.ip_address(int(host, 16))]
        except ValueError:
            return []
    return []


def _blocked_name(host: str) -> bool:
    name = host.lower().rstrip(".")
    if name in {"localhost", "metadata", "metadata.google.internal"}:
        return True
    return any(name.endswith(suffix) for suffix in _BLOCKED_SUFFIXES)


def public_url_ok(url: str | None) -> bool:
    """True only for http(s) URLs whose host resolves to public addresses."""
    if not url:
        return False
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
        return False
    host = (parsed.hostname or "").strip().lower().rstrip(".")
    if not host or _blocked_name(host):
        return False
    literals = _literal_ips(host)
    if literals:
        return all(_routable(ip) for ip in literals)
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    addresses: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for info in infos:
        try:
            addresses.append(ipaddress.ip_address(info[4][0]))
        except ValueError:
            return False
    return bool(addresses) and all(_routable(ip) for ip in addresses)


async def safe_get(
    url: str,
    *,
    timeout: float,
    headers: dict[str, str] | None = None,
    max_redirects: int = 3,
) -> httpx.Response | None:
    """GET a public URL. A redirect is checked again before it is followed."""
    current = url
    async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=False) as client:
        for _ in range(max_redirects + 1):
            if not public_url_ok(current):
                return None
            response = await client.get(current)
            if response.status_code not in {301, 302, 303, 307, 308}:
                return response
            location = response.headers.get("location")
            if not location:
                return None
            current = urljoin(current, location)
    return None
