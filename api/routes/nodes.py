"""
Node management API routes.
"""
from fastapi import APIRouter, HTTPException, status

from api.schemas.models import (
    NodeBatchTestResponse,
    NodeTestJobResponse,
    NodeTestRequest,
    NodeTestResult,
    NodeResponse,
    ErrorResponse,
)
from api.routes.node_response_builder import build_node_response
from api.services.custom_group_service import get_custom_group_service
from api.services.node_test_service import get_node_test_service
from api.services.proxy_service import get_proxy_service
from api.services.subscription_service import get_subscription_service

router = APIRouter(prefix="/api/nodes", tags=["Nodes"])


def _proxy_port_by_node_id() -> dict[str, int]:
    proxy_service = get_proxy_service()
    return {
        str(item["node_id"]): int(item["port"])
        for item in proxy_service.get_all_proxies()
    }


def _build_node_response(node: dict, proxy_port_map: dict[str, int]) -> NodeResponse:
    proxy_port = proxy_port_map.get(str(node["id"]))
    subscription_id_raw = node.get("subscription_id")
    subscription_id = str(subscription_id_raw) if subscription_id_raw else None
    if subscription_id:
        group_id = str(subscription_id)
        group_type = "subscription"
    else:
        group_id = str(node.get("group_id") or "")
        group_type = "custom"
    return build_node_response(
        node,
        group_id=group_id,
        group_type=group_type,
        subscription_id=subscription_id,
        proxy_port=proxy_port,
    )


@router.get(
    "/{node_id}",
    response_model=NodeResponse,
    responses={404: {"model": ErrorResponse, "description": "Node not found"}},
    operation_id="getNode"
)
async def get_node(node_id: str):
    """Get a single node by ID."""
    subscription_service = get_subscription_service()
    node = subscription_service.get_node(node_id)
    if not node:
        node = get_custom_group_service().get_node(node_id)
    
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node {node_id} not found"
        )
    proxy_port_map = _proxy_port_by_node_id()

    return _build_node_response(node, proxy_port_map)


@router.post(
    "/test",
    response_model=NodeBatchTestResponse,
    responses={400: {"model": ErrorResponse, "description": "Invalid node test request"}},
    operation_id="testNodes",
)
async def test_nodes(data: NodeTestRequest):
    """Run isolated connectivity tests for selected subscription nodes."""
    service = get_node_test_service()
    try:
        result = service.test_nodes(
            node_ids=data.node_ids,
            timeout=data.timeout,
            test_profile=data.test_profile,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return NodeBatchTestResponse(**result)


@router.post(
    "/test-jobs",
    response_model=NodeTestJobResponse,
    responses={400: {"model": ErrorResponse, "description": "Invalid node test request"}},
    operation_id="startNodeTestJob",
)
async def start_node_test_job(data: NodeTestRequest):
    """Start an asynchronous node test job and return the initial progress state."""
    service = get_node_test_service()
    try:
        result = service.start_test_job(
            node_ids=data.node_ids,
            timeout=data.timeout,
            test_profile=data.test_profile,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return NodeTestJobResponse(**result)


@router.get(
    "/test-jobs/{job_id}",
    response_model=NodeTestJobResponse,
    responses={404: {"model": ErrorResponse, "description": "Node test job not found"}},
    operation_id="getNodeTestJob",
)
async def get_node_test_job(job_id: str):
    """Get the current progress snapshot for an asynchronous node test job."""
    service = get_node_test_service()
    result = service.get_test_job(job_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node test job {job_id} not found",
        )
    return NodeTestJobResponse(**result)
