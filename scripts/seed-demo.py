#!/usr/bin/env python3
"""Seed a demo tenant into a running TAP control plane.

Creates: tenant -> project -> workspace -> demo agent registration, via the
public API (idempotent: safe to rerun; existing objects are reused).

Usage:
    python scripts/seed-demo.py [--api-url http://localhost:8080] [--token TOKEN]

Environment:
    TAP_API_URL   (default http://localhost:8080)
    TAP_API_TOKEN (default: none — dev servers run with auth disabled)
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

import httpx

DEMO_TENANT = {"name": "demo", "display_name": "Demo Tenant", "isolation_tier": "pooled"}
DEMO_PROJECT = {"name": "getting-started", "description": "Seeded demo project"}
DEMO_WORKSPACE = {
    "name": "aws-vpc-baseline",
    "environment": "dev",
    "iac_engine": "terraform",
    "working_directory": "examples/aws-vpc-baseline",
    "budget_usd": 100,
    "tags": {
        "owner": "platform-team",
        "cost_center": "cc-0000",
        "environment": "dev",
        "data_class": "internal",
    },
}
DEMO_AGENT = {
    "name": "infra-agent-demo",
    "version": "0.1.0",
    "capabilities": ["infrastructure.provision", "infrastructure.plan"],
    "subject": "agent.infra-agent-demo.request",
    "manifest": {
        "description": "Seeded demo infrastructure agent",
        "guardrails": {"dry_run_default": True, "mutation_budget": 10},
    },
}


def ensure(client: httpx.Client, path: str, body: dict[str, Any], key: str = "name") -> dict[str, Any]:
    """POST `body` to `path`; on 409 fetch the existing object instead."""
    resp = client.post(path, json=body)
    if resp.status_code == 409:
        existing = client.get(path, params={key: body[key]})
        existing.raise_for_status()
        items = existing.json().get("items", [])
        if items:
            print(f"  = exists {path} {body[key]!r}")
            return dict(items[0])
        resp.raise_for_status()
    resp.raise_for_status()
    print(f"  + created {path} {body[key]!r}")
    return dict(resp.json())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default=os.environ.get("TAP_API_URL", "http://localhost:8080"))
    parser.add_argument("--token", default=os.environ.get("TAP_API_TOKEN", ""))
    args = parser.parse_args()

    headers = {"Authorization": f"Bearer {args.token}"} if args.token else {}
    with httpx.Client(base_url=args.api_url, headers=headers, timeout=15.0) as client:
        try:
            health = client.get("/healthz")
            health.raise_for_status()
        except httpx.HTTPError as exc:
            print(f"error: TAP API not reachable at {args.api_url}: {exc}", file=sys.stderr)
            return 1

        print(f"Seeding demo data into {args.api_url}")
        tenant = ensure(client, "/v1/tenants", DEMO_TENANT)
        tenant_id = tenant.get("id", tenant.get("tenant_id"))

        project = ensure(client, f"/v1/tenants/{tenant_id}/projects", DEMO_PROJECT)
        project_id = project.get("id", project.get("project_id"))

        workspace = ensure(client, f"/v1/projects/{project_id}/workspaces", DEMO_WORKSPACE)
        workspace_id = workspace.get("id", workspace.get("workspace_id"))

        agent = ensure(client, f"/v1/tenants/{tenant_id}/agents", DEMO_AGENT)

        print("\nDemo environment ready:")
        print(f"  tenant     {tenant_id}  (demo)")
        print(f"  project    {project_id}  (getting-started)")
        print(f"  workspace  {workspace_id}  (aws-vpc-baseline, budget $100/mo)")
        print(f"  agent      {agent.get('name', DEMO_AGENT['name'])} v{DEMO_AGENT['version']}")
        print("\nFirst governed run:")
        print("  tap run plan --workspace aws-vpc-baseline --dir examples/aws-vpc-baseline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
