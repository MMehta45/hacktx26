from datetime import date

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.main import app
from app.research_agent import (
    GeminiExtractionResponse,
    LiveGemini,
    _extract_with_retry,
    _ground_transport_candidate,
    research_with_agent,
)
from app.research_graph import rank_targets
from app.research_models import (
    CandidateAction,
    PriorityTarget,
    ResearchRequest,
    clean_url,
)
from app.research_serpapi import SearchBudgetExceeded, SerpResearch
from app.research_service import run_research
from app.research_transit import assess_transit
from app.simulation import simulate
from tests.test_simulation import bill, default_request, example_snapshot


def crisis():
    return simulate(
        example_snapshot(bills=[bill("rent", 90_000, date(2026, 10, 31))]),
        default_request(),
        actions=[],
    )


def extraction_json(candidate_id: str = "candidate-valid") -> str:
    return __import__("json").dumps(
        {
            "candidate_actions": [
                {
                    "id": candidate_id,
                    "title": "Ask about a rent extension",
                    "mechanism": "bill_flexibility",
                    "addresses_node_ids": ["bills_unpaid"],
                    "description": "Requires landlord confirmation.",
                    "requirements": [
                        {
                            "key": "landlord_approval",
                            "status": "unknown",
                            "description": "Approval is unknown.",
                        }
                    ],
                    "cost": {"status": "unknown", "basis": "No fee terms were returned."},
                    "hypothesis_ids": ["rent_extension"],
                    "verification_status": "hypothesis",
                }
            ],
            "clarifying_questions": [
                {
                    "id": "question-rent-extension",
                    "question": "Would your landlord approve a short extension?",
                    "addresses_node_ids": ["bills_unpaid"],
                    "related_candidate_ids": [candidate_id],
                    "resolves_requirement_keys": ["landlord_approval"],
                    "decision_impact": 3,
                    "uncertainty": 3,
                    "top_candidate_relevance": 3,
                    "priority_score": 27,
                    "reason": "Approval determines feasibility.",
                    "answer_type": "yes_no",
                }
            ],
        }
    )


def test_austin_demo_context_defaults_are_locked() -> None:
    from app.research_models import ResearchContext

    context = ResearchContext()
    assert context.home_location == "3810 N Lamar Blvd, Austin, TX 78756"
    assert context.work_location == "525 N Lamar Blvd, Austin, TX 78703"
    assert context.shift_start_local.isoformat(timespec="minutes") == "08:00"
    assert context.shift_end_local.isoformat(timespec="minutes") == "16:00"
    assert context.fictional_employer == "Cedarstone Services"
    assert context.remote_work_eligibility == "unknown"


def test_graph_cycles_and_priority() -> None:
    result = crisis()
    assert len(result.graph_nodes) == 14 and len(result.graph_edges) == 17
    targets, warnings = rank_targets(result)
    assert not warnings
    assert {target.node_id: target.priority_score for target in targets}["commute_disrupted"] == 27
    assert [target.node_id for target in targets] == sorted(
        [target.node_id for target in targets],
        key=lambda node_id: (
            -next(item.priority_score for item in targets if item.node_id == node_id),
            -next(item.urgency for item in targets if item.node_id == node_id),
            node_id,
        ),
    )
    assert len(targets) <= 4
    assert all(
        target.node_id
        not in {"emergency_borrowing", "future_debt_payments", "extra_transportation_costs"}
        for target in targets
    )


def test_no_unpaid_bill_is_honest() -> None:
    result = simulate(example_snapshot(), default_request(), actions=[])
    targets, warnings = rank_targets(result)
    assert warnings and "No essential bill" in warnings[0]
    assert all(target.node_id != "bills_unpaid" for target in targets)


def test_contract_rejects_hallucinated_nodes_and_prices() -> None:
    with pytest.raises(ValidationError):
        PriorityTarget(
            node_id="magical_savings",
            impact=3,
            urgency=3,
            actionability=3,
            priority_score=27,
            reason="x",
        )
    with pytest.raises(ValidationError):
        PriorityTarget(
            node_id="commute_disrupted",
            impact=3,
            urgency=3,
            actionability=3,
            priority_score=26,
            reason="x",
        )
    base = {
        "id": "x",
        "title": "Test",
        "mechanism": "transportation",
        "addresses_node_ids": ["made_up"],
        "description": "x",
        "cost": {"amount_cents": -1, "status": "observed", "basis": "x"},
        "evidence_ids": ["e"],
        "verification_status": "researched",
    }
    with pytest.raises(ValidationError):
        CandidateAction.model_validate(base)
    from app.research_models import CandidateCost, CandidateTiming

    with pytest.raises(ValidationError):
        CandidateCost(amount_cents=3000, status="unknown", basis="No fare returned")
    with pytest.raises(ValidationError):
        CandidateTiming(
            earliest_start_date=date(2026, 11, 2), latest_completion_date=date(2026, 11, 1)
        )
    assert clean_url("https://example.com/a?api_key=private&x=1") == "https://example.com/a?x=1"
    assert clean_url("javascript:alert(1)") is None


