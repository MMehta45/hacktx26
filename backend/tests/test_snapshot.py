from datetime import date

from fastapi.testclient import TestClient

from app.config import Settings
from app.fixtures import fixture_snapshot, summarize_categories
from app.main import app
from app.models import Transaction
from app.nessie import normalize_snapshot
from app.seed import missing_descriptions
from app.snapshot import get_snapshot


def test_fixture_category_totals_and_wage_math_reconcile() -> None:
    snapshot = fixture_snapshot(
        anchor=date(2026, 10, 24),
        display_name="Maya",
        hourly_rate_cents=2_175,
        repair_quote_cents=55_000,
        message="fixture",
    )

    debit_total = sum(
        transaction.amount_cents
        for transaction in snapshot.history.transactions
        if transaction.direction == "debit"
    )
    credit_total = sum(
        transaction.amount_cents
        for transaction in snapshot.history.transactions
        if transaction.direction == "credit"
    )
    assert sum(category.total_cents for category in snapshot.history.categories) == debit_total
    assert snapshot.history.spending_total_cents == debit_total
    assert credit_total == debit_total
    assert len(snapshot.history.transactions) == 89
    assert sum(item.source == "fixture_purchase" for item in snapshot.history.transactions) == 72
    assert sum(item.source == "fixture_deposit" for item in snapshot.history.transactions) == 13
    assert sum(item.source == "fixture_withdrawal" for item in snapshot.history.transactions) == 4
    assert len(snapshot.upcoming_bills) == 5
    assert snapshot.income_projection.gross_per_shift_cents == 17_400
    assert snapshot.income_projection.gross_weekly_cents == 87_000
    assert snapshot.income_projection.estimated_net_per_shift_cents == 13_920
    assert snapshot.income_projection.estimated_net_weekly_cents == 69_600
    assert snapshot.scenario.repair_quote_cents == 55_000
    assert len(snapshot.income_projection.forecast_entries) == 4
    assert snapshot.cash_flow.starting_balance_cents == 31_000
    assert snapshot.cash_flow.minimum_balance_cents == -18_900
    assert snapshot.cash_flow.peak_cash_shortfall_cents == 18_900
    assert snapshot.cash_flow.ending_balance_cents == 188_400
    assert len(snapshot.cash_flow.events) == 9


def test_category_summary_excludes_historical_deposits() -> None:
    transactions = [
        Transaction(
            id="purchase",
            date=date(2026, 10, 1),
            amount_cents=3_000,
            direction="debit",
            merchant_display="H-E-B",
            category="Groceries",
            source="fixture_purchase",
            account_id="account",
        ),
        Transaction(
            id="deposit",
            date=date(2026, 10, 2),
            amount_cents=80_000,
            direction="credit",
            merchant_display="Payroll",
            category="Other",
            source="fixture_deposit",
            account_id="account",
        ),
    ]

    summaries = summarize_categories(transactions)

    assert len(summaries) == 1
    assert summaries[0].category == "Groceries"
    assert summaries[0].total_cents == 3_000
    assert summaries[0].monthly_average_cents == 1_000


def test_nessie_normalization_uses_documented_shapes() -> None:
    snapshot = normalize_snapshot(
        anchor=date(2026, 10, 24),
        display_name="Alex",
        hourly_rate_cents=2_000,
        repair_quote_cents=40_000,
        customer={"_id": "customer-id", "first_name": "Maya", "last_name": "Torres"},
        accounts_raw=[
            {
                "_id": "account-id",
                "type": "Checking",
                "nickname": "OBT Demo Checking",
                "balance": 310,
            }
        ],
        purchases_by_account={
            "account-id": [
                {
                    "_id": "purchase-id",
                    "merchant_id": "merchant-id",
                    "purchase_date": "2026-10-01",
                    "amount": 42,
                    "description": "Fuel",
                }
            ]
        },
        deposits_by_account={
            "account-id": [
                {
                    "_id": "deposit-id",
                    "transaction_date": "2026-10-04",
                    "amount": 640,
                    "description": "Historical payroll",
                }
            ]
        },
        withdrawals_by_account={
            "account-id": [
                {
                    "_id": "withdrawal-id",
                    "transaction_date": "2026-10-06",
                    "amount": 25,
                    "description": "ATM cash",
                }
            ]
        },
        bills_by_account={"account-id": []},
        merchants={"merchant-id": {"_id": "merchant-id", "name": "Shell", "category": "Gas"}},
    )

    assert snapshot.accounts[0].balance_cents == 31_000
    assert snapshot.history.transactions[0].amount_cents == 2_500
    purchase = next(
        item for item in snapshot.history.transactions if item.source == "nessie_purchase"
    )
    assert purchase.amount_cents == 4_200
    assert purchase.category == "Transportation/Gas"
    withdrawal = next(
        item for item in snapshot.history.transactions if item.source == "nessie_withdrawal"
    )
    assert withdrawal.amount_cents == 2_500
    assert snapshot.source.banking == "nessie"


def test_seed_planning_is_idempotent_by_description() -> None:
    desired = [
        {"description": "OBT-M1-one", "amount": 10},
        {"description": "OBT-M1-two", "amount": 20},
    ]
    existing = [{"description": "OBT-M1-one", "amount": 10}]

    assert missing_descriptions(existing, desired) == [desired[1]]
    assert missing_descriptions(desired, desired) == []


def test_snapshot_service_uses_explicit_fixture_mode() -> None:
    snapshot = get_snapshot(
        settings=Settings(demo_data_mode="fixture", demo_anchor_date=date(2026, 10, 24)),
        display_name="Jordan",
        hourly_rate_cents=2_500,
        repair_quote_cents=70_000,
    )

    assert snapshot.customer.display_name == "Jordan"
    assert snapshot.source.mode == "fixture"
    assert snapshot.income_projection.gross_weekly_cents == 100_000
    assert snapshot.income_projection.estimated_net_weekly_cents == 80_000
    assert snapshot.cash_flow.end_date == date(2026, 11, 23)


def test_snapshot_api_validates_and_returns_contract() -> None:
    response = TestClient(app).get(
        "/api/customer/snapshot",
        params={
            "display_name": "Taylor",
            "hourly_rate_cents": 2_000,
            "repair_quote_cents": 40_000,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == 1
    assert payload["customer"]["display_name"] == "Taylor"
    assert payload["income_projection"]["gross_weekly_cents"] == 80_000
    assert payload["income_projection"]["estimated_net_weekly_cents"] == 64_000
    assert len(payload["cash_flow"]["daily_balances"]) == 31
    assert payload["source"]["mode"] == "fixture"
