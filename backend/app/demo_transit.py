"""Narrow deterministic transit evidence for the HackTX Maya demo.

This is intentionally not provider data.  It keeps the demo usable while live
directions are unreliable, and it is only emitted for the exact fictional
Maya scenario documented in Build 04.4.
"""

from datetime import UTC, datetime, time
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from app.research_models import Evidence, ResearchContext, TransitLeg

DEMO_NAME = "maya rodriguez"
DEMO_HOME = "3810 n lamar blvd, austin, tx 78756"
DEMO_WORK = "525 n lamar blvd, austin, tx 78703"
ROUTE = "CapMetro Route 5"


def _normalized(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def matches_maya_demo(display_name: str, context: ResearchContext) -> bool:
    return (
        _normalized(display_name) == DEMO_NAME
        and _normalized(context.home_location) == DEMO_HOME
        and _normalized(context.work_location) == DEMO_WORK
        and context.timezone == "America/Chicago"
        and context.shift_start_local == time(8, 0)
        and context.shift_end_local == time(16, 0)
        and context.workdays == ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    )


def _maps_link(origin: str, destination: str) -> str:
    # A manual navigation aid only; the deterministic timings below are not
    # asserted to have been returned by Google Maps.
    return "https://www.google.com/maps/dir/?" + urlencode(
        {"api": "1", "origin": origin, "destination": destination, "travelmode": "transit"}
    )


def maya_route_5_fixture(display_name: str, context: ResearchContext, simulation: object) -> list[Evidence]:
    """Return paired Route 5 evidence for currently missed weekday shifts only."""
    if not matches_maya_demo(display_name, context):
        return []
    zone = ZoneInfo(context.timezone)
    now = datetime.now(UTC)
    evidence: list[Evidence] = []
    for shift in simulation.shift_records:
        if shift.attendance != "projected_missed" or shift.date.weekday() >= 5:
            continue
        outbound_departure = datetime.combine(shift.date, time(7, 35), zone)
        outbound_arrival = datetime.combine(shift.date, time(7, 52), zone)
        return_departure = datetime.combine(shift.date, time(16, 17), zone)
        common = {
            "provider_engine": "demo_scenario_assumption",
            "source_domain": "demo_scenario_assumption",
            "query": "Build 04.4 deterministic Maya Route 5 commute assumption",
            "retrieved_at": now,
            "facts_supported": [
                "Synthetic demo assumption: CapMetro Route 5 can preserve this 08:00–16:00 weekday shift.",
                "One-way fare is modeled as $1.25; round-trip cost is $2.50 per workday.",
            ],
            "limitations": [
                "Explicit synthetic demo scenario assumption; not provider-observed or externally verified.",
                "Personal ability to use Route 5 still requires Maya's confirmation.",
                "Stops, walking instructions, transfers, and return arrival time were not supplied and are not inferred.",
            ],
            "route_numbers": [ROUTE],
            "transit_origin_matches": True,
            "transit_destination_matches": True,
            "transit_time_constraint_honored": True,
            "observed_cost_cents": 125,
            "fare_source": "Explicit Build 04.4 deterministic demo scenario assumption",
            "fare_certainty": "demo_scenario_assumption",
        }
        evidence.append(Evidence(
            id=f"demo-route-5-outbound-{shift.date.isoformat()}",
            source_type="transit_directions",
            title=f"Demo assumption: Route 5 outbound on {shift.date:%b %-d}",
            url=_maps_link(context.home_location or "", context.work_location or ""),
            transit_request_kind="arrive_by",
            transit_request_date=shift.date,
            transit_origin=context.home_location,
            transit_destination=context.work_location,
            transit_requested_origin=context.home_location,
            transit_requested_destination=context.work_location,
            transit_departure=outbound_departure,
            transit_arrival=outbound_arrival,
            transit_duration_minutes=17,
            transit_legs=[TransitLeg(mode="transit", route=ROUTE, departure=outbound_departure, arrival=outbound_arrival, duration_minutes=17)],
            **common,
        ))
        evidence.append(Evidence(
            id=f"demo-route-5-return-{shift.date.isoformat()}",
            source_type="transit_directions",
            title=f"Demo assumption: Route 5 return on {shift.date:%b %-d}",
            url=_maps_link(context.work_location or "", context.home_location or ""),
            transit_request_kind="depart_at",
            transit_request_date=shift.date,
            transit_origin=context.work_location,
            transit_destination=context.home_location,
            transit_requested_origin=context.work_location,
            transit_requested_destination=context.home_location,
            transit_departure=return_departure,
            transit_arrival=None,
            transit_duration_minutes=None,
            transit_legs=[TransitLeg(mode="transit", route=ROUTE, departure=return_departure)],
            **common,
        ))
    return evidence
