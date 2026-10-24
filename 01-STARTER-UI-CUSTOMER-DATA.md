# Build Sheet 01 — Starter UI + Synthetic Customer Data

**Depends on:** repository initialized with Build Sheet 00. **Read first:** `00-PROJECT-BLUEPRINT.md` for final intent. **Implement only this sheet.**

## Goal
Deliver a polished, locally running first vertical slice: a customer can enter a **name**, **hourly wage**, and choose a **car-repair quote**; proceed to a starter dashboard populated with **actual seeded or read-back Nessie sandbox data** and a calculated weekly-income preview. The other screens exist as explicitly labeled, functional **placeholder states**, ready for later build sheets. No agent or real financial crisis simulator yet.

## User-provided screen requirements (from sketches)
1. **Starter screen:** Name; hourly income input; slider for car repair.
2. **Graph + bank information:** graph-being-built/graph area plus banking details.
3. **Solution activity + questions:** indication that a solution is being worked on; occasional question popup later.
4. **Recommended plan:** final plan view (placeholder in this milestone).

**Base customer data requirements:** (a) old financial history → categorized spending; (b) current balance; (c) upcoming payments, e.g. rent and electricity with dates; (d) upcoming income, paid weekly using the user's hourly wage and assumed shifts.

## Scope boundaries
### Implement in this sheet
- App shell/navigation through all four screen stages, with helpful layout and accessible controls.
- The **Starter** screen works fully: editable name, valid positive hourly wage, repair slider with visible value and reset, Continue button, back navigation and preserved inputs.
- Real backend routes returning one consolidated `customer_snapshot` from Nessie where supported, with honest provenance and errors.
- Synthetic customer seeding and reproducible 90-day activity plus persistent ID handling, not a production multi-user system.
- Transaction normalization and categorized spending charts/cards, balance, future scheduled bills, income preview.
- Graph pane **placeholder** describing future graph-building (optionally draw a static simplified skeleton, visibly marked preview). Research/questions/plan placeholders **must not pretend the actual agent ran**.
- Test and document setup, seed, backend/frontend connection and no-key fallback mode.

### Do NOT implement in this sheet
- No Gemini calls, SerpApi calls, financial crisis propagation, intervention graph activation, question-decision logic, action search, optimization, live recommendations or production banking onboarding.
- No real user bank connections, payments, lending, approval claims, auth infrastructure or paid deployment.
- Don't spend time inventing detailed screen requirements beyond the attached rough concept; design sane defaults.

## A. Working pages and UI behavior

### Screen 1 — Start scenario
- Hero: short emotional premise, e.g. “One bad day shouldn't become a bad month.”
- Text input **Name**; prefill optional synthetic profile name, let user edit a display name without automatically creating new Nessie customer each keystroke.
- Currency input **Hourly wage ($/hr)**: numeric, 0 < wage <= sensible demo max, two decimal precision; immediate derived gross $/shift and $/week. Default configurable demo value (e.g. $20/hr).
- **Car repair quote slider** e.g. $100–$1,500 stepping by $50, default $400. Show the exact value.
- Clearly label assumptions: 5 shifts/week, 8 hrs/shift, 40 hrs/week. Include estimated take-home as a labeled assumption if shown (e.g. 80%, adjustable later). Prefer showing **gross** first to avoid confusing banking deposit data with estimated pay.
- “Begin scenario” loads the customer snapshot, then routes to the dashboard. Loading, retry, API unavailable and mock-mode banners are handled.

### Screen 2 — Financial snapshot + graph placeholder
Desktop: two-column layout (financial cards / graph canvas); mobile: stacked sections. Display:
- Customer display name, scenario repair quote and calculated weekly gross income.
- Checking/savings account type(s) and **current balance from Nessie** (no invented balance presented as Nessie).
- **90-day historical spending** aggregated into labeled categories, with totals, monthly averages and a compact chart. Show “Unknown/Other” for transactions without confident classifications.
- **Upcoming payments** list containing obligation name, amount, due date, status and source (`nessie_bill` or `synthetic_schedule`). These future commitments are **not** the same as already-paid purchase records.
- **Upcoming income** schedule: 40*r gross each weekly payday, 8*r per shift. If presenting take-home projections, use clearly displayed estimated multiplier; avoid representing synthetic projections as a recorded Nessie deposit.
- Graph/loading canvas placeholder with projected chain teaser and “Full financial cascade in Build Sheet 02.” Do not claim running analyses.
- Navigation to future placeholder stages; snapshot refresh button; obvious error/empty states.

