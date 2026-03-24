# -*- coding: utf-8 -*-
"""
VLESS outbound adapter.
"""

from typing import Any, Dict

from ...models import ProxyNode
from .base import StreamSettingsBuilder


def build_vless_outbound(node: ProxyNode, tag: str, stream_builder: StreamSettingsBuilder) -> Dict[str, Any]:
    user = {
        "id": node.uuid,
        "encryption": node.security or "none"
    }
    if node.flow:
        user["flow"] = node.flow

    return {
        "tag": tag,
        "protocol": "vless",
        "settings": {
            "vnext": [{
                "address": node.address,
                "port": node.port,
                "users": [user]
            }]
        },
        "streamSettings": stream_builder(node)
    }

