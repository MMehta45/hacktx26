"""Conservative, read-only opportunities derived from a customer snapshot.

These records explain potential recovery actions.  They never create baseline
cash-flow events; only an explicit, dated recovery effect may do that.
"""

from collections import defaultdict
from datetime import timedelta
from itertools import pairwise
from statistics import median

from app.models import CustomerSnapshot, Transaction
from app.recovery_models import FinancialOpportunity

FIXED_ESSENTIAL = {"Housing/Rent", "Utilities", "Insurance"}
VARIABLE_ESSENTIAL = {"Groceries", "Transportation/Gas", "Health"}
DISCRETIONARY = {"Dining", "Entertainment", "Shopping", "Subscriptions"}


def _classification(category: str) -> str:
    if category in FIXED_ESSENTIAL:
        return "fixed_essential"
    if category in VARIABLE_ESSENTIAL:
        return "variable_essential"
    return "discretionary"


def _merchant_key(transaction: Transaction) -> str:
    return (transaction.merchant_display or transaction.description or "Unknown").casefold().strip()


def _scheduled_match(snapshot: CustomerSnapshot, transactions: list[Transaction]):
    """Match only conservative near-identical payment identities, avoiding double forecasts."""
    amount = round(sum(item.amount_cents for item in transactions) / len(transactions))
    category = transactions[0].category
    latest = max(item.date for item in transactions)
    for bill in snapshot.upcoming_bills:
        if bill.category != category or bill.amount_cents != amount:
            continue
        # A prior monthly/weekly charge reasonably supports the named schedule.
        if abs((bill.due_date - latest).days) <= 45:
            return bill
    return None


def analyze_financial_opportunities(snapshot: CustomerSnapshot) -> list[FinancialOpportunity]:
    debits = [item for item in snapshot.history.transactions if item.direction == "debit"]
    groups: dict[str, list[Transaction]] = defaultdict(list)
    for item in debits:
        groups[_merchant_key(item)].append(item)
    observations = max(1, (snapshot.history.end - snapshot.history.start).days)
    results: list[FinancialOpportunity] = []

    # Scheduled bills are authoritative forecast obligations.
    for bill in snapshot.upcoming_bills:
        results.append(FinancialOpportunity(
            id=f"scheduled:{bill.id}", kind="scheduled_bill", merchant=bill.name,
            category=bill.category, classification=_classification(bill.category),
            monthly_average_cents=bill.amount_cents, expected_next_date=bill.due_date,
            confidence="confirmed", scheduled_bill_id=bill.id, forecast_included=True,
            explanation="Explicit upcoming schedule; included once in the baseline forecast.",
        ))

    for merchant, transactions in groups.items():
        ordered = sorted(transactions, key=lambda item: item.date)
        category = ordered[0].category
        total = sum(item.amount_cents for item in ordered)
        monthly = round(total * 30 / observations)
        classification = _classification(category)
        gaps = [(later.date - earlier.date).days for earlier, later in pairwise(ordered)]
        amounts = [item.amount_cents for item in ordered]
        consistent_amount = max(amounts) - min(amounts) <= max(100, round(median(amounts) * 0.12))
        cadence = round(median(gaps)) if gaps else 0
        recurring = len(ordered) >= 3 and cadence in range(25, 36) and max(gaps) - min(gaps) <= 7 and consistent_amount
        scheduled = _scheduled_match(snapshot, ordered) if recurring else None
        if recurring and not scheduled:
            results.append(FinancialOpportunity(
                id=f"recurring:{merchant}", kind="recurring_charge", merchant=ordered[-1].merchant_display or merchant,
                category=category, classification=classification, monthly_average_cents=monthly,
                expected_next_date=ordered[-1].date + timedelta(days=cadence), confidence="high",
                transaction_ids=[item.id for item in ordered], forecast_included=False,
                potential_savings_cents=monthly if classification == "discretionary" else None,
                explanation="Repeated monthly merchant charge inferred from consistent historical dates and amounts; not added to the baseline forecast.",
            ))
        elif classification in {"variable_essential", "discretionary"} and total:
            results.append(FinancialOpportunity(
                id=f"variable:{merchant}", kind="variable_spending", merchant=ordered[-1].merchant_display or merchant,
                category=category, classification=classification, monthly_average_cents=monthly,
                confidence="medium" if len(ordered) >= 3 else "low", transaction_ids=[item.id for item in ordered],
                forecast_included=False,
                potential_savings_cents=round(monthly * 0.25) if classification == "discretionary" else None,
                explanation=("Historical variable spending, not a contractual recurring bill. Any reduction is conditional and does not change the baseline forecast."),
            ))
    return sorted(results, key=lambda item: (item.kind != "scheduled_bill", item.category, item.merchant))
