import type { CustomerSnapshot, DataMode } from "@/types/customer";

export type ProblemStatus = "projected" | "conditional" | "inactive" | "unresolved";

export type ShiftRecord = {
  id: string;
  date: string;
  scheduled_start_local: string;
  scheduled_end_local: string;
  hours: 8;
  gross_earning_potential_cents: number;
  take_home_earning_potential_cents: number;
  associated_payday: string;
  vehicle_usable_at_shift_start: boolean;
  attendance: "worked" | "projected_missed" | "unresolved";
  reason: string;
};

export type PayrollRecord = {
  id: string;
  work_period_start: string;
  work_period_end: string;
  payday: string;
  normal_gross_cents: number;
  normal_take_home_cents: number;
  actual_projected_take_home_cents: number;
  scheduled_shift_count: number;
  worked_shift_count: number;
  missed_shift_count: number;
  lost_take_home_cents: number;
  reliability: "already_earned" | "attendance_derived";
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

export type CrisisSimulation = {
  schema_version: 2;
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
    breakdown_at_local: string;
    timezone: "America/Chicago";
    repair_quote_cents: number;
    hourly_rate_cents: number;
    workdays: string[];
    shift_start_local: string;
    shift_end_local: string;
    hours_per_shift: 8;
    weekly_hours: 40;
    take_home_multiplier_basis_points: 8000;
    payroll_frequency: "weekly";
    payroll_weekday: "Friday";
    payroll_lag_weeks: 1;
    actions: string[];
  };
  shift_records: ShiftRecord[];
  payroll_records: PayrollRecord[];
  repair_projection: {
    quote_cents: number;
    earliest_financially_feasible_payment_date: string | null;
    modeled_payment_date: string | null;
    vehicle_restoration_date: string | null;
    days_unavailable_within_forecast: number;
    funding_status: "affordable_and_paid" | "unaffordable_within_horizon" | "unresolved";
    blocked_reason: string | null;
    cash_balance_after_payment_cents: number | null;
    protected_essential_obligations: Array<{
      obligation_id: string;
      name: string;
      amount_cents: number;
      due_date: string;
    }>;
    policy: string;
  };
  events: Array<{
    id: string;
    date: string;
    type: "paycheck" | "bill_due" | "lost_wages" | "repair_payment" | "action_expense" | "assistance" | "borrowing" | "debt_payment" | "bill_fee" | "makeup_wages";
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
  graph_edges: Array<{ id: string; source: string; target: string; condition: string | null }>;
  warnings: string[];
  applied_action_ids: string[];
};

export type CrisisSimulationResponse = {
  snapshot: CustomerSnapshot;
  simulation: CrisisSimulation;
};
