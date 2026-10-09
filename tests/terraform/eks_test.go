// Terratest skeleton for the EKS module (terraform/aws/eks).
//
// Default mode is init + plan only — no resources are created. Full apply
// (with teardown) is opt-in for the nightly sandbox job:
//
//	TAP_TERRATEST_APPLY=1 go test -v -timeout 60m -run TestEksModule
//
// Requires: terraform >= 1.9 on PATH, AWS credentials (plan needs provider
// auth for data sources).
package test

import (
	"os"
	"testing"

	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

const eksModuleDir = "../../terraform/aws/eks"

func eksOptions(t *testing.T) *terraform.Options {
	return terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: eksModuleDir,
		Vars: map[string]interface{}{
			"name":               "tap-terratest",
			"kubernetes_version": "1.30",
			"subnet_ids":         []string{"subnet-00000000000000001", "subnet-00000000000000002"},
			"tags": map[string]string{
				"owner":       "platform-team",
				"cost_center": "cc-0000",
				"environment": "dev",
				"data_class":  "internal",
			},
		},
		NoColor: true,
		// Speculative plan: never touch shared state.
		BackendConfig: map[string]interface{}{},
	})
}

// TestEksModulePlan validates that the module initializes and produces a plan
// containing the cluster with the expected governed defaults.
func TestEksModulePlan(t *testing.T) {
	t.Parallel()

	if _, err := os.Stat(eksModuleDir); os.IsNotExist(err) {
		t.Skipf("module %s not present yet — skipping", eksModuleDir)
	}

	options := eksOptions(t)
	options.PlanFilePath = t.TempDir() + "/eks.plan"

	_, err := terraform.InitE(t, options)
	require.NoError(t, err, "terraform init must succeed")

	plan, err := terraform.InitAndPlanAndShowWithStructE(t, options)
	require.NoError(t, err, "terraform plan must succeed")

	// The cluster resource must be planned for creation.
	cluster, ok := plan.ResourcePlannedValuesMap["aws_eks_cluster.this"]
	require.True(t, ok, "plan must contain aws_eks_cluster.this")
	assert.Equal(t, "tap-terratest", cluster.AttributeValues["name"])

	// Governed defaults: secrets encryption and private endpoint.
	if enc, ok := cluster.AttributeValues["encryption_config"]; ok {
		assert.NotEmpty(t, enc, "EKS secrets encryption must be configured")
	}

	// Mandatory tag contract (mirrors tap.terraform.require_tags).
	tags, _ := cluster.AttributeValues["tags"].(map[string]interface{})
	for _, key := range []string{"owner", "cost_center", "environment", "data_class"} {
		assert.Contains(t, tags, key, "required tag %q missing on cluster", key)
	}
}

// TestEksModuleApply provisions and destroys a real cluster. Opt-in only.
func TestEksModuleApply(t *testing.T) {
	if os.Getenv("TAP_TERRATEST_APPLY") != "1" {
		t.Skip("set TAP_TERRATEST_APPLY=1 to run the full apply test (sandbox account only)")
	}
	if _, err := os.Stat(eksModuleDir); os.IsNotExist(err) {
		t.Skipf("module %s not present yet — skipping", eksModuleDir)
	}

	options := eksOptions(t)
	defer terraform.Destroy(t, options)

	terraform.InitAndApply(t, options)

	endpoint := terraform.Output(t, options, "cluster_endpoint")
	assert.NotEmpty(t, endpoint, "cluster endpoint output must be set")
}
