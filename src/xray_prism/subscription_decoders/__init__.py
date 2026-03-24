# -*- coding: utf-8 -*-
"""
Subscription content decoders.
"""

from .base import DecodedSubscription
from .base64_text import decode_base64_subscription, is_base64_subscription
from .clash_yaml import decode_clash_yaml, is_clash_yaml
from .plain_text import decode_plain_text
from .registry import SubscriptionDecoderRegistry, create_default_decoder_registry
from .sip008_json import decode_sip008_json, is_sip008_json

__all__ = [
    "DecodedSubscription",
    "SubscriptionDecoderRegistry",
    "create_default_decoder_registry",
    "is_base64_subscription",
    "decode_base64_subscription",
    "is_sip008_json",
    "decode_sip008_json",
    "is_clash_yaml",
    "decode_clash_yaml",
    "decode_plain_text",
]
