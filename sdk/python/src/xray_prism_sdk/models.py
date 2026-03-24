"""Typed API payloads generated from the OpenAPI schema."""

from __future__ import annotations

from typing import Any, Literal
from typing_extensions import NotRequired, TypedDict

class ActiveLeaseInfo(TypedDict):
    """Information about an active lease."""
    lease_id: str
    workspace_id: str
    proxy_port: int
    node_name: NotRequired[str | None]
    proxy_address: str
    proxy_scheme: str
    supported_proxy_protocols: list[str]
    http_proxy_url: str
    socks5_proxy_url: str
    socks5h_proxy_url: str
    acquired_at: str
    expires_at: str

class CooldownInfo(TypedDict):
    """Information about a cooldown."""
    workspace_id: str
    proxy_port: int
    node_name: NotRequired[str | None]
    until: str | None
    set_at: str
    source: Literal['manual', 'timed']

class CustomGroupCopyNodesRequest(TypedDict):
    """Request model for copying existing nodes into a custom group."""
    source_node_ids: list[str]

class CustomGroupCopyNodesResponse(TypedDict):
    """Response model for copying nodes into a custom group."""
    copied_count: int
    skipped_duplicates: int
    total_requested: int
    missing_node_ids: NotRequired[list[str]]

class CustomGroupCreateRequest(TypedDict):
    """Request model for creating a custom node group."""
    name: str

class CustomGroupImportRequest(TypedDict):
    """Request model for importing nodes into a custom node group."""
    content: str

class CustomGroupImportResponse(TypedDict):
    """Response model for importing nodes into a custom group."""
    imported_count: int
    skipped_duplicates: int
    total_parsed: int
    ignored_unsupported_count: NotRequired[int]

class CustomGroupListResponse(TypedDict):
    """Response model for custom node group list."""
    groups: list[CustomGroupResponse]
    total: int

class CustomGroupRenameRequest(TypedDict):
    """Request model for renaming a custom node group."""
    name: str

class CustomGroupResponse(TypedDict):
    """Response model for custom node group metadata."""
    id: str
    name: str
    group_type: NotRequired[GroupType]
    node_count: NotRequired[int]
    created_at: str
    updated_at: str

GroupType = Literal['subscription', 'custom']

class HealthConfigResponse(TypedDict):
    """Response model for health monitoring config."""
    enabled: bool
    check_interval_seconds: int
    test_target: str
    test_timeout_seconds: int
    test_targets_presets: list[TestTargetPreset]
    penalty_levels_minutes: list[int]
    is_monitoring: bool

class HealthConfigUpdate(TypedDict):
    """Request model for updating health config."""
    enabled: NotRequired[bool | None]
    check_interval_seconds: NotRequired[int | None]
    test_target: NotRequired[str | None]
    test_timeout_seconds: NotRequired[int | None]

HealthStatusEnum = Literal['healthy', 'degraded', 'disabled']

class HealthStatusListResponse(TypedDict):
    """Response model for list of health states."""
    states: list[ProxyHealthResponse]
    total: int
    healthy_count: int
    degraded_count: int
    disabled_count: int

class LeaseAcquireRequest(TypedDict):
    """Request model for acquiring a proxy lease."""
    workspace_id: str
    ttl: NotRequired[int]
    initial_port_ordering: NotRequired[LeaseInitialPortOrdering]

class LeaseAcquireResponse(TypedDict):
    """Response model for successful lease acquisition."""
    success: NotRequired[bool]
    lease_id: str
    proxy_address: str
    proxy_scheme: str
    supported_proxy_protocols: list[str]
    http_proxy_url: str
    socks5_proxy_url: str
    socks5h_proxy_url: str
    expires_at: str

class LeaseCooldownActionResponse(TypedDict):
    """Response model for manual cooldown and recall actions."""
    success: NotRequired[bool]
    workspace_id: str
    proxy_port: int
    source: NotRequired[Literal['manual', 'timed'] | None]

class LeaseCooldownRequest(TypedDict):
    """Request model for manual cooldown/recall operations."""
    workspace_id: str
    proxy_port: int

LeaseInitialPortOrdering = Literal['random', 'port_asc']

class LeaseReleaseRequest(TypedDict):
    """Request model for releasing a proxy lease."""
    workspace_id: str
    proxy_address: str
    cooldown_seconds: NotRequired[int]

