# -*- coding: utf-8 -*-
"""
Plain text / URI line subscription decoder.
"""

from .base import DecodedSubscription


def decode_plain_text(content: str) -> DecodedSubscription:
    """Treat content as plain multi-line URI text."""
    return DecodedSubscription(mode="uri_lines", content=content)
