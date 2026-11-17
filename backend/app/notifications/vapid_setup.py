"""Ensure VAPID keys exist for Web Push."""

from __future__ import annotations

import base64
import logging

from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from app.config import settings

logger = logging.getLogger(__name__)


def _as_text(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode()
    return ""


def _application_server_key(vapid) -> str:
    """Uncompressed P-256 point, base64url — what the browser PushManager expects."""
    pub = vapid.public_key
    if isinstance(pub, (str, bytes)):
        return _as_text(pub)
    raw = pub.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def ensure_vapid_keys() -> tuple[str, str]:
    if isinstance(settings.vapid_public_key, str) and settings.vapid_public_key and isinstance(
        settings.vapid_private_key, str
    ) and settings.vapid_private_key:
        return settings.vapid_public_key, settings.vapid_private_key

    try:
        from py_vapid import Vapid

        vapid = Vapid()
        vapid.generate_keys()
        pub = _application_server_key(vapid)
        priv = _as_text(vapid.private_pem())
        settings.vapid_public_key = pub
        settings.vapid_private_key = priv
        logger.warning(
            "Generated ephemeral VAPID keys — set CYCLICAL_VAPID_PUBLIC_KEY and "
            "CYCLICAL_VAPID_PRIVATE_KEY in production for stable push subscriptions"
        )
        return pub, priv
    except Exception as exc:
        logger.warning("Could not generate VAPID keys: %s", exc)
        return "", ""
