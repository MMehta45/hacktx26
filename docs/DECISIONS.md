# Architecture decisions

## M0 — Repository foundation

### Separate frontend and backend in one repository

The repository uses `frontend/` for Next.js and `backend/` for FastAPI. This keeps each
ecosystem conventional while allowing one root command to run both during the hackathon.

### Use npm and uv lockfiles

npm is already bundled with Node and is familiar to the team. uv provides fast,
cross-platform Python environment and lockfile management. Dependencies are locked at
both JavaScript levels and in `backend/uv.lock`.

### Proxy browser health checks through Next.js

The browser calls the same-origin Next.js `/api/health` route, which forwards to FastAPI.
This avoids exposing backend configuration to browser bundles and avoids relying on CORS
for the main app path. FastAPI still permits the configured local frontend origin for
direct development requests.

### Keep integrations optional and backend-only

Nessie, SerpApi, and Gemini settings load only in FastAPI. Missing keys do not prevent
local startup; the health response reports that those integrations are unconfigured. No
paid infrastructure has been selected.

### Use webpack for Next.js development and builds

Next.js 16 defaults to Turbopack, but its PostCSS worker opens an internal port that is
not supported in the managed development environment used for this milestone. Webpack is
stable, needs no special infrastructure, and keeps Tailwind's standard PostCSS setup.

## M1 — Starter UI and synthetic customer data

### Use one versioned backend snapshot contract

FastAPI normalizes Nessie and fixture records into `CustomerSnapshot` schema version 1.
Money is represented in integer cents and dates are explicit ISO dates. Frontend scenario
inputs only change the display name, wage forecast, and repair quote overlay; they never
write banking transactions.

### Use an explicit, frozen demo date

`DEMO_ANCHOR_DATE` defaults to 2026-10-24. This makes the 90-day history, bill schedule,
and next four Fridays deterministic across rehearsals. The value can be changed locally
without rewriting fixtures.

### Keep future obligations in a synthetic schedule

Nessie bills expose payment and recurrence fields, but those fields do not guarantee the
explicit future due-date semantics required by the demo. The app reads usable future
Nessie bill dates when present and separately labels the deterministic local obligations
as `synthetic_schedule`. Historical purchases and future obligations are never summed as
the same event.

### Seed supported Nessie resources through a CLI only

The local CLI creates/reuses a customer, account, merchants, purchases, and deposits
using documented fields. A Git-ignored manifest holds returned IDs. Stable descriptions
make history insertion idempotent, and the reset command deletes the known account before
recreating it. No destructive seed endpoint is exposed over HTTP.

### Keep fixture and live provenance obvious

`auto` mode falls back to a deterministic fixture when the key, manifest, or sandbox is
unavailable and includes the reason in the API response. Strict `nessie` mode instead
returns an error. The UI always shows a live Nessie or local fixture badge.

### Reconcile fixture history without equating it to wage forecasts

The 13 weekly historical payroll deposits are $640 each and total $8,320. Seventy-two
purchases total $7,250 and four cash withdrawals total $1,070, so all historical debits
also total $8,320. This keeps the seeded $310 starting balance coherent whether the
sandbox treats account balance as independent or transaction-derived. These historical
deposits are fixed evidence and are not derived from the editable wage forecast.

## Live customer dashboard

### Keep one consolidated read contract and a CLI-only seed path

The existing versioned snapshot endpoint remains the frontend's single read model. It
contains account, normalized ledger, category summaries, bills, income forecasts, and
cash flow in one coherent response. Mutation remains in the explicit seed/reset CLI so
ordinary page loads and refreshes cannot duplicate sandbox resources.

### Use an 80% take-home estimate only for forward planning

Gross and estimated take-home values remain side by side. The 80% multiplier is a clear
planning assumption, not tax advice or a claim about a bank transaction. The cash-flow
baseline includes projected take-home pay and dated unpaid bills, but deliberately does
not deduct the uncommitted repair quote.

### Detect recurring spending deterministically

