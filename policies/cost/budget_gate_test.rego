package tap.cost.budget_gate_test

import rego.v1

import data.tap.cost.budget_gate as policy

run(delta, budget) := {
	"cost": {"monthly_delta_usd": delta},
	"workspace": {"budget_usd": budget, "name": "payments-prod"},
}

test_under_budget_passes if {
	count(policy.deny) == 0 with input as run(100, 300)
	count(policy.soft_fail) == 0 with input as run(100, 300)
	count(policy.advisory) == 0 with input as run(100, 300)
}

test_approaching_budget_is_advisory if {
	count(policy.advisory) == 1 with input as run(280, 300)
	count(policy.soft_fail) == 0 with input as run(280, 300)
}

test_over_budget_soft_fails if {
	count(policy.soft_fail) == 1 with input as run(420.50, 300)
	count(policy.deny) == 0 with input as run(420.50, 300)
}

test_exactly_double_budget_still_soft_fail if {
	count(policy.soft_fail) == 1 with input as run(600, 300)
	count(policy.deny) == 0 with input as run(600, 300)
}

test_over_double_budget_hard_fails if {
	some msg in policy.deny with input as run(601, 300)
	contains(msg, "hard fail")
	count(policy.soft_fail) == 0 with input as run(601, 300)
}

test_no_budget_configured_is_advisory if {
	count(policy.deny) == 0 with input as run(5000, 0)
	count(policy.soft_fail) == 0 with input as run(5000, 0)
	some msg in policy.advisory with input as run(5000, 0)
	contains(msg, "no budget configured")
}

test_negative_delta_passes if {
	count(policy.deny) == 0 with input as run(-50, 300)
	count(policy.advisory) == 0 with input as run(-50, 300)
}
