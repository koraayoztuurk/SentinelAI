"""API foundation package.

The versioned business API of SentinelAI. Following the API Design architecture,
this layer is a thin communication boundary: it assigns request context, applies
standard response/error envelopes and (from ES-015+) delegates business operations
to backend services. It never accesses persistence or contains business logic.

``API_VERSION`` is the single source of the current API version, matching the
``/api/v1`` router prefix.
"""

API_VERSION = "v1"
