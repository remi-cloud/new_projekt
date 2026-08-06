from fastapi import APIRouter, HTTPException

from app.db.database import (
    get_alert_settings,
    get_notification_log,
    get_push_subscriptions,
    save_push_subscription,
    update_alert_settings,
)
from app.models.schemas import AlertSettings, NotificationStatus, PushSubscriptionRequest, TwilioConfigRequest
from app.notifications.credentials import save_twilio_credentials, twilio_is_configured
from app.notifications.ntfy import send_ntfy_test
from app.notifications.push import get_vapid_public_key, vapid_configured
from app.notifications.sms_test import send_sms_test

router = APIRouter(tags=["notifications"])


@router.get("/api/notifications/status", response_model=NotificationStatus)
async def notification_status():
    settings_data = await get_alert_settings()
    subs = await get_push_subscriptions()
    topic = settings_data.get("ntfy_topic", "")
    return NotificationStatus(
        push_configured=vapid_configured(),
        sms_configured=twilio_is_configured(),
        ntfy_configured=bool(topic),
        ntfy_subscribe_url=f"https://ntfy.sh/{topic}" if topic else "",
        ntfy_app_url=f"ntfy://{topic}" if topic else "",
        vapid_public_key=get_vapid_public_key(),
        push_subscriptions=len(subs),
        settings=AlertSettings(**settings_data),
    )


@router.get("/api/notifications/settings", response_model=AlertSettings)
async def get_notifications_settings():
    return AlertSettings(**await get_alert_settings())


@router.put("/api/notifications/settings", response_model=AlertSettings)
async def put_notifications_settings(body: AlertSettings):
    updated = await update_alert_settings(body.model_dump())
    return AlertSettings(**updated)


@router.post("/api/notifications/push/subscribe")
async def push_subscribe(body: PushSubscriptionRequest):
    p256dh = body.keys.get("p256dh", "")
    auth = body.keys.get("auth", "")
    if not body.endpoint or not p256dh or not auth:
        raise HTTPException(status_code=400, detail="Niepełna subskrypcja push")
    await save_push_subscription(body.endpoint, p256dh, auth)
    return {"subscribed": True}


@router.get("/api/notifications/log")
async def notification_log(limit: int = 30):
    return await get_notification_log(limit)


@router.post("/api/notifications/twilio")
async def save_twilio_config(body: TwilioConfigRequest):
    if not body.account_sid.startswith("AC") or len(body.auth_token) < 10:
        raise HTTPException(status_code=400, detail="Nieprawidłowe dane Twilio")
    if not body.from_number.startswith("+"):
        raise HTTPException(status_code=400, detail="Numer nadawcy w formacie E.164 (+...)")
    save_twilio_credentials(body.account_sid, body.auth_token, body.from_number)
    return {"saved": True, "sms_configured": True}


@router.post("/api/notifications/test")
async def test_notifications():
    settings_data = await get_alert_settings()
    topic = settings_data.get("ntfy_topic", "")
    results: dict[str, object] = {}

    if settings_data.get("ntfy_enabled") and topic:
        ok = await send_ntfy_test(topic)
        results["ntfy"] = {"ok": ok, "topic": topic, "url": f"https://ntfy.sh/{topic}"}

    sms_ok, sms_msg = await send_sms_test()
    results["sms"] = {"ok": sms_ok, "message": sms_msg}

    return results
