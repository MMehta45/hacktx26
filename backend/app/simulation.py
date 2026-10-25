from collections import defaultdict
from collections.abc import Sequence
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.models import CustomerSnapshot, ForecastIncome, UpcomingBill
from app.simulation_models import (
    BillOutcome,
    CrisisSimulationRequest,
    FinancialEvent,
    IncomeLoss,
    ProblemEdge,
    ProblemNode,
    SimulationCashflowPoint,
    SimulationResult,
    SimulationScenario,
    SimulationSource,
)


def _multiply_basis_points(amount_cents: int, basis_points: int) -> int:
    return int(
        (Decimal(amount_cents) * Decimal(basis_points) / Decimal(10_000)).quantize(
            Decimal(1), rounding=ROUND_HALF_UP
        )
    )


def _default_shift_dates(start: date, count: int) -> list[date]:
    shifts: list[date] = []
    candidate = start
    while len(shifts) < count:
        if candidate.weekday() < 5:
            shifts.append(candidate)
        candidate += timedelta(days=1)
    return shifts


def _event_priority(event: FinancialEvent) -> tuple[date, int, str]:
    priorities = {
        "paycheck": 0,
        "borrowing": 1,
        "lost_wages": 2,
        "repair_payment": 3,
        "transport_cost": 3,
        "debt_payment": 3,
        "bill_due": 4 if event.essential else 5,
    }
    return (event.date, priorities[event.type], event.id)


def _deduplicate_bills(
    bills: Sequence[UpcomingBill], start: date, end: date
) -> tuple[list[UpcomingBill], list[str]]:
    unique: dict[str, UpcomingBill] = {}
    warnings: list[str] = []
    for bill in sorted(bills, key=lambda item: (item.due_date, item.id)):
        if bill.status.casefold() in {"paid", "completed"} or not start <= bill.due_date <= end:
            continue
        if bill.id in unique:
            warnings.append(f"Duplicate obligation {bill.id} was included only once.")
            continue
        unique[bill.id] = bill
    return list(unique.values()), warnings


def _find_pay_period(
    shift_date: date, forecast_entries: Sequence[ForecastIncome]
) -> ForecastIncome | None:
    return next(
        (
            entry
            for entry in forecast_entries
            if entry.work_period_start <= shift_date <= entry.work_period_end
        ),
        None,
    )


def _graph_edges() -> list[ProblemEdge]:
    definitions = (
        ("breakdown-unavailable", "car_breaks_down", "car_unavailable", None),
        ("unavailable-commute", "car_unavailable", "commute_disrupted", None),
        ("commute-work", "commute_disrupted", "missed_work", None),
        ("work-paycheck", "missed_work", "reduced_paycheck", None),
        ("paycheck-shortfall", "reduced_paycheck", "cash_shortfall", None),
        ("shortfall-bills", "cash_shortfall", "bills_unpaid", None),
        ("breakdown-repair", "car_breaks_down", "unexpected_repair_expense", None),
        (
            "repair-reserves",
            "unexpected_repair_expense",
            "cash_reserves_depleted",
            "only if repair is paid",
        ),
        ("reserves-shortfall", "cash_reserves_depleted", "cash_shortfall", None),
        (
            "commute-transport",
            "commute_disrupted",
            "extra_transportation_costs",
            "only if alternative transport is purchased",
        ),
        ("transport-shortfall", "extra_transportation_costs", "cash_shortfall", None),
        (
            "reserves-delay",
            "cash_reserves_depleted",
            "repair_delayed",
            "if repair cannot be completed",
        ),
        ("delay-unavailable", "repair_delayed", "car_unavailable", "over later days"),
        (
            "shortfall-borrowing",
            "cash_shortfall",
            "emergency_borrowing",
            "only if borrowing occurs",
        ),
        ("borrowing-debt", "emergency_borrowing", "future_debt_payments", None),
        ("debt-shortfall", "future_debt_payments", "cash_shortfall", "over later days"),
        ("bills-fees", "bills_unpaid", "late_fees", "only with a known fee schedule"),
    )
    return [
        ProblemEdge(id=edge_id, source=source, target=target, condition=condition)
        for edge_id, source, target, condition in definitions
    ]


