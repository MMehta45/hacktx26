from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models import CustomerSnapshot
from app.research_models import ResearchRequest, ResearchResponse
from app.research_service import run_research
from app.simulation import simulate
from app.simulation_models import CrisisSimulationRequest, CrisisSimulationResponse
from app.snapshot import SnapshotUnavailable, get_snapshot

settings = get_settings()

app = FastAPI(title="One Bad Tuesday API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
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
    display_name: Annotated[str, Query(min_length=1, max_length=80)] = "Maya Rodriguez",
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


@app.post("/api/simulations/crisis", response_model=CrisisSimulationResponse)
def crisis_simulation(request: CrisisSimulationRequest) -> CrisisSimulationResponse:
    """Refresh the read-only banking snapshot and simulate an untreated crisis."""

    try:
        snapshot = get_snapshot(
            settings=settings,
            display_name=request.display_name.strip(),
            hourly_rate_cents=request.hourly_rate_cents,
            repair_quote_cents=request.repair_quote_cents,
        )
        return CrisisSimulationResponse(
            snapshot=snapshot,
            simulation=simulate(snapshot, request, actions=[]),
        )
    except SnapshotUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/research/interventions", response_model=ResearchResponse)
def research_interventions(request: ResearchRequest) -> ResearchResponse:
    try:
        return run_research(request, settings)
    except SnapshotUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
