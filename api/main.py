"""
FastAPI application entry point.
Provides REST API for Xray-Prism web frontend.
"""
import sys
import os
import threading
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response

from api.routes import subscriptions, proxies, system, nodes, health, lease, custom_groups, geo

# Create FastAPI app
app = FastAPI(
    title="Xray-Prism API",
    description="REST API for managing VPN subscriptions and proxy ports",
    version="0.2.0",
    summary="Client-facing REST API for subscriptions, proxies, health monitoring, lease allocation, and Xray lifecycle control.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "Subscriptions", "description": "Manage subscription sources and parsed nodes."},
        {"name": "Custom Groups", "description": "Manage user-defined node groups and snapshot nodes."},
        {"name": "Nodes", "description": "Inspect individual proxy nodes parsed from subscriptions."},
        {"name": "Proxies", "description": "Manage local proxy port mappings and runtime tests."},
        {"name": "Health", "description": "Inspect and control background health monitoring."},
        {"name": "Lease", "description": "Acquire and release proxy leases for client workloads."},
        {"name": "Geo", "description": "Resolve IP geo metadata and list exit IPs by ISO country code."},
        {"name": "System", "description": "Control Xray lifecycle and query runtime status."},
    ]
)


def _env_flag_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def maybe_autostart_xray() -> None:
    """Auto-start Xray when explicitly enabled (used by `server.py`)."""
    if not _env_flag_truthy(os.environ.get("XRAY_PRISM_AUTOSTART_XRAY")):
        return

    def _worker() -> None:
        try:
            from api.services.proxy_service import get_proxy_service
            service = get_proxy_service()
            result = service.start_xray()
            # Do not raise on startup; log via stdout is fine for local script use.
            if not result.get("success"):
                # Common case: no proxies configured yet.
                print(f"[xray-prism] Xray autostart skipped: {result.get('message')}")
        except Exception as exc:
            print(f"[xray-prism] Xray autostart failed: {exc}")

    threading.Thread(target=_worker, daemon=True, name="XrayAutoStart").start()


@app.on_event("startup")
def _startup_autostart_xray() -> None:
    maybe_autostart_xray()


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(subscriptions.router)
app.include_router(custom_groups.router)
app.include_router(nodes.router)
app.include_router(proxies.router)
app.include_router(system.router)
app.include_router(health.router)
app.include_router(lease.router)
app.include_router(geo.router)


# Static files for web frontend
WEB_DIR = PROJECT_ROOT / "web"
if WEB_DIR.exists():
    app.mount("/css", StaticFiles(directory=str(WEB_DIR / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(WEB_DIR / "js")), name="js")
    app.mount("/assets", StaticFiles(directory=str(WEB_DIR / "assets")), name="assets")


@app.get("/", include_in_schema=False)
async def serve_index():
    """Serve the main frontend page."""
    index_path = WEB_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Welcome to Xray-Prism API", "docs": "/docs"}


@app.get("/favicon.ico", include_in_schema=False)
async def serve_favicon():
    """Avoid frontend console noise when no favicon asset is provided."""
    favicon_path = WEB_DIR / "assets" / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(str(favicon_path))
    return Response(status_code=204)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "xray-prism"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
