"""
Pydantic models for API request/response schemas.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


# ==================== Enums ====================

class ProtocolType(str, Enum):
    VMESS = "vmess"
    VLESS = "vless"
    SHADOWSOCKS = "shadowsocks"
    TROJAN = "trojan"


class XrayStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    ERROR = "error"


class TestStatus(str, Enum):
    PENDING = "pending"
    TESTING = "testing"
    SUCCESS = "success"
    FAILED = "failed"


# ==================== Subscription Schemas ====================

class SubscriptionCreate(BaseModel):
    """Request model for creating a new subscription."""
    name: str = Field(..., min_length=1, max_length=100, description="Subscription name")
    url: str = Field(..., description="Subscription URL")


class SubscriptionResponse(BaseModel):
    """Response model for subscription data."""
    id: str
    name: str
    url: str
    node_count: int = 0
    last_updated: Optional[datetime] = None
    created_at: datetime


class SubscriptionListResponse(BaseModel):
    """Response model for list of subscriptions."""
    subscriptions: List["SubscriptionResponse"]
    total: int


# ==================== Node Schemas ====================

class NodeResponse(BaseModel):
    """Response model for node data."""
    id: str
    subscription_id: str
    name: str
    protocol: ProtocolType
    address: str
    port: int
    test_status: TestStatus = TestStatus.PENDING
    latency_ms: Optional[int] = None
    exit_ip: Optional[str] = None
    exit_country: Optional[str] = None


class NodeListResponse(BaseModel):
    """Response model for list of nodes."""
    nodes: List[NodeResponse]
    total: int


class NodeTestResult(BaseModel):
    """Response model for node test result."""
    node_id: str
    name: str
    status: TestStatus
    latency_ms: Optional[int] = None
    exit_ip: Optional[str] = None
    exit_country: Optional[str] = None
    error: Optional[str] = None


# ==================== Proxy Schemas ====================

class ProxyAddRequest(BaseModel):
    """Request model for adding nodes to proxy list."""
    node_ids: List[str] = Field(..., min_length=1)
    start_port: int = Field(default=10000, ge=1024, le=65535)


class ProxyResponse(BaseModel):
    """Response model for active proxy."""
    port: int
    node_id: str
    node_name: str
    protocol: ProtocolType
    address: str
    server_port: int
    test_status: TestStatus = TestStatus.PENDING
    latency_ms: Optional[int] = None
    exit_ip: Optional[str] = None


class ProxyListResponse(BaseModel):
    """Response model for list of active proxies."""
    proxies: List[ProxyResponse]
    total: int
    xray_status: XrayStatus


class ProxyTestAllResponse(BaseModel):
    """Response model for testing all proxies."""
    results: List[NodeTestResult]
    success_count: int
    failed_count: int


# ==================== System Schemas ====================

class SystemStatusResponse(BaseModel):
    """Response model for system status."""
    xray_status: XrayStatus
    xray_version: Optional[str] = None
    active_proxy_count: int
    subscription_count: int
    uptime_seconds: Optional[int] = None


class SystemActionResponse(BaseModel):
    """Response model for system actions (start/stop/restart)."""
    success: bool
    message: str
    xray_status: XrayStatus


# ==================== Common Schemas ====================

class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
    code: Optional[str] = None


class SuccessResponse(BaseModel):
    """Standard success response."""
    success: bool = True
    message: str
