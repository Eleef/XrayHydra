# -*- coding: utf-8 -*-
"""
Clash YAML subscription format detection.
"""

from .base import DecodedSubscription


CLASH_KEYWORDS = ("proxies:", "proxy-groups:", "mixed-port:", "port:")


def is_clash_yaml(content: str) -> bool:
    """Return whether content looks like Clash YAML."""
    content_lower = content.lower()
    return any(keyword in content_lower for keyword in CLASH_KEYWORDS)


def decode_clash_yaml(content: str) -> DecodedSubscription:
    """Treat content as Clash YAML."""
    return DecodedSubscription(mode="clash_yaml", content=content)
