import hashlib
import json
from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta
from itertools import combinations
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.config import Settings
from app.financial_analysis import analyze_financial_opportunities
from app.models import CustomerSnapshot
from app.recovery_models import (
    CandidateSummary,
    CreateRecoverySessionRequest,
    EvaluateRecoveryRequest,
    OutreachDraft,
    PlanDelta,
    PlanReconciliation,
    PlanResource,
    PlanSource,
    PlanTimelineEvent,
    RecoveryActionDefinition,
    RecoveryAnswer,
    RecoveryEvaluation,
    RecoveryPlan,
    RecoveryQuestion,
    RecoveryRequirement,
    RecoverySession,
    RequirementUpdateRequest,
    StoredRecoverySession,
    SubmitAnswerRequest,
    TargetedResearchResult,
)
from app.research_models import Evidence, ResearchResult
from app.research_serpapi import SearchBudgetExceeded, SearchFailure, SerpResearch
from app.research_service import research_fingerprint
from app.simulation import simulate
from app.simulation_models import (
    AlternativeRepairQuoteEffect,
    BillDueDateEffect,
    BillReductionEffect,
    ExpenseEffect,
    PreserveShiftEffect,
    RecoveryEffect,
)
from app.snapshot import get_snapshot


class RecoverySessionNotFound(LookupError):
    pass


class RecoveryVersionConflict(ValueError):
    pass


_sessions: dict[str, StoredRecoverySession] = {}
_targeted_cache: dict[str, list[Evidence]] = {}