Transactions sharing a merchant are recurring when at least three dates have nearly
regular intervals, while housing, utilities, insurance, and subscription merchant groups
are treated as naturally recurring once repeated. Unknown merchants fall back to Other;
no AI categorization runs in this milestone.

## M2 — Crisis simulation and consequence graph

### Keep simulation pure and return its source snapshot

`simulate(snapshot, scenario, actions=[])` consumes typed data and returns typed results
without calling Nessie or mutating its input. The POST endpoint refreshes the read-only
snapshot once, then returns that exact snapshot beside its simulation so the UI never
mixes results from two banking reads. Nonempty recovery actions are rejected until their
later milestone defines dated effects.

### Separate raw funding need from payable cash

The normal and crisis lines are unconstrained arithmetic forecasts, so a negative crisis
line communicates required funding. An independent constrained ledger never overdrafts:
it applies paychecks and wage reductions first, then allocates cash to essential bills
before discretionary bills, using obligation ID for stable same-day ties. Partial funding
is reported explicitly and unpaid amounts remain outstanding rather than being deducted.

### Map absences through explicit pay-period coverage

Affected shifts are explicit weekdays. Each maps to the existing forecast entry whose
work-period start/end contains it; estimated lost take-home is capped at that paycheck's
modeled take-home and posted only on its payday. Historical deposits are evidence only and
are never rewritten.

### Treat the graph as a status view, not an execution engine

The backend owns all 14 stable problem nodes, 17 dependency edges, statuses, evidence,
dates, and amounts. React Flow only lays out, animates, and inspects that returned graph.
The repair quote is exposure; reserves deplete only with a dated payment. Transportation,
borrowing, debt payments, and late fees remain inactive or conditional at their $0
defaults.

### Use a frozen snapshot date for reproducible demo scheduling

The live account is retrieved at request time, but its forecast calendar remains anchored
to the configured customer date and `America/Chicago`. The response carries both the
source date and retrieval timestamp. Explicit scenario dates must match the loaded
snapshot, preventing a caller from silently combining bills and pay periods from a
different calendar.

## M3 — Agentic research

### Keep research read-only and tied to one M2 result

The research endpoint gets one snapshot, runs `simulate(..., actions=[])` once, and
returns both with a fingerprint. The fingerprint covers the scenario request, source
identity/balance/date, bills, wage losses, and fictional location context, while omitting
the volatile retrieval timestamp so identical fresh reads can reuse research for 15
minutes. No candidate changes a Nessie transaction or a projected balance.

### Use official Gemini SDK with backend-owned tool execution

`google-genai` is the only Gemini client. The configured default is
`gemini-3.5-flash-lite`, verified with this project's key; the formerly common
`gemini-2.5-flash` appeared in model listing but returned 404 on generation for this key.
Gemini selects one of three declared functions, while Python validates and executes
SerpApi requests, enforces up to six calls (eight on explicit refresh), and limits model
turns and elapsed time. Extracted JSON is checked against strict Pydantic contracts and
the actual evidence IDs. Search snippets are untrusted; provider failures remain visible.

### Treat listings as evidence of listings, not personal approvals

SerpApi uses its Google web, Maps places, and Maps directions engines. Every public
source URL is sanitized, linked, and time-stamped. A listing can support the existence
of a service or publicly stated terms; it does not verify this customer's eligibility,
employer permission, appointment, extension, or final price. Unknown required terms make
a candidate conditional. Only source-observed USD fares can be tagged observed; missing
fares remain unknown. Transit is verified only with fictional origin and destination,
both shift times, and dated outward and return route evidence for each affected shift.
No route inputs are invented for the default demo.

### Keep M4 action hints separate from execution

Candidate actions carry stable graph IDs, mechanism, requirements, cost/timing certainty,
evidence IDs, and potential-effect hints. Questions link to unknown candidate
requirements and are capped at two. These structures let M4 bind confirmed answers and
define dated action effects, but M3 never passes nonempty actions to the simulator or
calculates a recovered cash-flow path.

## M3.2 — Geographic grounding and research coverage

### Allocate the provider budget by pathway

