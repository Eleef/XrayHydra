# -*- coding: utf-8 -*-
"""
Trojan outbound adapter.
"""

from typing import Any, Dict

from ...models import ProxyNode
from .base import StreamSettingsBuilder


def build_trojan_outbound(node: ProxyNode, tag: str, stream_builder: StreamSettingsBuilder) -> Dict[str, Any]:
    return {
        "tag": tag,
        "protocol": "trojan",
        "settings": {
            "servers": [{
                "address": node.address,
                "port": node.port,
                "password": node.password
            }]
        },
        "streamSettings": stream_builder(node)
    }

