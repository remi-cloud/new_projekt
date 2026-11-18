"""Process-local worker id. Kept apart from the service so imports stay one-way."""

from __future__ import annotations

import uuid

_OWNER = uuid.uuid4().hex


def process_owner() -> str:
    return _OWNER
