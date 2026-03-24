# -*- coding: utf-8 -*-
"""
Subscription decoder registry.
"""

from __future__ import annotations

from typing import Callable, List, Tuple

from .base import DecodedSubscription
from .clash_yaml import decode_clash_yaml, is_clash_yaml
from .plain_text import decode_plain_text


DecoderRule = Tuple[Callable[[str], bool], Callable[[str], DecodedSubscription]]


class SubscriptionDecoderRegistry:
    """Detect subscription content format and normalize it."""

    def __init__(self) -> None:
        self._rules: List[DecoderRule] = []

    def register(self, matcher: Callable[[str], bool], decoder: Callable[[str], DecodedSubscription]) -> None:
        self._rules.append((matcher, decoder))

    def decode(self, content: str) -> DecodedSubscription:
        for matcher, decoder in self._rules:
            if matcher(content):
                return decoder(content)
        return decode_plain_text(content)


def create_default_decoder_registry() -> SubscriptionDecoderRegistry:
    registry = SubscriptionDecoderRegistry()
    registry.register(is_clash_yaml, decode_clash_yaml)
    return registry
