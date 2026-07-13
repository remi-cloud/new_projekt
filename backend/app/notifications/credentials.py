"""Persist Twilio and notification credentials locally (gitignored data/)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.db.paths import database_path

logger = logging.getLogger(__name__)

CREDENTIALS_PATH = database_path().parent / "credentials.local.json"


def _read() -> dict:
    if not CREDENTIALS_PATH.exists():
        return {}
    try:
        return json.loads(CREDENTIALS_PATH.read_text())
    except Exception as exc:
        logger.warning("Could not read credentials file: %s", exc)
        return {}


def _write(data: dict) -> None:
    CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_PATH.write_text(json.dumps(data, indent=2))
    CREDENTIALS_PATH.chmod(0o600)
    logger.info("Credentials saved to %s", CREDENTIALS_PATH)


def get_twilio_credentials() -> dict | None:
    """DB-stored credentials first, then env vars."""
    data = _read().get("twilio", {})
    sid = data.get("account_sid") or settings.twilio_account_sid
    token = data.get("auth_token") or settings.twilio_auth_token
    from_num = data.get("from_number") or settings.twilio_from_number
    if sid and token and from_num:
        return {"account_sid": sid, "auth_token": token, "from_number": from_num}
    return None


def save_twilio_credentials(account_sid: str, auth_token: str, from_number: str) -> None:
    payload = _read()
    payload["twilio"] = {
        "account_sid": account_sid.strip(),
        "auth_token": auth_token.strip(),
        "from_number": from_number.strip(),
    }
    payload["alert_phone"] = settings.alert_phone_number
    _write(payload)

    # Mirror to process env for current runtime
    settings.twilio_account_sid = account_sid.strip()
    settings.twilio_auth_token = auth_token.strip()
    settings.twilio_from_number = from_number.strip()

    # Persist to .env for server restarts
    _sync_env_file(
        {
            "CYCLICAL_TWILIO_ACCOUNT_SID": account_sid.strip(),
            "CYCLICAL_TWILIO_AUTH_TOKEN": auth_token.strip(),
            "CYCLICAL_TWILIO_FROM_NUMBER": from_number.strip(),
            "CYCLICAL_ALERT_PHONE_NUMBER": settings.alert_phone_number,
        }
    )


def twilio_is_configured() -> bool:
    return get_twilio_credentials() is not None


def _sync_env_file(updates: dict[str, str]) -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    lines: list[str] = []
    existing_keys: set[str] = set()
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            key = line.split("=", 1)[0] if "=" in line else ""
            if key in updates:
                lines.append(f"{key}={updates[key]}")
                existing_keys.add(key)
            else:
                lines.append(line)
    for key, val in updates.items():
        if key not in existing_keys:
            lines.append(f"{key}={val}")
    env_path.write_text("\n".join(lines) + "\n")
    env_path.chmod(0o600)
