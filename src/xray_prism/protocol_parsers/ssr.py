# -*- coding: utf-8 -*-
"""
SSR URI parser.
"""

import re
from urllib.parse import parse_qs

from ..models import NetworkType, Protocol, ProxyNode
from .base import ParseError, decode_base64, decode_optional_base64_param


def parse_ssr(uri: str) -> ProxyNode:
    """
    Parse SSR URI.

    Format: ssr://base64(server:port:protocol:method:obfs:base64(password)/?params)
    """
    try:
        encoded = uri.replace("ssr://", "", 1).strip()
        decoded = decode_base64(encoded)
        main_part, _, query = decoded.partition("/?")
        match = re.match(
            r"^(?P<address>.+?):(?P<port>\d+):(?P<ssr_protocol>[^:]+):(?P<method>[^:]+):(?P<obfs>[^:]+):(?P<password>.+)$",
            main_part,
        )
        if not match:
            raise ParseError("无法识别的 SSR 格式")

        params = parse_qs(query, keep_blank_values=True)
        name = decode_optional_base64_param(params.get("remarks", [None])[0]) or "Unknown"

        return ProxyNode(
            name=name,
            protocol=Protocol.SSR,
            address=match.group("address"),
            port=int(match.group("port")),
            password=decode_optional_base64_param(match.group("password")) or "",
            security=match.group("method"),
            network=NetworkType.TCP,
        )
    except ParseError:
        raise
    except Exception as e:
        raise ParseError(f"SSR 解析失败: {e}")
