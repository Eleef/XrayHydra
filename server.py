"""
Xray-Prism Web Server Entry Point

Usage:
    python server.py [--host HOST] [--port PORT] [--reload]

Examples:
    python server.py                    # Start on localhost:8000
    python server.py --port 3000        # Start on localhost:3000
    python server.py --host 0.0.0.0     # Listen on all interfaces
    python server.py --reload           # Enable auto-reload for development
"""
import argparse
import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        description="Start the Xray-Prism web server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Access Points:
  Frontend:     http://localhost:8000/
  API Docs:     http://localhost:8000/docs
  ReDoc:        http://localhost:8000/redoc
        """
    )
    parser.add_argument(
        "--host",
        type=str,
        default=os.environ.get("HOST", "127.0.0.1"),
        help="Host to bind to (default: 127.0.0.1 or HOST env)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", 8000)),
        help="Port to bind to (default: 8000 or PORT env)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    
    args = parser.parse_args()
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                     🌐 Xray-Prism                             ║
║                  Web Server Starting...                       ║
╠══════════════════════════════════════════════════════════════╣
║  Frontend:   http://{args.host}:{args.port}/                       
║  API Docs:   http://{args.host}:{args.port}/docs                   
║  ReDoc:      http://{args.host}:{args.port}/redoc                  
╚══════════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )


if __name__ == "__main__":
    main()
