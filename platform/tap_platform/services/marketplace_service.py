"""Marketplace service: signed OCI agent artifacts (publish/verify/install)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

import httpx

from tap_platform.config import Settings, get_settings

if TYPE_CHECKING:
    from tap_platform.api.common import CursorPage, PageParams
    from tap_platform.api.marketplace import InstallRequest, Listing, ListingTier, PublishRequest


class SignatureVerificationError(Exception):
    """Raised when a cosign signature for an artifact cannot be verified."""


class MarketplaceService:
    """Publish, verify, browse and install agent artifacts."""

    def __init__(self, db: Any, http: httpx.AsyncClient | None, settings: Settings) -> None:
        self._db = db
        self._http = http or httpx.AsyncClient(timeout=30)
        self._settings = settings

    @classmethod
    def from_app_state(cls, state: Any) -> Self:
        """Build from FastAPI ``app.state``."""
        return cls(
            getattr(state, "db", None),
            getattr(state, "http", None),
            getattr(state, "settings", get_settings()),
        )

    async def fetch_oci_manifest(self, artifact_uri: str) -> dict[str, Any]:
        """Pull the OCI image manifest for an artifact reference.

        Contract: resolve registry + repository + tag/digest from the
        reference, perform the OCI distribution token dance, and GET
        ``/v2/{repo}/manifests/{ref}`` with the image-manifest Accept headers.
        """
        raise NotImplementedError("OCI distribution API manifest pull")

    async def verify_cosign_signature(self, artifact_uri: str) -> bool:
        """Verify the artifact's cosign signature against the tenant trust root.

        Contract (stub): locate the ``.sig`` tag per cosign conventions,
        verify with sigstore-python / cosign CLI against configured public
        keys or keyless Fulcio identities. Raises
        :class:`SignatureVerificationError` on failure.
        """
        raise NotImplementedError("cosign verification against tenant trust policy")

    async def publish(self, body: "PublishRequest", *, idempotency_key: str | None = None) -> "Listing":
        """Verify signature, extract manifest metadata, create the listing row."""
        raise NotImplementedError("verify_cosign_signature + INSERT marketplace listing")

    async def install(
        self, listing_id: str, body: "InstallRequest", *, idempotency_key: str | None = None
    ) -> "Listing":
        """Install a listing into the tenant registry (delegates to RegistryService)."""
        raise NotImplementedError("re-verify signature, register agent, bump downloads")

    async def get_listing(self, listing_id: str) -> "Listing":
        """Fetch one listing."""
        raise NotImplementedError("SELECT listing")

    async def list_listings(
        self,
        page: "PageParams",
        *,
        tier: "ListingTier | None" = None,
        domain: str | None = None,
        query: str | None = None,
    ) -> "CursorPage[Listing]":
        """Browse/search listings (query = websearch on name/description)."""
        raise NotImplementedError("paginate listings with filters + full-text search")
