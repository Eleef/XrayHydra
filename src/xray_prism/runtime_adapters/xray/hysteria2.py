# -*- coding: utf-8 -*-
"""
Hysteria2 outbound adapter.
"""

from typing import Any, Dict

from ...models import ProxyNode
from .base import StreamSettingsBuilder


def build_hysteria2_outbound(node: ProxyNode, tag: str, _stream_builder: StreamSettingsBuilder) -> Dict[str, Any]:
    stream_settings = {
        "network": "hysteria",
        "security": "tls",
        "tlsSettings": {},
        "hysteriaSettings": {
            "version": 2,
            "auth": node.password or "",
        },
    }

    stream_settings["tlsSettings"]["serverName"] = node.sni or node.address
    if node.allow_insecure:
        stream_settings["tlsSettings"]["allowInsecure"] = True
    if node.fingerprint:
        stream_settings["tlsSettings"]["fingerprint"] = node.fingerprint
    if node.hy_alpn:
        stream_settings["tlsSettings"]["alpn"] = [item.strip() for item in node.hy_alpn.split(",") if item.strip()]
    if node.hy_obfs:
        stream_settings["hysteriaSettings"]["obfs"] = {
            "type": node.hy_obfs,
            "password": node.hy_obfs_password or "",
        }

    return {
        "tag": tag,
        # Xray-core uses the `hysteria` outbound protocol with version=2 transport settings.
        "protocol": "hysteria",
        "settings": {
            "address": node.address,
            "port": node.port,
        },
        "streamSettings": stream_settings,
    }
