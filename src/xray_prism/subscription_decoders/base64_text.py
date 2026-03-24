# -*- coding: utf-8 -*-
"""
Base64-encoded subscription payload decoder.
"""

from __future__ import annotations

import base64
from typing import Optional

from .base import DecodedSubscription
from .clash_yaml import decode_clash_yaml, is_clash_yaml
from .sip008_json import decode_sip008_json, is_sip008_json


_PROTOCOL_PREFIXES = (
    "vmess://",
    "vless://",
    "ss://",
    "trojan://",
    "hysteria2://",
    "hy2://",
    "ssr://",
)


def _decode_base64_candidate(content: str) -> Optional[str]:
    candidate = "".join(content.strip().split())
    if not candidate or len(candidate) < 16:
        return None
    if any(prefix in candidate.lower() for prefix in _PROTOCOL_PREFIXES):
        return None
    if any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=_-" for ch in candidate):
        return None

    normalized = candidate.replace("-", "+").replace("_", "/")
    padding = (-len(normalized)) % 4
    if padding:
        normalized += "=" * padding
    try:
        decoded = base64.b64decode(normalized, validate=False).decode("utf-8")
    except Exception:
        return None
    decoded = decoded.strip()
    return decoded or None


def is_base64_subscription(content: str) -> bool:
    """Return whether content looks like a Base64-encoded subscription payload."""
    decoded = _decode_base64_candidate(content)
    if not decoded:
        return False

    lowered = decoded.lower()
    if any(prefix in lowered for prefix in _PROTOCOL_PREFIXES):
        return True
    if is_clash_yaml(decoded):
        return True
    if is_sip008_json(decoded):
        return True
    return False


def decode_base64_subscription(content: str) -> DecodedSubscription:
    """Decode Base64-encoded payload and classify downstream format."""
    decoded = _decode_base64_candidate(content)
    if not decoded:
        return DecodedSubscription(mode="uri_lines", content=content)

    if is_sip008_json(decoded):
        return decode_sip008_json(decoded)
    if is_clash_yaml(decoded):
        return decode_clash_yaml(decoded)
    return DecodedSubscription(mode="uri_lines", content=decoded)

