# Build Sheet 03 — Gemini Agentic Research + SerpApi Intervention Discovery

**Project:** One Bad Tuesday — HackTX 2026  
**Milestone:** M3 — Research and action discovery  
**Implementation repository:** `MMehta45/hacktx26`  
**Product source of truth:** repository-root `00-PROJECT-BLUEPRINT.md` (use the refreshed companion context file if supplied)  
**Reference build-sheet style:** `AlanRoybal/hackgt/prompts/01-claude-code-build.md` — explicit source of truth, verification, milestones, decisions log, honest tests  
**Status:** Implementation specification, not a report of completed work

---

## 0. How to work — read first

You are implementing **only Build 03**, not rebuilding the repo or jumping into full recovery planning.

1. Inspect the actual current repository before editing anything. At minimum read `README.md`, `00-PROJECT-BLUEPRINT.md`, `docs/02-CRISIS-SIMULATOR-GRAPH.md`, `docs/DECISIONS.md`, `docs/progress/M1.md`, `docs/progress/M2.md`, `backend/app/models.py`, `backend/app/simulation_models.py`, `backend/app/simulation.py`, `backend/app/snapshot.py`, `backend/app/main.py`, `backend/app/config.py`, `frontend/src/components/scenario-app.tsx`, and the existing API proxies and tests.
2. Write a short **M3 implementation plan** inside `docs/progress/M3-PLAN.md` describing the exact interface changes, schema and tool approach, local test strategy, and any dependencies. Do not stop for approval: implement this authorized milestone after writing the plan.
3. Reuse the working **Next.js 16 + TypeScript frontend**, **FastAPI + Python backend**, current **Nessie-backed snapshot**, and **deterministic M2 simulator**. Extend their interfaces minimally. Do not regenerate the application scaffold.
4. Build in the order specified in §15. After each phase run the relevant tests and fix regressions. Never claim the live providers were tested unless real requests succeeded. Keep cost and API-call counts visible in the progress report; avoid unnecessary SerpApi calls.
5. Document material architecture choices in `docs/DECISIONS.md` and the tested outcome in `docs/progress/M3.md`; include precise manual tests if a browser or provider behavior cannot be verified automatically.
6. **Stop after M3.** Do not implement action application, plan combinations, mitigated graph calculations, or the final UI redesign. Those belong to M4/M5.

### Definition of done (one sentence)

After running the untreated car-breakdown simulation, the user can click **Find ways out**, watch a truthful research activity feed backed by **real Gemini reasoning and real SerpApi queries**, and see **source-linked, typed potential interventions and up to two useful unanswered clarifying questions**, without any invented recommendations or financial outcomes.

---

## 1. Product context — what we're ultimately building

**One bad day shouldn't become a bad month.** The prototype models how a car breakdown causes an hourly worker to miss shifts, lose upcoming pay, and risk unpaid essential bills. The application then **reasons backward from the damaging financial outcome**, researches possible ways to interrupt that chain, asks a small number of high-leverage questions, combines feasible interventions, and reruns the same deterministic cash-flow engine to determine whether they prevent the problem.

- **Capital One Nessie:** real sandbox API supplying fictional customer/account/transaction/bill records. The customer and accounts are synthetic, not a user's actual bank.
- **Python simulator:** authoritative mathematical model of dated income, outgoing obligations, bill shortfall, graph statuses and the untreated crisis.
- **Gemini:** proposes hypotheses, chooses external research queries and tools, interprets evidence, extracts structured candidates and identifies questions. Gemini is **not** the authority for financial calculations, eligibility, route feasibility, or provider claims.
- **SerpApi:** backend-accessed real Google Search, Google Maps places, Google Maps Directions/transit research. Results are evidence for possible actions, not proof of acceptance, personal eligibility, appointments, or quoted prices unless explicitly supported.
- **M4 optimizer:** tests combinations and updates the cash-flow/graph against verified action effects. **Do not build M4 yet.**

### Product flow

1. **Start:** name, wage, repair quote, affected shifts.
2. **Crisis:** show the untreated graph and normal-vs-crisis financial timeline.
3. **Explore (THIS BUILD):** backward priority analysis → Gemini-generated hypotheses → SerpApi calls → findings → structured candidate actions → prioritized unknown questions.
4. **Plan (FUTURE):** answer questions, simulate combinations, rank 2–3 plans, show mitigated/unresolved nodes and dated savings/risks.

This stage should be a real functional research milestone, **not** another static preview and **not** a full UI overhaul.

---

## 2. Locked facts from M1/M2 — do not break these

The repository currently provides:

- `GET /api/customer/snapshot`: typed synthetic customer snapshot, account balance and provenance, 90-day history, category summaries, dated upcoming bills, weekly income forecasts and normal cash flow.
- `POST /api/simulations/crisis`: returns `{snapshot: CustomerSnapshot, simulation: SimulationResult}` for an untreated crisis.
- `simulate(snapshot, scenario, actions=[])`: pure deterministic function in `backend/app/simulation.py`; **rejects nonempty actions in M2**. Do not change that constraint in M3.
- `SimulationResult` fields include `source`, `scenario`, `events`, `cashflow`, `income_lost_by_payday`, `bill_outcomes`, `unpaid_bills`, `peak_funding_gap_cents`, `unpaid_essential_total_cents`, `graph_nodes`, `graph_edges`, `warnings`.
- M2 data contracts use **integer cents** and explicitly dated forecast events. Projection timezone is **America/Chicago**, with a reproducible anchor date. Preserve date/source identity.
- The existing four-stage `ScenarioApp` frontend currently has Stage 3 `ResearchPreview` and Stage 4 `PlanPreview`. **Replace Stage 3 with a real Explore stage. Preserve Stage 1/2 behavior and leave Stage 4 honest/inactive.**
- Current backend configuration already has `GEMINI_API_KEY` and `SERPAPI_API_KEY` fields. Do not create new naming conventions for the same credentials; add a configurable model name and reasonable research limits.

