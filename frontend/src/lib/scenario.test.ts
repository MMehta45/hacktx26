import { describe, expect, it } from "vitest";

import { wageInputToCents, wagePreview } from "./scenario";

describe("scenario wage input", () => {
  it("calculates five eight-hour shifts from exact cents", () => {
    const cents = wageInputToCents("21.75");

    expect(cents).toBe(2175);
    if (cents === null) throw new Error("Expected a valid wage");
    expect(wagePreview(cents)).toEqual({
      grossPerShiftCents: 17_400,
      grossWeeklyCents: 87_000,
      estimatedNetPerShiftCents: 13_920,
      estimatedNetWeeklyCents: 69_600,
    });
  });

  it("rejects non-positive, over-precise, and excessive wages", () => {
    expect(wageInputToCents("0")).toBeNull();
    expect(wageInputToCents("20.001")).toBeNull();
    expect(wageInputToCents("500.01")).toBeNull();
  });
});
