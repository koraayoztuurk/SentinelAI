"""Centralized logging configuration.

Provides a single function that configures the standard library logging system
for the whole application, ensuring consistent log formatting and a configurable
log level. Centralizing this configuration keeps logging behaviour observable and
uniform across every module.
"""

import logging

from app.config.settings import Settings

LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configure_logging(settings: Settings) -> None:
    """Configure application-wide logging.

    The log level is taken from :class:`~app.config.settings.Settings`. An
    invalid level falls back to ``INFO`` so that misconfiguration never prevents
    the application from starting.
    """

    level = logging.getLevelName(settings.log_level.upper())
    if not isinstance(level, int):
        level = logging.INFO

    logging.basicConfig(level=level, format=LOG_FORMAT)
