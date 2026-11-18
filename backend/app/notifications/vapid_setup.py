"""Ensure VAPID keys exist for Web Push."""

from __future__ import annotations

import base64
import logging

from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from app.config import settings

logger = logging.getLogger(__name__)


def ensure_vapid_keys() -> tuple[str, str]:
    if isinstance(settings.vapid_public_key, str) and settings.vapid_public_key and isinstance(
        settings.vapid_private_key, str
    ) and settings.vapid_private_key:
        return settings.vapid_public_key, settings.vapid_private_key

    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec

        key = ec.generate_private_key(ec.SECP256R1())
        priv = key.private_bytes(
            Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode()
        pub = base64.urlsafe_b64encode(
            key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
        ).decode().rstrip("=")
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