### Existing seeded example (verification reference, not a hardcoded answer)

M2's recorded live sandbox verification: Maya Rodriguez, $310 checking balance, 89 history records, two missed eight-hour shifts at $20/hour, estimated $256 lost take-home on the covered payday, $400 **unpaid** repair quote, $501 projected peak funding gap, $391 uncovered rent and $110 uncovered auto insurance. Real M3 reads current M2 output; **never assume these values are immutable**, never copy them into actual API responses and never alter Nessie records to make the research story work.

---

## 3. Canonical 14-node problem graph

**The graph is for problems only. Never insert candidate actions into graph nodes.** The graph is a catalogue of potential dependencies and the untreated projection marks statuses conditionally. Respect all 14 stable IDs in M2; use them unchanged for candidate action `addresses_node_ids`.

```mermaid
flowchart TD
    A[Car breaks down] --> B[Car unavailable]
    B --> C[Commute disrupted]
    C --> D[Missed work]
    D --> E[Reduced paycheck]
    E --> F[Cash shortfall]
    F --> G[Bills unpaid]
    A --> H[Unexpected repair expense]
    H --> I[Cash reserves depleted]
    I --> F
    C --> J[Extra transportation costs]
    J --> F
    I --> K[Repair delayed]
    K --> B
    F --> L[Emergency borrowing]
    L --> M[Future debt payments]
    M --> F
    G --> N[Late fees]
```

IDs from `backend/app/simulation.py`:

`car_breaks_down`, `car_unavailable`, `commute_disrupted`, `missed_work`, `reduced_paycheck`, `cash_shortfall`, `bills_unpaid`, `unexpected_repair_expense`, `cash_reserves_depleted`, `repair_delayed`, `extra_transportation_costs`, `emergency_borrowing`, `future_debt_payments`, `late_fees`.

**Actual graph contract:** 14 nodes, 17 edges. It includes time-dependent feedback edges; traversal must use a visited set and never recursively spin forever. Target only nodes contributing to the negative outcome in the **active/projected relevant subgraph**, while still allowing an actionable direct intervention at `bills_unpaid` (e.g., a possible due-date extension) and upstream solutions (e.g., commute, missed work, repair).

**False assumptions to avoid:** An unpaid repair quote does not drain cash, the default scenario does not automatically borrow or purchase transit, an employer has not preapproved remote work, a bill has not automatically accrued late fees, and a search result does not prove that assistance is available to this customer.

---

## 4. Locked formulas and their ownership

**Existing M1/M2 equations are the source of numerical truth. M3 may refer to them to set research priorities or estimate *potential* magnitude, but it must not change or recompute finalized plan cash-flow outcomes.** All calculations use cents/Decimal and customer-local dates.

| Formula | Meaning | M3 usage |
|---|---|---|
| `W_gross = 40*r` | Weekly gross pay, `r` dollars per hour | Context, no bank mutation |
| `S_gross = 8*r` | Gross pay per shift | Context |
| `L_net = 8*r*m*alpha`, alpha default `0.80` | Estimated take-home earnings lost for `m` missed shifts | **Upper bound** for income-preservation hypotheses; reconcile with M2 actual `income_lost_by_payday` |
| `M_c = sum(90-day spending in category c)/3` | Historical average monthly category spend | Generate research ideas only; **not** immediately available cash or guaranteed savings |
| `B_normal(t) = B0 + Σ_{d<=t} income(d) - Σ_{d<=t} obligations(d)` | Baseline dated cash forecast | Read from M2 |
| `B_crisis(t) = B_normal(t) - Σ_{d<=t} wage_loss(d) - Σ_{d<=t} actually_incurred_crisis_cost(d)` | Untreated case | Read from M2; unpaid repair quote is **not** an incurred cost |
| `G = max(0, -min_t B_crisis(t))` | Peak raw funding gap | Prioritize timing/scale; **not** necessarily the total amount of essential bills unpaid |
| `U = Σ unpaid_essential_bill_amounts_on_due_dates` | Essential obligations unmet on due dates (constrained ledger) | **North-star outcome** for M4; M3 uses current outcome as research goal |
| `P(node) = impact × urgency × actionability` | Search-priority heuristic, each dimension integer 1–3 | **Implement in M3**; not a financial optimization score |
| `Q(question) = decision_impact × uncertainty × top_plan_relevance` | Question-priority heuristic, each 1–3 | **Implement provisional ranking in M3**; top-plan relevance is **estimated from research candidates**, not from an M4 optimizer |
| `B_plan(t) = B_crisis(t) + Σ_actions Σ_{d<=t} Δ_action(d)` | Future financial effects of actions, deduplicated | **Reserved for M4**, not implemented here |
| `N(n<=3) = C(n,1)+C(n,2)+C(n,3)` | Future combinations; 8 candidates → 92 combinations | **Reserved for M4** |

**Critical rules:**

