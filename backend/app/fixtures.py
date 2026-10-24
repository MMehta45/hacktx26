from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.models import (
    Account,
    CategoryName,
    CategorySummary,
    Customer,
    CustomerSnapshot,
    History,
    IncomeProjection,
    Scenario,
    SourceMetadata,
    Transaction,
    UpcomingBill,
)

FIXTURE_CUSTOMER_ID = "fixture-maya-torres"
FIXTURE_ACCOUNT_ID = "fixture-checking"

PURCHASE_PATTERN: tuple[tuple[int, str, CategoryName, str], ...] = (
    (89, "Sunrise Apartments", "Housing/Rent", "Monthly rent"),
    (84, "H-E-B", "Groceries", "Weekly groceries"),
    (78, "Austin Energy", "Utilities", "Electric utility"),
    (75, "Shell", "Transportation/Gas", "Fuel"),
    (70, "H-E-B", "Groceries", "Weekly groceries"),
    (66, "Taco Deli", "Dining", "Lunch"),
    (61, "Central Health Clinic", "Health", "Clinic copay"),
    (59, "Sunrise Apartments", "Housing/Rent", "Monthly rent"),
    (55, "H-E-B", "Groceries", "Weekly groceries"),
    (50, "Shell", "Transportation/Gas", "Fuel"),
    (47, "Capital Metro", "Transportation/Gas", "Transit pass"),
    (44, "H-E-B", "Groceries", "Weekly groceries"),
    (40, "QuickCart", "Shopping", "Household supplies"),
    (36, "StreamBox", "Subscriptions", "Streaming subscription"),
    (33, "Taco Deli", "Dining", "Dinner"),
    (30, "Sunrise Apartments", "Housing/Rent", "Monthly rent"),
    (27, "Lone Star Insurance", "Insurance", "Auto insurance"),
    (24, "H-E-B", "Groceries", "Weekly groceries"),
    (20, "Austin Energy", "Utilities", "Electric utility"),
    (17, "Shell", "Transportation/Gas", "Fuel"),
    (13, "H-E-B", "Groceries", "Weekly groceries"),
    (9, "Taco Deli", "Dining", "Lunch"),
    (6, "QuickCart", "Shopping", "Work shoes"),
    (2, "H-E-B", "Groceries", "Weekly groceries"),
)

PURCHASE_AMOUNTS_CENTS = (
    85_000,
    7_800,
    9_400,
    4_200,
    6_900,
    1_500,
    3_500,
    85_000,
    8_200,
    3_800,
    4_100,
    7_100,
    4_800,
    1_500,
    2_100,
    85_000,
    12_500,
    7_600,
    8_700,
    4_000,
    7_300,
    1_800,
    6_400,
    7_900,
)

# These historical deposits intentionally reconcile to the fixture's recorded purchases.
# They are past facts and are not derived from the user's forward-looking wage input.
DEPOSIT_AMOUNTS_CENTS = (29_300, *([28_900] * 12))


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
        (("utility", "electric", "energy", "water"), "Utilities"),
        (("insurance",), "Insurance"),
        (("shopping", "retail", "quickcart"), "Shopping"),
        (("subscription", "stream"), "Subscriptions"),
        (("health", "clinic", "medical", "pharmacy"), "Health"),
    )
    for needles, category in mappings:
        if any(needle in normalized for needle in needles):
            return category
    return "Other"


def summarize_categories(transactions: list[Transaction]) -> list[CategorySummary]:
    totals: dict[CategoryName, int] = defaultdict(int)
    counts: dict[CategoryName, int] = defaultdict(int)
    for transaction in transactions:
        if transaction.direction != "debit":
            continue
        totals[transaction.category] += transaction.amount_cents
        counts[transaction.category] += 1
    return [
        CategorySummary(
            category=category,
            total_cents=total,
            monthly_average_cents=int(
                (Decimal(total) / Decimal(3)).quantize(
                    Decimal(1), rounding=ROUND_HALF_UP
                )
            ),
            transaction_count=counts[category],
        )
        for category, total in sorted(totals.items(), key=lambda item: item[1], reverse=True)
    ]


def fixture_transactions(anchor: date) -> list[Transaction]:
    transactions = [
        Transaction(
            id=f"fixture-purchase-{index:02d}",
            date=anchor - timedelta(days=days_ago),
            amount_cents=PURCHASE_AMOUNTS_CENTS[index],
            direction="debit",
            merchant_display=merchant,
            category=category,
            source="fixture_purchase",
            account_id=FIXTURE_ACCOUNT_ID,
            description=description,
        )
        for index, (days_ago, merchant, category, description) in enumerate(PURCHASE_PATTERN)
    ]
    for index in range(13):
        transactions.append(
            Transaction(
                id=f"fixture-deposit-{index:02d}",
                date=anchor - timedelta(days=3 + index * 7),
                amount_cents=DEPOSIT_AMOUNTS_CENTS[index],
                direction="credit",
                merchant_display="Hill Country Market payroll",
                category="Other",
                source="fixture_deposit",
                account_id=FIXTURE_ACCOUNT_ID,
                description="Historical weekly payroll deposit",
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
            amount_cents=6_500,
            due_date=upcoming(27),
            source="synthetic_schedule",
            status="scheduled",
        ),
        UpcomingBill(
            id="schedule-electricity",
            name="Electricity",
            amount_cents=9_200,
            due_date=upcoming(29),
            source="synthetic_schedule",
            status="scheduled",
        ),
        UpcomingBill(
            id="schedule-rent",
            name="Rent",
            amount_cents=85_000,
            due_date=upcoming(1),
            source="synthetic_schedule",
            status="scheduled",
        ),
        UpcomingBill(
            id="schedule-insurance",
            name="Auto insurance",
            amount_cents=12_500,
            due_date=upcoming(5),
            source="synthetic_schedule",
            status="scheduled",
        ),
    ]


def income_projection(anchor: date, hourly_rate_cents: int) -> IncomeProjection:
    first_payday = next_weekday(anchor, 4)
    return IncomeProjection(
        hourly_rate_cents=hourly_rate_cents,
        gross_per_shift_cents=hourly_rate_cents * 8,
        gross_weekly_cents=hourly_rate_cents * 40,
        next_pay_dates=[first_payday + timedelta(days=7 * index) for index in range(4)],
    )


def fixture_snapshot(
    *, anchor: date, display_name: str, hourly_rate_cents: int, repair_quote_cents: int, message: str
) -> CustomerSnapshot:
    transactions = fixture_transactions(anchor)
    categories = summarize_categories(transactions)
    return CustomerSnapshot(
        customer=Customer(id=FIXTURE_CUSTOMER_ID, display_name=display_name),
        accounts=[
            Account(
                id=FIXTURE_ACCOUNT_ID,
                type="Checking",
                nickname="Everyday checking",
                balance_cents=31_000,
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
        upcoming_bills=upcoming_bills(anchor),
        income_projection=income_projection(anchor, hourly_rate_cents),
        scenario=Scenario(repair_quote_cents=repair_quote_cents),
        source=SourceMetadata(
            banking="fixture",
            simulation_data="local_fixture",
            mode="fixture",
            message=message,
        ),
    )
