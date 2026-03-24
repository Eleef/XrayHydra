# -*- coding: utf-8 -*-
"""
Registry for protocol-specific URI parsers.
"""

from typing import Callable, Dict, Optional

from ..models import ProxyNode
from .hysteria2 import parse_hysteria2
from .shadowsocks import parse_shadowsocks
from .ssr import parse_ssr
from .trojan import parse_trojan
from .vless import parse_vless
from .vmess import parse_vmess


ParserFunc = Callable[[str], ProxyNode]


class ProtocolParserRegistry:
    """Maps URI prefixes to parser functions."""

    def __init__(self) -> None:
        self._parsers: Dict[str, ParserFunc] = {}

    def register(self, prefix: str, parser: ParserFunc) -> None:
        self._parsers[prefix] = parser

    def resolve(self, uri: str) -> Optional[ParserFunc]:
        for prefix, parser in self._parsers.items():
            if uri.startswith(prefix):
                return parser
        return None

    def parse(self, uri: str) -> Optional[ProxyNode]:
        parser = self.resolve(uri)
        if parser is None:
            return None
        return parser(uri)


def create_default_registry() -> ProtocolParserRegistry:
    registry = ProtocolParserRegistry()
    registry.register("vmess://", parse_vmess)
    registry.register("vless://", parse_vless)
    registry.register("ss://", parse_shadowsocks)
    registry.register("trojan://", parse_trojan)
    registry.register("hysteria2://", parse_hysteria2)
    registry.register("hy2://", parse_hysteria2)
    registry.register("ssr://", parse_ssr)
    return registry
