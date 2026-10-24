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
        "nessie_purchase", "nessie_deposit", "fixture_purchase", "fixture_deposit"
    ]
    account_id: str
    description: str | None = None


class CategorySummary(ApiModel):
    category: CategoryName
    total_cents: int = Field(ge=0)
    monthly_average_cents: int = Field(ge=0)
    transaction_count: int = Field(ge=0)


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


class IncomeProjection(ApiModel):
    hourly_rate_cents: int = Field(gt=0)
    shift_hours: int = 8
    shifts_per_week: int = 5
    gross_per_shift_cents: int
    gross_weekly_cents: int
    pay_frequency: Literal["weekly"] = "weekly"
    next_pay_dates: list[date]
    provenance: Literal["user_wage_forecast"] = "user_wage_forecast"


class Scenario(ApiModel):
    repair_quote_cents: int = Field(ge=10_000, le=150_000)


class SourceMetadata(ApiModel):
    banking: Literal["nessie", "fixture"]
    simulation_data: Literal["seeded_synthetic", "local_fixture"]
    mode: Literal["live", "fixture"]
    message: str


class CustomerSnapshot(ApiModel):
    schema_version: Literal[1] = 1
    customer: Customer
    accounts: list[Account]
    history: History
    upcoming_bills: list[UpcomingBill]
    income_projection: IncomeProjection
    scenario: Scenario
    source: SourceMetadata
