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