1. Income loss is applied on each affected **payday**, not immediately on missed-shift dates.
2. An intervention preserving a missed shift later **removes the original lost-wage event**; it does **not** invent a second income payment.
3. Only future spending that is demonstrably avoidable may be counted as savings; history is a clue.
4. A loan creates future liabilities; a due-date extension moves the obligation rather than erasing it; an unpaid quote is not a debit.
5. Never add candidate action estimates into the live balances or stage-2 simulation in M3.
6. Research priority and question scores are coarse 1–3 heuristics, **never probabilities, eligibility scores, or claims of actual dollar benefit**.

---

## 5. M3 user stories and testable acceptance criteria

### Story R1 — Identify research targets from the active crisis

_As a customer, I want the assistant to focus on the reasons my essentials become unaffordable, so that it doesn't waste time researching unrelated suggestions._

- **Given** an M2 simulation with `unpaid_essential_total_cents > 0`, **when** research starts, **then** the backend starts at `bills_unpaid`, traverses upstream safely and returns 3–4 meaningful ranked intervention targets where available.
- **Given** inactive conditional branches, **then** they cannot be presented as already-completed financial damage.
- **Given** a cycle through repair delay or future debt, **then** the traversal finishes deterministically with no infinite recursion.
- **Given** zero unpaid essential bills, **then** the system truthfully explains that there is no current terminal bill failure and may research remaining near-term risks without inventing one.

### Story R2 — The LLM controls relevant external investigation

_As a customer, I want relevant local and online possibilities discovered from actual sources, not generic prewritten advice._

- **Given** a target such as `commute_disrupted`, **when** Gemini reasons about solutions, **then** it chooses appropriate tools and search parameters; the backend executes the selected **real SerpApi** calls.
- **Given** a `search_web`, `search_places`, or `find_transit` request, **then** every call is constrained by schemas, geographic/date context, budgets, timeouts and backend-only credentials.
- **Given** no route addresses or shift time, **then** transit can't be marked feasible; research generates the needed question or uses available general transport information clearly labeled as incomplete.
- **Given** a failed call or no results, **then** report the failure/no-results clearly rather than fabricate a candidate.
- **Given** actual response data, **then** each public-facing finding retains an evidence URL, source type and retrieval timestamp where available.

### Story R3 — Structured possible actions, not recommendations

_As a customer, I want to see what might help and what still has to be confirmed._

- **Given** a usable source, **when** Gemini extracts an intervention, **then** it produces an action conforming to a strict Pydantic model with graph node IDs, mechanism, time/cost assumptions, evidence, requirements and verification statuses.
- **Given** an unsupported specific dollar amount, **then** mark the price `unknown` or `estimate` with rationale; do not mark it `verified`.
- **Given** a public service listing, **then** do not claim availability, eligibility, payment-plan approval, employer permission or bill deferment without corresponding evidence/confirmation.
- **Given** duplicated sources describing the same option, **then** deduplicate and retain merged evidence, not duplicate action cards.
- **Given** fewer than six defensible actions, **then** return fewer with a limitation; do not invent filler to hit a target count.

### Story R4 — Only ask valuable questions

_As a customer, I want the app to ask questions only when the answers could change an intervention's viability._

- Generate zero to two prioritized clarifying questions per research result.
- Connect each question to a candidate or target and an unresolved requirement.
- Prefer search over questioning when public evidence can directly resolve the fact; never assume public search can verify personal permissions.
- No actual Q&A-driven replanning yet; return questions as pending M4 inputs, with UI cards that do not fake answers or completed decisions.

### Story R5 — Transparent Explore stage

_As a judge, I want to see actual tool use and inspect evidence._

- Stage 3 displays selected graph targets, authentic backend research events, tool/source type, candidate actions and unresolved blockers; retain links to sources.
- Distinguish `researching`, `complete`, `partial`, `failed`, `no_results`, and `not_configured` states.
- Re-entering Explore with identical scenario should reuse cached results where valid; changing a relevant scenario input must not display stale findings as fresh.
- The Plan stage remains visibly future-only; no UI card falsely asserts a financially validated recovery plan.

---

## 6. Input: consume the real M2 contract and preserve provenance

The existing `POST /api/simulations/crisis` consumes `CrisisSimulationRequest` and returns `CrisisSimulationResponse`. M3 should reuse **the same scenario validation** and **the same backend `get_snapshot(...)` / `simulate(snapshot, request, actions=[])`** rather than inventing a second, subtly different crisis calculator.

### Recommended M3 backend contract

`POST /api/research/interventions` with:

```json
{
  "scenario": {
    "display_name": "Maya Rodriguez",
    "hourly_rate_cents": 2000,
    "repair_quote_cents": 40000,
    "affected_shift_count": 2
  },
  "context": {
    "city": "Austin, TX",
    "timezone": "America/Chicago",
    "home_location": null,
    "work_location": null,
    "shift_start_local": null,
    "shift_end_local": null
  },
  "force_refresh": false
}
```

Design the actual Pydantic request type and validate all fields. The location fields are **synthetic demo context** and not sourced from Nessie. Do not introduce real personally identifying addresses. If useful, provide a configurable, clearly labeled **fictional-but-geocodable** home/work demo route pair and work schedule; confirm that routes actually exist before any feasible-route claim. If no verified routing inputs are supplied, show a blocker instead. `force_refresh` may bypass cache but remains subject to call budgets.

The M3 handler must:

