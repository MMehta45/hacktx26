import argparse
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from app.config import Settings
from app.fixtures import PURCHASE_PATTERN, fixture_transactions, upcoming_bills
from app.nessie import NessieClient, NessieError, dollars_to_cents, resource_id

CUSTOMER_FIRST_NAME = "Maya"
CUSTOMER_LAST_NAME = "Rodriguez"
ACCOUNT_NICKNAME = "OBT Demo Checking"


def is_demo_customer(item: Mapping[str, Any]) -> bool:
    address = item.get("address")
    street_name = address.get("street_name") if isinstance(address, Mapping) else None
    return (
        item.get("first_name") == CUSTOMER_FIRST_NAME
        and item.get("last_name") == CUSTOMER_LAST_NAME
        and street_name == "Lavaca Street"
    )


def created_resource_id(payload: Any) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    direct = resource_id(payload)
    if direct:
        return direct
    nested = payload.get("objectCreated")
    return resource_id(nested) if isinstance(nested, Mapping) else None


def missing_descriptions(
    existing: list[Mapping[str, Any]], desired: list[Mapping[str, Any]]
) -> list[Mapping[str, Any]]:
    existing_descriptions = {str(item.get("description")) for item in existing}
    return [item for item in desired if str(item.get("description")) not in existing_descriptions]