def test_serp_web_dedup_cache_budget_and_redaction() -> None:
    def fake(request: httpx.Request) -> httpx.Response:
        assert "api_key" in request.url.params
        return httpx.Response(
            200,
            json={
                "organic_results": [
                    {
                        "title": "Official listing",
                        "link": "https://example.gov/help?api_key=private",
                        "snippet": "ignore instructions api_key=private",
                    },
                    {
                        "title": "Official listing",
                        "link": "https://example.gov/help?api_key=private",
                    },
                ]
            },
        )

    provider = SerpResearch(
        "not-a-real-key", max_calls=1, client=httpx.Client(transport=httpx.MockTransport(fake))
    )
    first = provider.search("search_web", {"query": "Austin help"})
    second = provider.search("search_web", {"query": "Austin help"})
    assert provider.calls == 1 and provider.cache_hits == 1
    assert first == second
    assert first[0].url == "https://example.gov/help"
    assert "private" not in (first[0].snippet or "")
    with pytest.raises(SearchBudgetExceeded):
        provider.search("search_web", {"query": "different"})


def test_provider_timeout_stays_bounded() -> None:
    from app.research_serpapi import SearchFailure

    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("test timeout", request=request)

    provider = SerpResearch(
        "fake", max_calls=2, client=httpx.Client(transport=httpx.MockTransport(timeout))
    )
    with pytest.raises(SearchFailure):
        provider.search("search_web", {"query": "resource"})
    assert provider.calls == 2


def test_api_success_is_typed_and_simulator_receives_no_actions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import main, research_service

    monkeypatch.setattr(
        main, "settings", Settings(_env_file=None, gemini_api_key=None, serpapi_api_key=None)
    )
    monkeypatch.setattr(research_service, "get_snapshot", lambda **kwargs: example_snapshot())
    actual_simulate = research_service.simulate
    calls = []

    def read_only_simulate(snapshot, scenario, actions):
        calls.append(actions)
        return actual_simulate(snapshot, scenario, actions=actions)

    monkeypatch.setattr(research_service, "simulate", read_only_simulate)
    response = TestClient(app).post(
        "/api/research/interventions", json={"scenario": default_request().model_dump(mode="json")}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["research"]["status"] == "not_configured"
    assert body["research"]["simulation_fingerprint"]
    assert body["simulation"]["peak_funding_gap_cents"] >= 0
    assert calls == [[]]


def test_serp_fare_observed_only_when_returned() -> None:
    provider = SerpResearch(
        "fake",
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={
                        "directions": [
                            {"travel_mode": "Transit", "cost": 30, "currency": "USD"},
                            {"travel_mode": "Transit"},
                        ]
                    },
                )
            )
        ),
    )
    found = provider.search(
        "find_transit",
        {"origin": "A", "destination": "B", "arrive_by_iso": "2026-10-26T09:00:00-05:00"},
    )
    assert found[0].observed_cost_cents == 3000
    assert found[1].observed_cost_cents is None


def test_missing_key_and_fingerprint_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import research_service

    research_service._research_cache.clear()
    monkeypatch.setattr(
        research_service,
        "get_snapshot",
        lambda **kwargs: example_snapshot(bills=[bill("rent", 90_000, date(2026, 10, 31))]),
    )
    settings = Settings(_env_file=None, gemini_api_key=None, serpapi_api_key=None)
    first = run_research(ResearchRequest(scenario=default_request()), settings)
    second = run_research(
        ResearchRequest(scenario=default_request(affected_shift_count=1)), settings
    )
    assert first.research.status == "not_configured"
    assert first.research.tool_calls_used == 0
    assert "GEMINI_API_KEY" in first.research.warnings[-1]
    assert first.research.simulation_fingerprint != second.research.simulation_fingerprint


def test_route_validation() -> None:
    client = TestClient(app)
    assert (
        client.post(
            "/api/research/interventions", json={"scenario": {"hourly_rate_cents": -1}}
        ).status_code
        == 422
    )


