"""P0 LinkGuard — validate terminal URLs on launch candidates + Axiom desk."""

from __future__ import annotations

from app.launch_scout.terminal_url import _norm_chain


def _audit_rows(rows: list[dict], *, sample: int = 50) -> dict:
    bad_4meme = 0
    missing_chain_axiom = 0
    missing_url = 0
    checked = 0

    for c in rows[:sample]:
        checked += 1
        url = str(c.get("url") or c.get("terminal_url") or "")
        chain = _norm_chain(str(c.get("chain") or ""))
        if not url:
            missing_url += 1
            continue
        if ":4meme" in url.lower() or "%3a4meme" in url.lower():
            bad_4meme += 1
        if "axiom.trade/meme/" in url and "chain=" not in url:
            missing_chain_axiom += 1

    return {
        "checked": checked,
        "bad_4meme": bad_4meme,
        "missing_chain_axiom": missing_chain_axiom,
        "missing_url": missing_url,
        "ok": bad_4meme == 0 and missing_chain_axiom == 0,
    }


def audit_terminal_urls(candidates: list[dict], *, sample: int = 50) -> dict:
    """Return bad URL counts for coordinator / launch tick telemetry."""
    return _audit_rows(candidates, sample=sample)


def audit_axiom_urls(pulse: list[dict], positions: list[dict], *, sample: int = 40) -> dict:
    """Audit Axiom Pulse + positions for missing chain= on meme deep links."""
    rows = list(pulse[:sample]) + list(positions[:sample])
    return _audit_rows(rows, sample=sample * 2)


def link_guard_bad_count(lg: dict | None) -> int:
    """Total bad terminal URLs across Launch + Axiom samples."""
    if not lg:
        return 0
    return (
        int(lg.get("bad_4meme") or 0)
        + int(lg.get("missing_chain_axiom") or 0)
        + int(lg.get("axiom_missing_chain") or 0)
        + int(lg.get("axiom_bad_4meme") or 0)
    )


def link_guard_ok(lg: dict | None) -> bool:
    return link_guard_bad_count(lg) == 0
