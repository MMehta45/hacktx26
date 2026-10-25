One Bad Tuesday --- Build 04
==========================

Interactive Recovery, Agentic Research Expansion & Financial Plan Optimization
------------------------------------------------------------------------------

**Repository:** `MMehta45/hacktx26`\
**Milestone:** M4\
**Status:** Implementation specification\
**Primary objective:** Turn researched intervention possibilities into interactive, financially tested, evidence-backed recovery plans.

* * * * *

0\. Product objective
=====================

One Bad Tuesday helps a financially vulnerable person understand how one emergency can create a cascade of financial consequences, then identify practical ways to interrupt that cascade.

The existing system already:

-   Connects to a fictional Capital One Nessie customer and banking history.

-   Normalizes financial data and upcoming bills.

-   Simulates the untreated consequences of a car breakdown.

-   Models the cascade through a consequence graph.

-   Uses Gemini to propose intervention hypotheses.

-   Uses SerpApi to investigate real services, transportation, mechanics, and assistance programs.

-   Generates conditional candidate actions and high-impact questions.

-   Preserves evidence and candidates when Gemini extraction fails.

The updated simulator also uses Friday weekly payroll with a one-week lag and derives shift losses and repair timing from the financial timeline. Verify the exact implementation before modifying it.

**Build 04 must complete the loop.**

The user should be able to answer questions, see which options become more or less plausible, compare multiple recovery strategies, and understand their effects on income, repair timing, cash balances, and unpaid bills.

The product should answer:

> What could Maya do now to prevent one car breakdown from becoming a month-long financial crisis, what would each option require, and what changes financially if it succeeds?

This is not an AI chatbot that merely offers generic advice.

It is a **constraint-aware recovery planning system backed by deterministic financial simulation and verifiable external research.**

* * * * *

1\. Non-negotiable principles
=============================

1.1 Possibility is not approval
-------------------------------

Distinguish these concepts explicitly:

1.  **Suggested:** An idea the system thinks might help.

2.  **User-reported possible:** Maya thinks the option could be available.

3.  **Researched:** Public information supports some relevant facts.

4.  **Pending confirmation:** An employer, provider, landlord, mechanic, or other party must agree.

5.  **Confirmed:** The necessary condition has actually been established.

6.  **Rejected or unavailable:** The option cannot currently be used.

A yes/no answer is not automatically definitive.

Examples:

-   "Could you potentially work remotely?" → Yes means remote work deserves consideration, not that her manager has approved it.

-   "Has your manager approved remote work for Monday and Tuesday?" → Yes can establish approval for those dates, subject to any remaining equipment constraints.

-   "Would your landlord consider a rent extension?" → Yes does not mean a new due date has been agreed.

-   "Can you take the bus?" → Yes establishes personal willingness or ability, not schedule feasibility.

-   "Is this mechanic affordable?" → Reviews cannot establish Maya's actual repair quote.

A plan must distinguish what **can be simulated as a hypothetical outcome** from what **is confirmed and usable**.

Do not promote a tentative answer into verified plan feasibility.

1.2 Gemini reasons; Python calculates
-------------------------------------

Gemini can:

-   Interpret user answers.

-   Propose interventions.

-   Select research directions.

-   Identify missing information.

-   Draft outreach.

-   Explain tradeoffs.

-   Suggest combinations worth evaluating.

Gemini must not:

-   Invent a repair price.

-   Decide a route is feasible without itinerary evidence.

-   Declare an employer approval.

-   Generate arbitrary dollar savings.

-   Assign bill funding outcomes.

-   Produce final recovery-plan ranking without simulator results.

Money, dates, eligibility rules, combination constraints, and financial outcomes should be validated or computed in backend code.

1.3 Use the latest financial simulator
--------------------------------------

Build 03.5 is changing the central simulation model.

Before implementation:

1.  Read the latest local working tree, including uncommitted changes.

2.  Verify the derived-shift and repair-affordability migration.

3.  Inspect the new payroll, repair, and bill-allocation contracts.

4.  Treat the implemented simulator as the authoritative engine for financial consequences.

5.  Do not reintroduce the old two-missed-shift default.

6.  Do not calculate financial outcomes independently inside the research agent or frontend.

The planner should evaluate interventions through the same deterministic engine that produces the untreated crisis.

1.4 Never claim outcomes that are conditional
---------------------------------------------

If a plan relies on unapproved remote work, show:

**If the employer approves this option: projected financial outcome X.**

Separately show:

**Approval status: pending.**

The original untreated crisis remains the reference forecast until a conditional assumption is confirmed.

Do not mix hypothetical improvements into the actual baseline.

* * * * *

2\. Overall architecture
========================

Target flow:

