# Build 06 — Breakpoint: Complete Product UI Overhaul

**Repository:** `MMehta45/hacktx26`

**Scope:** Major frontend redesign, product rebrand, interaction overhaul, and causal graph animation.

**Priority:** High — final HackTX presentation build.

## Objective

Transform the existing **One Bad Tuesday** prototype into a polished, coherent financial-recovery product named **Breakpoint**.

The backend, simulator, recovery engine, Gemini research, SerpApi integrations, Nessie integration, and financial calculations are functioning.

**This build is frontend-focused.**

We need to replace the current dense developer-oriented experience with a distinctive consumer-facing product that communicates:

1. What happened to Maya?
2. How will one disruption spread into other problems?
3. Which parts of the cascade can we interrupt?
4. What did Breakpoint discover?
5. What actions should Maya take?
6. How does her financial future change?

Make the experience memorable and visually compelling without sacrificing actual functionality or accounting accuracy.

Do not rewrite the financial engine, research pipeline, recovery endpoints, or existing business logic.

Work with the existing Next.js / React / Tailwind / React Flow architecture.

---

# 1. Rebrand the product to Breakpoint

The application should be called:

**Breakpoint**

Suggested tagline:

**One bad day shouldn't become a bad month.**

The product positioning is not simply financial budgeting.

Breakpoint analyzes how a disruption could cascade through someone's finances, identifies interventions, and helps them act before the consequences compound.

## Rebranding scope

Replace "One Bad Tuesday" in user-facing product branding with "Breakpoint":

- Page title
- Navigation/header
- Hero
- Browser metadata
- Footer
- Loading states
- Recovery-plan presentation
- Product explanations

Do not blindly rename repository folders, API routes, test fixtures, or internal scenario identifiers.

Keep the name "One Bad Tuesday" when it refers to the original HackTX project concept or historical documentation, not the current product brand.

Create a simple, typography-driven wordmark for Breakpoint.

Avoid generating a complicated illustrative logo.

A small abstract fracture, connection, or interrupted-line motif may accompany the wordmark.

The identity should feel premium, intelligent, and human-centered.

---

# 2. Implement the new design system

## Color palette

Use these exact colors as the foundation.

| Token | Name | Hex | Suggested usage |
|---|---|---|---|
| `--color-cream` | Papaya Whip | `#FFF3D8` | Main backgrounds, large editorial sections |
| `--color-blue` | Dusk Blue | `#4B5480` | Secondary surfaces, navigation, information |
| `--color-mint` | Ocean Mist | `#1FBFA7` | Recovery, positive impact, primary actions |
| `--color-ink` | Carbon Black | `#1A2122` | Text, dark sections, graph canvas |

### Palette rules

The entire product should use these four colors consistently.

Allowed:

- Opacity variations.
- Tonal shades derived from these colors.
- White or near-white surfaces where contrast and readability require them.
- Muted neutrals for secondary text and borders.

Avoid the current mixture of random orange, slate, violet, amber, and emerald styles.

Do not use bright green to communicate every positive result or red for every negative result.

Use color with purpose:

- Cream: context and breathing room.
- Ink: high-value information and core visualization.
- Blue: secondary information and unknown/conditional states.
- Mint: interventions, important connections, recovery, selected actions.

Negative outcomes can use contrast, iconography, labels, and restrained warning accents rather than introducing an entirely new color system.

Maintain WCAG-appropriate text contrast.

### Visual direction

Design language:

- Editorial fintech
- Large typography
- Deliberate whitespace
- Clean data visualization
- Thin borders
- Elegant rounded corners
- Minimal shadows
- Occasional dark immersive sections
- Restrained motion
- Clear contrast between story and underlying detail

Avoid making the app look like an enterprise admin dashboard or a collection of generic Tailwind cards.

---

# 3. Typography

Use the following Google Fonts:

**Faculty Glyphic**

https://fonts.google.com/specimen/Faculty+Glyphic

**Prata**

https://fonts.google.com/specimen/Prata

### Typography hierarchy

Use:

**Prata**
- Hero headline
- Major editorial statements
- Occasional large financial figures or pull quotes
- Visually important section transitions

**Faculty Glyphic**
- Major section titles
- Strategy names
- Branded interface elements
- Selected callouts

**Clean sans-serif fallback/system font**
- Long paragraphs
- Tables
- Metrics labels
- Forms
- Technical details
- Buttons when the decorative fonts reduce readability

