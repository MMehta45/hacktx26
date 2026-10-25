# One Bad Tuesday

One Bad Tuesday is a HackTX 2026 financial-resilience prototype. It provides an
interactive four-stage shell, a normalized synthetic customer snapshot, a Capital One
Nessie seed/read path, spending analysis, upcoming obligations and income, and a
deterministic 30-day crisis simulator with an inspectable consequence graph. The Explore
stage performs bounded Gemini and SerpApi research and shows source-linked potential
interventions. The Plan stage turns confirmed or explicitly conditional actions into
dated financial effects and ranks up to three recalculated recovery strategies.

## Prerequisites

- Node.js 20.9 or newer and npm
- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/getting-started/installation/) for Python dependencies
- Git

## Install

macOS:

```bash
git clone https://github.com/MMehta45/hacktx26.git one-bad-tuesday
cd one-bad-tuesday
npm install
npm --prefix frontend install
uv sync --directory backend
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

Windows PowerShell:

```powershell
git clone https://github.com/MMehta45/hacktx26.git one-bad-tuesday
Set-Location one-bad-tuesday
npm install
npm --prefix frontend install
uv sync --directory backend
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env.local
```

The app runs without credentials in a visibly labeled fixture mode. Real `.env` files
are ignored by Git.

## Configure Nessie and seed the fictional customer

1. Sign in through the official [Nessie Getting Started](https://nessieisreal.com/getting-started)
   flow and retrieve the sandbox key from your profile.
2. Put it directly in the ignored `backend/.env` file:

   ```ini
   NESSIE_API_KEY=your-local-key
   DEMO_DATA_MODE=auto
   ```

3. Seed and immediately read back the deterministic Maya Rodriguez profile:

   ```bash
   npm run seed:customer
   ```

The seed command creates or reuses one customer, a checking account, supported merchant
records, 72 purchases, 13 weekly $640 payroll deposits, four cash withdrawals, and five
pending bills. Purchases and withdrawals total the same $8,320 as deposits so the target
$310 account balance remains mathematically consistent if Nessie applies transaction
effects. The command reads all resources and the final balance back before succeeding.
It stores only returned resource IDs in `backend/.local/nessie-seed.json`, which is
ignored. Stable descriptions and bill nicknames make reruns skip existing history.

To explicitly recreate the seeded account and its history while retaining the customer:

```bash
npm run seed:customer:reset
```

This reset deletes the account identified by the local manifest before creating its
replacement. It stops if deletion fails, rather than silently adding another account.

The dashboard uses readable future Nessie bills when available and fills any missing
named obligation from a separately labeled `synthetic_schedule`. Bills are never treated
as completed purchase transactions. User-entered wages generate gross and 80%-estimated
take-home forecasts only; changing the wage never creates or rewrites a Nessie deposit.

## Run

Start both services from the repository root:

```bash
npm run dev
```

- Frontend: <http://localhost:3000>
- Backend health: <http://127.0.0.1:8000/health>
- Snapshot API: <http://127.0.0.1:8000/api/customer/snapshot>
- Crisis simulator: `POST http://127.0.0.1:8000/api/simulations/crisis`
- Research: `POST http://127.0.0.1:8000/api/research/interventions`
- Recovery sessions: `POST http://127.0.0.1:8000/api/recovery/sessions`
- FastAPI docs: <http://127.0.0.1:8000/docs>

The browser calls same-origin Next.js routes, which forward to FastAPI. Backend secrets
never enter browser code.

## Demo the untreated crisis

1. Open the frontend and confirm the starter card says **Live Nessie sandbox** (or read
   the explicit fixture warning).
2. Keep the default $20 hourly wage, $400 repair quote, and October 26 breakdown.
3. Select **Simulate crisis**.
4. Watch the problem-only graph reveal the missed-work chain, select nodes to inspect
   evidence, and compare normal versus crisis balance lines.
5. Review the event ledger and constrained **Projected bills at risk** section. Open the
   banking context to retain access to accounts, categories, bills, and all 90-day
   transactions.
