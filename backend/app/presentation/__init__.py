"""Presentation layer.

The HTTP boundary of the backend. Following the API Design architecture, this
layer is intentionally thin: it validates and formats requests and responses and
delegates business operations to application services. It never accesses storage
directly or contains business logic.

In the backend skeleton it exposes the operational ``/health`` endpoint and the
application exception handlers. The versioned business API (and the full response
envelope) is introduced by ES-016 (API Foundation) and the resource-specific
specifications that follow it.
"""