The original M3 loop gave all targets to one Gemini conversation and stopped whenever
the model returned no next tool call. Gemini selected one rental-assistance query and
then ended, so the unused SerpApi budget never reached commute or repair research. M3.2
turns ranked targets into four explicit pathways: transportation, employer flexibility,
repair affordability, and bill assistance. Gemini still chooses the allowed tool and
query within each researchable pathway. Python reserves the six-call initial budget as
up to four dated transit legs, one mechanic search, and one bill-assistance search. A
failed or empty pathway does not stop the remaining pathways.

### Ground the fictional demo in editable Austin locations

The default research context uses `3810 N Lamar Blvd` as a geographic home proxy and
`525 N Lamar Blvd` as the fictional workplace, with an 08:00–16:00 weekday shift and
fictional Whole Foods employment. These values are explicit UI defaults, stay editable,
and are fingerprinted with research. They are never inferred from IP or Nessie data.

### Let the model choose transit, then canonicalize dated legs

When Gemini selects `find_transit` for a high-priority commute pathway, the backend
expands that intent into trusted scenario dates: an arrive-by request ten minutes before
shift start and a return request five minutes after shift end for each of the two
affected shifts, within the pathway budget. This prevents model-generated dates or
addresses from drifting from the scenario. Route feasibility still requires timely
outbound and return evidence for every affected date. Late, one-way, or incomplete
routes remain false or unknown and cannot claim protected shifts.

### Treat mechanic ratings and prices separately

Maps ratings and listings establish that a shop is listed; they do not establish a
low price. Repair candidates without explicit price/value evidence are rewritten as a
request for a written estimate, with unknown cost and conditional status. Review snippets
are retained when SerpApi supplies them, but the UI labels ratings as non-price evidence.

## M3.3 — Adaptive research and review-based mechanic evidence

### Make hypotheses model-proposed, scored, and extensible

The four M3.2 pathways were a coverage checklist rather than an adaptive investigation.
M3.3 asks Gemini for scored hypotheses before tool use, validates the
`Impact × Urgency × Actionability` product, and permits arbitrary stable hypothesis IDs.
A small baseline guarantees remote-work, transit, repair, and bill-risk consideration;
semantic deduplication prevents model restatements of those baselines from wasting calls.
Question-driven hypotheses use no public search, while evidence-driven hypotheses compete
for the bounded provider budget. All hypotheses and their outcomes remain visible.

### Guarantee remote-work consideration without assuming permission

Maya's fictional employer is Cedarstone Services and her fictional role is Hourly
Customer Support Specialist, normally onsite. Remote eligibility, equipment, shift
flexibility, and make-up hours are explicit unknowns. The backend guarantees a remote-work
hypothesis and high-priority question, but assigns no protected shifts and makes no claim
about employer approval or technical access.

### Use Maps Reviews only to prioritize estimate requests

A repair-place search may spend two follow-up calls on `google_maps_reviews` using the
listing's real `data_id`. Positive and negative price language and transparency language
are retained separately. The 0–1 contact heuristic weights price evidence 45%,
transparency 25%, listing reputation 20%, and convenience 10%; convenience remains a
neutral 0.5 when route evidence is unavailable. Missing review language contributes zero,
and every candidate still requires a written estimate for the unknown repair. DIY and
parts-only facilities are excluded from the repair-provider shortlist.

### Treat one late arrive-by result as conditional evidence

SerpApi's documented directions syntax is `time=arrive_by:<timestamp>`, which the client
already used with an America/Chicago-aware Unix timestamp. A provider result arriving
after 08:00 proves only that the returned itinerary misses the checked shift. It now yields
"potentially feasible with adjustment" rather than universal infeasibility; an earlier
departure, alternative itinerary, return leg, or manager-approved schedule change still
requires evidence.

## M3.4 — Reliable extraction and complete candidate preservation

### Constrain Gemini output and retain stop diagnostics

The prior extractor requested only the JSON MIME type, duplicated a large hand-written
shape in the prompt, capped output at 4,000 tokens, discarded `finish_reason`, and called
`json.loads` once. The observed warning therefore identifies a JSON syntax failure—not a
Pydantic rejection—but the discarded response metadata makes the historical run's exact
stop cause unrecoverable. M3.4 uses Gemini's JSON Schema structured-output setting with
the `ResearchExtraction` Pydantic schema, removes the duplicate prompt schema, raises the
bounded output allowance to 7,000 tokens, and validates with `model_validate_json`.