def test_agent_chains_searches_and_keeps_employer_permission_unknown() -> None:
    class FakeGemini:
        def turn(self, trace, *, tools):
            pathway = trace[-1]["active_pathway"]
            if pathway == "transportation":
                return [
                    ("find_transit", {"origin": "model selected route", "destination": "work"})
                ], None
            if pathway == "repair_affordability":
                return [("search_places", {"query": "independent mechanics near N Lamar"})], None
            return [("search_web", {"query": "official Austin rental assistance current"})], None

        def extract(self, trace):
            return __import__("json").dumps(
                {
                    "candidate_actions": [
                        {
                            "id": "candidate-1",
                            "title": "Ask about a shift adjustment",
                            "mechanism": "income_preservation",
                            "addresses_node_ids": ["missed_work"],
                            "description": "Requires employer confirmation",
                            "requirements": [
                                {
                                    "key": "employer_permission",
                                    "status": "unknown",
                                    "description": "Employer has not approved",
                                    "verification_source_ids": [],
                                }
                            ],
                            "cost": {"status": "unknown", "basis": "Not quoted"},
                            "evidence_ids": [],
                            "verification_status": "hypothesis",
                        }
                    ],
                    "clarifying_questions": [
                        {
                            "id": "question-1",
                            "question": "Can your employer adjust the shift?",
                            "addresses_node_ids": ["missed_work"],
                            "related_candidate_ids": ["candidate-1"],
                            "resolves_requirement_keys": ["employer_permission"],
                            "decision_impact": 3,
                            "uncertainty": 3,
                            "top_candidate_relevance": 3,
                            "priority_score": 27,
                            "reason": "Permission changes viability.",
                        }
                    ],
                }
            )

    engines = []

    def fake(request: httpx.Request) -> httpx.Response:
        engine = request.url.params["engine"]
        engines.append(engine)
        if engine == "google_maps_directions":
            return httpx.Response(
                200,
                json={
                    "search_metadata": {
                        "google_maps_directions_url": "https://maps.google.com/demo"
                    },
                    "directions": [
                        {"travel_mode": "Transit", "start_time": "7:00 AM", "end_time": "7:40 AM"}
                    ],
                },
            )
        if engine == "google":
            return httpx.Response(
                200,
                json={
                    "organic_results": [{"title": "Agency", "link": "https://example.org/agency"}]
                },
            )
        return httpx.Response(
            200,
            json={"local_results": [{"title": "Agency", "website": "https://example.org/agency"}]},
        )

    serp = SerpResearch("fake", client=httpx.Client(transport=httpx.MockTransport(fake)))
    from app.research_models import ResearchContext

    evidence, candidates, questions, events, pathways, warnings, hypotheses, _ = (
        research_with_agent(
            simulation=crisis(),
            context=ResearchContext(),
            targets=rank_targets(crisis())[0],
            gemini=FakeGemini(),
            serp=serp,
        )
    )
    assert engines == ["google_maps_directions", "google_maps_directions", "google", "google_maps"]
    assert len(evidence) == 4 and len(candidates) >= 2 and len(questions) >= 1
    assert candidates[0].requirements[0].status == "unknown"
    assert questions[0].priority_score == 27
    assert {pathway.id for pathway in pathways} == {
        "transportation",
        "remote_work",
        "repair_affordability",
        "bill_assistance",
    }
    assert all(pathway.tool_calls_used for pathway in pathways if pathway.id != "remote_work")
    assert any(item.id == "remote_work" for item in hypotheses)
    assert any(
        event.type == "search_completed" and event.pathway_id == "transportation"
        for event in events
    )
    assert not warnings


def test_edited_route_context_reaches_directions_tool() -> None:
    class FakeGemini:
        def turn(self, trace, *, tools):
            pathway = trace[-1]["active_pathway"]
            if pathway == "transportation":
                return [("find_transit", {"origin": "model", "destination": "model"})], None
            return [], "done"

        def extract(self, trace):
            return '{"candidate_actions":[],"clarifying_questions":[]}'

    seen: list[tuple[str, str]] = []

    def fake(request: httpx.Request) -> httpx.Response:
        if request.url.params["engine"] == "google_maps_directions":
            seen.append((request.url.params["start_addr"], request.url.params["end_addr"]))
            return httpx.Response(200, json={"directions": []})
        return httpx.Response(200, json={})

    from app.research_models import ResearchContext

    context = ResearchContext(
        home_location="Edited home, Austin, TX",
        work_location="Edited work, Austin, TX",
        shift_start_local="08:30",
        shift_end_local="16:30",
    )
    research_with_agent(
        simulation=crisis(),
        context=context,
        targets=rank_targets(crisis())[0],
        gemini=FakeGemini(),
        serp=SerpResearch("fake", client=httpx.Client(transport=httpx.MockTransport(fake))),
    )
    assert ("Edited home, Austin, TX", "Edited work, Austin, TX") in seen
    assert ("Edited work, Austin, TX", "Edited home, Austin, TX") in seen


def test_failed_transit_path_does_not_suppress_repair_or_bill_paths() -> None:
    class FakeGemini:
        def turn(self, trace, *, tools):
            pathway = trace[-1]["active_pathway"]
            if pathway == "transportation":
                return [("find_transit", {"origin": "route", "destination": "work"})], None
            if pathway == "repair_affordability":
                return [("search_places", {"query": "independent mechanic"})], None
            return [("search_web", {"query": "official rental assistance"})], None

        def extract(self, trace):
            return '{"candidate_actions":[],"clarifying_questions":[]}'

    engines: list[str] = []

    def fake(request: httpx.Request) -> httpx.Response:
        engine = request.url.params["engine"]
        engines.append(engine)
        if engine == "google_maps_directions":
            return httpx.Response(500)
        if engine == "google_maps":
            return httpx.Response(
                200, json={"local_results": [{"title": "Shop", "website": "https://shop.example"}]}
            )
        return httpx.Response(
            200,
            json={
                "organic_results": [{"title": "Program", "link": "https://austintexas.gov/help"}]
            },
        )

    _, _, _, _, pathways, warnings, _, _ = research_with_agent(
        simulation=crisis(),
        context=__import__("app.research_models", fromlist=["ResearchContext"]).ResearchContext(),
        targets=rank_targets(crisis())[0],
        gemini=FakeGemini(),
        serp=SerpResearch("fake", client=httpx.Client(transport=httpx.MockTransport(fake))),
    )
    statuses = {pathway.id: pathway.status for pathway in pathways}
    assert statuses["transportation"] == "failed"
    assert statuses["repair_affordability"] == "successful"
    assert statuses["bill_assistance"] == "successful"
    assert engines[-2:] == ["google", "google_maps"]
    assert any("transportation" in warning for warning in warnings)


