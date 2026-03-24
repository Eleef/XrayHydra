# -*- coding: utf-8 -*-
"""
VMess outbound adapter.
"""

from typing import Any, Dict

from ...models import ProxyNode
from .base import StreamSettingsBuilder


def build_vmess_outbound(node: ProxyNode, tag: str, stream_builder: StreamSettingsBuilder) -> Dict[str, Any]:
    return {
        "tag": tag,
        "protocol": "vmess",
        "settings": {
            "vnext": [{
                "address": node.address,
                "port": node.port,
                "users": [{
                    "id": node.uuid,
                    "alterId": node.alter_id,
                    "security": node.security
                }]
            }]
        },
        "streamSettings": stream_builder(node)
    }