1. Obtain **one coherent snapshot** using the same M2 read method, then run `simulate(snapshot, scenario, actions=[])` exactly once for that result. Do not mix banking reads from different instants.
2. Use the resulting `SimulationResult` for graph traversal, current financial impact, bills, shift dates, and research objective.
3. Return a **simulation fingerprint** based on relevant source/customer/scenario fields (no secrets), the source timestamp/anchor, and a `ResearchResult`. Ensure the frontend associates the research with the correct scenario; if the backend re-simulates, return its authoritative financial summary or exact response/fingerprint and replace any stale frontend M2 state safely.
4. Do not trust client-supplied arbitrary `graph_nodes`, balances, or dollar harms as ground truth.
5. Do not mutate Nessie or rewrite historical transactions. This is read-only research.

If the existing route architecture makes a different shape more maintainable, document the choice and keep the same correctness guarantees.

---

## 7. Deterministic backward traversal and target priority

### Algorithm

1. If `bills_unpaid` is projected, use it as the root; include its active/meaningful upstream causes and the root itself as a potential intervention target. If not projected, explain what terminal risk (if any) remains and avoid claiming an unpaid bill.
2. Build reverse adjacency from M2's actual `graph_edges`. Traverse with `visited` to handle cycles.
3. Distinguish three categories: **directly contributing projected problem**, **conditional branch requiring more information**, and **inactive branch that must not be described as current harm**.
4. Don't blindly multiply descendant counts. Rank the *intervention usefulness* of a node, not simply its graph degree. Couple impact to unpaid dollar exposure/deadlines where possible; use small discrete scores and explanations.
5. Score each eligible target with `P(n)=impact(n)×urgency(n)×actionability(n)`; dimensions 1–3. Tie-break deterministically by urgency then stable node ID. Return at most four, preferably across distinct mechanisms (commute/income, repair/transport, cash/bill timing) rather than four adjacent synonyms.
6. Produce a short `why_this_target` grounded in M2 outcome; e.g. avoiding two missed shifts might protect the upcoming paycheck. **Do not** assert resolving that node alone protects bills—the repair/payment branches may still contribute.
7. Guard against no unpaid bills, no shifts, zero quote, missing pay period, bill before payday, and feedback edges.

### Example *illustrative* prioritization, not hardcoded output

| Target | Impact | Urgency | Actionability | Priority |
| --- | ---: | ---: | ---: | ---: |
| `commute_disrupted` | 3 | 3 | 3 | 27 |
| `missed_work` | 3 | 3 | 2 | 18 |
| `cash_shortfall` | 3 | 2 | 2 | 12 |
| `unexpected_repair_expense` | 3 | 2 | 2 | 12 |

**Tests must cover** graph with cycles, conditional/inactive nodes, deterministic scores, no positive `bills_unpaid`, and avoiding overcounting an inactive repair-paid branch.

---

## 8. Gemini agent design — genuinely agentic, bounded, inspectable

Use the supported official Google GenAI Python SDK (`google-genai`, not the retired `google-generativeai` package) and the configured `GEMINI_API_KEY`. Put the model name in `GEMINI_MODEL` as an env option, verify availability for the configured key and choose an available low-latency model. Do not hardcode a model that may not be accessible. Use native function/tool calling (automatic or explicit loop, with **backend-owned execution and counters**).

### Agent input

Provide a bounded summary, not the entire 90-day ledger or API keys:

- Scenario anchor/timezone, synthetic city and available home/work/shift coordinates/times.
- Highest-impact unpaid essential bills: names, amounts, due dates, uncovered amounts.
- Current balance and dated pay-loss projections, payday dates, repair quote/status, `peak_funding_gap_cents`.
- Selected graph targets: IDs, descriptions, statuses, activation dates and why selected.
- Helpful spending-category summaries for *research hypotheses*, explicitly marked historical.
- Existing research tool results, errors, candidate actions and unresolved questions from this run.
- Constraints: no made-up prices, no personally guaranteed eligibility, no double-counted wages, no solutions as graph nodes, no final ranking in M3.

### Suggested stages

1. **Plan hypotheses:** Gemini offers a small list of different mechanisms: preserve shifts via transit or working arrangements, reduce repair cash timing, explore assistance/payment flexibility, reduce a scheduled discretionary outflow, etc. LLM may suggest mechanisms independently; don't bake every search response or solution into the graph.
2. **Choose tools:** Gemini chooses among the three allowed SerpApi tools and specifies targeted queries using research context. Tool calls must be actual model-selected calls, not only pre-scripted query sequences disguised as an agent. It can chain a follow-up call when a prior result identifies a new question/location.
3. **Inspect and refine:** after observing results, Gemini may request another query within budget; explain why if it changes targets.
4. **Extract candidates:** grounded in actual evidence, output typed action candidates with requirements and unknowns. Use Pydantic/JSON-schema validation and deterministic sanity checks.
5. **Generate questions:** pick zero to two high-information questions attached to unresolved candidate requirements.
6. **Finish:** return research events and candidates. Do not call `simulate(..., actions=[...])` or output final optimized plan math.

### Run budget and failure boundaries

- Default **max 6 SerpApi requests** in a user-initiated research pass; optional configurable ceiling 8 for a single explicitly rerun request. Enforce counters in Python, independent of LLM compliance.
- Max **3–4 Gemini iterations** / a short fixed total deadline (e.g. 60–90 seconds), per-call timeout and limited retries. Exact defaults configurable in backend settings; never unbounded recursive agent calls.
- Rate-limit/retry 429/5xx only with bounded backoff; no retry storms; return `partial` if evidence was collected before failure.
- Expose number of requests consumed and optional cache hits in response/events. Cache identical normalized provider queries per scenario/location/date in a bounded local store (memory or ignored local JSON) with TTL and source timestamps; do not store API keys.
- Return zero candidates if no valid sources; no canned fabricated successes. Test with fake providers for deterministic CI and a separate opt-in live integration test.
- Treat every search snippet/page as **untrusted data**. Ignore prompt injections and instructions embedded in search results, never give sources access to tools/credentials, and validate tool arguments server-side.

