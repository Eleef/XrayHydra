# -*- coding: utf-8 -*-
"""
Protocol/runtime capability evaluation.

This module is the single source of truth for deciding whether a parsed node
can enter the current Xray runtime chain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .models import NetworkType, Protocol


RUNTIME_SUPPORTED_PROTOCOLS = frozenset({
    Protocol.VMESS,
    Protocol.VLESS,
    Protocol.SHADOWSOCKS,
    Protocol.TROJAN,
    Protocol.HYSTERIA2,
})

SUPPORTED_STREAM_NETWORKS = frozenset({
    NetworkType.TCP,
    NetworkType.WS,
    NetworkType.GRPC,
    NetworkType.H2,
})
SUPPORTED_VLESS_FLOWS = frozenset({
    "xtls-rprx-vision",
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


def _require_text_field(node: Any, field: str, label: str, protocol_name: str) -> Optional[RuntimeCapability]:
    value = _normalize_optional_text(_get_node_field(node, field))
    if value:
        return None
    return _unsupported_reason(f"当前 {protocol_name} 节点缺少可运行的{label}")


def _normalize_network(node: Any) -> Optional[NetworkType]:
    value = _get_node_field(node, "network")
    if isinstance(value, NetworkType):
        return value
    if value is None:
        return NetworkType.TCP
    if isinstance(value, str) and not value.strip():
        return NetworkType.TCP
    try:
        return NetworkType(str(value))
    except ValueError:
        return None


def _evaluate_common_parse_degradation(node: Any) -> Optional[RuntimeCapability]:
    if bool(_get_node_field(node, "parse_degraded")):
        reason = _normalize_optional_text(_get_node_field(node, "parse_degraded_reason"))
        return _unsupported_reason(reason or "当前节点解析信息不完整，无法进入运行链路")

    raw_network = _normalize_optional_text(_get_node_field(node, "raw_network"))
    if raw_network:
        return _unsupported_reason(f"当前节点使用了未支持的 network 传输类型: {raw_network}")
    return None


def _evaluate_stream_network(node: Any, protocol_name: str) -> Optional[RuntimeCapability]:
    network = _normalize_network(node)
    if network is None:
        return _unsupported_reason(f"当前 {protocol_name} 节点缺少可识别的 network 传输类型")
    if network not in SUPPORTED_STREAM_NETWORKS:
        return _unsupported_reason(f"当前 Xray 运行链路未支持该 {protocol_name} network 传输类型: {network.value}")
    return None


def _evaluate_vmess_runtime(node: Any) -> RuntimeCapability:
    degraded = _evaluate_common_parse_degradation(node)
    if degraded:
        return degraded
    network_check = _evaluate_stream_network(node, "VMess")
    if network_check:
        return network_check
    missing_uuid = _require_text_field(node, "uuid", "UUID", "VMess")
    if missing_uuid:
        return missing_uuid
    return RuntimeCapability(True, True, "native", None)


def _evaluate_vless_runtime(node: Any) -> RuntimeCapability:
    degraded = _evaluate_common_parse_degradation(node)
    if degraded:
        return degraded
    network_check = _evaluate_stream_network(node, "VLESS")
    if network_check:
        return network_check
    missing_uuid = _require_text_field(node, "uuid", "UUID", "VLESS")
    if missing_uuid:
        return missing_uuid
    flow = _normalize_optional_text(_get_node_field(node, "flow"))
    if flow and flow not in SUPPORTED_VLESS_FLOWS:
        return _unsupported_reason(f"当前 Xray 运行链路未支持该 VLESS flow: {flow}")
    return RuntimeCapability(True, True, "native", None)


def _evaluate_trojan_runtime(node: Any) -> RuntimeCapability:
    degraded = _evaluate_common_parse_degradation(node)
    if degraded:
        return degraded
    network_check = _evaluate_stream_network(node, "Trojan")
    if network_check:
        return network_check
    missing_password = _require_text_field(node, "password", "password / 密码信息", "Trojan")
    if missing_password:
        return missing_password
    return RuntimeCapability(True, True, "native", None)


def _evaluate_hysteria2_runtime(node: Any) -> RuntimeCapability:
    degraded = _evaluate_common_parse_degradation(node)
    if degraded:
        return degraded
    network = _normalize_network(node)
    if network != NetworkType.HYSTERIA:
        return _unsupported_reason("当前 Hysteria2 节点 network 传输类型无效")
    missing_password = _require_text_field(node, "password", "password / 密码信息", "Hysteria2")
    if missing_password:
        return missing_password
    obfs = _normalize_optional_text(_get_node_field(node, "hy_obfs"))
    obfs_password = _normalize_optional_text(_get_node_field(node, "hy_obfs_password"))
    if bool(obfs) != bool(obfs_password):
        return _unsupported_reason("当前 Hysteria2 节点 obfs 与 obfs 密码必须成对出现")
    return RuntimeCapability(True, True, "native", None)


def _evaluate_shadowsocks_runtime(node: Any) -> RuntimeCapability:
    degraded = _evaluate_common_parse_degradation(node)
    if degraded:
        return degraded

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

    network = _normalize_network(node)
    if network not in {None, NetworkType.TCP}:
        return _unsupported_reason(
            f"当前 Xray 运行链路未支持该 Shadowsocks network 传输类型: {network.value}"
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
    if normalized == Protocol.VMESS:
        return _evaluate_vmess_runtime(node)
    if normalized == Protocol.VLESS:
        return _evaluate_vless_runtime(node)
    if normalized == Protocol.TROJAN:
        return _evaluate_trojan_runtime(node)
    if normalized == Protocol.HYSTERIA2:
        return _evaluate_hysteria2_runtime(node)
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
