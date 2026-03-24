# -*- coding: utf-8 -*-
"""
Shadowsocks outbound adapter.
"""

from typing import Any, Dict

from ...models import ProxyNode
from .base import StreamSettingsBuilder


def build_shadowsocks_outbound(node: ProxyNode, tag: str, stream_builder: StreamSettingsBuilder) -> Dict[str, Any]:
    server: Dict[str, Any] = {
        "address": node.address,
        "port": node.port,
        "method": node.security,
        "password": node.password,
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
