# Breakingpoint

> One bad day shouldn’t become a bad month.

Breakingpoint is a HackTX 2026 financial-recovery prototype. It combines a seeded Capital
One Nessie sandbox customer, deterministic 30-day financial simulation, bounded Gemini and
SerpApi research, and ranked recovery plans.

The user experience has four parts:

1. **Your situation** — review Maya’s starting finances and edit the wage, repair quote,
   and breakdown date.
2. **The ripple effect** — inspect the projected cash impact and animated causal graph.
3. **Preparing your recovery** — confirm commute details, run research, and answer
   high-impact questions one at a time.
4. **Your recovery plan** — compare ranked strategies, financial effects, Route 5 details,
   useful resources, and copyable outreach drafts.

The simulator never edits historical Nessie transactions. Plans are projections; the app
does not send messages, book services, borrow money, make payments, or silently confirm an
employer or landlord decision.

## Stack

- Next.js 16, React 19, and TypeScript
- FastAPI, Python, and Pydantic
- Capital One Nessie sandbox for the seeded banking snapshot
- Gemini for bounded hypothesis and candidate extraction
- SerpApi for public research evidence
- React Flow for the consequence graph

## Prerequisites

- Node.js 20.9 or newer
- npm
- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Git

## Install

```bash
git clone https://github.com/MMehta45/hacktx26.git
cd hacktx26
npm install
npm --prefix frontend install
uv sync --directory backend
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

PowerShell equivalents for the final two copy commands:

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env.local
```

Local `.env` files and the Nessie seed manifest are ignored by Git. Never place backend
credentials in a `NEXT_PUBLIC_*` variable.

## Configure integrations

Add credentials only to `backend/.env`:

```ini
NESSIE_API_KEY=your_nessie_sandbox_key
SERPAPI_API_KEY=your_serpapi_key
GEMINI_API_KEY=your_gemini_key
DEMO_DATA_MODE=auto
```

Where to obtain them:

