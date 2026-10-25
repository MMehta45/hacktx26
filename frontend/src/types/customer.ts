export type DataMode = "live" | "fixture";

export type CustomerSnapshot = {
  schema_version: 1;
  customer: {
    id: string;
    display_name: string;
    age: number;
    occupation: string;
    city: string;
  };
  accounts: Array<{
    id: string;
    type: string;
    nickname: string | null;
    balance_cents: number;
    source: "nessie" | "fixture";
  }>;
  history: {
    start: string;
    end: string;
    transactions: Array<{
      id: string;
      date: string;
      amount_cents: number;
      direction: "debit" | "credit";
      merchant_display: string | null;
      category: string;
      source: string;
      account_id: string;
      description: string | null;
      recurring: boolean;
    }>;
    categories: Array<{
      category: string;
      total_cents: number;
      monthly_average_cents: number;
      transaction_count: number;
      percentage: number;
      recurring_cents: number;
      irregular_cents: number;
      essential: boolean;
    }>;
    spending_total_cents: number;
  };
  upcoming_bills: Array<{
    id: string;
    name: string;
    amount_cents: number;
    due_date: string;
    source: "nessie_bill" | "synthetic_schedule";
    status: string;
    category: string;
    essential: boolean;
    nessie_bill_id: string | null;
    provenance: string;
  }>;
  income_projection: {
    hourly_rate_cents: number;
    shift_hours: 8;
    shifts_per_week: 5;
    gross_per_shift_cents: number;
    gross_weekly_cents: number;
    estimated_net_per_shift_cents: number;
    estimated_net_weekly_cents: number;
    take_home_multiplier_basis_points: number;
    pay_frequency: "weekly";
    next_pay_dates: string[];
    forecast_entries: Array<{
      expected_payment_date: string;
      gross_amount_cents: number;
      estimated_take_home_cents: number;
      work_period_start: string;
      work_period_end: string;
      shift_count: number;
      status: "projected";
      source: "user_wage_forecast";
    }>;
    provenance: "user_wage_forecast";
  };
  cash_flow: {
    start_date: string;
    end_date: string;
    starting_balance_cents: number;
    minimum_balance_cents: number;
    ending_balance_cents: number;
    peak_cash_shortfall_cents: number;
    events: Array<{
      date: string;
      name: string;
      amount_cents: number;
      direction: "income" | "expense";
      source: "projected_income" | "scheduled_bill";
    }>;
    daily_balances: Array<{ date: string; projected_balance_cents: number }>;
    assumption: string;
  };
  scenario: { repair_quote_cents: number };
  source: {
    banking: "nessie" | "fixture";
    simulation_data: "seeded_synthetic" | "local_fixture";
    mode: DataMode;
    message: string;
    retrieved_at: string;
  };
};
