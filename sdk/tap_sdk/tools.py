"""@tool decorator + built-in platform tools (httpx clients against the TAP API).

Every tool is a typed async function; the decorator attaches a name,
description, and a JSON-schema derived from the signature (via pydantic), and
routes each call through the agent's guardrails when bound.
"""

from __future__ import annotations

import functools
import inspect
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, ParamSpec, TypeVar

import httpx
from pydantic import TypeAdapter

P = ParamSpec("P")
R = TypeVar("R")

DEFAULT_BASE_URL = "http://localhost:8080/v1"


@dataclass(frozen=True)
class ToolSpec:
    """Metadata attached to a decorated tool function."""

    name: str
    description: str
    parameters_schema: dict[str, Any]
    mutating: bool = False


def tool(
    name: str | None = None,
    *,
    description: str | None = None,
    mutating: bool = False,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Decorate a typed async function as a TAP agent tool.

    The wrapped function gains a ``.spec: ToolSpec`` attribute (name,
    description, JSON schema of its parameters) used for LLM tool definitions
    and MCP exposure. ``mutating=True`` tools are gated by Guardrails.
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        signature = inspect.signature(func)
        parameters: dict[str, Any] = {"type": "object", "properties": {}, "required": []}
        for param_name, param in signature.parameters.items():
            if param_name in {"self", "client"}:
                continue
            annotation = param.annotation if param.annotation is not inspect.Parameter.empty else Any
            parameters["properties"][param_name] = TypeAdapter(annotation).json_schema()
            if param.default is inspect.Parameter.empty:
                parameters["required"].append(param_name)

        spec = ToolSpec(
            name=name or func.__name__,
            description=description or (inspect.getdoc(func) or "").split("\n", 1)[0],
            parameters_schema=parameters,
            mutating=mutating,
        )

        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            return await func(*args, **kwargs)

        wrapper.spec = spec  # type: ignore[attr-defined]
        return wrapper

    return decorator


def _client(base_url: str | None = None, token: str | None = None) -> httpx.AsyncClient:
    """Shared API client factory (OIDC bearer token from the agent runtime)."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return httpx.AsyncClient(base_url=base_url or DEFAULT_BASE_URL, headers=headers, timeout=120)


# --- built-in platform tools --------------------------------------------------


@tool("terraform_plan", description="Start a governed plan run for a workspace.")
async def terraform_plan(
    workspace_id: str, variables: dict[str, Any] | None = None, engine: str = "terraform"
) -> dict[str, Any]:
    """POST /v1/runs {action: plan}; returns the Run resource."""
    async with _client() as client:
        response = await client.post(
            "/runs",
            json={
                "workspace_id": workspace_id,
                "action": "plan",
                "engine": engine,
                "variables": variables or {},
            },
        )
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result


@tool("terraform_apply", description="Apply an evaluated plan. Requires an approval token.", mutating=True)
async def terraform_apply(run_id: str, approval_token: str) -> dict[str, Any]:
    """Promote a planned run to apply; the approval token proves the human gate.

    Contract: POST /v1/runs with action=apply referencing the planned run's
    evaluated artifact, passing the approval token for verification. The
    platform rejects tokens that do not match a granted approval for this run.
    """
    raise NotImplementedError("POST /v1/runs {action: apply, source_run_id, approval_token}")


@tool("module_search", description="Semantic search over the module registry.")
async def module_search(query: str, provider: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
    """Search curated Terraform modules by intent (vector + keyword)."""
    raise NotImplementedError("GET /v1/modules/search?q=...&provider=...")


@tool("cost_estimate", description="Estimate the monthly cost delta of a plan.")
async def cost_estimate(run_id: str) -> dict[str, Any]:
    """Fetch (or compute) the cost estimate attached to a planned run."""
    raise NotImplementedError("GET /v1/costs/runs/{run_id}")


@tool("policy_check", description="Evaluate a plan against the tenant's OPA policy sets.")
async def policy_check(workspace_id: str, plan_json: dict[str, Any]) -> dict[str, Any]:
    """POST /v1/policies/evaluate; returns {allowed, enforcement_level, violations}."""
    async with _client() as client:
        response = await client.post(
            "/policies/evaluate",
            json={"workspace_id": workspace_id, "plan_json": plan_json},
        )
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result


@tool("scan_checkov", description="Run Checkov static analysis against a plan/configuration.")
async def scan_checkov(run_id: str) -> list[dict[str, Any]]:
    """Return Checkov findings recorded for the run's plan stage."""
    raise NotImplementedError("GET /v1/runs/{run_id}/scans?scanner=checkov")


@tool("scan_tfsec", description="Run tfsec static analysis against a plan/configuration.")
async def scan_tfsec(run_id: str) -> list[dict[str, Any]]:
    """Return tfsec findings recorded for the run's plan stage."""
    raise NotImplementedError("GET /v1/runs/{run_id}/scans?scanner=tfsec")


@tool("scan_trivy", description="Run Trivy scanning (IaC + images) for the run context.")
async def scan_trivy(run_id: str) -> list[dict[str, Any]]:
    """Return Trivy findings recorded for the run's plan stage."""
    raise NotImplementedError("GET /v1/runs/{run_id}/scans?scanner=trivy")


BUILTIN_TOOLS = [
    terraform_plan,
    terraform_apply,
    module_search,
    cost_estimate,
    policy_check,
    scan_checkov,
    scan_tfsec,
    scan_trivy,
]
