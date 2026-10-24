import { type NextRequest, NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.toString();
  try {
    const response = await fetch(`${backendUrl}/api/customer/snapshot?${query}`, {
      cache: "no-store",
    });
    const body = (await response.json()) as unknown;

    if (!response.ok) {
      const detail =
        typeof body === "object" && body !== null && "detail" in body
          ? String(body.detail)
          : `Backend returned ${response.status}`;
      return NextResponse.json({ message: detail }, { status: response.status });
    }

    return NextResponse.json(body);
  } catch {
    return NextResponse.json(
      {
        message: "The customer API is unavailable. Start the FastAPI backend and retry.",
      },
      { status: 503 },
    );
  }
}
