import { describe, expect, it } from "vitest";

import { AUSTIN_DEMO_CONTEXT, filterUnsupportedMechanicRecommendations, researchRequestBody } from "./research";
import type { ResearchResult } from "@/types/research";

describe("Austin demo research context", () => {
  it("prefills the locked routing locations and shift times", () => {
    expect(AUSTIN_DEMO_CONTEXT).toMatchObject({
      home: "3810 N Lamar Blvd, Austin, TX 78756",
      work: "525 N Lamar Blvd, Austin, TX 78703",
      shiftStart: "08:00",
      shiftEnd: "16:00",
      fictionalEmployer: "Cedarstone Services",
    });
  });

  it("sends edited routing fields to the backend contract", () => {
    const body = researchRequestBody(
      {
        displayName: "Maya Rodriguez",
        hourlyRateCents: 2000,
        repairQuoteCents: 40000,
        breakdownDate: "2026-10-26",
      },
      { home: "Edited origin", work: "Edited work", shiftStart: "08:30", shiftEnd: "16:30" },
      false,
    );
    expect(body.context).toMatchObject({
      home_location: "Edited origin",
      work_location: "Edited work",
      shift_start_local: "08:30",
      shift_end_local: "16:30",
      remote_work_eligibility: "unknown",
    });
    expect(body.scenario.breakdown_date).toBe("2026-10-26");
  });

  it("suppresses generic or negative-only mechanic recommendations", () => {
    const result = {
      evidence: [
        { id: "shop", source_type: "place" },
        { id: "negative", source_type: "place_review", parent_place_evidence_id: "shop", positive_price_review_snippets: [], negative_price_review_snippets: ["Too expensive"] },
        { id: "positive", source_type: "place_review", parent_place_evidence_id: "shop", positive_price_review_snippets: ["Fair price"] },
      ],
      candidate_actions: [
        { id: "generic", mechanism: "repair_affordability", evidence_ids: ["shop"] },
        { id: "negative-only", mechanism: "repair_affordability", evidence_ids: ["shop", "negative"] },
        { id: "qualified", mechanism: "repair_affordability", evidence_ids: ["shop", "positive"] },
        { id: "remote", mechanism: "income_preservation", evidence_ids: [] },
      ],
    } as unknown as ResearchResult;
    expect(filterUnsupportedMechanicRecommendations(result).candidate_actions.map((item) => item.id)).toEqual(["qualified", "remote"]);
  });
});