```
Nessie / Fixture Financial Snapshot
               |
               v
Derived Crisis Simulation (Build 03.5)
               |
               v
Consequence Graph + Financial Vulnerabilities
               |
               v
Gemini Hypotheses + SerpApi Evidence (Build 03)
               |
               v
Candidate Actions + Open Questions
               |
               v
INTERACTIVE RECOVERY SESSION
     |
     +-- User answers questions
     |
     +-- Requirement/approval status changes
     |
     +-- Targeted research if necessary
     |
     +-- Generate or update candidate actions
     |
     v
FEASIBILITY & EFFECT COMPILER
     |
     +-- Eligibility and requirements
     +-- Timing and deadlines
     +-- Action dependencies
     +-- Cost certainty
     +-- Per-shift effects
     +-- Bill and cash effects
     |
     v
COMBINATION GENERATOR
     |
     v
DETERMINISTIC SCENARIO SIMULATOR
     |
     v
PLAN RANKING + EXPLANATION
     |
     v
MULTIPLE RECOVERY PLANS
     |
     +-- Financial outcome
     +-- Unresolved dependencies
     +-- Sources/resources
     +-- Outreach drafts
     +-- Next actions
```

Keep three responsibilities separate:

**Research layer:** What options exist, and what evidence supports them?

**Feasibility layer:** Under which conditions could each option work?

**Simulation layer:** What happens financially if those conditions are satisfied?

Avoid implementing everything as one long Gemini prompt.

* * * * *

3\. Interactive question-and-answer system
==========================================

3.1 Convert existing questions into real controls
-------------------------------------------------

Build 03 already returns `ClarifyingQuestion` objects with:

-   ID

-   Question

-   Answer type

-   Priority

-   Related candidate IDs

-   Requirements resolved

-   Relevant graph nodes

Extend them to support submitted answers and follow-up decisions.

Support:

-   Yes/no

-   Multiple choice

-   Numeric answer

-   Date or date range

-   Free text

Each response should be stored in a recovery session, not just local visual component state.

Users should be able to revise previous answers.

When an answer changes, invalidate only downstream conclusions that depend on it.

3.2 Distinguish answer interpretation from confirmation
-------------------------------------------------------

Create a structured answer-resolution layer.

Example:

**Question:** Could you potentially work remotely while your car is unavailable?

User answers: Yes.

Interpretation:

```
{
  "remote_work_personally_possible": true,
  "employer_approval": "unknown",
  "equipment_available": "unknown",
  "eligible_shift_dates": "unconfirmed"
}
```

Possible response:

"Remote work could preserve your shifts without transportation. Would you like to request temporary approval?"

The agent may now draft an email.

However, the employer approval requirement is still unresolved.

Another example:

**Question:** Has your manager approved remote work for October 26 and 27?

User answers: Yes.

Now the system can mark approval as user-reported confirmed for those dates, while still checking any necessary equipment or access conditions.

Model user-reported confirmation as distinct from externally verified approval. Do not pretend the application contacted the employer.

3.3 Requirement status model
----------------------------

Use a richer requirement system than a single boolean.

Suggested statuses:

-   `unknown`

-   `possible`

-   `pending_external_approval`

-   `user_reported_confirmed`

-   `externally_verified`

-   `rejected`

-   `expired`

Track:

-   Requirement ID

-   Associated candidate IDs

-   Required condition

-   Current status

-   Source of status

-   Answer or evidence establishing it

-   Effective dates

-   Last updated timestamp

Requirements should be reusable across candidates.

For example, confirmation that Maya can physically ride public transportation should not have to be requested separately for every bus itinerary.

3.4 Questions should be generated based on plan impact
------------------------------------------------------

The system should not mechanically ask every available question.

Use:

`QuestionPriority = DecisionImpact × Uncertainty × RelevanceToPromisingPlans`

Each component scores from 1--3.

Build 03 currently uses relevance to leading candidate actions because no evaluated plans exist yet.

Build 04 should use actual simulated plans whenever available.

A useful question is one whose answer could meaningfully change the best recovery decision.

For example:

-   Can remote work preserve $640 of weekly take-home?

-   Would a rent extension prevent an otherwise uncovered essential obligation?

-   Can Maya use an alternate commute for three affected shifts?

-   Can the employer approve a shift-time adjustment?

-   Does Maya have an actual mechanic estimate?

Ask one or two high-value questions at a time.

After answering, reevaluate priorities rather than displaying a predetermined questionnaire.

3.5 Support conditional follow-up questions
-------------------------------------------

Questions can depend on earlier answers.

Example:

1.  Could you potentially work remotely?

2.  If yes: Do you have access to a work computer and required systems?

3.  If yes: Has your manager already approved it?

4.  If not: Offer to draft an approval request.

Do not show irrelevant questions.

If Maya says remote work is impossible, stop pursuing that path unless new evidence changes the situation.

3.6 Persistent recovery session
-------------------------------

Create a structured session object containing:

-   Session ID

-   Scenario fingerprint

-   Research run ID

-   Current answers

-   Requirement states

-   Candidate actions

-   Confirmed/possible/rejected constraints

-   Evaluated plan IDs

-   Last simulation results

-   Relevant evidence IDs

-   Revision/version counter

For the hackathon, lightweight server-side session storage is acceptable. A durable database is optional, not required.

Do not store sensitive financial information in public client-visible logs.

Refresh should not erase the session unexpectedly.

Changing the base scenario should trigger clear reconciliation or reset behavior.

* * * * *

4\. Outreach and action assistance
==================================

The user should be able to act on recommendations.