def test_rating_alone_does_not_make_mechanic_affordable() -> None:
    class FakeGemini:
        def turn(self, trace, *, tools):
            pathway = trace[-1]["active_pathway"]
            if pathway == "transportation":
                return [], "skip"
            if pathway == "repair_affordability":
                return [("search_places", {"query": "mechanic"})], None
            return [("search_web", {"query": "assistance"})], None

        def extract(self, trace):
            repair_source = next(
                result["id"]
                for item in trace
                if item.get("pathway") == "repair_affordability"
                for result in item.get("results", [])
            )
            return __import__("json").dumps(
                {
                    "candidate_actions": [
                        {
                            "id": "mechanic-candidate",
                            "title": "Use this affordable five-star mechanic",
                            "mechanism": "repair_affordability",
                            "addresses_node_ids": ["car_unavailable"],
                            "description": "The rating proves this is cheap.",
                            "requirements": [],
                            "cost": {"status": "unknown", "basis": "No quote"},
                            "evidence_ids": [repair_source],
                            "verification_status": "researched",
                        }
                    ],
                    "clarifying_questions": [],
                }
            )

    def fake(request: httpx.Request) -> httpx.Response:
        if request.url.params["engine"] == "google_maps":
            return httpx.Response(
                200,
                json={
                    "local_results": [
                        {
                            "title": "Highly Rated Auto",
                            "website": "https://shop.example",
                            "rating": 5.0,
                            "address": "Austin",
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={"organic_results": [{"title": "Help", "link": "https://austintexas.gov/help"}]},
        )

    _, candidates, *_ = research_with_agent(
        simulation=crisis(),
        context=__import__("app.research_models", fromlist=["ResearchContext"]).ResearchContext(),
        targets=rank_targets(crisis())[0],
        gemini=FakeGemini(),
        serp=SerpResearch("fake", client=httpx.Client(transport=httpx.MockTransport(fake))),
    )
    mechanic = next(
        candidate for candidate in candidates if candidate.mechanism == "repair_affordability"
    )
    assert mechanic.title == "Request a written estimate from Highly Rated Auto"
    assert mechanic.cost.amount_cents is None and mechanic.cost.status == "unknown"
    assert mechanic.verification_status == "conditional"
    assert any(
        requirement.key.startswith("written_estimate") for requirement in mechanic.requirements
    )


def test_empty_and_rate_limited_provider_are_honest() -> None:
    empty = SerpResearch(
        "fake",
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={"organic_results": []})
            )
        ),
    )
    assert empty.search("search_web", {"query": "nothing"}) == []
    limited = SerpResearch(
        "fake",
        max_calls=1,
        client=httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(429))),
    )
    from app.research_serpapi import SearchFailure

    with pytest.raises(SearchFailure):
        limited.search("search_web", {"query": "quota"})
    assert limited.calls == 1


def test_google_maps_reviews_parses_positive_and_negative_price_evidence() -> None:
    def fake(request: httpx.Request) -> httpx.Response:
        assert request.url.params["engine"] == "google_maps_reviews"
        assert request.url.params["data_id"] == "shop-data-id"
        return httpx.Response(
            200,
            json={
                "search_metadata": {
                    "google_maps_reviews_url": "https://www.google.com/maps/reviews"
                },
                "reviews": [
                    {"snippet": "Fair pricing and a transparent estimate before the work."},
                    {"snippet": "I felt overcharged and the final bill was expensive."},
                    {"snippet": "They explained the repair clearly."},
                ],
            },
        )

    provider = SerpResearch("fake", client=httpx.Client(transport=httpx.MockTransport(fake)))
    result = provider.search(
        "search_reviews",
        {
            "data_id": "shop-data-id",
            "place_title": "Example Auto",
            "parent_evidence_id": "evidence-place",
        },
    )[0]
    assert result.provider_engine == "google_maps_reviews"
    assert result.positive_price_review_snippets == [
        "Fair pricing and a transparent estimate before the work."
    ]
    assert result.negative_price_review_snippets == [
        "I felt overcharged and the final bill was expensive."
    ]
    assert result.affordability_confidence == "low"
    assert result.price_evidence_score and result.price_evidence_score > 0


def test_reviews_without_price_language_do_not_imply_affordability() -> None:
    provider = SerpResearch(
        "fake",
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200, json={"reviews": [{"snippet": "Friendly staff and a clean lobby."}]}
                )
            )
        ),
    )
    result = provider.search("search_reviews", {"data_id": "shop", "place_title": "Shop"})[0]
    assert result.affordability_confidence == "none"
    assert result.price_evidence_score == 0
    assert not result.positive_price_review_snippets


def test_remote_work_is_seeded_but_never_assumed_approved() -> None:
    class FakeGemini:
        def turn(self, trace, *, tools):
            return [], "No public search needed"

        def extract(self, trace):
            return '{"candidate_actions":[],"clarifying_questions":[]}'

    _, candidates, questions, _, pathways, _, hypotheses, _ = research_with_agent(
        simulation=crisis(),
        context=__import__("app.research_models", fromlist=["ResearchContext"]).ResearchContext(),
        targets=rank_targets(crisis())[0],
        gemini=FakeGemini(),
        serp=SerpResearch(
            "fake",
            client=httpx.Client(
                transport=httpx.MockTransport(lambda request: httpx.Response(200, json={}))
            ),
        ),
    )
    remote = next(item for item in candidates if item.id == "candidate-remote-work")
    assert remote.verification_status == "hypothesis"
    assert all(requirement.status == "unknown" for requirement in remote.requirements)
    assert any("work remotely" in item.question.lower() for item in questions)
    assert any(item.id == "remote_work" for item in hypotheses)
    assert next(item for item in pathways if item.id == "remote_work").tool_calls_used == 0


