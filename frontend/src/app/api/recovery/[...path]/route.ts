import { NextResponse } from "next/server";

import { backendErrorMessage } from "@/lib/api-error";

const backendUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

async function forward(request: Request, segments: string[], method: "GET" | "POST") {
  try {
    const response = await fetch(`${backendUrl}/api/recovery/${segments.join("/")}`, {
      method,
      headers: method === "POST" ? { "Content-Type": "application/json" } : undefined,
      body: method === "POST" ? await request.text() : undefined,
      cache: "no-store",
      signal: AbortSignal.timeout(130000),
    });
    const body = (await response.json().catch(() => null)) as unknown;
    if (!response.ok) {
      if (response.status === 404) {
        const savedSessionLookup = method === "GET" && segments[0] === "sessions" && segments.length === 2;
        const missingCreateRoute = method === "POST" && segments.join("/") === "sessions";
        return NextResponse.json(
          {
            code: savedSessionLookup ? "RECOVERY_SESSION_NOT_FOUND" : "RECOVERY_ROUTE_MISSING",
            message: savedSessionLookup
              ? "This saved recovery session no longer exists. A fresh session will be created."
              : missingCreateRoute
                ? "The configured FastAPI process does not expose Build 04 recovery routes. Restart the backend from this repository and verify BACKEND_URL."
                : "The configured FastAPI process does not recognize this recovery endpoint. Restart the current backend and retry.",
          },
          { status: savedSessionLookup ? 404 : 503 },
        );
      }
      return NextResponse.json(
        { code: response.status === 422 ? "RECOVERY_PAYLOAD_INVALID" : "RECOVERY_BACKEND_ERROR", message: backendErrorMessage(body, response.status) },
        { status: response.status },
      );
    }
    return NextResponse.json(body);
  } catch {
    return NextResponse.json(
      { code: "RECOVERY_BACKEND_UNAVAILABLE", message: "Recovery planning cannot reach FastAPI. Check BACKEND_URL and start the current backend." },
      { status: 503 },
    );
  }
}

export async function GET(
  request: Request,
  { params }: { params: Promise<{ path: string[] }> },
) {
  return forward(request, (await params).path, "GET");
}

export async function POST(
  request: Request,
  { params }: { params: Promise<{ path: string[] }> },
) {
  return forward(request, (await params).path, "POST");
}