But Build 04 must distinguish **help preparing an action** from **actually executing it**.

Support useful draft generation when applicable:

-   Email requesting temporary remote work

-   Message requesting a shift swap or adjustment

-   Request for a rent extension or payment arrangement

-   Request for an insurance payment extension

-   Message asking a mechanic for a written estimate

These drafts should be tailored to the fictional scenario and the actual requested dates.

Example:

Maya may receive a ready-to-copy request explaining that her vehicle is temporarily unavailable and asking permission to work remotely on specific affected days.

The draft should not falsely state approval, invent promises, or disclose unnecessary financial details.

For now:

-   Drafting is supported.

-   Copying is supported.

-   Opening a source or contact page is supported.

-   Sending emails, submitting applications, making payments, and booking services are outside scope.

Track an action as `draft_prepared`, not `approved` or `completed`.

Never change financial projections simply because a draft was generated.

* * * * *

5\. Expand the research engine
==============================

Build 03's hypothesis-driven research is a foundation, but its scope and depth are constrained.

Build 04 should support additional evidence gathering when it affects a proposed plan.

5.1 Expand mechanisms without hardcoding an exhaustive solution list
--------------------------------------------------------------------

Potential interventions include:

**Income preservation**

-   Remote work

-   Shift swaps

-   Makeup hours

-   Modified shift schedules

-   Temporary workplace reassignment

-   Alternative paid work, where practical

**Transportation**

-   Fixed-route public transit

-   Walking

-   Biking

-   Carpooling

-   Borrowing a vehicle

-   Employer-provided transport

-   Rideshare, if the cost is justified

-   Multimodal trips

**Repair affordability**

-   Different mechanic estimates

-   Lower-cost repair options

-   Repair financing, clearly identified as debt

-   Delayed repair arrangements

-   Community automotive assistance, if verified

**Bill and housing flexibility**

-   Rent extensions

-   Partial-payment arrangements

-   Utility hardship programs

-   Insurance due-date extensions

-   Fee waivers

-   Assistance organizations

-   Emergency grants, if genuinely available

**Cash preservation**

-   Delay discretionary purchases

-   Pause cancellable subscriptions

-   Defer lower-priority obligations where allowed

-   Avoid expensive borrowing when alternatives exist

These are starting categories, not the only allowed hypotheses.

Gemini should still be able to introduce a new, relevant option.

5.2 Research breadth versus depth
---------------------------------

Do not search every category exhaustively on every pass.

Use two stages:

### Discovery

Generate a reasonably diverse initial set of hypotheses with bounded research.

### Targeted investigation

Once the user answers questions or a potential plan looks promising, spend additional searches resolving the specific evidence needed for that plan.

Examples:

-   Investigate bus fare because transit appears financially promising.

-   Retrieve a mechanic's reviews because lower repair pricing might change the repair date.

-   Check a program's eligibility and whether applications are currently open.

-   Find an actual policy or provider contact page for a bill extension.

-   Check another public transit departure after the initial result proves late.

The agent should explain why it chose to perform the follow-up search.

5.3 Adaptive research budget
----------------------------

Retain cost controls, but separate budgets by purpose.

Suggested defaults:

-   Initial discovery: preserve the existing approximate six-request budget.

-   Explicit research refresh: preserve the approximate eight-request budget.

-   Targeted plan investigation: separate configurable budget, approximately four to six additional requests per user-triggered round.

-   Set an overall maximum per recovery session.

-   Cache identical queries and reuse evidence.

-   Deduplicate repeated resources.

-   Avoid repeatedly researching impossible or rejected options.

Gemini may propose searches, but the backend enforces the budget.

Record actual provider calls, cache hits, skipped searches, and failures.

5.4 Evidence freshness and specificity
--------------------------------------

For every external fact track:

-   Source URL

-   Retrieval timestamp

-   What the source actually supports

-   Geographic relevance

-   Time relevance

-   Eligibility or approval requirements

-   Known price

-   Price certainty

-   Limitations

A resource listing does not establish that Maya qualifies or can receive money before a bill is due.

Distinguish evergreen information from time-sensitive availability.

Only count an assistance amount as a plan cash inflow if the amount, timing, and necessary eligibility/approval assumptions are explicitly satisfied in that conditional scenario.

* * * * *

6\. Detailed transit research
=============================

Transportation should become a fully structured recovery action rather than a generic link.

6.1 Required itinerary fields
-----------------------------

For each trip, attempt to capture:

-   Shift date

-   Trip direction

-   Origin and destination

-   Planned departure time

-   Arrival time

-   Total travel duration

-   Route and line numbers

-   Boarding stop

-   Alighting stop

-   Transfers

-   Walking distance

-   Walking duration

-   Fare

-   Fare source and certainty

-   Relevant route link

-   Provider source ID

When available, preserve individual legs:

```
Walk → Bus 5 → Walk
```

Each leg should contain its own timing and relevant stop details.

If the provider does not return enough information, mark the missing fields unknown.

Do not fabricate departure times, fares, stops, or transfer details.

6.2 Evaluate transport at the shift level
-----------------------------------------

A route is useful only if it can help Maya attend a particular scheduled shift.

