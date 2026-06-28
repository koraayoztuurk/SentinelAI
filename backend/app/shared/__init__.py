"""Shared kernel.

Holds small, dependency-free building blocks reused across every application
layer. In the backend skeleton this is the base exception hierarchy. The shared
kernel must never contain business logic; it only provides primitives that other
layers build upon.
"""

from app.shared.exceptions import SentinelAIError

__all__ = ["SentinelAIError"]
