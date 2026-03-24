# -*- coding: utf-8 -*-
"""
Subscription decoder base types.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DecodedSubscription:
    """Normalized subscription content and its detected format."""

    mode: str
    content: str
