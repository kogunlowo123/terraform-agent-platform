"""OpenTofu CLI runner.

OpenTofu is CLI-compatible with Terraform for everything TAP uses (init /
plan -out / show -json / apply -json / destroy), so this runner reuses the
Terraform wrapper and only swaps the binary and automation env vars.
"""

from __future__ import annotations

from tap_platform.runner.terraform_runner import TerraformRunner


class OpenTofuRunner(TerraformRunner):
    """Drives the ``tofu`` binary inside an ephemeral runner pod."""

    engine = "opentofu"
    binary = "tofu"
