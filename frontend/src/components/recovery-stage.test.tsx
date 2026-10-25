import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { RecoveryPlanView } from "./recovery-stage";
import type { RecoveryPlan } from "@/types/recovery";
import type { CrisisSimulation } from "@/types/simulation";

const baseline = {
  unpaid_essential_total_cents: 90_000,
  peak_funding_gap_cents: 65_000,
  crisis_ending_balance_cents: -65_000,
  graph_nodes: [],
  shift_records: [],
  cashflow: [],
  unpaid_bills: [],
  repair_projection: { modeled_payment_date: null },
} as unknown as CrisisSimulation;

const plan = {
  id: "plan-remote",
  rank: 1,
  name: "Request temporary remote work",
  strategy_labels: ["income_preservation"],
  feasibility: "conditional_pending_approval",
  conditional_label: "If manager approval succeeds, this is the recalculated outcome.",
  action_ids: ["action-remote-work"],
  actions: [],
  unresolved_requirement_ids: ["remote_manager_approval"],
  conditional_assumptions: ["The manager approves the listed dates."],
  result: { unpaid_essential_total_cents: 26_000, peak_funding_gap_cents: 1_000, crisis_ending_balance_cents: -1_000, graph_nodes: [], shift_records: [], cashflow: [], unpaid_bills: [], repair_projection: { modeled_payment_date: "2026-11-06" } } as unknown as CrisisSimulation,
  delta: { essential_unpaid_change_cents: -64_000, peak_funding_gap_change_cents: -64_000, ending_balance_change_cents: 64_000, recovered_shift_ids: ["shift-2026-10-26"], income_preserved_cents: 64_000, incremental_cost_cents: 0, repair_date_change_days: -17 },
  ranking_rationale: [],
  explanation: "The authoritative simulator preserves five shifts only under the listed conditions.",
  sources: [],
  outreach_drafts: [],
  next_steps: ["Copy the employer request draft.", "Wait for explicit approval."],
} as RecoveryPlan;

describe("recovery plan", () => {
  it("labels contingent outcomes and shows recalculated before/after values", () => {
    const html = renderToStaticMarkup(<RecoveryPlanView plan={plan} baseline={baseline} busy={false} onConfirm={() => undefined} />);
    expect(html).toContain("Conditional");
    expect(html).toContain("The manager approves the listed dates");
    expect(html).toContain("Additional earnings");
    expect(html).toContain("$260.00");
    expect(html).toContain("Detailed financial view");
    expect(html).not.toContain("WHAT MUST STILL HAPPEN");
    expect(html).not.toContain("guaranteed");
  });
});
