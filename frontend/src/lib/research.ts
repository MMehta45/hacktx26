import type { ResearchResult } from "@/types/research";

export const AUSTIN_DEMO_CONTEXT = {
  city: "Austin, TX",
  timezone: "America/Chicago",
  home: "3810 N Lamar Blvd, Austin, TX 78756",
  work: "525 N Lamar Blvd, Austin, TX 78703",
  shiftStart: "08:00",
  shiftEnd: "16:00",
  fictionalEmployer: "Cedarstone Services",
  position: "Hourly Customer Support Specialist",
} as const;

export type RouteContext = {
  home: string;
  work: string;
  shiftStart: string;
  shiftEnd: string;
};

export function filterUnsupportedMechanicRecommendations(result: ResearchResult): ResearchResult {
  const evidence = new Map(result.evidence.map((item) => [item.id, item]));
  return {
    ...result,
    evidence: result.evidence.map((item) => ({
      ...item,
      transit_legs: item.transit_legs?.map((leg) => ({ ...leg, route_name: leg.route })),
    })),
    candidate_actions: result.candidate_actions.filter((candidate) => {
      if (candidate.mechanism !== "repair_affordability") return true;
      const cited = candidate.evidence_ids.map((id) => evidence.get(id)).filter(Boolean);
      const placeIds = new Set(cited.filter((item) => item?.source_type === "place").map((item) => item?.id));
      return cited.some(
        (item) => item?.source_type === "place_review"
          && (item.positive_price_review_snippets?.length ?? 0) > 0
          && Boolean(item.parent_place_evidence_id && placeIds.has(item.parent_place_evidence_id)),
      );
    }),
  };
}

export function researchRequestBody(
  scenario: {
    displayName: string;
    hourlyRateCents: number;
    repairQuoteCents: number;
    breakdownDate: string;
  },
  route: RouteContext,
  forceRefresh: boolean,
) {
  return {
    scenario: {
      display_name: scenario.displayName,
      hourly_rate_cents: scenario.hourlyRateCents,
      repair_quote_cents: scenario.repairQuoteCents,
      breakdown_date: scenario.breakdownDate,
    },
    context: {
      city: AUSTIN_DEMO_CONTEXT.city,
      timezone: AUSTIN_DEMO_CONTEXT.timezone,
      home_location: route.home || null,
      work_location: route.work || null,
      shift_start_local: route.shiftStart || null,
      shift_end_local: route.shiftEnd || null,
      fictional_employer: AUSTIN_DEMO_CONTEXT.fictionalEmployer,
      job_context: "Hourly Customer Support Specialist; normally onsite",
      remote_work_eligibility: "unknown",
      work_equipment_availability: "unknown",
      shift_flexibility: "unknown",
      make_up_hours_ability: "unknown",
      workdays: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
      primary_transportation: "Personal car",
    },
    force_refresh: forceRefresh,
  };
}