6. Change the repair quote or breakdown date and choose **Rerun simulation**. The engine
   derives attendance, payroll reductions, and the bill-protective repair date; it never
   changes the live balance or historical ledger.

## Demo Explore research (Build 03)

1. Add `GEMINI_API_KEY` from [Google AI Studio](https://aistudio.google.com/apikey) and
   `SERPAPI_API_KEY` from your [SerpApi dashboard](https://serpapi.com/manage-api-key)
   directly to ignored `backend/.env`. Keep `GEMINI_MODEL=gemini-3.5-flash-lite` unless
   your key supports a different current model. Restart FastAPI after editing `.env`.
2. Simulate the crisis and open **Explore**. Choose **Start research**. This sends one
   read-only Nessie snapshot and untreated simulation through Gemini tool selection;
   SerpApi search results become linked evidence. The activity list appears after the
   backend confirms each step. Re-entering Explore keeps the result; **Check this
   scenario** reuses backend cache while **Refresh sources** spends a new bounded pass.
3. The Explore fields start with an editable fictional Austin route: `3810 N Lamar Blvd`
   to `525 N Lamar Blvd`, 08:00–16:00. The first address is a geographic proxy and the
   Cedarstone Services employer and office are fictional. Maya's fictional role is an
   hourly Customer Support Specialist who normally works onsite; remote eligibility,
   equipment, schedule flexibility, and make-up hours are unknown. The app never derives
   route values from IP.
4. Gemini proposes and scores multiple hypotheses, then allocates the bounded search
   budget. Transit uses documented arrival-by semantics and requires outbound and return
   evidence. A single late itinerary is conditional evidence, not proof that all transit
   is unavailable.
5. Repair research can follow Maps listings with real Google Maps Reviews calls. The
   shortlist only recommends a shop on affordability grounds when an actual returned review
   contains positive pricing language. Reviews never establish the cheapest shop or replace
   a written estimate.

## Demo interactive recovery (Build 04)

1. Complete the crisis simulation and optionally run Explore research. Select **Build
   recovery plans**. A versioned recovery session is retained across browser refreshes;
   restarting FastAPI clears server-side sessions.
2. Answer one or two high-impact questions. Saying remote work is possible creates a
   ready-to-copy employer request but keeps manager approval pending. Confirm approval
   only if it actually occurred.
3. Compare up to three plans. Each card shows conditional dependencies, untreated versus
   recalculated bill/gap/balance outcomes, missed shifts, repair timing, dated cash
   checkpoints, cascade-node changes, sources, and next steps.
4. Confirm or reject an unresolved requirement to rerank plans. Enter a confirmed rent
   date or written repair quote when prompted; those values become typed simulator effects.
5. Use **Research this dependency** for a bounded targeted SerpApi pass. Timed transit
   actions require both shift-compatible directions and observed fares. Existing answers
   and plans remain if research fails.

All plans are hypothetical copies. The app never sends a draft, obtains approval, books a
repair, borrows money, changes a Nessie transaction, or treats a conditional outcome as
guaranteed. `RECOVERY_RESEARCH_MAX_CALLS` limits one targeted round and
`RECOVERY_SESSION_MAX_CALLS` caps a session.

The default pass permits at most six SerpApi HTTP requests, including retries; explicit
refresh permits eight. Results are cached in backend memory for 15 minutes per relevant
snapshot/scenario/location. Restarting FastAPI clears this cache. Search quota or model
errors yield partial or failed results rather than fabricated options. The model and
request/time limits can be changed with `GEMINI_MODEL` and the `RESEARCH_*` backend
variables in `.env.example`.

The default simulator uses the financial snapshot date in `America/Chicago`, weekday
08:00–16:00 shifts, and an explicitly labeled 80% take-home estimate. A Monday–Sunday
work period is paid the following Friday, so the October 30 paycheck covers October
19–25 and cannot be reduced by an October 26 breakdown. Each day processes the morning
shift, then payroll, bills, and finally a possible repair payment. The full quote is paid
once only when cash can also protect essential bills through the next reliable payday.
Raw negative balances are funding requirements; the constrained ledger reports what can
actually be funded on each due date.

To run services separately:

```bash
npm run dev:backend
npm run dev:frontend
```

If ports 3000/8000 are occupied, use alternatives. On macOS/Linux:

```bash
uv run --directory backend uvicorn app.main:app --reload --port 8001
BACKEND_URL=http://127.0.0.1:8001 npm --prefix frontend run dev -- --port 3001
```

On Windows PowerShell:

```powershell
uv run --directory backend uvicorn app.main:app --reload --port 8001
$env:BACKEND_URL = "http://127.0.0.1:8001"
npm --prefix frontend run dev -- --port 3001
```

## Data modes and environment variables

All credentials belong in `backend/.env`. Never put them in `frontend/.env.local`, a
`NEXT_PUBLIC_*` variable, source code, documentation, or logs.

| Variable | Purpose |
| --- | --- |
| `NESSIE_API_KEY` | Optional Nessie sandbox key used only by FastAPI and the seeder |
| `SERPAPI_API_KEY` | Backend-only web, places, and transit search key for Explore |
| `GEMINI_API_KEY` | Backend-only Gemini tool selection and candidate extraction key |
| `GEMINI_MODEL` | Configured Gemini model, default `gemini-3.5-flash-lite` |
| `RESEARCH_*`, `RECOVERY_*` | Backend discovery and targeted recovery-research limits; see `.env.example` |
| `NESSIE_BASE_URL` | Nessie API origin; defaults to `https://prod-api.nessieisreal.com` |
| `DEMO_DATA_MODE` | `auto`, `fixture`, or strict `nessie` mode |
| `DEMO_ANCHOR_DATE` | Frozen ISO date used for repeatable 90-day history and schedules |
| `SEED_MANIFEST_PATH` | Ignored local manifest path, relative to `backend/` |
| `FRONTEND_ORIGIN` | Origin allowed by FastAPI CORS |
| `BACKEND_URL` | Server-only Next.js proxy target in `frontend/.env.local` |

Mode behavior:

- `auto` uses seeded Nessie data when the key and valid manifest are available; otherwise
  it returns the labeled deterministic fixture with an explanation.
- `fixture` never calls Nessie.
- `nessie` returns a clear error instead of falling back when credentials, seed state, or
  the sandbox are unavailable.

## Tests and checks

Run the complete suite:

```bash
npm test
```

This runs backend contract, normalization, simulator/effect arithmetic, plan ranking,
sessions, due-date allocation, graph, idempotency, and offline research tests; frontend
wage, crisis, Explore, and conditional-plan render tests; TypeScript; ESLint;
and a production Next.js build. Backend lint is separate:

```bash
npm run lint:backend
```

Dependency versions are locked in `package-lock.json`, `frontend/package-lock.json`, and
`backend/uv.lock`.

## Troubleshooting

- **Fixture badge appears:** read its message. Add the key and run `npm run seed:customer`
  for Nessie mode; the app never labels fixture data as live.
- **Nessie credential/permission error:** retrieve the key again from your Nessie profile,
  update `backend/.env`, restart FastAPI, and rerun the seed command.
- **Seed manifest points to deleted records:** rerun `npm run seed:customer`; missing
  customer/account IDs are validated before reuse.
- **Port already in use:** use the alternate-port commands above.
- **Frontend cannot reach FastAPI:** confirm `BACKEND_URL`, restart Next.js, and check the
  backend `/health` endpoint.
- **Recovery says the route is missing:** inspect `/health` for `api_version: 0.4.1` and
  `capabilities.recovery_sessions: true`. A different or stale process may own the configured
  port. Stop only that old project process, restart FastAPI from this checkout, and make
  `BACKEND_URL` point to it. A stale saved session is cleared automatically and recreated.
- **`uv` is missing:** install it from the linked official instructions, then rerun
  `uv sync --directory backend`.

See [docs/DECISIONS.md](docs/DECISIONS.md) for architectural rationale and
[docs/progress/M4.1.md](docs/progress/M4.1.md) for the latest recovery/transit reliability verification. Real
provider calls are opt-in through Explore; ordinary automated tests use fake adapters
and do not spend API quota.
