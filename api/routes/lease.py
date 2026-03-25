"""
Lease API routes.
Provides endpoints for proxy lease management with workspace isolation.

Authentication:
    - Disabled by default
    - Enable by setting LEASE_API_TOKEN environment variable
    - When enabled, requests must include "Authorization: Bearer <token>" header
"""
import os
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Security
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.schemas.lease_models import (
    LeaseAcquireRequest,
    LeaseAcquireResponse,
    LeaseReleaseRequest,
    LeaseReleaseResponse,
    LeaseCooldownRequest,
    LeaseTimedCooldownBatchRequest,
    LeaseCooldownActionResponse,
    LeaseTimedCooldownBatchResponse,
    WorkspaceResetRequest,
    WorkspaceResetResponse,
    LeaseErrorResponse,
    LeaseStatusResponse,
    LeaseStatsResponse,
    ActiveLeaseInfo,
    CooldownInfo,
    LeaseProxyMetrics,
    LeaseUsageStatsItem,
    WorkspaceLeaseSummary,
)
from api.services.lease_service import get_lease_manager
from api.schemas.models import ErrorResponse
from api.services.proxy_service import build_proxy_access_fields
from api.services.proxy_service import ProxyService

# Configurable authentication
# Set LEASE_API_TOKEN environment variable to enable
LEASE_API_TOKEN = os.environ.get("LEASE_API_TOKEN", "")
lease_bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="LeaseBearerAuth",
    description="Optional Bearer token for Lease API. Required only when LEASE_API_TOKEN is configured on the server."
)


async def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(lease_bearer_scheme)
):
    """
    Verify Bearer token if authentication is enabled.
    
    Authentication is disabled by default (LEASE_API_TOKEN not set or empty).
    When enabled, requires "Authorization: Bearer <token>" header.
    """
    # Skip auth if token not configured
    if not LEASE_API_TOKEN:
        return None
    
    # Token configured - require auth
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Validate token
    if credentials.credentials != LEASE_API_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return credentials.credentials


router = APIRouter(
    prefix="/api/lease", 
    tags=["Lease"],
    dependencies=[Security(verify_token)]  # Apply auth to all routes
)


def build_lease_metrics(metrics: Optional[dict]) -> LeaseProxyMetrics:
    payload = metrics or {}
    return LeaseProxyMetrics(
        usage_count=int(payload.get("usage_count", 0) or 0),
        success_count=int(payload.get("success_count", 0) or 0),
        failure_count=int(payload.get("failure_count", 0) or 0),
        last_used_at=payload.get("last_used_at"),
    )


@router.post(
    "/acquire",
    response_model=LeaseAcquireResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication failed"},
        503: {"model": LeaseErrorResponse, "description": "No available proxy"}
    },
    operation_id="acquireLease",
    summary="申请代理租约",
    description="""
    为指定 workspace 申请一个代理租约。
    
    - **workspace_id**: 业务隔离标识（不同 workspace 可使用同一代理）
    - **ttl**: 租约有效时间（秒），超时自动释放
    
    返回代理地址和租约ID，或 503 表示无可用代理。
    """
)
async def acquire_lease(request: LeaseAcquireRequest):
    """Acquire a proxy lease for the given workspace."""
    manager = get_lease_manager()
    result = manager.acquire(
        workspace_id=request.workspace_id,
        ttl=request.ttl,
        initial_port_ordering=request.initial_port_ordering.value,
    )
    
    if not result.success:
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": result.error,
                "message": result.message
            }
        )
    
    return LeaseAcquireResponse(
        success=True,
        lease_id=result.lease_id,
        expires_at=result.expires_at,
        metrics=build_lease_metrics(result.metrics),
        **build_proxy_access_fields(result.proxy_port)
    )


