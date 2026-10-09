"""NetOps domain tools: CIDR planning (real subnet math), DNS, load balancers."""

from __future__ import annotations

import ipaddress
import math
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from tap_sdk import tool


class SubnetRequest(BaseModel):
    name: str
    hosts: int = Field(gt=0, description="Required usable host count.")
    tier: Literal["public", "private", "isolated"] = "private"


class CidrPlanInput(BaseModel):
    base_cidr: str = Field(description="Address space to carve, e.g. '10.20.0.0/16'.")
    availability_zones: int = Field(default=3, ge=1, le=6)
    subnets: list[SubnetRequest]
    existing_cidrs: list[str] = Field(
        default_factory=list, description="Tenant CIDRs to collision-check against."
    )

    @field_validator("base_cidr")
    @classmethod
    def _valid_cidr(cls, v: str) -> str:
        ipaddress.ip_network(v)  # raises ValueError on bad input
        return v


class PlannedSubnet(BaseModel):
    name: str
    az_index: int
    cidr: str
    tier: Literal["public", "private", "isolated"]
    usable_hosts: int


class CidrPlanOutput(BaseModel):
    subnets: list[PlannedSubnet]
    unallocated: list[str] = Field(description="Remaining free blocks in the base CIDR.")
    collisions: list[str] = Field(default_factory=list)


class DnsRecordManageInput(BaseModel):
    zone: str
    action: Literal["upsert", "delete"]
    record_type: Literal["A", "AAAA", "CNAME", "TXT", "MX", "SRV", "ALIAS"]
    name: str
    values: list[str]
    ttl_seconds: int = Field(default=300, ge=30)


class DnsRecordManageOutput(BaseModel):
    change_id: str
    status: Literal["pending", "applied", "pending_approval"]


class LbConfigureInput(BaseModel):
    workspace: str
    lb_type: Literal["application", "network"]
    listeners: list[dict[str, str]] = Field(description="[{port, protocol, target_group}].")
    tls_policy: str = Field(default="TLS13", description="Minimum TLS policy id.")
    internal: bool = True


class LbConfigureOutput(BaseModel):
    run_id: str
    status: Literal["planned", "applied", "pending_approval"]


@tool
def cidr_plan(params: CidrPlanInput) -> CidrPlanOutput:
    """Carve a base CIDR into per-AZ subnets sized for the requested hosts.

    Pure, fully implemented locally (subnet math, no platform call):
    allocates largest-first to minimise fragmentation, one subnet per AZ per
    request, and collision-checks against existing tenant CIDRs.
    """
    base = ipaddress.ip_network(params.base_cidr)
    existing = [ipaddress.ip_network(c) for c in params.existing_cidrs]
    collisions = [str(e) for e in existing if base.overlaps(e)]

    # Expand each request across AZs, then allocate largest-first.
    wanted: list[tuple[SubnetRequest, int, int]] = []  # (req, az, prefix)
    for req in params.subnets:
        # +5: network, broadcast, router, DNS, reserve (AWS-style).
        prefix = 32 - max(math.ceil(math.log2(req.hosts + 5)), 2)
        for az in range(params.availability_zones):
            wanted.append((req, az, prefix))
    wanted.sort(key=lambda w: w[2])  # smallest prefix (largest block) first

    free: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = [base]
    planned: list[PlannedSubnet] = []
    for req, az, prefix in wanted:
        candidate_idx = next(
            (i for i, blk in enumerate(free) if blk.prefixlen <= prefix), None
        )
        if candidate_idx is None:
            raise ValueError(
                f"address space exhausted: cannot fit /{prefix} for '{req.name}' az{az}"
            )
        block = free.pop(candidate_idx)
        carved = list(block.subnets(new_prefix=prefix))
        alloc, remainder = carved[0], carved[1:]
        # Return the remainder as coalesced free blocks.
        free.extend(ipaddress.collapse_addresses(remainder))
        free.sort(key=lambda n: (n.prefixlen, int(n.network_address)), reverse=True)
        planned.append(
            PlannedSubnet(
                name=f"{req.name}-az{az}",
                az_index=az,
                cidr=str(alloc),
                tier=req.tier,
                usable_hosts=alloc.num_addresses - 5,
            )
        )
    return CidrPlanOutput(
        subnets=planned,
        unallocated=sorted(str(f) for f in ipaddress.collapse_addresses(free)),
        collisions=collisions,
    )


@tool
def dns_record_manage(params: DnsRecordManageInput) -> DnsRecordManageOutput:
    """Create, update or delete a DNS record via a governed change.

    Mutating: production zones and apex changes route through approval.
    Deletes are treated as destructive (always escalate).
    """
    # Contract: POST /v1/network/dns/{zone}/changes -> 202 {change_id, status}
    raise NotImplementedError("platform API binding injected by runner")


@tool
def lb_configure(params: LbConfigureInput) -> LbConfigureOutput:
    """Configure a load balancer (listeners, target groups, TLS policy)
    through a governed Terraform run.

    Mutating: listener changes on internet-facing LBs require approval;
    TLS policy downgrades are denied by policy.
    """
    # Contract: POST /v1/workspaces/{workspace}/runs (lb module overlay)
    #   -> 202 {run_id, status}
    raise NotImplementedError("platform API binding injected by runner")
