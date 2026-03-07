"""
Node management API routes.
"""
from fastapi import APIRouter, HTTPException, status

from api.schemas.models import (
    NodeResponse,
    ErrorResponse,
)
from api.services.subscription_service import get_subscription_service

router = APIRouter(prefix="/api/nodes", tags=["Nodes"])


@router.get(
    "/{node_id}",
    response_model=NodeResponse,
    responses={404: {"model": ErrorResponse, "description": "Node not found"}},
    operation_id="getNode"
)
async def get_node(node_id: str):
    """Get a single node by ID."""
    service = get_subscription_service()
    node = service.get_node(node_id)
    
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node {node_id} not found"
        )
    
    return NodeResponse(
        id=node["id"],
        subscription_id=node["subscription_id"],
        name=node["name"],
        protocol=node["protocol"],
        address=node["address"],
        port=node["port"],
        test_status=node.get("test_status", "pending"),
        latency_ms=node.get("latency_ms"),
        exit_ip=node.get("exit_ip"),
        exit_country=node.get("exit_country")
    )
