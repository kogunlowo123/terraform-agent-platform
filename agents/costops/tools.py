"""CostOps domain tools: forecasting, budget enforcement, rightsizing.

This agent is advisory + enforcing (its mutation_budget is 0): it blocks
over-budget runs via policy verdicts rather than mutating infrastructure
itself. Rightsizing changes are delegated to the infrastructure agent.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from tap_sdk import tool


class CostForecastInput(BaseModel):
    scope: str = Field(description="tenant | project:<id> | workspace:<slug>.")
    horizon_days: int = Field(default=90, ge=7, le=365)
    include_planned_changes: bool = Field(
        default=True, description="Fold pending plan cost deltas into the forecast."
    )


class CostForecastOutput(BaseModel):
    monthly_usd: list[float] = Field(description="Forecast per month across the horizon.")
    confidence: Literal["high", "medium", "low"]
    drivers: list[str] = Field(description="Top cost drivers, resource ids/services.")


class BudgetCheckInput(BaseModel):
    budget_id: str
    workspace: str
    proposed_delta_usd: float = Field(
        description="Monthly cost delta of the proposed run (from cost_estimate)."
    )


class BudgetCheckOutput(BaseModel):
    verdict: Literal["within_budget", "over_budget", "requires_approval"]
    budget_limit_usd: float
    projected_spend_usd: float
    overage_usd: float = Field(default=0.0)


class RightsizeRecommendInput(BaseModel):
    scope: str
    observation_window_days: int = Field(default=30, ge=14, description="Utilization window.")
    min_monthly_saving_usd: float = Field(
        default=10.0, description="Noise floor; smaller savings are not emitted."
    )


class RightsizeRecommendation(BaseModel):
    resource_id: str
    current: str = Field(description="Current size/sku.")
    recommended: str
    monthly_saving_usd: float
    utilization_evidence: str = Field(description="e.g. 'p95 CPU 11% over 30d'.")


class RightsizeRecommendOutput(BaseModel):
    recommendations: list[RightsizeRecommendation]
    total_monthly_saving_usd: float
    observation_window_days: int


@tool
def cost_forecast(params: CostForecastInput) -> CostForecastOutput:
    """Forecast spend for a scope over a horizon, optionally folding in the
    cost deltas of pending plans.

    Pure: reads billing exports + the cost estimate store.
    """
    # Contract: POST /v1/costs/forecast -> 200 {monthly_usd[], confidence, drivers[]}
    raise NotImplementedError("platform API binding injected by runner")


@tool
def budget_check(params: BudgetCheckInput) -> BudgetCheckOutput:
    """Check a proposed cost delta against a budget. The verdict is
    authoritative: 'over_budget' blocks the run via the policy engine
    (cost.budget.enforce), and the agent never suggests workarounds.

    Pure read, enforcing effect: the verdict is written to the policy input
    document for the associated run.
    """
    # Contract: POST /v1/costs/budgets/{budget_id}/check -> 200 {verdict,
    #   budget_limit_usd, projected_spend_usd, overage_usd}
    raise NotImplementedError("platform API binding injected by runner")


@tool
def rightsize_recommend(params: RightsizeRecommendInput) -> RightsizeRecommendOutput:
    """Produce rightsizing recommendations backed by utilization evidence.

    Pure: recommendations cite the observation window and utilization data;
    recommendations without data are not emitted. Execution is delegated to
    the infrastructure agent via the orchestrator.
    """
    # Contract: POST /v1/costs/rightsizing -> 200 {recommendations[],
    #   total_monthly_saving_usd, observation_window_days}
    raise NotImplementedError("platform API binding injected by runner")
