"""/v1/marketplace — distribution of signed agent artifacts (OCI + cosign)."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field

from tap_platform.api.common import CursorPage, PageParams, idempotency_key, page_params
from tap_platform.services.marketplace_service import MarketplaceService

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


class ListingTier(StrEnum):
    INTERNAL = "internal"
    COMMUNITY = "community"
    ENTERPRISE = "enterprise"


class Listing(BaseModel):
    """A marketplace listing for a published agent artifact."""

    id: str
    name: str
    publisher: str
    tier: ListingTier
    domain: str
    description: str | None = None
    artifact_uri: str = Field(description="OCI reference, e.g. ghcr.io/org/agent:1.2.0")
    signature_verified: bool = Field(description="cosign verification result at publish time.")
    downloads: int = 0
    created_at: str
    updated_at: str


class PublishRequest(BaseModel):
    """Request body for POST /v1/marketplace/listings."""

    artifact_uri: str = Field(description="OCI reference of the agent artifact to list.")
    tier: ListingTier = ListingTier.INTERNAL
    description: str | None = None


class InstallRequest(BaseModel):
    """Request body for POST /v1/marketplace/listings/{id}/install."""

    target_agent_name: str | None = Field(
        default=None, description="Override registry name; defaults to listing name."
    )


def _service(request: Request) -> MarketplaceService:
    return MarketplaceService.from_app_state(request.app.state)


@router.get("/listings", response_model=CursorPage[Listing])
async def list_listings(
    request: Request,
    page: Annotated[PageParams, Depends(page_params)],
    tier: ListingTier | None = None,
    domain: str | None = None,
    q: str | None = None,
) -> CursorPage[Listing]:
    """Search/browse marketplace listings."""
    return await _service(request).list_listings(page, tier=tier, domain=domain, query=q)


@router.get("/listings/{listing_id}", response_model=Listing)
async def get_listing(listing_id: str, request: Request) -> Listing:
    """Fetch one listing."""
    return await _service(request).get_listing(listing_id)


@router.post("/listings", response_model=Listing, status_code=status.HTTP_201_CREATED)
async def publish_listing(
    body: PublishRequest,
    request: Request,
    idem_key: Annotated[str | None, Depends(idempotency_key)] = None,
) -> Listing:
    """Publish an artifact: pull OCI manifest, verify cosign signature, create listing."""
    return await _service(request).publish(body, idempotency_key=idem_key)


@router.post("/listings/{listing_id}/install", response_model=Listing, status_code=status.HTTP_202_ACCEPTED)
async def install_listing(
    listing_id: str,
    body: InstallRequest,
    request: Request,
    idem_key: Annotated[str | None, Depends(idempotency_key)] = None,
) -> Listing:
    """Install a listed agent into the caller's tenant registry."""
    return await _service(request).install(listing_id, body, idempotency_key=idem_key)
