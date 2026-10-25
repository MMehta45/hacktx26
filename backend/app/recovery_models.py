from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Literal

from pydantic import Field, model_validator

from app.models import ApiModel, CustomerSnapshot
from app.research_models import Evidence, ResearchContext, ResearchResult
from app.simulation_models import (
    BillOutcome,
    CrisisSimulationRequest,
    RecoveryEffect,
    SimulationResult,
)

RequirementStatus = Literal[
    "unknown",
    "possible",
    "pending_external_approval",
    "user_reported_confirmed",
    "externally_verified",
    "rejected",
    "expired",
]


class RecoveryRequirement(ApiModel):
    id: str
    candidate_ids: list[str]
    condition: str
    status: RequirementStatus = "unknown"
    source: Literal["system", "user_answer", "user_confirmation", "provider_evidence"] = "system"
    established_by_id: str | None = None
    effective_dates: list[date] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RecoveryAnswer(ApiModel):
    question_id: str
    # `not_yet` is explicit unresolved state; it is not false/empty/zero.
    value: Literal["not_yet"] | bool | int | str | list[date]
    clarification: str | None = Field(default=None, max_length=500)
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RecoveryQuestion(ApiModel):
    id: str
    prompt: str
    answer_type: Literal["yes_no", "choice", "number", "date", "date_range", "free_text"]
    reason: str
    requirement_ids: list[str]
    candidate_ids: list[str]
    priority_score: int = Field(ge=1, le=27)
    choices: list[str] = Field(default_factory=list)
    depends_on_question_id: str | None = None
    active: bool = True


class OutreachDraft(ApiModel):
    id: str
    candidate_id: str
    kind: Literal[
        "remote_work_request",
        "shift_adjustment_request",
        "bill_extension_request",
        "mechanic_estimate_request",
    ]
    recipient: str
    subject: str
    body: str
    status: Literal["draft_prepared"] = "draft_prepared"
    disclaimer: str = "Prepared for copying only; this message has not been sent or approved."


class RecoveryActionDefinition(ApiModel):
    id: str
    title: str
    strategy: Literal[
        "income_preservation",
        "transportation",
        "bill_flexibility",
        "repair_affordability",
        "cash_preservation",
        "assistance",
        "borrowing",
    ]
    description: str
    effects: list[RecoveryEffect]
    requirement_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    incompatible_action_ids: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    quantified: bool = True
    evidence_status: Literal[
        "verified_route_feasible",
        "demo_scenario_assumption",
        "conditionally_feasible",
        "route_infeasible",
        "insufficient_schedule_evidence",
    ] | None = None


class PlanDelta(ApiModel):
    essential_unpaid_change_cents: int
    peak_funding_gap_change_cents: int
    ending_balance_change_cents: int
    recovered_shift_ids: list[str]
    income_preserved_cents: int = Field(ge=0)
    additional_take_home_earned_cents: int = Field(default=0, ge=0)
    additional_pay_received_cents: int = Field(default=0, ge=0)
    additional_pay_after_horizon_cents: int = Field(default=0, ge=0)
    incremental_cost_cents: int = Field(ge=0)
    repair_date_change_days: int | None = None


class PlanSource(ApiModel):
    evidence_id: str
    title: str
    url: str | None
    supports: list[str]
    limitations: list[str]


class PlanResource(ApiModel):
    id: str
    resource_type: Literal["external_link", "transit_route", "provider_contact", "assistance_program", "outreach_draft", "internal_action"]
    title: str
    action_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    url: str | None = None
    resource_date: date | None = Field(default=None, validation_alias="date", serialization_alias="date")
    details: str
    limitations: list[str] = Field(default_factory=list)


class PlanTimelineEvent(ApiModel):
    event_date: date = Field(validation_alias="date", serialization_alias="date")
    event_type: Literal["decision", "shift", "expense", "payday", "bill_due", "repair", "consequence"]
    label: str
    action_ids: list[str] = Field(default_factory=list)
    conditional: bool = False


class PlanReconciliation(ApiModel):
    direct_recovered_shift_ids: list[str] = Field(default_factory=list)
    indirect_recovered_shift_ids: list[str] = Field(default_factory=list)
    remaining_missed_shift_ids: list[str] = Field(default_factory=list)
    direct_income_preserved_cents: int = Field(default=0, ge=0)
    indirect_income_preserved_cents: int = Field(default=0, ge=0)
    total_income_preserved_cents: int = Field(default=0, ge=0)
    direct_earned_take_home_cents: int = Field(default=0, ge=0)
    indirect_earned_take_home_cents: int = Field(default=0, ge=0)
    additional_pay_received_cents: int = Field(default=0, ge=0)
    additional_pay_after_horizon_cents: int = Field(default=0, ge=0)
    payday_differences: dict[str, int] = Field(default_factory=dict)
    unpaid_bills: list[BillOutcome] = Field(default_factory=list)
    worst_gap_date: date | None = None


