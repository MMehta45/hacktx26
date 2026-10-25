import { NextResponse } from "next/server";

import { backendErrorMessage } from "@/lib/api-error";

const backendUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export async function POST(request: Request) {
  try {
    const payload = (await request.json()) as unknown;
    const response = await fetch(`${backendUrl}/api/simulations/crisis`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
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
      { message: "The crisis simulator is unavailable. Start FastAPI and retry." },
      { status: 503 },
    );
  }
}
