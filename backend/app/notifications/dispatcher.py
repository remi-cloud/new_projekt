"""Dispatch signal-change alerts via ntfy and/or webhook."""

from __future__ import annotations

import logging

import httpx

from app.db.settings_store import get_alert_settings, log_alert

logger = logging.getLogger(__name__)

ACTION_PL = {
    "buy": "KUPUJ",
    "sell": "SPRZEDAJ",
    "hold": "TRZYMAJ",
    "watch": "OBSERWUJ",
}


def format_change_message(change: dict) -> str:
    prev = ACTION_PL.get(change.get("previous_action") or "", change.get("previous_action") or "—")
    new = ACTION_PL.get(change["new_action"], change["new_action"])
    return (
        f"{change['name']} ({change['symbol']}): {prev} → {new} "
        f"@ {change['new_confidence']}% · ${change['price']}"
    )


async def dispatch_signal_changes(changes: list[dict]) -> dict:
    """Send alerts for qualifying signal changes. Returns delivery summary."""
    if not changes:
        return {"sent": 0, "skipped": 0, "errors": 0}

    cfg = await get_alert_settings()
    if not cfg["enabled"]:
        return {"sent": 0, "skipped": len(changes), "errors": 0, "reason": "disabled"}

    allowed = set(cfg["actions"] or [])
    min_conf = float(cfg["min_confidence"])
    alert_first = cfg["alert_on_first_seen"]

    qualifying: list[dict] = []
    for change in changes:
        if change.get("previous_action") is None and not alert_first:
            continue
        if change["new_action"] not in allowed:
            continue
        if float(change["new_confidence"]) < min_conf:
            continue
        qualifying.append(change)

    if not qualifying:
        return {"sent": 0, "skipped": len(changes), "errors": 0, "reason": "filtered"}

    body = "Cyclical Trader — zmiany sygnałów\n" + "\n".join(
        format_change_message(c) for c in qualifying
    )
    summary = {"sent": 0, "skipped": len(changes) - len(qualifying), "errors": 0}

    if cfg["ntfy_topic"]:
        ok = await _send_ntfy(cfg["ntfy_server"], cfg["ntfy_topic"], body, len(qualifying))
        summary["sent" if ok else "errors"] += 1

    if cfg["webhook_url"]:
        ok = await _send_webhook(cfg["webhook_url"], body, qualifying)
        summary["sent" if ok else "errors"] += 1

    if not cfg["ntfy_topic"] and not cfg["webhook_url"]:
        await log_alert("none", "skipped", body, "No ntfy topic or webhook configured")
        summary["skipped"] += len(qualifying)

    return summary


async def send_test_alert() -> dict:
    cfg = await get_alert_settings()
    body = "Cyclical Trader — test alertu. Skaner działa."
    results = {"ntfy": None, "webhook": None}

    if cfg["ntfy_topic"]:
        results["ntfy"] = await _send_ntfy(cfg["ntfy_server"], cfg["ntfy_topic"], body, 0)
    if cfg["webhook_url"]:
        results["webhook"] = await _send_webhook(cfg["webhook_url"], body, [])
    if results["ntfy"] is None and results["webhook"] is None:
        await log_alert("none", "error", body, "Configure ntfy topic or webhook first")
        return {"ok": False, "detail": "Brak ntfy topic lub webhook URL", "results": results}
    ok = any(v is True for v in results.values())
    return {"ok": ok, "results": results}


async def _send_ntfy(server: str, topic: str, body: str, count: int) -> bool:
    url = f"{server.rstrip('/')}/{topic}"
    headers = {
        "Title": "Cyclical Trader",
        "Priority": "default",
        "Tags": "chart_with_upwards_trend",
    }
    if count:
        headers["Title"] = f"Cyclical Trader · {count} zmian"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, content=body.encode("utf-8"), headers=headers)
            resp.raise_for_status()
        await log_alert("ntfy", "sent", body, f"topic={topic}")
        return True
    except Exception as exc:
        logger.warning("ntfy delivery failed: %s", exc)
        await log_alert("ntfy", "error", body, str(exc))
        return False


async def _send_webhook(url: str, body: str, changes: list[dict]) -> bool:
    payload = {"text": body, "source": "cyclical-trader", "changes": changes}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        await log_alert("webhook", "sent", body, url)
        return True
    except Exception as exc:
        logger.warning("webhook delivery failed: %s", exc)
        await log_alert("webhook", "error", body, str(exc))
        return False
