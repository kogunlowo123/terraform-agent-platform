"""Terraform CLI runner (subprocess wrapper with -json parsing)."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from tap_platform.runner.base import ApplyResult, IaCRunner, PlanResult


class TerraformRunner(IaCRunner):
    """Drives the ``terraform`` binary inside an ephemeral runner pod."""

    engine = "terraform"
    binary = "terraform"

    async def _exec(self, *args: str) -> tuple[int, str, str]:
        """Run the engine binary in the working dir; return (rc, stdout, stderr)."""
        process = await asyncio.create_subprocess_exec(
            self.binary,
            *args,
            cwd=self.working_dir,
            env={**os.environ, **self.env, "TF_IN_AUTOMATION": "1", "TF_INPUT": "0"},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return process.returncode or 0, stdout.decode(), stderr.decode()

    async def init(self, backend_config: dict[str, str] | None = None) -> None:
        """``terraform init -input=false`` with generated -backend-config args."""
        args = ["init", "-input=false", "-no-color"]
        for key, value in (backend_config or {}).items():
            args.append(f"-backend-config={key}={value}")
        rc, _, stderr = await self._exec(*args)
        if rc != 0:
            raise RuntimeError(f"terraform init failed: {stderr}")

    async def plan(
        self,
        *,
        variables: dict[str, Any] | None = None,
        destroy: bool = False,
        refresh_only: bool = False,
        out_file: str = "plan.out",
    ) -> PlanResult:
        """``terraform plan -out`` + ``show -json``; -detailed-exitcode drives has_changes."""
        args = ["plan", "-input=false", "-no-color", "-detailed-exitcode", f"-out={out_file}"]
        if destroy:
            args.append("-destroy")
        if refresh_only:
            args.append("-refresh-only")
        for key, value in (variables or {}).items():
            args.append(f"-var={key}={json.dumps(value) if not isinstance(value, str) else value}")

        rc, _, stderr = await self._exec(*args)
        if rc == 1:
            return PlanResult(succeeded=False, stderr=stderr)

        plan_json = await self.show(out_file)
        changes = plan_json.get("resource_changes", [])
        mutating = [
            c for c in changes
            if set(c.get("change", {}).get("actions", [])) - {"no-op", "read"}
        ]
        return PlanResult(
            succeeded=True,
            has_changes=rc == 2,
            plan_artifact_path=str(Path(self.working_dir) / out_file),
            plan_json=plan_json,
            resource_changes=len(mutating),
            # cost_delta_usd and scan_findings are attached by the cost/scan
            # steps of the runner entrypoint, not by the engine wrapper.
        )

    async def apply(self, plan_file: str) -> ApplyResult:
        """``terraform apply <plan_file>`` parsing the ``-json`` event stream.

        Contract: stream ``apply -json`` NDJSON events, count change_summary
        (add/change/remove), surface diagnostics on failure, and read the new
        state serial from the backend after completion.
        """
        raise NotImplementedError("apply -json NDJSON stream parsing + change summary")

    async def destroy(self, *, variables: dict[str, Any] | None = None) -> ApplyResult:
        """``terraform destroy`` via a destroy plan + apply of that artifact."""
        raise NotImplementedError("destroy = plan(destroy=True) then apply(plan.out)")

    async def show(self, plan_file: str) -> dict[str, Any]:
        """``terraform show -json <plan_file>`` -> parsed plan representation."""
        rc, stdout, stderr = await self._exec("show", "-json", plan_file)
        if rc != 0:
            raise RuntimeError(f"{self.binary} show failed: {stderr}")
        result: dict[str, Any] = json.loads(stdout)
        return result
