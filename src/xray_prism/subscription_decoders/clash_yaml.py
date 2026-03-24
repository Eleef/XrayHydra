# -*- coding: utf-8 -*-
"""
Clash YAML subscription format detection.
"""

from .base import DecodedSubscription


CLASH_KEYWORDS = ("proxies:", "proxy-groups:", "mixed-port:", "port:")


def _looks_like_proxy_list_yaml(content: str) -> bool:
    lines = [line.strip().lower() for line in content.splitlines() if line.strip()]
    if not lines:
        return False
    if not lines[0].startswith("-"):
        return False

    sample = lines[:40]
    has_name = any("name:" in line for line in sample)
    has_type = any("type:" in line for line in sample)
    has_server = any("server:" in line for line in sample)
    has_port = any("port:" in line for line in sample)
    return has_type and has_server and has_port and has_name


def is_clash_yaml(content: str) -> bool:
    """Return whether content looks like Clash YAML."""
    content_lower = content.lower()
    if any(keyword in content_lower for keyword in CLASH_KEYWORDS):
        return True
    return _looks_like_proxy_list_yaml(content)


def decode_clash_yaml(content: str) -> DecodedSubscription:
    """Treat content as Clash YAML."""
    return DecodedSubscription(mode="clash_yaml", content=content)
