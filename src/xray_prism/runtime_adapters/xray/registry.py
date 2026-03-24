# -*- coding: utf-8 -*-
"""
Registry for protocol -> Xray outbound adapter mapping.
"""

from typing import Any, Dict

from ...models import Protocol, ProxyNode
from .base import OutboundAdapter, StreamSettingsBuilder
from .hysteria2 import build_hysteria2_outbound
from .shadowsocks import build_shadowsocks_outbound
from .trojan import build_trojan_outbound
from .vless import build_vless_outbound
from .vmess import build_vmess_outbound


class XrayAdapterRegistry:
    """Resolve outbound builders by protocol."""

    def __init__(self) -> None:
        self._adapters: Dict[Protocol, OutboundAdapter] = {
            Protocol.VMESS: build_vmess_outbound,
            Protocol.VLESS: build_vless_outbound,
            Protocol.SHADOWSOCKS: build_shadowsocks_outbound,
            Protocol.TROJAN: build_trojan_outbound,
            Protocol.HYSTERIA2: build_hysteria2_outbound,
        }

    def build_outbound(
        self,
        node: ProxyNode,
        tag: str,
        stream_builder: StreamSettingsBuilder,
    ) -> Dict[str, Any]:
        adapter = self._adapters.get(node.protocol)
        if adapter is None:
            raise ValueError(f"不支持的协议: {node.protocol}")
        return adapter(node, tag, stream_builder)

