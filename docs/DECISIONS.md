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