One retry receives only a sanitized validation summary. Each failed attempt records a
safe error code, field location/message, finish reason, and output-token count where the
provider supplies them. Raw model text and credentials are never returned by the API.

### Preserve conservative candidates before model extraction

Provider evidence is now converted to conservative typed candidates before final Gemini
extraction. Ask-user hypotheses retain unknown requirements; transit retains deterministic
route status; each repair listing/review remains a separate estimate request; and web
resources retain conditional verification requirements. Gemini can add richer distinct
candidates, but malformed output cannot delete the deterministic set.

Candidates carry stable `hypothesis_ids`. Every hypothesis returns one structured outcome:
viable candidate, conditional candidate, blocked, rejected with a reason, or insufficient
evidence. Exact semantic duplicates are merged by mechanism/title while their evidence
and hypothesis links are unioned. Repeated extraction failure keeps a completed research
status when evidence-grounded candidates survived, with warnings and diagnostics attached.

## M3.5 — Derived crisis timeline

### Make employment attendance a derived state

The crisis request now contains a breakdown date/time and repair quote, not missed-shift
or repair-outcome fields. The simulator generates Monday–Friday 08:00–16:00 shifts,
maps each to the following-Friday payday for its Monday–Sunday workweek, and determines
attendance from vehicle availability at shift start. This keeps historical Nessie
deposits immutable and separates observed banking history from fictional employment
assumptions and future projections.

### Use deterministic intraday ordering

Each simulated date processes the 08:00 shift, then a Friday payroll arrival, scheduled
bills, and finally repair affordability. A same-day repair restores the vehicle after
the morning attendance decision, so a Friday paycheck cannot retroactively recover that
Friday's missed shift. This single forward pass resolves the unpaid-repair/lost-work/
lower-payroll feedback loop without recursion.

### Protect near-term essential bills before funding repair

The untreated policy pays the full repair quote once only when constrained cash also
covers essential obligations due through the next payday supported by already earned or
hypothetically attendable work after repair. If no such payday exists, remaining
essential obligations in the forecast stay protected. The policy is intentionally
conservative and is not claimed to be optimal; Build 04 may compare alternative actions.

### Retain the seeded history without reseeding

The fixture and Nessie seed already create thirteen $640 deposits on Fridays, so no
historical migration is required. Build 03.5 corrects only the forward forecast mapping:
the October 30 payroll now covers October 19–25 rather than a Thursday–Wednesday period.
The existing explicit reset command remains available, but normal API reads never seed
or mutate Nessie.

## M4 — Interactive recovery optimization

### Keep research, feasibility, and simulation as separate contracts

Research candidates remain leads until the backend can compile them into typed, dated
effects. Requirements separately record possible, pending approval, user-reported,
externally verified, rejected, and expired states. The simulator receives effects—not
research prose—and therefore remains deterministic and usable without Gemini. Conditional
plans run under explicit assumptions while retaining their unresolved requirement IDs.

### Reuse the derived simulator for every plan

The optimizer never patches the untreated ending balance. It enumerates combinations of
one to three among at most eight quantified actions, applies their typed effects, and
reruns the shift/payroll/repair/bill engine. Stable shift and ledger IDs prevent duplicate
wage recovery and cash flows. The same bill-protective repair rule applies to every plan.

### Rank finances lexicographically, then diversify presentation

Plans sort by feasibility, essential unpaid dollars and count, peak funding gap, recovered
shifts, incremental cost, unresolved dependencies, and complexity. A second pass selects
up to three different strategy signatures so a near-duplicate top three does not hide a
meaningfully different option. The response retains ranking rationale and untreated
comparison deltas.

### Treat outreach and provider evidence as preparation, not execution

