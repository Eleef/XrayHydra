# -*- coding: utf-8 -*-
"""
VMess protocol parser.
"""

import json

from ..models import NetworkType, Protocol, ProxyNode
from .base import ParseError, decode_base64, resolve_network_type


def parse_vmess(uri: str) -> ProxyNode:
    """Parse a VMess URI into a ProxyNode."""
    try:
        encoded = uri.replace("vmess://", "").strip()
        config = json.loads(decode_base64(encoded))

        name = config.get("ps", config.get("remarks", "Unknown"))
        address = config.get("add", config.get("address", ""))
        port = int(config.get("port", 0))
        uuid = config.get("id", "")
        alter_id = int(config.get("aid", config.get("alterId", 0)))
        security = config.get("scy", config.get("security", "auto"))
        parsed_network = resolve_network_type(config.get("net", config.get("network", "tcp")))
        network = parsed_network.network
        tls = config.get("tls", "") == "tls"
        sni = config.get("sni", config.get("host", ""))
        host = config.get("host", "")
        path = config.get("path", "")
        service_name = config.get("type", "") if network == NetworkType.GRPC else None

        return ProxyNode(
            name=name,
            protocol=Protocol.VMESS,
            address=address,
            port=port,
            uuid=uuid,
            alter_id=alter_id,
            security=security,
            network=network,
            tls=tls,
            sni=sni if sni else None,
            host=host if host else None,
            path=path if path else None,
            service_name=service_name,
            raw_network=parsed_network.unsupported_raw_value,
            parse_degraded=parsed_network.unsupported_raw_value is not None,
            parse_degraded_reason=(
                f"当前节点使用了未支持的 network 传输类型: {parsed_network.unsupported_raw_value}"
                if parsed_network.unsupported_raw_value
                else None
            ),
        )
    except Exception as exc:
        raise ParseError(f"VMess 解析失败: {exc}")
