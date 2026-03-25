"""
Pydantic models for Lease API request/response schemas.
"""
from datetime import datetime
from enum import Enum
from typing import Literal, Optional, List
from pydantic import BaseModel, Field, ConfigDict


class LeaseInitialPortOrdering(str, Enum):
    """Tie-break strategy when available ports have no prior usage history."""

    RANDOM = "random"
    PORT_ASC = "port_asc"


class LeaseExecutionResult(str, Enum):
    """Optional result marker reported when releasing or freezing a leased proxy."""

    SUCCESS = "success"
    FAILURE = "failure"


# ==================== Request Schemas ====================

class LeaseAcquireRequest(BaseModel):
    """Request model for acquiring a proxy lease."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workspace_id": "amazon_crawler",
                "ttl": 60,
                "initial_port_ordering": "random",
            }
        }
    )
    workspace_id: str = Field(
        ..., 
        min_length=1, 
        max_length=100, 
        description="Workspace identifier for isolation (e.g., 'amazon_crawler')"
    )
    ttl: int = Field(
        default=30, 
        ge=5, 
        le=3600, 
        description="Time-to-live in seconds (default: 30s, max: 1h)"
    )
    initial_port_ordering: LeaseInitialPortOrdering = Field(
        default=LeaseInitialPortOrdering.RANDOM,
        description="Tie-break strategy used only when candidate ports have no prior usage history"
    )


class LeaseReleaseRequest(BaseModel):
    """Request model for releasing a proxy lease."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workspace_id": "amazon_crawler",
                "proxy_address": "127.0.0.1:10001",
                "cooldown_seconds": 300,
                "result": "success",
            }
        }
    )
    workspace_id: str = Field(
        ..., 
        min_length=1, 
        max_length=100, 
        description="Workspace identifier"
    )
    proxy_address: str = Field(
        ..., 
        description="Proxy address to release (e.g., '127.0.0.1:10001')"
    )
    cooldown_seconds: int = Field(
        default=0, 
        ge=0, 
        le=86400, 
        description="Cooldown period in seconds (default: 0, max: 24h)"
    )
    result: Optional[LeaseExecutionResult] = Field(
        default=None,
        description="Optional execution result marker used to increment success/failure metrics"
    )


class LeaseCooldownRequest(BaseModel):
    """Request model for manual cooldown/recall operations."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workspace_id": "amazon_crawler",
                "proxy_port": 10001,
                "result": "failure",
            }
        }
    )
    workspace_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Workspace identifier"
    )
    proxy_port: int = Field(
        ...,
        ge=1,
        le=65535,
        description="Local proxy port"
    )
    result: Optional[LeaseExecutionResult] = Field(
        default=None,
        description="Optional execution result marker used to increment success/failure metrics"
    )


class LeaseTimedCooldownBatchRequest(BaseModel):
    """Request model for applying timed cooldowns to multiple proxy ports."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workspace_id": "amazon_crawler",
                "proxy_ports": [10001, 10002],
                "cooldown_seconds": 300,
                "result": "failure",
            }
        }
    )
    workspace_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Workspace identifier"
    )
    proxy_ports: List[int] = Field(
        ...,
        min_length=1,
        description="Local proxy ports to cool down"
    )
    cooldown_seconds: int = Field(
        default=300,
        ge=1,
        le=86400,
        description="Timed cooldown duration in seconds"
    )
    result: Optional[LeaseExecutionResult] = Field(
        default=None,
        description="Optional execution result marker applied to successfully cooled-down ports"
    )


