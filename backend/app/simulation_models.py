from datetime import date, datetime, time
from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.models import ApiModel, CustomerSnapshot


class CrisisSimulationRequest(ApiModel):
    display_name: str = Field(default="Maya Rodriguez", min_length=1, max_length=80)
    hourly_rate_cents: int = Field(default=2_000, gt=0, le=50_000)
    repair_quote_cents: int = Field(default=40_000, ge=10_000, le=150_000)
    breakdown_date: date | None = None
    breakdown_time_local: time = time(7, 0)
    forecast_horizon_days: int = Field(default=30, ge=1, le=30)


EffectCertainty = Literal[
    "confirmed", "user_reported", "conditional", "provider_observed"
]


class EffectBase(ApiModel):
    effect_id: str
    action_id: str
    requirement_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    certainty: EffectCertainty = "conditional"


class PreserveShiftEffect(EffectBase):
    effect_type: Literal["preserve_shift"] = "preserve_shift"
    shift_ids: list[str] = Field(min_length=1)


class ExpenseEffect(EffectBase):
    effect_type: Literal["expense"] = "expense"
    ledger_id: str
    amount_cents: int = Field(gt=0)
    date: date
    description: str
    supported_shift_ids: list[str] = Field(default_factory=list)
    # Transportation is only paid when this action actually supplies the commute.
    # This avoids charging a fare when another selected action (for example remote
    # work) preserves the same shift.
    charge_only_when_needed_for_supported_shift: bool = False


class BillDueDateEffect(EffectBase):
    effect_type: Literal["change_bill_due_date"] = "change_bill_due_date"
    obligation_id: str
    original_due_date: date
    new_due_date: date
    fee_cents: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def due_date_moves_forward(self) -> "BillDueDateEffect":
        if self.new_due_date <= self.original_due_date:
            raise ValueError("A bill extension must move the due date forward.")
        return self


class BillReductionEffect(EffectBase):
    effect_type: Literal["reduce_bill"] = "reduce_bill"
    obligation_id: str
    reduction_cents: int = Field(gt=0)
    effective_date: date


class AssistanceEffect(EffectBase):
    effect_type: Literal["assistance"] = "assistance"
    ledger_id: str
    amount_cents: int = Field(gt=0)
    arrival_date: date
    restricted_to_obligation_id: str | None = None


class AlternativeRepairQuoteEffect(EffectBase):
    effect_type: Literal["alternative_repair_quote"] = "alternative_repair_quote"
    quote_cents: int = Field(ge=1_000, le=150_000)
    earliest_appointment_date: date


class Repayment(ApiModel):
    ledger_id: str
    date: date
    amount_cents: int = Field(gt=0)


class BorrowFundsEffect(EffectBase):
    effect_type: Literal["borrow_funds"] = "borrow_funds"
    ledger_id: str
    principal_cents: int = Field(gt=0)
    availability_date: date
    repayments: list[Repayment] = Field(min_length=1)

    @model_validator(mode="after")
    def repayments_follow_funding(self) -> "BorrowFundsEffect":
        if any(item.date <= self.availability_date for item in self.repayments):
            raise ValueError("Borrowing repayments must occur after funds become available.")
        return self


class MakeupHoursEffect(EffectBase):
    effect_type: Literal["makeup_hours"] = "makeup_hours"
    original_shift_id: str
    makeup_work_date: date
    hours: int = Field(gt=0, le=8)
    payroll_date: date

    @model_validator(mode="after")
    def payroll_follows_work(self) -> "MakeupHoursEffect":
        if self.payroll_date <= self.makeup_work_date or self.payroll_date.weekday() != 4:
            raise ValueError("Makeup hours must be paid on a later Friday payroll.")
        return self


RecoveryEffect = Annotated[
    PreserveShiftEffect
    | ExpenseEffect
    | BillDueDateEffect
    | BillReductionEffect
    | AssistanceEffect
    | AlternativeRepairQuoteEffect
    | BorrowFundsEffect
    | MakeupHoursEffect,
    Field(discriminator="effect_type"),
]


