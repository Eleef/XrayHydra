# -*- coding: utf-8 -*-
"""
Protocol/runtime capability evaluation.

This module is the single source of truth for deciding whether a parsed node
can enter the current Xray runtime chain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .models import Protocol


RUNTIME_SUPPORTED_PROTOCOLS = frozenset({
    Protocol.VMESS,
    Protocol.VLESS,
    Protocol.SHADOWSOCKS,
    Protocol.TROJAN,
    Protocol.HYSTERIA2,
})


@dataclass(frozen=True)
class RuntimeCapability:
    """Runtime support evaluation result."""

    recognized: bool
    runtime_supported: bool
    support_level: str
    reason: Optional[str] = None


def _get_node_field(node: Any, field: str) -> Any:
    if isinstance(node, dict):
        return node.get(field)
    return getattr(node, field, None)


def normalize_protocol(protocol: Protocol | str) -> Optional[Protocol]:
    """Normalize protocol-like input into a Protocol enum, if recognized."""
    try:
        return protocol if isinstance(protocol, Protocol) else Protocol(str(protocol))
    except ValueError:
        return None


def evaluate_protocol_runtime(protocol: Protocol | str) -> RuntimeCapability:
    """Evaluate runtime support based on protocol type only."""
    normalized = normalize_protocol(protocol)
    if normalized is None:
        return RuntimeCapability(
            recognized=False,
            runtime_supported=False,
            support_level="unsupported",
            reason=f"当前 Xray 运行链路未支持协议 {protocol}",
        )
    if normalized in RUNTIME_SUPPORTED_PROTOCOLS:
        return RuntimeCapability(
            recognized=True,
            runtime_supported=True,
            support_level="native",
            reason=None,
        )
    if normalized == Protocol.SSR:
        reason = "当前 Xray 不支持 SSR（ShadowsocksR）协议"
    else:
        reason = f"当前 Xray 运行链路未支持协议 {normalized.value}"
    return RuntimeCapability(
        recognized=True,
        runtime_supported=False,
        support_level="unsupported",
        reason=reason,
    )


def evaluate_node_runtime(node: Any) -> RuntimeCapability:
    """Evaluate runtime support for a node-like object or mapping."""
    protocol = getattr(node, "protocol", None)
    if protocol is None and isinstance(node, dict):
        protocol = node.get("protocol")
    capability = evaluate_protocol_runtime(protocol)
    if not capability.runtime_supported:
        return capability

    normalized = normalize_protocol(protocol)
    if normalized == Protocol.SHADOWSOCKS:
        plugin = _get_node_field(node, "ss_plugin")
        if plugin:
            plugin_name = str(plugin).strip()
            if plugin_name:
                return RuntimeCapability(
                    recognized=True,
                    runtime_supported=False,
                    support_level="unsupported",
                    reason=f"当前 Xray 运行链路未支持该 Shadowsocks plugin: {plugin_name}",
                )

    return capability


def is_runtime_supported(protocol_or_node: Protocol | str | Any) -> bool:
    """Compatibility helper returning only the runtime-supported flag."""
    if hasattr(protocol_or_node, "protocol") or isinstance(protocol_or_node, dict):
        return evaluate_node_runtime(protocol_or_node).runtime_supported
    return evaluate_protocol_runtime(protocol_or_node).runtime_supported


def get_runtime_support_reason(protocol_or_node: Protocol | str | Any) -> Optional[str]:
    """Compatibility helper returning only the support reason."""
    if hasattr(protocol_or_node, "protocol") or isinstance(protocol_or_node, dict):
        return evaluate_node_runtime(protocol_or_node).reason
    return evaluate_protocol_runtime(protocol_or_node).reason