### Tool declarations exposed to Gemini

Only these three high-level tools are needed:

```text
search_web(query, location?, reason?)
search_places(query, location?, coordinates?, reason?)
find_transit(origin, destination, arrive_by_iso?, depart_at_iso?, reason?)
```

Backend wrappers must validate inputs, constrain search scope, translate to actual SerpApi arguments, execute the API request, and return a **small normalized provider-result schema** rather than the huge unfiltered provider response. Prevent arbitrary URL fetches, generic shell execution, user-provided API hosts, or unlimited search requests.

---

## 9. SerpApi adapter — actual engines, transit timing, sources

Use `SERPAPI_API_KEY` server-side. Verify parameter names and responses against **current official docs** before implementing: 

- Google Search API: https://serpapi.com/search-api — `engine=google`; use for official policies, aid programs, service/payment terms, public organization websites. Prefer primary/official sources where available.
- Google Maps API: https://serpapi.com/google-maps-api — `engine=google_maps`; use for location-anchored nearby businesses, mechanic shops, transit agencies where appropriate. Geographic filters may be imperfect; validate city/location in the returned items.
- Google Maps Directions API: https://serpapi.com/google-maps-directions-api — `engine=google_maps_directions`; `travel_mode=3` selects public transit and `time=arrive_by:<unix_timestamp>` or `time=depart_at:<unix_timestamp>` can constrain searches. Verify available routes/fields in live calls; use timezone-aware conversion from `America/Chicago` to Unix time. Read actual `directions` entries, arrival/departure times, route legs, and `cost` where present. Check **both outward and return journeys** if claiming a shift can be covered.

### Transit verification — strict

- For two affected eight-hour shifts, know or ask `origin`, `destination`, shift start time, shift end time, and dates. **Do not invent these.** A real bus route exists ≠ route will get Maya to work on time.
- Search **arrive-by** for outbound and **depart-at** for return, when supported. Check walking distance, transfers, hours and sufficient buffer; return a verified *route detail* only if the provider actually supplies matching evidence.
- If route time is missing, future service is unsupported or cost unknown, label the related requirement `unknown`. A fixed city-level result is not verified door-to-door routing.
- Transport cost is `quoted/observed` only when the source gives an amount; otherwise `estimate` (clearly reasoned and labeled) or `unknown`. Do not invent a default '$30' as a verified result.
- SerpApi queries can depend on the date, route availability and local schedule; keep these inputs in cache keys.

### Credibility and provenance

For each search result capture (as available): `tool`, `provider_engine`, `query`, `title`, `url`, `snippet/description`, `source_domain`, `retrieved_at`, place address/coordinates, **source type** and a stable internal evidence ID. Do not propagate the SerpApi API key embedded in provider metadata URLs (redact `api_key` and other secret parameters before returning anything to the frontend).

A source can substantiate *what the provider lists*. It usually **cannot** substantiate personalized approval, exact future price, qualification for aid, or a mechanic accepting this particular car/job. The UI must distinguish evidence-backed facts from customer-dependent constraints.

### Research categories to cover (ideation, not hardcoded outcomes)

- **Transportation:** public transit, limited ride alternatives, temporary travel arrangements, accessibility and work-hours tradeoffs.
- **Protect work/income:** remote work, shift swaps, alternative shifts and make-up hours; these typically require customer/employer confirmation, not public search.
- **Car repair:** lower-cost quotes, local nonprofit referrals, whether a named shop publicly advertises payment options. Never claim personalized approval.
- **Bills/cash timing:** published biller hardship/deferral channels, emergency assistance, scheduled discretionary charges that might actually be canceled. Do not auto-create borrowing plans.
- **Borrowing risk:** if considered, mark all unknown rates, fees and repayments; M3 does not recommend or execute borrowing.

Ensure diversification: a typical useful result includes multiple intervention mechanisms, not 8 generic searches about the same car-repair keyword.

---

## 10. Typed output contracts — define for M4 compatibility

Create `backend/app/research_models.py` (or best-fit location) with Pydantic models that reject unsupported fields and validate known node IDs, amounts, status enums, and source links. Add corresponding frontend TypeScript definitions and tests.

### A. Priority target

```json
{
  "node_id": "commute_disrupted",
  "impact": 3,
  "urgency": 3,
  "actionability": 3,
  "priority_score": 27,
  "reason": "Two upcoming shifts are threatened, creating a dated paycheck reduction."
}
```

### B. Evidence item

```json
{
  "id": "evidence-001",
  "source_type": "transit_directions",
  "provider_engine": "google_maps_directions",
  "title": "Example transit itinerary",
  "url": "https://example.org/official-route-or-source",
  "query": "route request summary",
  "retrieved_at": "2026-10-24T21:30:00-05:00",
  "facts_supported": ["A mapped trip is described by the provider"],
  "limitations": ["Eligibility and future availability are not established"]
}
```

**Example values above are illustrative contract shapes, not real SerpApi findings; do not ship them as real research.** Evidence URLs must be valid, sanitized HTTP(S) destinations from results or stable provider pages; if a result supplies no usable source URL, preserve internal provenance and mark limitations rather than inventing a URL.

