from datetime import date, datetime
from typing import Literal

from pydantic import Field, model_validator

from app.models import ApiModel, CustomerSnapshot


class CrisisSimulationRequest(ApiModel):
    display_name: str = Field(default="Maya Rodriguez", min_length=1, max_length=80)
    hourly_rate_cents: int = Field(default=2_000, gt=0, le=50_000)
    repair_quote_cents: int = Field(default=40_000, ge=10_000, le=150_000)
    scenario_start_date: date | None = None
    affected_shift_count: int = Field(default=2, ge=0, le=5)
    affected_shift_dates: list[date] | None = Field(default=None, max_length=5)
    hours_per_shift: int = Field(default=8, ge=1, le=16)
    weekly_hours: int = Field(default=40, ge=1, le=80)
    take_home_multiplier_basis_points: int = Field(default=8_000, ge=1, le=10_000)
    repair_payment_status: Literal["unpaid", "deferred", "paid"] = "unpaid"
    repair_payment_date: date | None = None
    repair_delay_days: int = Field(default=14, ge=0, le=90)
    transport_cost_cents: int = Field(default=0, ge=0, le=100_000)
    transport_cost_date: date | None = None
    borrowed_amount_cents: int = Field(default=0, ge=0, le=1_000_000)
    borrowing_date: date | None = None
    debt_payment_cents: int = Field(default=0, ge=0, le=1_000_000)
    debt_payment_date: date | None = None
    forecast_horizon_days: int = Field(default=30, ge=1, le=30)

    @model_validator(mode="after")
    def validate_scenario(self) -> "CrisisSimulationRequest":
        if self.affected_shift_dates is not None:
            if len(set(self.affected_shift_dates)) != len(self.affected_shift_dates):
                raise ValueError("Affected shift dates must be unique.")
            if len(self.affected_shift_dates) != self.affected_shift_count:
                raise ValueError("Affected shift count must match the explicit shift dates.")
        if self.repair_payment_status == "paid" and self.repair_payment_date is None:
            raise ValueError("A paid repair requires repair_payment_date.")
        if self.repair_payment_status != "paid" and self.repair_payment_date is not None:
            raise ValueError("An unpaid or deferred repair cannot have a payment date.")
        if self.debt_payment_cents > 0 and self.borrowed_amount_cents == 0:
            raise ValueError("A debt payment requires a modeled borrowed amount.")
        return self


class SimulationScenario(ApiModel):
    scenario_start_date: date
    forecast_end_date: date
    timezone: Literal["America/Chicago"] = "America/Chicago"
    repair_quote_cents: int
    repair_payment_status: Literal["unpaid", "deferred", "paid"]
    repair_delay_days: int
    affected_shift_dates: list[date]
    hours_per_shift: int
    weekly_hours: int
    take_home_multiplier_basis_points: int
    transport_cost_cents: int
    borrowed_amount_cents: int
    debt_payment_cents: int
    actions: list[str] = Field(default_factory=list)


class FinancialEvent(ApiModel):
    id: str
    date: date
    type: Literal[
        "paycheck",
        "bill_due",
        "lost_wages",
        "repair_payment",
        "transport_cost",
        "borrowing",
        "debt_payment",
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
    schema_version: Literal[1] = 1
    source: SimulationSource
    scenario: SimulationScenario
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


class CrisisSimulationResponse(ApiModel):
    snapshot: CustomerSnapshot
    simulation: SimulationResult
