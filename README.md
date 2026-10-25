# One Bad Tuesday

One Bad Tuesday is a HackTX 2026 financial-resilience prototype. It provides an
interactive four-stage shell, a normalized synthetic customer snapshot, a Capital One
Nessie seed/read path, spending analysis, upcoming obligations and income, and a
deterministic 30-day crisis simulator with an inspectable consequence graph. Live
research, questions, and recovery plans remain clearly disabled previews.

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
- FastAPI docs: <http://127.0.0.1:8000/docs>

The browser calls same-origin Next.js routes, which forward to FastAPI. Backend secrets
never enter browser code.

## Demo the untreated crisis

1. Open the frontend and confirm the starter card says **Live Nessie sandbox** (or read
   the explicit fixture warning).
2. Keep the default $20 hourly wage, $400 unpaid repair quote, and two missed shifts.
3. Select **Simulate crisis**.
4. Watch the problem-only graph reveal the missed-work chain, select nodes to inspect
   evidence, and compare normal versus crisis balance lines.
5. Review the event ledger and constrained **Projected bills at risk** section. Open the
   banking context to retain access to accounts, categories, bills, and all 90-day
   transactions.
6. Change the repair quote or missed shifts and choose **Rerun simulation**. A quote alone
   never changes the live balance or historical ledger.

The default simulator uses the financial snapshot date in `America/Chicago`, five
eight-hour weekday shifts, weekly paychecks, and an explicitly labeled 80% take-home
estimate. Pay loss is applied to the paycheck covering each missed shift. Paychecks are
processed first on a date; essential bills follow before discretionary bills, with ID as
the stable same-day tie-breaker. Raw negative balances are funding requirements. A
separate constrained ledger partially funds obligations only with cash available on the
due date and reports the remainder as projected unpaid.

To run services separately:

```bash
npm run dev:backend
npm run dev:frontend
```

If ports 3000/8000 are occupied, use alternatives. On macOS/Linux:

```bash
npm run dev:backend -- --port 8010
BACKEND_URL=http://127.0.0.1:8010 npm --prefix frontend run dev -- --port 3010
```

On Windows PowerShell:

```powershell
npm run dev:backend -- --port 8010
$env:BACKEND_URL = "http://127.0.0.1:8010"
npm --prefix frontend run dev -- --port 3010
```

## Data modes and environment variables

All credentials belong in `backend/.env`. Never put them in `frontend/.env.local`, a
`NEXT_PUBLIC_*` variable, source code, documentation, or logs.

| Variable | Purpose |
| --- | --- |
| `NESSIE_API_KEY` | Optional Nessie sandbox key used only by FastAPI and the seeder |
| `SERPAPI_API_KEY` | Reserved for a later build sheet; not invoked in M1 |
| `GEMINI_API_KEY` | Reserved for a later build sheet; not invoked in M1 |
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

This runs backend contract, normalization, simulator arithmetic, due-date allocation,
graph, and idempotency tests; frontend wage and crisis-render tests; TypeScript; ESLint;
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
- **`uv` is missing:** install it from the linked official instructions, then rerun
  `uv sync --directory backend`.

See [docs/DECISIONS.md](docs/DECISIONS.md) for architectural rationale and
[docs/progress/M2.md](docs/progress/M2.md) for actual milestone verification.
