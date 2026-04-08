from __future__ import annotations

import os

from dotenv import load_dotenv


load_dotenv()

DEFAULT_PROXY_BIND_HOST = "127.0.0.1"
DEFAULT_PROXY_ACCESS_HOST = "127.0.0.1"
ALL_INTERFACE_HOSTS = {"0.0.0.0", "::", "[::]"}


def get_proxy_bind_host() -> str:
    """Return the host Xray should bind proxy inbounds to."""
    host = (os.environ.get("PROXY_BIND_HOST") or DEFAULT_PROXY_BIND_HOST).strip()
    return host or DEFAULT_PROXY_BIND_HOST


def get_proxy_access_host() -> str:
    """
    Return the host advertised to clients for proxy access.

    When the listener binds to all interfaces, default client access falls back to
    loopback unless PROXY_ACCESS_HOST is set explicitly.
    """
    explicit_host = (os.environ.get("PROXY_ACCESS_HOST") or "").strip()
    if explicit_host:
        return explicit_host

    bind_host = get_proxy_bind_host()
    if bind_host in ALL_INTERFACE_HOSTS:
        return DEFAULT_PROXY_ACCESS_HOST
    return bind_host


def format_host_port(host: str, port: int) -> str:
    """Format a host:port pair, adding IPv6 brackets when needed."""
    normalized_host = host.strip()
    if ":" in normalized_host and not normalized_host.startswith("["):
        normalized_host = f"[{normalized_host}]"
    return f"{normalized_host}:{int(port)}"


def build_proxy_address(port: int) -> str:
    """Build the client-facing proxy host:port string."""
    return format_host_port(get_proxy_access_host(), port)
