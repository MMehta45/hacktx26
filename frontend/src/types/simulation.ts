import type { CustomerSnapshot, DataMode } from "@/types/customer";

export type ProblemStatus = "projected" | "conditional" | "inactive" | "unresolved";

export type CrisisSimulation = {
  schema_version: 1;
  source: {
    customer_id: string;
    account_ids: string[];
    current_balance_cents: number;
    banking_mode: DataMode;
    source_as_of_date: string;
    source_retrieved_at: string;
    timezone: "America/Chicago";
  };
  scenario: {
    scenario_start_date: string;
    forecast_end_date: string;
    timezone: "America/Chicago";
    repair_quote_cents: number;
    repair_payment_status: "unpaid" | "deferred" | "paid";
    repair_delay_days: number;
    affected_shift_dates: string[];
    hours_per_shift: number;
    weekly_hours: number;
    take_home_multiplier_basis_points: number;
    transport_cost_cents: number;
    borrowed_amount_cents: number;
    debt_payment_cents: number;
    actions: string[];
  };
  events: Array<{
    id: string;
    date: string;
    type:
      | "paycheck"
      | "bill_due"
      | "lost_wages"
      | "repair_payment"
      | "transport_cost"
      | "borrowing"
      | "debt_payment";
    signed_amount_cents: number;
    description: string;
    source: string;
    status: "projected" | "scenario_assumption";
    provenance_id: string | null;
    essential: boolean | null;
  }>;
  cashflow: Array<{
    date: string;
    normal_balance_cents: number;
    crisis_balance_cents: number;
    constrained_available_cents: number;
    raw_shortfall: boolean;
  }>;
  income_lost_by_payday: Array<{
    payday: string;
    affected_shift_dates: string[];
    gross_lost_cents: number;
    take_home_lost_cents: number;
    normal_take_home_cents: number;
    crisis_take_home_cents: number;
  }>;
  bill_outcomes: BillOutcome[];
  unpaid_bills: BillOutcome[];
  normal_ending_balance_cents: number;
  crisis_ending_balance_cents: number;
  constrained_ending_cash_cents: number;
  peak_funding_gap_cents: number;
  unpaid_essential_total_cents: number;
  graph_nodes: Array<{
    id: string;
    label: string;
    description: string;
    status: ProblemStatus;
    activation_date: string | null;
    evidence: string;
    amount_cents: number | null;
    source: "nessie" | "fixture" | "scenario_assumption" | "projection";
  }>;
  graph_edges: Array<{
    id: string;
    source: string;
    target: string;
    condition: string | null;
  }>;
  warnings: string[];
};

export type BillOutcome = {
  obligation_id: string;
  name: string;
  amount_cents: number;
  due_date: string;
  funded_cents: number;
  unpaid_cents: number;
  essential: boolean;
  category: string;
  projected_status: "funded" | "partially_unpaid" | "unpaid";
  payment_priority: number;
  source: string;
};

export type CrisisSimulationResponse = {
  snapshot: CustomerSnapshot;
  simulation: CrisisSimulation;
};
