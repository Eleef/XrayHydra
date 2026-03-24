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


def _normalize_optional_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _unsupported_reason(reason: str) -> RuntimeCapability:
    return RuntimeCapability(
        recognized=True,
        runtime_supported=False,
        support_level="unsupported",
        reason=reason,
    )


def _evaluate_shadowsocks_runtime(node: Any) -> RuntimeCapability:
    plugin = _normalize_optional_text(_get_node_field(node, "ss_plugin"))
    plugin_opts = _normalize_optional_text(_get_node_field(node, "ss_plugin_opts"))
    if plugin:
        return _unsupported_reason(
            f"当前 Xray 运行链路未支持该 Shadowsocks plugin: {plugin}"
        )
    if plugin_opts:
        return _unsupported_reason(
            "当前 Xray 运行链路未支持该 Shadowsocks plugin 扩展参数"
        )

    method = _normalize_optional_text(_get_node_field(node, "security"))
    if not method or method == "auto":
        return _unsupported_reason(
            "当前 Shadowsocks 节点缺少可运行的加密方法"
        )

    password = _normalize_optional_text(_get_node_field(node, "password"))
    if not password:
        return _unsupported_reason(
            "当前 Shadowsocks 节点缺少可运行的密码信息"
        )

    uot_version = _get_node_field(node, "ss_uot_version")
    if uot_version is not None:
        try:
            version = int(uot_version)
        except (TypeError, ValueError):
            return _unsupported_reason(
                "当前 Shadowsocks 节点 UoTVersion 格式无效"
            )
        if version <= 0:
            return _unsupported_reason(
                "当前 Shadowsocks 节点 UoTVersion 必须大于 0"
            )

    return RuntimeCapability(
        recognized=True,
        runtime_supported=True,
        support_level="native",
        reason=None,
    )


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
        return _evaluate_shadowsocks_runtime(node)

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
