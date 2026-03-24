# -*- coding: utf-8 -*-
"""
SIP008-style Shadowsocks JSON subscription decoder.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import quote, urlencode

from .base import DecodedSubscription


def _extract_servers(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict):
        servers = payload.get("servers")
        if isinstance(servers, list):
            return [item for item in servers if isinstance(item, dict)]
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _normalize_host(host: str) -> str:
    host = host.strip()
    if ":" in host and not host.startswith("[") and not host.endswith("]"):
        return f"[{host}]"
    return host


def _stringify_plugin_opts(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, dict):
        parts: List[str] = []
        for key, val in value.items():
            key_text = str(key).strip()
            if not key_text:
                continue
            if val in (True, False, None, ""):
                parts.append(key_text if val is True else f"{key_text}={val}")
                continue
            parts.append(f"{key_text}={val}")
        return ";".join(parts) or None
    text = str(value).strip()
    return text or None


def _first_non_empty(container: Dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = container.get(key)
        if value not in (None, ""):
            return value
    return None


def _to_ss_uri(server: Dict[str, Any]) -> Optional[str]:
    method = _first_non_empty(server, ("method", "cipher", "encryption"))
    password = _first_non_empty(server, ("password",))
    host = _first_non_empty(server, ("server", "address", "host"))
    port = _first_non_empty(server, ("server_port", "port"))
    if method in (None, "") or password in (None, "") or host in (None, "") or port in (None, ""):
        return None

    try:
        port_num = int(str(port).strip())
    except ValueError:
        return None

    userinfo = quote(f"{method}:{password}", safe="")
    uri = f"ss://{userinfo}@{_normalize_host(str(host))}:{port_num}"

    query: Dict[str, str] = {}
    plugin = _first_non_empty(server, ("plugin",))
    plugin_opts = _stringify_plugin_opts(_first_non_empty(server, ("plugin_opts", "plugin-opts")))
    if plugin:
        plugin_value = str(plugin).strip()
        if plugin_opts:
            plugin_value = f"{plugin_value};{plugin_opts}"
        query["plugin"] = plugin_value

    uot = _first_non_empty(server, ("uot", "udp-over-tcp", "udp_over_tcp", "UoT"))
    if uot is not None:
        if isinstance(uot, bool):
            query["uot"] = "1" if uot else "0"
        else:
            query["uot"] = str(uot).strip()
    uot_version = _first_non_empty(
        server,
        ("UoTVersion", "uotVersion", "uot-version", "udp-over-tcp-version", "udp_over_tcp_version"),
    )
    if uot_version is not None:
        query["UoTVersion"] = str(uot_version).strip()

    if query:
        uri += "?" + urlencode(query)

    name = _first_non_empty(server, ("remarks", "name", "tag"))
    if name:
        uri += "#" + quote(str(name), safe="")
    return uri


def is_sip008_json(content: str) -> bool:
    """Return whether content looks like SIP008-style JSON payload."""
    stripped = content.strip()
    if not stripped or stripped[0] not in ("{", "["):
        return False
    try:
        payload = json.loads(stripped)
    except Exception:
        return False

    servers = _extract_servers(payload)
    if not servers:
        return False
    for item in servers:
        if any(key in item for key in ("method", "cipher")) and any(key in item for key in ("server", "host", "address")):
            return True
    return False


def decode_sip008_json(content: str) -> DecodedSubscription:
    """
    Normalize SIP008 JSON into URI lines so protocol parser path stays unified.
    """
    try:
        payload = json.loads(content.strip())
    except Exception:
        return DecodedSubscription(mode="uri_lines", content=content)

    servers = _extract_servers(payload)
    uris: List[str] = []
    for server in servers:
        uri = _to_ss_uri(server)
        if uri:
            uris.append(uri)
    return DecodedSubscription(mode="uri_lines", content="\n".join(uris))