def _money(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    return f"{sign}${abs(cents) / 100:,.2f}"


def _fingerprint(snapshot: CustomerSnapshot, scenario: object) -> str:
    payload = {
        "customer": snapshot.customer.id,
        "accounts": [(item.id, item.balance_cents) for item in snapshot.accounts],
        "bills": [item.model_dump(mode="json") for item in snapshot.upcoming_bills],
        "scenario": scenario.model_dump(mode="json"),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _requirement(
    requirement_id: str, candidate_id: str, condition: str
) -> RecoveryRequirement:
    return RecoveryRequirement(
        id=requirement_id,
        candidate_ids=[candidate_id],
        condition=condition,
    )


def _remote_draft(shift_dates: list[date], *, sender_name: str, inquiry: bool = False, equipment_confirmed: bool = False) -> OutreachDraft:
    listed = ", ".join(value.strftime("%A, %B %-d") for value in shift_dates)
    return OutreachDraft(
        id="draft-remote-work",
        candidate_id="action-remote-work",
        kind="remote_work_request",
        recipient="[Manager's Name]",
        subject="Question about temporary remote-work options" if inquiry else "Temporary remote-work request",
        body=(
            "Hello [Manager's Name],\n\nI wanted to reach out about a temporary transportation issue. "
            "My car is currently unavailable, and I am working to resolve it as quickly as I can. "
            + ("Could you let me know whether temporary remote work is permitted for " if inquiry else "Would you consider approving temporary remote work for ")
            + f"{listed}? My goal is to avoid any interruption to my schedule or responsibilities.\n\n"
            "I would remain available throughout my normal 8:00 AM–4:00 PM shift and continue handling my usual work and communications. "
            + ("I have the equipment and system access I need. " if equipment_confirmed else "Please let me know whether there are equipment, system-access, or security requirements I would need to arrange. ")
            + "If remote work is not available, I would also appreciate discussing any shift adjustment that might help me keep these hours.\n\n"
            "Thank you for considering this. Please let me know whether this could be possible and what next steps or approvals are needed.\n\n"
            f"Best,\n{sender_name}"
        ),
    )


def _bill_draft(name: str, due_date: date, amount_cents: int, *, sender_name: str) -> OutreachDraft:
    return OutreachDraft(
        id=f"draft-extension-{name.casefold().replace(' ', '-')}",
        candidate_id="action-rent-extension",
        kind="bill_extension_request",
        recipient="[Property Manager's Name]",
        subject=f"Request to discuss a short extension for {name}",
        body=(
            "Hello [Property Manager's Name],\n\n"
            "I'm writing because a temporary transportation problem has caused an unexpected disruption to my work income. "
            f"My {_money(amount_cents)} {name.lower()} payment is currently due on {due_date:%B %-d}, and I want to communicate early and make a responsible plan for the full amount.\n\n"
            "Would [Company / Property Name] be willing to offer a short extension, grace period, or payment arrangement? "
            "I am not asking for the balance to be waived. I am working to bridge the timing between this bill and my next available paycheck, and I would be grateful to understand what arrangements may be available.\n\n"
            "If an arrangement is possible, please send the new due date, any fees, and the complete terms in writing so I can make sure I follow them correctly. "
            "Thank you for your time and consideration.\n\n"
            f"Sincerely,\n{sender_name}"
        ),
    )


def _base_questions() -> list[RecoveryQuestion]:
    return [
        RecoveryQuestion(
            id="question-remote-possible",
            prompt="Could remote work be personally possible while the car is unavailable?",
            answer_type="yes_no",
            reason="If approved later, remote work could preserve specific shifts without a commute.",
            requirement_ids=["remote_personally_possible"],
            candidate_ids=["action-remote-work"],
            priority_score=27,
        ),
        RecoveryQuestion(
            id="question-transit-usable",
            prompt="Would you be able to take Route 5 to work on the listed days?",
            answer_type="yes_no",
            reason="The Route 5 schedule and fare are a synthetic demo assumption; Maya's personal ability to use it remains separate.",
            requirement_ids=["transit_personally_usable"],
            candidate_ids=["action-transit-route-5"],
            priority_score=26,
        ),
        RecoveryQuestion(
            id="question-rent-considered",
            prompt="Would you be willing to ask the landlord for a short rent extension?",
            answer_type="yes_no",
            reason="An agreed date change could release cash for the repair, but willingness is not approval.",
            requirement_ids=["rent_extension_approval"],
            candidate_ids=["action-rent-extension"],
            priority_score=18,
        ),
        RecoveryQuestion(
            id="question-subscription-pause",
            prompt="Can the upcoming streaming subscription be cancelled before it renews?",
            answer_type="yes_no",
            reason="Confirmed cancellation removes only the scheduled discretionary charge.",
            requirement_ids=["subscription_cancellation"],
            candidate_ids=["action-pause-subscription"],
            priority_score=12,
        ),
        RecoveryQuestion(
            id="question-written-quote",
            prompt="Do you have a written alternative repair quote? Enter its dollar amount, or leave this unanswered.",
            answer_type="number",
            reason="Only an actual user-reported quote can replace the $400 repair exposure.",
            requirement_ids=["written_repair_quote"],
            candidate_ids=["action-alternative-repair"],
            priority_score=12,
        ),
        RecoveryQuestion(
            id="question-remote-equipment",
            prompt="Do you have the equipment and system access needed to work remotely?",
            answer_type="yes_no",
            reason="Personal possibility is not enough without usable equipment and access.",
            requirement_ids=["remote_equipment"],
            candidate_ids=["action-remote-work"],
            priority_score=27,
            depends_on_question_id="question-remote-possible",
            active=False,
        ),
        RecoveryQuestion(
            id="question-remote-approved",
            prompt="Has your manager approved remote work for the listed at-risk shifts?",
            answer_type="yes_no",
            reason="Only this confirmation can move employer approval beyond pending status.",
            requirement_ids=["remote_manager_approval"],
            candidate_ids=["action-remote-work"],
            priority_score=27,
            depends_on_question_id="question-remote-possible",
            active=False,
        ),
        RecoveryQuestion(
            id="question-rent-approved",
            prompt="Has the landlord actually agreed to an extension?",
            answer_type="yes_no",
            reason="A request or proposed date is not an approved payment arrangement.",
            requirement_ids=["rent_extension_approval"],
            candidate_ids=["action-rent-extension"],
            priority_score=27,
            depends_on_question_id="question-rent-considered",
            active=False,
        ),
        RecoveryQuestion(
            id="question-rent-new-date",
            prompt="If the landlord agreed, what is the exact new rent due date?",
            answer_type="date",
            reason="A dated agreement moves the obligation; it does not erase rent.",
            requirement_ids=["rent_extension_approval"],
            candidate_ids=["action-rent-extension"],
            priority_score=27,
            depends_on_question_id="question-rent-approved",
            active=False,
        ),
        RecoveryQuestion(
            id="question-repair-appointment",
            prompt="What is the earliest confirmed appointment date for that written quote?",
            answer_type="date",
            reason="A lower quote cannot restore the vehicle before the shop can perform the repair.",
            requirement_ids=["repair_appointment"],
            candidate_ids=["action-alternative-repair"],
            priority_score=18,
            depends_on_question_id="question-written-quote",
            active=False,
        ),
    ]


def _transit_actions(
    baseline: object, evidence: list[Evidence]
) -> tuple[list[RecoveryActionDefinition], list[RecoveryRequirement]]:
    actions: list[RecoveryActionDefinition] = []
    requirements: list[RecoveryRequirement] = []
    for shift in baseline.shift_records:
        if shift.attendance != "projected_missed":
            continue
        day_evidence = [
            item
            for item in evidence
            if item.source_type == "transit_directions" and item.transit_request_date == shift.date
        ]
        outbound = next(
            (
                item
                for item in day_evidence
                if item.transit_request_kind == "arrive_by"
                and item.transit_arrival
                and item.transit_arrival.replace(tzinfo=None) <= shift.scheduled_start_local
                and item.transit_time_constraint_honored is True
                and item.transit_origin_matches is True
                and item.transit_destination_matches is True
            ),
            None,
        )
        returning = next(
            (
                item
                for item in day_evidence
                if item.transit_request_kind == "depart_at"
                and item.transit_departure
                and item.transit_departure.replace(tzinfo=None) >= shift.scheduled_end_local
                and item.transit_time_constraint_honored is True
                and item.transit_origin_matches is True
                and item.transit_destination_matches is True
            ),
            None,
        )
        if not outbound or not returning:
            continue
        costs = [outbound.observed_cost_cents, returning.observed_cost_cents]
        if any(value is None for value in costs):
            action_id = f"action-transit-lead-{shift.date.isoformat()}"
            requirement_id = "transit_fare_known"
            requirements.append(_requirement(requirement_id, action_id, "A supported fare assumption is available for both journeys."))
            actions.append(RecoveryActionDefinition(
                id=action_id,
                title=f"Investigate the verified transit timing on {shift.date:%b %-d}",
                strategy="transportation",
                description="Timing covers this shift, but one or more fares are unresolved; confirm the applicable CapMetro fare before counting a financial benefit.",
                effects=[], requirement_ids=[requirement_id], evidence_ids=[outbound.id, returning.id],
                next_steps=["Confirm the published or provider-observed fare for both journeys."], quantified=False,
                evidence_status="insufficient_schedule_evidence",
            ))
            continue
        is_demo_assumption = (
            outbound.fare_certainty == "demo_scenario_assumption"
            and returning.fare_certainty == "demo_scenario_assumption"
        )
        action_id = f"action-transit-{shift.date.isoformat()}"
        requirement_id = "transit_personally_usable"
        requirements.append(
            _requirement(
                requirement_id,
                action_id,
                "Maya reports that she can use this Route 5 itinerary.",
            )
        )
        total = sum(value or 0 for value in costs)
        actions.append(
            RecoveryActionDefinition(
                id=action_id,
                title=(
                    f"Use demo Route 5 round trip on {shift.date:%b %-d}"
                    if is_demo_assumption
                    else f"Use the verified transit round trip on {shift.date:%b %-d}"
                ),
                strategy="transportation",
                description=(
                    "Synthetic demo assumption: Route 5 departs 07:35, arrives near work at 07:52, and has a 16:17 return departure. "
                    "The $2.50 round trip is modeled only if Maya confirms she can use it."
                    if is_demo_assumption
                    else "Provider-backed outbound and return timing covers this exact shift; personal usability remains unconfirmed."
                ),
                effects=[
                    PreserveShiftEffect(
                        effect_id=f"effect-transit-shift-{shift.date.isoformat()}",
                        action_id=action_id,
                        shift_ids=[shift.id],
                        requirement_ids=[requirement_id],
                        evidence_ids=[outbound.id, returning.id],
                        certainty="conditional" if is_demo_assumption else "provider_observed",
                    ),
                    ExpenseEffect(
                        effect_id=f"effect-transit-cost-{shift.date.isoformat()}",
                        action_id=action_id,
                        ledger_id=f"transit-cost-{shift.date.isoformat()}",
                        amount_cents=total,
                        date=shift.date,
                        description=(
                            f"Demo Route 5 round-trip fare for {shift.date.isoformat()}"
                            if is_demo_assumption
                            else f"Provider-observed transit fare for {shift.date.isoformat()}"
                        ),
                        supported_shift_ids=[shift.id],
                        charge_only_when_needed_for_supported_shift=True,
                        requirement_ids=[requirement_id],
                        evidence_ids=[outbound.id, returning.id],
                        certainty="conditional" if is_demo_assumption else "provider_observed",
                    ),
                ],
                requirement_ids=[requirement_id],
                evidence_ids=[outbound.id, returning.id],
                next_steps=(
                    ["Confirm personal ability to use Route 5.", "Use the linked map only as a manual navigation aid; recheck service before travel."]
                    if is_demo_assumption
                    else ["Confirm personal ability to use this itinerary.", "Recheck service alerts before travel."]
                ),
                evidence_status="demo_scenario_assumption" if is_demo_assumption else "verified_route_feasible",
            )
        )
    # The deterministic fixture is one offered commute strategy, not a set of
    # one-day recommendations. Its preserve/expense effects remain dated.
    demo_actions = [action for action in actions if action.evidence_status == "demo_scenario_assumption"]
    if demo_actions:
        action_id = "action-transit-route-5"
        demo_effects = [effect for action in demo_actions for effect in action.effects]
        demo_evidence_ids = list(dict.fromkeys(
            evidence_id for action in demo_actions for evidence_id in action.evidence_ids
        ))
        actions = [action for action in actions if action not in demo_actions]
        actions.append(RecoveryActionDefinition(
            id=action_id,
            title="Use demo CapMetro Route 5 while the car is unavailable",
            strategy="transportation",
            description=(
                "Synthetic demo assumption: Route 5 departs at 07:35, arrives near work at 07:52, "
                "and has a 16:17 return departure. Each used round trip costs $2.50. "
                "Fares stop after repair and are skipped on remote-work days."
            ),
            effects=[effect.model_copy(update={"action_id": action_id}) for effect in demo_effects],
            requirement_ids=["transit_personally_usable"],
            evidence_ids=demo_evidence_ids,
            next_steps=[
                "Confirm personal ability to use Route 5 on the listed weekday shifts.",
                "Use Route 5 only while the vehicle remains unavailable.",
                "Map links are navigation aids; the schedule and fare are demo assumptions.",
            ],
            evidence_status="demo_scenario_assumption",
        ))
        requirements = [
            requirement.model_copy(update={"candidate_ids": [action_id]})
            if requirement.id == "transit_personally_usable" else requirement
            for requirement in requirements
        ]

    deduped: dict[str, RecoveryRequirement] = {}
    for requirement in requirements:
        existing = deduped.get(requirement.id)
        if existing:
            existing.candidate_ids = list(
                dict.fromkeys([*existing.candidate_ids, *requirement.candidate_ids])
            )
        else:
            deduped[requirement.id] = requirement
    return actions, list(deduped.values())


def _initial_actions(
    snapshot: CustomerSnapshot, baseline: object, research: ResearchResult | None
) -> tuple[list[RecoveryActionDefinition], list[RecoveryRequirement]]:
    missed = [item for item in baseline.shift_records if item.attendance == "projected_missed"]
    remote_shifts = missed[:5]
    actions: list[RecoveryActionDefinition] = []
    requirements = [
        _requirement("remote_personally_possible", "action-remote-work", "Remote work is personally possible."),
        _requirement("remote_equipment", "action-remote-work", "Required work equipment and access are available."),
        _requirement("remote_manager_approval", "action-remote-work", "The manager approves remote work for the specified dates."),
        _requirement("subscription_cancellation", "action-pause-subscription", "The subscription cancellation is effective before renewal."),
        _requirement("rent_extension_approval", "action-rent-extension", "The landlord agrees to a specific new due date."),
        _requirement("written_repair_quote", "action-alternative-repair", "A written alternative quote amount is available."),
        _requirement("repair_appointment", "action-alternative-repair", "A repair appointment date is available."),
    ]
    if remote_shifts:
        actions.append(
            RecoveryActionDefinition(
                id="action-remote-work",
                title=f"Work remotely for {len(remote_shifts)} at-risk shifts",
                strategy="income_preservation",
                description="Conditional simulation only: these shifts are preserved if equipment and manager approval are confirmed.",
                effects=[
                    PreserveShiftEffect(
                        effect_id="effect-remote-work-shifts",
                        action_id="action-remote-work",
                        shift_ids=[item.id for item in remote_shifts],
                        requirement_ids=["remote_personally_possible", "remote_equipment", "remote_manager_approval"],
                        certainty="conditional",
                    )
                ],
                requirement_ids=["remote_personally_possible", "remote_equipment", "remote_manager_approval"],
                next_steps=["Confirm equipment and access.", "Obtain manager approval for the listed dates."],
            )
        )
    streaming = next(
        (bill for bill in snapshot.upcoming_bills if bill.category == "Subscriptions"), None
    )
    if streaming:
        actions.append(
            RecoveryActionDefinition(
                id="action-pause-subscription",
                title=f"Cancel {streaming.name} before renewal",
                strategy="cash_preservation",
                description="Removes only the scheduled discretionary charge if cancellation is confirmed before renewal.",
                effects=[
                    BillReductionEffect(
                        effect_id="effect-pause-subscription",
                        action_id="action-pause-subscription",
                        obligation_id=streaming.id,
                        reduction_cents=streaming.amount_cents,
                        effective_date=streaming.due_date,
                        requirement_ids=["subscription_cancellation"],
                        certainty="conditional",
                    )
                ],
                requirement_ids=["subscription_cancellation"],
                next_steps=["Cancel before the renewal date and retain confirmation."],
            )
        )
    transit, transit_requirements = _transit_actions(
        baseline, research.evidence if research else []
    )
    actions.extend(transit)
    requirements.extend(transit_requirements)
    if research:
        evidence_by_id = {item.id: item for item in research.evidence}
        for candidate in research.candidate_actions:
            # The deterministic remote-work family already owns this mechanism;
            # retain its research provenance on that action instead of exposing
            # a duplicate unquantified "21 shifts" lead.
            if candidate.mechanism == "income_preservation":
                remote = next((item for item in actions if item.id == "action-remote-work"), None)
                if remote:
                    remote.evidence_ids = list(dict.fromkeys([*remote.evidence_ids, *candidate.evidence_ids]))
                    remote.next_steps = list(dict.fromkeys([*remote.next_steps, *candidate.remaining_unknowns]))
                    continue
            if candidate.mechanism == "repair_affordability":
                cited = [
                    evidence_by_id[item]
                    for item in candidate.evidence_ids
                    if item in evidence_by_id
                ]
                place_ids = {item.id for item in cited if item.source_type == "place"}
                if not any(
                    item.source_type == "place_review"
                    and item.positive_price_review_snippets
                    and item.parent_place_evidence_id in place_ids
                    for item in cited
                ):
                    continue
            action_id = f"investigate-{candidate.id}"
            if any(item.id == action_id for item in actions):
                continue
            strategy = {
                "transportation": "transportation",
                "income_preservation": "income_preservation",
                "repair_affordability": "repair_affordability",
                "bill_flexibility": "bill_flexibility",
                "budget_adjustment": "cash_preservation",
                "assistance": "assistance",
                "borrowing_risk": "borrowing",
            }[candidate.mechanism]
            actions.append(
                RecoveryActionDefinition(
                    id=action_id,
                    title=candidate.title,
                    strategy=strategy,  # type: ignore[arg-type]
                    description=(
                        f"Research lead only: {candidate.description} "
                        f"Missing before simulation: {', '.join(candidate.remaining_unknowns) or 'a dated executable effect'}."
                    ),
                    effects=[],
                    evidence_ids=candidate.evidence_ids,
                    next_steps=["Run targeted research or obtain the missing confirmation before quantifying this option."],
                    quantified=False,
                )
            )
    return actions, requirements


def _requirement_map(session: RecoverySession) -> dict[str, RecoveryRequirement]:
    return {item.id: item for item in session.requirements}


def _candidate_summary(
    actions: list[RecoveryActionDefinition], research: ResearchResult | None
) -> CandidateSummary:
    researched = research.candidate_actions if research else []
    quantified = [item for item in actions if item.quantified]
    conditional = [item for item in quantified if item.requirement_ids]
    return CandidateSummary(
        total_research_candidates=len(researched),
        executable_actions=len(quantified),
        conditional_executable_actions=len(conditional),
        unquantified_leads=sum(not item.quantified for item in actions),
        blocked_candidates=sum(1 for item in (research.hypothesis_outcomes if research else []) if item.status == "blocked"),
    )


def _actionable_resources(research: ResearchResult | None) -> list[PlanResource]:
    if not research:
        return []
    evidence = {item.id: item for item in research.evidence}
    resources: list[PlanResource] = []
    for candidate in research.candidate_actions:
        for evidence_id in candidate.evidence_ids:
            item = evidence.get(evidence_id)
            if not item:
                continue
            kind = "transit_route" if item.source_type == "transit_directions" else "external_link"
            resources.append(PlanResource(
                id=f"opportunity:{candidate.id}:{item.id}", resource_type=kind,
                title=item.title, action_ids=[candidate.id], evidence_ids=[item.id], url=item.url,
                date=item.transit_request_date,
                details=candidate.description,
                limitations=[*item.limitations, *candidate.remaining_unknowns],
            ))
    return resources


def _action_feasibility(
    action_ids: Iterable[str], actions: dict[str, RecoveryActionDefinition], requirements: dict[str, RecoveryRequirement]
) -> tuple[str, list[str]]:
    ids = list(dict.fromkeys(req for action_id in action_ids for req in actions[action_id].requirement_ids))
    states = [requirements[item].status for item in ids if item in requirements]
    unresolved = [item for item in ids if requirements[item].status not in {"possible", "user_reported_confirmed", "externally_verified"}]
    if any(state == "rejected" for state in states):
        return "blocked", unresolved
    if any(state == "pending_external_approval" for state in states):
        return "conditional_pending_approval", unresolved
    if any(state in {"unknown", "expired"} for state in states):
        return "conditional_pending_information", unresolved
    return "ready_with_confirmed_conditions", unresolved


def _effects(actions: Iterable[RecoveryActionDefinition]) -> list[RecoveryEffect]:
    return [effect for action in actions for effect in action.effects]


def _incremental_cost(effects: list[RecoveryEffect], result: object) -> int:
    # Conditional fares are included only when the simulator actually used the
    # itinerary; static effect summation would charge an unused transit ride.
    total = sum(
        -event.signed_amount_cents
        for event in result.events
        if event.type == "action_expense"
    )
    for effect in effects:
        if isinstance(effect, ExpenseEffect) and not effect.charge_only_when_needed_for_supported_shift:
            total += effect.amount_cents
        elif isinstance(effect, BillDueDateEffect):
            total += effect.fee_cents
    return total


def _plan_details(selected, action_ids, baseline, result, evidence, drafts):
    resources: list[PlanResource] = []
    for action in selected:
        for evidence_id in action.evidence_ids:
            item = evidence.get(evidence_id)
            if not item:
                continue
            resource_type = "transit_route" if item.source_type == "transit_directions" else "external_link"
            details = item.title
            if item.source_type == "transit_directions":
                routes = ", ".join(item.route_numbers) or "route unknown"
                if item.fare_certainty == "demo_scenario_assumption":
                    time_text = (
                        item.transit_departure.strftime("%I:%M %p").lstrip("0")
                        if item.transit_departure else "time unspecified"
                    )
                    arrival_text = (
                        item.transit_arrival.strftime("%I:%M %p").lstrip("0")
                        if item.transit_arrival else "return arrival unspecified"
                    )
                    details = f"Demo scenario assumption: {routes}; {time_text} → {arrival_text}; $1.25 one way, $2.50 round trip."
                else:
                    details = f"{routes}; fare {item.observed_cost_cents or 0} cents; {item.transit_duration_minutes or '?'} minutes"
            resources.append(PlanResource(
                id=f"resource:{action.id}:{item.id}", resource_type=resource_type,
                title=item.title, action_ids=[action.id], evidence_ids=[item.id], url=item.url,
                date=item.transit_request_date, details=details, limitations=item.limitations,
            ))
    for action in selected:
        if action.id in drafts:
            draft = drafts[action.id]
            resources.append(PlanResource(
                id=f"resource:draft:{draft.id}", resource_type="outreach_draft",
                title=draft.subject, action_ids=[action.id], details="Copyable draft; not sent or approved.",
                limitations=[draft.disclaimer],
            ))
    # A multi-day transit offer can contain effects beyond the date on which
    # repair restores the car. Only a recorded fare proves that transit was the
    # mechanism actually used for that shift; remote effects remain direct.
    used_transit_shift_ids = {
        f"shift-{event.date.isoformat()}"
        for event in result.events
        if event.type == "action_expense" and event.id.startswith("transit-cost-")
    }
    direct = sorted({
        shift_id
        for action in selected
        for effect in action.effects
        if isinstance(effect, PreserveShiftEffect)
        for shift_id in effect.shift_ids
        if action.strategy != "transportation" or shift_id in used_transit_shift_ids
    })
    baseline_missed = {item.id for item in baseline.shift_records if item.attendance == "projected_missed"}
    worked_after = {item.id for item in result.shift_records if item.attendance == "worked"}
    recovered = baseline_missed & worked_after
    indirect = sorted(recovered - set(direct))
    remaining = sorted(baseline_missed - recovered)
    before_pay = {item.payday: item.actual_projected_take_home_cents for item in baseline.payroll_records}
    after_pay = {item.payday: item.actual_projected_take_home_cents for item in result.payroll_records}
    payday_differences = {str(day): after_pay[day] - before_pay.get(day, 0) for day in after_pay if after_pay[day] != before_pay.get(day, 0)}
    direct_pay = sum(item.take_home_earning_potential_cents for item in baseline.shift_records if item.id in direct)
    total_pay = sum(payday_differences.values())
    indirect_earned = sum(
        item.take_home_earning_potential_cents
        for item in baseline.shift_records if item.id in indirect
    )
    additional_after_horizon = max(
        0,
        result.wage_accounting.earned_but_unpaid_cents
        - baseline.wage_accounting.earned_but_unpaid_cents,
    )
    timeline: list[PlanTimelineEvent] = [PlanTimelineEvent(date=baseline.scenario.scenario_start_date, event_type="decision", label="Review this recovery plan", action_ids=list(action_ids))]
    for shift in result.shift_records:
        if shift.id in recovered:
            timeline.append(PlanTimelineEvent(date=shift.date, event_type="shift", label=f"Shift protected/restored ({shift.date:%b %-d})", action_ids=list(action_ids)))
    for event in result.events:
        if event.type in {"paycheck", "bill_due", "repair_payment", "action_expense"}:
            event_type = "payday" if event.type == "paycheck" else "bill_due" if event.type == "bill_due" else "repair" if event.type == "repair_payment" else "expense"
            timeline.append(PlanTimelineEvent(date=event.date, event_type=event_type, label=event.description, action_ids=list(action_ids)))
    timeline.sort(key=lambda item: (item.event_date, item.event_type, item.label))
    gap = min(result.cashflow, key=lambda point: point.crisis_balance_cents, default=None)
    return resources, timeline, PlanReconciliation(
        direct_recovered_shift_ids=sorted(set(direct) & recovered), indirect_recovered_shift_ids=indirect,
        remaining_missed_shift_ids=remaining, direct_income_preserved_cents=max(0, direct_pay),
        indirect_income_preserved_cents=max(0, total_pay - direct_pay), total_income_preserved_cents=max(0, total_pay),
        direct_earned_take_home_cents=max(0, direct_pay),
        indirect_earned_take_home_cents=max(0, indirect_earned),
        additional_pay_received_cents=max(0, total_pay),
        additional_pay_after_horizon_cents=additional_after_horizon,
        payday_differences=payday_differences, unpaid_bills=result.unpaid_bills,
        worst_gap_date=gap.date if gap else None,
    )


def _evaluate(
    stored: StoredRecoverySession,
    *,
    max_actions: int = 3,
    max_candidates: int = 8,
) -> RecoveryEvaluation:
    session = stored.public
    baseline = simulate(stored.snapshot, session.scenario, actions=[])
    actions = {
        item.id: item
        for item in session.candidate_actions
        if item.quantified
    }
    actions = dict(list(actions.items())[:max_candidates])
    requirements = _requirement_map(session)
    evaluated: list[tuple[tuple, RecoveryPlan]] = []
    pruned = 0
    evidence = {item.id: item for item in session.evidence}
    drafts = {item.candidate_id: item for item in session.outreach_drafts}
    for size in range(1, min(max_actions, len(actions)) + 1):
        for action_ids_tuple in combinations(actions, size):
            action_ids = list(action_ids_tuple)
            selected = [actions[item] for item in action_ids]
            if any(
                other in action_ids
                for action in selected
                for other in action.incompatible_action_ids
            ):
                pruned += 1
                continue
            feasibility, unresolved = _action_feasibility(action_ids, actions, requirements)
            if feasibility == "blocked":
                pruned += 1
                continue
            effects = _effects(selected)
            try:
                result = simulate(stored.snapshot, session.scenario, actions=effects)
            except ValueError:
                pruned += 1
                continue
            baseline_missed = {item.id for item in baseline.shift_records if item.attendance == "projected_missed"}
            result_worked = {item.id for item in result.shift_records if item.attendance == "worked"}
            recovered = sorted(baseline_missed & result_worked)
            income_preserved = max(
                0,
                sum(item.take_home_lost_cents for item in baseline.income_lost_by_payday)
                - sum(item.take_home_lost_cents for item in result.income_lost_by_payday),
            )
            repair_change = None
            if result.repair_projection.modeled_payment_date:
                if baseline.repair_projection.modeled_payment_date:
                    repair_change = (
                        result.repair_projection.modeled_payment_date
                        - baseline.repair_projection.modeled_payment_date
                    ).days
                else:
                    repair_change = -(
                        baseline.scenario.forecast_end_date
                        - result.repair_projection.modeled_payment_date
                    ).days
            delta = PlanDelta(
                essential_unpaid_change_cents=result.unpaid_essential_total_cents - baseline.unpaid_essential_total_cents,
                peak_funding_gap_change_cents=result.peak_funding_gap_cents - baseline.peak_funding_gap_cents,
                ending_balance_change_cents=result.crisis_ending_balance_cents - baseline.crisis_ending_balance_cents,
                recovered_shift_ids=recovered,
                income_preserved_cents=income_preserved,
                additional_take_home_earned_cents=max(
                    0,
                    result.wage_accounting.earned_take_home_cents
                    - baseline.wage_accounting.earned_take_home_cents,
                ),
                additional_pay_received_cents=max(
                    0,
                    result.wage_accounting.pay_for_horizon_shifts_received_cents
                    - baseline.wage_accounting.pay_for_horizon_shifts_received_cents,
                ),
                additional_pay_after_horizon_cents=max(
                    0,
                    result.wage_accounting.earned_but_unpaid_cents
                    - baseline.wage_accounting.earned_but_unpaid_cents,
                ),
                incremental_cost_cents=_incremental_cost(effects, result),
                repair_date_change_days=repair_change,
            )
            source_ids = list(dict.fromkeys(item for action in selected for item in action.evidence_ids))
            plan_sources = [
                PlanSource(
                    evidence_id=item,
                    title=evidence[item].title,
                    url=evidence[item].url,
                    supports=evidence[item].facts_supported,
                    limitations=evidence[item].limitations,
                )
                for item in source_ids
                if item in evidence
            ]
            conditions = [requirements[item].condition for item in unresolved if item in requirements]
            labels = list(dict.fromkeys(action.strategy for action in selected))
            resources, timeline, reconciliation = _plan_details(
                selected, action_ids, baseline, result, evidence, drafts
            )
            plan_id = "plan-" + hashlib.sha256(
                f"{session.scenario_fingerprint}|{'|'.join(action_ids)}".encode()
            ).hexdigest()[:12]
            explanation = (
                f"Under the listed conditions, this recovers {len(recovered)} shift(s), adds "
                f"{_money(delta.additional_take_home_earned_cents)} of take-home earnings, and deposits "
                f"{_money(delta.additional_pay_received_cents)} of that additional pay by the forecast end. "
                f"Projected available cash ends at {_money(result.ending_liquid_cash_cents)} with "
                f"{_money(result.ending_outstanding_essential_cents)} of essential bills still outstanding."
            )
            feasibility_penalty = {
                "ready_with_confirmed_conditions": 0,
                "conditional_pending_approval": 15_000,
                "conditional_pending_information": 10_000,
            }[feasibility]
            impact_score = (
                delta.additional_take_home_earned_cents
                + max(0, baseline.ending_outstanding_essential_cents - result.ending_outstanding_essential_cents) * 2
                + max(0, result.net_cash_position_after_liabilities_cents - baseline.net_cash_position_after_liabilities_cents)
                - delta.incremental_cost_cents
                - feasibility_penalty
                - len(unresolved) * 2_500
            )
            plan = RecoveryPlan(
                id=plan_id,
                rank=1,
                name=" + ".join(action.title for action in selected),
                strategy_labels=labels,
                feasibility=feasibility,  # type: ignore[arg-type]
                conditional_label=(
                    "Ready using user-reported or externally verified conditions."
                    if feasibility == "ready_with_confirmed_conditions"
                    else "If the unresolved conditions succeed, this is the recalculated outcome."
                ),
                action_ids=action_ids,
                actions=selected,
                unresolved_requirement_ids=unresolved,
                conditional_assumptions=conditions,
                result=result,
                delta=delta,
                ranking_rationale=[
                    f"Feasibility: {feasibility.replace('_', ' ')}.",
                    f"Essential bills outstanding at forecast end: {_money(result.ending_outstanding_essential_cents)}.",
                    f"Peak scheduled-obligation funding gap: {_money(result.peak_funding_gap_cents)}.",
                    f"Recovered shifts: {len(recovered)}; transportation and action costs: {_money(delta.incremental_cost_cents)}.",
                ],
                ranking_score=impact_score,
                explanation=explanation,
                sources=plan_sources,
                outreach_drafts=[drafts[item] for item in action_ids if item in drafts],
                next_steps=list(dict.fromkeys(step for action in selected for step in action.next_steps)),
                resources=resources,
                timeline=timeline,
                reconciliation=reconciliation,
            )
            feasibility_order = {
                "ready_with_confirmed_conditions": 0,
                "conditional_pending_approval": 1,
                "conditional_pending_information": 2,
            }[feasibility]
            key = (
                -impact_score,
                feasibility_order,
                result.ending_outstanding_essential_cents,
                -delta.additional_take_home_earned_cents,
                result.peak_funding_gap_cents,
                len(unresolved),
                len(selected),
                action_ids,
            )
            evaluated.append((key, plan))
    evaluated.sort(key=lambda item: item[0])
    ranked = [
        plan.model_copy(update={"rank": index + 1})
        for index, (_, plan) in enumerate(evaluated)
    ]
    diverse: list[RecoveryPlan] = []
    strategy_signatures: set[tuple[str, ...]] = set()
    for plan in ranked:
        signature = tuple(sorted(plan.strategy_labels))
        if signature in strategy_signatures and len(diverse) >= 1:
            continue
        diverse.append(plan)
        strategy_signatures.add(signature)
        if len(diverse) == 8:
            break
    # A quantified transportation option is materially distinct from generic
    # cash/income plans. Preserve its actual rank even when the three-card
    # presentation cut would otherwise hide every Route 5 combination.
    if not any("transportation" in plan.strategy_labels for plan in diverse):
        transportation_plan = next(
            (plan for plan in ranked if "transportation" in plan.strategy_labels), None
        )
        if transportation_plan:
            if len(diverse) >= 8:
                diverse[-1] = transportation_plan
            else:
                diverse.append(transportation_plan)
    return RecoveryEvaluation(
        baseline_fingerprint=session.scenario_fingerprint,
        baseline=baseline,
        evaluated_plan_count=len(evaluated),
        pruned_combination_count=pruned,
        plans=diverse,
    )


def _answered(session: RecoverySession, question_id: str) -> RecoveryAnswer | None:
    return next((item for item in session.answers if item.question_id == question_id), None)


def _refresh_questions(session: RecoverySession) -> list[str]:
    questions: list[tuple[int, RecoveryQuestion]] = []
    answers = {item.question_id: item for item in session.answers}
    plan_relevance = {
        action_id: max(1, 4 - plan.rank)
        for plan in session.evaluation.plans
        for action_id in plan.action_ids
    }
    for question in session.questions:
        active = question.depends_on_question_id is None
        if question.depends_on_question_id:
            parent = answers.get(question.depends_on_question_id)
            active = bool(
                parent
                and parent.value is not False
                and parent.value != ""
                and parent.value != 0
            )
        question.active = active
        if active and question.id not in answers:
            score = question.priority_score + 3 * max(
                [plan_relevance.get(item, 0) for item in question.candidate_ids] or [0]
            )
            questions.append((score, question))
    questions.sort(key=lambda item: (-item[0], item[1].id))
    return [item.id for _, item in questions[:2]]


def create_session(request: CreateRecoverySessionRequest, settings: Settings) -> RecoverySession:
    snapshot = get_snapshot(
        settings=settings,
        display_name=request.scenario.display_name.strip(),
        hourly_rate_cents=request.scenario.hourly_rate_cents,
        repair_quote_cents=request.scenario.repair_quote_cents,
    )
    baseline = simulate(snapshot, request.scenario, actions=[])
    if request.research:
        expected_research_fingerprint = research_fingerprint(
            simulation=baseline,
            scenario=request.scenario,
            context=request.context,
        )
        if request.research.simulation_fingerprint != expected_research_fingerprint:
            raise ValueError(
                "The supplied Explore result belongs to a different scenario or work-location context. Run Explore again before planning."
            )
    fingerprint = _fingerprint(snapshot, request.scenario)
    actions, requirements = _initial_actions(snapshot, baseline, request.research)
    now = datetime.now(UTC)
    session_id = str(uuid4())
    empty_evaluation = RecoveryEvaluation(
        baseline_fingerprint=fingerprint,
        baseline=baseline,
        evaluated_plan_count=0,
        pruned_combination_count=0,
        plans=[],
    )
    rent = next(
        (item for item in snapshot.upcoming_bills if item.category == "Housing/Rent"),
        None,
    )
    initial_drafts = (
        [
            _bill_draft(
                rent.name,
                rent.due_date,
                rent.amount_cents,
                sender_name=request.scenario.display_name.strip(),
            )
        ]
        if rent
        else []
    )
    public = RecoverySession(
        id=session_id,
        scenario_fingerprint=fingerprint,
        research_run_id=request.research.run_id if request.research else None,
        research_context=request.context,
        scenario=request.scenario,
        version=1,
        created_at=now,
        updated_at=now,
        answers=[],
        requirements=requirements,
        candidate_actions=actions,
        questions=_base_questions(),
        next_question_ids=[],
        outreach_drafts=initial_drafts,
        evidence=request.research.evidence if request.research else [],
        research=request.research,
        financial_opportunities=analyze_financial_opportunities(snapshot),
        actionable_resources=_actionable_resources(request.research),
        candidate_summary=_candidate_summary(actions, request.research),
        evaluation=empty_evaluation,
        warnings=(
            []
            if request.research
            else ["Recovery planning is using deterministic built-in candidates because no research result was supplied."]
        ),
    )
    public.next_question_ids = _refresh_questions(public)
    stored = StoredRecoverySession(public=public, snapshot=snapshot, research=request.research)
    public.evaluation = _evaluate(stored)
    _sessions[session_id] = stored
    return public


def get_session(session_id: str) -> RecoverySession:
    stored = _sessions.get(session_id)
    if not stored:
        raise RecoverySessionNotFound("Recovery session was not found or the backend restarted.")
    return stored.public


def targeted_research(
    session_id: str,
    candidate_ids: list[str],
    version: int,
    settings: Settings,
    *,
    serp: SerpResearch | None = None,
) -> TargetedResearchResult:
    stored = _sessions.get(session_id)
    if not stored:
        raise RecoverySessionNotFound("Recovery session was not found or the backend restarted.")
    _check_version(stored, version)
    session = stored.public
    if not settings.serpapi_api_key and serp is None:
        raise ValueError("SERPAPI_API_KEY is required for targeted research.")
    remaining = max(0, settings.recovery_session_max_calls - session.research_calls_used)
    round_budget = min(settings.recovery_research_max_calls, remaining)
    if round_budget == 0:
        raise ValueError("This recovery session has reached its targeted research budget.")
    provider = serp or SerpResearch(settings.serpapi_api_key or "", max_calls=round_budget)
    calls_before = provider.calls
    cache_hits = 0
    new_evidence: list[Evidence] = []

    def search(tool: str, args: dict[str, str]) -> list[Evidence]:
        nonlocal cache_hits
        key = hashlib.sha256(
            json.dumps({"tool": tool, "args": args}, sort_keys=True).encode()
        ).hexdigest()
        if key in _targeted_cache:
            cache_hits += 1
            return _targeted_cache[key]
        results = provider.search(tool, args, max_attempts=1)
        _targeted_cache[key] = results
        return results

    selected = [item for item in session.candidate_actions if item.id in candidate_ids]
    try:
        for candidate in selected:
            if provider.calls - calls_before >= round_budget:
                break
            if candidate.strategy == "transportation":
                missed = [
                    shift
                    for shift in session.evaluation.baseline.shift_records
                    if shift.attendance == "projected_missed"
                ][:2]
                context = session.research_context
                if not all((context.home_location, context.work_location, context.shift_start_local, context.shift_end_local)):
                    continue
                zone = ZoneInfo(context.timezone)
                for shift in missed:
                    if provider.calls - calls_before >= round_budget:
                        break
                    arrival = datetime.combine(shift.date, context.shift_start_local, zone)
                    departure = datetime.combine(shift.date, context.shift_end_local, zone) + timedelta(minutes=15)
                    for args in (
                        {
                            "origin": context.home_location,
                            "destination": context.work_location,
                            "arrive_by_iso": arrival.isoformat(),
                            "reason": f"Targeted plan check for shift {shift.id}",
                        },
                        {
                            "origin": context.work_location,
                            "destination": context.home_location,
                            "depart_at_iso": departure.isoformat(),
                            "reason": f"Targeted return check for shift {shift.id}",
                        },
                    ):
                        if provider.calls - calls_before >= round_budget:
                            break
                        new_evidence.extend(search("find_transit", args))
            elif candidate.strategy == "repair_affordability":
                places = [
                    item
                    for item in session.evidence
                    if item.id in candidate.evidence_ids and item.provider_business_id
                ]
                for place in places[:1]:
                    new_evidence.extend(
                        search(
                            "search_reviews",
                            {
                                "data_id": place.provider_business_id or "",
                                "place_title": place.title,
                                "parent_evidence_id": place.id,
                                "reason": "Targeted affordability review check for recovery planning",
                            },
                        )
                    )
            elif candidate.strategy in {"bill_flexibility", "assistance"}:
                new_evidence.extend(
                    search(
                        "search_web",
                        {
                            "query": "official Austin rent payment extension or emergency assistance application",
                            "location": session.research_context.city,
                            "reason": "Resolve a recovery-plan bill flexibility dependency",
                        },
                    )
                )
    except (SearchFailure, SearchBudgetExceeded):
        session.warnings.append("Targeted research returned a provider error; existing evidence and plans were retained.")
    finally:
        if serp is None:
            provider.close()

    evidence_by_id = {item.id: item for item in [*session.evidence, *new_evidence]}
    session.evidence = list(evidence_by_id.values())
    existing_non_transit = [
        item
        for item in session.candidate_actions
        if item.strategy != "transportation" or item.id.startswith("investigate-")
    ]
    transit, transit_requirements = _transit_actions(
        session.evaluation.baseline, session.evidence
    )
    session.candidate_actions = existing_non_transit + transit
    req_map = _requirement_map(session)
    for requirement in transit_requirements:
        if requirement.id not in req_map:
            session.requirements.append(requirement)
    round_calls = provider.calls - calls_before
    session.research_calls_used += round_calls
    session.research_cache_hits += cache_hits + provider.cache_hits
    session.version += 1
    session.updated_at = datetime.now(UTC)
    session.evaluation = _evaluate(stored)
    return TargetedResearchResult(
        session=session,
        calls_used=round_calls,
        cache_hits=cache_hits + provider.cache_hits,
        message=(
            f"Targeted research added {len(new_evidence)} evidence record(s); "
            "existing answers and unrelated plans were preserved."
        ),
    )


def _check_version(stored: StoredRecoverySession, version: int) -> None:
    if stored.public.version != version:
        raise RecoveryVersionConflict(
            f"Session version {version} is stale; current version is {stored.public.version}."
        )


def _set_requirement(
    session: RecoverySession,
    requirement_id: str,
    status: str,
    *,
    source: str,
    established_by: str,
    effective_dates: list[date] | None = None,
) -> None:
    requirement = next((item for item in session.requirements if item.id == requirement_id), None)
    if not requirement:
        raise ValueError(f"Unknown requirement: {requirement_id}.")
    requirement.status = status  # type: ignore[assignment]
    requirement.source = source  # type: ignore[assignment]
    requirement.established_by_id = established_by
    requirement.effective_dates = effective_dates or []
    requirement.updated_at = datetime.now(UTC)


def _upsert_answer(session: RecoverySession, answer: RecoveryAnswer) -> None:
    session.answers = [item for item in session.answers if item.question_id != answer.question_id]
    session.answers.append(answer)


def _activate_remote_draft(session: RecoverySession) -> None:
    action = next((item for item in session.candidate_actions if item.id == "action-remote-work"), None)
    if not action:
        return
    effect = next((item for item in action.effects if isinstance(item, PreserveShiftEffect)), None)
    dates = [date.fromisoformat(item.removeprefix("shift-")) for item in effect.shift_ids] if effect else []
    equipment = next((item for item in session.requirements if item.id == "remote_equipment"), None)
    possible = next((item for item in session.requirements if item.id == "remote_personally_possible"), None)
    draft = _remote_draft(
        dates,
        sender_name=session.scenario.display_name,
        inquiry=possible is None or possible.status == "unknown",
        equipment_confirmed=equipment is not None and equipment.status == "user_reported_confirmed",
    )
    session.outreach_drafts = [item for item in session.outreach_drafts if item.id != draft.id]
    session.outreach_drafts.append(draft)


def submit_answer(
    session_id: str, request: SubmitAnswerRequest
) -> RecoverySession:
    stored = _sessions.get(session_id)
    if not stored:
        raise RecoverySessionNotFound("Recovery session was not found or the backend restarted.")
    _check_version(stored, request.session_version)
    session = stored.public
    question = next((item for item in session.questions if item.id == request.question_id), None)
    if not question:
        raise ValueError("Unknown recovery question.")
    answer = RecoveryAnswer(
        question_id=request.question_id,
        value=request.value,
        clarification=request.clarification,
    )
    _upsert_answer(session, answer)
    yes = request.value is True
    unresolved = request.value == "not_yet"
    if request.question_id == "question-remote-possible":
        _set_requirement(session, "remote_personally_possible", "possible" if yes else "unknown" if unresolved else "rejected", source="user_answer", established_by=answer.question_id)
        _set_requirement(session, "remote_manager_approval", "pending_external_approval" if yes else "unknown" if unresolved else "rejected", source="user_answer", established_by=answer.question_id)
        if yes or unresolved:
            _activate_remote_draft(session)
    elif request.question_id == "question-remote-equipment":
        _set_requirement(session, "remote_equipment", "user_reported_confirmed" if yes else "unknown" if unresolved else "rejected", source="user_confirmation", established_by=answer.question_id)
    elif request.question_id == "question-transit-usable":
        _set_requirement(
            session,
            "transit_personally_usable",
            "possible" if yes else "unknown" if unresolved else "rejected",
            source="user_answer",
            established_by=answer.question_id,
        )
    elif request.question_id == "question-remote-approved":
        action = next(item for item in session.candidate_actions if item.id == "action-remote-work")
        effect = next(item for item in action.effects if isinstance(item, PreserveShiftEffect))
        dates = [date.fromisoformat(item.removeprefix("shift-")) for item in effect.shift_ids]
        _set_requirement(session, "remote_manager_approval", "user_reported_confirmed" if yes else "pending_external_approval" if unresolved else "rejected", source="user_confirmation", established_by=answer.question_id, effective_dates=dates if yes else [])
    elif request.question_id == "question-subscription-pause":
        _set_requirement(session, "subscription_cancellation", "user_reported_confirmed" if yes else "unknown" if unresolved else "rejected", source="user_confirmation", established_by=answer.question_id)
    elif request.question_id == "question-rent-considered":
        _set_requirement(session, "rent_extension_approval", "pending_external_approval" if yes else "unknown" if unresolved else "rejected", source="user_answer", established_by=answer.question_id)
        if yes or unresolved:
            rent = next((item for item in stored.snapshot.upcoming_bills if item.category == "Housing/Rent"), None)
            if rent:
                draft = _bill_draft(rent.name, rent.due_date, rent.amount_cents, sender_name=session.scenario.display_name)
                session.outreach_drafts = [item for item in session.outreach_drafts if item.id != draft.id]
                session.outreach_drafts.append(draft)
        else:
            session.outreach_drafts = [
                item
                for item in session.outreach_drafts
                if item.candidate_id != "action-rent-extension"
            ]
    elif request.question_id == "question-rent-approved":
        _set_requirement(
            session,
            "rent_extension_approval",
            "possible" if yes else "pending_external_approval" if unresolved else "rejected",
            source="user_answer",
            established_by=answer.question_id,
        )
    elif request.question_id == "question-rent-new-date":
        new_date = date.fromisoformat(str(request.value))
        rent = next((item for item in stored.snapshot.upcoming_bills if item.category == "Housing/Rent"), None)
        if not rent:
            raise ValueError("No rent obligation is available to extend.")
        forecast_end = stored.snapshot.cash_flow.start_date + timedelta(
            days=session.scenario.forecast_horizon_days
        )
        if new_date > forecast_end:
            raise ValueError("The confirmed rent date must fall within the 30-day plan horizon.")
        effect = BillDueDateEffect(
            effect_id="effect-rent-extension",
            action_id="action-rent-extension",
            obligation_id=rent.id,
            original_due_date=rent.due_date,
            new_due_date=new_date,
            requirement_ids=["rent_extension_approval"],
            certainty="user_reported",
        )
        action = RecoveryActionDefinition(
            id="action-rent-extension",
            title=f"Move rent due date to {new_date:%b %-d}",
            strategy="bill_flexibility",
            description="User-reported landlord agreement moves the full rent obligation; it does not erase rent.",
            effects=[effect],
            requirement_ids=["rent_extension_approval"],
            next_steps=["Keep the written landlord agreement and pay the full rent by the new date."],
        )
        session.candidate_actions = [item for item in session.candidate_actions if item.id != action.id] + [action]
        _set_requirement(session, "rent_extension_approval", "user_reported_confirmed", source="user_confirmation", established_by=answer.question_id, effective_dates=[new_date])
    elif request.question_id == "question-written-quote":
        if unresolved:
            _set_requirement(session, "written_repair_quote", "unknown", source="user_answer", established_by=answer.question_id)
            session.version += 1
            session.updated_at = datetime.now(UTC)
            session.evaluation = _evaluate(stored)
            session.next_question_ids = _refresh_questions(session)
            return session
        dollars = int(request.value)
        if dollars <= 0:
            raise ValueError("Repair quote must be a positive dollar amount.")
        _set_requirement(session, "written_repair_quote", "user_reported_confirmed", source="user_confirmation", established_by=answer.question_id)
        session.questions = [
            item.model_copy(update={"active": True})
            if item.id == "question-repair-appointment"
            else item
            for item in session.questions
        ]
        action = RecoveryActionDefinition(
            id="action-alternative-repair",
            title=f"Use the user-reported ${dollars} written repair quote",
            strategy="repair_affordability",
            description="Conditional until an appointment date is supplied; review language alone never changes the quote.",
            effects=[AlternativeRepairQuoteEffect(effect_id="effect-alternative-repair", action_id="action-alternative-repair", quote_cents=dollars * 100, earliest_appointment_date=session.scenario.breakdown_date or stored.snapshot.cash_flow.start_date, requirement_ids=["written_repair_quote", "repair_appointment"], certainty="user_reported")],
            requirement_ids=["written_repair_quote", "repair_appointment"],
            next_steps=["Confirm the appointment and retain the written estimate."],
        )
        session.candidate_actions = [item for item in session.candidate_actions if item.id != action.id] + [action]
    elif request.question_id == "question-repair-appointment":
        if unresolved:
            _set_requirement(session, "repair_appointment", "unknown", source="user_answer", established_by=answer.question_id)
            session.version += 1
            session.updated_at = datetime.now(UTC)
            session.evaluation = _evaluate(stored)
            session.next_question_ids = _refresh_questions(session)
            return session
        appointment = date.fromisoformat(str(request.value))
        action = next((item for item in session.candidate_actions if item.id == "action-alternative-repair"), None)
        if not action:
            raise ValueError("Enter the written quote before its appointment date.")
        effect = next(item for item in action.effects if isinstance(item, AlternativeRepairQuoteEffect))
        action.effects = [effect.model_copy(update={"earliest_appointment_date": appointment})]
        _set_requirement(session, "repair_appointment", "user_reported_confirmed", source="user_confirmation", established_by=answer.question_id, effective_dates=[appointment])

    session.version += 1
    session.updated_at = datetime.now(UTC)
    session.evaluation = _evaluate(stored)
    session.next_question_ids = _refresh_questions(session)
    return session


def update_requirement(
    session_id: str, request: RequirementUpdateRequest
) -> RecoverySession:
    stored = _sessions.get(session_id)
    if not stored:
        raise RecoverySessionNotFound("Recovery session was not found or the backend restarted.")
    _check_version(stored, request.session_version)
    _set_requirement(stored.public, request.requirement_id, request.status, source=request.source, established_by=f"requirement-update-v{request.session_version}", effective_dates=request.effective_dates)
    stored.public.version += 1
    stored.public.updated_at = datetime.now(UTC)
    stored.public.evaluation = _evaluate(stored)
    stored.public.next_question_ids = _refresh_questions(stored.public)
    return stored.public


def evaluate_session(
    session_id: str, request: EvaluateRecoveryRequest
) -> RecoverySession:
    stored = _sessions.get(session_id)
    if not stored:
        raise RecoverySessionNotFound("Recovery session was not found or the backend restarted.")
    _check_version(stored, request.session_version)
    stored.public.evaluation = _evaluate(
        stored,
        max_actions=request.max_actions_per_plan,
        max_candidates=request.max_candidate_actions,
    )
    return stored.public
