"""
Proxy management API routes.
"""
from fastapi import APIRouter, HTTPException, status
from typing import List

from api.schemas.models import (
    ProxyAddRequest,
    ProxyResponse,
    ProxyListResponse,
    ProxyTestAllResponse,
    ProxyExitIpDedupeRequest,
    ProxyExitIpDedupeResponse,
    ProxyExitIpDuplicatePreviewResponse,
    ProxyExitIpDuplicateGroup,
    ProxyExitIpDuplicateProxy,
    NodeTestResult,
    SuccessResponse,
    ErrorResponse,
)
from api.services.proxy_service import get_proxy_service

router = APIRouter(prefix="/api/proxies", tags=["Proxies"])


@router.get("", response_model=ProxyListResponse, operation_id="listProxies")
async def get_proxies():
    """Get all active proxies."""
    service = get_proxy_service()
    proxies = service.get_all_proxies()
    xray_status = service.get_xray_status()
    xray_running = xray_status == "running"
    runtime_ports = set(service.get_runtime_proxy_ports()) if xray_running else set()
    
    return ProxyListResponse(
        proxies=[ProxyResponse(**{
            **service.build_proxy_access_fields(p["port"]),
            "port": p["port"],
            "node_id": p["node_id"],
            "node_name": p["node_name"],
            "protocol": p["protocol"],
            "address": p["address"],
            "server_port": p["server_port"],
            "test_status": p.get("test_status", "pending"),
            "latency_ms": p.get("latency_ms"),
            "exit_ip": p.get("exit_ip"),
            "pool_status": p.get("pool_status", "active"),
            "disabled_reason": p.get("disabled_reason"),
            **service.get_proxy_runtime_metadata(p, runtime_ports=runtime_ports, xray_running=xray_running),
        }) for p in proxies],
        total=len(proxies),
        xray_status=xray_status
    )


@router.post(
    "",
    response_model=List[ProxyResponse],
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse, "description": "Invalid proxy request"}},
    operation_id="addProxies"
)
async def add_proxies(data: ProxyAddRequest):
    """Add nodes to the active proxy list."""
    service = get_proxy_service()
    
    try:
        new_proxies = service.add_proxies(data.node_ids, data.start_port)
        if not new_proxies:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No new proxies added (nodes may already be in proxy list)"
            )
        
        xray_running = service.get_xray_status() == "running"
        runtime_ports = set(service.get_runtime_proxy_ports()) if xray_running else set()
        return [ProxyResponse(**{
            **service.build_proxy_access_fields(p["port"]),
            "port": p["port"],
            "node_id": p["node_id"],
            "node_name": p["node_name"],
            "protocol": p["protocol"],
            "address": p["address"],
            "server_port": p["server_port"],
            "test_status": p.get("test_status", "pending"),
            "pool_status": p.get("pool_status", "active"),
            "disabled_reason": p.get("disabled_reason"),
            **service.get_proxy_runtime_metadata(p, runtime_ports=runtime_ports, xray_running=xray_running),
        }) for p in new_proxies]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/{port}",
    response_model=SuccessResponse,
    responses={404: {"model": ErrorResponse, "description": "Proxy not found"}},
    operation_id="removeProxy"
)
async def remove_proxy(port: int):
    """Remove a proxy by port."""
    service = get_proxy_service()
    
    if not service.remove_proxy(port):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proxy on port {port} not found"
        )
    
    return SuccessResponse(message=f"Proxy on port {port} removed successfully")


@router.delete("", response_model=SuccessResponse, operation_id="clearAllProxies")
async def clear_all_proxies():
    """Remove all proxies."""
    service = get_proxy_service()
    count = service.clear_all_proxies()
    return SuccessResponse(message=f"Removed {count} proxies")


@router.get(
    "/duplicates/exit-ip",
    response_model=ProxyExitIpDuplicatePreviewResponse,
    operation_id="previewProxyExitIpDuplicates"
)
async def preview_proxy_exit_ip_duplicates():
    """Preview duplicate active proxies that currently share the same exit IP."""
    service = get_proxy_service()
    groups = service.get_exit_ip_duplicate_groups()
    duplicate_proxy_count = sum(len(group["remove_proxies"]) for group in groups)
    return ProxyExitIpDuplicatePreviewResponse(
        groups=[
            ProxyExitIpDuplicateGroup(
                exit_ip=group["exit_ip"],
                keep_proxy=ProxyExitIpDuplicateProxy(**group["keep_proxy"]),
                remove_proxies=[ProxyExitIpDuplicateProxy(**item) for item in group["remove_proxies"]],
            )
            for group in groups
        ],
        duplicate_group_count=len(groups),
        duplicate_proxy_count=duplicate_proxy_count,
    )


@router.post(
    "/dedupe/exit-ip",
    response_model=ProxyExitIpDedupeResponse,
    responses={400: {"model": ErrorResponse, "description": "Invalid duplicate selection"}},
    operation_id="dedupeProxiesByExitIp"
)
async def dedupe_proxies_by_exit_ip(data: ProxyExitIpDedupeRequest):
    """Disable duplicate active proxies after user confirmation."""
    service = get_proxy_service()
    try:
        result = service.dedupe_proxies_by_exit_ip(data.disable_ports)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return ProxyExitIpDedupeResponse(
        disabled_count=result["disabled_count"],
        disabled_ports=result["disabled_ports"],
        kept_ports=result["kept_ports"],
    )


@router.post(
    "/test-all",
    response_model=ProxyTestAllResponse,
    responses={400: {"model": ErrorResponse, "description": "Xray is not running"}},
    operation_id="testAllProxies"
)
async def test_all_proxies(timeout: int = 5, workers: int = 20, attempts: int = 1):
    """Test all active proxies."""
    service = get_proxy_service()
    
    try:
        result = service.test_all_proxies(timeout=timeout, workers=workers, attempts=attempts)
        
        return ProxyTestAllResponse(
            results=[NodeTestResult(
                node_id=r["node_id"],
                name=r["name"],
                proxy_port=r.get("port"),
                status=r["status"],
                latency_ms=r.get("latency_ms"),
                exit_ip=r.get("exit_ip"),
                error=r.get("error")
            ) for r in result["results"]],
            success_count=result["success_count"],
            failed_count=result["failed_count"],
            attempts=result["attempts"],
            cooldown_candidates=result["cooldown_candidates"],
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{port}/test",
    response_model=NodeTestResult,
    responses={
        400: {"model": ErrorResponse, "description": "Xray is not running"},
        404: {"model": ErrorResponse, "description": "Proxy not found"}
    },
    operation_id="testSingleProxy"
)
async def test_single_proxy(port: int, timeout: int = 5):
    """Test a single proxy."""
    service = get_proxy_service()
    
    try:
        result = service.test_single_proxy(port, timeout=timeout)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Proxy on port {port} not found"
            )
        
        return NodeTestResult(
            node_id=result["node_id"],
            name=result["name"],
            status=result["status"],
            latency_ms=result.get("latency_ms"),
            exit_ip=result.get("exit_ip"),
            error=result.get("error")
        )
    except (RuntimeError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
