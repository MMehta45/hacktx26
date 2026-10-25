from datetime import date, time

from fastapi.testclient import TestClient

from app.fixtures import fixture_snapshot
from app.main import app
from app.models import Account, SourceMetadata, UpcomingBill
from app.simulation import payday_for_shift, simulate
from app.simulation_models import CrisisSimulationRequest

ANCHOR = date(2026, 10, 24)
BREAKDOWN = date(2026, 10, 26)
FIRST_PAYDAY = date(2026, 10, 30)


def example_snapshot(
    *, balance_cents: int = 31_000, bills: list[UpcomingBill] | None = None, **_: object
):
    snapshot = fixture_snapshot(
        anchor=ANCHOR,
        display_name="Maya Rodriguez",
        hourly_rate_cents=2_000,
        repair_quote_cents=40_000,
        message="test fixture",
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
        "breakdown_date": BREAKDOWN,
        "forecast_horizon_days": 7,
    }
    values.update(updates)
    return CrisisSimulationRequest(**values)


def test_weekly_friday_payroll_has_one_week_lag() -> None:
    result = simulate(example_snapshot(), default_request())

    first = result.payroll_records[0]
    assert (first.work_period_start, first.work_period_end, first.payday) == (
        date(2026, 10, 19),
        date(2026, 10, 25),
        FIRST_PAYDAY,
    )
    assert payday_for_shift(date(2026, 10, 26)) == date(2026, 11, 6)


def test_previous_week_paycheck_is_unchanged_by_breakdown() -> None:
    result = simulate(example_snapshot(), default_request())

    payroll = result.payroll_records[0]
    assert payroll.reliability == "already_earned"
    assert payroll.actual_projected_take_home_cents == 64_000
    assert payroll.lost_take_home_cents == 0


def test_weekday_shifts_are_generated_and_linked_to_payday() -> None:
    result = simulate(example_snapshot(), default_request())

    assert [shift.date for shift in result.shift_records] == [
        date(2026, 10, 26),
        date(2026, 10, 27),
        date(2026, 10, 28),
        date(2026, 10, 29),
        date(2026, 10, 30),
    ]
    assert all(shift.associated_payday == date(2026, 11, 6) for shift in result.shift_records)
    assert all(shift.scheduled_start_local.time() == time(8) for shift in result.shift_records)


def test_breakdown_before_vs_after_shift_start() -> None:
    snapshot = example_snapshot(balance_cents=50_000)
    before = simulate(snapshot, default_request(repair_quote_cents=10_000))
    after = simulate(
        snapshot,
        default_request(repair_quote_cents=10_000, breakdown_time_local=time(9)),
    )

    assert before.shift_records[0].attendance == "projected_missed"
    assert after.shift_records[0].attendance == "worked"
    assert before.repair_projection.modeled_payment_date == BREAKDOWN
    assert after.repair_projection.modeled_payment_date == BREAKDOWN


def test_repair_affordable_immediately_is_charged_once() -> None:
    result = simulate(
        example_snapshot(balance_cents=50_000),
        default_request(repair_quote_cents=40_000),
    )

    assert result.repair_projection.funding_status == "affordable_and_paid"
    assert result.repair_projection.cash_balance_after_payment_cents == 10_000
    assert [event.type for event in result.events].count("repair_payment") == 1


def test_repair_becomes_affordable_after_already_earned_payroll() -> None:
    result = simulate(
        example_snapshot(balance_cents=0),
        default_request(repair_quote_cents=40_000),
    )

    assert result.repair_projection.modeled_payment_date == FIRST_PAYDAY
    assert sum(shift.attendance == "projected_missed" for shift in result.shift_records) == 5


def test_essential_bill_delays_repair() -> None:
    snapshot = example_snapshot(
        balance_cents=31_000,
        bills=[bill("electricity", 25_000, date(2026, 10, 27))],
    )
    result = simulate(snapshot, default_request(repair_quote_cents=10_000))

    assert result.repair_projection.modeled_payment_date == FIRST_PAYDAY
    assert result.bill_outcomes[0].projected_status == "funded"


def test_missed_shifts_reduce_only_the_corresponding_future_paycheck() -> None:
    result = simulate(
        example_snapshot(balance_cents=0),
        default_request(forecast_horizon_days=14, repair_quote_cents=150_000),
    )
    impacted = next(item for item in result.payroll_records if item.payday == date(2026, 11, 6))

    assert impacted.missed_shift_count == 5
    assert impacted.actual_projected_take_home_cents == 0
    assert impacted.lost_take_home_cents == 64_000
    assert result.payroll_records[0].actual_projected_take_home_cents == 64_000