### Screen 3 — Agent research + questions placeholder
- Outline which kinds of problems future agent will investigate (transportation, attendance, repair affordability, bill flexibility).
- Show mock sample question only if explicitly labeled **Demo preview — not an active agent**; no fake progress/search result citations.
- Buttons to navigate back and onward.

### Screen 4 — Recommended plan placeholder
- Explain later milestone will compare 2–3 coordinated plans, bill protection, cost and unresolved assumptions.
- A non-deceptive sample layout skeleton is acceptable, labeled preview; no made-up verified sources or claims of selected winning plan.
- Allow restarting / adjusting inputs.

## B. Nessie synthetic customer — required data contract

Define a typed, versioned `CustomerSnapshot` consumed by the UI. Suggested conceptual shape (Codex choose actual files/implementation):

```json
{
  "schema_version": 1,
  "customer": {"id": "nessie-customer-id", "display_name": "Maya"},
  "accounts": [{"id": "nessie-account-id", "type": "Checking", "balance_cents": 31000}],
  "history": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "transactions": [], "categories": []},
  "upcoming_bills": [{"id": "rent", "name": "Rent", "amount_cents": 90000, "due_date": "YYYY-MM-DD", "source": "synthetic_schedule", "status": "scheduled"}],
  "income_projection": {"hourly_rate_cents": 2000, "shift_hours": 8, "shifts_per_week": 5, "gross_per_shift_cents": 16000, "gross_weekly_cents": 80000, "pay_frequency": "weekly", "next_pay_dates": []},
  "scenario": {"repair_quote_cents": 40000},
  "source": {"banking": "nessie", "simulation_data": "seeded_synthetic"}
}
```

For `transactions`, normalize at least `id`, `date`, `amount_cents`, `direction`, `merchant_display`, `category`, `source` and `account_id`; permit missing raw merchant information. Support server-side transformation of Nessie's actual resource shapes. For future API uses, avoid breaking this contract.

### Seed the sandbox customer reproducibly
- Create **one fictional persona**, e.g. Maya, hourly worker in Austin, with a plausible balance (~$310), category-diverse purchase history covering roughly 90 days, and realistic recurring bills. Exact values should be coherent but are illustrative.
- **Inspect Nessie documentation and responses before coding against endpoints**. Customer, account, deposit, purchase and bill resources are documented, but request fields may differ; do not guess resource semantics or silently ignore errors. See https://prod.nessieisreal.com/docs.
- Build a `seed` CLI/API-internal tool that creates the customer, account and supported history records; persist returned IDs in an **ignored local seed manifest**. On rerun, validate/reuse IDs before inserting to avoid duplicates. Offer explicit manual reseed/recreate if records need resetting.
- Populate **bank balance consistently**. Understand whether Nessie account creation uses an initial balance and how recorded purchase/deposit operations change balance. Avoid creating 90 days of purchases and deposits in ways that make the final balance incoherent. If API semantics prevent direct arbitrary balance assignment, explain and choose a feasible controlled seed sequence.
- Seed merchant records where required for purchases, or map existing supported merchants. Use supported API endpoints, with straightforward rate limiting/retries as appropriate.
- If future bills can be recorded through Nessie, use bills; if due-date requirements aren't represented in the API, keep explicit **synthetic schedule entries** in a local fixture and mark `source=synthetic_schedule`. Do not falsely claim every upcoming due date came from Nessie.
- Weekly income **forecast** is based on user-entered hourly rate. Historical Nessie deposit records may be seeded as past paychecks, but those records must remain distinct from projected future income.
- Use a deterministic relative-time schedule or frozen demo anchor (`DEMO_ANCHOR_DATE` in config) so due dates/90-day periods remain coherent on demo day. Record which choice was made.

