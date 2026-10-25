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
  },
  shift_records: [{ id: "shift-1", date: "2026-10-26", scheduled_start_local: "2026-10-26T08:00:00", scheduled_end_local: "2026-10-26T16:00:00", hours: 8, gross_earning_potential_cents: 16_000, take_home_earning_potential_cents: 12_800, associated_payday: "2026-11-06", vehicle_usable_at_shift_start: false, attendance: "projected_missed", reason: "Vehicle unavailable" }],
  payroll_records: [{ id: "payroll-1", work_period_start: "2026-10-19", work_period_end: "2026-10-25", payday: "2026-10-30", normal_gross_cents: 80_000, normal_take_home_cents: 64_000, actual_projected_take_home_cents: 64_000, scheduled_shift_count: 5, worked_shift_count: 5, missed_shift_count: 0, lost_take_home_cents: 0, reliability: "already_earned" }],
  repair_projection: { quote_cents: 40_000, earliest_financially_feasible_payment_date: null, modeled_payment_date: null, vehicle_restoration_date: null, days_unavailable_within_forecast: 31, funding_status: "unaffordable_within_horizon", blocked_reason: "Essential bills remain protected.", cash_balance_after_payment_cents: null, protected_essential_obligations: [], policy: "test" },
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
        loading={false}
        error={null}
        onRepairChange={() => undefined}
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
