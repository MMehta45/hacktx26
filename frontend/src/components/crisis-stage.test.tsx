import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { CrisisStage } from "./crisis-stage";
import type { CustomerSnapshot } from "@/types/customer";
import type { CrisisSimulation } from "@/types/simulation";

const snapshot = {
  accounts: [{ id: "account", type: "Checking", nickname: "Demo", balance_cents: 31_000, source: "fixture" }],
  history: { spending_total_cents: 0, categories: [], transactions: [] },
  upcoming_bills: [],
} as unknown as CustomerSnapshot;

const simulation = {
  source: {
    banking_mode: "fixture",
    current_balance_cents: 31_000,
    source_retrieved_at: "2026-10-24T12:00:00Z",
  },
  scenario: {
    scenario_start_date: "2026-10-24",
    forecast_end_date: "2026-11-23",
    repair_quote_cents: 40_000,
    repair_payment_status: "unpaid",
  },
  cashflow: [
    { date: "2026-10-24", normal_balance_cents: 31_000, crisis_balance_cents: 31_000, constrained_available_cents: 31_000, raw_shortfall: false },
    { date: "2026-10-25", normal_balance_cents: 5_000, crisis_balance_cents: -20_600, constrained_available_cents: 0, raw_shortfall: true },
  ],
  income_lost_by_payday: [{ take_home_lost_cents: 25_600 }],
  events: [{ id: "lost", date: "2026-10-30", type: "lost_wages", signed_amount_cents: -25_600, description: "Estimated take-home lost", source: "crisis_projection" }],
  unpaid_bills: [{ obligation_id: "rent", name: "Rent", amount_cents: 90_000, due_date: "2026-10-31", funded_cents: 69_400, unpaid_cents: 20_600, essential: true, category: "Housing/Rent", projected_status: "partially_unpaid", payment_priority: 1, source: "synthetic_schedule" }],
  graph_nodes: [{ id: "car_breaks_down", label: "Car breaks down", description: "Scenario starts", status: "projected", activation_date: "2026-10-24", evidence: "Scenario assumption", amount_cents: null, source: "scenario_assumption" }],
  graph_edges: [],
  normal_ending_balance_cents: 5_000,
  crisis_ending_balance_cents: -20_600,
  constrained_ending_cash_cents: 0,
  peak_funding_gap_cents: 20_600,
  unpaid_essential_total_cents: 20_600,
  warnings: [],
} as unknown as CrisisSimulation;

describe("crisis dashboard", () => {
  it("renders both balance series, graph data, and unpaid-bill explanation", () => {
    const markup = renderToStaticMarkup(
      <CrisisStage
        snapshot={snapshot}
        simulation={simulation}
        repairQuote={400}
        affectedShifts={2}
        loading={false}
        error={null}
        onRepairChange={() => undefined}
        onAffectedShiftsChange={() => undefined}
        onRerun={() => undefined}
        onBack={() => undefined}
        onNext={() => undefined}
      />,
    );

    expect(markup).toContain("Normal vs untreated cash flow");
    expect(markup.match(/<polyline/g)).toHaveLength(2);
    expect(markup).toContain("Car breaks down");
    expect(markup).toContain("Rent");
    expect(markup).toContain("$206.00 uncovered");
  });
});
