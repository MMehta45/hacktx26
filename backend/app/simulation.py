from collections.abc import Sequence
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.models import CustomerSnapshot, UpcomingBill
from app.simulation_models import (
    BillOutcome,
    CrisisSimulationRequest,
    FinancialEvent,
    IncomeLoss,
    PayrollRecord,
    ProblemEdge,
    ProblemNode,
    ProtectedObligation,
    RepairProjection,
    ShiftRecord,
    SimulationCashflowPoint,
    SimulationResult,
    SimulationScenario,
    SimulationSource,
)

SHIFT_START = time(8, 0)
SHIFT_END = time(16, 0)
TAKE_HOME_BASIS_POINTS = 8_000


def _multiply_basis_points(amount_cents: int, basis_points: int) -> int:
    return int(
        (Decimal(amount_cents) * Decimal(basis_points) / Decimal(10_000)).quantize(
            Decimal(1), rounding=ROUND_HALF_UP
        )
    )


def _next_weekday_on_or_after(anchor: date, weekday: int) -> date:
    return anchor + timedelta(days=(weekday - anchor.weekday()) % 7)


def _next_monday(anchor: date) -> date:
    return anchor + timedelta(days=(7 - anchor.weekday()) % 7 or 7)


def payday_for_shift(shift_date: date) -> date:
    """Map a Monday-Sunday workweek to the following Friday."""

    workweek_monday = shift_date - timedelta(days=shift_date.weekday())
    return workweek_monday + timedelta(days=11)


def pay_period_for_payday(payday: date) -> tuple[date, date]:
    return payday - timedelta(days=11), payday - timedelta(days=5)


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


