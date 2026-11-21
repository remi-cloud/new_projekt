"""Cope Capital outage helpers.

When the upstream is down we show NO invented traders or buys: the page keeps
the last real rows (with their timestamps) or reports "brak danych".
"""

from __future__ import annotations

def is_cope_unreachable(exc: BaseException | str) -> bool:
    text = str(exc).lower()
    markers = (
        "530",
        "1033",
        "cloudflare tunnel",
        "error code: 1033",
        "connecterror",
        "timed out",
        "timeout",
        "connection refused",
        "name or service not known",
        "temporary failure in name resolution",
        "network is unreachable",
        "non-json response",
    )
    return any(m in text for m in markers)


def humanize_cope_error(exc: BaseException | str) -> str:
    if is_cope_unreachable(exc):
        return (
            "Cope Capital API offline (Cloudflare tunnel 1033/530). "
            "Brak danych na żywo — widoczne są tylko ostatnie realne dane z ich czasem."
        )
    msg = str(exc).strip().replace("\n", " ")
    return msg[:280] if msg else "Cope request failed"