### C. Candidate action (not a confirmed recovery plan)

```json
{
  "id": "candidate-transit-001",
  "title": "Take a temporary transit route to upcoming shifts",
  "mechanism": "income_preservation",
  "addresses_node_ids": ["commute_disrupted", "missed_work"],
  "description": "Potential way to keep work attendance despite a disabled car.",
  "requirements": [
    {
      "key": "home_and_work_locations_known",
      "status": "unknown",
      "description": "Precise fictional routing endpoints are not yet configured",
      "verification_source_ids": []
    }
  ],
  "cost": {
    "amount_cents": null,
    "currency": "USD",
    "status": "unknown",
    "basis": "Fare not verified"
  },
  "timing": {
    "earliest_start_date": null,
    "latest_completion_date": null,
    "duration_description": "Requires commute-time check"
  },
  "potential_effects": {
    "shift_dates_potentially_protected": [],
    "expense_avoided_cents": null,
    "expense_avoidance_date": null,
    "bill_due_date_change": null
  },
  "evidence_ids": [],
  "verification_status": "unverified",
  "remaining_unknowns": ["origin", "destination", "shift timing", "fare"]
}
```

This is a **schema template only**, not a candidate that should be returned automatically. No action may be classified as evidence-backed without at least one applicable source reference. If a candidate is a hypothesis with zero evidence, label it explicitly as `hypothesis` and keep it visually separate from `researched` actions; it must not pass as a confirmed provider option.

**Required action categories:** `transportation`, `income_preservation`, `repair_affordability`, `bill_flexibility`, `budget_adjustment`, `assistance`, `borrowing_risk` (use reasonable typed representation). Include optional structured dates, eligibility/confirmation requirements, source IDs, confidence as an explanation rather than an invented numeric probability, cost uncertainty, source/provider type and M4-compatible effect hints.

**Requirements:** `verified`, `unknown`, `false`, `user_confirmed` are distinct statuses. Do not use `verified` if the evidence doesn't actually establish the specific requirement. An intervention with unknown required terms remains **conditional**. Requirements that are false make the action impossible unless the underlying assumptions change.

### D. Clarifying question

```json
{
  "id": "question-remote-work",
  "question": "Would your employer permit you to work remotely for the next two shifts?",
  "addresses_node_ids": ["missed_work", "reduced_paycheck"],
  "related_candidate_ids": ["candidate-remote-work"],
  "resolves_requirement_keys": ["employer_remote_permission"],
  "decision_impact": 3,
  "uncertainty": 3,
  "top_candidate_relevance": 3,
  "priority_score": 27,
  "reason": "A yes could preserve upcoming shifts without transport; this needs employer approval.",
  "status": "pending"
}
```

Do not present as though the employer was asked or approved. If the candidate ID doesn't exist, the final validator must either attach to a specific research hypothesis or omit the invalid link.

### E. Research event and response

```json
{
  "schema_version": 1,
  "status": "partial",
  "run_id": "generated-on-server",
  "simulation_fingerprint": "generated-on-server",
  "research_started_at": "2026-10-24T21:30:00-05:00",
  "research_finished_at": "2026-10-24T21:30:13-05:00",
  "priority_targets": [],
  "research_events": [
    {
      "id": "event-001",
      "type": "target_selected",
      "timestamp": "2026-10-24T21:30:01-05:00",
      "message": "Investigating commuting impact",
      "target_node_id": "commute_disrupted",
      "tool": null,
      "evidence_id": null
    }
  ],
  "evidence": [],
  "candidate_actions": [],
  "clarifying_questions": [],
  "tool_calls_used": 0,
  "cache_hits": 0,
  "warnings": ["Example shape only"]
}
```

**Event types** should cover `target_selected`, `hypothesis_generated`, `search_started`, `search_completed`, `search_failed`, `evidence_found`, `candidate_extracted`, `question_identified`, and `research_finished`. Real events must correspond to real work done. Do not make decorative fake tool-call animations or hallucinated progress messages.

**Status model:** `idle` is frontend-only; backend returns one of `completed`, `partial`, `failed`, `no_results`, or `not_configured` (and `researching` only for an actual async/streaming API workflow). If `not_configured`, explain which backend env variable is missing without exposing its value.

---

## 11. What the model can and cannot verify

| Finding | Can M3 establish it? | Required handling |
| --- | --- | --- |
| Transit itinerary displayed by provider | Yes, if data includes the relevant dates and times | Evidence-backed route detail |
| Works for Maya's actual shift and return | Only with precise origin/work/times, both legs and allowed service schedule | Unknown otherwise |
| Fare cost in provider result | Yes, when an actual amount is returned | `observed` with source; currency in USD cents |
| Mechanic listing and address | Yes, via Maps | `researched`, not appointment or service guarantee |
| Mechanic offers a payment program publicly | If an appropriate official source supports it | Terms exist; approval remains unknown |
| A landlord grants an extension | No, not from Google | Question/conditional request |
| Employer permits remote work/shift change | No | Customer/employer-confirmation blocker |
| Existing $15 subscription can be canceled before next charge | Requires particular charge/date and cancellation terms | Unknown until grounded |
| A program's personal eligibility | No, unless specific criteria are known and satisfied; still may require agency decision | Conditional; never guaranteed |
| $256 of lost take-home wages from two shifts | M2 already computes, not SerpApi | Read existing result; potential to preserve, **not** action benefit yet |
| Future bank balance after two actions | **No in M3** | M4 deterministic simulator only |