For each shift, evaluate:

1.  Does the outbound trip reach work before the shift starts?

2.  Does the return trip depart after the shift ends?

3.  Are both journeys supported for the relevant date?

4.  Is the cost known or reasonably supported?

5.  Are there unresolved personal constraints?

6.  Is the evidence sufficient to call the itinerary viable?

Return one of:

-   `verified_route_feasible`

-   `conditionally_feasible`

-   `route_infeasible`

-   `insufficient_schedule_evidence`

A single late itinerary does not prove all possible departures are unavailable.

If an arrival-by query returns a late journey, investigate an earlier departure or alternative where budget permits.

6.3 Transit financial effects
-----------------------------

For a verified or explicitly assumed usable round trip:

`TransportationCost = outbound fare + return fare`

Account for valid fare products or transfer rules when supported. Do not double-charge an integrated or daily-capped fare.

If that trip preserves a scheduled shift:

`IncrementalTakeHomePreserved = estimated take-home wages for that shift`

Then evaluate its dated financial effects.

Example, purely illustrative:

-   Shift take-home: $128

-   Round-trip transit: $5

-   Net incremental benefit before other effects: $123

However, do not simply add $123 to checking immediately.

The transit cost occurs on the travel date; recovered wages arrive on the appropriate Friday payroll date.

The repaired financial timeline may then change the future repair date, which can restore other shifts.

6.4 Transit versus alternatives
-------------------------------

The planner should be able to compare:

-   Bus for five days

-   Bus for two days, then repair

-   Remote work for three days and bus for two

-   Shift adjustment plus an otherwise late bus itinerary

-   Rideshare for a single critical shift, if a supported fare estimate exists

Transport actions must identify the exact shifts they protect.

No generic action should preserve an entire week unless coverage is established for that week.

* * * * *

7\. Mechanic review research and recommendations
================================================

The present mechanic pipeline retrieves listings and can fetch Google Maps reviews.

Improve its selection and ranking.

7.1 Positive affordability evidence required for recommendation
---------------------------------------------------------------

The product should only surface a mechanic as a **recommended affordable repair shop** when actual retrieved reviews provide credible positive price-related evidence.

Examples of relevant language:

-   Affordable

-   Reasonably priced

-   Fair price

-   Transparent estimate

-   Honest pricing

-   Good value

A high star rating alone is not evidence of affordability.

A listing with no positive pricing evidence may remain in the underlying research record, but should not be presented as a price-based recommendation.

If no shop meets the evidence threshold, show:

**"We couldn't verify an affordable repair shop from the available reviews."**

The system may then suggest requesting written quotes through a generic next step, but should not endorse an unsupported shop as inexpensive.

7.2 Correct the affordability scoring
-------------------------------------

The current price-evidence heuristic uses the volume of positive and negative price-language matches. That should not be interpreted as affordability.

Separate:

-   Positive price sentiment

-   Negative price sentiment

-   Transparency

-   Review sample size and confidence

-   General business reputation

-   Geographic convenience

Suggested score:

`AffordabilityScore = 0.45 × PositivePriceSignal + 0.25 × Transparency + 0.20 × Reputation + 0.10 × Convenience - NegativePricePenalty`

This is a contact-prioritization heuristic, not an estimated repair quote.

Use a confidence penalty for tiny or ambiguous review samples.

Avoid keyword-only false positives where possible. For example, "not affordable" is negative despite containing "affordable."

For sentiment classification, deterministic matching with negation handling is acceptable; a bounded Gemini classification step is optional.

7.3 Structured review evidence
------------------------------

Store:

-   Shop and provider identifier

-   Business address

-   Overall rating

-   Actual sampled review count

-   Positive price snippets

-   Negative price snippets

-   Transparency snippets

-   Affordability assessment

-   Confidence

-   Evidence URL

Do not confuse the listing's total review count with the number of reviews retrieved and analyzed.

Never invent a review excerpt.

7.4 Impact on simulation
------------------------

A review saying a shop is reasonably priced does not justify changing the $400 repair quote.

Only a confirmed or explicitly conditional alternative repair quote can affect the financial simulation.

Possible action states:

-   Contact an affordable-looking shop --- research-supported, no financial savings yet.

-   Shop provides a user-reported $300 written quote --- conditional/confirmed quote input with provenance.

-   Maya confirms an available appointment and repair timing --- allows evaluation of an alternative repair scenario.

If the lower price is hypothetical rather than quoted, show it strictly as a what-if sensitivity analysis, not a recommended saving.

* * * * *

8\. Recovery action effect model
================================

Existing `CandidateAction` objects contain useful hints but not enough information to drive full financial simulations.

Introduce a typed action-effect contract.

Do not rely on Gemini-generated free-text descriptions to apply money.

8.1 Supported action effects
----------------------------

Initial effect types should cover:

### Preserve scheduled shift

-   Specific shift IDs/dates

-   Required commute or remote-work conditions

-   Scheduled work hours preserved

-   Associated payroll period

### Incur transportation expense

-   Amount

-   Date

-   Which route/shift it supports

-   Evidence and cost certainty

### Change bill due date

-   Obligation ID

