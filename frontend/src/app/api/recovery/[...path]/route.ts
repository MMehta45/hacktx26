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
    const body = (await response.json()) as unknown;
    if (!response.ok) {
      return NextResponse.json(
        { message: backendErrorMessage(body, response.status) },
        { status: response.status },
      );
    }
    return NextResponse.json(body);
  } catch {
    return NextResponse.json(
      { message: "Recovery planning is unavailable. Start FastAPI and retry." },
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
