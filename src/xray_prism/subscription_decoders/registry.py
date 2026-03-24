# -*- coding: utf-8 -*-
"""
Subscription decoder registry.
"""

from __future__ import annotations

from typing import Callable, List, Tuple

from .base64_text import decode_base64_subscription, is_base64_subscription
from .base import DecodedSubscription
from .clash_yaml import decode_clash_yaml, is_clash_yaml
from .plain_text import decode_plain_text
from .sip008_json import decode_sip008_json, is_sip008_json


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
    registry.register(is_base64_subscription, decode_base64_subscription)
    registry.register(is_sip008_json, decode_sip008_json)
    registry.register(is_clash_yaml, decode_clash_yaml)
    return registry