Do not set every paragraph and every tiny label in a decorative typeface.

Use the fonts intentionally to create hierarchy.

Prefer `next/font/google` where supported and ensure font loading does not break production builds.

Define typography tokens in the global styles.

Implement appropriate responsive font scaling.

---

# 4. Redesign the overall product journey

Preserve the existing four-stage workflow:

1. Start
2. Crisis
3. Explore
4. Plan

But reframe the stages in more intuitive product language.

Suggested labels:

| Existing | New |
|---|---|
| Start | Your situation |
| Crisis | The ripple effect |
| Explore | Find a way through |
| Plan | Your recovery plan |

These labels are suggestions; choose polished language that fits the visual system.

### Navigation

Replace the existing pill-heavy navigation with a more elegant progress/navigation treatment.

Show:

- Current stage
- Completed stages
- Upcoming stages
- Ability to navigate backward
- Clear progression

Avoid displaying unnecessary implementation information such as internal session versions, scenario fingerprints, call budgets, or research IDs.

Retain navigability and state preservation.

### Overall page structure

Each stage should have:

- A clear headline
- One short explanation
- One primary visual or interaction
- Concise key metrics
- Secondary supporting information
- A prominent action to continue

The current UI has too many equally prominent sections.

Introduce a consistent hierarchy.

---

# 5. Stage 01 — Your situation

This stage introduces Maya and the disruption.

## Desired experience

The user should immediately understand:

"Maya has $310 in her account, works an hourly job, and just received a $400 car repair quote."

The story should feel personal and concrete.

### Hero

Use a large editorial headline along the lines of:

**A $400 problem shouldn't cost someone their livelihood.**

Supporting text:

"See how a single unexpected expense can affect work, bills, and financial stability—and where to interrupt the chain."

Create a clean introductory section with Breakpoint branding.

### Scenario inputs

Keep:

- Person/scenario name
- Current finances
- Hourly wage
- Repair quote
- Breakdown date
- Relevant work/location context

But reduce form clutter.

Use compact, attractive input groups or an editable scenario summary.

The default Maya example should be ready to explore immediately.

### Transaction and spending data

Currently the UI exposes extensive transaction history and category spending data.

This should not dominate the experience.

Replace it with a compact financial overview:

- Available starting balance
- Income cadence
- Upcoming bills
- Typical spending
- Data source

Show an optional **View financial details** or **Explore spending** drawer.

Inside it:

- Transaction history
- Spending categories
- Recurring charges
- Evidence/provenance

Do not delete the data or remove access to it.

The user should not need to inspect 89 transactions to understand Maya's problem.

---

# 6. Stage 02 — The ripple effect

This is one of the most important parts of the project.

The current crisis stage contains useful financial analysis, but its presentation is too dense.

The centerpiece must be the **causal cascade graph**.

## Desired story

Show how one disruption propagates:

**Car breaks down → Can't commute → Missed work → Smaller paycheck → Cash shortage → Bills at risk**

Secondary branches should remain visible when relevant:

- Repair expense
- Delayed repair
- Transportation alternatives/costs
- Cash reserves
- Borrowing
- Late fees
- Future debt payments

The graph should feel like a developing chain of consequences, not a static diagram of database entities.

## Primary graph redesign

Inspect:

`frontend/src/components/crisis-graph.tsx`

The current graph uses hardcoded horizontal positions and reveals several nodes sequentially while most other elements already exist.

Replace this with a **top-to-bottom hierarchical layout**.

### Direction

Use:

`Top → Bottom`

The initial event should sit at the top.

Consequences flow downward.

Branches split naturally.

The final financial consequences should appear near the bottom.

Avoid the current very wide left-to-right graph.

### Layout requirements

Use a proper hierarchical/DAG layout mechanism, such as:

- Dagre with React Flow, or
- ELK.js if its added complexity is justified.

Prefer the smallest reliable dependency and implementation.

The layout should:

- Compute node positions.
- Respect parent/child relationships.
- Reduce edge crossings.
- Maintain consistent row spacing.
- Support multiple branches.
- Keep the central causal chain visually obvious.
- Avoid overlapping nodes and labels.
- Fit comfortably in a desktop viewport.
- Remain usable on mobile.

The graph model may contain feedback-like edges or conditional relationships.

Do not force a cyclic structure into an invalid DAG layout.

Where necessary, distinguish the primary forward cascade from secondary feedback/dependency links, or use a deterministic layer assignment that safely handles cycles.