-   Original due date

-   New due date

-   Approval requirement

-   Fee, if verified

### Reduce or waive a bill

-   Obligation ID

-   Reduction amount

-   Approval or eligibility requirement

-   Effective date

### Receive assistance

-   Amount

-   Arrival date

-   Eligibility and approval requirements

-   Whether it must go directly to a specific bill

### Alternative repair quote

-   New quote amount

-   Source/confirmation status

-   Earliest appointment date

-   Repair completion assumption or confirmed timing

### Borrow funds

-   Principal

-   Availability date

-   Repayment schedule

-   Verified or explicitly assumed cost of borrowing

### Make up missed hours

-   Makeup work date

-   Hours

-   Associated payroll date

-   Employer approval

-   No overlap with existing scheduled paid work

If amounts or timing are unknown, the effect cannot be represented as a quantified guaranteed benefit.

8.2 Action schema
-----------------

Each action effect should have:

-   Stable action ID

-   Type

-   Effective dates

-   Affected entity IDs

-   Amount fields as integer cents

-   Requirement IDs

-   Evidence IDs

-   Certainty/provenance

-   Compatibility constraints

-   Conflict/dependency identifiers

Keep research candidates separate from executable effects.

A candidate may have several possible effects, some still unresolved.

8.3 No automatic action execution
---------------------------------

All simulations operate on hypothetical copies of the financial state.

Never mutate historical Nessie records.

Never create actual deposits, loans, bill payments, or repair purchases.

* * * * *

9\. Financial plan optimizer
============================

This is the core functionality of Build 04.

9.1 Generate action combinations
--------------------------------

From the currently relevant candidate actions, generate possible plans with one, two, or three distinct actions.

For eight eligible candidates:

`C(8,1) + C(8,2) + C(8,3) = 92`

This is a baseline combinatorial approach, not a requirement to evaluate every arbitrary pairing.

Filter combinations using:

-   Known impossibilities

-   Incompatible timing

-   Mutually exclusive actions

-   Duplicate financial effects

-   Unavailable services

-   Insufficient evidence for quantified effects

-   Required action dependencies

Because actions may cover multiple shifts, compare their combined coverage rather than naively summing individually estimated benefits.

9.2 Conditional scenarios
-------------------------

Separate plan feasibility from scenario financial performance.

A conditional plan might include:

-   Remote work for three shifts if approved

-   Transit for two shifts if the route is usable

-   Rent extension if the landlord agrees

The simulator should calculate what happens **under those explicit assumptions**.

The plan should also report the dependencies that must be resolved.

Suggested plan feasibility states:

-   `ready_with_confirmed_conditions`

-   `conditional_pending_approval`

-   `conditional_pending_information`

-   `blocked`

If the user says remote work is possible but has no approval, the plan remains conditional.

Avoid presenting a single mixed "projected balance" that silently assumes every uncertain action succeeds.

9.3 Rerun the full simulator
----------------------------

**Do not calculate plan impact by simply adding estimated savings to the untreated ending balance.**

Apply action effects to the derived crisis simulator and rerun the dated employment, payroll, repair affordability, and bill-allocation timeline.

Why:

-   Transit can preserve Monday's shift.

-   That increases the following week's paycheck.

-   The additional income may accelerate repair affordability.

-   Earlier repair may restore other shifts.

-   Those restored shifts create further paycheck changes.

-   The result may prevent a rent or insurance shortfall.

These consequences must be computed chronologically.

9.4 Avoid double counting
-------------------------

Examples:

-   Bus and remote work both protecting Monday cannot recover Monday's wages twice.

-   Working remotely restores wages; it does not create a second paycheck.

-   A deferred rent bill still exists and must be accounted for at its new due date.

-   An assistance payment assigned to rent cannot also be treated as unrestricted cash unless permitted.

-   An alternative repair quote replaces the original quote; it is not an additional repair expense.

-   A borrowed amount is an inflow accompanied by future repayment obligations.

-   A shift made up later should not also be counted as worked on its original date.

Use stable ledger IDs and shift IDs to enforce this.

9.5 Preserve the repair-affordability policy
--------------------------------------------

The updated baseline uses a bill-protective repair funding rule.

Every recovery plan should use the same rule unless a candidate explicitly changes an obligation or available funding.

An approved rent extension may free money previously reserved for an imminent essential bill.

A preserved paycheck may make the repair affordable earlier.

A less expensive confirmed repair quote may change the repair payment date.

These changes must be recomputed rather than manually patched.

9.6 Financial outcomes per plan
-------------------------------

Every simulated plan should return:

-   Original untouched baseline fingerprint

-   Actions applied

-   Conditional assumptions

-   Requirement statuses

-   Projected worked/missed shifts

-   Shift dates recovered

-   Income preserved by payday

-   Transportation and other new expenses

-   Repair funding date and restoration date

-   Cash-flow series

-   Minimum projected cash balance

-   Peak funding gap

-   Unpaid essentials

-   Bill-by-bill outcomes

-   Additional borrowing and future repayments

-   Graph node status differences

-   Warnings and unresolved dependencies

Include comparison deltas against the untreated crisis.

