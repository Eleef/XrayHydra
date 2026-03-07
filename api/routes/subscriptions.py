"""
Subscription management API routes.
"""
from fastapi import APIRouter, HTTPException, status

from api.schemas.models import (
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionListResponse,
    NodeResponse,
    NodeListResponse,
    SuccessResponse,
    ErrorResponse
)
from api.services.subscription_service import get_subscription_service

router = APIRouter(prefix="/api/subscriptions", tags=["Subscriptions"])


@router.get(
    "",
    response_model=SubscriptionListResponse,
    operation_id="listSubscriptions"
)
async def get_subscriptions():
    """Get all subscriptions."""
    service = get_subscription_service()
    subscriptions = service.get_all_subscriptions()
    return SubscriptionListResponse(
        subscriptions=[SubscriptionResponse(**s) for s in subscriptions],
        total=len(subscriptions)
    )


@router.post(
    "",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse, "description": "Invalid subscription payload"}},
    operation_id="createSubscription"
)
async def create_subscription(data: SubscriptionCreate):
    """Create a new subscription and fetch its nodes."""
    service = get_subscription_service()
    
    try:
        result = service.create_subscription(data.name, data.url)
        return SubscriptionResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/{sub_id}",
    response_model=SubscriptionResponse,
    responses={404: {"model": ErrorResponse, "description": "Subscription not found"}},
    operation_id="getSubscription"
)
async def get_subscription(sub_id: str):
    """Get a subscription by ID."""
    service = get_subscription_service()
    result = service.get_subscription(sub_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription {sub_id} not found"
        )
    
    return SubscriptionResponse(**result)


@router.delete(
    "/{sub_id}",
    response_model=SuccessResponse,
    responses={404: {"model": ErrorResponse, "description": "Subscription not found"}},
    operation_id="deleteSubscription"
)
async def delete_subscription(sub_id: str):
    """Delete a subscription and all its nodes."""
    service = get_subscription_service()
    
    if not service.delete_subscription(sub_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription {sub_id} not found"
        )
    
    return SuccessResponse(message=f"Subscription {sub_id} deleted successfully")


@router.post(
    "/{sub_id}/refresh",
    response_model=SubscriptionResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Refresh failed"},
        404: {"model": ErrorResponse, "description": "Subscription not found"}
    },
    operation_id="refreshSubscription"
)
async def refresh_subscription(sub_id: str):
    """Refresh a subscription's nodes from the source URL."""
    service = get_subscription_service()
    
    try:
        result = service.refresh_subscription(sub_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription {sub_id} not found"
            )
        return SubscriptionResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/{sub_id}/nodes",
    response_model=NodeListResponse,
    responses={404: {"model": ErrorResponse, "description": "Subscription not found"}},
    operation_id="listSubscriptionNodes"
)
async def get_subscription_nodes(sub_id: str):
    """Get all nodes for a subscription."""
    service = get_subscription_service()
    
    # Check if subscription exists
    if not service.get_subscription(sub_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription {sub_id} not found"
        )
    
    nodes = service.get_nodes_by_subscription(sub_id)
    return NodeListResponse(
        nodes=[NodeResponse(
            id=n["id"],
            subscription_id=n["subscription_id"],
            name=n["name"],
            protocol=n["protocol"],
            address=n["address"],
            port=n["port"],
            test_status=n.get("test_status", "pending"),
            latency_ms=n.get("latency_ms"),
            exit_ip=n.get("exit_ip"),
            exit_country=n.get("exit_country")
        ) for n in nodes],
        total=len(nodes)
    )
