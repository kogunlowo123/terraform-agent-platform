"""Dual Terraform/OpenTofu runner abstraction + ephemeral K8s job launcher.

Runners implement :class:`tap_platform.runner.base.IaCRunner` and are
discovered via the ``tap.runners`` entry-point group.
"""

from __future__ import annotations

__all__ = ["base", "k8s_job_launcher", "opentofu_runner", "terraform_runner"]
