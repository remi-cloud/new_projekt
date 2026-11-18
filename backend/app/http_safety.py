"""Block fetches that can reach loopback, private, or link-local addresses.

Every redirect hop is checked again. A name that does not resolve, or that
resolves to any non-public address, is refused.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx

_REDIRECTS = frozenset({301, 302, 303, 307, 308})


class UnsafeUrlError(ValueError):
    """The URL is not a public http(s) address."""


def _public_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _resolved_ips(host: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        return [literal]
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeUrlError("Adres nie rozwiązuje się na publiczny host.") from exc
    found: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for info in infos:
        try:
            found.append(ipaddress.ip_address(info[4][0]))
        except ValueError:
            continue
    if not found:
        raise UnsafeUrlError("Adres nie rozwiązuje się na publiczny host.")
    return found


def assert_public_http_url(url: str) -> None:
    """Refuse non-http schemes and any hop that is not a public IP."""
    parsed = urlparse((url or "").strip())
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeUrlError("Dozwolone są tylko adresy http i https.")
    if parsed.username or parsed.password:
        raise UnsafeUrlError("Adres z loginem jest zablokowany.")
    host = (parsed.hostname or "").strip().lower().rstrip(".")
    if not host or host == "localhost" or host.endswith(".local") or host.endswith(".localhost"):
        raise UnsafeUrlError("Adres lokalny jest zablokowany.")
    ips = _resolved_ips(host)
    if any(not _public_ip(ip) for ip in ips):
        raise UnsafeUrlError("Adres prywatny, pętla zwrotna albo link-local jest zablokowany.")


async def guarded_get(
    client: httpx.AsyncClient,
    url: str,
    *,
    max_hops: int = 5,
    **kwargs,
) -> httpx.Response:
    """GET without automatic redirects. Each Location is checked before the next hop."""
    current = url
    kwargs.pop("follow_redirects", None)
    for hop in range(max_hops + 1):
        assert_public_http_url(current)
        response = await client.get(current, follow_redirects=False, **kwargs)
        if response.status_code not in _REDIRECTS:
            return response
        if hop == max_hops:
            raise UnsafeUrlError("Za dużo przekierowań.")
        location = (response.headers.get("location") or "").strip()
        if not location:
            return response
        current = urljoin(current, location)
    raise UnsafeUrlError("Za dużo przekierowań.")
