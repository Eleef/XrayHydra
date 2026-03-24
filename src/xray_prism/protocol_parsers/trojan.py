# -*- coding: utf-8 -*-
"""
Trojan protocol parser.
"""

from urllib.parse import parse_qs, unquote, urlparse

from ..models import Protocol, ProxyNode
from .base import ParseError, parse_network_type


def parse_trojan(uri: str) -> ProxyNode:
    """Parse a Trojan URI into a ProxyNode."""
    try:
        parsed = urlparse(uri)
        password = unquote(parsed.username) if parsed.username else ""
        address = parsed.hostname or ""
        port = parsed.port or 443
        name = unquote(parsed.fragment) if parsed.fragment else "Unknown"
        params = parse_qs(parsed.query)

        network = parse_network_type(params.get("type", ["tcp"])[0])
        tls_type = params.get("security", ["tls"])[0]
        tls = tls_type != "none"
        sni = params.get("sni", [None])[0]
        fingerprint = params.get("fp", [None])[0]
        allow_insecure_str = params.get("allowInsecure", params.get("allowinsecure", ["0"]))[0]
        allow_insecure = allow_insecure_str in ("1", "true", "True")
        host = params.get("host", [None])[0]
        path = params.get("path", [None])[0]
        if path:
            path = unquote(path)
        service_name = params.get("serviceName", [None])[0]

        return ProxyNode(
            name=name,
            protocol=Protocol.TROJAN,
            address=address,
            port=port,
            password=password,
            network=network,
            tls=tls,
            sni=sni,
            fingerprint=fingerprint,
            allow_insecure=allow_insecure,
            host=host,
            path=path,
            service_name=service_name,
        )
    except Exception as exc:
        raise ParseError(f"Trojan 解析失败: {exc}")