Research snippets might advertise misleading or expired programs. Prefer official sources, capture `retrieved_at`, and do not claim specific live availability when it cannot be verified.

---

## 12. Question generation — before M4 asks answers

In M3, identify and rank missing high-impact pieces of information. **Do not hardcode a static intake questionnaire.**

Question triggers:

- A plausible candidate requires a user- or employer-dependent fact (remote work, shift change, access to another vehicle).
- A publicly advertised option needs user confirmation or merchant approval (specific repair quote/payment terms).
- A promising route cannot be checked due to missing synthetic origin/destination/work times.

`Q = decision_impact × uncertainty × relevance_to_leading_candidates`, with 1–3 values per dimension and deterministic multiplication. Because M4 hasn't ranked plans yet, relevance means **to promising candidate actions** in M3; do not falsely claim top optimized plans exist.

Rules:

1. Maximum **two questions** in returned result; zero questions is allowed.
2. Prefer questions that could unlock/kill multiple candidates or resolve a major feasibility constraint.
3. Deduplicate near-equivalent questions and don't ask trivia.
4. Store `resolves_requirement_keys` for M4 to bind user answers to actions.
5. Show questions in the Explore UI as **suggested pending questions**, not a full interactive resolution loop in this build. If desired, allow a non-persistent input but don't label outcomes as re-evaluated.
6. Don't claim that asking for confirmation constitutes verification.

---

## 13. Backend and UI integration

### Backend

Suggested modules (adjust based on current code shape):

- `research_models.py`: Pydantic contracts, strict schema, validation.
- `research_graph.py`: deterministic reverse traversal and target rank.
- `research_serpapi.py`: SerpApi wrappers, normalized evidence, cache, timeouts, sanitization.
- `research_agent.py`: Gemini tool choice, bounded reasoning loop, candidate extraction, question generation.
- `research_service.py`: orchestrates snapshot + crisis simulation + ranked targets + Gemini research, fingerprint, deduplication, response.
- Extend `config.py` for `GEMINI_MODEL`/limits; extend `main.py` with the endpoint. No new database, auth system, queue stack or async worker required for a 24-hour hackathon unless a genuine need arises.

Use the existing FastAPI testing patterns and typed responses. Never return raw provider payloads containing secret-bearing URLs or unsupported private data.

### Frontend

- Extend the existing Next.js `/api/*` proxy pattern with one research endpoint. Keep Gemini and SerpApi keys backend-only.
- Replace `ResearchPreview` with a working `ResearchStage` component on **stage 3**. Preserve navigation, snapshot, graph, crisis sliders and Stage 4's honest future-only status.
- Provide a **Start Research** button, loading state, visible server-backed activity, prioritized targets, candidate cards, evidence/source links, pending question cards and a failure/partial state with a retry option.
- If using **streaming** (SSE or fetch streaming), emit actual backend events. If implementing a simple synchronous request instead, display an honest loading indicator followed by the recorded event timeline: **do not animate pretend search milestones before the API responds**.
- Candidate cards must distinguish `researched`, `hypothesis`, `conditional`, `unverified`, `blocked`; specifically show unknown cost/route/eligibility instead of placeholders disguised as actual terms.
- Research results must match the scenario fingerprint. On changed pay/quote/shifts/location, invalidate mismatched findings (or show a clear "results from earlier scenario" marker until research is rerun). Reuse cached results when inputs are unchanged and source freshness supports it.
- Keep spending/Nessie context accessible; do not overhaul layout or introduce a new design system this milestone.
- Do not show full suggested plans, calculated savings, a mitigated graph or "bills saved" claims yet.

---

## 14. Verification & acceptance tests — required

**Unit tests (offline, fake Gemini/SerpApi adapters):**

1. Reverse traversal terminates over 14 nodes / 17 edges, including cycles; returns only eligible targets and correct rooted relevance.
2. Priority scores calculate correctly, e.g. `3×3×3=27`, and ties resolve deterministically.
3. With `bills_unpaid` inactive, no false claim of an unpaid bill.
4. Income context uses the M2 `income_lost_by_payday` result; no second wage credit or mutation to Nessie records.
5. All candidate `addresses_node_ids` exist; hallucinated IDs rejected; bad URLs/dates/negative costs rejected.
6. A fake provider returning a $30 fare can yield **observed $30** with source; empty fare yields `unknown`, never auto-filled $30.
7. Missing employer approval remains unknown even if a news/blog result says remote work sometimes exists.
8. Transit that arrives after shift start **fails its arrival-time requirement**; one-way-only trip leaves return viability unknown; date/timezone conversions are checked.
9. Same provider result returned twice deduplicates candidates/evidence; repeated queries use cache and don't expend extra SerpApi calls.
10. Search result contains prompt-injection text, fake instructions, or `api_key` URLs: ignore instructions, redact secrets and continue safely.
11. Enforce six-call initial budget even if fake Gemini requests 20 queries; enforce iteration and timeout caps.
12. Empty provider results return `no_results` or `partial` rather than synthetic success.
13. Missing env credentials return `not_configured` and explain setup, without leaking values.
14. Re-running same input yields stable candidate IDs/order where determinism is possible, notwithstanding live provider freshness.
15. Scenario fingerprint changes with shifts, wage or repair amount and relevant locations; identical inputs hit cache.
16. Clarifying questions: 1–3 scale, `Q=D×U×R`, max two, correct linked requirement IDs, no irrelevant static question.
17. No call to `simulate(..., nonempty_actions)`, Nessie writes, or plan optimizer in the M3 endpoint.

