from datetime import date

from fastapi.testclient import TestClient

from app.fixtures import fixture_snapshot
from app.main import app
from app.models import Account, ForecastIncome, IncomeProjection, UpcomingBill
from app.simulation import simulate
from app.simulation_models import CrisisSimulationRequest

ANCHOR = date(2026, 10, 24)
PAYDAY = date(2026, 10, 30)


def example_snapshot(
    *,
    balance_cents: int = 31_000,
    bills: list[UpcomingBill] | None = None,
    include_paycheck: bool = True,
):
    snapshot = fixture_snapshot(
        anchor=ANCHOR,
        display_name="Maya Rodriguez",
        hourly_rate_cents=2_000,
        repair_quote_cents=40_000,
        message="test fixture",
    )
    entries = (
        [
            ForecastIncome(
                expected_payment_date=PAYDAY,
                gross_amount_cents=80_000,
                estimated_take_home_cents=64_000,
                work_period_start=date(2026, 10, 23),
                work_period_end=date(2026, 10, 29),
            )
        ]
        if include_paycheck
        else []
    )
    income = IncomeProjection(
        hourly_rate_cents=2_000,
        gross_per_shift_cents=16_000,
        gross_weekly_cents=80_000,
        estimated_net_per_shift_cents=12_800,
        estimated_net_weekly_cents=64_000,
        next_pay_dates=[entry.expected_payment_date for entry in entries],
        forecast_entries=entries,
    )
    return snapshot.model_copy(
        update={
            "accounts": [
                Account(
                    id="account",
                    type="Checking",
                    nickname="Demo checking",
                    balance_cents=balance_cents,
                    source="fixture",
                )
            ],
            "upcoming_bills": bills or [],
            "income_projection": income,
        }
    )


def bill(
    bill_id: str,
    amount_cents: int,
    due_date: date,
    *,
    essential: bool = True,
) -> UpcomingBill:
    return UpcomingBill(
        id=bill_id,
        name=bill_id.title(),
        amount_cents=amount_cents,
        due_date=due_date,
        source="synthetic_schedule",
        status="scheduled",
        category="Housing/Rent" if essential else "Subscriptions",
        essential=essential,
        provenance="test",
    )


def default_request(**updates: object) -> CrisisSimulationRequest:
    values: dict[str, object] = {
        "scenario_start_date": ANCHOR,
        "forecast_horizon_days": 7,
    }
    values.update(updates)
    return CrisisSimulationRequest(**values)


def test_required_numeric_example_and_correct_payday() -> None:
    snapshot = example_snapshot(bills=[bill("rent", 90_000, date(2026, 10, 31))])

    result = simulate(snapshot, default_request())

    assert result.source.current_balance_cents == 31_000
    assert result.normal_ending_balance_cents == 5_000
    assert result.crisis_ending_balance_cents == -20_600
    assert result.peak_funding_gap_cents == 20_600
    assert result.unpaid_essential_total_cents == 20_600
    assert result.constrained_ending_cash_cents == 0
    assert result.income_lost_by_payday[0].payday == PAYDAY
    assert result.income_lost_by_payday[0].take_home_lost_cents == 25_600
    assert result.income_lost_by_payday[0].crisis_take_home_cents == 38_400
    assert next(item for item in result.events if item.type == "lost_wages").date == PAYDAY


def test_unpaid_quote_and_zero_cost_branches_do_not_debit_cash() -> None:
    snapshot = example_snapshot()

    result = simulate(snapshot, default_request(repair_quote_cents=40_000))

    assert not any(item.type == "repair_payment" for item in result.events)
    assert not any(item.type == "transport_cost" for item in result.events)
    assert not any(item.type == "borrowing" for item in result.events)
    nodes = {item.id: item for item in result.graph_nodes}
    assert nodes["unexpected_repair_expense"].amount_cents == 40_000
    assert nodes["cash_reserves_depleted"].status == "inactive"
    assert nodes["extra_transportation_costs"].status == "inactive"
    assert nodes["emergency_borrowing"].status == "conditional"
    assert result.source.current_balance_cents == 31_000


def test_bill_before_payday_cannot_use_future_income() -> None:
    snapshot = example_snapshot(bills=[bill("electricity", 40_000, date(2026, 10, 25))])

    result = simulate(snapshot, default_request(affected_shift_count=0))

    outcome = result.bill_outcomes[0]
    assert outcome.funded_cents == 31_000
    assert outcome.unpaid_cents == 9_000
    assert result.constrained_ending_cash_cents == 64_000


def test_same_day_bills_allocate_essential_first_then_id() -> None:
    due = date(2026, 10, 25)
    snapshot = example_snapshot(
        include_paycheck=False,
        bills=[
            bill("b-essential", 20_000, due),
            bill("a-essential", 20_000, due),
            bill("c-discretionary", 10_000, due, essential=False),
        ],
    )

    result = simulate(
        snapshot,
        default_request(affected_shift_count=0, forecast_horizon_days=1),
    )

    assert [item.obligation_id for item in result.bill_outcomes] == [
        "a-essential",
        "b-essential",
        "c-discretionary",
    ]
    assert [item.funded_cents for item in result.bill_outcomes] == [20_000, 11_000, 0]
    assert result.unpaid_essential_total_cents == 9_000
    assert result.peak_funding_gap_cents == 19_000


def test_simulation_is_deterministic_and_never_changes_history() -> None:
    snapshot = example_snapshot(bills=[bill("rent", 90_000, date(2026, 10, 31))])
    transaction_ids = [item.id for item in snapshot.history.transactions]
    request = default_request()

    first = simulate(snapshot, request)
    second = simulate(snapshot, request)

    assert first == second
    assert [item.id for item in snapshot.history.transactions] == transaction_ids
    assert len(snapshot.history.transactions) == 89


def test_repair_slider_changes_exposure_not_balance_or_ledger() -> None:
    snapshot = example_snapshot()

    low = simulate(snapshot, default_request(repair_quote_cents=10_000))
    high = simulate(snapshot, default_request(repair_quote_cents=150_000))

    low_repair = next(item for item in low.graph_nodes if item.id == "unexpected_repair_expense")
    high_repair = next(item for item in high.graph_nodes if item.id == "unexpected_repair_expense")
    assert low_repair.amount_cents == 10_000
    assert high_repair.amount_cents == 150_000
    assert low.crisis_ending_balance_cents == high.crisis_ending_balance_cents
    assert low.source.current_balance_cents == high.source.current_balance_cents == 31_000
    assert [item.id for item in low.events] == [item.id for item in high.events]


def test_graph_contract_is_stable_and_problem_only() -> None:
    result = simulate(example_snapshot(), default_request())

    assert [item.id for item in result.graph_nodes] == [
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
    assert len(result.graph_edges) == 17
    assert all(
        item.status in {"projected", "conditional", "inactive", "unresolved"}
        for item in result.graph_nodes
    )


def test_crisis_api_returns_snapshot_and_both_line_series() -> None:
    response = TestClient(app).post(
        "/api/simulations/crisis",
        json={
            "display_name": "Maya Rodriguez",
            "hourly_rate_cents": 2_000,
            "repair_quote_cents": 40_000,
            "scenario_start_date": "2026-10-24",
            "affected_shift_count": 2,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["snapshot"]["source"]["mode"] == "fixture"
    assert len(payload["simulation"]["cashflow"]) == 31
    assert "normal_balance_cents" in payload["simulation"]["cashflow"][0]
    assert "crisis_balance_cents" in payload["simulation"]["cashflow"][0]
    assert len(payload["simulation"]["graph_nodes"]) == 14