A yes to possible remote work creates a copyable draft and a pending manager-approval
requirement. It does not preserve a shift as a confirmed fact. Transit becomes executable
only with dated outbound and return timing plus observed fares; personal usability remains
a reusable condition. A mechanic is shown as affordable only when actual review excerpts
contain positive pricing language, and even then the financial quote stays unknown until
the user supplies a written amount and appointment date.

### Bound targeted research independently

Recovery sessions may spend a small per-round SerpApi budget within a larger session cap.
Identical targeted queries are cached, provider failures preserve existing evidence and
answers, and unquantified research leads never enter plan arithmetic. Session storage is
in-memory for the prototype; the browser retains only an opaque session ID.

## M4.1 — Recovery and provider-data corrections

### Advertise backend capabilities and classify recovery failures

The recovery 404 came from stale running processes, not the checked-in FastAPI router.
Health now advertises API version 0.4.1 and recovery capabilities. The Next.js proxy maps a
missing saved session to `RECOVERY_SESSION_NOT_FOUND`, a missing recovery router to
`RECOVERY_ROUTE_MISSING`, payload validation to `RECOVERY_PAYLOAD_INVALID`, and connection
failure to `RECOVERY_BACKEND_UNAVAILABLE`. The browser recreates only a genuinely stale
session; it no longer hides backend or route failures by clearing state indiscriminately.

### Distrust a provider itinerary that ignores its requested time

SerpApi accepted and echoed the documented `arrive_by:<unix timestamp>` parameter during a
live check but returned current-time routes at 12:20 and 21:34 for an 08:00–16:00 shift.
Each itinerary now records whether the returned time is plausibly tied to the requested
constraint, and whether provider-resolved endpoints match the requested commute. Only
matched, time-honoring, same-date outbound/return evidence with known fares can compile to
a shift-preserving financial action.

### Treat documented duration numbers as seconds

SerpApi documents `directions[].duration` and `trips[].duration` as seconds. Numeric values
are now converted with ceiling-to-minutes; strings remain parsed as formatted durations.
Transit stop times come from nested `start_stop.time` and `end_stop.time`. Missing overall
duration falls back to the valid start/end interval.

### Require linked positive pricing evidence everywhere

Generic mechanic listings remain raw evidence but no longer become affordability candidates.
Both deterministic and Gemini candidates must cite a place plus a review linked to that
same place containing non-negated positive price language. Negative-only, missing-review,
or rating-only shops are suppressed in research, recovery conversion, and frontend display.
Qualified shops request an alternative quote against Maya's existing $400 quote; reviews
never create a lower repair amount.

## M4.2 — Research handoff and financial opportunities

### Bind a recovery session to the exact Explore scenario and context

Explore and Recovery now share a stable fingerprint over the read-only simulation,
scenario inputs, scheduled obligations, income-loss timeline, and geographic/work context.
Recovery rejects a supplied research result when that fingerprint differs instead of mixing
evidence from another scenario. Browser session reuse additionally compares the stored
research run ID, so a baseline session cannot replace a later Explore-backed session.

### Keep historical-spending analysis explanatory until an explicit dated effect exists

The recovery response exposes scheduled obligations, conservative inferred monthly charges,
and variable-spending categories with source transaction IDs and confidence. Scheduled bills
remain the only baseline forecast expenses. A matching historical recurring charge is marked
as already scheduled rather than projected a second time; discretionary history is a
conditional opportunity, never cash that has already been saved.

### Separate a rent request from landlord agreement

Willingness to request an extension creates only an unsent draft and pending status. A
separate landlord-agreement answer unlocks a proposed date; only the dated agreement creates
the bill-date effect, and that effect moves—not waives—the full obligation.

## M4.3 — Actionable plan evidence and reconciliation

Recovery plans now expose structured resources, timelines, and reconciliation alongside the
simulator result. Evidence-linked resources are filtered to selected actions; private
approvals use unsent outreach drafts rather than invented public URLs. Direct preserved
shifts are separated from later shifts restored by earlier repair, while payday deltas come
from rerun payroll records. Scheduled bill outcomes remain the source of truth for unpaid
essentials, so a later ending-balance improvement cannot imply an earlier bill was funded.
