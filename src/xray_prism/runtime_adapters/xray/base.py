# -*- coding: utf-8 -*-
"""
Base type definitions for Xray outbound adapters.
"""

from typing import Any, Callable, Dict

from ...models import ProxyNode

StreamSettingsBuilder = Callable[[ProxyNode], Dict[str, Any]]
OutboundAdapter = Callable[[ProxyNode, str, StreamSettingsBuilder], Dict[str, Any]]

