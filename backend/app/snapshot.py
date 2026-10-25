import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.config import Settings
from app.fixtures import fixture_snapshot
from app.models import CustomerSnapshot
from app.nessie import NessieClient, NessieError, normalize_snapshot, resource_id


class SnapshotUnavailable(RuntimeError):
    pass


def read_manifest(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return dict(payload) if isinstance(payload, Mapping) else None


def get_snapshot(
    *, settings: Settings, display_name: str, hourly_rate_cents: int, repair_quote_cents: int
) -> CustomerSnapshot:
    fallback_reason = "No Nessie key is configured. Showing the deterministic local fixture."
    if settings.demo_data_mode == "fixture":
        fallback_reason = "Fixture mode is selected explicitly. No Nessie request was made."
    elif settings.nessie_api_key:
        manifest = read_manifest(settings.seed_manifest_path)
        if manifest and manifest.get("customer_id") and manifest.get("account_id"):
            try:
                with NessieClient(
                    api_key=settings.nessie_api_key, base_url=settings.nessie_base_url
                ) as client:
                    customer = client.get_customer(str(manifest["customer_id"]))
                    manifest_account_id = str(manifest["account_id"])
                    accounts = [
                        account
                        for account in client.list_accounts(str(manifest["customer_id"]))
                        if resource_id(account) == manifest_account_id
                    ]
                    if not accounts:
                        raise NessieError(
                            "The seeded account is not attached to the configured customer. "
                            "Rerun the seeder."
                        )
                    account_ids = [
                        account_id
                        for account in accounts
                        if (account_id := resource_id(account)) is not None
                    ]
                    merchants = {
                        merchant_id: merchant
                        for merchant in client.list_merchants()
                        if (merchant_id := resource_id(merchant)) is not None
                    }
                    return normalize_snapshot(
                        anchor=settings.demo_anchor_date,
                        display_name=display_name,
                        hourly_rate_cents=hourly_rate_cents,
                        repair_quote_cents=repair_quote_cents,
                        customer=customer,
                        accounts_raw=accounts,
                        purchases_by_account={
                            account_id: client.list_purchases(account_id)
                            for account_id in account_ids
                        },
                        deposits_by_account={
                            account_id: client.list_deposits(account_id)
                            for account_id in account_ids
                        },
                        withdrawals_by_account={
                            account_id: client.list_withdrawals(account_id)
                            for account_id in account_ids
                        },
                        bills_by_account={
                            account_id: client.list_bills(account_id) for account_id in account_ids
                        },
                        merchants=merchants,
                    )
            except NessieError as error:
                if settings.demo_data_mode == "nessie":
                    raise SnapshotUnavailable(str(error)) from error
                fallback_reason = f"{error} Showing the deterministic local fixture instead."
        else:
            fallback_reason = (
                "A Nessie key is configured, but the local seed manifest is missing. "
                "Run the seed command; showing the fixture meanwhile."
            )
    elif settings.demo_data_mode == "nessie":
        raise SnapshotUnavailable(
            "Nessie mode requires NESSIE_API_KEY in backend/.env. Add it locally and restart."
        )

    return fixture_snapshot(
        anchor=settings.demo_anchor_date,
        display_name=display_name,
        hourly_rate_cents=hourly_rate_cents,
        repair_quote_cents=repair_quote_cents,
        message=fallback_reason,
    )
