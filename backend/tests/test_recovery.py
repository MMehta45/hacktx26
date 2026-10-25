from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.fixtures import upcoming_bills
from app.main import app
from app.recovery_models import (
    CreateRecoverySessionRequest,
    EvaluateRecoveryRequest,
    RecoveryActionDefinition,
    SubmitAnswerRequest,
)
from app.recovery_service import (
    RecoveryVersionConflict,
    _sessions,
    create_session,
    evaluate_session,
    submit_answer,
    targeted_research,
)
from app.research_models import Evidence, ResearchContext
from app.simulation import simulate
from app.simulation_models import (
    AlternativeRepairQuoteEffect,
    AssistanceEffect,
    BillDueDateEffect,
    BillReductionEffect,
    BorrowFundsEffect,
    ExpenseEffect,
    MakeupHoursEffect,
    PreserveShiftEffect,
    Repayment,
)
from tests.test_simulation import BREAKDOWN, default_request, example_snapshot


def test_preserved_shift_changes_correct_payday_and_can_accelerate_repair() -> None:
    snapshot = example_snapshot(bills=upcoming_bills(date(2026, 10, 24)))
    baseline = simulate(snapshot, default_request(forecast_horizon_days=30))
    first_week = [item.id for item in baseline.shift_records[:5]]
    recovered = simulate(
        snapshot,
        default_request(forecast_horizon_days=30),
        actions=[
            PreserveShiftEffect(
                effect_id="remote-week-one",
                action_id="remote",
                shift_ids=first_week,
            )
        ],
    )

    november_six = next(item for item in recovered.payroll_records if item.payday == date(2026, 11, 6))
    assert november_six.actual_projected_take_home_cents == 64_000
    assert baseline.repair_projection.modeled_payment_date is None
    assert recovered.repair_projection.modeled_payment_date == date(2026, 11, 6)


def test_duplicate_shift_coverage_recovers_wages_once() -> None:
    snapshot = example_snapshot(balance_cents=0)
    shift_id = "shift-2026-10-26"
    result = simulate(
        snapshot,
        default_request(forecast_horizon_days=14, repair_quote_cents=150_000),
        actions=[
            PreserveShiftEffect(effect_id="remote", action_id="remote", shift_ids=[shift_id]),
            PreserveShiftEffect(effect_id="bus", action_id="bus", shift_ids=[shift_id]),
        ],
    )
    payroll = next(item for item in result.payroll_records if item.payday == date(2026, 11, 6))
    assert payroll.actual_projected_take_home_cents == 12_800
    assert payroll.worked_shift_count == 1


def test_expense_and_unrestricted_assistance_are_dated_once() -> None:
    result = simulate(
        example_snapshot(),
        default_request(),
        actions=[
            ExpenseEffect(
                effect_id="fare",
                action_id="bus",
                ledger_id="fare-ledger",
                amount_cents=500,
                date=BREAKDOWN,
                description="Round-trip fare",
            ),
            AssistanceEffect(
                effect_id="grant",
                action_id="grant",
                ledger_id="grant-ledger",
                amount_cents=1_000,
                arrival_date=BREAKDOWN,
            ),
        ],
    )
    assert [item.type for item in result.events].count("action_expense") == 1
    assert [item.type for item in result.events].count("assistance") == 1
    assert result.cashflow[2].crisis_balance_cents == 31_500


def test_bill_extension_preserves_obligation_and_reduction_is_explicit() -> None:
    snapshot = example_snapshot(bills=upcoming_bills(date(2026, 10, 24)))
    streaming = next(item for item in snapshot.upcoming_bills if item.category == "Subscriptions")
    extended = simulate(
        snapshot,
        default_request(forecast_horizon_days=30),
        actions=[
            BillDueDateEffect(
                effect_id="extend",
                action_id="extend",
                obligation_id=streaming.id,
                original_due_date=streaming.due_date,
                new_due_date=streaming.due_date + __import__("datetime").timedelta(days=7),
            )
        ],
    )
    assert next(item for item in extended.bill_outcomes if item.obligation_id == streaming.id).amount_cents == streaming.amount_cents
    assert next(item for item in extended.bill_outcomes if item.obligation_id == streaming.id).due_date == streaming.due_date + __import__("datetime").timedelta(days=7)

    reduced = simulate(
        snapshot,
        default_request(forecast_horizon_days=30),
        actions=[BillReductionEffect(effect_id="waive", action_id="waive", obligation_id=streaming.id, reduction_cents=streaming.amount_cents, effective_date=streaming.due_date)],
    )
    assert next(item for item in reduced.bill_outcomes if item.obligation_id == streaming.id).amount_cents == 0


