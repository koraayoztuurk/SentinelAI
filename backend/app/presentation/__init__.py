"""Presentation layer.

The HTTP boundary of the backend. Following the API Design architecture, this
layer is intentionally thin: it validates and formats requests and responses and
delegates business operations to application services. It never accesses storage
directly or contains business logic.

It exposes the operational ``/health`` endpoint and the application exception
handlers. The versioned business API (``/api/v1``), the request context and the
standard response/error envelope are provided by the API foundation (ES-014); the
resource-specific routers are introduced by the specifications that follow it
(ES-015+).
"""
