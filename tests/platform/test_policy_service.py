"""Contract tests for the Policy service.

Pins the contract between the control plane and OPA (mocked at the HTTP
boundary): decision aggregation across packages, the verdict ladder
(deny > soft_fail > advisory), rollout-stage downgrades from the bundle
manifest, and fail-closed behavior when OPA is unreachable.

The reference implementation is the executable specification until
`tap_platform.services.policy_service` lands (see tests/README.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock

import pytest

try:  # pragma: no cover - exercised once the platform module exists
    from tap_platform.services.policy_service import PolicyService  # type: ignore
except ImportError:  # reference implementation = executable contract

    @dataclass
    class PolicyService:
        opa: Any  # async client: evaluate(input) -> {"tap": {domain: {pkg: {deny: [...], ...}}}}
        stages: dict[str, str] = field(default_factory=dict)  # package -> advisory|soft|hard

        async def evaluate(self, plan_input: dict[str, Any]) -> dict[str, Any]:
            try:
                raw = await self.opa.evaluate(plan_input)
            except Exception as exc:  # fail closed: no decision means no apply
                return {
                    "verdict": "deny",
                    "deny": [f"policy service unavailable: {exc}"],
                    "soft_fail": [],
                    "advisory": [],
                }

            deny: list[str] = []
            soft_fail: list[str] = []
            advisory: list[str] = []
            for domain, packages in raw.get("tap", {}).items():
                if domain == "config":
                    continue
                for pkg, decisions in packages.items():
                    full = f"tap.{domain}.{pkg}"
                    stage = self.stages.get(full, "hard")
                    d = list(decisions.get("deny", []))
                    s = list(decisions.get("soft_fail", []))
                    a = list(decisions.get("advisory", []))
                    if stage == "advisory":
                        advisory += d + s + a
                    elif stage == "soft":
                        soft_fail += d + s
                        advisory += a
                    else:
                        deny += d
                        soft_fail += s
                        advisory += a

            if deny:
                verdict = "deny"
            elif soft_fail:
                verdict = "soft_fail"
            else:
                verdict = "allow"
            return {"verdict": verdict, "deny": deny, "soft_fail": soft_fail, "advisory": advisory}


OPA_RESULT_CLEAN: dict[str, Any] = {"tap": {"terraform": {"deny_public_s3": {"deny": []}}}}


@pytest.fixture()
def opa() -> AsyncMock:
    client = AsyncMock()
    client.evaluate.return_value = OPA_RESULT_CLEAN
    return client


@pytest.mark.asyncio
async def test_clean_evaluation_allows(opa):
    service = PolicyService(opa=opa)
    result = await service.evaluate({"resource_changes": []})
    assert result["verdict"] == "allow"
    assert result["deny"] == [] and result["soft_fail"] == []


@pytest.mark.asyncio
async def test_any_deny_wins_over_soft_fail(opa):
    opa.evaluate.return_value = {"tap": {
        "terraform": {"deny_public_s3": {"deny": ["bucket is public"]}},
        "cost": {"budget_gate": {"soft_fail": ["over budget"]}},
    }}
    service = PolicyService(opa=opa)
    result = await service.evaluate({})
    assert result["verdict"] == "deny"
    assert "bucket is public" in result["deny"]
    assert "over budget" in result["soft_fail"]  # still reported


@pytest.mark.asyncio
async def test_soft_fail_without_deny_requires_approval(opa):
    opa.evaluate.return_value = {"tap": {"cost": {"budget_gate": {"soft_fail": ["over budget"]}}}}
    service = PolicyService(opa=opa)
    result = await service.evaluate({})
    assert result["verdict"] == "soft_fail"


@pytest.mark.asyncio
async def test_advisory_never_blocks(opa):
    opa.evaluate.return_value = {"tap": {"terraform": {
        "instance_allowlist": {"advisory": ["no allowlist for staging"]},
    }}}
    service = PolicyService(opa=opa)
    result = await service.evaluate({})
    assert result["verdict"] == "allow"
    assert result["advisory"] == ["no allowlist for staging"]


@pytest.mark.asyncio
async def test_advisory_stage_downgrades_deny(opa):
    opa.evaluate.return_value = {"tap": {"ai": {"model_governance": {"deny": ["unapproved model"]}}}}
    service = PolicyService(opa=opa, stages={"tap.ai.model_governance": "advisory"})
    result = await service.evaluate({})
    assert result["verdict"] == "allow"
    assert "unapproved model" in result["advisory"]


@pytest.mark.asyncio
async def test_soft_stage_downgrades_deny_to_approval(opa):
    opa.evaluate.return_value = {"tap": {"terraform": {"require_tags": {"deny": ["missing owner tag"]}}}}
    service = PolicyService(opa=opa, stages={"tap.terraform.require_tags": "soft"})
    result = await service.evaluate({})
    assert result["verdict"] == "soft_fail"
    assert "missing owner tag" in result["soft_fail"]


@pytest.mark.asyncio
async def test_opa_unreachable_fails_closed(opa):
    opa.evaluate.side_effect = ConnectionError("opa down")
    service = PolicyService(opa=opa)
    result = await service.evaluate({})
    assert result["verdict"] == "deny"
    assert any("unavailable" in m for m in result["deny"])


@pytest.mark.asyncio
async def test_config_namespace_is_not_a_policy(opa):
    opa.evaluate.return_value = {"tap": {
        "config": {"instance_allowlist": {"prod": ["m6i.large"]}},
        "terraform": {"deny_public_s3": {"deny": []}},
    }}
    service = PolicyService(opa=opa)
    result = await service.evaluate({})
    assert result["verdict"] == "allow"
