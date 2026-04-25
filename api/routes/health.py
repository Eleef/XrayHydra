"""
Health monitoring API routes.
"""
from fastapi import APIRouter, HTTPException, status
from typing import List

from api.schemas.models import (
    HealthStatusListResponse,
    HealthConfigResponse,
    HealthConfigUpdate,
    ProxyHealthResponse,
    SuccessResponse,
    TestTargetPreset,
    ErrorResponse,
)
from api.services.health_service import get_health_service
from api.services.proxy_service import get_proxy_service

router = APIRouter(prefix="/api/health", tags=["Health"])


@router.get("/status", response_model=HealthStatusListResponse, operation_id="getHealthStatus")
async def get_health_status():
    """Get health status for all monitored proxies."""
    service = get_health_service()
    states = service.get_all_health_states()
    
    # Count by status
    healthy_count = sum(1 for s in states if s.get("status") == "healthy")
    degraded_count = sum(1 for s in states if s.get("status") == "degraded")
    disabled_count = sum(1 for s in states if s.get("status") == "disabled")
    
    return HealthStatusListResponse(
        states=[ProxyHealthResponse(**s) for s in states],
        total=len(states),
        healthy_count=healthy_count,
        degraded_count=degraded_count,
        disabled_count=disabled_count,
    )


@router.get(
    "/status/{port}",
    response_model=ProxyHealthResponse,
    responses={404: {"model": ErrorResponse, "description": "Health state not found"}},
    operation_id="getProxyHealthStatus"
)
async def get_proxy_health_status(port: int):
    """Get health status for a specific proxy."""
    service = get_health_service()
    state = service.get_health_state(port)
    
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No health state for port {port}"
        )
    
    return ProxyHealthResponse(**state)


@router.get("/config", response_model=HealthConfigResponse, operation_id="getHealthConfig")
async def get_health_config():
    """Get health monitoring configuration."""
    service = get_health_service()
    config = service.get_config()
    
    return HealthConfigResponse(
        enabled=config["enabled"],
        check_interval_seconds=config["check_interval_seconds"],
        connectivity_targets=config["connectivity_targets"],
        test_timeout_seconds=config["test_timeout_seconds"],
        test_targets_presets=[
            TestTargetPreset(**p) for p in config["test_targets_presets"]
        ],
        penalty_levels_minutes=config["penalty_levels_minutes"],
        is_monitoring=config["is_monitoring"],
    )


@router.put("/config", response_model=HealthConfigResponse, operation_id="updateHealthConfig")
async def update_health_config(data: HealthConfigUpdate):
    """Update health monitoring configuration."""
    service = get_health_service()
    
    config = service.update_config(
        enabled=data.enabled,
        check_interval_seconds=data.check_interval_seconds,
        connectivity_targets=data.connectivity_targets,
        test_timeout_seconds=data.test_timeout_seconds,
    )
    
    return HealthConfigResponse(
        enabled=config["enabled"],
        check_interval_seconds=config["check_interval_seconds"],
        connectivity_targets=config["connectivity_targets"],
        test_timeout_seconds=config["test_timeout_seconds"],
        test_targets_presets=[
            TestTargetPreset(**p) for p in config["test_targets_presets"]
        ],
        penalty_levels_minutes=config["penalty_levels_minutes"],
        is_monitoring=config["is_monitoring"],
    )


@router.post(
    "/reset/{port}",
    response_model=SuccessResponse,
    responses={404: {"model": ErrorResponse, "description": "Health state not found"}},
    operation_id="resetProxyHealth"
)
async def reset_proxy_health(port: int):
    """Reset health state for a specific proxy."""
    service = get_health_service()
    
    if not service.reset_proxy_health(port):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No health state for port {port}"
        )
    
    return SuccessResponse(message=f"Health state for port {port} reset successfully")


@router.post("/reset-all", response_model=SuccessResponse, operation_id="resetAllHealth")
async def reset_all_health():
    """Reset health states for all proxies."""
    service = get_health_service()
    count = service.reset_all_health()
    return SuccessResponse(message=f"Reset health states for {count} proxies")


@router.post("/check", response_model=HealthStatusListResponse, operation_id="runHealthCheck")
async def run_health_check():
    """
    Manually trigger a health check on all active proxies.
    This is in addition to automatic background monitoring.
    """
    health_service = get_health_service()
    proxy_service = get_proxy_service()
    
    # Get active proxy ports
    ports = proxy_service.get_runtime_proxy_ports()
    
    if not ports:
        return HealthStatusListResponse(
            states=[],
            total=0,
            healthy_count=0,
            degraded_count=0,
            disabled_count=0,
        )
    
    # Run health check
    states = health_service.run_health_check(ports)
    
    # Count by status
    healthy_count = sum(1 for s in states if s.get("status") == "healthy")
    degraded_count = sum(1 for s in states if s.get("status") == "degraded")
    disabled_count = sum(1 for s in states if s.get("status") == "disabled")
    
    return HealthStatusListResponse(
        states=[ProxyHealthResponse(**s) for s in states],
        total=len(states),
        healthy_count=healthy_count,
        degraded_count=degraded_count,
        disabled_count=disabled_count,
    )


@router.post("/monitoring/start", response_model=SuccessResponse, operation_id="startHealthMonitoring")
async def start_monitoring():
    """Start background health monitoring."""
    health_service = get_health_service()
    proxy_service = get_proxy_service()
    
    def get_active_ports():
        return proxy_service.get_runtime_proxy_ports()
    
    if health_service.start_monitoring(get_active_ports):
        return SuccessResponse(message="Health monitoring started")
    else:
        return SuccessResponse(message="Health monitoring already running")


@router.post("/monitoring/stop", response_model=SuccessResponse, operation_id="stopHealthMonitoring")
async def stop_monitoring():
    """Stop background health monitoring."""
    service = get_health_service()
    
    if service.stop_monitoring():
        return SuccessResponse(message="Health monitoring stopped")
    else:
        return SuccessResponse(message="Health monitoring not running")
