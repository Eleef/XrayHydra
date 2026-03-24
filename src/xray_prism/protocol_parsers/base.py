# -*- coding: utf-8 -*-
"""
Shared helpers for protocol URI parsers.
"""

import base64
from typing import Optional
from urllib.parse import unquote

from ..models import NetworkType


class ParseError(Exception):
    """Protocol parse error."""


def decode_base64(content: str) -> str:
    """Decode URL-safe / standard base64 content."""
    content = content.strip()
    content = content.replace("-", "+").replace("_", "/")
    padding_needed = 4 - (len(content) % 4)
    if padding_needed != 4:
        content += "=" * padding_needed
    return base64.b64decode(content).decode("utf-8")


def parse_network_type(net: str) -> NetworkType:
    """Normalize network type values."""
    net = net.lower() if net else "tcp"
    mapping = {
        "tcp": NetworkType.TCP,
        "ws": NetworkType.WS,
        "websocket": NetworkType.WS,
        "grpc": NetworkType.GRPC,
        "gun": NetworkType.GRPC,
        "h2": NetworkType.H2,
        "http": NetworkType.H2,
        "kcp": NetworkType.KCP,
        "hysteria": NetworkType.HYSTERIA,
        "hy2": NetworkType.HYSTERIA,
        "hysteria2": NetworkType.HYSTERIA,
    }
    return mapping.get(net, NetworkType.TCP)


def decode_optional_base64_param(value: Optional[str]) -> Optional[str]:
    """Decode optional base64-like param and fall back to URL decoding."""
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        return decode_base64(raw)
    except Exception:
        return unquote(raw)
