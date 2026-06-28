"""Health endpoint.

Exposes a lightweight operational ``/health`` endpoint used for liveness checks.
The endpoint reports application identity and is independent of any business
capability or backend service.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app import __version__
from app.config.settings import Settings, get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Response model for the health endpoint."""

    status: str
    name: str
    version: str
    environment: str


@router.get("/health", response_model=HealthResponse, summary="Liveness check")
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Return the application's liveness status and identity."""

    return HealthResponse(
        status="ok",
        name=settings.app_name,
        version=__version__,
        environment=settings.app_env,
    )