Do not alter the underlying financial graph data merely to produce a prettier layout.

---

# 7. Build a true graph-drawing animation

This is the most important interaction requirement.

**Do not simply fade in all graph nodes or animate particles along already visible lines.**

The animation should visually construct the causal graph.

### Desired sequence

1. The initial problem appears.
2. Its outgoing connection starts drawing.
3. The connection visibly extends toward the next problem.
4. The next node appears when the connection reaches it.
5. That node's outgoing connections begin drawing.
6. Each branch develops in causal/dependency order.
7. The animation continues until the important consequences are revealed.
8. The full graph remains available for interaction.

Think of the financial cascade being traced or drawn onto the canvas.

### Animation mechanics

Use SVG path-drawing animation where possible.

For example:

- `stroke-dasharray`
- `stroke-dashoffset`
- CSS transitions or requestAnimationFrame
- React Flow custom edges
- Motion library only if genuinely beneficial

A path should transition from completely hidden to fully drawn.

Nodes can use a restrained opacity and scale entrance as the incoming edge finishes.

### Dependency-aware sequencing

Base the reveal order on the actual graph relationships, not an arbitrary fixed array of node IDs.

The animation must account for:

- Branching paths
- Multiple incoming edges
- Conditional nodes
- Inactive nodes
- Feedback connections

A node should not be marked causally activated merely because an incoming edge is drawn.

Use model status to distinguish projected, conditional, and inactive consequences.

### Status styling

Suggested behavior:

**Projected**
- High contrast
- Stronger connection
- Clearly activated

**Conditional**
- More muted
- Dashed or lower-opacity connection
- Distinct conditional marker

**Inactive**
- Low prominence
- Accessible on interaction
- Not animated as a realized consequence

Do not animate conditional or inactive branches as though they definitely happened.

### Graph controls

Include:

- Replay
- Pause/resume
- Skip animation / Show full graph
- Fit graph
- Zoom controls where useful

Replay should restart the actual line-tracing sequence.

It should not merely change node opacity.

### Timing

Keep the overall experience concise enough for a live demo.

The primary cascade should complete within a few seconds.

Secondary branches can reveal slightly later.

Avoid long waits between each node.

Allow users to skip immediately.

### Accessibility

Respect `prefers-reduced-motion`.

If reduced motion is enabled, display the full graph immediately.

Do not rely on animation alone to communicate causal meaning.

Keyboard selection and accessible labels should continue working.

---

# 8. Make the graph more readable and interactive

The existing graph has tiny labels and large amounts of unused canvas.

Improve:

- Node size
- Text readability
- Spacing
- Contrast
- Selected-node styles
- Edge routing
- Branch grouping
- Zoom defaults
- Fit-to-view behavior

### Focus mode

When the user selects a node:

- Highlight that node.
- Highlight its relevant incoming and outgoing causal connections.
- De-emphasize unrelated branches.
- Show a compact explanation panel.

For example:

**Missed work**

"Without transportation, Maya misses scheduled shifts. Those lost hours reduce her next paycheck."

Then show:

- Affected dates
- Financial consequence
- Next downstream consequence
- Whether the node is projected or conditional

Do not display raw internal evidence strings as the default explanation.

Keep detailed provenance available under an optional "How we calculated this" control.

### Important

The graph should communicate the cascade at first glance even if the user never clicks a node.

---

# 9. Simplify the rest of Stage 02

The crisis stage currently exposes many detailed metrics.

Keep the most valuable:

- Shifts at risk
- Estimated income lost
- Bills threatened
- Peak scheduled funding gap
- Repair affordability

Use a clean summary row or editorial metric layout.

### Cash-flow visualization

Preserve the normal-versus-crisis cash-flow comparison.

Improve its readability:

- Better labels
- Clear units
- Date markers
- Hover or selected-day details
- Strong but restrained color differentiation
- Explanation of what the negative projected balance means

The chart should make divergence between normal and crisis understandable immediately.

### Hide deep financial data

Move detailed:

- Bill-allocation records
- Day-by-day ledger
- Full shift records
- Payroll breakdowns
- Formula explanations
- Source data

into expandable details or a drawer.

Do not delete functionality.

---

# 10. Stage 03 — Find a way through

This stage should feel like Breakpoint is actively investigating ways to stop the cascade.

Currently it exposes too many:

- Hypotheses
- Tool statuses
- Research events
- Candidate cards
- Raw sources
- Uncertainty descriptions

The core experience should answer:

**"What can we do about this?"**

## Proposed top-level presentation

Show a concise investigation summary:

- Interventions discovered
- High-impact opportunities
- Actions needing confirmation
- Relevant resources found

Then organize candidate interventions into useful categories:

- Keep earning
- Get to work
- Buy time on bills
- Find assistance
- Reduce immediate costs
- Repair the car

Only display categories that actually have relevant findings.

### Opportunity cards

Each card should show:

- Intervention name
- Why it could help
- Expected type of impact
- What must be confirmed
- One clear next action

Examples:

**Take Route 5 to work**

"Keep your shifts for about $2.50 per workday."

**Ask about temporary remote work**

"Protect income while your car is unavailable."

**Request a rent extension**

"Buy time until your next paycheck."

Do not invent specific numerical impact when it is not known.

### Source handling

Keep meaningful external links accessible.

However, do not display five raw Google Search results under every intervention.

Show:

- The strongest relevant link or resource
- A "View resources" expansion for the rest

Group duplicates and filter irrelevant results.

Retain source attribution and limitations in the expanded view.

### Remove developer-oriented content from the default UI

Hide:

- Gemini extraction diagnostics
- Token/call budgets
- SerpApi cache hits
- Raw hypothesis IDs
- Confidence-debug strings
- Backend pathway status objects
- Internal source types
- Raw tool-call logs

These may remain available through a development-only debug panel if useful.

Do not expose them as part of the primary consumer experience.

### Research loading state

Make the investigation feel active.

Use meaningful progress language:

- Checking transportation options
- Looking for ways to protect income
- Finding assistance resources
- Comparing possible interventions
- Preparing recovery options

Use actual process state where available.

Do not fabricate progress percentages or imply a search completed when it hasn't.

---

# 11. Stage 04 — Your recovery plan

The current Plan stage contains strong underlying information but is visually overwhelming.

Seven enormous strategy cards should not appear one after another in full detail.

## Primary redesign

Create a clear strategy comparison interface.

At the top, display a concise summary:

**Here's how Maya can recover.**

Show the most relevant strategies as compact selectable cards or rows.

For each strategy, emphasize:

- Strategy name
- Status: ready or conditional
- Shifts saved
- Additional earnings
- Immediate cost
- Effect on bills
- Repair timing

A selected strategy opens its complete details.

### Strategy examples

**Take Route 5**

Preserves work using low-cost transportation.

**Work remotely**

Protects eligible shifts if approved.

**Combine approaches**

Use remote work and public transportation on different days.

**Reduce immediate spending**

Cancel or adjust upcoming discretionary expenses.

Preserve all financially meaningful alternatives from the optimizer.

Do not limit the backend to these examples.

### Default selection

Select a financially meaningful high-ranked strategy by default.

Avoid overwhelming users with every variation of the same approach.

Allow the user to switch between alternatives without losing their answered questions.

### Selected plan details

Organize the details into clear areas:

**1. What to do**
- Actions
- Order
- Dependencies
- Confirmation requirements

**2. Expected outcome**
- Shifts preserved
- Take-home earnings preserved
- Pay received versus payable later
- Repair timing
- Bills missed or settled

**3. Financial picture**
- Starting position
- Peak funding gap
- Available cash
- Outstanding liabilities
- Expected living expenses
- Remaining shortfall

**4. Resources**
- Transit details
- Application links
- Contact information
- Outreach drafts

**5. Timeline**
- Immediate actions
- Work shifts
- Paydays
- Bill due dates
- Repair/restoration milestones

### Progressive disclosure

The default view should not expose:

- Full 30-day ledger
- Every payroll record
- Every financial formula
- Full source metadata
- Every graph-node reconciliation
- Every model assumption

Keep the information accessible through expandable sections.

### Outreach drafts

Retain the full detailed drafts and working copy functionality.

Present drafts as part of the relevant action.

For example:

**Request temporary remote work**

[Read draft] [Copy message]

Use properly functioning controls.

Preserve subject, body, and line breaks.

Never claim the request has been sent.

---

# 12. Rewrite product-facing language

The current UI frequently uses technical or defensive language.

Examples:

- "Projected untreated cascade"
- "This is not a live banking event"
- "No public source is asserted"
- "Provider-backed outbound and return timing"
- "Under the listed conditions, the simulator recovers..."
- "Unquantified research leads"
- "Research dependency"
- "Scenario assumption"