**API and UI tests:**

- Backend route accepts valid request, rejects invalid request, and returns a typed `ResearchResult` including status, target ranks, events, citations/provenance, candidates, questions, tool counts and warnings.
- Frontend compiles, proxy works, research results show evidence links and uncertainty labels, retries and error messages are honest, stage-2 regression tests still pass, stage-4 placeholder remains a placeholder.
- Fake-adapter integration verifies a chained research flow: Gemini chooses web search based on initial graph target, inspects result, then chooses follow-up maps/directions; provider response is actually consumed, not an ignored mock.

**Live-provider smoke test (explicitly opt-in; do not burn quota in ordinary tests):**

1. Configure ignored `backend/.env` with `GEMINI_API_KEY` and `SERPAPI_API_KEY` (never commit, paste into docs or print values).
2. Run at least one real Gemini tool-call flow and one real SerpApi search from backend; verify call IDs, actual request counts and response origin.
3. With a carefully selected **fictional/demo** Austin location query, capture at least one valid source-backed finding or report that no viable results were returned. Do not require particular real businesses or prices to exist.
4. Try a transit search with date/arrival time; if provider availability or routing data is insufficient, report the limitation precisely.
5. Check result in browser if available; otherwise manual test script with UI screenshots/steps. Verify keys never appear in client payloads/URLs/logs.
6. Run all existing `npm test` / `npm run lint:backend` and document exact pass/failure counts and any provider request cost/count.

**Required failure demonstrations:** missing key; provider timeout/429; empty results; unsupported transit route; malformed model JSON; unverified price; changing scenario after cached research. Never say all tests passed when live providers were not exercised.

---

## 15. Implementation order (keep it manageable)

**M3-A — Contracts and graph:** Add typed `ResearchResult`, `CandidateAction`, `Evidence`, `ClarifyingQuestion`, event and priority types. Add deterministic reverse graph selection and scoring. Verify offline first.

**M3-B — SerpApi integration:** Implement search_web / search_places / find_transit, normalized evidence, redaction, strict tool budgets, retry/timeouts and local cache; verify mocked responses and a small opt-in live call.

**M3-C — Gemini orchestration:** Model receives concise simulation context, emits tool calls, inspects results, produces validated candidates/questions; stop at caps. Test multiple turns, validation, injection/no-result cases.

**M3-D — API + frontend Explore:** Add research route/proxy and activate Stage 3 with genuine research event feed, findings, source links, status and pending questions. Keep Stage 4 disabled.

**M3-E — verification & documentation:** Run all automated checks, one opt-in live call sequence if configured, manually inspect the UI, record limitations/credits and update docs.

---

## 16. Deliverables and completion report

Must produce:

- Live Gemini + SerpApi **research-only** backend, with bounded tool execution and actual external evidence where accessible.
- Deterministic backward graph target selection using real M2 data.
- Structured, evidence-linked candidate actions and linked clarifying questions.
- Frontend Explore stage with truthful activity, source links, loading and failure states.
- Repeatable offline tests, opt-in live smoke test and `docs/progress/M3.md`.
- A short section in `docs/DECISIONS.md` describing the SDK/model choice, source-verification policy, location assumptions, budget/caching choices, failure behavior and how the action contract supports M4.

### Completion-report template

```text
Milestone: M3 — Research and action discovery
Implementation: [files/modules changed]
Reference financial result: [snapshot provenance, core crisis metrics]
Provider mode: [live or mocked]
Gemini model: [name, configured, verified/unverified]
SerpApi engines actually called: [list]
Provider tool requests / cache hits: [numbers]
Top target scores: [node IDs, scores, explanatory rationale]
Candidate actions: [counts by researched/hypothesis/conditional]
Questions: [count; why selected]
Tests: [exact results]
Manual verification: [what was actually viewed]
Costs/quota: [known actual/estimated/unknown]
Known blockers: [explicit]
Out-of-scope work: [confirm no optimizer, no nonempty actions, no real financial changes]
```

### Stop condition

**Stop after useful, source-grounded potential interventions and pending questions appear in Explore.** Do not show a user that their bills are prevented yet. The next milestone (M4) will bind user answers to requirements, apply dated action effects to the existing simulator, enumerate combinations (8 actions → 92 up-to-three-action plans), enforce feasibility, rank plans, and update the graph and cash-flow future.

---

## 17. References

- HackTX repository: https://github.com/MMehta45/hacktx26
- HackGT build prompt reference: https://github.com/AlanRoybal/hackgt/blob/main/prompts/01-claude-code-build.md
- Product blueprint in repo root: `00-PROJECT-BLUEPRINT.md`
- Current M2 contract: `backend/app/simulation_models.py`, `docs/progress/M2.md`
- Gemini function-calling guide: https://ai.google.dev/gemini-api/docs/function-calling
- Gemini current SDK guide: https://ai.google.dev/gemini-api/docs/get-started
- SerpApi general search: https://serpapi.com/search-api
- SerpApi Google Maps: https://serpapi.com/google-maps-api
- SerpApi Google Maps Directions: https://serpapi.com/google-maps-directions-api

**Security:** Do not paste previously shared credentials into Markdown, prompts, commits, debug traces or frontend variables. If any key has been exposed, rotate it and configure the replacement only in ignored backend `.env`.
