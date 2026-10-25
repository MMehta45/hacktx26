import { afterEach, describe, expect, it, vi } from "vitest";

import { GET, POST } from "./[...path]/route";

afterEach(() => vi.unstubAllGlobals());

describe("recovery proxy", () => {
  it("forwards recovery session creation to FastAPI", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: "session-1", version: 1 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const response = await POST(
      new Request("http://localhost/api/recovery/sessions", { method: "POST", body: "{}" }),
      { params: Promise.resolve({ path: ["sessions"] }) },
    );
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ id: "session-1", version: 1 });
    expect(fetchMock.mock.calls[0][0]).toBe("http://127.0.0.1:8000/api/recovery/sessions");
  });

  it("distinguishes a stale session from a backend missing Build 04 routes", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "Not Found" }), {
          status: 404,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
    const stale = await GET(new Request("http://localhost/api/recovery/sessions/old"), {
      params: Promise.resolve({ path: ["sessions", "old"] }),
    });
    expect(stale.status).toBe(404);
    expect(await stale.json()).toMatchObject({ code: "RECOVERY_SESSION_NOT_FOUND" });

    const missingRoute = await POST(
      new Request("http://localhost/api/recovery/sessions", { method: "POST", body: "{}" }),
      { params: Promise.resolve({ path: ["sessions"] }) },
    );
    expect(missingRoute.status).toBe(503);
    expect(await missingRoute.json()).toMatchObject({ code: "RECOVERY_ROUTE_MISSING" });
  });
});
