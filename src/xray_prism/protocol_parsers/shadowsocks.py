# -*- coding: utf-8 -*-
"""Shadowsocks URI parser."""

from __future__ import annotations

from typing import Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse

from ..models import Protocol, ProxyNode
from .base import ParseError, decode_base64


def _parse_host_port(host_port: str) -> Tuple[str, int]:
    candidate = host_port.strip().rstrip("/")
    parsed = urlparse(f"//{candidate}")
    if not parsed.hostname or parsed.port is None:
        raise ParseError("无法识别的 Shadowsocks 主机端口")
    return parsed.hostname, parsed.port


def _decode_user_info(user_info: str) -> str:
    raw = user_info.strip()
    plain = unquote(raw)
    if ":" in plain:
        return plain
    try:
        decoded = decode_base64(raw)
        if ":" in decoded:
            return decoded
    except Exception:
        pass
    return plain


def _parse_plugin(value: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if value is None:
        return None, None
    raw = unquote(str(value)).strip()
    if not raw:
        return None, None
    parts = [item.strip() for item in raw.split(";")]
    plugin = parts[0] or None
    opts = ";".join(item for item in parts[1:] if item) or None
    return plugin, opts


def _parse_optional_bool(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return None


def _parse_optional_int(value: Optional[str]) -> Optional[int]:
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(str(value).strip())
    except ValueError:
        return None


def parse_shadowsocks(uri: str) -> ProxyNode:
    """
    Parse Shadowsocks URI.

    Supports:
    1. ss://base64(method:password)@host:port#name
    2. ss://base64(method:password@host:port)#name
    """
    try:
        parsed = urlparse(uri)
        name = unquote(parsed.fragment) if parsed.fragment else "Unknown"
        params = parse_qs(parsed.query, keep_blank_values=True)
        plugin, plugin_opts = _parse_plugin(params.get("plugin", [None])[0])
        ss_uot = _parse_optional_bool(
            params.get("uot", params.get("udp-over-tcp", [None]))[0]
        )
        ss_uot_version = _parse_optional_int(
            params.get(
                "UoTVersion",
                params.get("uotVersion", params.get("uot-version", params.get("udp-over-tcp-version", [None]))),
            )[0]
        )

        main = uri.replace("ss://", "", 1)
        if "#" in main:
            main = main.split("#", 1)[0]
        if "?" in main:
            main = main.split("?", 1)[0]
        main = main.strip().rstrip("/")

        method: Optional[str] = None
        password: Optional[str] = None
        address: Optional[str] = None
        port: Optional[int] = None

        if "@" in main:
            user_info, host_port = main.rsplit("@", 1)
            decoded_user_info = _decode_user_info(user_info)
            if ":" not in decoded_user_info:
                raise ParseError("无法识别的 Shadowsocks 用户信息")
            method, password = decoded_user_info.split(":", 1)
            address, port = _parse_host_port(host_port)
        else:
            decoded = decode_base64(main)
            if "@" not in decoded:
                raise ParseError("无法识别的 Shadowsocks 格式")
            user_info, host_port = decoded.rsplit("@", 1)
            if ":" not in user_info:
                raise ParseError("无法识别的 Shadowsocks 用户信息")
            method, password = user_info.split(":", 1)
            address, port = _parse_host_port(host_port)

        return ProxyNode(
            name=name,
            protocol=Protocol.SHADOWSOCKS,
            address=address,
            port=port,
            password=password,
            security=method,
            ss_plugin=plugin,
            ss_plugin_opts=plugin_opts,
            ss_uot=ss_uot,
            ss_uot_version=ss_uot_version,
        )
    except ParseError:
        raise
    except Exception as e:
        raise ParseError(f"Shadowsocks 解析失败: {e}")
