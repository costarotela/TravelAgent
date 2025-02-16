"""API endpoints for monitoring and metrics."""
from fastapi import APIRouter, Depends, HTTPException
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from src.core.providers.aero import AeroProvider
from src.core.providers.base import BaseProvider

# Crear el router
router = APIRouter(
    prefix="/monitoring",
    tags=["monitoring"],
    responses={404: {"description": "Not found"}},
)

async def get_provider() -> BaseProvider:
    """Get provider instance."""
    # Por ahora solo tenemos Aero
    # TODO: Hacer esto configurable y permitir múltiples proveedores
    provider = AeroProvider({
        "client_id": "test_client",
        "client_secret": "test_secret"
    })
    try:
        yield provider
    finally:
        await provider.close()

@router.get("/metrics")
async def metrics():
    """Get Prometheus metrics."""
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

@router.get("/status")
async def get_provider_status(
    provider: BaseProvider = Depends(get_provider)
):
    """Get current provider status and metrics."""
    try:
        return await provider.get_status()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting provider status: {str(e)}"
        )