def write_manifest(path: Path, manifest: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(dict(manifest), indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def resolve_after_create(
    *,
    response: Any,
    resource_name: str,
    list_resources: Callable[[], list[dict[str, Any]]],
    matches: Callable[[Mapping[str, Any]], bool],
) -> str:
    created_id = created_resource_id(response)
    if created_id:
        return created_id
    for item in list_resources():
        if matches(item) and (item_id := resource_id(item)):
            return item_id
    raise NessieError(
        f"Nessie acknowledged {resource_name} creation but did not return a readable identifier."
    )


def seed_customer(*, settings: Settings, recreate_account: bool = False) -> dict[str, Any]:
    if not settings.nessie_api_key:
        raise NessieError(
            "NESSIE_API_KEY is missing. Add it directly to ignored backend/.env, then retry."
        )

    manifest_path = settings.seed_manifest_path
    try:
        manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest = dict(manifest_payload) if isinstance(manifest_payload, Mapping) else {}
    except (OSError, json.JSONDecodeError):
        manifest = {}

    with NessieClient(api_key=settings.nessie_api_key, base_url=settings.nessie_base_url) as client:
        customer_id = str(manifest.get("customer_id") or "")
        if customer_id:
            try:
                client.get_customer(customer_id)
            except NessieError as error:
                if error.status_code != 404:
                    raise
                customer_id = ""
        if not customer_id:
            customers = client.list_customers()
            customer = next(
                (item for item in customers if is_demo_customer(item)),
                None,
            )
            customer_id = resource_id(customer) if customer else None
            if not customer_id:
                customer_payload = {
                    "first_name": CUSTOMER_FIRST_NAME,
                    "last_name": CUSTOMER_LAST_NAME,
                    "address": {
                        "street_number": "700",
                        "street_name": "Lavaca Street",
                        "city": "Austin",
                        "state": "TX",
                        "zip": "78701",
                    },
                }
                response = client.create_customer(customer_payload)
                customer_id = resolve_after_create(
                    response=response,
                    resource_name="customer",
                    list_resources=client.list_customers,
                    matches=is_demo_customer,
                )

        account_id = str(manifest.get("account_id") or "")
        if recreate_account and account_id:
            client.delete_account(account_id)
            account_id = ""
            manifest.pop("account_id", None)
            write_manifest(manifest_path, {**manifest, "customer_id": customer_id})
        if account_id:
            try:
                client.get_account(account_id)
            except NessieError as error:
                if error.status_code != 404:
                    raise
                account_id = ""
        if not account_id:
            accounts = client.list_accounts(customer_id)
            account = next(
                (item for item in accounts if item.get("nickname") == ACCOUNT_NICKNAME), None
            )
            account_id = resource_id(account) if account else None
            if not account_id:
                response = client.create_account(
                    customer_id,
                    {
                        "type": "Checking",
                        "nickname": ACCOUNT_NICKNAME,
                        "rewards": 0,
                        "balance": 310,
                    },
                )
                account_id = resolve_after_create(
                    response=response,
                    resource_name="account",
                    list_resources=lambda: client.list_accounts(customer_id),
                    matches=lambda item: item.get("nickname") == ACCOUNT_NICKNAME,
                )

        manifest.update(
            {
                "schema_version": 1,
                "customer_id": customer_id,
                "account_id": account_id,
                "anchor_date": settings.demo_anchor_date.isoformat(),
            }
        )
        write_manifest(manifest_path, manifest)

        category_by_merchant = {
            merchant: category for _, merchant, category, _, _ in PURCHASE_PATTERN
        }
        merchants = client.list_merchants()
        merchant_ids: dict[str, str] = {}
        for merchant_name, category in category_by_merchant.items():
            merchant = next((item for item in merchants if item.get("name") == merchant_name), None)
            merchant_id = resource_id(merchant) if merchant else None
            if not merchant_id:
                response = client.create_merchant({"name": merchant_name, "category": category})
                merchant_id = resolve_after_create(
                    response=response,
                    resource_name=f"merchant {merchant_name}",
                    list_resources=client.list_merchants,
                    matches=lambda item, name=merchant_name: item.get("name") == name,
                )
                merchants.append({"_id": merchant_id, "name": merchant_name, "category": category})
            merchant_ids[merchant_name] = merchant_id

        desired_purchases: list[Mapping[str, Any]] = []
        desired_deposits: list[Mapping[str, Any]] = []
        desired_withdrawals: list[Mapping[str, Any]] = []
        fixture = fixture_transactions(settings.demo_anchor_date)
        for transaction in fixture:
            if transaction.source == "fixture_purchase":
                merchant_name = transaction.merchant_display or "Other"
                desired_purchases.append(
                    {
                        "merchant_id": merchant_ids[merchant_name],
                        "medium": "balance",
                        "purchase_date": transaction.date.isoformat(),
                        "amount": transaction.amount_cents // 100,
                        "status": "completed",
                        "description": f"OBT-M1-{transaction.id}",
                    }
                )
            elif transaction.source == "fixture_deposit":
                desired_deposits.append(
                    {
                        "medium": "balance",
                        "transaction_date": transaction.date.isoformat(),
                        "status": "completed",
                        "amount": transaction.amount_cents // 100,
                        "description": f"OBT-M1-{transaction.id}",
                    }
                )
            else:
                desired_withdrawals.append(
                    {
                        "medium": "balance",
                        "transaction_date": transaction.date.isoformat(),
                        "status": "completed",
                        "amount": transaction.amount_cents // 100,
                        "description": f"OBT-M1-{transaction.id}",
                    }
                )

        # Deposits are inserted first so a sandbox that applies transaction effects has
        # funds available before purchases. Net seeded history is zero, leaving $310.
        existing_deposits = client.list_deposits(account_id)
        for deposit in missing_descriptions(existing_deposits, desired_deposits):
            client.create_deposit(account_id, deposit)

        existing_purchases = client.list_purchases(account_id)
        for purchase in missing_descriptions(existing_purchases, desired_purchases):
            client.create_purchase(account_id, purchase)

        existing_withdrawals = client.list_withdrawals(account_id)
        for withdrawal in missing_descriptions(existing_withdrawals, desired_withdrawals):
            client.create_withdrawal(account_id, withdrawal)

        desired_bills = [
            {
                "status": "pending",
                "payee": bill.name,
                "nickname": f"OBT {bill.name}",
                "payment_date": bill.due_date.isoformat(),
                "recurring_date": bill.due_date.day,
                "payment_amount": bill.amount_cents // 100,
            }
            for bill in upcoming_bills(settings.demo_anchor_date)
        ]
        existing_bills = client.list_bills(account_id)
        existing_bill_names = {str(item.get("nickname")) for item in existing_bills}
        missing_bills = [
            bill for bill in desired_bills if str(bill["nickname"]) not in existing_bill_names
        ]
        for bill in missing_bills:
            client.create_bill(account_id, bill)

        account = client.get_account(account_id)
        purchases_readback = client.list_purchases(account_id)
        deposits_readback = client.list_deposits(account_id)
        withdrawals_readback = client.list_withdrawals(account_id)
        bills_readback = client.list_bills(account_id)
        purchase_count = sum(
            str(item.get("description", "")).startswith("OBT-M1-") for item in purchases_readback
        )
        deposit_count = sum(
            str(item.get("description", "")).startswith("OBT-M1-") for item in deposits_readback
        )
        withdrawal_count = sum(
            str(item.get("description", "")).startswith("OBT-M1-") for item in withdrawals_readback
        )
        bill_count = sum(
            str(item.get("nickname", "")).startswith("OBT ") for item in bills_readback
        )
        final_balance_cents = dollars_to_cents(account.get("balance", 0))
        manifest["merchant_ids"] = merchant_ids
        write_manifest(manifest_path, manifest)
        return {
            "customer_id": customer_id,
            "account_id": account_id,
            "account_balance_cents": final_balance_cents,
            "balance_matches_target": final_balance_cents == 31_000,
            "purchase_count": purchase_count,
            "deposit_count": deposit_count,
            "withdrawal_count": withdrawal_count,
            "bill_count": bill_count,
            "reused": (
                len(missing_descriptions(existing_purchases, desired_purchases)) == 0
                and len(missing_descriptions(existing_deposits, desired_deposits)) == 0
                and len(missing_descriptions(existing_withdrawals, desired_withdrawals)) == 0
                and not missing_bills
            ),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the fictional One Bad Tuesday customer.")
    parser.add_argument(
        "--recreate-account",
        action="store_true",
        help="Delete and recreate the manifest account and its seeded history.",
    )
    args = parser.parse_args()
    try:
        result = seed_customer(settings=Settings(), recreate_account=bool(args.recreate_account))
    except NessieError as error:
        raise SystemExit(f"Seed failed: {error}") from error
    action = "Reused" if result["reused"] else "Seeded"
    print(
        f"{action} Nessie customer and account; read back "
        f"{result['purchase_count']} purchases, {result['deposit_count']} deposits, "
        f"{result['withdrawal_count']} withdrawals, and {result['bill_count']} bills. "
        f"Final balance: ${result['account_balance_cents'] / 100:,.2f}."
    )
    if not result["balance_matches_target"]:
        raise SystemExit(
            "Seed readback did not match the $310.00 target. "
            "Do not use this profile until the sandbox balance behavior is reviewed."
        )


if __name__ == "__main__":
    main()