9.7 Plan ranking
----------------

Use a transparent, lexicographic ranking rather than a mysterious single AI score.

Suggested order:

1.  **Feasibility:** confirmed/ready plans before plans relying on unresolved approvals, while still displaying compelling conditional plans separately.

2.  **Essential bills protected:** minimize essential unpaid dollars, then the number of missed essential obligations.

3.  **Worst funding gap:** minimize peak cash shortfall.

4.  **Income and repair recovery:** maximize protected shifts and improve restoration timing where relevant.

5.  **Incremental cost:** minimize transportation costs, fees, and future debt obligations.

6.  **Complexity:** prefer fewer dependencies, fewer external approvals, and fewer required actions.

Within feasibility groups, compare plans using the financial outcomes.

Do not let a low-complexity plan outrank one that substantially better protects essential bills merely because it is simpler.

Preserve the full ranking rationale in the response.

9.8 Present diverse plans
-------------------------

Do not simply show the top three near-identical combinations.

Return up to three meaningfully different strategies where available.

Examples:

-   **Keep income flowing:** remote work plus limited transit

-   **Stabilize essential bills:** negotiated due-date extension plus targeted assistance

-   **Restore transportation sooner:** alternative repair financing or verified cheaper quote

These are illustrative, not hardcoded plan names or guaranteed solutions.

Use diversity-aware selection after financial ranking, without hiding a materially superior plan.

If fewer than three credible options exist, show fewer.

If every plan is conditional, communicate that clearly.

* * * * *

10\. Plan presentation and user experience
==========================================

Build 04 needs usable UI, but not the final visual overhaul.

10.1 Question step
------------------

Show:

-   Highest-impact question

-   Why it matters

-   Answer control

-   Immediate interpretation

-   Next recommended action or follow-up question

Avoid long forms.

10.2 Plan comparison
--------------------

For each plan show:

-   Plan name and strategy

-   Readiness/conditional status

-   Actions involved

-   Estimated essential bills protected

-   Income preserved

-   Repair date change

-   Extra costs

-   Remaining funding gap

-   Unresolved approvals

-   Source links

Make the difference between conditional and confirmed outcomes visually obvious.

10.3 Financial comparison
-------------------------

Show untreated vs selected plan:

-   Cash-flow timeline

-   Bill outcomes

-   Lost workdays

-   Repair timing

-   Critical downstream graph nodes

The user should be able to understand *why* the plan works.

For example:

"Working remotely for three approved days protects those wages. The additional paycheck then allows the repair to be funded earlier, which restores two further shifts."

This explanation must be derived from simulator results.

10.4 Sources and resources in the final plan
--------------------------------------------

**Source links belong in the final plans, not just the research stage.**

For relevant actions, display:

-   Transportation route links

-   Transit schedule and fare evidence

-   Mechanic website and positive affordability review evidence

-   Official financial assistance resources

-   Relevant provider policy pages

-   Contact or application pages

Distinguish an informational resource from an approved benefit.

Do not display irrelevant source dumps.

10.5 Next steps
---------------

Every plan should provide an actionable sequence.

For example:

1.  Ask your manager to approve remote work for specified shifts.

2.  Confirm equipment and access.

3.  Check the proposed bus itinerary for the remaining workday.

4.  Request a written repair estimate.

5.  Recalculate after approval or a new quote.

Provide generated outreach drafts where useful.

The user can update confirmation states and recompute the plan.

No external execution is required.

* * * * *

11\. Replanning after new answers
=================================

Recovery planning should be iterative.

Examples:

### Remote work denied

-   Mark employer approval as rejected.

-   Remove remote work from feasible plans.

-   Retain existing research evidence.

-   Evaluate alternate commutes and schedule adjustments.

-   Rerank plans.

### Landlord grants extension

-   Record the agreed new due date.

-   Recalculate bill allocation.

-   Reevaluate repair affordability.

-   Update financial comparisons.

### Mechanic provides new quote

-   Record amount and source.

-   Reevaluate alternative repair strategy.

-   Update the expected repair date.

-   Recalculate projected shifts and payroll.

### Transit evidence changes

-   Update affected itinerary status.

-   Recompute only plans using that itinerary.

-   Preserve unaffected candidate evidence.

Use session versions and dependency tracking to avoid stale results.

Do not rerun all SerpApi searches whenever the user clicks an answer.

* * * * *

12\. API and backend structure
==============================

Prefer extending the existing FastAPI application.

Suggested endpoint design:

### Recovery session creation

`POST /api/recovery/sessions`

Input: Base scenario and existing research identifiers.

Output: Recovery session, initial questions, candidates, and current plan evaluation state.

### Submit answers

`POST /api/recovery/sessions/{id}/answers`

Input: Question ID, typed answer, optional clarification.

Output: Updated requirement states, next questions, invalidated plan IDs, and whether targeted research is needed.

### Research follow-up

`POST /api/recovery/sessions/{id}/research`

Input: Specific candidate IDs or unresolved evidence needs.

Output: New evidence, updated candidates, research activity, and costs/call counts.

### Evaluate plans

`POST /api/recovery/sessions/{id}/evaluate`

