from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from itertools import pairwise

from app.models import (
    Account,
    CashFlowEvent,
    CashFlowForecast,
    CashFlowPoint,
    CategoryName,
    CategorySummary,
    Customer,
    CustomerSnapshot,
    ForecastIncome,
    History,
    IncomeProjection,
    Scenario,
    SourceMetadata,
    Transaction,
    UpcomingBill,
)

FIXTURE_CUSTOMER_ID = "fixture-maya-rodriguez"
FIXTURE_ACCOUNT_ID = "fixture-checking"

PurchaseSeed = tuple[int, str, CategoryName, str, int]


def _purchase_pattern() -> tuple[PurchaseSeed, ...]:
    records: list[PurchaseSeed] = [
        *(
            (days, "Sunrise Apartments", "Housing/Rent", "Monthly rent", 90_000)
            for days in (89, 59, 29)
        ),
        *(
            (days, "Austin Energy", "Utilities", "Electric utility", 12_500)
            for days in (83, 53, 23)
        ),
        *((days, "Connect Mobile", "Utilities", "Mobile phone", 6_000) for days in (80, 50, 20)),
        *(
            (days, "Lone Star Insurance", "Insurance", "Auto insurance", 11_000)
            for days in (77, 47, 17)
        ),
        *(
            (days, "StreamBox", "Subscriptions", "Streaming subscription", 1_500)
            for days in (74, 44, 14)
        ),
    ]
    series = (
        (
            range(86, 1, -7),
            "H-E-B",
            "Groceries",
            "Weekly groceries",
            (112, 126, 118, 134, 109, 121, 127, 115, 130, 117, 124, 110, 117),
        ),
        (
            range(84, 6, -7),
            "Shell",
            "Transportation/Gas",
            "Fuel",
            (47, 52, 49, 55, 46, 51, 53, 48, 50, 54, 45, 50),
        ),
        (
            (82, 74, 68, 60, 54, 48, 39, 33, 26, 19, 14, 8, 3),
            "Taco Deli",
            "Dining",
            "Restaurant",
            (42, 58, 47, 55, 39, 63, 51, 44, 57, 49, 52, 46, 47),
        ),
        (
            range(85, 0, -7),
            "Bennu Coffee",
            "Dining",
            "Coffee",
            (18, 22, 19, 21, 17, 23, 20, 18, 22, 19, 21, 20, 20),
        ),
        ((68, 49, 31, 9), "QuickCart", "Shopping", "Household and work items", (85, 124, 73, 118)),
        ((62, 25), "Central Health Clinic", "Health", "Clinic and pharmacy", (75, 75)),
    )
    for days_values, merchant, category, description, dollar_amounts in series:
        records.extend(
            (days, merchant, category, description, amount * 100)
            for days, amount in zip(days_values, dollar_amounts, strict=True)
        )
    return tuple(sorted(records, key=lambda item: item[0], reverse=True))


PURCHASE_PATTERN = _purchase_pattern()
WITHDRAWAL_PATTERN = ((66, 25_000), (43, 28_000), (22, 26_000), (5, 28_000))
DEPOSIT_AMOUNTS_CENTS = (64_000,) * 13

ESSENTIAL_CATEGORIES: frozenset[CategoryName] = frozenset(
    {"Housing/Rent", "Groceries", "Transportation/Gas", "Utilities", "Insurance", "Health"}
)


def next_weekday(anchor: date, weekday: int) -> date:
    days = (weekday - anchor.weekday()) % 7
    return anchor + timedelta(days=days or 7)