@router.post(
    "/release",
    response_model=LeaseReleaseResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid release request"},
        401: {"model": ErrorResponse, "description": "Authentication failed"}
    },
    operation_id="releaseLease",
    summary="归还代理租约",
    description="""
    归还代理租约并可选设置冷却期。
    
    - **workspace_id**: 业务隔离标识
    - **proxy_address**: 要归还的代理地址
    - **cooldown_seconds**: 冷却时间（秒），期间该 workspace 不会再获取此代理
    
    幂等设计：重复归还不会报错。
    """
)
async def release_lease(request: LeaseReleaseRequest):
    """Release a proxy lease and optionally set cooldown."""
    manager = get_lease_manager()
    success, cooldown_until = manager.release(
        workspace_id=request.workspace_id,
        proxy_address=request.proxy_address,
        cooldown_seconds=request.cooldown_seconds,
        result=request.result.value if request.result else None,
    )
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Invalid proxy address format"
        )
    
    return LeaseReleaseResponse(
        success=True,
        cooldown_until=cooldown_until
    )


@router.post(
    "/cooldown/manual",
    response_model=LeaseCooldownActionResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid cooldown request"},
        401: {"model": ErrorResponse, "description": "Authentication failed"},
        409: {"model": ErrorResponse, "description": "Proxy is actively leased by the workspace"},
    },
    operation_id="setManualLeaseCooldown",
    summary="手动冷却代理",
    description="为指定 workspace 的代理端口创建一个仅手动召回结束的冷却记录。"
)
async def set_manual_lease_cooldown(request: LeaseCooldownRequest):
    """Create a manual cooldown for a workspace and proxy port."""
    manager = get_lease_manager()
    success, error = manager.set_manual_cooldown(
        workspace_id=request.workspace_id,
        proxy_port=request.proxy_port,
        result=request.result.value if request.result else None,
    )

    if not success:
        raise HTTPException(status_code=409, detail=error or "Unable to set manual cooldown")

    return LeaseCooldownActionResponse(
        success=True,
        workspace_id=request.workspace_id,
        proxy_port=request.proxy_port,
        source="manual",
    )


@router.post(
    "/cooldown/recall",
    response_model=LeaseCooldownActionResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid recall request"},
        401: {"model": ErrorResponse, "description": "Authentication failed"},
    },
    operation_id="recallLeaseCooldown",
    summary="召回冷却代理",
    description="移除指定 workspace 的代理冷却记录，可用于结束手动冷却或提前结束定时冷却。"
)
async def recall_lease_cooldown(request: LeaseCooldownRequest):
    """Recall an existing cooldown for a workspace and proxy port."""
    manager = get_lease_manager()
    success, source = manager.recall_cooldown(
        workspace_id=request.workspace_id,
        proxy_port=request.proxy_port,
    )

    if not success:
        raise HTTPException(status_code=400, detail="Unable to recall cooldown")

    return LeaseCooldownActionResponse(
        success=True,
        workspace_id=request.workspace_id,
        proxy_port=request.proxy_port,
        source=source,
    )


@router.post(
    "/cooldown/timed/batch",
    response_model=LeaseTimedCooldownBatchResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid timed cooldown batch request"},
        401: {"model": ErrorResponse, "description": "Authentication failed"},
    },
    operation_id="applyTimedLeaseCooldownBatch",
    summary="批量加入定时冷却",
    description="为指定 workspace 的多个代理端口批量加入定时冷却，活跃租约中的端口会被跳过。"
)
async def apply_timed_lease_cooldown_batch(request: LeaseTimedCooldownBatchRequest):
    """Apply timed cooldowns to multiple proxy ports for one workspace."""
    manager = get_lease_manager()
    result = manager.set_timed_cooldowns(
        workspace_id=request.workspace_id,
        proxy_ports=request.proxy_ports,
        cooldown_seconds=request.cooldown_seconds,
        result=request.result.value if request.result else None,
    )
    return LeaseTimedCooldownBatchResponse(success=True, **result)


