from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.research_models import Evidence, ResearchContext


def assess_transit(
    evidence: list[Evidence], context: ResearchContext, shift_dates: list[date]
) -> tuple[str, str]:
    """A route covers a shift only with timely outbound and return legs for every date."""
    if (
        not context.home_location
        or not context.work_location
        or not context.shift_start_local
        or not context.shift_end_local
        or not shift_dates
    ):
        return "unknown", "Origin, destination, both shift times, and affected dates are required."
    for shift_date in shift_dates:
        shift_start = datetime.combine(
            shift_date, context.shift_start_local, ZoneInfo(context.timezone)
        )
        shift_end = datetime.combine(
            shift_date, context.shift_end_local, ZoneInfo(context.timezone)
        )
        outbound = [
            item
            for item in evidence
            if item.source_type == "transit_directions"
            and item.transit_request_kind == "arrive_by"
            and item.transit_request_date == shift_date
            and context.home_location.casefold() in item.query.casefold()
            and context.work_location.casefold() in item.query.casefold()
        ]
        inbound = [
            item
            for item in evidence
            if item.source_type == "transit_directions"
            and item.transit_request_kind == "depart_at"
            and item.transit_request_date == shift_date
            and context.home_location.casefold() in item.query.casefold()
            and context.work_location.casefold() in item.query.casefold()
        ]
        if outbound and all(
            item.transit_arrival and item.transit_arrival > shift_start for item in outbound
        ):
            earliest = min(item.transit_arrival for item in outbound if item.transit_arrival)
            return (
                "adjustment",
                f"The returned arrive-by search still arrived at {earliest:%H:%M}; this checked itinerary misses the shift, but does not prove all transit is unavailable. An earlier departure or manager-approved shift adjustment needs checking.",
            )
        if inbound and all(
            item.transit_departure and item.transit_departure < shift_end for item in inbound
        ):
            return "false", "Provider return itineraries depart before the shift ends."
        if not any(
            item.transit_arrival and item.transit_arrival <= shift_start for item in outbound
        ):
            return "unknown", "No timed outbound itinerary verifies on-time arrival."
        if not any(
            item.transit_departure and item.transit_departure >= shift_end for item in inbound
        ):
            return "unknown", "No timed return itinerary verifies travel after the shift."
    return (
        "verified",
        "Provider directions include on-time outbound and return itineraries for each affected shift.",
    )
