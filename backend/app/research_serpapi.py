import hashlib
import json
import re
import time
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import httpx

from app.research_models import Evidence, clean_url


class SearchFailure(RuntimeError):
    pass


class SearchBudgetExceeded(SearchFailure):
    pass


def _safe_text(value: object, limit: int = 350) -> str:
    text = re.sub(r"https?://\S+", "[link]", str(value or ""))
    text = re.sub(r"(?i)(api[_-]?key|token|secret)\s*[:=]\s*\S+", "[redacted]", text)
    return text[:limit]


def _review_snippets(row: dict) -> list[str]:
    values: list[str] = []
    for key in ("reviews", "reviews_original", "review_snippets"):
        raw = row.get(key)
        if not isinstance(raw, list):
            continue
        for item in raw[:3]:
            text = item.get("snippet") or item.get("text") if isinstance(item, dict) else item
            if text:
                values.append(_safe_text(text, 220))
    return list(dict.fromkeys(values))


class SerpResearch:
    def __init__(self, api_key: str, *, max_calls: int = 6, client: httpx.Client | None = None):
        self.api_key = api_key
        self.max_calls = max_calls
        self.client = client or httpx.Client(timeout=12)
        self.owns_client = client is None
        self.calls = 0
        self.cache_hits = 0
        self.cache: dict[str, tuple[float, list[Evidence]]] = {}

    def close(self) -> None:
        if self.owns_client:
            self.client.close()

    def search(self, tool: str, args: dict[str, str], *, max_attempts: int = 2) -> list[Evidence]:
        allowed = {
            "search_web": {"query", "location", "reason"},
            "search_places": {"query", "location", "coordinates", "reason"},
            "search_reviews": {"data_id", "place_title", "parent_evidence_id", "reason"},
            "find_transit": {"origin", "destination", "arrive_by_iso", "depart_at_iso", "reason"},
        }
        if tool not in allowed or set(args) - allowed[tool]:
            raise SearchFailure("Unsupported research tool arguments")
        if any(not isinstance(value, str) or len(value) > 180 for value in args.values()):
            raise SearchFailure("Research query is invalid or too long")
        engine = {
            "search_web": "google",
            "search_places": "google_maps",
            "search_reviews": "google_maps_reviews",
            "find_transit": "google_maps_directions",
        }[tool]
        params: dict[str, str] = {"engine": engine, "hl": "en"}
        if tool == "search_reviews":
            if not args.get("data_id"):
                raise SearchFailure("Review search needs a provider business identifier")
            params.update(data_id=args["data_id"], sort_by="qualityScore")
            if args.get("place_title"):
                params["place_title"] = args["place_title"]
            if args.get("parent_evidence_id"):
                params["parent_evidence_id"] = args["parent_evidence_id"]
        elif tool == "find_transit":
            if not args.get("origin") or not args.get("destination"):
                raise SearchFailure("Transit needs origin and destination")
            params.update(start_addr=args["origin"], end_addr=args["destination"], travel_mode="3")
            for key, prefix in (("arrive_by_iso", "arrive_by"), ("depart_at_iso", "depart_at")):
                if args.get(key):
                    try:
                        stamp = datetime.fromisoformat(args[key])
                        if stamp.tzinfo is None:
                            raise ValueError
                        params["time"] = f"{prefix}:{int(stamp.timestamp())}"
                    except ValueError as error:
                        raise SearchFailure("Transit time must be timezone-aware ISO") from error
            if args.get("arrive_by_iso") and args.get("depart_at_iso"):
                raise SearchFailure("Choose one transit timing constraint")
        else:
            if not args.get("query"):
                raise SearchFailure("Search query is required")
            location = args.get("location")
            params["q"] = (
                f"{args['query']} in {location}"[:150]
                if tool == "search_places" and location
                else args["query"][:150]
            )
            if location and tool == "search_web":
                params["location"] = args["location"]
            if tool == "search_places" and args.get("coordinates"):
                params["ll"] = args["coordinates"]
        key = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
        cached = self.cache.get(key)
        if cached and time.monotonic() - cached[0] < 3600:
            self.cache_hits += 1
            return cached[1]
        for attempt in range(max_attempts):
            if self.calls >= self.max_calls:
                raise SearchBudgetExceeded("SerpApi request budget reached")
            self.calls += 1
            try:
                response = self.client.get(
                    "https://serpapi.com/search.json", params={**params, "api_key": self.api_key}
                )
                if response.status_code in {429, 500, 502, 503, 504} and attempt + 1 < max_attempts:
                    time.sleep(0.4)
                    continue
                response.raise_for_status()
                payload = response.json()
                if payload.get("error"):
                    raise SearchFailure("SerpApi returned an error; inspect account quota or query")
                evidence = self._normalize(engine, params, payload)
                self.cache[key] = (time.monotonic(), evidence)
                return evidence
            except (httpx.HTTPError, ValueError) as error:
                if attempt + 1 < max_attempts and isinstance(error, httpx.TimeoutException):
                    time.sleep(0.4)
                    continue
                raise SearchFailure("SerpApi request failed or timed out") from error
        raise SearchFailure("SerpApi request failed")

    def _normalize(self, engine: str, params: dict[str, str], payload: dict) -> list[Evidence]:
        if engine == "google_maps_reviews":
            return self._normalize_reviews(params, payload)
        rows = (
            payload.get("organic_results", [])
            if engine == "google"
            else payload.get("local_results", [])
            if engine == "google_maps"
            else payload.get("directions", [])
        )
        if not isinstance(rows, list):
            return []
        output: list[Evidence] = []
        query = (
            params.get("q")
            or f"{params.get('start_addr')} → {params.get('end_addr')} ({params.get('time', 'unscheduled')})"
        )
        for row in rows[:5]:
            if not isinstance(row, dict):
                continue
            url = clean_url(
                row.get("link")
                or row.get("website")
                or row.get("place_id_search")
                or payload.get("search_metadata", {}).get("google_maps_directions_url")
            )
            title = _safe_text(
                row.get("title") or row.get("name") or row.get("via") or "Listed result", 120
            )
            reviews = _review_snippets(row)
            snippet = _safe_text(
                row.get("snippet")
                or row.get("description")
                or (reviews[0] if reviews else None)
                or row.get("address")
                or ""
            )
            stable = hashlib.sha256(f"{engine}|{url}|{title}|{query}".encode()).hexdigest()[:12]
            cost = row.get("cost")
            amount = None
            if isinstance(cost, dict):
                cost = cost.get("amount") or cost.get("text")
            if (
                isinstance(cost, (int, float))
                and not isinstance(cost, bool)
                and cost >= 0
                and row.get("currency") == "USD"
            ):
                amount = int(
                    (Decimal(str(cost)) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP)
                )
            elif isinstance(cost, str) and re.fullmatch(r"\$\d+(?:\.\d{1,2})?", cost.strip()):
                amount = int(
                    (Decimal(cost.strip()[1:]) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP)
                )
            arrival = departure = None
            request_kind = None
            request_date = None
            route_numbers: list[str] = []
            transit_stops: list[str] = []
            walking_distance = 0
            transit_trip_count = 0
            if engine == "google_maps_directions" and params.get("time"):
                request_kind = params["time"].split(":", 1)[0]
                date_local = datetime.fromtimestamp(
                    int(params["time"].split(":", 1)[1]), ZoneInfo("America/Chicago")
                ).date()
                request_date = date_local
                for field, name in (("start_time", "departure"), ("end_time", "arrival")):
                    raw = row.get(field)
                    if isinstance(raw, str):
                        try:
                            parsed = datetime.strptime(
                                raw.replace("\u202f", " "), "%I:%M %p"
                            ).time()
                            value = datetime.combine(
                                date_local, parsed, ZoneInfo("America/Chicago")
                            )
                            if name == "departure":
                                departure = value
                            else:
                                arrival = value
                        except ValueError:
                            pass
                trips = row.get("trips", [])
                if isinstance(trips, list):
                    for trip in trips:
                        if not isinstance(trip, dict):
                            continue
                        if str(trip.get("travel_mode", "")).casefold() == "transit":
                            transit_trip_count += 1
                            if trip.get("title"):
                                route_numbers.append(_safe_text(trip["title"], 80))
                            for stop_key in ("start_stop", "end_stop"):
                                stop = trip.get(stop_key)
                                if isinstance(stop, dict) and stop.get("name"):
                                    transit_stops.append(_safe_text(stop["name"], 100))
                        elif str(trip.get("travel_mode", "")).casefold() == "walking":
                            distance = trip.get("distance")
                            if isinstance(distance, (int, float)) and distance >= 0:
                                walking_distance += int(distance)
            output.append(
                Evidence(
                    id=f"evidence-{stable}",
                    source_type="web"
                    if engine == "google"
                    else "place"
                    if engine == "google_maps"
                    else "transit_directions",
                    provider_engine=engine,
                    title=title,
                    url=url,
                    query=query,
                    retrieved_at=datetime.now(UTC),
                    facts_supported=[
                        "Provider listed this result; verify service and current terms with the source."
                    ],
                    limitations=[
                        "Listing does not establish personal eligibility, availability, appointment, or approval."
                    ],
                    snippet=snippet,
                    source_domain=urlsplit(url).hostname if url else None,
                    observed_cost_cents=amount,
                    transit_arrival=arrival,
                    transit_departure=departure,
                    transit_request_kind=request_kind,
                    transit_request_date=request_date,
                    place_address=_safe_text(row.get("address"), 180) or None,
                    rating=float(row["rating"])
                    if isinstance(row.get("rating"), (int, float))
                    else None,
                    review_snippets=reviews,
                    review_count=int(row["reviews"])
                    if isinstance(row.get("reviews"), int)
                    else None,
                    provider_business_id=str(row.get("data_id") or row.get("place_id"))
                    if row.get("data_id") or row.get("place_id")
                    else None,
                    route_numbers=list(dict.fromkeys(route_numbers)),
                    transfer_count=max(0, transit_trip_count - 1)
                    if engine == "google_maps_directions" and transit_trip_count
                    else None,
                    walking_distance_meters=walking_distance
                    if engine == "google_maps_directions"
                    else None,
                    transit_stops=list(dict.fromkeys(transit_stops)),
                )
            )
        return output

    def _normalize_reviews(self, params: dict[str, str], payload: dict) -> list[Evidence]:
        rows = payload.get("reviews", [])
        if not isinstance(rows, list):
            return []
        positive_terms = (
            "affordable",
            "fair price",
            "fair pricing",
            "reasonable price",
            "reasonably priced",
            "good value",
        )
        negative_terms = ("overcharged", "expensive", "hidden fee", "hidden fees", "too much")
        transparency_terms = ("transparent", "estimate", "explained", "upfront", "honest")
        snippets: list[str] = []
        positive: list[str] = []
        negative: list[str] = []
        transparent = 0
        for row in rows[:20]:
            if not isinstance(row, dict):
                continue
            raw = row.get("snippet") or row.get("text") or row.get("review")
            if not raw:
                continue
            snippet = _safe_text(raw, 300)
            snippets.append(snippet)
            folded = snippet.casefold()
            if any(term in folded for term in positive_terms):
                positive.append(snippet)
            if any(term in folded for term in negative_terms):
                negative.append(snippet)
            if any(term in folded for term in transparency_terms):
                transparent += 1
        if not snippets:
            return []
        total = len(snippets)
        price_score = min(1.0, (len(positive) + len(negative)) / max(3, total))
        transparency_score = min(1.0, transparent / max(2, total))
        confidence = (
            "moderate"
            if len(positive) + len(negative) >= 3
            else "low"
            if positive or negative
            else "none"
        )
        stable = hashlib.sha256(f"reviews|{params['data_id']}".encode()).hexdigest()[:12]
        url = clean_url(payload.get("search_metadata", {}).get("google_maps_reviews_url"))
        return [
            Evidence(
                id=f"evidence-{stable}",
                source_type="place_review",
                provider_engine="google_maps_reviews",
                title=f"Price-related reviews for {params.get('place_title', 'repair shop')}",
                url=url,
                query=f"Google Maps reviews for {params.get('place_title', params['data_id'])}",
                retrieved_at=datetime.now(UTC),
                facts_supported=[
                    "Provider returned these review excerpts for the selected listing."
                ],
                limitations=[
                    "Review language helps prioritize estimate requests; it is not a quote for Maya's repair."
                ],
                snippet=snippets[0],
                review_snippets=snippets,
                review_count=len(snippets),
                provider_business_id=params["data_id"],
                parent_place_evidence_id=params.get("parent_evidence_id"),
                positive_price_review_snippets=positive,
                negative_price_review_snippets=negative,
                price_evidence_score=price_score,
                transparency_evidence_score=transparency_score,
                affordability_confidence=confidence,
                source_domain=urlsplit(url).hostname if url else "google.com",
            )
        ]