class RecoveryPlan(ApiModel):
    id: str
    rank: int = Field(ge=1)
    name: str
    strategy_labels: list[str]
    feasibility: Literal[
        "ready_with_confirmed_conditions",
        "conditional_pending_approval",
        "conditional_pending_information",
    ]
    conditional_label: str
    action_ids: list[str] = Field(min_length=1, max_length=3)
    actions: list[RecoveryActionDefinition]
    unresolved_requirement_ids: list[str]
    conditional_assumptions: list[str]
    result: SimulationResult
    delta: PlanDelta
    ranking_rationale: list[str]
    ranking_score: int = 0
    explanation: str
    sources: list[PlanSource]
    outreach_drafts: list[OutreachDraft]
    next_steps: list[str]
    resources: list[PlanResource] = Field(default_factory=list)
    timeline: list[PlanTimelineEvent] = Field(default_factory=list)
    reconciliation: PlanReconciliation = Field(default_factory=PlanReconciliation)
    exclusion_reasons: list[str] = Field(default_factory=list)


class RecoveryEvaluation(ApiModel):
    baseline_fingerprint: str
    baseline: SimulationResult
    evaluated_plan_count: int = Field(ge=0)
    pruned_combination_count: int = Field(ge=0)
    plans: list[RecoveryPlan] = Field(max_length=8)


class FinancialOpportunity(ApiModel):
    """Read-only history analysis; never itself adds a forecast ledger entry."""

    id: str
    kind: Literal["scheduled_bill", "recurring_charge", "variable_spending"]
    merchant: str
    category: str
    classification: Literal["fixed_essential", "variable_essential", "discretionary"]
    monthly_average_cents: int = Field(ge=0)
    expected_next_date: date | None = None
    confidence: Literal["confirmed", "high", "medium", "low"]
    transaction_ids: list[str] = Field(default_factory=list)
    scheduled_bill_id: str | None = None
    forecast_included: bool = False
    potential_savings_cents: int | None = Field(default=None, ge=0)
    explanation: str


class CandidateSummary(ApiModel):
    total_research_candidates: int = Field(default=0, ge=0)
    executable_actions: int = Field(default=0, ge=0)
    conditional_executable_actions: int = Field(default=0, ge=0)
    unquantified_leads: int = Field(default=0, ge=0)
    blocked_candidates: int = Field(default=0, ge=0)


class RecoverySession(ApiModel):
    schema_version: Literal[1] = 1
    id: str
    scenario_fingerprint: str
    research_run_id: str | None
    research_context: ResearchContext = Field(default_factory=ResearchContext)
    scenario: CrisisSimulationRequest
    version: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime
    answers: list[RecoveryAnswer]
    requirements: list[RecoveryRequirement]
    candidate_actions: list[RecoveryActionDefinition]
    questions: list[RecoveryQuestion]
    next_question_ids: list[str] = Field(max_length=2)
    outreach_drafts: list[OutreachDraft]
    evidence: list[Evidence]
    # Immutable Explore payload retained for traceability and Build 04 follow-up questions.
    research: ResearchResult | None = None
    financial_opportunities: list[FinancialOpportunity] = Field(default_factory=list)
    actionable_resources: list[PlanResource] = Field(default_factory=list)
    candidate_summary: CandidateSummary = Field(default_factory=CandidateSummary)
    evaluation: RecoveryEvaluation
    research_calls_used: int = Field(default=0, ge=0)
    research_cache_hits: int = Field(default=0, ge=0)
    warnings: list[str] = Field(default_factory=list)


class CreateRecoverySessionRequest(ApiModel):
    scenario: CrisisSimulationRequest = Field(default_factory=CrisisSimulationRequest)
    research: ResearchResult | None = None
    context: ResearchContext = Field(default_factory=ResearchContext)


class SubmitAnswerRequest(ApiModel):
    session_version: int = Field(ge=1)
    question_id: str
    value: Literal["not_yet"] | bool | int | str | list[date]
    clarification: str | None = Field(default=None, max_length=500)


class RequirementUpdateRequest(ApiModel):
    session_version: int = Field(ge=1)
    requirement_id: str
    status: RequirementStatus
    source: Literal["user_confirmation", "provider_evidence"]
    effective_dates: list[date] = Field(default_factory=list)


class EvaluateRecoveryRequest(ApiModel):
    session_version: int = Field(ge=1)
    max_actions_per_plan: int = Field(default=3, ge=1, le=3)
    max_candidate_actions: int = Field(default=8, ge=1, le=8)


class TargetedResearchRequest(ApiModel):
    session_version: int = Field(ge=1)
    candidate_ids: list[str] = Field(min_length=1, max_length=3)


class TargetedResearchResult(ApiModel):
    session: RecoverySession
    calls_used: int = Field(ge=0)
    cache_hits: int = Field(ge=0)
    message: str


class StoredRecoverySession(ApiModel):
    public: RecoverySession
    snapshot: CustomerSnapshot
    research: ResearchResult | None = None

    @model_validator(mode="after")
    def matching_research(self) -> StoredRecoverySession:
        if self.research and self.public.research_run_id != self.research.run_id:
            raise ValueError("Stored research does not match the recovery session.")
        return self