class LeaseReleaseResponse(TypedDict):
    """Response model for lease release."""
    success: NotRequired[bool]
    cooldown_until: NotRequired[str | None]

class LeaseStatsResponse(TypedDict):
    """Response model for lease statistics."""
    total_available_proxies: int
    total_active_leases: int
    total_cooldowns: int
    workspaces: list[str]
    proxies_by_usage: list[dict[str, Any]]

class LeaseStatusResponse(TypedDict):
    """Response model for lease status query."""
    workspace_id: NotRequired[str | None]
    active_leases: list[ActiveLeaseInfo]
    cooldowns: list[CooldownInfo]
    total_active: int
    total_cooldowns: int
    workspaces: list[WorkspaceLeaseSummary]

class LeaseTimedCooldownBatchRequest(TypedDict):
    """Request model for applying timed cooldowns to multiple proxy ports."""
    workspace_id: str
    proxy_ports: list[int]
    cooldown_seconds: NotRequired[int]

class LeaseTimedCooldownBatchResponse(TypedDict):
    """Response model for applying timed cooldowns to multiple proxy ports."""
    success: NotRequired[bool]
    workspace_id: str
    cooldown_seconds: int
    applied_ports: list[int]
    skipped_ports: list[int]

class NodeBatchTestResponse(TypedDict):
    """Response model for batch node connectivity tests."""
    results: list[NodeTestResult]
    success_count: int
    failed_count: int
    test_profile: NotRequired[str]

class NodeListResponse(TypedDict):
    """Response model for list of nodes."""
    nodes: list[NodeResponse]
    total: int

class NodeResponse(TypedDict):
    """Response model for node data."""
    id: str
    group_id: str
    group_type: GroupType
    subscription_id: NotRequired[str | None]
    name: str
    protocol: ProtocolType
    address: str
    port: int
    test_status: NotRequired[TestStatus]
    latency_ms: NotRequired[int | None]
    exit_ip: NotRequired[str | None]
    exit_country: NotRequired[str | None]
    runtime_supported: NotRequired[bool]
    runtime_support_reason: NotRequired[str | None]
    in_proxy_pool: NotRequired[bool]
    proxy_port: NotRequired[int | None]

class NodeTestJobResponse(TypedDict):
    """Response model for asynchronous node test job progress."""
    job_id: str
    status: NodeTestJobStatus
    total: int
    completed_count: NotRequired[int]
    success_count: NotRequired[int]
    failed_count: NotRequired[int]
    progress_percent: NotRequired[int]
    active_target: NotRequired[str | None]
    target_index: NotRequired[int | None]
    target_total: NotRequired[int | None]
    current_target_completed: NotRequired[int]
    current_target_total: NotRequired[int]
    note: NotRequired[str | None]
    test_profile: NotRequired[str]
    results: NotRequired[list[NodeTestResult]]
    error: NotRequired[str | None]

NodeTestJobStatus = Literal['queued', 'running', 'completed', 'failed']

class NodeTestRequest(TypedDict):
    """Request model for testing subscription nodes."""
    node_ids: list[str]
    timeout: NotRequired[int]
    test_profile: NotRequired[str]

class NodeTestResult(TypedDict):
    """Response model for node test result."""
    node_id: str
    name: str
    proxy_port: NotRequired[int | None]
    status: TestStatus
    latency_ms: NotRequired[int | None]
    exit_ip: NotRequired[str | None]
    exit_country: NotRequired[str | None]
    error: NotRequired[str | None]
    test_profile: NotRequired[str | None]
    tested_target: NotRequired[str | None]
    successful_target: NotRequired[str | None]

ProtocolType = Literal['vmess', 'vless', 'shadowsocks', 'trojan', 'hysteria2', 'ssr']

class ProxyAddRequest(TypedDict):
    """Request model for adding nodes to proxy list."""
    node_ids: list[str]
    start_port: NotRequired[int]

class ProxyCooldownCandidate(TypedDict):
    """A proxy that failed all configured test attempts and may be cooled down."""
    node_id: str
    name: str
    proxy_port: int
    failed_attempts: int
    error: NotRequired[str | None]

class ProxyExitIpDedupeRequest(TypedDict):
    """Request to disable duplicate proxies after preview confirmation."""
    disable_ports: list[int]