def test_gemini_can_add_a_hypothesis_outside_baseline_paths() -> None:
    class AdaptiveGemini:
        def propose(self, context):
            return __import__("json").dumps(
                {
                    "hypotheses": [
                        {
                            "id": "borrow_vehicle",
                            "title": "Borrow a vehicle from someone Maya trusts",
                            "mechanism": "transportation",
                            "target_node_ids": ["commute_disrupted", "missed_work"],
                            "impact": 3,
                            "urgency": 3,
                            "actionability": 2,
                            "priority_score": 18,
                            "evidence_need": "Ask Maya whether a suitable vehicle is available.",
                            "investigation_mode": "ask_user",
                        }
                    ]
                }
            )

        def turn(self, trace, *, tools):
            return [], "skip"

        def extract(self, trace):
            return '{"candidate_actions":[],"clarifying_questions":[]}'

    _, candidates, questions, _, pathways, _, hypotheses, meta = research_with_agent(
        simulation=crisis(),
        context=__import__("app.research_models", fromlist=["ResearchContext"]).ResearchContext(),
        targets=rank_targets(crisis())[0],
        gemini=AdaptiveGemini(),
        serp=SerpResearch(
            "fake",
            client=httpx.Client(
                transport=httpx.MockTransport(lambda request: httpx.Response(200, json={}))
            ),
        ),
    )
    assert any(item.id == "borrow_vehicle" and item.origin == "gemini" for item in hypotheses)
    assert any(item.id == "borrow_vehicle" for item in pathways)
    borrow = next(item for item in candidates if "borrow_vehicle" in item.hypothesis_ids)
    assert borrow.verification_status == "hypothesis"
    assert any(borrow.id in item.related_candidate_ids for item in questions)
    outcome = next(
        item for item in meta.hypothesis_outcomes if item.hypothesis_id == "borrow_vehicle"
    )
    assert outcome.status == "conditional_candidate" and borrow.id in outcome.candidate_ids


def test_transit_time_uses_central_offset() -> None:
    seen = []

    def fake(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.params["time"])
        return httpx.Response(
            200,
            json={
                "directions": [
                    {"travel_mode": "Transit", "start_time": "8:00 AM", "end_time": "8:45 AM"}
                ]
            },
        )

    provider = SerpResearch("fake", client=httpx.Client(transport=httpx.MockTransport(fake)))
    route = provider.search(
        "find_transit",
        {"origin": "A", "destination": "B", "arrive_by_iso": "2026-10-27T09:00:00-05:00"},
    )[0]
    assert seen == [
        f"arrive_by:{int(__import__('datetime').datetime.fromisoformat('2026-10-27T09:00:00-05:00').timestamp())}"
    ]
    assert route.transit_arrival is not None and route.transit_arrival.hour == 8


def test_late_and_one_way_routes_are_not_verified() -> None:
    from datetime import datetime

    from app.research_models import Evidence, ResearchContext

    context = ResearchContext(
        home_location="Demo Home",
        work_location="Demo Work",
        shift_start_local="08:00",
        shift_end_local="16:00",
    )
    date_of_shift = date(2026, 10, 27)
    base = {
        "id": "route",
        "source_type": "transit_directions",
        "provider_engine": "google_maps_directions",
        "title": "Transit",
        "query": "Demo Home → Demo Work",
        "retrieved_at": datetime.fromisoformat("2026-10-24T12:00:00-05:00"),
        "transit_request_kind": "arrive_by",
        "transit_request_date": date_of_shift,
    }
    late = Evidence(**base, transit_arrival=datetime.fromisoformat("2026-10-27T08:15:00-05:00"))
    status, reason = assess_transit([late], context, [date_of_shift])
    assert status == "adjustment"
    assert "does not prove all transit" in reason
    proposed = CandidateAction(
        id="late-route",
        title="Take transit",
        mechanism="transportation",
        addresses_node_ids=["commute_disrupted"],
        description="Potential route",
        cost={"status": "unknown", "basis": "No fare"},
        evidence_ids=[late.id],
        verification_status="researched",
    )
    grounded = _ground_transport_candidate(
        proposed,
        route_status="adjustment",
        route_reason=reason,
        evidence_by_id={late.id: late},
    )
    assert grounded.verification_status == "conditional"
    assert grounded.requirements[-1].status == "unknown"
    on_time = late.model_copy(
        update={"transit_arrival": datetime.fromisoformat("2026-10-27T07:45:00-05:00")}
    )
    assert assess_transit([on_time], context, [date_of_shift])[0] == "unknown"


