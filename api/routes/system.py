"""
System control API routes.
"""
from fastapi import APIRouter

from api.schemas.models import (
    SystemStatusResponse,
    SystemActionResponse,
    XrayStatus,
    ErrorResponse,
)
from api.services.proxy_service import get_proxy_service
from api.services.subscription_service import get_subscription_service
from src.xray_prism.runner import XRAY_VERSION

router = APIRouter(prefix="/api/system", tags=["System"])


@router.get("/status", response_model=SystemStatusResponse, operation_id="getSystemStatus")
async def get_system_status():
    """Get overall system status."""
    proxy_service = get_proxy_service()
    subscription_service = get_subscription_service()
    
    proxies = proxy_service.get_all_proxies(include_disabled=False)
    subscriptions = subscription_service.get_all_subscriptions()
    xray_status = proxy_service.get_xray_status()
    uptime = proxy_service.get_uptime()
    
    return SystemStatusResponse(
        xray_status=xray_status,
        xray_version=XRAY_VERSION,
        active_proxy_count=len(proxies),
        subscription_count=len(subscriptions),
        uptime_seconds=uptime
    )


@router.post(
    "/start",
    response_model=SystemActionResponse,
    responses={400: {"model": ErrorResponse, "description": "System start failed"}},
    operation_id="startXray"
)
async def start_xray():
    """Start the Xray process."""
    service = get_proxy_service()
    result = service.start_xray()
    
    return SystemActionResponse(
        success=result["success"],
        message=result["message"],
        xray_status=XrayStatus(result["status"])
    )


@router.post(
    "/stop",
    response_model=SystemActionResponse,
    responses={400: {"model": ErrorResponse, "description": "System stop failed"}},
    operation_id="stopXray"
)
async def stop_xray():
    """Stop the Xray process."""
    service = get_proxy_service()
    result = service.stop_xray()
    
    return SystemActionResponse(
        success=result["success"],
        message=result["message"],
        xray_status=XrayStatus(result["status"])
    )


@router.post(
    "/restart",
    response_model=SystemActionResponse,
    responses={400: {"model": ErrorResponse, "description": "System restart failed"}},
    operation_id="restartXray"
)
async def restart_xray():
    """Restart the Xray process."""
    service = get_proxy_service()
    result = service.restart_xray()
    
    return SystemActionResponse(
        success=result["success"],
        message=result["message"],
        xray_status=XrayStatus(result["status"])
    )
