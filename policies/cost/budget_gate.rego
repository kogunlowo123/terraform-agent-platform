# Cost budget gate.
#
# Input (assembled by the Run workflow from Infracost / cost estimation):
#   {
#     "cost":      {"monthly_delta_usd": 420.50},
#     "workspace": {"budget_usd": 300, "name": "payments-prod"}
#   }
#
# Decision ladder:
#   * delta >  2x budget          -> deny       (hard fail, run blocked)
#   * budget < delta <= 2x budget -> soft_fail  (approval required)
#   * 80% of budget < delta       -> advisory   (surfaced, never blocks)
#   * no budget configured        -> advisory
package tap.cost.budget_gate

import rego.v1

delta := object.get(input, ["cost", "monthly_delta_usd"], 0)

budget := object.get(input, ["workspace", "budget_usd"], 0)

workspace := object.get(input, ["workspace", "name"], "unknown")

deny contains msg if {
	budget > 0
	delta > 2 * budget
	msg := sprintf(
		"workspace %q: monthly cost delta $%.2f exceeds 2x budget ($%.2f); hard fail",
		[workspace, delta, budget],
	)
}

soft_fail contains msg if {
	budget > 0
	delta > budget
	delta <= 2 * budget
	msg := sprintf(
		"workspace %q: monthly cost delta $%.2f exceeds budget $%.2f; approval required",
		[workspace, delta, budget],
	)
}

advisory contains msg if {
	budget > 0
	delta > 0.8 * budget
	delta <= budget
	msg := sprintf(
		"workspace %q: monthly cost delta $%.2f is above 80%% of budget $%.2f",
		[workspace, delta, budget],
	)
}

advisory contains msg if {
	budget == 0
	delta > 0
	msg := sprintf(
		"workspace %q: no budget configured; cost delta $%.2f is ungoverned",
		[workspace, delta],
	)
}
