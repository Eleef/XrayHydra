# -*- coding: utf-8 -*-
"""
Shadowsocks outbound adapter.
"""

from typing import Any, Dict

from ...models import ProxyNode
from .base import StreamSettingsBuilder


def _normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def build_shadowsocks_outbound(node: ProxyNode, tag: str, stream_builder: StreamSettingsBuilder) -> Dict[str, Any]:
    plugin = _normalize_optional_text(node.ss_plugin)
    if plugin:
        raise ValueError(f"当前 Xray 运行链路未支持该 Shadowsocks plugin: {plugin}")
    if _normalize_optional_text(node.ss_plugin_opts):
        raise ValueError("当前 Xray 运行链路未支持该 Shadowsocks plugin 扩展参数")

    method = _normalize_optional_text(node.security)
    if not method or method == "auto":
        raise ValueError("当前 Shadowsocks 节点缺少可运行的加密方法")
    password = _normalize_optional_text(node.password)
    if not password:
        raise ValueError("当前 Shadowsocks 节点缺少可运行的密码信息")

    if node.ss_uot_version is not None:
        try:
            version = int(node.ss_uot_version)
        except (TypeError, ValueError) as exc:
            raise ValueError("当前 Shadowsocks 节点 UoTVersion 格式无效") from exc
        if version <= 0:
            raise ValueError("当前 Shadowsocks 节点 UoTVersion 必须大于 0")

    server: Dict[str, Any] = {
        "address": node.address,
        "port": node.port,
        "method": method,
        "password": password,
    }
    if node.ss_uot is not None:
        server["uot"] = bool(node.ss_uot)
    if node.ss_uot_version is not None:
        server["UoTVersion"] = int(node.ss_uot_version)

    return {
        "tag": tag,
        "protocol": "shadowsocks",
        "settings": {
            "servers": [server]
        },
        "streamSettings": stream_builder(node)
    }
