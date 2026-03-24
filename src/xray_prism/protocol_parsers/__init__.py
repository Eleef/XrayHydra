# -*- coding: utf-8 -*-
"""
Protocol parser registry and per-protocol parser modules.
"""

from .base import ParseError
from .hysteria2 import parse_hysteria2
from .registry import ProtocolParserRegistry, create_default_registry
from .shadowsocks import parse_shadowsocks
from .ssr import parse_ssr
from .trojan import parse_trojan
from .vless import parse_vless
from .vmess import parse_vmess

__all__ = [
    "ParseError",
    "ProtocolParserRegistry",
    "create_default_registry",
    "parse_vmess",
    "parse_vless",
    "parse_shadowsocks",
    "parse_trojan",
    "parse_hysteria2",
    "parse_ssr",
]
