from datetime import date, datetime, time
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, field_validator, model_validator

from app.models import ApiModel, CustomerSnapshot
from app.simulation_models import CrisisSimulationRequest, SimulationResult

NODE_IDS = frozenset(
    {
        "car_breaks_down",
        "car_unavailable",
        "commute_disrupted",
        "missed_work",
        "reduced_paycheck",
        "cash_shortfall",
        "bills_unpaid",
        "unexpected_repair_expense",
        "cash_reserves_depleted",
        "repair_delayed",
        "extra_transportation_costs",
        "emergency_borrowing",
        "future_debt_payments",
        "late_fees",
    }
)
NodeId = Literal[
    "car_breaks_down",
    "car_unavailable",
    "commute_disrupted",
    "missed_work",
    "reduced_paycheck",
    "cash_shortfall",
    "bills_unpaid",
    "unexpected_repair_expense",
    "cash_reserves_depleted",
    "repair_delayed",
    "extra_transportation_costs",
    "emergency_borrowing",
    "future_debt_payments",
    "late_fees",
]


def clean_url(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parts = urlsplit(value)
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username:
            return None
        filtered = [
            (key, val)
            for key, val in parse_qsl(parts.query)
            if key.lower() not in {"api_key", "key", "token", "access_token"}
        ]
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(filtered), ""))
    except ValueError:
        return None