class ProxyExitIpDedupeResponse(TypedDict):
    """Response after disabling duplicate proxies by exit IP."""
    disabled_count: int
    disabled_ports: list[int]
    kept_ports: list[int]

class ProxyExitIpDuplicateGroup(TypedDict):
    """One duplicate exit IP group with the recommended keep/remove split."""
    exit_ip: str
    keep_proxy: ProxyExitIpDuplicateProxy
    remove_proxies: list[ProxyExitIpDuplicateProxy]

class ProxyExitIpDuplicatePreviewResponse(TypedDict):
    """Preview response for duplicate exit IP groups in the active proxy pool."""
    groups: list[ProxyExitIpDuplicateGroup]
    duplicate_group_count: int
    duplicate_proxy_count: int

class ProxyExitIpDuplicateProxy(TypedDict):
    """Proxy info used when previewing duplicate exit IP entries."""
    port: int
    node_id: str
    node_name: str
    exit_ip: str
    test_status: NotRequired[TestStatus]
    latency_ms: NotRequired[int | None]

class ProxyHealthResponse(TypedDict):
    """Response model for proxy health state."""
    proxy_port: int
    status: HealthStatusEnum
    failure_count: NotRequired[int]
    penalty_level: NotRequired[int]
    penalty_remaining_seconds: NotRequired[int | None]
    last_check: NotRequired[str | None]
    last_success: NotRequired[str | None]
    last_latency_ms: NotRequired[float | None]

class ProxyListResponse(TypedDict):
    """Response model for list of active proxies."""
    proxies: list[ProxyResponse]
    total: int
    xray_status: XrayStatus

ProxyPoolStatus = Literal['active', 'dedupe_disabled']

class ProxyResponse(TypedDict):
    """Response model for active proxy."""
    port: int
    proxy_address: str
    proxy_scheme: str
    supported_proxy_protocols: list[str]
    http_proxy_url: str
    socks5_proxy_url: str
    socks5h_proxy_url: str
    node_id: str
    node_name: str
    protocol: ProtocolType
    address: str
    server_port: int
    test_status: NotRequired[TestStatus]
    latency_ms: NotRequired[int | None]
    exit_ip: NotRequired[str | None]
    pool_status: NotRequired[ProxyPoolStatus]
    disabled_reason: NotRequired[str | None]

class ProxyTestAllResponse(TypedDict):
    """Response model for testing all proxies."""
    results: list[NodeTestResult]
    success_count: int
    failed_count: int
    attempts: NotRequired[int]
    cooldown_candidates: NotRequired[list[ProxyCooldownCandidate]]

class SubscriptionCreate(TypedDict):
    """Request model for creating a new subscription."""
    name: str
    url: str

class SubscriptionListResponse(TypedDict):
    """Response model for list of subscriptions."""
    subscriptions: list[SubscriptionResponse]
    total: int

class SubscriptionResponse(TypedDict):
    """Response model for subscription data."""
    id: str
    name: str
    url: str
    node_count: NotRequired[int]
    last_updated: NotRequired[str | None]
    created_at: str

class SuccessResponse(TypedDict):
    """Standard success response."""
    success: NotRequired[bool]
    message: str

class SystemActionResponse(TypedDict):
    """Response model for system actions (start/stop/restart)."""
    success: bool
    message: str
    xray_status: XrayStatus

class SystemStatusResponse(TypedDict):
    """Response model for system status."""
    xray_status: XrayStatus
    xray_version: NotRequired[str | None]
    active_proxy_count: int
    subscription_count: int
    uptime_seconds: NotRequired[int | None]

TestStatus = Literal['pending', 'testing', 'success', 'failed']

class TestTargetPreset(TypedDict):
    """Preset test target."""
    name: str
    url: str

class WorkspaceLeaseSummary(TypedDict):
    """Aggregated lease/cooldown counts for one workspace."""
    workspace_id: str
    active_count: int
    cooldown_count: int
    last_activity_at: str

class WorkspaceResetRequest(TypedDict):
    """Request model for workspace reset operations."""
    workspace_id: str

class WorkspaceResetResponse(TypedDict):
    """Response model for workspace reset operations."""
    success: NotRequired[bool]
    workspace_id: str
    released_count: int
    recalled_count: int

XrayStatus = Literal['running', 'stopped', 'starting', 'error']