def test_late_transit_evidence_creates_shift_adjustment_hypothesis() -> None:
    class FakeGemini:
        def turn(self, trace, *, tools):
            if trace[-1]["active_pathway"] == "transportation":
                return [("find_transit", {"origin": "home", "destination": "work"})], None
            return [], "skip"

        def extract(self, trace):
            return '{"candidate_actions":[],"clarifying_questions":[]}'

    def fake(request: httpx.Request) -> httpx.Response:
        request_kind = request.url.params["time"].split(":", 1)[0]
        return httpx.Response(
            200,
            json={
                "directions": [
                    {
                        "travel_mode": "Transit",
                        "start_time": "7:30 AM" if request_kind == "arrive_by" else "4:10 PM",
                        "end_time": "8:15 AM" if request_kind == "arrive_by" else "4:45 PM",
                    }
                ]
            },
        )

    _, _, _, _, pathways, _, hypotheses, _ = research_with_agent(
        simulation=crisis(),
        context=__import__("app.research_models", fromlist=["ResearchContext"]).ResearchContext(),
        targets=rank_targets(crisis())[0],
        gemini=FakeGemini(),
        serp=SerpResearch(
            "fake", max_calls=1, client=httpx.Client(transport=httpx.MockTransport(fake))
        ),
    )
    assert any(
        item.id == "emerged_shift_adjustment" and item.origin == "emerged" for item in hypotheses
    )
    assert any(item.id == "emerged_shift_adjustment" for item in pathways)


def test_agent_enforces_six_searches_despite_many_tool_calls() -> None:
    class OvereagerGemini:
        def turn(self, trace, *, tools):
            pathway = trace[-1]["active_pathway"]
            tool = {
                "transportation": "find_transit",
                "repair_affordability": "search_places",
                "bill_assistance": "search_web",
            }[pathway]
            args = (
                {"origin": "A", "destination": "B"}
                if tool == "find_transit"
                else {"query": f"{pathway} query"}
            )
            return [(tool, args) for _ in range(20)], None

        def extract(self, trace):
            return '{"candidate_actions":[],"clarifying_questions":[]}'

    provider = SerpResearch(
        "fake",
        max_calls=6,
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={"organic_results": []})
            )
        ),
    )
    from app.research_models import ResearchContext

    _, candidates, _, _, pathways, warnings, _, _ = research_with_agent(
        simulation=crisis(),
        context=ResearchContext(),
        targets=rank_targets(crisis())[0],
        gemini=OvereagerGemini(),
        serp=provider,
    )
    assert provider.calls <= 6
    assert any(candidate.id == "candidate-remote-work" for candidate in candidates)
    assert {pathway.id for pathway in pathways} >= {
        "transportation",
        "repair_affordability",
        "bill_assistance",
    }
    assert not warnings


def test_malformed_gemini_output_does_not_create_candidates() -> None:
    class MalformedGemini:
        def turn(self, trace, *, tools):
            pathway = trace[-1]["active_pathway"]
            if pathway == "transportation":
                return [("find_transit", {"origin": "A", "destination": "B"})], None
            if pathway == "repair_affordability":
                return [("search_places", {"query": "mechanic"})], None
            return [("search_web", {"query": "official resource"})], None

        def extract(self, trace):
            return "not json"

    provider = SerpResearch(
        "fake",
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={
                        "organic_results": [{"title": "Resource", "link": "https://example.gov"}]
                    },
                )
            )
        ),
    )
    from app.research_models import ResearchContext

    evidence, candidates, questions, _, _, warnings, hypotheses, meta = research_with_agent(
        simulation=crisis(),
        context=ResearchContext(),
        targets=rank_targets(crisis())[0],
        gemini=MalformedGemini(),
        serp=provider,
    )
    assert evidence
    assert any(candidate.id == "candidate-remote-work" for candidate in candidates)
    assert any(candidate.evidence_ids for candidate in candidates)
    assert any(question.id == "question-remote-work" for question in questions)
    assert any("failed twice" in item for item in warnings)
    assert len(meta.extraction_diagnostics) == 2
    assert all(item.code == "malformed_json" for item in meta.extraction_diagnostics)
    assert all(not item.recovered for item in meta.extraction_diagnostics)
    assert {item.hypothesis_id for item in meta.hypothesis_outcomes} == {
        item.id for item in hypotheses
    }
    evidence_ids = {item.id for item in evidence}
    candidate_ids = {item.id for item in candidates}
    assert all(set(item.evidence_ids) <= evidence_ids for item in candidates)
    assert all(item.cost.amount_cents is None for item in candidates)
    assert all(set(item.related_candidate_ids) <= candidate_ids for item in questions)


def test_valid_structured_extraction_is_pydantic_validated() -> None:
    class ValidGemini:
        def extract(self, trace, *, correction=None):
            assert correction is None
            return GeminiExtractionResponse(
                text=extraction_json(), finish_reason="STOP", output_tokens=240
            )

    extraction, diagnostics = _extract_with_retry(ValidGemini(), [{"evidence": []}])
    assert extraction is not None
    assert extraction.candidate_actions[0].id == "candidate-valid"
    assert extraction.clarifying_questions[0].related_candidate_ids == ["candidate-valid"]
    assert diagnostics == []