def _graph_nodes(
    *,
    snapshot: CustomerSnapshot,
    request: CrisisSimulationRequest,
    scenario_start: date,
    shifts: list[date],
    income_losses: list[IncomeLoss],
    cashflow: list[SimulationCashflowPoint],
    unpaid_bills: list[BillOutcome],
    peak_gap_cents: int,
) -> list[ProblemNode]:
    lost_total = sum(item.take_home_lost_cents for item in income_losses)
    first_loss_date = min((item.payday for item in income_losses), default=None)
    first_shortfall_date = next(
        (point.date for point in cashflow if point.crisis_balance_cents < 0), None
    )
    first_unpaid_date = min((item.due_date for item in unpaid_bills), default=None)
    banking_source = "nessie" if snapshot.source.mode == "live" else "fixture"
    repair_paid = request.repair_payment_status == "paid"
    transport_incurred = request.transport_cost_cents > 0
    borrowed = request.borrowed_amount_cents > 0
    debt_scheduled = request.debt_payment_cents > 0
    missed_work = bool(shifts and lost_total)
    shortfall = peak_gap_cents > 0
    bill_failure = bool(unpaid_bills)
    repair_delayed = request.repair_payment_status in {"unpaid", "deferred"}

    return [
        ProblemNode(
            id="car_breaks_down",
            label="Car breaks down",
            description="The untreated scenario begins with a fictional vehicle breakdown.",
            status="projected",
            activation_date=scenario_start,
            evidence="Explicit scenario assumption; no bank transaction was created.",
            source="scenario_assumption",
        ),
        ProblemNode(
            id="car_unavailable",
            label="Car unavailable",
            description="The vehicle is assumed unavailable during the modeled repair delay.",
            status="projected",
            activation_date=scenario_start,
            evidence=f"Scenario assumes a {request.repair_delay_days}-day availability window.",
            source="scenario_assumption",
        ),
        ProblemNode(
            id="commute_disrupted",
            label="Commute disrupted",
            description="The unavailable car threatens Maya's weekday commute.",
            status="projected" if shifts else "inactive",
            activation_date=min(shifts) if shifts else None,
            evidence=f"{len(shifts)} explicit weekday shift(s) are affected.",
            source="scenario_assumption",
        ),
        ProblemNode(
            id="missed_work",
            label="Missed work",
            description="Affected shifts are modeled as missed in the untreated path.",
            status="projected" if missed_work else "inactive",
            activation_date=min(shifts) if missed_work else None,
            evidence=(
                f"{len(shifts)} shift(s) × {request.hours_per_shift} hours; dates are mapped "
                "to their covered pay periods."
            ),
            source="scenario_assumption",
        ),
        ProblemNode(
            id="reduced_paycheck",
            label="Reduced paycheck",
            description="Lost estimated take-home appears on the paycheck covering the missed shifts.",
            status="projected" if lost_total else "inactive",
            activation_date=first_loss_date,
            evidence="80% take-home estimate; historical Nessie deposits remain unchanged.",
            amount_cents=lost_total,
            source="projection",
        ),
        ProblemNode(
            id="cash_shortfall",
            label="Cash shortfall",
            description="The raw forecast requires funding below a zero-dollar balance.",
            status="projected" if shortfall else "inactive",
            activation_date=first_shortfall_date,
            evidence=(
                f"Starts from the {banking_source} balance and applies dated forecast events; "
                "a negative value is a required funding gap, not an actual overdraft."
            ),
            amount_cents=peak_gap_cents,
            source="projection",
        ),
        ProblemNode(
            id="bills_unpaid",
            label="Bills unpaid",
            description="Essential obligations cannot be fully funded on their due dates.",
            status="projected" if bill_failure else "inactive",
            activation_date=first_unpaid_date,
            evidence=(
                f"Constrained due-date allocation found {len(unpaid_bills)} essential "
                "obligation(s) with an uncovered amount."
            ),
            amount_cents=sum(item.unpaid_cents for item in unpaid_bills),
            source="projection",
        ),
        ProblemNode(
            id="unexpected_repair_expense",
            label="Unexpected repair expense",
            description="A repair quote exists as exposure, but is not automatically paid.",
            status="projected",
            activation_date=scenario_start,
            evidence=f"Repair status is {request.repair_payment_status}; quote is separate from cash flow.",
            amount_cents=request.repair_quote_cents,
            source="scenario_assumption",
        ),
        ProblemNode(
            id="cash_reserves_depleted",
            label="Cash reserves depleted",
            description="This branch activates only when the repair is actually paid.",
            status="projected" if repair_paid else "inactive",
            activation_date=request.repair_payment_date if repair_paid else None,
            evidence=(
                "A dated repair outflow is included."
                if repair_paid
                else "The quote is unpaid, so it removes $0 from checking."
            ),
            amount_cents=request.repair_quote_cents if repair_paid else 0,
            source="projection" if repair_paid else "scenario_assumption",
        ),
        ProblemNode(
            id="repair_delayed",
            label="Repair delayed",
            description="The car remains unavailable while the quoted repair is deferred.",
            status="projected" if repair_delayed else "inactive",
            activation_date=(
                scenario_start + timedelta(days=request.repair_delay_days)
                if repair_delayed
                else None
            ),
            evidence=(
                f"Explicit {request.repair_payment_status} status and "
                f"{request.repair_delay_days}-day delay assumption."
            ),
            source="scenario_assumption",
        ),
        ProblemNode(
            id="extra_transportation_costs",
            label="Extra transportation costs",
            description="Alternative transportation counts only when a dated cost is modeled.",
            status="projected" if transport_incurred else "inactive",
            activation_date=(request.transport_cost_date or scenario_start)
            if transport_incurred
            else None,
            evidence=(
                "A dated scenario cost is included."
                if transport_incurred
                else "Default untreated scenario uses $0 alternative transportation."
            ),
            amount_cents=request.transport_cost_cents,
            source="scenario_assumption",
        ),
        ProblemNode(
            id="emergency_borrowing",
            label="Emergency borrowing",
            description="Borrowing is a potential problem branch, not an assumed solution.",
            status="projected" if borrowed else "conditional",
            activation_date=(request.borrowing_date or scenario_start) if borrowed else None,
            evidence=(
                "A dated borrowing inflow is explicitly modeled."
                if borrowed
                else "Default borrowed amount is $0; no loan is asserted."
            ),
            amount_cents=request.borrowed_amount_cents,
            source="scenario_assumption",
        ),
        ProblemNode(
            id="future_debt_payments",
            label="Future debt payments",
            description="Repayment is relevant only when borrowing and a dated payment are modeled.",
            status="projected" if debt_scheduled else "conditional",
            activation_date=request.debt_payment_date if debt_scheduled else None,
            evidence=(
                "A dated debt payment is explicitly modeled."
                if debt_scheduled
                else "No borrowing repayment is included in the default cash flow."
            ),
            amount_cents=request.debt_payment_cents,
            source="scenario_assumption",
        ),
        ProblemNode(
            id="late_fees",
            label="Late fees",
            description="A missed bill may create fees, but no verified fee schedule is configured.",
            status="conditional" if bill_failure else "inactive",
            activation_date=None,
            evidence="No fee amount is invented or included in cash flow.",
            amount_cents=0,
            source="projection",
        ),
    ]