class ResearchContext(ApiModel):
    city: str = Field(default="Austin, TX", min_length=2, max_length=100)
    timezone: Literal["America/Chicago"] = "America/Chicago"
    home_location: str | None = Field(default="3810 N Lamar Blvd, Austin, TX 78756", max_length=150)
    work_location: str | None = Field(default="525 N Lamar Blvd, Austin, TX 78703", max_length=150)
    shift_start_local: time | None = time(8, 0)
    shift_end_local: time | None = time(16, 0)
    fictional_employer: str = Field(default="Cedarstone Services", max_length=100)
    job_context: str = Field(
        default="Hourly Customer Support Specialist; normally onsite", max_length=150
    )
    remote_work_eligibility: Literal["unknown"] = "unknown"
    work_equipment_availability: Literal["unknown"] = "unknown"
    shift_flexibility: Literal["unknown"] = "unknown"
    make_up_hours_ability: Literal["unknown"] = "unknown"
    workdays: list[Literal["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]] = Field(
        default_factory=lambda: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    )
    primary_transportation: Literal["Personal car"] = "Personal car"


class ResearchRequest(ApiModel):
    scenario: CrisisSimulationRequest = Field(default_factory=CrisisSimulationRequest)
    context: ResearchContext = Field(default_factory=ResearchContext)
    force_refresh: bool = False


class PriorityTarget(ApiModel):
    node_id: NodeId
    impact: int = Field(ge=1, le=3)
    urgency: int = Field(ge=1, le=3)
    actionability: int = Field(ge=1, le=3)
    priority_score: int
    reason: str

    @field_validator("node_id")
    @classmethod
    def known_node(cls, value: str) -> str:
        if value not in NODE_IDS:
            raise ValueError("Unknown graph node")
        return value

    @model_validator(mode="after")
    def correct_score(self) -> "PriorityTarget":
        if self.priority_score != self.impact * self.urgency * self.actionability:
            raise ValueError("Incorrect priority score")
        return self


class TransitLeg(ApiModel):
    mode: str
    route: str | None = None
    departure: datetime | None = None
    arrival: datetime | None = None
    boarding_stop: str | None = None
    alighting_stop: str | None = None
    duration_minutes: int | None = Field(default=None, ge=0)
    distance_meters: int | None = Field(default=None, ge=0)


class Evidence(ApiModel):
    id: str
    source_type: Literal["web", "place", "place_review", "transit_directions"]
    provider_engine: str
    title: str
    url: str | None = None
    query: str
    retrieved_at: datetime
    facts_supported: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    snippet: str | None = None
    source_domain: str | None = None
    observed_cost_cents: int | None = Field(default=None, ge=0)
    transit_arrival: datetime | None = None
    transit_departure: datetime | None = None
    transit_request_kind: Literal["arrive_by", "depart_at"] | None = None
    transit_request_date: date | None = None
    place_address: str | None = None
    rating: float | None = Field(default=None, ge=0, le=5)
    review_snippets: list[str] = Field(default_factory=list)
    review_count: int | None = Field(default=None, ge=0)
    provider_business_id: str | None = None
    parent_place_evidence_id: str | None = None
    positive_price_review_snippets: list[str] = Field(default_factory=list)
    negative_price_review_snippets: list[str] = Field(default_factory=list)
    price_evidence_score: float | None = Field(default=None, ge=0, le=1)
    transparency_evidence_score: float | None = Field(default=None, ge=0, le=1)
    shop_score: float | None = Field(default=None, ge=0, le=1)
    affordability_confidence: Literal["none", "low", "moderate"] | None = None
    route_numbers: list[str] = Field(default_factory=list)
    transfer_count: int | None = Field(default=None, ge=0)
    walking_distance_meters: int | None = Field(default=None, ge=0)
    transit_stops: list[str] = Field(default_factory=list)
    transit_origin: str | None = None
    transit_destination: str | None = None
    transit_duration_minutes: int | None = Field(default=None, ge=0)
    walking_duration_minutes: int | None = Field(default=None, ge=0)
    boarding_stop: str | None = None
    alighting_stop: str | None = None
    fare_source: str | None = None
    fare_certainty: Literal["observed", "unknown"] | None = None
    transit_legs: list[TransitLeg] = Field(default_factory=list)

    @field_validator("url")
    @classmethod
    def valid_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        clean = clean_url(value)
        if clean is None:
            raise ValueError("Invalid evidence URL")
        return clean

    @field_validator("retrieved_at", "transit_arrival", "transit_departure")
    @classmethod
    def timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("Evidence timestamps must include a timezone")
        return value


class Requirement(ApiModel):
    key: str
    status: Literal["verified", "unknown", "false", "user_confirmed"]
    description: str
    verification_source_ids: list[str] = Field(default_factory=list)


class CandidateCost(ApiModel):
    amount_cents: int | None = Field(default=None, ge=0)
    currency: Literal["USD"] = "USD"
    status: Literal["unknown", "estimate", "observed"] = "unknown"
    basis: str

    @model_validator(mode="after")
    def coherent_amount(self) -> "CandidateCost":
        if self.status == "unknown" and self.amount_cents is not None:
            raise ValueError("Unknown cost cannot have a numeric amount")
        if self.status in {"estimate", "observed"} and self.amount_cents is None:
            raise ValueError("Estimated or observed cost needs a numeric amount")
        return self


class CandidateTiming(ApiModel):
    earliest_start_date: date | None = None
    latest_completion_date: date | None = None
    duration_description: str = "Timing requires confirmation"

    @model_validator(mode="after")
    def ordered_dates(self) -> "CandidateTiming":
        if (
            self.earliest_start_date
            and self.latest_completion_date
            and self.latest_completion_date < self.earliest_start_date
        ):
            raise ValueError("Completion cannot precede start")
        return self


class PotentialEffects(ApiModel):
    shift_dates_potentially_protected: list[date] = Field(default_factory=list)
    expense_avoided_cents: int | None = Field(default=None, ge=0)
    expense_avoidance_date: date | None = None
    bill_due_date_change: date | None = None


class CandidateAction(ApiModel):
    id: str
    title: str
    mechanism: Literal[
        "transportation",
        "income_preservation",
        "repair_affordability",
        "bill_flexibility",
        "budget_adjustment",
        "assistance",
        "borrowing_risk",
    ]
    addresses_node_ids: list[NodeId] = Field(min_length=1)
    description: str
    requirements: list[Requirement] = Field(default_factory=list)
    cost: CandidateCost
    timing: CandidateTiming = Field(default_factory=CandidateTiming)
    potential_effects: PotentialEffects = Field(default_factory=PotentialEffects)
    evidence_ids: list[str] = Field(default_factory=list)
    hypothesis_ids: list[str] = Field(default_factory=list)
    verification_status: Literal["hypothesis", "researched", "conditional", "unverified", "blocked"]
    remaining_unknowns: list[str] = Field(default_factory=list)
    confidence_explanation: str = "Further verification required."

    @field_validator("addresses_node_ids")
    @classmethod
    def known_nodes(cls, values: list[str]) -> list[str]:
        if any(value not in NODE_IDS for value in values):
            raise ValueError("Unknown graph node")
        return values

    @model_validator(mode="after")
    def grounded_status(self) -> "CandidateAction":
        if self.verification_status != "hypothesis" and not self.evidence_ids:
            raise ValueError("Evidence required for non-hypothesis candidate")
        if self.cost.status == "observed" and (
            self.cost.amount_cents is None or not self.evidence_ids
        ):
            raise ValueError("Observed cost requires amount and evidence")
        return self


class ClarifyingQuestion(ApiModel):
    id: str
    question: str
    addresses_node_ids: list[NodeId]
    related_candidate_ids: list[str] = Field(default_factory=list)
    resolves_requirement_keys: list[str] = Field(min_length=1)
    decision_impact: int = Field(ge=1, le=3)
    uncertainty: int = Field(ge=1, le=3)
    top_candidate_relevance: int = Field(ge=1, le=3)
    priority_score: int
    reason: str
    answer_type: Literal["yes_no", "number", "choice", "free_text"] = "free_text"
    status: Literal["pending"] = "pending"

    @field_validator("addresses_node_ids")
    @classmethod
    def known_nodes(cls, values: list[str]) -> list[str]:
        if any(value not in NODE_IDS for value in values):
            raise ValueError("Unknown graph node")
        return values

    @model_validator(mode="after")
    def correct_score(self) -> "ClarifyingQuestion":
        if (
            self.priority_score
            != self.decision_impact * self.uncertainty * self.top_candidate_relevance
        ):
            raise ValueError("Incorrect question score")
        return self


class ResearchExtraction(ApiModel):
    candidate_actions: list[CandidateAction] = Field(default_factory=list, max_length=12)
    clarifying_questions: list[ClarifyingQuestion] = Field(default_factory=list, max_length=8)


class ExtractionDiagnostic(ApiModel):
    attempt: int = Field(ge=1, le=2)
    code: Literal["malformed_json", "schema_validation", "truncated", "provider_error"]
    message: str
    finish_reason: str | None = None
    output_tokens: int | None = Field(default=None, ge=0)
    recovered: bool = False


class HypothesisOutcome(ApiModel):
    hypothesis_id: str
    status: Literal[
        "viable_candidate",
        "conditional_candidate",
        "blocked",
        "rejected",
        "insufficient_evidence",
    ]
    candidate_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    reason: str


class ResearchEvent(ApiModel):
    id: str
    type: Literal[
        "target_selected",
        "hypothesis_generated",
        "search_started",
        "search_completed",
        "search_failed",
        "evidence_found",
        "candidate_extracted",
        "extraction_retry",
        "extraction_fallback",
        "question_identified",
        "research_finished",
        "pathway_started",
        "pathway_finished",
        "pathway_blocked",
        "pathway_skipped",
    ]
    timestamp: datetime
    message: str
    target_node_id: str | None = None
    tool: str | None = None
    evidence_id: str | None = None
    pathway_id: str | None = None


class ResearchHypothesis(ApiModel):
    id: str
    title: str
    mechanism: str
    target_node_ids: list[NodeId]
    impact: int = Field(ge=1, le=3)
    urgency: int = Field(ge=1, le=3)
    actionability: int = Field(ge=1, le=3)
    priority_score: int
    evidence_need: str
    investigation_mode: Literal["public_research", "ask_user", "no_research"]
    suggested_tool: Literal["search_web", "search_places", "find_transit"] | None = None
    suggested_query: str | None = None
    origin: Literal["baseline", "gemini", "emerged"]

    @model_validator(mode="after")
    def correct_priority(self) -> "ResearchHypothesis":
        if self.priority_score != self.impact * self.urgency * self.actionability:
            raise ValueError("Incorrect hypothesis score")
        if self.investigation_mode == "public_research" and self.suggested_tool is None:
            raise ValueError("Public research hypothesis requires a tool")
        return self


class ResearchPathway(ApiModel):
    id: str
    label: str
    status: Literal["successful", "inconclusive", "blocked", "failed", "skipped_budget"]
    target_node_ids: list[NodeId]
    tool_calls_used: int = Field(ge=0)
    evidence_ids: list[str] = Field(default_factory=list)
    message: str


class ResearchResult(ApiModel):
    schema_version: Literal[1] = 1
    status: Literal["completed", "partial", "failed", "no_results", "not_configured"]
    run_id: str
    simulation_fingerprint: str
    research_started_at: datetime
    research_finished_at: datetime
    priority_targets: list[PriorityTarget]
    hypotheses: list[ResearchHypothesis] = Field(default_factory=list)
    pathways: list[ResearchPathway] = Field(default_factory=list)
    research_events: list[ResearchEvent]
    evidence: list[Evidence]
    candidate_actions: list[CandidateAction]
    hypothesis_outcomes: list[HypothesisOutcome] = Field(default_factory=list)
    extraction_diagnostics: list[ExtractionDiagnostic] = Field(default_factory=list)
    clarifying_questions: list[ClarifyingQuestion] = Field(default_factory=list, max_length=8)
    initial_question_ids: list[str] = Field(default_factory=list, max_length=2)
    tool_calls_used: int = Field(ge=0)
    cache_hits: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)


class ResearchResponse(ApiModel):
    snapshot: CustomerSnapshot
    simulation: SimulationResult
    research: ResearchResult
