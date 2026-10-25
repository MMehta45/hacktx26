import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

from app.config import Settings
from app.demo_transit import maya_route_5_fixture
from app.research_agent import LiveGemini, ResearchRunMeta, research_with_agent
from app.research_graph import rank_targets
from app.research_models import ResearchRequest, ResearchResponse, ResearchResult
from app.research_serpapi import SerpResearch
from app.simulation import simulate
from app.snapshot import get_snapshot

_research_cache: dict[str, tuple[datetime, ResearchResult]] = {}


def research_fingerprint(*, simulation, scenario, context) -> str:
    """Stable identity shared by Explore and Recovery; excludes retrieval time."""
    fingerprint_data = {
        "source": simulation.source.model_dump(mode="json", exclude={"source_retrieved_at"}),
        "scenario": simulation.scenario.model_dump(mode="json"),
        "scenario_request": scenario.model_dump(mode="json"),
        "context": context.model_dump(mode="json"),
        "bills": [bill.model_dump(mode="json") for bill in simulation.bill_outcomes],
        "income_losses": [loss.model_dump(mode="json") for loss in simulation.income_lost_by_payday],
    }
    return hashlib.sha256(json.dumps(fingerprint_data, sort_keys=True).encode()).hexdigest()


def run_research(
    request: ResearchRequest, settings: Settings, *, gemini=None, serp=None
) -> ResearchResponse:
    snapshot = get_snapshot(
        settings=settings,
        display_name=request.scenario.display_name.strip(),
        hourly_rate_cents=request.scenario.hourly_rate_cents,
        repair_quote_cents=request.scenario.repair_quote_cents,
    )
    simulation = simulate(snapshot, request.scenario, actions=[])
    demo_transit_evidence = maya_route_5_fixture(
        request.scenario.display_name, request.context, simulation
    )
    fingerprint = research_fingerprint(
        simulation=simulation, scenario=request.scenario, context=request.context
    )
    now = datetime.now(UTC)
    cached = _research_cache.get(fingerprint)
    if (
        cached
        and not request.force_refresh
        and (now - cached[0]).total_seconds() < settings.research_cache_ttl_seconds
    ):
        return ResearchResponse(
            snapshot=snapshot,
            simulation=simulation,
            research=cached[1].model_copy(update={"cache_hits": cached[1].cache_hits + 1}),
        )
    targets, warnings = rank_targets(simulation)
    started = now
    if not settings.gemini_api_key or not settings.serpapi_api_key:
        missing = [
            name
            for name, present in (
                ("GEMINI_API_KEY", settings.gemini_api_key),
                ("SERPAPI_API_KEY", settings.serpapi_api_key),
            )
            if not present
        ]
        result = ResearchResult(
            status="not_configured",
            run_id=str(uuid4()),
            simulation_fingerprint=fingerprint,
            research_started_at=started,
            research_finished_at=datetime.now(UTC),
            priority_targets=targets,
            research_events=[],
            evidence=demo_transit_evidence,
            candidate_actions=[],
            clarifying_questions=[],
            tool_calls_used=0,
            cache_hits=0,
            warnings=warnings
            + [f"Configure {', '.join(missing)} in ignored backend/.env to run research."],
        )
        return ResearchResponse(snapshot=snapshot, simulation=simulation, research=result)
    serp_client = serp or SerpResearch(
        settings.serpapi_api_key,
        max_calls=settings.research_max_calls
        if not request.force_refresh
        else settings.research_rerun_max_calls,
    )
    try:
        evidence, candidates, questions, events, pathways, agent_warnings, hypotheses, meta = (
            research_with_agent(
                simulation=simulation,
                context=request.context,
                targets=targets,
                gemini=gemini or LiveGemini(settings.gemini_api_key, settings.gemini_model),
                serp=serp_client,
                max_iterations=settings.research_max_iterations,
                deadline_seconds=settings.research_deadline_seconds,
            )
        )
    except Exception:  # noqa: BLE001 - never expose provider exceptions or credentials to the API
        evidence, candidates, questions, events, pathways, agent_warnings, hypotheses, meta = (
            [],
            [],
            [],
            [],
            [],
            ["Research provider failed; retry later."],
            [],
            ResearchRunMeta(hypothesis_outcomes=[], extraction_diagnostics=[]),
        )
    finally:
        if serp is None:
            serp_client.close()
    # The deterministic fixture is deliberately first: live Maps output is kept
    # for research, but cannot replace the fixed hackathon-demo assumptions.
    evidence = [*demo_transit_evidence, *evidence]
    grounded = any(
        candidate.verification_status not in {"hypothesis", "unverified"}
        for candidate in candidates
    )
    blocking_agent_warnings = [
        warning
        for warning in agent_warnings
        if not warning.startswith("Gemini extraction failed twice")
    ]
    status = (
        "completed"
        if evidence and grounded and not blocking_agent_warnings
        else "partial"
        if evidence
        else "failed"
        if agent_warnings
        else "no_results"
    )
    result = ResearchResult(
        status=status,
        run_id=str(uuid4()),
        simulation_fingerprint=fingerprint,
        research_started_at=started,
        research_finished_at=datetime.now(UTC),
        priority_targets=targets,
        hypotheses=hypotheses,
        pathways=pathways,
        research_events=events,
        evidence=evidence,
        candidate_actions=candidates,
        hypothesis_outcomes=meta.hypothesis_outcomes,
        extraction_diagnostics=meta.extraction_diagnostics,
        clarifying_questions=questions,
        initial_question_ids=[question.id for question in questions[:2]],
        tool_calls_used=serp_client.calls,
        cache_hits=serp_client.cache_hits,
        warnings=warnings
        + agent_warnings
        + (
            ["Sources were found, but no candidate met validation requirements."]
            if evidence and not candidates
            else []
        ),
    )
    if result.status in {"completed", "partial", "no_results"}:
        if len(_research_cache) >= 128:
            oldest = min(_research_cache, key=lambda key: _research_cache[key][0])
            _research_cache.pop(oldest, None)
        _research_cache[fingerprint] = (datetime.now(UTC), result)
    return ResearchResponse(snapshot=snapshot, simulation=simulation, research=result)