def simulate(
    snapshot: CustomerSnapshot,
    request: CrisisSimulationRequest,
    actions: Sequence[object] = (),
) -> SimulationResult:
    """Run the deterministic untreated projection without mutating the snapshot."""

    if actions:
        raise ValueError("Recovery actions are reserved for a later milestone.")

    start = request.scenario_start_date or snapshot.cash_flow.start_date
    if start != snapshot.cash_flow.start_date:
        raise ValueError("Scenario start date must match the loaded financial snapshot date.")
    end = start + timedelta(days=request.forecast_horizon_days)
    shifts = list(
        request.affected_shift_dates or _default_shift_dates(start, request.affected_shift_count)
    )
    if any(day.weekday() >= 5 for day in shifts):
        raise ValueError("Affected shifts must fall on Monday through Friday.")
    if any(day < start or day > end for day in shifts):
        raise ValueError("Affected shifts must fall inside the forecast horizon.")

    balance = sum(account.balance_cents for account in snapshot.accounts)
    bills, warnings = _deduplicate_bills(snapshot.upcoming_bills, start, end)
    forecast_entries = [
        entry
        for entry in snapshot.income_projection.forecast_entries
        if start <= entry.expected_payment_date <= end
    ]

    shifts_by_payday: dict[date, list[date]] = defaultdict(list)
    pay_entries: dict[date, ForecastIncome] = {
        entry.expected_payment_date: entry for entry in forecast_entries
    }
    for shift in shifts:
        entry = _find_pay_period(shift, forecast_entries)
        if entry is None:
            warnings.append(
                f"Affected shift {shift.isoformat()} has no forecast paycheck in the horizon."
            )
            continue
        shifts_by_payday[entry.expected_payment_date].append(shift)

    gross_per_shift = request.hourly_rate_cents * request.hours_per_shift
    take_home_per_shift = _multiply_basis_points(
        gross_per_shift, request.take_home_multiplier_basis_points
    )
    income_losses: list[IncomeLoss] = []
    for payday, shift_dates in sorted(shifts_by_payday.items()):
        entry = pay_entries[payday]
        requested_loss = take_home_per_shift * len(shift_dates)
        take_home_loss = min(requested_loss, entry.estimated_take_home_cents)
        income_losses.append(
            IncomeLoss(
                payday=payday,
                affected_shift_dates=sorted(shift_dates),
                gross_lost_cents=gross_per_shift * len(shift_dates),
                take_home_lost_cents=take_home_loss,
                normal_take_home_cents=entry.estimated_take_home_cents,
                crisis_take_home_cents=entry.estimated_take_home_cents - take_home_loss,
            )
        )

    events: list[FinancialEvent] = []
    for entry in forecast_entries:
        events.append(
            FinancialEvent(
                id=f"paycheck-{entry.expected_payment_date.isoformat()}",
                date=entry.expected_payment_date,
                type="paycheck",
                signed_amount_cents=entry.estimated_take_home_cents,
                description="Projected weekly take-home paycheck",
                source=entry.source,
                status="projected",
            )
        )
    for item in income_losses:
        events.append(
            FinancialEvent(
                id=f"lost-wages-{item.payday.isoformat()}",
                date=item.payday,
                type="lost_wages",
                signed_amount_cents=-item.take_home_lost_cents,
                description=f"Estimated take-home lost from {len(item.affected_shift_dates)} missed shift(s)",
                source="crisis_projection",
                status="projected",
            )
        )
    for bill in bills:
        events.append(
            FinancialEvent(
                id=f"bill-{bill.source}-{bill.id}",
                date=bill.due_date,
                type="bill_due",
                signed_amount_cents=-bill.amount_cents,
                description=f"{bill.name} due",
                source=bill.source,
                status="projected",
                provenance_id=bill.nessie_bill_id or bill.id,
                essential=bill.essential,
            )
        )

    def add_scenario_event(
        *, event_id: str, event_date: date | None, event_type: str, amount: int, description: str
    ) -> None:
        if amount == 0:
            return
        date_value = event_date or start
        if not start <= date_value <= end:
            warnings.append(
                f"{description} falls outside the forecast horizon and was not applied."
            )
            return
        signed_amount = amount if event_type == "borrowing" else -amount
        events.append(
            FinancialEvent(
                id=event_id,
                date=date_value,
                type=event_type,  # type: ignore[arg-type]
                signed_amount_cents=signed_amount,
                description=description,
                source="scenario_assumption",
                status="scenario_assumption",
            )
        )

    if request.repair_payment_status == "paid":
        add_scenario_event(
            event_id="repair-payment",
            event_date=request.repair_payment_date,
            event_type="repair_payment",
            amount=request.repair_quote_cents,
            description="Repair payment incurred",
        )
    add_scenario_event(
        event_id="transport-cost",
        event_date=request.transport_cost_date,
        event_type="transport_cost",
        amount=request.transport_cost_cents,
        description="Alternative transportation cost incurred",
    )
    add_scenario_event(
        event_id="borrowing",
        event_date=request.borrowing_date,
        event_type="borrowing",
        amount=request.borrowed_amount_cents,
        description="Emergency borrowing received",
    )
    add_scenario_event(
        event_id="debt-payment",
        event_date=request.debt_payment_date,
        event_type="debt_payment",
        amount=request.debt_payment_cents,
        description="Future debt payment due",
    )
    events.sort(key=_event_priority)

    normal_delta: dict[date, int] = defaultdict(int)
    crisis_delta: dict[date, int] = defaultdict(int)
    for event in events:
        if event.type in {"paycheck", "bill_due"}:
            normal_delta[event.date] += event.signed_amount_cents
        crisis_delta[event.date] += event.signed_amount_cents

    normal_balance = balance
    crisis_balance = balance
    constrained_cash = max(0, balance)
    bill_outcomes: list[BillOutcome] = []
    points: list[SimulationCashflowPoint] = []
    events_by_date: dict[date, list[FinancialEvent]] = defaultdict(list)
    for event in events:
        events_by_date[event.date].append(event)

    priority_counter = 1
    for offset in range(request.forecast_horizon_days + 1):
        current = start + timedelta(days=offset)
        normal_balance += normal_delta[current]
        crisis_balance += crisis_delta[current]

        for event in events_by_date[current]:
            if event.type == "bill_due":
                continue
            constrained_cash = max(0, constrained_cash + event.signed_amount_cents)

        due_bills = sorted(
            (bill for bill in bills if bill.due_date == current),
            key=lambda item: (not item.essential, item.id),
        )
        for bill in due_bills:
            funded = min(constrained_cash, bill.amount_cents)
            unpaid = bill.amount_cents - funded
            constrained_cash -= funded
            bill_outcomes.append(
                BillOutcome(
                    obligation_id=bill.id,
                    name=bill.name,
                    amount_cents=bill.amount_cents,
                    due_date=bill.due_date,
                    funded_cents=funded,
                    unpaid_cents=unpaid,
                    essential=bill.essential,
                    category=bill.category,
                    projected_status=(
                        "funded" if unpaid == 0 else "unpaid" if funded == 0 else "partially_unpaid"
                    ),
                    payment_priority=priority_counter,
                    source=bill.source,
                )
            )
            priority_counter += 1

        points.append(
            SimulationCashflowPoint(
                date=current,
                normal_balance_cents=normal_balance,
                crisis_balance_cents=crisis_balance,
                constrained_available_cents=constrained_cash,
                raw_shortfall=crisis_balance < 0,
            )
        )

    unpaid_bills = [
        outcome for outcome in bill_outcomes if outcome.essential and outcome.unpaid_cents > 0
    ]
    peak_gap = max(0, -min(point.crisis_balance_cents for point in points))
    nodes = _graph_nodes(
        snapshot=snapshot,
        request=request,
        scenario_start=start,
        shifts=shifts,
        income_losses=income_losses,
        cashflow=points,
        unpaid_bills=unpaid_bills,
        peak_gap_cents=peak_gap,
    )
    return SimulationResult(
        source=SimulationSource(
            customer_id=snapshot.customer.id,
            account_ids=[account.id for account in snapshot.accounts],
            current_balance_cents=balance,
            banking_mode=snapshot.source.mode,
            source_as_of_date=snapshot.cash_flow.start_date,
            source_retrieved_at=snapshot.source.retrieved_at,
        ),
        scenario=SimulationScenario(
            scenario_start_date=start,
            forecast_end_date=end,
            repair_quote_cents=request.repair_quote_cents,
            repair_payment_status=request.repair_payment_status,
            repair_delay_days=request.repair_delay_days,
            affected_shift_dates=shifts,
            hours_per_shift=request.hours_per_shift,
            weekly_hours=request.weekly_hours,
            take_home_multiplier_basis_points=request.take_home_multiplier_basis_points,
            transport_cost_cents=request.transport_cost_cents,
            borrowed_amount_cents=request.borrowed_amount_cents,
            debt_payment_cents=request.debt_payment_cents,
        ),
        events=events,
        cashflow=points,
        income_lost_by_payday=income_losses,
        bill_outcomes=bill_outcomes,
        unpaid_bills=unpaid_bills,
        normal_ending_balance_cents=points[-1].normal_balance_cents,
        crisis_ending_balance_cents=points[-1].crisis_balance_cents,
        constrained_ending_cash_cents=points[-1].constrained_available_cents,
        peak_funding_gap_cents=peak_gap,
        unpaid_essential_total_cents=sum(item.unpaid_cents for item in unpaid_bills),
        graph_nodes=nodes,
        graph_edges=_graph_edges(),
        warnings=warnings,
    )
