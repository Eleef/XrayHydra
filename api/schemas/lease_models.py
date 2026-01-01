"""
Pydantic models for Lease API request/response schemas.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ==================== Request Schemas ====================

class LeaseAcquireRequest(BaseModel):
    """Request model for acquiring a proxy lease."""
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


class LeaseReleaseRequest(BaseModel):
    """Request model for releasing a proxy lease."""
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


# ==================== Response Schemas ====================

class LeaseAcquireResponse(BaseModel):
    """Response model for successful lease acquisition."""
    success: bool = True
    lease_id: str = Field(..., description="Unique lease identifier")
    proxy_address: str = Field(..., description="Proxy address (e.g., '127.0.0.1:10001')")
    expires_at: datetime = Field(..., description="Lease expiration time")


class LeaseReleaseResponse(BaseModel):
    """Response model for lease release."""
    success: bool = True
    cooldown_until: Optional[datetime] = Field(
        None, 
        description="Cooldown end time (null if no cooldown)"
    )


class LeaseErrorResponse(BaseModel):
    """Response model for lease errors."""
    success: bool = False
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")


# ==================== Status Schemas ====================

class ActiveLeaseInfo(BaseModel):
    """Information about an active lease."""
    lease_id: str
    workspace_id: str
    proxy_port: int
    proxy_address: str
    acquired_at: datetime
    expires_at: datetime


class CooldownInfo(BaseModel):
    """Information about a cooldown."""
    workspace_id: str
    proxy_port: int
    until: datetime
    set_at: datetime


class LeaseStatusResponse(BaseModel):
    """Response model for lease status query."""
    workspace_id: Optional[str] = None
    active_leases: List[ActiveLeaseInfo]
    cooldowns: List[CooldownInfo]
    total_active: int
    total_cooldowns: int


class LeaseStatsResponse(BaseModel):
    """Response model for lease statistics."""
    total_available_proxies: int
    total_active_leases: int
    total_cooldowns: int
    workspaces: List[str]
    proxies_by_usage: List[dict]  # [{port, last_used_at, usage_count}]
