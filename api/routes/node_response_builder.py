"""
Shared helpers for NodeResponse construction.
"""

from __future__ import annotations

from api.schemas.models import NodeResponse
from src.xray_prism.capabilities import evaluate_node_runtime


def build_node_response(
    node: dict,
    *,
    group_id: str,
    group_type: str,
    subscription_id: str | None,
    proxy_port: int | None,
) -> NodeResponse:
    """Build a NodeResponse while keeping runtime support fields consistent."""
    capability = evaluate_node_runtime(node)
    return NodeResponse(
        id=node["id"],
        group_id=group_id,
        group_type=group_type,
        subscription_id=subscription_id,
        name=node["name"],
        protocol=node["protocol"],
        address=node["address"],
        port=node["port"],
        test_status=node.get("test_status", "pending"),
        latency_ms=node.get("latency_ms"),
        exit_ip=node.get("exit_ip"),
        exit_country=node.get("exit_country"),
        runtime_supported=capability.runtime_supported,
        runtime_support_reason=capability.reason,
        in_proxy_pool=proxy_port is not None,
        proxy_port=proxy_port,
    )
