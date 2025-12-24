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
    NodeTestResult,
    SuccessResponse
)
from api.services.proxy_service import get_proxy_service

router = APIRouter(prefix="/api/proxies", tags=["Proxies"])


@router.get("", response_model=ProxyListResponse)
async def get_proxies():
    """Get all active proxies."""
    service = get_proxy_service()
    proxies = service.get_all_proxies()
    xray_status = service.get_xray_status()
    
    return ProxyListResponse(
        proxies=[ProxyResponse(
            port=p["port"],
            node_id=p["node_id"],
            node_name=p["node_name"],
            protocol=p["protocol"],
            address=p["address"],
            server_port=p["server_port"],
            test_status=p.get("test_status", "pending"),
            latency_ms=p.get("latency_ms"),
            exit_ip=p.get("exit_ip")
        ) for p in proxies],
        total=len(proxies),
        xray_status=xray_status
    )


@router.post("", response_model=List[ProxyResponse], status_code=status.HTTP_201_CREATED)
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
        
        return [ProxyResponse(
            port=p["port"],
            node_id=p["node_id"],
            node_name=p["node_name"],
            protocol=p["protocol"],
            address=p["address"],
            server_port=p["server_port"],
            test_status=p.get("test_status", "pending")
        ) for p in new_proxies]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{port}", response_model=SuccessResponse)
async def remove_proxy(port: int):
    """Remove a proxy by port."""
    service = get_proxy_service()
    
    if not service.remove_proxy(port):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proxy on port {port} not found"
        )
    
    return SuccessResponse(message=f"Proxy on port {port} removed successfully")


@router.delete("", response_model=SuccessResponse)
async def clear_all_proxies():
    """Remove all proxies."""
    service = get_proxy_service()
    count = service.clear_all_proxies()
    return SuccessResponse(message=f"Removed {count} proxies")


@router.post("/test-all", response_model=ProxyTestAllResponse)
async def test_all_proxies(timeout: int = 5, workers: int = 20):
    """Test all active proxies."""
    service = get_proxy_service()
    
    try:
        results = service.test_all_proxies(timeout=timeout, workers=workers)
        
        success_count = sum(1 for r in results if r.get("status") == "success")
        failed_count = len(results) - success_count
        
        return ProxyTestAllResponse(
            results=[NodeTestResult(
                node_id=r["node_id"],
                name=r["name"],
                status=r["status"],
                latency_ms=r.get("latency_ms"),
                exit_ip=r.get("exit_ip"),
                error=r.get("error")
            ) for r in results],
            success_count=success_count,
            failed_count=failed_count
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{port}/test", response_model=NodeTestResult)
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
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