@router.post(
    "/workspace/reset",
    response_model=WorkspaceResetResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid workspace reset request"},
        401: {"model": ErrorResponse, "description": "Authentication failed"},
    },
    operation_id="resetWorkspaceLeaseState",
    summary="Reset workspace lease state",
    description="Clear the active leases and cooldown records for the specified workspace."
)
async def reset_workspace_lease_state(request: WorkspaceResetRequest):
    """Reset all lease-related state for a workspace."""
    manager = get_lease_manager()
    result = manager.reset_workspace(request.workspace_id, clear_metrics=request.clear_metrics)
    return WorkspaceResetResponse(success=True, **result)


@router.get(
    "/status",
    response_model=LeaseStatusResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication failed"}
    },
    operation_id="getLeaseStatus",
    summary="查看租约状态",
    description="""
    查看当前租约和冷却状态。
    
    - **workspace_id**: 可选，指定则只返回该 workspace 的信息
    """
)
async def get_lease_status(
    workspace_id: Optional[str] = Query(
        None, 
        description="Filter by workspace ID"
    )
):
    """Get current lease and cooldown status."""
    manager = get_lease_manager()
    proxy_service = ProxyService()
    proxy_by_port = {
        proxy["port"]: proxy
        for proxy in proxy_service.get_all_proxies()
    }
    status = manager.get_status(workspace_id=workspace_id)
    
    # Convert to response model
    active_leases = [
        ActiveLeaseInfo(
            lease_id=lease["lease_id"],
            workspace_id=lease["workspace_id"],
            proxy_port=lease["proxy_port"],
            node_name=proxy_by_port.get(lease["proxy_port"], {}).get("node_name"),
            acquired_at=lease["acquired_at"],
            expires_at=lease["expires_at"],
            metrics=build_lease_metrics(lease.get("metrics")),
            **build_proxy_access_fields(lease["proxy_port"])
        )
        for lease in status["active_leases"]
    ]
    
    cooldowns = [
        CooldownInfo(
            workspace_id=cd["workspace_id"],
            proxy_port=cd["proxy_port"],
            node_name=proxy_by_port.get(cd["proxy_port"], {}).get("node_name"),
            until=cd["until"],
            set_at=cd["set_at"],
            source=cd["source"],
            metrics=build_lease_metrics(cd.get("metrics")),
        )
        for cd in status["cooldowns"]
    ]

    workspaces = [
        WorkspaceLeaseSummary(
            workspace_id=workspace["workspace_id"],
            active_count=workspace["active_count"],
            cooldown_count=workspace["cooldown_count"],
            last_activity_at=workspace["last_activity_at"],
        )
        for workspace in status["workspaces"]
    ]
    
    return LeaseStatusResponse(
        workspace_id=status["workspace_id"],
        active_leases=active_leases,
        cooldowns=cooldowns,
        total_active=status["total_active"],
        total_cooldowns=status["total_cooldowns"],
        workspaces=workspaces,
    )


@router.get(
    "/stats",
    response_model=LeaseStatsResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication failed"}
    },
    operation_id="getLeaseStats",
    summary="获取租约统计",
    description="获取租约系统的统计信息，包括可用代理数、活跃租约数、使用频率等。"
)
async def get_lease_stats():
    """Get lease statistics."""
    manager = get_lease_manager()
    stats = manager.get_stats()
    
    return LeaseStatsResponse(
        total_available_proxies=stats["total_available_proxies"],
        total_active_leases=stats["total_active_leases"],
        total_cooldowns=stats["total_cooldowns"],
        workspaces=stats["workspaces"],
        proxies_by_usage=[
            LeaseUsageStatsItem(
                workspace_id=item["workspace_id"],
                port=item["port"],
                usage_count=item["usage_count"],
                success_count=item["success_count"],
                failure_count=item["failure_count"],
                last_used_at=item["last_used_at"],
            )
            for item in stats["proxies_by_usage"]
        ]
    )
