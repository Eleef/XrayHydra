"""
FastAPI application entry point.
Provides REST API for Xray-Prism web frontend.
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.routes import subscriptions, proxies, system, nodes

# Create FastAPI app
app = FastAPI(
    title="Xray-Prism API",
    description="REST API for managing VPN subscriptions and proxy ports",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

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
app.include_router(nodes.router)
app.include_router(proxies.router)
app.include_router(system.router)


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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "xray-prism"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