def _paydays(start: date, end: date) -> list[date]:
    first = _next_weekday_on_or_after(start, 4)
    return [first + timedelta(days=7 * index) for index in range(((end - first).days // 7) + 1)]


def _graph_edges() -> list[ProblemEdge]:
    definitions = (
        ("breakdown-unavailable", "car_breaks_down", "car_unavailable", None),
        ("unavailable-commute", "car_unavailable", "commute_disrupted", None),
        ("commute-work", "commute_disrupted", "missed_work", None),
        ("work-paycheck", "missed_work", "reduced_paycheck", None),
        ("paycheck-shortfall", "reduced_paycheck", "cash_shortfall", None),
        ("shortfall-bills", "cash_shortfall", "bills_unpaid", None),
        ("breakdown-repair", "car_breaks_down", "unexpected_repair_expense", None),
        ("repair-reserves", "unexpected_repair_expense", "cash_reserves_depleted", "only if repair is paid"),
        ("reserves-shortfall", "cash_reserves_depleted", "cash_shortfall", None),
        ("commute-transport", "commute_disrupted", "extra_transportation_costs", "only if alternative transport is purchased"),
        ("transport-shortfall", "extra_transportation_costs", "cash_shortfall", None),
        ("reserves-delay", "cash_reserves_depleted", "repair_delayed", "if repair cannot be completed"),
        ("delay-unavailable", "repair_delayed", "car_unavailable", "over later days"),
        ("shortfall-borrowing", "cash_shortfall", "emergency_borrowing", "only if borrowing occurs"),
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
    breakdown_date: date,
    shifts: list[ShiftRecord],
    payrolls: list[PayrollRecord],
    repair: RepairProjection,
    cashflow: list[SimulationCashflowPoint],
    unpaid_bills: list[BillOutcome],
    peak_gap_cents: int,
) -> list[ProblemNode]:
    missed = [shift for shift in shifts if shift.attendance == "projected_missed"]
    impacted_payrolls = [payroll for payroll in payrolls if payroll.lost_take_home_cents]
    lost_total = sum(payroll.lost_take_home_cents for payroll in impacted_payrolls)
    first_shortfall = next(
        (point.date for point in cashflow if point.crisis_balance_cents < 0), None
    )
    first_unpaid = min((bill.due_date for bill in unpaid_bills), default=None)
    repair_paid = repair.modeled_payment_date is not None
    repair_delayed = repair.modeled_payment_date != breakdown_date
    source = "nessie" if snapshot.source.mode == "live" else "fixture"
    return [
        ProblemNode(id="car_breaks_down", label="Car breaks down", description="A fictional breakdown starts the untreated timeline.", status="projected", activation_date=breakdown_date, evidence="Explicit scenario assumption; Nessie history is unchanged.", source="scenario_assumption"),
        ProblemNode(id="car_unavailable", label="Car unavailable", description="Vehicle availability is derived from the breakdown and modeled repair payment.", status="projected", activation_date=breakdown_date, evidence=f"Unavailable for {repair.days_unavailable_within_forecast} calendar day(s) in the forecast.", source="projection"),
        ProblemNode(id="commute_disrupted", label="Commute disrupted", description="Scheduled onsite shifts are at risk while the car is unavailable.", status="projected" if missed else "inactive", activation_date=missed[0].date if missed else None, evidence=f"{len(missed)} scheduled shift(s) occur while the vehicle is unusable at 08:00.", source="projection"),
        ProblemNode(id="missed_work", label="Missed work", description="Untreated attendance is calculated from vehicle availability at shift start.", status="projected" if missed else "inactive", activation_date=missed[0].date if missed else None, evidence=f"{len(missed)} derived missed shift(s); no transit, remote work, or borrowed car is assumed.", source="projection"),
        ProblemNode(id="reduced_paycheck", label="Reduced paycheck", description="Each missed shift reduces the following-Friday paycheck for its workweek.", status="projected" if impacted_payrolls else "inactive", activation_date=impacted_payrolls[0].payday if impacted_payrolls else None, evidence="Monday-Sunday work is paid the following Friday at an 80% take-home estimate.", amount_cents=lost_total, source="projection"),
        ProblemNode(id="cash_shortfall", label="Cash shortfall", description="The raw crisis forecast falls below zero.", status="projected" if peak_gap_cents else "inactive", activation_date=first_shortfall, evidence=f"Starts from the {source} balance; a negative forecast is a funding need, not an observed overdraft.", amount_cents=peak_gap_cents, source="projection"),
        ProblemNode(id="bills_unpaid", label="Bills unpaid", description="Essential obligations cannot be fully funded on their due dates.", status="projected" if unpaid_bills else "inactive", activation_date=first_unpaid, evidence=f"Constrained allocation leaves {len(unpaid_bills)} essential obligation(s) uncovered.", amount_cents=sum(item.unpaid_cents for item in unpaid_bills), source="projection"),
        ProblemNode(id="unexpected_repair_expense", label="Unexpected repair expense", description="The full quote is required before same-day restoration.", status="projected", activation_date=breakdown_date, evidence="The quote is only debited if the bill-protective policy can fund it.", amount_cents=repair.quote_cents, source="scenario_assumption"),
        ProblemNode(id="cash_reserves_depleted", label="Cash reserves depleted", description="This branch activates only if the repair payment is modeled.", status="projected" if repair_paid else "inactive", activation_date=repair.modeled_payment_date, evidence="One repair outflow is modeled." if repair_paid else "No affordable repair payment was modeled; the quote removes $0.", amount_cents=repair.quote_cents if repair_paid else 0, source="projection"),
        ProblemNode(id="repair_delayed", label="Repair delayed", description="Funding constraints postpone or prevent the repair.", status="projected" if repair_delayed else "inactive", activation_date=breakdown_date if repair_delayed else None, evidence=repair.blocked_reason or "The repair was affordable on the breakdown date.", source="projection"),
        ProblemNode(id="extra_transportation_costs", label="Extra transportation costs", description="Alternative transportation is a future intervention, not a baseline fact.", status="inactive", activation_date=None, evidence="Untreated transportation cost is $0.", amount_cents=0, source="scenario_assumption"),
        ProblemNode(id="emergency_borrowing", label="Emergency borrowing", description="Borrowing is not assumed in the untreated timeline.", status="conditional", activation_date=None, evidence="No loan or outside assistance is modeled.", amount_cents=0, source="scenario_assumption"),
        ProblemNode(id="future_debt_payments", label="Future debt payments", description="Debt repayment only applies if borrowing later occurs.", status="conditional", activation_date=None, evidence="No borrowing means no debt payment.", amount_cents=0, source="scenario_assumption"),
        ProblemNode(id="late_fees", label="Late fees", description="An unpaid bill may create fees, but no verified fee schedule is available.", status="conditional" if unpaid_bills else "inactive", activation_date=None, evidence="No fee amount is invented or included.", amount_cents=0, source="projection"),
    ]


def simulate(
    snapshot: CustomerSnapshot,
    request: CrisisSimulationRequest,
    actions: Sequence[object] = (),
) -> SimulationResult:
    """Run a pure, deterministic employment and financial state-transition timeline."""

    if actions:
        raise ValueError("Recovery actions are reserved for a later milestone.")
    start = snapshot.cash_flow.start_date
    end = start + timedelta(days=request.forecast_horizon_days)
    breakdown_date = request.breakdown_date or _next_monday(start)
    if not start <= breakdown_date <= end:
        raise ValueError("Breakdown date must fall inside the loaded forecast horizon.")
    breakdown_at = datetime.combine(breakdown_date, request.breakdown_time_local)
    balance = sum(account.balance_cents for account in snapshot.accounts)
    bills, warnings = _deduplicate_bills(snapshot.upcoming_bills, start, end)
    bills_by_date: dict[date, list[UpcomingBill]] = {}
    for bill in bills:
        bills_by_date.setdefault(bill.due_date, []).append(bill)

    gross_shift = request.hourly_rate_cents * 8
    net_shift = _multiply_basis_points(gross_shift, TAKE_HOME_BASIS_POINTS)
    gross_week = gross_shift * 5
    net_week = net_shift * 5
    payday_dates = _paydays(start, end)
    shift_records: list[ShiftRecord] = []
    payroll_records: list[PayrollRecord] = []
    payroll_by_date: dict[date, PayrollRecord] = {}
    repair_date: date | None = None
    repair_cash_after: int | None = None
    last_blocked_reason: str | None = None
    last_protected: list[ProtectedObligation] = []
    constrained_cash = max(0, balance)
    normal_balance = balance
    crisis_balance = balance
    points: list[SimulationCashflowPoint] = []
    events: list[FinancialEvent] = []
    bill_outcomes: list[BillOutcome] = []
    priority_counter = 1

    def attendance_for(workday: date) -> str:
        if workday < start:
            return "worked"
        record = next((item for item in shift_records if item.date == workday), None)
        return record.attendance if record else "unresolved"

    def projected_pay_if_repaired(current: date, payday: date) -> int:
        period_start, _period_end = pay_period_for_payday(payday)
        worked = 0
        for offset in range(7):
            workday = period_start + timedelta(days=offset)
            if workday.weekday() >= 5:
                continue
            state = attendance_for(workday)
            if state == "worked" or workday > current:
                worked += 1
        return worked * net_shift

    def protection_window(current: date) -> tuple[date | None, list[UpcomingBill]]:
        reliable = next(
            (
                payday
                for payday in payday_dates
                if payday > current and projected_pay_if_repaired(current, payday) > 0
            ),
            None,
        )
        protected = [
            bill
            for bill in bills
            if bill.essential
            and bill.due_date > current
            and (bill.due_date <= reliable if reliable else True)
        ]
        return reliable, protected

    for offset in range(request.forecast_horizon_days + 1):
        current = start + timedelta(days=offset)

        # 08:00 shift occurs before Friday payroll, bills, and the end-of-day repair decision.
        if current.weekday() < 5:
            shift_start = datetime.combine(current, SHIFT_START)
            vehicle_usable = current < breakdown_date or (
                current == breakdown_date and breakdown_at > shift_start
            ) or (repair_date is not None and repair_date < current)
            attendance = "worked" if vehicle_usable else "projected_missed"
            reason = (
                "Vehicle was usable at the 08:00 shift start."
                if vehicle_usable
                else "Vehicle was unavailable at 08:00; untreated baseline assumes no alternate commute."
            )
            shift_records.append(
                ShiftRecord(
                    id=f"shift-{current.isoformat()}",
                    date=current,
                    scheduled_start_local=shift_start,
                    scheduled_end_local=datetime.combine(current, SHIFT_END),
                    gross_earning_potential_cents=gross_shift,
                    take_home_earning_potential_cents=net_shift,
                    associated_payday=payday_for_shift(current),
                    vehicle_usable_at_shift_start=vehicle_usable,
                    attendance=attendance,
                    reason=reason,
                )
            )

        # Payroll arrives after the morning shift and pays the prior Monday-Sunday period.
        if current in payday_dates:
            period_start, period_end = pay_period_for_payday(current)
            states = [
                attendance_for(period_start + timedelta(days=index))
                for index in range(5)
            ]
            worked = states.count("worked")
            missed = states.count("projected_missed")
            actual = worked * net_shift
            # Sunday closes the period, but Friday is the final scheduled workday.
            final_scheduled_workday = period_end - timedelta(days=2)
            reliability = (
                "already_earned"
                if final_scheduled_workday < start
                else "attendance_derived"
            )
            payroll = PayrollRecord(
                id=f"payroll-{current.isoformat()}",
                work_period_start=period_start,
                work_period_end=period_end,
                payday=current,
                normal_gross_cents=gross_week,
                normal_take_home_cents=net_week,
                actual_projected_take_home_cents=actual,
                scheduled_shift_count=5,
                worked_shift_count=worked,
                missed_shift_count=missed,
                lost_take_home_cents=net_week - actual,
                reliability=reliability,
            )
            payroll_records.append(payroll)
            payroll_by_date[current] = payroll
            normal_balance += net_week
            crisis_balance += actual
            constrained_cash += actual
            events.append(FinancialEvent(id=f"paycheck-{current.isoformat()}", date=current, type="paycheck", signed_amount_cents=net_week, description="Normal weekly take-home paycheck", source="user_wage_forecast", status="projected"))
            if payroll.lost_take_home_cents:
                events.append(FinancialEvent(id=f"lost-wages-{current.isoformat()}", date=current, type="lost_wages", signed_amount_cents=-payroll.lost_take_home_cents, description=f"Estimated take-home lost from {missed} derived missed shift(s)", source="crisis_projection", status="projected"))

        # Confirmed obligations are due after payroll; constrained cash never overdrafts.
        for bill in sorted(bills_by_date.get(current, []), key=lambda item: (not item.essential, item.id)):
            normal_balance -= bill.amount_cents
            crisis_balance -= bill.amount_cents
            funded = min(constrained_cash, bill.amount_cents)
            constrained_cash -= funded
            unpaid = bill.amount_cents - funded
            bill_outcomes.append(BillOutcome(obligation_id=bill.id, name=bill.name, amount_cents=bill.amount_cents, due_date=bill.due_date, funded_cents=funded, unpaid_cents=unpaid, essential=bill.essential, category=bill.category, projected_status="funded" if unpaid == 0 else "unpaid" if funded == 0 else "partially_unpaid", payment_priority=priority_counter, source=bill.source))
            priority_counter += 1
            events.append(FinancialEvent(id=f"bill-{bill.source}-{bill.id}", date=current, type="bill_due", signed_amount_cents=-bill.amount_cents, description=f"{bill.name} due", source=bill.source, status="projected", provenance_id=bill.nessie_bill_id or bill.id, essential=bill.essential))

        # Repair is considered last. A same-day payment cannot restore the 08:00 shift.
        if current >= breakdown_date and repair_date is None:
            reliable_payday, protected_bills = protection_window(current)
            protected_total = sum(item.amount_cents for item in protected_bills)
            last_protected = [ProtectedObligation(obligation_id=item.id, name=item.name, amount_cents=item.amount_cents, due_date=item.due_date) for item in protected_bills]
            required = request.repair_quote_cents + protected_total
            if constrained_cash >= required:
                repair_date = current
                constrained_cash -= request.repair_quote_cents
                crisis_balance -= request.repair_quote_cents
                repair_cash_after = constrained_cash
                events.append(FinancialEvent(id="repair-payment", date=current, type="repair_payment", signed_amount_cents=-request.repair_quote_cents, description="Bill-protective projected repair payment", source="crisis_projection", status="projected"))
                last_blocked_reason = None
            else:
                payday_text = reliable_payday.isoformat() if reliable_payday else "the forecast end"
                last_blocked_reason = (
                    f"Available cash is {constrained_cash} cents; {required} cents is required to pay "
                    f"the quote and protect essential bills through {payday_text}."
                )

        points.append(SimulationCashflowPoint(date=current, normal_balance_cents=normal_balance, crisis_balance_cents=crisis_balance, constrained_available_cents=constrained_cash, raw_shortfall=crisis_balance < 0))

    losses = [
        IncomeLoss(
            payday=payroll.payday,
            affected_shift_dates=[shift.date for shift in shift_records if shift.associated_payday == payroll.payday and shift.attendance == "projected_missed"],
            gross_lost_cents=payroll.missed_shift_count * gross_shift,
            take_home_lost_cents=payroll.lost_take_home_cents,
            normal_take_home_cents=payroll.normal_take_home_cents,
            crisis_take_home_cents=payroll.actual_projected_take_home_cents,
        )
        for payroll in payroll_records
        if payroll.lost_take_home_cents
    ]
    outage_end = repair_date or end
    unavailable_days = (outage_end - breakdown_date).days + 1
    repair = RepairProjection(
        quote_cents=request.repair_quote_cents,
        earliest_financially_feasible_payment_date=repair_date,
        modeled_payment_date=repair_date,
        vehicle_restoration_date=repair_date,
        days_unavailable_within_forecast=max(0, unavailable_days),
        funding_status="affordable_and_paid" if repair_date else "unaffordable_within_horizon",
        blocked_reason=last_blocked_reason,
        cash_balance_after_payment_cents=repair_cash_after,
        protected_essential_obligations=last_protected,
        policy="Pay the full quote only after due bills when cash also protects essential obligations through the next payday supported by earned or attendable work.",
    )
    unpaid_bills = [item for item in bill_outcomes if item.essential and item.unpaid_cents > 0]
    peak_gap = max(0, -min(point.crisis_balance_cents for point in points))
    events.sort(key=lambda item: (item.date, {"paycheck": 0, "lost_wages": 1, "bill_due": 2, "repair_payment": 3}[item.type], item.id))
    nodes = _graph_nodes(snapshot=snapshot, breakdown_date=breakdown_date, shifts=shift_records, payrolls=payroll_records, repair=repair, cashflow=points, unpaid_bills=unpaid_bills, peak_gap_cents=peak_gap)
    return SimulationResult(
        source=SimulationSource(customer_id=snapshot.customer.id, account_ids=[account.id for account in snapshot.accounts], current_balance_cents=balance, banking_mode=snapshot.source.mode, source_as_of_date=start, source_retrieved_at=snapshot.source.retrieved_at),
        scenario=SimulationScenario(scenario_start_date=start, forecast_end_date=end, breakdown_at_local=breakdown_at, repair_quote_cents=request.repair_quote_cents, hourly_rate_cents=request.hourly_rate_cents, workdays=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]),
        shift_records=shift_records,
        payroll_records=payroll_records,
        repair_projection=repair,
        events=events,
        cashflow=points,
        income_lost_by_payday=losses,
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
