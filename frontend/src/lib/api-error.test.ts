import { describe, expect, it } from "vitest";

import { backendErrorMessage } from "./api-error";

describe("backendErrorMessage", () => {
  it("formats FastAPI validation issues instead of object coercion", () => {
    expect(
      backendErrorMessage(
        {
          detail: [
            {
              loc: ["body", "breakdown_date"],
              msg: "Extra inputs are not permitted",
            },
          ],
        },
        422,
      ),
    ).toBe("breakdown_date: Extra inputs are not permitted");
  });

  it("retains string details and has a safe fallback", () => {
    expect(backendErrorMessage({ detail: "Snapshot unavailable" }, 503)).toBe(
      "Snapshot unavailable",
    );
    expect(backendErrorMessage({}, 500)).toBe("Backend returned 500");
  });
});