These are useful internally but should not dominate the product.

Rewrite interface copy so it sounds like a polished product.

### Language direction

Clear.

Human.

Specific.

Action-oriented.

Financially understandable.

Confident without overpromising.

### Examples

Instead of:

"Projected untreated cascade"

Use:

**What happens if nothing changes?**

Instead of:

"Unquantified research leads"

Use:

**Other ways forward**

Instead of:

"Under the listed conditions, the simulator recovers 16 shifts..."

Use:

**This could save 16 shifts and protect $2,048 in earnings.**

Instead of:

"Research this dependency"

Use a context-aware next step:

- Check availability
- Ask your manager
- Request an extension
- Explore the program
- Get a repair quote

Instead of:

"Modeled repair"

Use:

**When the car could be repaired**

Instead of:

"Ending raw balance"

Use:

**Projected balance after scheduled bills**

### Preserve critical truthfulness

Do not remove meaningful safety or financial distinctions merely to make copy sound stronger.

For example:

- Conditional plans must not sound guaranteed.
- A demo Route 5 schedule must not be presented as live-confirmed.
- Unknown assistance eligibility must remain unknown.
- A drafted email must not appear sent.
- Estimated cash after scheduled bills must not be described as fully disposable cash.
- Wages earned are not the same as pay received.

But communicate these distinctions naturally.

Keep a concise methodology/data-disclosure section for detailed assumptions.

Avoid repeating the same long disclaimer beneath every card.

---

# 13. Hide development information from regular users

We currently expose too much of the system's internals.

Implement a simple distinction between:

**Product UI**
- Useful information
- Actions
- Financial consequences
- Resources
- Uncertainty that affects decisions

**Developer diagnostics**
- Raw API responses
- Tool traces
- Evidence IDs
- Research cache statistics
- Scenario fingerprints
- Extraction errors
- Internal scores
- Full data payloads

Development diagnostics should be hidden by default and, where appropriate, available only in development mode.

Do not delete logs necessary for debugging.

Do not expose API credentials or private configuration.

---

# 14. Build reusable components

Refactor large frontend components where it improves maintainability.

Suggested reusable components:

- `BreakpointHeader`
- `StageProgress`
- `SectionHeading`
- `ImpactMetric`
- `MetricComparison`
- `DisclosurePanel`
- `FinancialDetailsDrawer`
- `OpportunityCard`
- `StrategySelector`
- `SelectedStrategyView`
- `ResourceList`
- `OutreachDraft`
- `RecoveryTimeline`
- `CascadeGraph`
- `CascadeNode`
- `CascadeEdge`
- `GraphDetailsPanel`

These names are suggestions, not mandatory.

Avoid creating excessive abstraction for tiny components.

The existing files may be split into smaller components, but preserve current data flow and behavior.

Use the established Next.js, React, and Tailwind patterns.

---

# 15. Responsive design

The current app is largely desktop-oriented.

Ensure the redesigned experience works on:

- Large desktop screens
- Standard laptop screens
- Tablets
- Mobile widths

### Graph behavior

On desktop:
- Large, readable hierarchical graph.
- Pan and zoom where needed.
- Properly positioned details panel.

On mobile:
- Scrollable/pannable graph viewport.
- Fit controls.
- Readable selected-node details below the graph.
- No clipped buttons or inaccessible branches.

Do not shrink an entire 14-node graph until every label becomes illegible.

### Other components

- Stack metric grids.
- Collapse navigation appropriately.
- Avoid horizontal overflow.
- Make buttons touch-friendly.
- Ensure drawers and expanded details are accessible.

---

# 16. Motion and microinteractions

Motion should support understanding rather than decoration.

Useful animations:

- Graph path tracing
- Node arrival
- Financial metric updates
- Stage transitions
- Expansion and collapse
- Selected strategy transitions
- Hover/selection responses

Avoid:

- Constantly pulsing elements
- Excessive parallax
- Large entrance animations on every card
- Long loading theatrics
- Distracting transitions during plan recalculation

Respect reduced-motion preferences throughout.

Use lightweight CSS transitions where sufficient.

---

# 17. Preserve the full existing application

Do not break or remove:

- Nessie snapshot loading
- Local fixture fallback
- Crisis simulation
- The 14-node graph model
- Gemini research
- SerpApi evidence
- Deterministic Route 5 fixture
- Remote-work actions
- Rent-extension actions
- Subscription cancellation
- Alternative repair quotes
- Research resources
- Financial opportunity summaries
- Outstanding-liability accounting
- Living-expense forecast variants
- Wage earning/payroll reconciliation
- Ranked recovery strategies
- Conditional requirements
- Yes / No / Not yet questions
- Detailed outreach drafts
- Copy draft functionality
- Session lifecycle and state persistence

This build should change how the user experiences the system, not remove the intelligence behind it.

---

# 18. Test requirements

Run all existing backend/frontend tests.

Add or update tests for the redesigned frontend.

### Navigation
- Four-stage flow still works.
- Back/forward navigation preserves relevant state.
- Restart resets correctly.

### Financial presentation
- Values still come directly from simulator/recovery results.
- No hardcoded financial figures.
- Earned versus received pay remains correct.
- Conditional plans remain clearly conditional.
- Living expenses remain labeled as estimates.

### Drill-down interactions
- Hidden transaction history can be opened.
- Full spending categories remain accessible.
- Financial details expand and collapse.
- Resources open correctly.
- Outreach drafts copy successfully.

### Graph
- Top-down positions are valid.
- Nodes do not overlap.
- Edges connect the intended nodes.
- Reveal order respects the causal/dependency structure.
- Paths actually draw in over time.
- Nodes reveal after their relevant incoming paths.
- Replay resets and replays the animation.
- Skip shows the full graph.
- Reduced motion shows the completed graph.
- Clicking a node reveals the correct detail.
- Conditional nodes aren't portrayed as guaranteed outcomes.
- Fit/zoom remains usable.
- No graph remains permanently hidden after a state change.

### Responsive
- No horizontal page overflow at mobile widths.
- Cards and controls remain usable.
- Graph details are accessible on small screens.

### Build verification

Run:

```bash
cd frontend
npm run typecheck
npm run lint
npm test
npm run build
```

Run backend tests as an additional regression check where available.

Do not add unnecessary dependencies.

---

# 19. Implementation order

Follow this sequence:

## A. Branding and design tokens

Implement:
- Breakpoint naming
- Palette
- Fonts
- Global typography
- Common button/card/input styles
- Header and navigation

## B. Graph overhaul — highest priority

Implement:
- Top-down hierarchical layout
- Node and edge styling
- Actual traced-path drawing animation
- Replay/pause/skip
- Focus mode
- Responsive graph behavior

This should receive substantial attention. It is a centerpiece of the demo.

## C. Stage 01 and Stage 02 cleanup

Simplify:
- Scenario overview
- Financial snapshot
- Transaction/category drill-downs
- Crisis summaries
- Cash-flow visualization

## D. Stage 03 cleanup

Simplify:
- Investigation overview
- Hypotheses
- Opportunity cards
- Resources
- Status reporting

Keep technical research details hidden.

## E. Stage 04 cleanup

Implement:
- Compact strategy comparison
- Selected plan detail
- Financial impact summary
- Resources and outreach
- Timeline and optional details

## F. Responsive and QA

- Cross-screen checks
- Typecheck
- Tests
- Production build
- Fix overflow and broken interactions

Do not stop after updating the palette and hero. Complete all stages.

---

# 20. Final deliverables

At completion, provide:

1. Summary of the Breakpoint design system.
2. Updated frontend component structure.
3. Explanation of the new graph layout and animation mechanics.
4. Screens/sections redesigned.
5. Details hidden behind drill-down interactions.
6. Confirmation of existing feature preservation.
7. Any backend changes, if absolutely necessary.
8. Test results.
9. Remaining visual limitations.
10. Files changed.

Update relevant frontend/design documentation.

Do not spend time developing new financial formulas, adding new external APIs, or rewriting the research engine.

---

# Definition of done

The product is now visibly **Breakpoint**, using the specified palette and typography.

The four-stage journey tells a clear story without overwhelming users with developer data.

The causal graph has a readable top-down hierarchy and a genuine edge-tracing animation that constructs the graph as consequences unfold.

Transaction history, spending categories, detailed calculations, and source metadata remain available through drill-downs rather than dominating the interface.

Research opportunities, financial strategies, resources, and outreach drafts are concise and actionable.

All existing financial logic and user interactions remain working.

**This is a full product-experience overhaul, not a reskin. Optimize for an impressive, understandable, reliable HackTX demo.**