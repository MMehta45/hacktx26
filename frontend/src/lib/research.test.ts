import { describe, expect, it } from "vitest";

import { AUSTIN_DEMO_CONTEXT, researchRequestBody } from "./research";

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
        affectedShiftCount: 2,
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
  });
});