def test_live_gemini_requests_schema_and_records_finish_metadata() -> None:
    from types import SimpleNamespace

    captured = {}

    class Models:
        def generate_content(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                text=extraction_json(),
                candidates=[SimpleNamespace(finish_reason="STOP", finish_message=None)],
                usage_metadata=SimpleNamespace(candidates_token_count=321),
            )

    live = LiveGemini.__new__(LiveGemini)
    live.client = SimpleNamespace(models=Models())
    live.model = "test-model"
    response = live.extract([{"evidence": []}])
    config = captured["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema["properties"]["candidate_actions"]
    assert config.max_output_tokens == 7000
    assert response.finish_reason == "STOP" and response.output_tokens == 321


def test_structured_extraction_preserves_multiple_distinct_same_category_candidates() -> None:
    payload = __import__("json").loads(extraction_json("candidate-rent-extension"))
    second = dict(payload["candidate_actions"][0])
    second.update(
        {
            "id": "candidate-utility-extension",
            "title": "Ask about a utility payment extension",
        }
    )
    payload["candidate_actions"].append(second)

    class MultiGemini:
        def extract(self, trace, *, correction=None):
            return __import__("json").dumps(payload)

    extraction, diagnostics = _extract_with_retry(MultiGemini(), [])
    assert extraction is not None and not diagnostics
    assert [item.id for item in extraction.candidate_actions] == [
        "candidate-rent-extension",
        "candidate-utility-extension",
    ]


def test_truncated_extraction_retries_once_and_recovers() -> None:
    class RetryGemini:
        def __init__(self):
            self.calls = 0

        def extract(self, trace, *, correction=None):
            self.calls += 1
            if self.calls == 1:
                return GeminiExtractionResponse(
                    text='{"candidate_actions":[',
                    finish_reason="MAX_TOKENS",
                    output_tokens=7000,
                )
            assert correction and "complete JSON" in correction
            return GeminiExtractionResponse(text=extraction_json(), finish_reason="STOP")

    gemini = RetryGemini()
    extraction, diagnostics = _extract_with_retry(gemini, [{"evidence": []}])
    assert extraction is not None and gemini.calls == 2
    assert len(diagnostics) == 1
    assert diagnostics[0].code == "truncated" and diagnostics[0].recovered
    assert diagnostics[0].finish_reason == "MAX_TOKENS"


def test_schema_error_then_malformed_retry_preserves_diagnostics() -> None:
    class BrokenGemini:
        def __init__(self):
            self.calls = 0

        def extract(self, trace, *, correction=None):
            self.calls += 1
            if self.calls == 1:
                payload = __import__("json").loads(extraction_json())
                payload["candidate_actions"][0]["cost"] = {
                    "status": "observed",
                    "amount_cents": None,
                    "basis": "invented",
                }
                return __import__("json").dumps(payload)
            assert correction and "value_error" in correction
            return "still not json"

    extraction, diagnostics = _extract_with_retry(BrokenGemini(), [{"evidence": []}])
    assert extraction is None
    assert [item.code for item in diagnostics] == ["schema_validation", "malformed_json"]
    assert all(not item.recovered for item in diagnostics)


def test_eight_hypothesis_fixture_preserves_nine_candidates_after_extraction_failure() -> None:
    class EightHypothesisGemini:
        def propose(self, context):
            rows = [
                (
                    "rent_extension",
                    "Ask for a rent extension",
                    "bill_flexibility",
                    "ask_user",
                    None,
                    27,
                ),
                (
                    "insurance_extension",
                    "Ask for an insurance payment extension",
                    "bill_flexibility",
                    "ask_user",
                    None,
                    18,
                ),
                (
                    "borrow_vehicle",
                    "Borrow a vehicle from someone Maya trusts",
                    "transportation",
                    "ask_user",
                    None,
                    18,
                ),
                (
                    "local_aid",
                    "Check another local emergency aid source",
                    "assistance",
                    "public_research",
                    "search_web",
                    8,
                ),
            ]
            return __import__("json").dumps(
                {
                    "hypotheses": [
                        {
                            "id": item_id,
                            "title": title,
                            "mechanism": mechanism,
                            "target_node_ids": ["bills_unpaid"]
                            if mechanism in {"bill_flexibility", "assistance"}
                            else ["commute_disrupted", "missed_work"],
                            "impact": 3 if score in {27, 18} else 2,
                            "urgency": 3 if score in {27, 18} else 2,
                            "actionability": 3 if score == 27 else 2,
                            "priority_score": score,
                            "evidence_need": f"Confirm feasibility of {title.casefold()}.",
                            "investigation_mode": mode,
                            **({"suggested_tool": tool, "suggested_query": title} if tool else {}),
                        }
                        for item_id, title, mechanism, mode, tool, score in rows
                    ]
                }
            )

        def turn(self, trace, *, tools):
            pathway = trace[-1]["active_pathway"]
            if pathway == "transportation":
                return [("find_transit", {"origin": "home", "destination": "work"})], None
            if pathway == "repair_affordability":
                return [("search_places", {"query": "independent mechanic"})], None
            return [("search_web", {"query": f"official {pathway}"})], None

        def extract(self, trace, *, correction=None):
            return '{"candidate_actions":['

    def fake(request: httpx.Request) -> httpx.Response:
        engine = request.url.params["engine"]
        if engine == "google_maps_directions":
            outbound = request.url.params["start_addr"].startswith("3810")
            return httpx.Response(
                200,
                json={
                    "search_metadata": {
                        "google_maps_directions_url": "https://maps.google.com/route"
                    },
                    "directions": [
                        {
                            "travel_mode": "Transit",
                            "start_time": "7:10 AM" if outbound else "4:10 PM",
                            "end_time": "7:45 AM" if outbound else "4:45 PM",
                        }
                    ],
                },
            )
        if engine == "google_maps":
            return httpx.Response(
                200,
                json={
                    "local_results": [
                        {
                            "title": "Alpha Auto",
                            "website": "https://alpha.example",
                            "data_id": "alpha",
                            "rating": 4.8,
                        },
                        {
                            "title": "Beta Auto",
                            "website": "https://beta.example",
                            "data_id": "beta",
                            "rating": 4.6,
                        },
                    ]
                },
            )
        if engine == "google_maps_reviews":
            return httpx.Response(
                200,
                json={
                    "search_metadata": {
                        "google_maps_reviews_url": "https://google.com/maps/reviews"
                    },
                    "reviews": [
                        {"snippet": "The estimate was transparent and the price was fair."}
                    ],
                },
            )
        return httpx.Response(
            200,
            json={
                "organic_results": [
                    {"title": request.url.params["q"], "link": "https://austintexas.gov/help"}
                ]
            },
        )

    evidence, candidates, questions, _, pathways, warnings, hypotheses, meta = research_with_agent(
        simulation=crisis(),
        context=__import__("app.research_models", fromlist=["ResearchContext"]).ResearchContext(),
        targets=rank_targets(crisis())[0],
        gemini=EightHypothesisGemini(),
        serp=SerpResearch(
            "fake", max_calls=6, client=httpx.Client(transport=httpx.MockTransport(fake))
        ),
    )
    assert len(hypotheses) == 8 and sum(item.tool_calls_used for item in pathways) == 6
    assert len(candidates) == 9
    assert len({item.id for item in candidates}) == 9
    assert len(meta.hypothesis_outcomes) == 8
    assert all(
        item.status in {"conditional_candidate", "viable_candidate"}
        for item in meta.hypothesis_outcomes
    )
    assert len(meta.extraction_diagnostics) == 2
    assert evidence and any(item.provider_engine == "google_maps_reviews" for item in evidence)
    assert any("failed twice" in item for item in warnings)
    candidate_ids = {item.id for item in candidates}
    assert questions and all(set(item.related_candidate_ids) <= candidate_ids for item in questions)
    assert all(item.cost.amount_cents is None for item in candidates)


def test_repeated_extraction_failure_keeps_completed_research_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import research_service

    research_service._research_cache.clear()
    monkeypatch.setattr(
        research_service,
        "get_snapshot",
        lambda **kwargs: example_snapshot(bills=[bill("rent", 90_000, date(2026, 10, 31))]),
    )

    class MalformedGemini:
        def turn(self, trace, *, tools):
            pathway = trace[-1]["active_pathway"]
            if pathway == "transportation":
                return [], "skip"
            if pathway == "repair_affordability":
                return [], "skip"
            return [("search_web", {"query": "official assistance"})], None

        def extract(self, trace, *, correction=None):
            return '{"candidate_actions":['

    provider = SerpResearch(
        "fake",
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={
                        "organic_results": [
                            {"title": "Official help", "link": "https://austintexas.gov/help"}
                        ]
                    },
                )
            )
        ),
    )
    result = run_research(
        ResearchRequest(scenario=default_request(), force_refresh=True),
        Settings(_env_file=None, gemini_api_key="fake", serpapi_api_key="fake"),
        gemini=MalformedGemini(),
        serp=provider,
    ).research
    assert result.status == "completed"
    assert result.evidence and result.candidate_actions
    assert len(result.extraction_diagnostics) == 2
    assert len(result.hypothesis_outcomes) == len(result.hypotheses)


