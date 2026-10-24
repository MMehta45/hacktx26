import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export async function GET() {
  try {
    const response = await fetch(`${backendUrl}/health`, { cache: "no-store" });

    if (!response.ok) {
      return NextResponse.json(
        { status: "error", message: `Backend returned ${response.status}` },
        { status: 503 },
      );
    }

    return NextResponse.json(await response.json());
  } catch {
    return NextResponse.json(
      {
        status: "error",
        message: "Backend is unavailable. Start it on port 8000 and retry.",
      },
      { status: 503 },
    );
  }
}
