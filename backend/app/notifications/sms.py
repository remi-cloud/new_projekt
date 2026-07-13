"""SMS alerts via Twilio REST API."""

from __future__ import annotations

import logging

import httpx

from app.config import settings
from app.db.database import get_alert_settings
from app.notifications.credentials import get_twilio_credentials, twilio_is_configured
from app.notifications.alert_engine import AlertEvent

logger = logging.getLogger(__name__)


def twilio_configured() -> bool:
    return twilio_is_configured()


async def send_sms_alerts(events: list[AlertEvent]) -> int:
    creds = get_twilio_credentials()
    if not settings.notifications_enabled or not creds or not events:
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
        f"{creds['account_sid']}/Messages.json"
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
                    auth=(creds["account_sid"], creds["auth_token"]),
                    data={"To": to_number, "From": creds["from_number"], "Body": body[:1500]},
                )
                if resp.is_success:
                    sent += 1
                else:
                    logger.warning("Twilio SMS failed: %s %s", resp.status_code, resp.text[:200])
            except Exception as exc:
                logger.warning("SMS send error: %s", exc)
    return sent
