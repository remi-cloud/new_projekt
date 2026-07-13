"""Ensure VAPID keys exist for Web Push."""

from __future__ import annotations

import logging

from app.config import settings

logger = logging.getLogger(__name__)


def ensure_vapid_keys() -> tuple[str, str]:
    if settings.vapid_public_key and settings.vapid_private_key:
        return settings.vapid_public_key, settings.vapid_private_key

    try:
        from py_vapid import Vapid

        vapid = Vapid()
        vapid.generate_keys()
        pub = vapid.public_key
        priv = vapid.private_key
        if isinstance(pub, bytes):
            pub = pub.decode()
        if isinstance(priv, bytes):
            priv = priv.decode()
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