### Categories and computations
- `monthly_average_cents = round(total_category_spend_last_90_days / 3)` when using an exact three-month approximation. Label it approximate; date-normalize if desired, with tests.
- Category defaults: Housing/Rent, Groceries, Dining, Transportation/Gas, Utilities, Insurance, Shopping, Subscriptions, Health, Other.
- Only categorize purchases based on merchant/category and documented mapping. Keep ambiguous transactions in Other, don't claim LLM enrichment happened.
- Prevent double counting when the same recurring bill is represented in purchases and the upcoming-bill schedule. Historical charts use past charges; future bills are planned obligations.
- Wage preview: `gross_per_shift=8*r`; `gross_weekly=40*r`; optional estimated net `gross_weekly*alpha` clearly labeled with assumption.

## C. Configuration, security and error handling
- Reuse repo stack and established patterns from Build Sheet 00; don't restructure without clear need.
- Backend `.env` includes `NESSIE_API_KEY`, `GEMINI_API_KEY`, `SERPAPI_API_KEY` plus optional base URL, demo date/mode. **Only Nessie is called in Sheet 01.** Other keys are configured for future milestones but not invoked.
- `.env.example` contains placeholders, never actual secrets; `.env` and seed manifests ignored by Git. Don't expose API keys via Next.js `NEXT_PUBLIC_` or responses or logs.
- If Nessie key unavailable, allow explicitly labeled **local synthetic demo mode**, with fixture-driven UI and an obvious mock badge; it must not silently masquerade as live Nessie data.
- Missing/expired credentials, partial seeds, unexpected API payloads and rate limits yield clear errors with retry instructions. Never leak full responses if they may contain credentials.

## D. Backend endpoints / coordination
Codex can choose names; these capabilities are required:
- `GET /health` or existing health endpoint.
- `GET /api/customer/snapshot` (or existing route): returns normalized customer snapshot and source metadata.
- `POST /api/customer/seed` **only for local dev** or equivalent CLI; avoid exposing destructive endpoints publicly. Prefer CLI.
- Scenario input (name, wage, repair quote) must be reflected in the returned projection/overlay without mutating the historical Nessie account by accident.
- Frontend API client with typed response/error handling and clear separation between server configuration and browser state.

## E. Verification / acceptance checklist
- [ ] One-command local frontend and backend startup instructions documented and tested.
- [ ] Start page has editable name, positive hourly input, repair quote slider, derived $/shift and $/week.
- [ ] Input state persists during navigation; modifying input updates derived values correctly.
- [ ] Seeding retrieves one Nessie customer and accounts; returning data is displayed in UI with accurate source.
- [ ] Re-running seed does not create duplicates under normal conditions.
- [ ] History is ~90 days with categorical spending totals and totals reconcile to individual transactions.
- [ ] Current balance is read back from Nessie or a clearly labeled fixture; upcoming bills have due dates and source.
- [ ] Weekly future income uses `40*hourly_rate`; 8-hour shifts; forecast is clearly distinct from past deposits.
- [ ] All four UI stages are navigable; stages 3–4 and full graph explicitly remain previews.
- [ ] Loading, empty, error and no-key/mock mode look reasonable.
- [ ] No real key is committed, printed in docs, served to browser or captured in logs.
- [ ] Tests cover normalization, category sum, weekly-pay math, seed idempotency or testable seed logic, and critical UI input behavior.
- [ ] README explains credentials, seeding, running and known limitations; milestone report records what actually passed.

## F. Deliverables
- Working frontend + backend code in existing repository.
- Local idempotent Nessie seeder and saved synthetic profile configuration.
- Shared customer snapshot contract/typed schemas.
- README additions for setup and local demo.
- `docs/progress/M1.md` with evidence for verification and decisions/limitations.

**Stop after the first milestone.** Do not implement graph consequences, live research, a Gemini agent, or recovery plans until authorized.