class SimulationScenario(ApiModel):
    scenario_start_date: date
    forecast_end_date: date
    breakdown_at_local: datetime
    timezone: Literal["America/Chicago"] = "America/Chicago"
    repair_quote_cents: int
    hourly_rate_cents: int
    workdays: list[Literal["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]]
    shift_start_local: time = time(8, 0)
    shift_end_local: time = time(16, 0)
    hours_per_shift: Literal[8] = 8
    weekly_hours: Literal[40] = 40
    take_home_multiplier_basis_points: Literal[8_000] = 8_000
    payroll_frequency: Literal["weekly"] = "weekly"
    payroll_weekday: Literal["Friday"] = "Friday"
    payroll_lag_weeks: Literal[1] = 1
    actions: list[str] = Field(default_factory=list)


class ShiftRecord(ApiModel):
    id: str
    date: date
    scheduled_start_local: datetime
    scheduled_end_local: datetime
    hours: Literal[8] = 8
    gross_earning_potential_cents: int = Field(ge=0)
    take_home_earning_potential_cents: int = Field(ge=0)
    associated_payday: date
    vehicle_usable_at_shift_start: bool
    attendance: Literal["worked", "projected_missed", "unresolved"]
    reason: str


class PayrollRecord(ApiModel):
    id: str
    work_period_start: date
    work_period_end: date
    payday: date
    normal_gross_cents: int = Field(ge=0)
    normal_take_home_cents: int = Field(ge=0)
    actual_projected_take_home_cents: int = Field(ge=0)
    scheduled_shift_count: int = Field(ge=0)
    worked_shift_count: int = Field(ge=0)
    missed_shift_count: int = Field(ge=0)
    lost_take_home_cents: int = Field(ge=0)
    reliability: Literal["already_earned", "attendance_derived"]


class ProtectedObligation(ApiModel):
    obligation_id: str
    name: str
    amount_cents: int = Field(ge=0)
    due_date: date


class RepairProjection(ApiModel):
    quote_cents: int = Field(ge=0)
    earliest_financially_feasible_payment_date: date | None
    modeled_payment_date: date | None
    vehicle_restoration_date: date | None
    days_unavailable_within_forecast: int = Field(ge=0)
    funding_status: Literal["affordable_and_paid", "unaffordable_within_horizon", "unresolved"]
    blocked_reason: str | None
    cash_balance_after_payment_cents: int | None = Field(default=None, ge=0)
    protected_essential_obligations: list[ProtectedObligation]
    policy: str


class FinancialEvent(ApiModel):
    id: str
    date: date
    type: Literal[
        "paycheck",
        "bill_due",
        "lost_wages",
        "repair_payment",
        "action_expense",
        "assistance",
        "borrowing",
        "debt_payment",
        "bill_fee",
        "makeup_wages",
    ]
    signed_amount_cents: int
    description: str
    source: str
    status: Literal["projected", "scenario_assumption"]
    provenance_id: str | None = None
    essential: bool | None = None


class IncomeLoss(ApiModel):
    payday: date
    affected_shift_dates: list[date]
    gross_lost_cents: int = Field(ge=0)
    take_home_lost_cents: int = Field(ge=0)
    normal_take_home_cents: int = Field(ge=0)
    crisis_take_home_cents: int = Field(ge=0)


class SimulationCashflowPoint(ApiModel):
    date: date
    normal_balance_cents: int
    crisis_balance_cents: int
    constrained_available_cents: int = Field(ge=0)
    raw_shortfall: bool


class BillOutcome(ApiModel):
    obligation_id: str
    name: str
    amount_cents: int = Field(ge=0)
    due_date: date
    funded_cents: int = Field(ge=0)
    unpaid_cents: int = Field(ge=0)
    essential: bool
    category: str
    projected_status: Literal["funded", "partially_unpaid", "unpaid"]
    payment_priority: int = Field(ge=1)
    source: str


class ProblemNode(ApiModel):
    id: str
    label: str
    description: str
    status: Literal["projected", "conditional", "inactive", "unresolved"]
    activation_date: date | None = None
    evidence: str
    amount_cents: int | None = None
    source: Literal["nessie", "fixture", "scenario_assumption", "projection"]


class ProblemEdge(ApiModel):
    id: str
    source: str
    target: str
    condition: str | None = None


class SimulationSource(ApiModel):
    customer_id: str
    account_ids: list[str]
    current_balance_cents: int
    banking_mode: Literal["live", "fixture"]
    source_as_of_date: date
    source_retrieved_at: datetime
    timezone: Literal["America/Chicago"] = "America/Chicago"


class SimulationResult(ApiModel):
    schema_version: Literal[2] = 2
    source: SimulationSource
    scenario: SimulationScenario
    shift_records: list[ShiftRecord]
    payroll_records: list[PayrollRecord]
    repair_projection: RepairProjection
    applied_action_ids: list[str] = Field(default_factory=list)
    events: list[FinancialEvent]
    cashflow: list[SimulationCashflowPoint]
    income_lost_by_payday: list[IncomeLoss]
    bill_outcomes: list[BillOutcome]
    unpaid_bills: list[BillOutcome]
    normal_ending_balance_cents: int
    crisis_ending_balance_cents: int
    constrained_ending_cash_cents: int = Field(ge=0)
    peak_funding_gap_cents: int = Field(ge=0)
    unpaid_essential_total_cents: int = Field(ge=0)
    graph_nodes: list[ProblemNode]
    graph_edges: list[ProblemEdge]
    warnings: list[str]

    @model_validator(mode="after")
    def validate_timeline(self) -> "SimulationResult":
        if sum(event.type == "repair_payment" for event in self.events) > 1:
            raise ValueError("A crisis timeline may contain at most one repair payment.")
        return self


class CrisisSimulationResponse(ApiModel):
    snapshot: CustomerSnapshot
    simulation: SimulationResult
