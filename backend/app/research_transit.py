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
            and item.transit_origin_matches is True
            and item.transit_destination_matches is True
        ]
        inbound = [
            item
            for item in evidence
            if item.source_type == "transit_directions"
            and item.transit_request_kind == "depart_at"
            and item.transit_request_date == shift_date
            and item.transit_origin_matches is True
            and item.transit_destination_matches is True
        ]
        dated = [
            item
            for item in evidence
            if item.source_type == "transit_directions"
            and item.transit_request_date == shift_date
        ]
        if dated and not outbound and not inbound:
            return "unknown", "Provider directions did not verify the requested commute endpoints."
        if outbound and all(
            item.transit_arrival and item.transit_arrival > shift_start for item in outbound
        ):
            earliest = min(item.transit_arrival for item in outbound if item.transit_arrival)
            return (
                "adjustment",
                f"The returned arrive-by search still arrived at {earliest:%H:%M}; this checked itinerary misses the shift, but does not prove all transit is unavailable. An earlier departure or manager-approved shift adjustment needs checking.",
            )
        if any(item.transit_time_constraint_honored is False for item in [*outbound, *inbound]):
            return (
                "unknown",
                "The provider returned itineraries but did not honor the requested shift-time constraint.",
            )
        if inbound and all(
            item.transit_departure and item.transit_departure < shift_end for item in inbound
        ):
            return "false", "Provider return itineraries depart before the shift ends."
        if not any(
            item.transit_arrival
            and item.transit_arrival <= shift_start
            and item.transit_time_constraint_honored is True
            for item in outbound
        ):
            return "unknown", "No timed outbound itinerary verifies on-time arrival."
        if not any(
            item.transit_departure
            and item.transit_departure >= shift_end
            and item.transit_time_constraint_honored is True
            for item in inbound
        ):
            return "unknown", "No timed return itinerary verifies travel after the shift."
        if not any(item.observed_cost_cents is not None for item in outbound) or not any(
            item.observed_cost_cents is not None for item in inbound
        ):
            return "unknown", "A complete round-trip fare was not returned, so cost remains unknown."
    return (
        "verified",
        "Provider directions include on-time outbound and return itineraries for each affected shift.",
    )