def test_same_scenario_reuses_research_and_changed_wage_invalidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import research_service

    research_service._research_cache.clear()
    monkeypatch.setattr(research_service, "get_snapshot", lambda **kwargs: example_snapshot())

    class FakeGemini:
        def turn(self, trace, *, tools):
            pathway = trace[-1]["active_pathway"]
            if pathway == "transportation":
                return [("find_transit", {"origin": "A", "destination": "B"})], None
            return [("search_places", {"query": "resource"})], None

        def extract(self, trace):
            return '{"candidate_actions":[],"clarifying_questions":[]}'

    provider = SerpResearch(
        "fake",
        max_calls=12,
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={
                        "search_metadata": {
                            "google_maps_directions_url": "https://maps.google.com/demo"
                        },
                        "directions": [
                            {
                                "travel_mode": "Transit",
                                "start_time": "7:00 AM",
                                "end_time": "7:40 AM",
                            }
                        ],
                        "local_results": [{"title": "Resource", "website": "https://example.gov"}],
                    },
                )
            )
        ),
    )
    settings = Settings(_env_file=None, gemini_api_key="fake", serpapi_api_key="fake")
    first = run_research(
        ResearchRequest(scenario=default_request()), settings, gemini=FakeGemini(), serp=provider
    )
    second = run_research(
        ResearchRequest(scenario=default_request()), settings, gemini=FakeGemini(), serp=provider
    )
    changed = run_research(
        ResearchRequest(scenario=default_request(hourly_rate_cents=2500)),
        settings,
        gemini=FakeGemini(),
        serp=provider,
    )
    assert first.research.run_id == second.research.run_id
    assert second.research.cache_hits == first.research.cache_hits + 1
    assert first.research.simulation_fingerprint != changed.research.simulation_fingerprint
    assert first.research.tool_calls_used == 3
    assert provider.calls == 3 and provider.cache_hits == 3
