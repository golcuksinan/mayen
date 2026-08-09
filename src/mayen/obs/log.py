"""Kayıt yapılandırması. Tek yerden kurulur, her yerden alınır."""

import logging

import structlog

type Logger = structlog.stdlib.BoundLogger


def configure(*, level: int = logging.INFO, json: bool = False) -> None:
    """Süreç başına bir kez, mümkün olan en erken anda çağrılır."""
    renderer: structlog.typing.Processor = (
        structlog.processors.JSONRenderer() if json else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> Logger:
    """Modül düzeyinde: `log = get_logger(__name__)`."""
    return structlog.get_logger(name)  # type: ignore[no-any-return]