Input: Current session version and optional strategy constraints.

Output: Baseline, evaluated combinations, ranked plans, conditional dependencies, and explanation data.

### Confirm or reject an action

`POST /api/recovery/sessions/{id}/requirements`

Input: Requirement ID, updated status, source, and effective dates.

Output: Updated eligibility and recomputed impacted plans.

Endpoint names are suggestions; fit the implementation to the existing routing structure.

Keep Pydantic and TypeScript models synchronized.

Use explicit schema versions.

* * * * *

13\. Implementation stages
==========================

This is a large milestone. Implement in ordered checkpoints and verify each before proceeding.

M4.A --- Recovery contracts and sessions
--------------------------------------

-   Define session, answer, requirement, effect, and plan models.

-   Extend existing candidate/question references.

-   Implement session persistence.

-   Implement typed answer handling.

-   Add tests.

**Checkpoint:** Answers update requirements without assuming external approval.

M4.B --- Action effects and deterministic simulation
--------------------------------------------------

-   Add executable effect types.

-   Integrate effects with the latest derived crisis simulator.

-   Support preserved shifts, expense events, bill timing, alternative repair quotes, and other supported effects.

-   Implement provenance and deduplication.

-   Add mathematical regression tests.

**Checkpoint:** A manually constructed action changes the correct payroll and downstream consequences, without any Gemini involvement.

M4.C --- Combination generation and ranking
-----------------------------------------

-   Generate candidate combinations.

-   Prune impossible combinations.

-   Simulate each valid conditional scenario.

-   Rank plans transparently.

-   Return diverse strategies.

-   Add deterministic tests.

**Checkpoint:** The same inputs always produce the same ranked plans.

M4.D --- Enhanced SerpApi research
--------------------------------

-   Implement detailed transit itineraries and fares.

-   Investigate route timing edge cases.

-   Improve mechanic review evidence and affordability scoring.

-   Expand targeted searches.

-   Add adaptive research allocation and caching.

-   Test against mocked provider payloads.

**Checkpoint:** Recommendations cite actual evidence, and missing prices remain unknown.

M4.E --- Interactive agent orchestration
--------------------------------------

-   Ask high-impact questions.

-   Interpret answers into requirements.

-   Generate follow-up questions.

-   Perform selective research.

-   Offer outreach drafts.

-   Rerun affected simulations.

-   Preserve session state.

**Checkpoint:** A changed user answer materially changes plan feasibility and ranking.

M4.F --- Plan-facing UI
---------------------

-   Add question controls.

-   Add multiple plan comparisons.

-   Add detailed financial differences.

-   Add linked sources/resources.

-   Add action preparation and status updates.

-   Use the existing graph for before/after comparison.

**Checkpoint:** A judge can follow the full recovery flow without reading raw JSON.

* * * * *

14\. Demo scenarios and acceptance tests
========================================

Test the complete system using deterministic financial fixtures and mocked research evidence.

### Scenario A --- Remote work possible but not approved

Maya says remote work is possible.

Expected:

-   Drafting an email is offered.

-   The requirement remains pending approval.

-   Remote-work benefits can be simulated conditionally.

-   Untreated finances remain unchanged.

-   No plan describes approval as guaranteed.

### Scenario B --- Remote work approved for specific shifts

Maya confirms employer approval for certain dates.

Expected:

-   Those specific shifts become recoverable if remaining requirements are satisfied.

-   Lost wages are restored to the appropriate Friday payroll.

-   Repair affordability recalculates.

-   Later shifts may be indirectly restored.

### Scenario C --- Transit financially valuable

A provider-backed round trip exists with sufficient timing and fare evidence.

Expected:

-   The route identifies exact shifts.

-   Transport cost occurs on travel dates.

-   Preserved wages arrive on payroll dates.

-   Net financial impact is computed through the simulator.

-   Unknown schedule evidence does not become verified feasibility.

### Scenario D --- Transit route arrives too late

Expected:

-   This itinerary is rejected for the original shift timing.

-   Earlier route research or shift adjustment may be considered.

-   One late route does not automatically invalidate every transit option.

### Scenario E --- Landlord extension

A specific extension is confirmed.

Expected:

-   The bill obligation moves to the new date.

-   The debt is not erased.

-   Repair affordability and cash flow are recomputed.

-   Any extension fee is included only if supported.

### Scenario F --- Positive mechanic reviews, no quote

Expected:

-   Shop can be shortlisted as promising.

-   Actual review evidence is displayed.

-   No arbitrary repair savings are applied.

### Scenario G --- No positive mechanic reviews

Expected:

-   No mechanic is endorsed as affordable.

-   The system explains the evidence gap.

-   The existing repair quote remains unchanged.

### Scenario H --- Two actions preserve the same shift

Expected:

-   Wages are recovered once.

-   Necessary distinct costs are accounted for.

-   Duplicate effects are detected.

### Scenario I --- Multiple complementary actions

Remote work, transit, and a bill extension together materially improve the crisis.

Expected:

-   Financial effects propagate through payroll and repair timing.

-   Multiple graph nodes change.

-   The combination may outperform individual actions.

-   Ranking is deterministic.

