from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models import CustomerSnapshot
from app.snapshot import SnapshotUnavailable, get_snapshot

settings = get_settings()

app = FastAPI(title="One Bad Tuesday API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str | dict[str, bool]]:
    """Report API availability and whether optional integrations are configured."""

    return {
        "status": "ok",
        "service": "one-bad-tuesday-api",
        "integrations": settings.integration_status,
    }


@app.get("/api/customer/snapshot", response_model=CustomerSnapshot)
def customer_snapshot(
    display_name: Annotated[str, Query(min_length=1, max_length=80)] = "Maya Torres",
    hourly_rate_cents: Annotated[int, Query(gt=0, le=50_000)] = 2_000,
    repair_quote_cents: Annotated[int, Query(ge=10_000, le=150_000)] = 40_000,
) -> CustomerSnapshot:
    try:
        return get_snapshot(
            settings=settings,
            display_name=display_name.strip(),
            hourly_rate_cents=hourly_rate_cents,
            repair_quote_cents=repair_quote_cents,
        )
    except SnapshotUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
