"""
Geo lookup API routes.
"""
from fastapi import APIRouter, HTTPException, status

from api.schemas.models import ErrorResponse, IpGeoLookupResponse
from api.services.geo_service import GeoLookupError, get_geo_service

router = APIRouter(prefix="/api/geo", tags=["Geo"])


@router.get(
    "/ip/{ip}",
    response_model=IpGeoLookupResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid IP"},
        404: {"model": ErrorResponse, "description": "Geo info not found"},
    },
    operation_id="lookupIpRegion",
)
async def lookup_ip_region(ip: str):
    """Resolve country name and ISO alpha-2 country code for one IP address."""
    service = get_geo_service()
    try:
        result = service.lookup_ip(ip)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except GeoLookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return IpGeoLookupResponse(**result)