### Scenario J --- All options uncertain

Expected:

-   Conditional plans can still be presented.

-   Unresolved approvals are explicit.

-   No hypothetical plan is presented as already secured.

-   The original untreated forecast remains available.

### Scenario K --- Research fails

Gemini or SerpApi is unavailable.

Expected:

-   Existing grounded candidates and session answers remain intact.

-   Deterministic simulator still runs.

-   No invented evidence or approvals.

-   The failure is explained without leaking API keys.

* * * * *

15\. Mathematical invariants
============================

Enforce these throughout the project.

**Payroll**

Recovered wages must be attributed to the correct work period and payday.

**No duplicate shift recovery**

A shift is either worked or missed in a given plan simulation, never both.

**No invented financing**

Loan principal and assistance must not appear without an explicit, properly labeled effect and its conditions.

**No free deferral**

Changing a bill's due date must preserve its obligation unless a separate valid reduction exists.

**No double repair**

An alternate repair quote replaces the original quote for that plan rather than creating an additional payment.

**No implicit approvals**

User-reported possibility never becomes employer or provider approval automatically.

**No unsupported cost**

Unknown transit fare or repair pricing must not be silently treated as zero.

**Chronological causality**

An income change cannot fund an earlier expense, and restoring transportation cannot retroactively recover past shifts.

**Historical immutability**

Nessie history must remain unchanged across every plan evaluation.

**Reproducibility**

The same snapshot, scenario, answers, requirements, and evidence must produce the same financial outcome.

* * * * *

16\. Test and reliability requirements
======================================

Include:

-   Backend unit tests for each effect type.

-   Payroll-date and shift-level tests.

-   Bill-allocation tests.

-   Repair-affordability feedback-loop tests.

-   Combination pruning tests.

-   Plan ranking tests.

-   Requirement transition tests.

-   Scenario session-version tests.

-   Gemini structured-output parsing tests.

-   SerpApi transit normalization tests.

-   Review-sentiment and filtering tests.

-   Research budget/cache tests.

-   Frontend interaction tests.

-   Full API contract checks.

-   End-to-end mocked demonstration path.

-   Regression tests for existing Nessie, simulation, graph, and research functionality.

Avoid paid provider calls for routine unit tests.

Allow a bounded live smoke test when credentials are available.

No silent fallback from a failed live provider request to fabricated evidence.

* * * * *

17\. Scope boundaries
=====================

### Included

-   Interactive questions

-   Persistent recovery state

-   Approval/eligibility distinctions

-   Outreach drafts

-   Expanded targeted research

-   Detailed transportation

-   Positive-review mechanic filtering

-   Action effects

-   Financial plan simulations

-   Combination ranking

-   Multiple candidate plans

-   Before/after graph and cash comparisons

-   Source-backed next steps

### Excluded

-   Actual email sending

-   Applying for assistance

-   Booking appointments

-   Charging cards or moving money

-   Loan applications

-   Real user banking connections

-   Fully autonomous external action execution

-   Major visual redesign

-   Production-scale distributed infrastructure

-   An unrestricted LLM research loop

* * * * *

18\. Deliverables
=================

Codex must:

1.  Audit the latest working Build 03.5 simulator before coding.

2.  Implement Build 04 in checkpoints.

3.  Preserve existing financial and research correctness.

4.  Add documented API schemas.

5.  Add comprehensive tests.

6.  Provide a functioning interactive demo path.

7.  Update `docs/DECISIONS.md`.

8.  Create `docs/04-INTERACTIVE-RECOVERY-OPTIMIZER.md`.

9.  Create `docs/progress/M4.md`.

10. Explain implementation decisions and incomplete features directly in final chat.

The final Codex report must include:

-   Files/modules changed.

-   How answers affect requirements.

-   How possible differs from confirmed.

-   How action effects reach the simulator.

-   How combinations are generated and ranked.

-   How overlap and double counting are prevented.

-   How many plans can be evaluated.

-   What new SerpApi capabilities were implemented.

-   How transit fare/timing evidence is handled.

-   How mechanic review recommendations are filtered.

-   An actual fixture-based example showing untreated versus recovered financial outcomes.

-   All test/build results.

-   Known limitations.

**Do not simply mark the milestone complete after creating contracts or UI placeholders.**

The milestone is complete only when answering questions can lead to multiple conditional or confirmed plans with genuinely recalculated financial outcomes.

* * * * *

Definition of done
==================

The finished experience should let a judge:

1.  See Maya's financially derived car-breakdown crisis.

2.  Understand which shifts and bills are threatened.

3.  Watch Gemini research possible interventions using SerpApi.

4.  Answer a meaningful question about her options.

5.  See the difference between a possible action and an approved one.

6.  Receive a useful outreach draft when approval is needed.

7.  Compare multiple recovery strategies.

8.  See genuine transit itinerary details and source-backed resources when available.

9.  Understand exactly which shifts, paychecks, repairs, and bills each strategy changes.

10. Update an answer or confirmation and watch the recovery plans recalculate.

**The product promise: One bad day shouldn't become a bad month. Build 04 needs to demonstrate how specific, plausible actions can actually interrupt that cascade.**