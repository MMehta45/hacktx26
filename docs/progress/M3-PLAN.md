# M3 implementation plan

1. Define strict research request/result contracts and deterministic backward target selection from M2 graph statuses. Test cycle handling, priority scoring, validation, and zero-unpaid-bill cases.
2. Add a backend-only SerpApi adapter for web, places, and transit directions. Normalize and sanitize evidence; bound requests, retries, timeouts, and cache lifetime. Test with fake HTTP responses, then opt in to a small live probe.
3. Add official `google-genai` tool-calling orchestration. Give Gemini a compact M2 summary and three constrained tools; validate its final candidates and questions against evidence, graph IDs, dates, and unknown requirements. Test chained calls and failure cases with fake adapters.
4. Add `POST /api/research/interventions` and a matching Next.js proxy. Return the authoritative snapshot/simulation with a fingerprint so the Explore view can replace stale M2 state. Replace Stage 3 preview with a real request, recorded activity, source links, candidate/unknown cards, retry, and pending questions. Keep Stage 4 as a preview.
5. Run backend and frontend suites, import/build checks, local API/UI checks, and an opt-in live Gemini/SerpApi smoke test if configured. Record exact counts, source limitations, decisions, and operating steps in M3 and README.

Dependencies: `google-genai` in the Python backend. Credentials remain in ignored `backend/.env`; no new frontend secrets or persistent infrastructure. Research is read-only and never passes actions into the M2 simulator.
