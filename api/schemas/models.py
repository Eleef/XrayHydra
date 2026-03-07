"""
Pydantic models for API request/response schemas.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
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
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "My Subscription",
                "url": "https://example.com/subscription"
            }
        }
    )
    name: str = Field(..., min_length=1, max_length=100, description="Subscription name")
    url: str = Field(..., description="Subscription URL")


class SubscriptionResponse(BaseModel):
    """Response model for subscription data."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "sub_ab12cd34",
                "name": "My Subscription",
                "url": "https://example.com/subscription",
                "node_count": 39,
                "last_updated": "2026-03-07T03:10:00",
                "created_at": "2026-03-07T03:09:00"
            }
        }
    )
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
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "node_sub_ab12cd34_0000",
                "subscription_id": "sub_ab12cd34",
                "name": "HK-01",
                "protocol": "trojan",
                "address": "hk.example.com",
                "port": 443,
                "test_status": "pending",
                "latency_ms": None,
                "exit_ip": None,
                "exit_country": None
            }
        }
    )
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
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "node_ids": ["node_sub_ab12cd34_0000", "node_sub_ab12cd34_0001"],
                "start_port": 10000
            }
        }
    )
    node_ids: List[str] = Field(..., min_length=1)
    start_port: int = Field(default=10000, ge=1024, le=65535)


class ProxyResponse(BaseModel):
    """Response model for active proxy."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "port": 10000,
                "proxy_address": "127.0.0.1:10000",
                "proxy_scheme": "http",
                "supported_proxy_protocols": ["http", "socks5"],
                "http_proxy_url": "http://127.0.0.1:10000",
                "socks5_proxy_url": "socks5://127.0.0.1:10000",
                "socks5h_proxy_url": "socks5h://127.0.0.1:10000",
                "node_id": "node_sub_ab12cd34_0000",
                "node_name": "HK-01",
                "protocol": "trojan",
                "address": "hk.example.com",
                "server_port": 443,
                "test_status": "success",
                "latency_ms": 420,
                "exit_ip": "203.0.113.10"
            }
        }
    )
    port: int
    proxy_address: str
    proxy_scheme: str
    supported_proxy_protocols: List[str]
    http_proxy_url: str
    socks5_proxy_url: str
    socks5h_proxy_url: str
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
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "xray_status": "running",
                "xray_version": "v24.12.18",
                "active_proxy_count": 39,
                "subscription_count": 1,
                "uptime_seconds": 120
            }
        }
    )
    xray_status: XrayStatus
    xray_version: Optional[str] = None
    active_proxy_count: int
    subscription_count: int
    uptime_seconds: Optional[int] = None


class SystemActionResponse(BaseModel):
    """Response model for system actions (start/stop/restart)."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Xray started successfully",
                "xray_status": "running"
            }
        }
    )
    success: bool
    message: str
    xray_status: XrayStatus


# ==================== Common Schemas ====================

class ErrorResponse(BaseModel):
    """Standard error response."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "Subscription sub_xxx not found",
                "code": "not_found"
            }
        }
    )
    detail: str
    code: Optional[str] = None


class SuccessResponse(BaseModel):
    """Standard success response."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Operation completed successfully"
            }
        }
    )
    success: bool = True
    message: str


# ==================== Health Monitoring Schemas ====================

class HealthStatusEnum(str, Enum):
    """Health status for a proxy."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DISABLED = "disabled"


class TestTargetPreset(BaseModel):
    """Preset test target."""
    name: str
    url: str


class ProxyHealthResponse(BaseModel):
    """Response model for proxy health state."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "proxy_port": 10000,
                "status": "healthy",
                "failure_count": 0,
                "penalty_level": 0,
                "penalty_remaining_seconds": None,
                "last_check": "2026-03-07T03:10:00",
                "last_success": "2026-03-07T03:10:00",
                "last_latency_ms": 386.12
            }
        }
    )
    proxy_port: int
    status: HealthStatusEnum
    failure_count: int = 0
    penalty_level: int = 0
    penalty_remaining_seconds: Optional[int] = None
    last_check: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_latency_ms: Optional[float] = None


class HealthStatusListResponse(BaseModel):
    """Response model for list of health states."""
    states: List[ProxyHealthResponse]
    total: int
    healthy_count: int
    degraded_count: int
    disabled_count: int


class HealthConfigResponse(BaseModel):
    """Response model for health monitoring config."""
    enabled: bool
    check_interval_seconds: int
    test_target: str
    test_timeout_seconds: int
    test_targets_presets: List[TestTargetPreset]
    penalty_levels_minutes: List[int]
    is_monitoring: bool


class HealthConfigUpdate(BaseModel):
    """Request model for updating health config."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "enabled": True,
                "check_interval_seconds": 60,
                "test_target": "http://ip-api.com/json",
                "test_timeout_seconds": 5
            }
        }
    )
    enabled: Optional[bool] = None
    check_interval_seconds: Optional[int] = Field(None, ge=10, le=3600)
    test_target: Optional[str] = None
    test_timeout_seconds: Optional[int] = Field(None, ge=1, le=30)
