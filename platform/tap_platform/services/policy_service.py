"""Policy service: OPA HTTP evaluation of plan JSON + policy set management."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Self

import httpx

from tap_platform.config import Settings, get_settings

if TYPE_CHECKING:
    from tap_platform.api.common import CursorPage, PageParams
    from tap_platform.api.policies import PolicyEvalResult, PolicySet, PolicySetCreate


class PolicyService:
    """Evaluate plans against OPA and manage tenant policy sets."""

    def __init__(self, db: Any, http: httpx.AsyncClient | None, settings: Settings) -> None:
        self._db = db
        self._http = http or httpx.AsyncClient(timeout=15)
        self._settings = settings

    @classmethod
    def from_app_state(cls, state: Any) -> Self:
        """Build from FastAPI ``app.state``."""
        return cls(
            getattr(state, "db", None),
            getattr(state, "http", None),
            getattr(state, "settings", get_settings()),
        )

    async def evaluate_opa(self, input_document: dict[str, Any]) -> dict[str, Any]:
        """POST the input document to OPA's data API and return the decision.

        The decision document shape (from governance Rego bundles) is::

            {"allow": bool, "enforcement_level": str, "violations": [
                {"policy": str, "rule": str, "message": str, "severity": str}]}
        """
        url = f"{self._settings.opa_url.rstrip('/')}{self._settings.opa_decision_path}"
        response = await self._http.post(url, json={"input": input_document})
        response.raise_for_status()
        result: dict[str, Any] = response.json().get("result", {})
        return result

    async def evaluate_plan(self, workspace_id: str, plan_json: dict[str, Any]) -> "PolicyEvalResult":
        """Evaluate a Terraform/OpenTofu plan JSON against the workspace's policy sets.

        Contract: load bound policy sets, build the OPA input
        ``{"plan": plan_json, "workspace": ..., "tenant": ...}``, call
        :meth:`evaluate_opa`, aggregate to the strictest enforcement level,
        and persist a ``policy_results`` row (even for ad-hoc evaluations).
        """
        _ = datetime.now(UTC)  # evaluated_at timestamp source
        raise NotImplementedError("compose OPA input, evaluate, persist policy_results")

    async def create_policy_set(
        self, body: "PolicySetCreate", *, idempotency_key: str | None = None
    ) -> "PolicySet":
        """Create a policy set and make its bundle discoverable by OPA."""
        raise NotImplementedError("INSERT policy_sets + bundle registration")

    async def get_policy_set(self, policy_set_id: str) -> "PolicySet":
        """Fetch one policy set."""
        raise NotImplementedError("SELECT policy_sets with RLS")

    async def list_policy_sets(self, page: "PageParams") -> "CursorPage[PolicySet]":
        """Paginated listing of the tenant's policy sets."""
        raise NotImplementedError("keyset-paginate policy_sets")
