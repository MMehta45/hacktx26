# Build 04 — Interactive Recovery Optimizer

Build 04 closes the loop from researched possibilities to explicit conditional or
confirmed recovery plans. It does not execute external actions or mutate Nessie.

## Architecture

1. `POST /api/recovery/sessions` reads the current snapshot once, reruns the untreated
   derived simulator, and creates a versioned in-memory session.
2. Answers update typed requirements. Possibility, pending external approval,
   user-reported confirmation, and provider verification remain distinct.
3. Research candidates compile to effects only when amount, date, entity, provenance, and
   required conditions are sufficient. Unknown-cost leads stay unquantified.
4. The optimizer enumerates combinations of one to three actions (at most 92 for eight
   actions), deduplicates shift/ledger effects, and reruns the authoritative simulator.
5. Plans are ranked lexicographically and up to three strategy-diverse results are returned.

## API

- `POST /api/recovery/sessions` — create a session from scenario, optional Build 03 result,
  and route context.
- `GET /api/recovery/sessions/{id}` — reload a session after browser refresh.
- `POST /api/recovery/sessions/{id}/answers` — submit or revise a typed answer with the
  current `session_version`.
- `POST /api/recovery/sessions/{id}/requirements` — explicitly confirm or reject a
  requirement and recompute plans.
- `POST /api/recovery/sessions/{id}/research` — run bounded candidate-specific SerpApi
  research without erasing answers or unrelated evidence.
- `POST /api/recovery/sessions/{id}/evaluate` — rerun bounded combination evaluation.

Stale writes return HTTP 409. Unknown sessions return 404. Validation and unsupported
transitions return 422. The schema version is `1`.

## Supported effects

Effects use integer cents, explicit dates, stable action/effect/ledger IDs, requirements,
evidence references, and certainty. The simulator supports preserving exact shifts,
dated expenses, bill due-date changes and reductions, restricted or unrestricted
assistance, replacement repair quotes, borrowing with repayments, and makeup hours paid
on an explicit payroll date.

Duplicate shift coverage is unioned. Duplicate ledger IDs are rejected. A due-date change
retains the full obligation, a replacement quote replaces rather than adds a repair, and
borrowing is inseparable from its repayment schedule.

## Conditional behavior

The optimizer calculates a conditional action's financial result so the user can see its
value, but the plan remains labeled `conditional_pending_approval` or
`conditional_pending_information`. A remote-work possibility prepares a draft only.
Manager confirmation and equipment are separately tracked. The draft is never sent.

## Evidence policy

A transit action requires same-date outbound arrival before shift start, a return departure
after shift end, and fares on both legs. The API preserves route lines, stops, transfers,
walk details, timings, leg details, fare source/certainty, and source URL when returned.
Missing values remain unknown.

Mechanic listings and ratings are not affordability evidence. A price-based recommendation
requires at least one actual positive price-related review excerpt. Negative and negated
language is retained separately. No review changes the $400 quote; only a user-reported
written quote and appointment can create a replacement-quote effect.

## Persistence and limits

Sessions and targeted-query cache are process memory, suitable for the hackathon. Browser
refresh restores the opaque session ID from local storage. A backend restart requires a
new session. Base-scenario or research-run changes use a different browser key.

`RECOVERY_RESEARCH_MAX_CALLS` limits each targeted round (default 5) and
`RECOVERY_SESSION_MAX_CALLS` limits the full session (default 12). Routine tests use mocked
providers and make no paid calls.