class WorkspaceResetRequest(BaseModel):
    """Request model for workspace reset operations."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workspace_id": "amazon_crawler",
                "clear_metrics": False,
            }
        }
    )
    workspace_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Workspace identifier to reset"
    )
    clear_metrics: bool = Field(
        default=False,
        description="Whether to clear persisted usage/success/failure metrics for the workspace"
    )


# ==================== Response Schemas ====================

class LeaseProxyMetrics(BaseModel):
    """Workspace-scoped usage metrics for one leased proxy port."""

    usage_count: int = Field(..., description="Total acquire count for this workspace and local proxy port")
    success_count: int = Field(..., description="Reported success count for this workspace and local proxy port")
    failure_count: int = Field(..., description="Reported failure count for this workspace and local proxy port")
    last_used_at: Optional[datetime] = Field(
        default=None,
        description="Most recent acquire timestamp for this workspace and local proxy port"
    )


class LeaseUsageStatsItem(BaseModel):
    """Aggregated usage metrics row returned by lease statistics."""

    workspace_id: str
    port: int
    usage_count: int
    success_count: int
    failure_count: int
    last_used_at: Optional[datetime] = None

class LeaseAcquireResponse(BaseModel):
    """Response model for successful lease acquisition."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "lease_id": "550e8400-e29b-41d4-a716-446655440000",
                "proxy_address": "127.0.0.1:10001",
                "proxy_scheme": "http",
                "supported_proxy_protocols": ["http", "socks5"],
                "http_proxy_url": "http://127.0.0.1:10001",
                "socks5_proxy_url": "socks5://127.0.0.1:10001",
                "socks5h_proxy_url": "socks5h://127.0.0.1:10001",
                "expires_at": "2026-03-07T03:10:00",
                "metrics": {
                    "usage_count": 12,
                    "success_count": 9,
                    "failure_count": 3,
                    "last_used_at": "2026-03-07T03:10:00"
                }
            }
        }
    )
    success: bool = True
    lease_id: str = Field(..., description="Unique lease identifier")
    proxy_address: str = Field(..., description="Proxy address (e.g., '127.0.0.1:10001')")
    proxy_scheme: str = Field(..., description="Default proxy URL scheme for backward-compatible clients")
    supported_proxy_protocols: List[str] = Field(..., description="Client protocols supported by the same local port")
    http_proxy_url: str = Field(..., description="HTTP proxy URL for the leased local port")
    socks5_proxy_url: str = Field(..., description="SOCKS5 proxy URL for the leased local port")
    socks5h_proxy_url: str = Field(..., description="SOCKS5H proxy URL for the leased local port (remote DNS)")
    expires_at: datetime = Field(..., description="Lease expiration time")
    metrics: LeaseProxyMetrics = Field(..., description="Workspace-scoped usage metrics for this port")


class LeaseReleaseResponse(BaseModel):
    """Response model for lease release."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "cooldown_until": "2026-03-07T03:15:00"
            }
        }
    )
    success: bool = True
    cooldown_until: Optional[datetime] = Field(
        None,
        description="Cooldown end time (null if no cooldown)"
    )


class LeaseCooldownActionResponse(BaseModel):
    """Response model for manual cooldown and recall actions."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "workspace_id": "amazon_crawler",
                "proxy_port": 10001,
                "source": "manual"
            }
        }
    )
    success: bool = True
    workspace_id: str
    proxy_port: int
    source: Optional[Literal["manual", "timed"]] = Field(
        default=None,
        description="Cooldown source that was created or recalled"
    )


class WorkspaceResetResponse(BaseModel):
    """Response model for workspace reset operations."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "workspace_id": "amazon_crawler",
                "released_count": 2,
                "recalled_count": 3,
                "cleared_metric_entries": 4,
            }
        }
    )
    success: bool = True
    workspace_id: str
    released_count: int = Field(..., description="Number of active leases removed for the workspace")
    recalled_count: int = Field(..., description="Number of cooldown records removed for the workspace")
    cleared_metric_entries: int = Field(..., description="Number of persisted metric entries removed for the workspace")


class LeaseTimedCooldownBatchResponse(BaseModel):
    """Response model for applying timed cooldowns to multiple proxy ports."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "workspace_id": "amazon_crawler",
                "cooldown_seconds": 300,
                "applied_ports": [10001],
                "skipped_ports": [10002],
            }
        }
    )
    success: bool = True
    workspace_id: str
    cooldown_seconds: int
    applied_ports: List[int]
    skipped_ports: List[int]


class LeaseErrorResponse(BaseModel):
    """Response model for lease errors."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "error": "no_available_proxy",
                "message": "所有代理均被占用或冷却中"
            }
        }
    )
    success: bool = False
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")


# ==================== Status Schemas ====================

class ActiveLeaseInfo(BaseModel):
    """Information about an active lease."""
    lease_id: str
    workspace_id: str
    proxy_port: int
    node_name: Optional[str] = None
    proxy_address: str
    proxy_scheme: str
    supported_proxy_protocols: List[str]
    http_proxy_url: str
    socks5_proxy_url: str
    socks5h_proxy_url: str
    acquired_at: datetime
    expires_at: datetime
    metrics: LeaseProxyMetrics


class CooldownInfo(BaseModel):
    """Information about a cooldown."""
    workspace_id: str
    proxy_port: int
    node_name: Optional[str] = None
    until: Optional[datetime]
    set_at: datetime
    source: Literal["manual", "timed"]
    metrics: LeaseProxyMetrics


class WorkspaceLeaseSummary(BaseModel):
    """Aggregated lease/cooldown counts for one workspace."""
    workspace_id: str
    active_count: int
    cooldown_count: int
    last_activity_at: datetime


class LeaseStatusResponse(BaseModel):
    """Response model for lease status query."""
    workspace_id: Optional[str] = None
    active_leases: List[ActiveLeaseInfo]
    cooldowns: List[CooldownInfo]
    total_active: int
    total_cooldowns: int
    workspaces: List[WorkspaceLeaseSummary]


class LeaseStatsResponse(BaseModel):
    """Response model for lease statistics."""
    total_available_proxies: int
    total_active_leases: int
    total_cooldowns: int
    workspaces: List[str]
    proxies_by_usage: List[LeaseUsageStatsItem]