- Nessie: [nessieisreal.com/getting-started](https://nessieisreal.com/getting-started)
- Gemini: [Google AI Studio](https://aistudio.google.com/apikey)
- SerpApi: [SerpApi dashboard](https://serpapi.com/manage-api-key)

The app still runs without credentials. `DEMO_DATA_MODE=auto` uses Nessie when a valid
key and seed manifest exist, then falls back to a clearly labeled local fixture. Use
`fixture` to avoid Nessie entirely or `nessie` to fail instead of falling back.

Gemini and SerpApi are invoked only during recovery research. They are not exposed to the
browser.

## Seed the fictional Nessie customer

```bash
npm run seed:customer
```

The idempotent seeder creates or reuses Maya Rodriguez, her checking account, 90 days of
fictional transactions, historical payroll deposits, and supported upcoming bills. Returned
resource IDs are stored in the ignored `backend/.local/nessie-seed.json` manifest. The seed
command reads the created records back before reporting success.

To recreate only the seeded account and its history while retaining the customer:

```bash
npm run seed:customer:reset
```

This deletes the account referenced by the local manifest. Do not use the reset command if
you want to preserve that seeded account.

## Run locally

Start both services from the repository root:

```bash
npm run dev
```

- App: <http://localhost:3000>
- FastAPI health: <http://127.0.0.1:8000/health>
- FastAPI docs: <http://127.0.0.1:8000/docs>

The browser uses relative `/api/...` URLs. Next.js handles those routes server-side and
forwards them to `BACKEND_URL`, so FastAPI and its credentials are not exposed directly.

To run each process separately:

```bash
npm run dev:backend
npm run dev:frontend
```

If the default ports are occupied:

```bash
uv run --directory backend uvicorn app.main:app --reload --port 8001
BACKEND_URL=http://127.0.0.1:8001 npm --prefix frontend run dev -- --port 3001
```

Then open <http://localhost:3001>. If `BACKEND_URL` is stored in
`frontend/.env.local`, restart Next.js after changing it.

## Demo flow

### 1. Your situation

- Confirm the badge says **Live Nessie sandbox** or displays the explicit fixture state.
- The breakdown date initially uses today in `America/Chicago` and remains editable within
  the loaded forecast window.
- Keep the default `$20/hour` wage and `$400` repair quote for the standard Maya scenario.
- Select **See the ripple effect**.

The wage forecast uses five eight-hour shifts and an explicit 80% take-home estimate. It
does not create a Nessie deposit.

### 2. The ripple effect

- Review the current balance, projected lost income, funding gap, and bills at risk.
- Scroll to the graph. Its root appears first, then edges trace to dependent nodes in causal
  order. Replay, pause, skip, zoom, fit, keyboard focus, and reduced-motion behavior remain
  available.
- Open the optional forecast, payroll, event, or banking details when needed.
- Use **Edit situation** to change wage, quote, or date and rerun from Stage 1.

The quoted repair costs nothing until the bill-protective policy can actually fund it.
Negative raw balances indicate required funding, not an observed Nessie overdraft.

### 3. Preparing your recovery

- Confirm the prefilled Austin home/work addresses and 08:00–16:00 shift.
- Select **Find my way forward**.
- The loading transition remains visible until both research and recovery-session creation
  finish, then the first prioritized question appears.
- Answer **Yes**, **No**, or **Not sure yet**. Unknown and pending approval remain distinct.
  You may continue to plans without resolving every external dependency.

The UI does not expose raw provider logs or research-result dumps. The complete structured
research response still passes into the recovery session.

### 4. Your recovery plan

- Select one compact strategy at a time.
- Review shifts saved, additional earnings, cost, repair timing, bills at risk, and next
  actions.
- Route 5 is automatically available for Maya’s configured commute. Its plan shows the
  7:35 AM departure, 7:52 AM arrival, 4:17 PM return departure, `$1.25` one-way fare, and
  `$2.50` round trip. Fares are charged only on dates the plan actually uses transit.
- Remote-work and rent-extension outcomes stay conditional until the required approval is
  reported. A willingness to ask creates a copyable draft, not an assumed approval.
- Full reconciliation and dated cash details remain under optional disclosures.

The optimizer evaluates compatible combinations of up to three actions. Overlapping remote
work and transit cannot preserve the same shift twice, and transit is not charged on a day
covered by remote work.

## Environment variables

### Backend-only: `backend/.env`

| Variable | Purpose |
| --- | --- |
| `NESSIE_API_KEY` | Nessie sandbox access for FastAPI and the seeder |
| `SERPAPI_API_KEY` | Public research provider access |
| `GEMINI_API_KEY` | Gemini research orchestration and extraction |
| `GEMINI_MODEL` | Gemini model; see `backend/.env.example` for the current default |
| `NESSIE_BASE_URL` | Nessie API origin |
| `DEMO_DATA_MODE` | `auto`, `fixture`, or strict `nessie` mode |
| `DEMO_ANCHOR_DATE` | Anchor date for the deterministic fictional banking history |
| `SEED_MANIFEST_PATH` | Manifest path relative to `backend/` |
| `RESEARCH_*` | Research call, iteration, timeout, and cache limits |
| `RECOVERY_*` | Targeted research and per-session limits |
| `FRONTEND_ORIGIN` | Allowed origin for direct FastAPI browser calls |

### Next.js server-only: `frontend/.env.local`

| Variable | Purpose |
| --- | --- |
| `BACKEND_URL` | Private FastAPI origin used by Next.js API route handlers |

`BACKEND_URL` is not a `NEXT_PUBLIC_*` variable and is never bundled into browser code.

## Test and build

Run the complete repository checks:

```bash
npm test
npm run lint:backend
```

Or run them individually:

```bash
uv run --directory backend pytest -q
uv run --directory backend ruff check .
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run lint
npm --prefix frontend run build
```

Automated tests use mocked research providers and do not spend Gemini or SerpApi quota.

## Sharing or deploying

GitHub Pages is not compatible with this app because Pages serves static files and cannot
run the Next.js server-side API proxy or FastAPI recovery sessions.

For a short demo, expose only the Next.js port with a temporary Cloudflare Tunnel while
FastAPI remains private:

```bash
cloudflared tunnel --url http://127.0.0.1:3000
```

No purchased domain is required for the generated `trycloudflare.com` URL. The URL remains
available only while the frontend, backend, and tunnel processes are running. Anyone with
the URL can view the fictional sandbox data and trigger Gemini/SerpApi calls, so stop the
tunnel after the demo.

A durable deployment needs hosting for both the Next.js server and FastAPI, persistent
recovery-session storage, appropriate CORS/origin configuration, and access controls before
using any non-fictional data.

## Troubleshooting

- **Fixture badge appears:** confirm `NESSIE_API_KEY`, `DEMO_DATA_MODE`, and the ignored seed
  manifest, then rerun `npm run seed:customer` and restart FastAPI.
- **Frontend cannot reach FastAPI:** verify `BACKEND_URL`, restart Next.js, and call the
  backend `/health` endpoint directly.
- **Recovery session disappeared:** sessions are currently in memory and are cleared when
  FastAPI restarts. The browser will create a fresh session.
- **Research failed or timed out:** verify Gemini and SerpApi credentials and quota. Partial
  provider failures preserve valid evidence and deterministic Route 5 behavior.
- **Port already in use:** use the alternate-port commands above and ensure
  `frontend/.env.local` points at the selected backend port.
- **`uv` is missing:** install it from the official documentation linked above.

Architecture decisions and milestone verification are recorded in
[`docs/DECISIONS.md`](docs/DECISIONS.md) and [`docs/progress/`](docs/progress/).
