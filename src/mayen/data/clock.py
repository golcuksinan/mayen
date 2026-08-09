"""Zaman damgası biçimi. Tek yerde, çünkü iki farklı biçim yazan iki modül sıralamayı bozar."""

from datetime import UTC, datetime


def now() -> str:
    """Şu an, ISO-8601 UTC ('2026-08-09T14:03:11Z')."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