def test_alternative_quote_replaces_original_and_borrowing_has_repayment() -> None:
    result = simulate(
        example_snapshot(balance_cents=0),
        default_request(forecast_horizon_days=30),
        actions=[
            AlternativeRepairQuoteEffect(
                effect_id="quote",
                action_id="quote",
                quote_cents=20_000,
                earliest_appointment_date=date(2026, 10, 30),
            ),
            BorrowFundsEffect(
                effect_id="loan",
                action_id="loan",
                ledger_id="loan-principal",
                principal_cents=20_000,
                availability_date=date(2026, 10, 30),
                repayments=[Repayment(ledger_id="loan-repay", date=date(2026, 11, 20), amount_cents=22_000)],
            ),
        ],
    )
    assert result.repair_projection.quote_cents == 20_000
    assert sum(item.type == "repair_payment" for item in result.events) <= 1
    assert any(item.type == "borrowing" for item in result.events)
    assert any(item.type == "debt_payment" for item in result.events)


def test_makeup_hours_are_paid_on_explicit_payday() -> None:
    result = simulate(
        example_snapshot(balance_cents=0),
        default_request(forecast_horizon_days=21, repair_quote_cents=150_000),
        actions=[
            MakeupHoursEffect(
                effect_id="makeup",
                action_id="makeup",
                original_shift_id="shift-2026-10-26",
                makeup_work_date=date(2026, 11, 2),
                hours=8,
                payroll_date=date(2026, 11, 13),
            )
        ],
    )
    assert any(item.type == "makeup_wages" and item.date == date(2026, 11, 13) for item in result.events)


def test_invalid_effect_dates_and_unknown_restrictions_are_rejected() -> None:
    with pytest.raises(ValueError, match="later Friday"):
        MakeupHoursEffect(
            effect_id="bad-makeup",
            action_id="bad",
            original_shift_id="shift-2026-10-26",
            makeup_work_date=date(2026, 11, 2),
            hours=8,
            payroll_date=date(2026, 11, 3),
        )
    with pytest.raises(ValueError, match="after funds"):
        BorrowFundsEffect(
            effect_id="bad-loan",
            action_id="bad",
            ledger_id="loan",
            principal_cents=10_000,
            availability_date=date(2026, 11, 6),
            repayments=[Repayment(ledger_id="repay", date=date(2026, 11, 6), amount_cents=11_000)],
        )
    with pytest.raises(ValueError, match="unknown obligation"):
        simulate(
            example_snapshot(),
            default_request(),
            actions=[
                AssistanceEffect(
                    effect_id="bad-grant",
                    action_id="bad",
                    ledger_id="grant",
                    amount_cents=10_000,
                    arrival_date=BREAKDOWN,
                    restricted_to_obligation_id="missing-bill",
                )
            ],
        )


def _session(monkeypatch: pytest.MonkeyPatch):
    from app import recovery_service

    _sessions.clear()
    monkeypatch.setattr(
        recovery_service,
        "get_snapshot",
        lambda **kwargs: example_snapshot(bills=upcoming_bills(date(2026, 10, 24))),
    )
    return create_session(
        CreateRecoverySessionRequest(scenario=default_request(forecast_horizon_days=30)),
        Settings(_env_file=None, demo_data_mode="fixture"),
    )


