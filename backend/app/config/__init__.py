"""Configuration management.

Owns the application configuration loaded from the environment and exposes a
single cached accessor (:func:`get_settings`). Configuration adapts operational
behaviour without redefining architectural responsibilities, consistent with the
Configuration Management architecture document.
"""

from app.config.settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]
