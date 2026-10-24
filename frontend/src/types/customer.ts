export type DataMode = "live" | "fixture";

export type CustomerSnapshot = {
  schema_version: 1;
  customer: { id: string; display_name: string };
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
    }>;
    categories: Array<{
      category: string;
      total_cents: number;
      monthly_average_cents: number;
      transaction_count: number;
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
  }>;
  income_projection: {
    hourly_rate_cents: number;
    shift_hours: 8;
    shifts_per_week: 5;
    gross_per_shift_cents: number;
    gross_weekly_cents: number;
    pay_frequency: "weekly";
    next_pay_dates: string[];
    provenance: "user_wage_forecast";
  };
  scenario: { repair_quote_cents: number };
  source: {
    banking: "nessie" | "fixture";
    simulation_data: "seeded_synthetic" | "local_fixture";
    mode: DataMode;
    message: string;
  };
};
