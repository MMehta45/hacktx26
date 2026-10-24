from collections.abc import Mapping
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from time import sleep
from typing import Any, Self

import httpx

from app.fixtures import categorize, income_projection, summarize_categories, upcoming_bills
from app.models import (
    Account,
    Customer,
    CustomerSnapshot,
    History,
    Scenario,
    SourceMetadata,
    Transaction,
    UpcomingBill,
)


class NessieError(RuntimeError):
    """A sanitized Nessie failure safe to show without response bodies or authenticated URLs."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class NessieClient:
    def __init__(self, *, api_key: str, base_url: str, timeout_seconds: float = 15.0) -> None:
        self._api_key = api_key
        self._client = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout_seconds)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _request(
        self, method: str, path: str, *, payload: Mapping[str, Any] | None = None
    ) -> Any:
        attempts = 3 if method == "GET" else 1
        response: httpx.Response | None = None
        for attempt in range(attempts):
            try:
                response = self._client.request(
                    method,
                    path,
                    params={"key": self._api_key},
                    json=dict(payload) if payload is not None else None,
                )
            except httpx.TimeoutException as error:
                if attempt + 1 < attempts:
                    sleep(0.25 * (attempt + 1))
                    continue
                raise NessieError(
                    "Nessie timed out. Retry after confirming the sandbox is available."
                ) from error
            except httpx.HTTPError as error:
                raise NessieError(
                    "Nessie could not be reached. Check the base URL and network."
                ) from error
            if response.status_code not in {429, 500, 502, 503, 504} or attempt + 1 == attempts:
                break
            sleep(0.25 * (attempt + 1))

        if response is None:
            raise NessieError("Nessie did not return a response.")

        if response.status_code >= 400:
            if response.status_code in {401, 403}:
                message = "Nessie rejected the credential or resource permission."
            elif response.status_code == 404:
                message = "A seeded Nessie resource no longer exists. Rerun the seeder."
            elif response.status_code == 429:
                message = "Nessie rate-limited the request. Wait briefly, then retry."
            elif response.status_code >= 500:
                message = "Nessie is temporarily unavailable. Retry later."
            else:
                message = "Nessie rejected the request. Review the documented resource fields."
            raise NessieError(message, status_code=response.status_code)

        if response.status_code == 204 or not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return response.text

    @staticmethod
    def _list(payload: Any, resource: str) -> list[dict[str, Any]]:
        if not isinstance(payload, list):
            raise NessieError(f"Nessie returned an unexpected {resource} payload.")
        return [dict(item) for item in payload if isinstance(item, Mapping)]

    def list_customers(self) -> list[dict[str, Any]]:
        return self._list(self._request("GET", "/customers"), "customer")

    def get_customer(self, customer_id: str) -> dict[str, Any]:
        payload = self._request("GET", f"/customers/{customer_id}")
        if not isinstance(payload, Mapping):
            raise NessieError("Nessie returned an unexpected customer payload.")
        return dict(payload)

    def create_customer(self, payload: Mapping[str, Any]) -> Any:
        return self._request("POST", "/customers", payload=payload)

    def list_accounts(self, customer_id: str) -> list[dict[str, Any]]:
        return self._list(
            self._request("GET", f"/customers/{customer_id}/accounts"), "account"
        )

    def get_account(self, account_id: str) -> dict[str, Any]:
        payload = self._request("GET", f"/accounts/{account_id}")
        if not isinstance(payload, Mapping):
            raise NessieError("Nessie returned an unexpected account payload.")
        return dict(payload)

    def create_account(self, customer_id: str, payload: Mapping[str, Any]) -> Any:
        return self._request("POST", f"/customers/{customer_id}/accounts", payload=payload)

    def delete_account(self, account_id: str) -> None:
        self._request("DELETE", f"/accounts/{account_id}")

    def list_merchants(self) -> list[dict[str, Any]]:
        return self._list(self._request("GET", "/merchants"), "merchant")

    def create_merchant(self, payload: Mapping[str, Any]) -> Any:
        return self._request("POST", "/merchants", payload=payload)

    def list_purchases(self, account_id: str) -> list[dict[str, Any]]:
        return self._list(
            self._request("GET", f"/accounts/{account_id}/purchases"), "purchase"
        )

    def create_purchase(self, account_id: str, payload: Mapping[str, Any]) -> Any:
        return self._request("POST", f"/accounts/{account_id}/purchases", payload=payload)

    def list_deposits(self, account_id: str) -> list[dict[str, Any]]:
        return self._list(
            self._request("GET", f"/accounts/{account_id}/deposits"), "deposit"
        )

    def create_deposit(self, account_id: str, payload: Mapping[str, Any]) -> Any:
        return self._request("POST", f"/accounts/{account_id}/deposits", payload=payload)

    def list_bills(self, account_id: str) -> list[dict[str, Any]]:
        return self._list(self._request("GET", f"/accounts/{account_id}/bills"), "bill")


def parse_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def dollars_to_cents(value: object) -> int:
    try:
        return int(
            (Decimal(str(value)) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP)
        )
    except (ValueError, TypeError):
        return 0


def resource_id(payload: Mapping[str, Any]) -> str | None:
    value = payload.get("_id") or payload.get("id")
    return str(value) if value else None


def merchant_category(merchant: Mapping[str, Any] | None) -> str:
    if merchant is None:
        return ""
    category = merchant.get("category")
    if isinstance(category, list):
        return " ".join(str(item) for item in category)
    return str(category or "")


def normalize_snapshot(
    *,
    anchor: date,
    display_name: str,
    hourly_rate_cents: int,
    repair_quote_cents: int,
    customer: Mapping[str, Any],
    accounts_raw: list[dict[str, Any]],
    purchases_by_account: Mapping[str, list[dict[str, Any]]],
    deposits_by_account: Mapping[str, list[dict[str, Any]]],
    bills_by_account: Mapping[str, list[dict[str, Any]]],
    merchants: Mapping[str, dict[str, Any]],
) -> CustomerSnapshot:
    customer_id = resource_id(customer)
    if not customer_id:
        raise NessieError("The seeded Nessie customer is missing an identifier.")

    accounts: list[Account] = []
    transactions: list[Transaction] = []
    live_bills: list[UpcomingBill] = []
    history_start = anchor - timedelta(days=89)

    for raw_account in accounts_raw:
        account_id = resource_id(raw_account)
        if not account_id:
            continue
        accounts.append(
            Account(
                id=account_id,
                type=str(raw_account.get("type") or "Unknown"),
                nickname=str(raw_account.get("nickname")) if raw_account.get("nickname") else None,
                balance_cents=dollars_to_cents(raw_account.get("balance", 0)),
                source="nessie",
            )
        )
        for raw_purchase in purchases_by_account.get(account_id, []):
            transaction_date = parse_date(
                raw_purchase.get("purchase_date") or raw_purchase.get("transaction_date")
            )
            if transaction_date is None or not history_start <= transaction_date <= anchor:
                continue
            merchant_id = raw_purchase.get("merchant_id")
            merchant = merchants.get(str(merchant_id)) if merchant_id else None
            merchant_name = str(merchant.get("name")) if merchant and merchant.get("name") else None
            description = str(raw_purchase.get("description") or "") or None
            category_text = " ".join(
                item for item in (merchant_category(merchant), merchant_name or "", description or "") if item
            )
            transactions.append(
                Transaction(
                    id=resource_id(raw_purchase)
                    or f"nessie-purchase-{account_id}-{len(transactions)}",
                    date=transaction_date,
                    amount_cents=dollars_to_cents(raw_purchase.get("amount", 0)),
                    direction="debit",
                    merchant_display=merchant_name,
                    category=categorize(category_text),
                    source="nessie_purchase",
                    account_id=account_id,
                    description=description,
                )
            )
        for raw_deposit in deposits_by_account.get(account_id, []):
            transaction_date = parse_date(raw_deposit.get("transaction_date"))
            if transaction_date is None or not history_start <= transaction_date <= anchor:
                continue
            transactions.append(
                Transaction(
                    id=resource_id(raw_deposit)
                    or f"nessie-deposit-{account_id}-{len(transactions)}",
                    date=transaction_date,
                    amount_cents=dollars_to_cents(raw_deposit.get("amount", 0)),
                    direction="credit",
                    merchant_display="Historical deposit",
                    category="Other",
                    source="nessie_deposit",
                    account_id=account_id,
                    description=str(raw_deposit.get("description") or "") or None,
                )
            )
        for raw_bill in bills_by_account.get(account_id, []):
            due_date = parse_date(
                raw_bill.get("upcoming_payment_date") or raw_bill.get("payment_date")
            )
            if due_date is None or due_date <= anchor:
                continue
            live_bills.append(
                UpcomingBill(
                    id=resource_id(raw_bill) or f"nessie-bill-{account_id}-{len(live_bills)}",
                    name=str(raw_bill.get("nickname") or raw_bill.get("payee") or "Bill"),
                    amount_cents=dollars_to_cents(raw_bill.get("payment_amount", 0)),
                    due_date=due_date,
                    source="nessie_bill",
                    status=str(raw_bill.get("status") or "scheduled"),
                )
            )

    if not accounts:
        raise NessieError("The seeded Nessie customer has no readable accounts.")

    transactions.sort(key=lambda transaction: transaction.date, reverse=True)
    categories = summarize_categories(transactions)
    return CustomerSnapshot(
        customer=Customer(id=customer_id, display_name=display_name),
        accounts=accounts,
        history=History(
            start=history_start,
            end=anchor,
            transactions=transactions,
            categories=categories,
            spending_total_cents=sum(category.total_cents for category in categories),
        ),
        upcoming_bills=sorted(
            [*live_bills, *upcoming_bills(anchor)], key=lambda bill: bill.due_date
        ),
        income_projection=income_projection(anchor, hourly_rate_cents),
        scenario=Scenario(repair_quote_cents=repair_quote_cents),
        source=SourceMetadata(
            banking="nessie",
            simulation_data="seeded_synthetic",
            mode="live",
            message="Banking records were read from the seeded Nessie sandbox; future wage and local schedule entries are forecasts or fixtures.",
        ),
    )