def test_reduced_payroll_does_not_magically_fund_repair() -> None:
    result = simulate(
        example_snapshot(balance_cents=0),
        default_request(repair_quote_cents=70_000, forecast_horizon_days=14),
    )

    assert result.repair_projection.modeled_payment_date is None
    assert next(item for item in result.payroll_records if item.payday == date(2026, 11, 6)).actual_projected_take_home_cents == 0


def test_repair_can_remain_unaffordable_and_creates_no_charge() -> None:
    result = simulate(
        example_snapshot(balance_cents=0),
        default_request(repair_quote_cents=150_000),
    )

    assert result.repair_projection.funding_status == "unaffordable_within_horizon"
    assert result.repair_projection.vehicle_restoration_date is None
    assert not any(event.type == "repair_payment" for event in result.events)


def test_lost_wages_are_not_double_counted() -> None:
    result = simulate(
        example_snapshot(balance_cents=0),
        default_request(forecast_horizon_days=14, repair_quote_cents=150_000),
    )
    normal_minus_crisis_before_bills_and_repair = (
        result.normal_ending_balance_cents - result.crisis_ending_balance_cents
    )

    assert normal_minus_crisis_before_bills_and_repair == sum(
        item.take_home_lost_cents for item in result.income_lost_by_payday
    )


def test_bill_before_payday_cannot_use_future_income() -> None:
    result = simulate(
        example_snapshot(bills=[bill("electricity", 40_000, date(2026, 10, 25))]),
        default_request(),
    )

    assert result.bill_outcomes[0].funded_cents == 31_000
    assert result.bill_outcomes[0].unpaid_cents == 9_000


def test_bill_protective_policy_reserves_near_term_essential_cash() -> None:
    result = simulate(
        example_snapshot(
            balance_cents=50_000,
            bills=[bill("electricity", 20_000, date(2026, 10, 27))],
        ),
        default_request(repair_quote_cents=40_000),
    )

    assert result.repair_projection.modeled_payment_date == FIRST_PAYDAY
    assert result.repair_projection.protected_essential_obligations == []
    assert result.bill_outcomes[0].funded_cents == 20_000


def test_same_day_bill_priority_is_stable() -> None:
    due = date(2026, 10, 25)
    result = simulate(
        example_snapshot(
            bills=[
                bill("b-essential", 20_000, due),
                bill("a-essential", 20_000, due),
                bill("c-discretionary", 10_000, due, essential=False),
            ]
        ),
        default_request(forecast_horizon_days=1, breakdown_date=date(2026, 10, 25)),
    )

    assert [item.obligation_id for item in result.bill_outcomes] == [
        "a-essential",
        "b-essential",
        "c-discretionary",
    ]
    assert [item.funded_cents for item in result.bill_outcomes] == [20_000, 11_000, 0]


def test_graph_statuses_and_dates_follow_computed_timeline() -> None:
    result = simulate(example_snapshot(balance_cents=0), default_request())
    nodes = {node.id: node for node in result.graph_nodes}

    assert nodes["missed_work"].activation_date == BREAKDOWN
    assert nodes["reduced_paycheck"].status == "inactive"  # impacted payday is outside 7 days
    assert nodes["repair_delayed"].status == "projected"
    assert nodes["cash_reserves_depleted"].status == "projected"


def test_fixture_and_live_sources_use_the_same_timeline_rules() -> None:
    fixture = example_snapshot()
    live = fixture.model_copy(
        update={
            "source": SourceMetadata(
                banking="nessie",
                simulation_data="seeded_synthetic",
                mode="live",
                message="test live normalization",
            )
        }
    )

    fixture_result = simulate(fixture, default_request())
    live_result = simulate(live, default_request())
    assert fixture_result.shift_records == live_result.shift_records
    assert fixture_result.payroll_records == live_result.payroll_records
    assert fixture_result.repair_projection == live_result.repair_projection


def test_simulation_is_deterministic_and_never_changes_history() -> None:
    snapshot = example_snapshot()
    transaction_ids = [item.id for item in snapshot.history.transactions]

    assert simulate(snapshot, default_request()) == simulate(snapshot, default_request())
    assert [item.id for item in snapshot.history.transactions] == transaction_ids


def test_api_schema_v2_and_stale_manual_outcomes_are_rejected() -> None:
    response = TestClient(app).post(
        "/api/simulations/crisis",
        json={
            "display_name": "Maya Rodriguez",
            "hourly_rate_cents": 2_000,
            "repair_quote_cents": 40_000,
            "breakdown_date": "2026-10-26",
        },
    )
    stale = TestClient(app).post(
        "/api/simulations/crisis",
        json={"affected_shift_count": 2, "repair_delay_days": 14},
    )

    assert response.status_code == 200
    payload = response.json()["simulation"]
    assert payload["schema_version"] == 2
    assert payload["shift_records"] and payload["payroll_records"]
    assert stale.status_code == 422