def money_to_cents(value: object) -> int:
    return int((Decimal(str(value)) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def categorize(text: str | None) -> CategoryName:
    normalized = (text or "").casefold()
    mappings: tuple[tuple[tuple[str, ...], CategoryName], ...] = (
        (("rent", "apartment", "housing"), "Housing/Rent"),
        (("grocery", "groceries", "h-e-b", "supermarket"), "Groceries"),
        (("restaurant", "dining", "taco", "cafe"), "Dining"),
        (("gas", "fuel", "shell", "transit", "transport"), "Transportation/Gas"),
        (("utility", "electric", "energy", "water", "phone", "mobile"), "Utilities"),
        (("insurance",), "Insurance"),
        (("shopping", "retail", "quickcart"), "Shopping"),
        (("subscription", "stream"), "Subscriptions"),
        (("health", "clinic", "medical", "pharmacy"), "Health"),
    )
    for needles, category in mappings:
        if any(needle in normalized for needle in needles):
            return category
    return "Other"


def mark_recurring(transactions: list[Transaction]) -> None:
    groups: dict[str, list[Transaction]] = defaultdict(list)
    for transaction in transactions:
        if transaction.direction == "debit" and transaction.merchant_display:
            groups[transaction.merchant_display.casefold()].append(transaction)
    naturally_recurring = {"Housing/Rent", "Utilities", "Insurance", "Subscriptions"}
    for group in groups.values():
        ordered = sorted(group, key=lambda item: item.date)
        if len(ordered) < 2:
            continue
        gaps = [(later.date - earlier.date).days for earlier, later in pairwise(ordered)]
        regular_interval = len(ordered) >= 3 and max(gaps) - min(gaps) <= 7
        category_recurring = ordered[0].category in naturally_recurring
        if regular_interval or category_recurring:
            for transaction in group:
                transaction.recurring = True


def summarize_categories(transactions: list[Transaction]) -> list[CategorySummary]:
    mark_recurring(transactions)
    totals: dict[CategoryName, int] = defaultdict(int)
    counts: dict[CategoryName, int] = defaultdict(int)
    recurring: dict[CategoryName, int] = defaultdict(int)
    for transaction in transactions:
        if transaction.direction != "debit":
            continue
        totals[transaction.category] += transaction.amount_cents
        counts[transaction.category] += 1
        if transaction.recurring:
            recurring[transaction.category] += transaction.amount_cents
    spending_total = sum(totals.values())
    return [
        CategorySummary(
            category=category,
            total_cents=total,
            monthly_average_cents=int(
                (Decimal(total) / Decimal(3)).quantize(Decimal(1), rounding=ROUND_HALF_UP)
            ),
            transaction_count=counts[category],
            percentage=round((total / spending_total) * 100, 1) if spending_total else 0,
            recurring_cents=recurring[category],
            irregular_cents=total - recurring[category],
            essential=category in ESSENTIAL_CATEGORIES,
        )
        for category, total in sorted(totals.items(), key=lambda item: item[1], reverse=True)
    ]


def fixture_transactions(anchor: date) -> list[Transaction]:
    transactions = [
        Transaction(
            id=f"fixture-purchase-{index:02d}",
            date=anchor - timedelta(days=days_ago),
            amount_cents=amount_cents,
            direction="debit",
            merchant_display=merchant,
            category=category,
            source="fixture_purchase",
            account_id=FIXTURE_ACCOUNT_ID,
            description=description,
        )
        for index, (days_ago, merchant, category, description, amount_cents) in enumerate(
            PURCHASE_PATTERN
        )
    ]
    for index in range(13):
        transactions.append(
            Transaction(
                id=f"fixture-deposit-{index:02d}",
                date=anchor - timedelta(days=1 + index * 7),
                amount_cents=DEPOSIT_AMOUNTS_CENTS[index],
                direction="credit",
                merchant_display="Hill Country Market payroll",
                category="Other",
                source="fixture_deposit",
                account_id=FIXTURE_ACCOUNT_ID,
                description="Historical weekly payroll deposit",
            )
        )
    for index, (days_ago, amount_cents) in enumerate(WITHDRAWAL_PATTERN):
        transactions.append(
            Transaction(
                id=f"fixture-withdrawal-{index:02d}",
                date=anchor - timedelta(days=days_ago),
                amount_cents=amount_cents,
                direction="debit",
                merchant_display="Cash withdrawal",
                category="Other",
                source="fixture_withdrawal",
                account_id=FIXTURE_ACCOUNT_ID,
                description="ATM cash and miscellaneous spending",
            )
        )
    return sorted(transactions, key=lambda transaction: transaction.date, reverse=True)


def upcoming_bills(anchor: date) -> list[UpcomingBill]:
    def upcoming(day: int) -> date:
        candidate = anchor.replace(day=min(day, monthrange(anchor.year, anchor.month)[1]))
        if candidate <= anchor:
            month = 1 if anchor.month == 12 else anchor.month + 1
            year = anchor.year + 1 if anchor.month == 12 else anchor.year
            candidate = date(year, month, min(day, monthrange(year, month)[1]))
        return candidate

    return [
        UpcomingBill(
            id="schedule-phone",
            name="Mobile phone",
            amount_cents=6_000,
            due_date=upcoming(27),
            source="synthetic_schedule",
            status="scheduled",
            category="Utilities",
            essential=True,
            provenance="Local forecast schedule; not a completed bank transaction.",
        ),
        UpcomingBill(
            id="schedule-electricity",
            name="Electricity",
            amount_cents=12_500,
            due_date=upcoming(29),
            source="synthetic_schedule",
            status="scheduled",
            category="Utilities",
            essential=True,
            provenance="Local forecast schedule; not a completed bank transaction.",
        ),
        UpcomingBill(
            id="schedule-rent",
            name="Rent",
            amount_cents=90_000,
            due_date=upcoming(1),
            source="synthetic_schedule",
            status="scheduled",
            category="Housing/Rent",
            essential=True,
            provenance="Local forecast schedule; not a completed bank transaction.",
        ),
        UpcomingBill(
            id="schedule-insurance",
            name="Auto insurance",
            amount_cents=11_000,
            due_date=upcoming(5),
            source="synthetic_schedule",
            status="scheduled",
            category="Insurance",
            essential=True,
            provenance="Local forecast schedule; not a completed bank transaction.",
        ),
        UpcomingBill(
            id="schedule-streaming",
            name="Streaming subscription",
            amount_cents=1_500,
            due_date=upcoming(8),
            source="synthetic_schedule",
            status="scheduled",
            category="Subscriptions",
            essential=False,
            provenance="Local forecast schedule; not a completed bank transaction.",
        ),
    ]


def income_projection(anchor: date, hourly_rate_cents: int) -> IncomeProjection:
    first_payday = next_weekday(anchor, 4)
    pay_dates = [first_payday + timedelta(days=7 * index) for index in range(5)]
    gross_weekly_cents = hourly_rate_cents * 40
    gross_per_shift_cents = hourly_rate_cents * 8
    estimated_net_weekly_cents = gross_weekly_cents * 8_000 // 10_000
    estimated_net_per_shift_cents = gross_per_shift_cents * 8_000 // 10_000
    return IncomeProjection(
        hourly_rate_cents=hourly_rate_cents,
        gross_per_shift_cents=gross_per_shift_cents,
        gross_weekly_cents=gross_weekly_cents,
        estimated_net_per_shift_cents=estimated_net_per_shift_cents,
        estimated_net_weekly_cents=estimated_net_weekly_cents,
        next_pay_dates=pay_dates,
        forecast_entries=[
            ForecastIncome(
                expected_payment_date=pay_date,
                gross_amount_cents=gross_weekly_cents,
                estimated_take_home_cents=estimated_net_weekly_cents,
                # Monday-Sunday work is paid on Friday of the following week.
                work_period_start=pay_date - timedelta(days=11),
                work_period_end=pay_date - timedelta(days=5),
            )
            for pay_date in pay_dates
            if pay_date <= anchor + timedelta(days=30)
        ],
    )


def cash_flow_forecast(
    *,
    anchor: date,
    starting_balance_cents: int,
    bills: list[UpcomingBill],
    income: IncomeProjection,
) -> CashFlowForecast:
    end_date = anchor + timedelta(days=30)
    events = [
        CashFlowEvent(
            date=entry.expected_payment_date,
            name="Projected weekly paycheck",
            amount_cents=entry.estimated_take_home_cents,
            direction="income",
            source="projected_income",
        )
        for entry in income.forecast_entries
        if entry.expected_payment_date <= end_date
    ]
    events.extend(
        CashFlowEvent(
            date=bill.due_date,
            name=bill.name,
            amount_cents=bill.amount_cents,
            direction="expense",
            source="scheduled_bill",
        )
        for bill in bills
        if anchor < bill.due_date <= end_date and bill.status not in {"paid", "completed"}
    )
    events.sort(key=lambda event: (event.date, event.direction))
    event_net: dict[date, int] = defaultdict(int)
    for event in events:
        event_net[event.date] += (
            event.amount_cents if event.direction == "income" else -event.amount_cents
        )
    balance = starting_balance_cents
    points: list[CashFlowPoint] = []
    for day_offset in range(31):
        current_date = anchor + timedelta(days=day_offset)
        balance += event_net[current_date]
        points.append(CashFlowPoint(date=current_date, projected_balance_cents=balance))
    minimum = min(point.projected_balance_cents for point in points)
    return CashFlowForecast(
        start_date=anchor,
        end_date=end_date,
        starting_balance_cents=starting_balance_cents,
        minimum_balance_cents=minimum,
        ending_balance_cents=points[-1].projected_balance_cents,
        peak_cash_shortfall_cents=max(0, -minimum),
        events=events,
        daily_balances=points,
        assumption=(
            "Daily baseline uses the live/fixture starting balance, 80% estimated take-home "
            "paychecks, and unpaid scheduled bills. The repair quote is not deducted."
        ),
    )


def fixture_snapshot(
    *,
    anchor: date,
    display_name: str,
    hourly_rate_cents: int,
    repair_quote_cents: int,
    message: str,
) -> CustomerSnapshot:
    transactions = fixture_transactions(anchor)
    categories = summarize_categories(transactions)
    bills = upcoming_bills(anchor)
    income = income_projection(anchor, hourly_rate_cents)
    starting_balance_cents = 31_000
    return CustomerSnapshot(
        customer=Customer(id=FIXTURE_CUSTOMER_ID, display_name=display_name),
        accounts=[
            Account(
                id=FIXTURE_ACCOUNT_ID,
                type="Checking",
                nickname="Everyday checking",
                balance_cents=starting_balance_cents,
                source="fixture",
            )
        ],
        history=History(
            start=anchor - timedelta(days=89),
            end=anchor,
            transactions=transactions,
            categories=categories,
            spending_total_cents=sum(item.total_cents for item in categories),
        ),
        upcoming_bills=bills,
        income_projection=income,
        cash_flow=cash_flow_forecast(
            anchor=anchor,
            starting_balance_cents=starting_balance_cents,
            bills=bills,
            income=income,
        ),
        scenario=Scenario(repair_quote_cents=repair_quote_cents),
        source=SourceMetadata(
            banking="fixture",
            simulation_data="local_fixture",
            mode="fixture",
            message=message,
        ),
    )
