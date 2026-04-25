"""
Xray-Prism Web Server Entry Point.

Usage:
    python server.py [--host HOST] [--port PORT] [--reload]

Examples:
    python server.py                    # Start on localhost:8000
    python server.py --port 3000        # Start on localhost:3000
    python server.py --host 0.0.0.0     # Listen on all interfaces
    python server.py --reload           # Enable auto-reload for development
"""
from __future__ import annotations

import argparse
import errno
import os
import socket
import sys
from typing import Optional

import uvicorn
from dotenv import load_dotenv


load_dotenv()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Start the Xray-Prism web server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Access Points:
  Frontend:     http://localhost:8000/
  API Docs:     http://localhost:8000/docs
  ReDoc:        http://localhost:8000/redoc
        """,
    )
    parser.add_argument(
        "--host",
        type=str,
        default=os.environ.get("HOST", "127.0.0.1"),
        help="Host to bind to (default: 127.0.0.1 or HOST env)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", 8000)),
        help="Port to bind to (default: 8000 or PORT env)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    parser.add_argument(
        "--no-autostart-xray",
        action="store_true",
        help="Disable auto-starting Xray when the web server boots",
    )
    return parser


def can_bind_port(host: str, port: int) -> tuple[bool, Optional[str]]:
    """Check whether the requested host/port can be bound before starting uvicorn."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        return True, None
    except OSError as exc:
        if exc.errno in {errno.EADDRINUSE, 10048}:
            return False, f"端口已被占用: http://{host}:{port}/"
        return False, f"无法绑定到 http://{host}:{port}/: {exc}"
    finally:
        sock.close()


def format_port_conflict_message(host: str, port: int, reason: Optional[str] = None) -> str:
    detail = reason or f"端口已被占用: http://{host}:{port}/"
    return (
        "Xray-Prism Web 服务启动失败。\n"
        f"{detail}\n"
        "请停止占用该端口的进程，或改用其他端口重新启动。"
    )


def run_server(args: argparse.Namespace) -> int:
    ok, reason = can_bind_port(args.host, args.port)
    if not ok:
        print(format_port_conflict_message(args.host, args.port, reason), file=sys.stderr)
        return 1

    print(
        f"""
╔══════════════════════════════════════════════════════════════╗
║                     Xray-Prism                               ║
║                  Web Server Starting...                      ║
╠══════════════════════════════════════════════════════════════╣
║  Frontend:   http://{args.host}:{args.port}/
║  API Docs:   http://{args.host}:{args.port}/docs
║  ReDoc:      http://{args.host}:{args.port}/redoc
╚══════════════════════════════════════════════════════════════╝
        """
    )

    # Default behavior when started via `server.py`: auto-start Xray in the API startup hook.
    # Respect user overrides (env var or CLI flag).
    if getattr(args, "no_autostart_xray", False):
        os.environ["XRAY_PRISM_AUTOSTART_XRAY"] = "0"
    else:
        os.environ.setdefault("XRAY_PRISM_AUTOSTART_XRAY", "1")

    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run_server(args)


if __name__ == "__main__":
    raise SystemExit(main())
