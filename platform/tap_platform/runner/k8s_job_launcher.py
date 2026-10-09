"""Ephemeral Kubernetes Job launcher for IaC runners.

Security posture (ARCHITECTURE.md §5/§12):
* single-use pods — one Job per run stage, TTL-deleted after completion;
* **no service account token** mounted (``automountServiceAccountToken: false``);
* cloud credentials are 15-minute OIDC tokens injected via env, scoped to the
  workspace's cloud role — never static secrets;
* hard resource limits and a restricted security context.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tap_platform.config import Settings, get_settings


@dataclass
class RunnerJobSpec:
    """Inputs needed to render one runner Job manifest."""

    run_id: str
    tenant_id: str
    workspace_id: str
    engine: str  # terraform | opentofu
    command: str  # plan | apply | destroy | show
    image: str
    oidc_token_env: dict[str, str] = field(default_factory=dict)
    plan_artifact_uri: str | None = None
    cpu_limit: str = "1"
    memory_limit: str = "2Gi"
    active_deadline_seconds: int = 2700  # 45 min, matches workflow timeout


class K8sJobLauncher:
    """Builds and submits ephemeral runner Jobs."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def build_job_manifest(self, spec: RunnerJobSpec) -> dict[str, Any]:
        """Render the Job manifest dict (no API call; pure function, testable)."""
        name = f"tap-runner-{spec.run_id[:8]}-{spec.command}"
        env = [{"name": k, "value": v} for k, v in spec.oidc_token_env.items()]
        env += [
            {"name": "TAP_RUN_ID", "value": spec.run_id},
            {"name": "TAP_TENANT_ID", "value": spec.tenant_id},
            {"name": "TAP_WORKSPACE_ID", "value": spec.workspace_id},
            {"name": "TAP_ENGINE", "value": spec.engine},
            {"name": "TAP_COMMAND", "value": spec.command},
        ]
        if spec.plan_artifact_uri:
            env.append({"name": "TAP_PLAN_ARTIFACT_URI", "value": spec.plan_artifact_uri})

        return {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "name": name,
                "namespace": self._settings.runner_namespace,
                "labels": {
                    "app.kubernetes.io/part-of": "tap",
                    "tap.io/run-id": spec.run_id,
                    "tap.io/tenant-id": spec.tenant_id,
                },
            },
            "spec": {
                "backoffLimit": 0,  # retries are Temporal's job, not kubelet's
                "ttlSecondsAfterFinished": 600,
                "activeDeadlineSeconds": spec.active_deadline_seconds,
                "template": {
                    "spec": {
                        "restartPolicy": "Never",
                        "automountServiceAccountToken": False,  # no K8s API access
                        "securityContext": {
                            "runAsNonRoot": True,
                            "runAsUser": 65532,
                            "seccompProfile": {"type": "RuntimeDefault"},
                        },
                        "containers": [
                            {
                                "name": "runner",
                                "image": spec.image,
                                "env": env,
                                "resources": {
                                    "requests": {"cpu": "250m", "memory": "512Mi"},
                                    "limits": {
                                        "cpu": spec.cpu_limit,
                                        "memory": spec.memory_limit,
                                    },
                                },
                                "securityContext": {
                                    "allowPrivilegeEscalation": False,
                                    "readOnlyRootFilesystem": False,  # TF writes .terraform/
                                    "capabilities": {"drop": ["ALL"]},
                                },
                            }
                        ],
                    }
                },
            },
        }

    def image_for_engine(self, engine: str) -> str:
        """Resolve the pinned runner image for an engine."""
        if engine == "opentofu":
            return self._settings.runner_image_opentofu
        return self._settings.runner_image_terraform

    async def launch(self, spec: RunnerJobSpec) -> str:
        """Submit the Job and return its name.

        Contract: create via the kubernetes client (``BatchV1Api.create_namespaced_job``)
        using the manifest from :meth:`build_job_manifest`; caller polls or
        watches for completion (see activities.schedule_runner_job).
        """
        raise NotImplementedError("kubernetes BatchV1Api create_namespaced_job")

    async def wait(self, job_name: str, *, poll_seconds: float = 5.0) -> bool:
        """Poll the Job until terminal; return True on success, False on failure."""
        raise NotImplementedError("watch Job status conditions Complete/Failed")
