"""
Custom node group API routes.
"""
from fastapi import APIRouter, HTTPException, status

from api.schemas.models import (
    CustomGroupCopyNodesRequest,
    CustomGroupCopyNodesResponse,
    CustomGroupCreateRequest,
    CustomGroupImportRequest,
    CustomGroupImportResponse,
    CustomGroupListResponse,
    CustomGroupRenameRequest,
    CustomGroupResponse,
    ErrorResponse,
    NodeListResponse,
    NodeResponse,
    SuccessResponse,
)
from api.services.custom_group_service import get_custom_group_service
from api.services.proxy_service import get_proxy_service
from api.services.subscription_service import get_subscription_service

router = APIRouter(prefix="/api/custom-groups", tags=["Custom Groups"])


def _proxy_port_by_node_id() -> dict[str, int]:
    proxy_service = get_proxy_service()
    return {
        str(item["node_id"]): int(item["port"])
        for item in proxy_service.get_all_proxies()
    }


def _build_node_response(node: dict, proxy_port_map: dict[str, int]) -> NodeResponse:
    proxy_port = proxy_port_map.get(str(node["id"]))
    group_id = str(node.get("group_id") or "")
    return NodeResponse(
        id=node["id"],
        group_id=group_id,
        group_type="custom",
        subscription_id=None,
        name=node["name"],
        protocol=node["protocol"],
        address=node["address"],
        port=node["port"],
        test_status=node.get("test_status", "pending"),
        latency_ms=node.get("latency_ms"),
        exit_ip=node.get("exit_ip"),
        exit_country=node.get("exit_country"),
        in_proxy_pool=proxy_port is not None,
        proxy_port=proxy_port,
    )


@router.get(
    "",
    response_model=CustomGroupListResponse,
    operation_id="listCustomGroups",
)
async def list_custom_groups():
    service = get_custom_group_service()
    groups = service.get_all_groups()
    return CustomGroupListResponse(
        groups=[CustomGroupResponse(**group) for group in groups],
        total=len(groups),
    )


@router.post(
    "",
    response_model=CustomGroupResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse, "description": "Invalid custom group payload"}},
    operation_id="createCustomGroup",
)
async def create_custom_group(data: CustomGroupCreateRequest):
    service = get_custom_group_service()
    try:
        result = service.create_group(data.name)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return CustomGroupResponse(**result)


@router.patch(
    "/{group_id}",
    response_model=CustomGroupResponse,
    responses={404: {"model": ErrorResponse, "description": "Custom group not found"}},
    operation_id="renameCustomGroup",
)
async def rename_custom_group(group_id: str, data: CustomGroupRenameRequest):
    service = get_custom_group_service()
    result = service.rename_group(group_id, data.name)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Custom group {group_id} not found",
        )
    return CustomGroupResponse(**result)


@router.delete(
    "/{group_id}",
    response_model=SuccessResponse,
    responses={404: {"model": ErrorResponse, "description": "Custom group not found"}},
    operation_id="deleteCustomGroup",
)
async def delete_custom_group(group_id: str):
    service = get_custom_group_service()
    if not service.delete_group(group_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Custom group {group_id} not found",
        )
    return SuccessResponse(message=f"Custom group {group_id} deleted successfully")


@router.get(
    "/{group_id}/nodes",
    response_model=NodeListResponse,
    responses={404: {"model": ErrorResponse, "description": "Custom group not found"}},
    operation_id="listCustomGroupNodes",
)
async def list_custom_group_nodes(group_id: str):
    service = get_custom_group_service()
    group = service.get_group(group_id)
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Custom group {group_id} not found",
        )
    nodes = service.get_nodes_by_group(group_id)
    proxy_port_map = _proxy_port_by_node_id()
    return NodeListResponse(
        nodes=[_build_node_response(node, proxy_port_map) for node in nodes],
        total=len(nodes),
    )


@router.post(
    "/{group_id}/nodes/import",
    response_model=CustomGroupImportResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid custom group import payload"},
        404: {"model": ErrorResponse, "description": "Custom group not found"},
    },
    operation_id="importCustomGroupNodes",
)
async def import_custom_group_nodes(group_id: str, data: CustomGroupImportRequest):
    service = get_custom_group_service()
    if service.get_group(group_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Custom group {group_id} not found",
        )
    try:
        result = service.import_nodes(group_id, data.content)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return CustomGroupImportResponse(**result)


@router.post(
    "/{group_id}/nodes/copy",
    response_model=CustomGroupCopyNodesResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid copy request"},
        404: {"model": ErrorResponse, "description": "Custom group not found"},
    },
    operation_id="copyNodesToCustomGroup",
)
async def copy_nodes_to_custom_group(group_id: str, data: CustomGroupCopyNodesRequest):
    custom_service = get_custom_group_service()
    if custom_service.get_group(group_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Custom group {group_id} not found",
        )

    requested_ids = list(dict.fromkeys(data.source_node_ids))
    subscription_nodes = get_subscription_service().get_nodes_by_ids(requested_ids)
    custom_nodes = custom_service.get_nodes_by_ids(requested_ids)
    node_map = {node["id"]: node for node in subscription_nodes}
    node_map.update({node["id"]: node for node in custom_nodes})

    source_nodes = [node_map[node_id] for node_id in requested_ids if node_id in node_map]
    missing_ids = [node_id for node_id in requested_ids if node_id not in node_map]

    try:
        result = custom_service.copy_nodes(
            group_id=group_id,
            source_nodes=source_nodes,
            missing_node_ids=missing_ids,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return CustomGroupCopyNodesResponse(**result)


@router.delete(
    "/{group_id}/nodes/{node_id}",
    response_model=SuccessResponse,
    responses={404: {"model": ErrorResponse, "description": "Node not found"}},
    operation_id="deleteCustomGroupNode",
)
async def delete_custom_group_node(group_id: str, node_id: str):
    service = get_custom_group_service()
    if not service.delete_group_node(group_id=group_id, node_id=node_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node {node_id} not found in custom group {group_id}",
        )
    return SuccessResponse(message=f"Node {node_id} removed from custom group {group_id}")
