"""SMS alerts via Twilio REST API."""

from __future__ import annotations

import logging

import httpx

from app.config import settings
from app.db.database import get_alert_settings
from app.notifications.alert_engine import AlertEvent

logger = logging.getLogger(__name__)


def twilio_configured() -> bool:
    return bool(
        settings.twilio_account_sid
        and settings.twilio_auth_token
        and settings.twilio_from_number
    )


async def send_sms_alerts(events: list[AlertEvent]) -> int:
    if not settings.notifications_enabled or not twilio_configured() or not events:
        return 0

    alert_settings = await get_alert_settings()
    if not alert_settings.get("sms_enabled"):
        return 0

    to_number = alert_settings.get("phone") or settings.alert_phone_number
    if not to_number:
        logger.info("SMS enabled but no phone number configured")
        return 0

    url = (
        f"https://api.twilio.com/2010-04-01/Accounts/"
        f"{settings.twilio_account_sid}/Messages.json"
    )
    sent = 0

    async with httpx.AsyncClient(timeout=20) as client:
        for event in events:
            body = (
                f"Cyclical Trader\n"
                f"{event.name} ({event.symbol})\n"
                f"Sygnał: {event.action.upper()} ({event.confidence:.0f}%)\n"
                f"Cena: {event.price}\n"
                f"{event.reason}\n"
                f"Handel manualny — sprawdź aplikację."
            )
            try:
                resp = await client.post(
                    url,
                    auth=(settings.twilio_account_sid, settings.twilio_auth_token),
                    data={"To": to_number, "From": settings.twilio_from_number, "Body": body[:1500]},
                )
                if resp.is_success:
                    sent += 1
                else:
                    logger.warning("Twilio SMS failed: %s %s", resp.status_code, resp.text[:200])
            except Exception as exc:
                logger.warning("SMS send error: %s", exc)
    return sent
