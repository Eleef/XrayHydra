# -*- coding: utf-8 -*-
"""
Hysteria2 URI parser.
"""

from urllib.parse import parse_qs, unquote, urlparse

from ..models import NetworkType, Protocol, ProxyNode
from .base import ParseError


def parse_hysteria2(uri: str) -> ProxyNode:
    """
    Parse Hysteria2 URI.

    Common formats:
    hysteria2://password@host:port/?insecure=1&sni=example.com#name
    hy2://password@host:port/?insecure=1&sni=example.com#name
    """
    try:
        normalized_uri = uri
        if normalized_uri.startswith("hy2://"):
            normalized_uri = "hysteria2://" + normalized_uri[len("hy2://") :]

        parsed = urlparse(normalized_uri)
        password = unquote(parsed.username) if parsed.username else ""
        address = parsed.hostname or ""
        port = parsed.port or 443
        name = unquote(parsed.fragment) if parsed.fragment else "Unknown"

        params = parse_qs(parsed.query)
        sni = params.get("sni", [None])[0] or params.get("peer", [None])[0]
        insecure_raw = params.get("insecure", params.get("allowInsecure", ["0"]))[0]
        allow_insecure = str(insecure_raw).lower() in ("1", "true", "yes")
        alpn = params.get("alpn", [None])[0]
        obfs = params.get("obfs", [None])[0]
        obfs_password = (
            params.get("obfs-password", [None])[0]
            or params.get("obfs_password", [None])[0]
        )

        return ProxyNode(
            name=name,
            protocol=Protocol.HYSTERIA2,
            address=address,
            port=port,
            password=password,
            network=NetworkType.HYSTERIA,
            tls=True,
            sni=sni or address,
            allow_insecure=allow_insecure,
            hy_obfs=obfs,
            hy_obfs_password=obfs_password,
            hy_alpn=alpn,
        )
    except Exception as e:
        raise ParseError(f"Hysteria2 解析失败: {e}")
