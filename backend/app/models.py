from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CategoryName = Literal[
    "Housing/Rent",
    "Groceries",
    "Dining",
    "Transportation/Gas",
    "Utilities",
    "Insurance",
    "Shopping",
    "Subscriptions",
    "Health",
    "Other",
]


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Customer(ApiModel):
    id: str
    display_name: str
    age: int = 29
    occupation: str = "Hourly employee"
    city: str = "Austin, TX"


class Account(ApiModel):
    id: str
    type: str
    nickname: str | None = None
    balance_cents: int
    source: Literal["nessie", "fixture"]


class Transaction(ApiModel):
    id: str
    date: date
    amount_cents: int = Field(ge=0)
    direction: Literal["debit", "credit"]
    merchant_display: str | None
    category: CategoryName
    source: Literal[
        "nessie_purchase",
        "nessie_deposit",
        "nessie_withdrawal",
        "fixture_purchase",
        "fixture_deposit",
        "fixture_withdrawal",
    ]
    account_id: str
    description: str | None = None
    recurring: bool = False


class CategorySummary(ApiModel):
    category: CategoryName
    total_cents: int = Field(ge=0)
    monthly_average_cents: int = Field(ge=0)
    transaction_count: int = Field(ge=0)
    percentage: float = Field(ge=0, le=100)
    recurring_cents: int = Field(ge=0)
    irregular_cents: int = Field(ge=0)
    essential: bool


class History(ApiModel):
    start: date
    end: date
    transactions: list[Transaction]
    categories: list[CategorySummary]
    spending_total_cents: int = Field(ge=0)


class UpcomingBill(ApiModel):
    id: str
    name: str
    amount_cents: int = Field(ge=0)
    due_date: date
    source: Literal["nessie_bill", "synthetic_schedule"]
    status: str
    category: CategoryName
    essential: bool
    nessie_bill_id: str | None = None
    provenance: str


class ForecastIncome(ApiModel):
    expected_payment_date: date
    gross_amount_cents: int = Field(ge=0)
    estimated_take_home_cents: int = Field(ge=0)
    work_period_start: date
    work_period_end: date
    shift_count: int = 5
    status: Literal["projected"] = "projected"
    source: Literal["user_wage_forecast"] = "user_wage_forecast"


class IncomeProjection(ApiModel):
    hourly_rate_cents: int = Field(gt=0)
    shift_hours: int = 8
    shifts_per_week: int = 5
    gross_per_shift_cents: int
    gross_weekly_cents: int
    estimated_net_per_shift_cents: int
    estimated_net_weekly_cents: int
    take_home_multiplier_basis_points: int = 8_000
    pay_frequency: Literal["weekly"] = "weekly"
    next_pay_dates: list[date]
    forecast_entries: list[ForecastIncome]
    provenance: Literal["user_wage_forecast"] = "user_wage_forecast"


class Scenario(ApiModel):
    repair_quote_cents: int = Field(ge=10_000, le=150_000)


class SourceMetadata(ApiModel):
    banking: Literal["nessie", "fixture"]
    simulation_data: Literal["seeded_synthetic", "local_fixture"]
    mode: Literal["live", "fixture"]
    message: str


class CashFlowEvent(ApiModel):
    date: date
    name: str
    amount_cents: int = Field(ge=0)
    direction: Literal["income", "expense"]
    source: Literal["projected_income", "scheduled_bill"]


class CashFlowPoint(ApiModel):
    date: date
    projected_balance_cents: int


class CashFlowForecast(ApiModel):
    start_date: date
    end_date: date
    starting_balance_cents: int
    minimum_balance_cents: int
    ending_balance_cents: int
    peak_cash_shortfall_cents: int = Field(ge=0)
    events: list[CashFlowEvent]
    daily_balances: list[CashFlowPoint]
    assumption: str


class CustomerSnapshot(ApiModel):
    schema_version: Literal[1] = 1
    customer: Customer
    accounts: list[Account]
    history: History
    upcoming_bills: list[UpcomingBill]
    income_projection: IncomeProjection
    cash_flow: CashFlowForecast
    scenario: Scenario
    source: SourceMetadata
