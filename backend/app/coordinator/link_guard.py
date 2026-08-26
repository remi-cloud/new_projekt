"""P0 LinkGuard — validate terminal URLs on launch candidates."""

from __future__ import annotations

from app.launch_scout.terminal_url import _AXIOM_CHAINS, _norm_chain


def audit_terminal_urls(candidates: list[dict], *, sample: int = 50) -> dict:
    """Return bad URL counts for coordinator / launch tick telemetry."""
    bad_4meme = 0
    missing_chain_axiom = 0
    missing_url = 0
    checked = 0

    for c in candidates[:sample]:
        checked += 1
        url = str(c.get("url") or c.get("terminal_url") or "")
        chain = _norm_chain(str(c.get("chain") or ""))
        if not url:
            missing_url += 1
            continue
        if ":4meme" in url.lower() or "%3a4meme" in url.lower():
            bad_4meme += 1
        if chain in _AXIOM_CHAINS and "axiom.trade/meme/" in url:
            if "chain=" not in url:
                missing_chain_axiom += 1

    return {
        "checked": checked,
        "bad_4meme": bad_4meme,
        "missing_chain_axiom": missing_chain_axiom,
        "missing_url": missing_url,
        "ok": bad_4meme == 0 and missing_chain_axiom == 0,
    }