def test_possible_remote_work_does_not_become_approval(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session(monkeypatch)
    updated = submit_answer(
        session.id,
        SubmitAnswerRequest(
            session_version=session.version,
            question_id="question-remote-possible",
            value=True,
        ),
    )
    requirements = {item.id: item for item in updated.requirements}
    assert requirements["remote_personally_possible"].status == "possible"
    assert requirements["remote_manager_approval"].status == "pending_external_approval"
    assert any(item.kind == "remote_work_request" for item in updated.outreach_drafts)
    assert any(plan.feasibility == "conditional_pending_approval" for plan in updated.evaluation.plans)


def test_confirmed_remote_answers_change_feasibility_and_finances(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session(monkeypatch)
    for question_id in (
        "question-remote-possible",
        "question-remote-equipment",
        "question-remote-approved",
    ):
        session = submit_answer(
            session.id,
            SubmitAnswerRequest(session_version=session.version, question_id=question_id, value=True),
        )
    remote = next(plan for plan in session.evaluation.plans if "action-remote-work" in plan.action_ids)
    assert remote.feasibility == "ready_with_confirmed_conditions"
    assert remote.delta.recovered_shift_ids
    assert remote.delta.income_preserved_cents >= 64_000


def test_session_versions_and_ranking_are_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session(monkeypatch)
    with pytest.raises(RecoveryVersionConflict):
        submit_answer(
            session.id,
            SubmitAnswerRequest(session_version=99, question_id="question-remote-possible", value=True),
        )
    first = evaluate_session(session.id, EvaluateRecoveryRequest(session_version=session.version))
    second = evaluate_session(session.id, EvaluateRecoveryRequest(session_version=session.version))
    assert [item.id for item in first.evaluation.plans] == [item.id for item in second.evaluation.plans]
    assert first.evaluation.evaluated_plan_count <= 92


def test_recovery_api_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import recovery_service

    _sessions.clear()
    monkeypatch.setattr(
        recovery_service,
        "get_snapshot",
        lambda **kwargs: example_snapshot(bills=upcoming_bills(date(2026, 10, 24))),
    )
    response = TestClient(app).post(
        "/api/recovery/sessions",
        json={"scenario": default_request(forecast_horizon_days=30).model_dump(mode="json")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == 1
    assert body["evaluation"]["plans"]
    assert TestClient(app).get("/api/recovery/sessions/stale-session").status_code == 404


def test_explore_result_to_answer_and_recovery_evaluation_flow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import recovery_service

    _sessions.clear()
    monkeypatch.setattr(
        recovery_service,
        "get_snapshot",
        lambda **kwargs: example_snapshot(bills=upcoming_bills(date(2026, 10, 24))),
    )
    client = TestClient(app)
    created = client.post(
        "/api/recovery/sessions",
        json={
            "scenario": default_request(forecast_horizon_days=30).model_dump(mode="json"),
            "research": {
                "status": "completed",
                "run_id": "explore-run",
                "simulation_fingerprint": "explore-fingerprint",
                "research_started_at": "2026-10-25T12:00:00Z",
                "research_finished_at": "2026-10-25T12:00:01Z",
                "priority_targets": [],
                "research_events": [],
                "evidence": [],
                "candidate_actions": [],
                "tool_calls_used": 0,
                "cache_hits": 0,
            },
        },
    )
    assert created.status_code == 200
    session = created.json()
    answered = client.post(
        f"/api/recovery/sessions/{session['id']}/answers",
        json={
            "session_version": session["version"],
            "question_id": "question-remote-possible",
            "value": True,
        },
    )
    assert answered.status_code == 200
    updated = answered.json()
    assert next(
        item for item in updated["requirements"] if item["id"] == "remote_manager_approval"
    )["status"] == "pending_external_approval"
    evaluated = client.post(
        f"/api/recovery/sessions/{session['id']}/evaluate",
        json={"session_version": updated["version"]},
    )
    assert evaluated.status_code == 200
    assert evaluated.json()["evaluation"]["plans"]


def test_recovery_accepts_build03_route_name_and_preserves_transit_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explore's legacy route_name spelling must survive the M4 session boundary."""
    from app import recovery_service

    _sessions.clear()
    monkeypatch.setattr(
        recovery_service,
        "get_snapshot",
        lambda **kwargs: example_snapshot(bills=upcoming_bills(date(2026, 10, 24))),
    )
    client = TestClient(app)
    research = {
        "status": "completed",
        "run_id": "build03-transit",
        "simulation_fingerprint": "fixture-fingerprint",
        "research_started_at": "2026-10-25T12:00:00Z",
        "research_finished_at": "2026-10-25T12:00:01Z",
        "priority_targets": [],
        "research_events": [],
        "candidate_actions": [],
        "tool_calls_used": 2,
        "cache_hits": 0,
        "evidence": [
            {
                "id": "transit-realistic",
                "source_type": "transit_directions",
                "provider_engine": "google_maps_directions",
                "title": "Timed bus itinerary",
                "url": "https://www.google.com/maps/dir/?api=1",
                "query": "home to work",
                "retrieved_at": "2026-10-25T12:00:00Z",
                "facts_supported": ["route and timing"],
                "limitations": ["availability can change"],
                "observed_cost_cents": 125,
                "transit_departure": "2026-10-26T07:10:00-05:00",
                "transit_arrival": "2026-10-26T07:48:00-05:00",
                "transit_request_kind": "arrive_by",
                "transit_request_date": "2026-10-26",
                "route_numbers": ["5", "801"],
                "transfer_count": 1,
                "walking_duration_minutes": 8,
                "transit_duration_minutes": 38,
                "fare_source": "provider observed",
                "fare_certainty": "provider_observed",
                "transit_legs": [
                    {
                        "mode": "walking",
                        "route_name": None,
                        "departure": "2026-10-26T07:00:00-05:00",
                        "arrival": "2026-10-26T07:08:00-05:00",
                        "duration_minutes": 8,
                        "distance_meters": 600,
                        "boarding_stop": "Home",
                        "alighting_stop": "North Lamar",
                    },
                    {
                        "mode": "transit",
                        "route_name": "5 Northcross",
                        "departure": "2026-10-26T07:10:00-05:00",
                        "arrival": "2026-10-26T07:30:00-05:00",
                        "duration_minutes": 20,
                        "distance_meters": 5000,
                        "boarding_stop": "North Lamar",
                        "alighting_stop": "Tech Center",
                    },
                    {
                        "mode": "transit",
                        "route": "801 Downtown",
                        "departure": "2026-10-26T07:32:00-05:00",
                        "arrival": "2026-10-26T07:42:00-05:00",
                        "duration_minutes": 10,
                        "distance_meters": 3000,
                        "boarding_stop": "Tech Center",
                        "alighting_stop": "Work",
                    },
                ],
            }
        ],
    }
    created = client.post(
        "/api/recovery/sessions",
        json={"scenario": default_request(forecast_horizon_days=30).model_dump(mode="json"), "research": research},
    )
    assert created.status_code == 200, created.text
    evidence = created.json()["evidence"][0]
    assert [leg["route"] for leg in evidence["transit_legs"]] == [None, "5 Northcross", "801 Downtown"]
    session = created.json()
    answered = client.post(
        f"/api/recovery/sessions/{session['id']}/answers",
        json={"session_version": session["version"], "question_id": "question-remote-possible", "value": True},
    )
    assert answered.status_code == 200, answered.text
    evaluated = client.post(
        f"/api/recovery/sessions/{session['id']}/evaluate",
        json={"session_version": answered.json()["version"]},
    )
    assert evaluated.status_code == 200, evaluated.text


def test_targeted_transit_research_preserves_answers_and_adds_quantified_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session(monkeypatch)
    session.research_context = ResearchContext(
        home_location="3810 N Lamar Blvd, Austin, TX",
        work_location="525 N Lamar Blvd, Austin, TX",
    )
    session.candidate_actions.append(
        RecoveryActionDefinition(
            id="investigate-transit",
            title="Investigate a timed transit route",
            strategy="transportation",
            description="Research lead only",
            effects=[],
            quantified=False,
        )
    )
    session = submit_answer(
        session.id,
        SubmitAnswerRequest(
            session_version=session.version,
            question_id="question-subscription-pause",
            value=True,
        ),
    )

    class FakeSerp:
        calls = 0
        cache_hits = 0

        def search(self, tool, args, *, max_attempts=1):
            self.calls += 1
            arrive = "arrive_by_iso" in args
            day = date.fromisoformat((args.get("arrive_by_iso") or args["depart_at_iso"])[:10])
            return [
                Evidence(
                    id=f"route-{self.calls}",
                    source_type="transit_directions",
                    provider_engine="google_maps_directions",
                    title="Timed transit itinerary",
                    query="A to B",
                    retrieved_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
                    observed_cost_cents=250,
                    transit_request_kind="arrive_by" if arrive else "depart_at",
                    transit_request_date=day,
                    transit_arrival=__import__("datetime").datetime.fromisoformat(f"{day}T07:45:00-05:00") if arrive else __import__("datetime").datetime.fromisoformat(f"{day}T17:00:00-05:00"),
                    transit_departure=__import__("datetime").datetime.fromisoformat(f"{day}T07:00:00-05:00") if arrive else __import__("datetime").datetime.fromisoformat(f"{day}T16:05:00-05:00"),
                    route_numbers=["7"],
                    transit_origin_matches=True,
                    transit_destination_matches=True,
                    transit_time_constraint_honored=True,
                    fare_source="Mock provider fare",
                    fare_certainty="provider_observed",
                )
            ]

    result = targeted_research(
        session.id,
        ["investigate-transit"],
        session.version,
        Settings(_env_file=None, serpapi_api_key="fake"),
        serp=FakeSerp(),  # type: ignore[arg-type]
    )
    assert any(item.question_id == "question-subscription-pause" for item in result.session.answers)
    transit = [item for item in result.session.candidate_actions if item.id.startswith("action-transit-")]
    assert transit
    assert all(item.quantified and len(item.effects) == 2 for item in transit)
    assert result.calls_used == 4
