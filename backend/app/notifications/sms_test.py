"""Send test SMS via Twilio."""

from __future__ import annotations

import logging

import httpx

from app.config import settings
from app.db.database import get_alert_settings
from app.notifications.credentials import get_twilio_credentials

logger = logging.getLogger(__name__)


async def send_sms_test() -> tuple[bool, str]:
    creds = get_twilio_credentials()
    if not creds:
        return False, "Brak danych Twilio — wklej Account SID, Token i numer nadawcy w aplikacji"

    alert_settings = await get_alert_settings()
    to_number = alert_settings.get("phone") or settings.alert_phone_number
    if not to_number:
        return False, "Brak numeru odbiorcy"

    url = f"https://api.twilio.com/2010-04-01/Accounts/{creds['account_sid']}/Messages.json"
    body = (
        "Cyclical Academy — test SMS\n"
        f"Alerty będą wysyłane na ten numer ({to_number}).\n"
        "Handel pozostaje manualny."
    )
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                url,
                auth=(creds["account_sid"], creds["auth_token"]),
                data={"To": to_number, "From": creds["from_number"], "Body": body},
            )
        if resp.is_success:
            return True, f"SMS wysłany na {to_number}"
        return False, f"Twilio odrzuciło: {resp.status_code} — {resp.text[:200]}"
    except Exception as exc:
        logger.warning("SMS test error: %s", exc)
        return False, str(exc)
