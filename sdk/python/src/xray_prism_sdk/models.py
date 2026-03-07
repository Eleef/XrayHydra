"""Typed request payloads generated from the OpenAPI schema."""

from __future__ import annotations

from typing import Any
from typing_extensions import NotRequired, TypedDict

class HealthConfigUpdate(TypedDict):
    """Request model for updating health config."""
    enabled: NotRequired[bool | None]
    check_interval_seconds: NotRequired[int | None]
    test_target: NotRequired[str | None]
    test_timeout_seconds: NotRequired[int | None]

class LeaseAcquireRequest(TypedDict):
    """Request model for acquiring a proxy lease."""
    workspace_id: str
    ttl: NotRequired[int]

class LeaseCooldownRequest(TypedDict):
    """Request model for manual cooldown/recall operations."""
    workspace_id: str
    proxy_port: int

class LeaseReleaseRequest(TypedDict):
    """Request model for releasing a proxy lease."""
    workspace_id: str
    proxy_address: str
    cooldown_seconds: NotRequired[int]

class ProxyAddRequest(TypedDict):
    """Request model for adding nodes to proxy list."""
    node_ids: list[str]
    start_port: NotRequired[int]

class SubscriptionCreate(TypedDict):
    """Request model for creating a new subscription."""
    name: str
    url: str
