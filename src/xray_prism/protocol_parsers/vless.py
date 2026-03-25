# -*- coding: utf-8 -*-
"""
VLESS protocol parser.
"""

from urllib.parse import parse_qs, unquote, urlparse

from ..models import Protocol, ProxyNode
from .base import ParseError, resolve_network_type


def parse_vless(uri: str) -> ProxyNode:
    """Parse a VLESS URI into a ProxyNode."""
    try:
        parsed = urlparse(uri)
        uuid = parsed.username or ""
        address = parsed.hostname or ""
        port = parsed.port or 443
        name = unquote(parsed.fragment) if parsed.fragment else "Unknown"
        params = parse_qs(parsed.query)

        security = params.get("encryption", ["none"])[0]
        parsed_network = resolve_network_type(params.get("type", ["tcp"])[0])
        network = parsed_network.network

        tls_type = params.get("security", ["none"])[0]
        tls = tls_type in ("tls", "reality")
        sni = params.get("sni", [None])[0]
        fingerprint = params.get("fp", [None])[0]

        host = params.get("host", [None])[0]
        path = params.get("path", [None])[0]
        if path:
            path = unquote(path)

        service_name = params.get("serviceName", [None])[0]
        flow = params.get("flow", [None])[0]
        public_key = params.get("pbk", [None])[0]
        short_id = params.get("sid", [None])[0]

        return ProxyNode(
            name=name,
            protocol=Protocol.VLESS,
            address=address,
            port=port,
            uuid=uuid,
            security=security,
            network=network,
            tls=tls,
            sni=sni,
            fingerprint=fingerprint,
            host=host,
            path=path,
            service_name=service_name,
            flow=flow,
            public_key=public_key,
            short_id=short_id,
            raw_network=parsed_network.unsupported_raw_value,
            parse_degraded=parsed_network.unsupported_raw_value is not None,
            parse_degraded_reason=(
                f"当前节点使用了未支持的 network 传输类型: {parsed_network.unsupported_raw_value}"
                if parsed_network.unsupported_raw_value
                else None
            ),
        )
    except Exception as exc:
        raise ParseError(f"VLess 解析失败: {exc}")
