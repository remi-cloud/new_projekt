"""Strip configured secrets out of log records and stored error strings.

Values are read from the environment at format time and never written back.
Short placeholders (under 16 characters) are left alone so tests stay readable.
"""

from __future__ import annotations

import logging
import os
import traceback

# Names only. The values stay in the process environment.
_SECRET_ENV = (
    "SOLANA_BOT_PRIVATE_KEY",
    "CYCLICAL_DESK_TOKEN",
    "CYCLICAL_INTERNAL_API_TOKEN",
    "CYCLICAL_X_API_KEY",
    "CYCLICAL_X_API_SECRET",
    "CYCLICAL_X_ACCESS_TOKEN",
    "CYCLICAL_X_ACCESS_TOKEN_SECRET",
    "CHAT_PIN",
)

_installed = False
_MIN_LEN = 16


def active_secrets() -> tuple[str, ...]:
    """Long secret values currently present. Empty strings are ignored."""
    found: list[str] = []
    for name in _SECRET_ENV:
        value = os.environ.get(name, "").strip()
        if len(value) >= _MIN_LEN and "%" not in value and value not in found:
            found.append(value)
    return tuple(found)


def scrub_text(value: object, secrets: tuple[str, ...] | None = None) -> object:
    """Replace known secrets in a string. Other types pass through."""
    if not isinstance(value, str):
        return value
    redacted = value
    for secret in secrets if secrets is not None else active_secrets():
        if secret in redacted:
            redacted = redacted.replace(secret, "[redacted]")
    return redacted


def scrub_record(record: logging.LogRecord) -> None:
    """Rewrite one log record in place, including the traceback text."""
    secrets = active_secrets()
    if not secrets:
        return
    record.msg = scrub_text(record.msg, secrets)
    if isinstance(record.args, tuple):
        record.args = tuple(scrub_text(item, secrets) for item in record.args)
    elif isinstance(record.args, dict):
        record.args = {key: scrub_text(item, secrets) for key, item in record.args.items()}
    elif record.args:
        record.args = scrub_text(record.args, secrets)
    if not record.exc_info or record.exc_info[1] is None:
        return
    text = "".join(traceback.format_exception(*record.exc_info))
    cleaned = scrub_text(text, secrets)
    if cleaned != text:
        record.exc_text = str(cleaned)
        record.exc_info = None


def install_log_redact() -> None:
    """Install a process-wide log factory. Safe to call more than once."""
    global _installed
    if _installed:
        return
    original = logging.getLogRecordFactory()

    def factory(*args, **kwargs):
        record = original(*args, **kwargs)
        scrub_record(record)
        return record

    logging.setLogRecordFactory(factory)
    _installed = True
