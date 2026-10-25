"use client";

import { FormEvent, useMemo, useState } from "react";

import {
  DEFAULT_HOURLY_WAGE,
  DEFAULT_REPAIR_QUOTE,
  formatCurrency,
  formatDate,
  wageInputToCents,
  wagePreview,
} from "@/lib/scenario";
import type { CustomerSnapshot } from "@/types/customer";

type Stage = 1 | 2 | 3 | 4;
type RequestState = { kind: "idle" } | { kind: "loading" } | { kind: "error"; message: string };

const stages: Array<{ id: Stage; short: string; label: string }> = [
  { id: 1, short: "Start", label: "Set the scene" },
  { id: 2, short: "Snapshot", label: "Financial snapshot" },
  { id: 3, short: "Explore", label: "Finding a way out" },
  { id: 4, short: "Plan", label: "Recommended plan" },
];

const categoryColors: Record<string, string> = {
  "Housing/Rent": "bg-violet-500",
  Groceries: "bg-emerald-500",
  Dining: "bg-orange-400",
  "Transportation/Gas": "bg-sky-500",
  Utilities: "bg-amber-400",
  Insurance: "bg-indigo-400",
  Shopping: "bg-pink-400",
  Subscriptions: "bg-fuchsia-400",
  Health: "bg-teal-400",
  Other: "bg-slate-400",
};

function daysBetween(start: string, end: string): number {
  return Math.round(
    (Date.parse(`${end}T00:00:00Z`) - Date.parse(`${start}T00:00:00Z`)) / 86_400_000,
  );
}

function DataBadge({ snapshot }: { snapshot: CustomerSnapshot }) {
  const live = snapshot.source.mode === "live";
  return (
    <div
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold ${
        live
          ? "border-emerald-200 bg-emerald-50 text-emerald-800"
          : "border-amber-200 bg-amber-50 text-amber-900"
      }`}
    >
      <span className={`h-2 w-2 rounded-full ${live ? "bg-emerald-500" : "bg-amber-500"}`} />
      {live ? "Live Nessie sandbox" : "Local fixture — not live banking data"}
    </div>
  );
}

function StageNavigation({
  current,
  snapshot,
  onNavigate,
}: {
  current: Stage;
  snapshot: CustomerSnapshot | null;
  onNavigate: (stage: Stage) => void;
}) {
  return (
    <nav aria-label="Scenario stages" className="overflow-x-auto pb-1">
      <ol className="flex min-w-max items-center gap-2">
        {stages.map((stage) => {
          const disabled = stage.id > 1 && snapshot === null;
          const active = stage.id === current;
          return (
            <li key={stage.id}>
              <button
                type="button"
                disabled={disabled}
                aria-current={active ? "step" : undefined}
                onClick={() => onNavigate(stage.id)}
                className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                  active
                    ? "bg-slate-950 text-white"
                    : "bg-white text-slate-600 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
                }`}
              >
                <span className="mr-2 font-mono text-xs opacity-60">0{stage.id}</span>
                {stage.short}
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

function StartStage({
  name,
  hourlyWage,
  repairQuote,
  requestState,
  onNameChange,
  onWageChange,
  onRepairChange,
  onSubmit,
}: {
  name: string;
  hourlyWage: string;
  repairQuote: number;
  requestState: RequestState;
  onNameChange: (value: string) => void;
  onWageChange: (value: string) => void;
  onRepairChange: (value: number) => void;
  onSubmit: () => void;
}) {
  const wageCents = wageInputToCents(hourlyWage);
  const preview = wageCents === null ? null : wagePreview(wageCents);
  const nameIsValid = name.trim().length > 0 && name.trim().length <= 80;
  const isValid = nameIsValid && preview !== null;

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isValid) onSubmit();
  }

  return (
    <section className="grid gap-10 py-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:py-16">
      <div>
        <p className="font-mono text-xs font-semibold uppercase tracking-[0.24em] text-orange-600">
          A financial resilience prototype
        </p>
        <h1 className="mt-5 max-w-3xl text-5xl font-semibold leading-[0.98] tracking-[-0.045em] text-slate-950 sm:text-7xl">
          One bad day shouldn&apos;t become a bad month.
        </h1>
        <p className="mt-7 max-w-xl text-lg leading-8 text-slate-600">
          See how a sudden car repair sits beside Maya&apos;s everyday finances—before later
          milestones model the cascade or suggest a way out.
        </p>
        <div className="mt-8 grid max-w-xl grid-cols-3 gap-3">
          {[
            ["5", "shifts / week"],
            ["8h", "each shift"],
            ["40h", "gross week"],
          ].map(([value, label]) => (
            <div key={label} className="rounded-2xl border border-slate-200 bg-white p-4">
              <p className="text-xl font-semibold text-slate-950">{value}</p>
              <p className="mt-1 text-xs text-slate-500">{label}</p>
            </div>
          ))}
        </div>
      </div>

      <form onSubmit={submit} className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/50 sm:p-8">
        <div className="mb-7 flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-orange-600">Build the scenario</p>
            <h2 className="mt-1 text-2xl font-semibold text-slate-950">Start with the facts</h2>
          </div>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">Synthetic profile</span>
        </div>

        <label htmlFor="name" className="block text-sm font-medium text-slate-700">
          Display name
        </label>
        <input
          id="name"
          name="name"
          value={name}
          maxLength={80}
          onChange={(event) => onNameChange(event.target.value)}
          aria-invalid={!nameIsValid}
          className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-950 outline-none transition focus:border-orange-500 focus:ring-4 focus:ring-orange-100"
        />

        <label htmlFor="wage" className="mt-6 block text-sm font-medium text-slate-700">
          Hourly wage <span className="font-normal text-slate-400">($ / hour)</span>
        </label>
        <div className="relative mt-2">
          <span className="absolute left-4 top-3 text-slate-400">$</span>
          <input
            id="wage"
            name="wage"
            type="number"
            inputMode="decimal"
            min="0.01"
            max="500"
            step="0.01"
            value={hourlyWage}
            onChange={(event) => onWageChange(event.target.value)}
            aria-describedby="wage-help"
            aria-invalid={wageCents === null}
            className="w-full rounded-xl border border-slate-300 py-3 pl-8 pr-4 text-slate-950 outline-none transition focus:border-orange-500 focus:ring-4 focus:ring-orange-100"
          />
        </div>
        <p id="wage-help" className="mt-2 text-xs text-slate-500">
          Enter a positive wage up to $500 with at most two decimals.
        </p>

        <div className="mt-6 flex items-center justify-between gap-4">
          <label htmlFor="repair-quote" className="text-sm font-medium text-slate-700">
            Car repair quote
          </label>
          <div className="flex items-center gap-3">
            <span className="text-lg font-semibold text-slate-950">{formatCurrency(repairQuote * 100)}</span>
            <button
              type="button"
              onClick={() => onRepairChange(DEFAULT_REPAIR_QUOTE)}
              className="text-xs font-medium text-slate-500 underline decoration-slate-300 underline-offset-4 hover:text-slate-950"
            >
              Reset
            </button>
          </div>
        </div>
        <input
          id="repair-quote"
          type="range"
          min="100"
          max="1500"
          step="50"
          value={repairQuote}
          onChange={(event) => onRepairChange(Number(event.target.value))}
          className="mt-3 w-full accent-orange-600"
        />
        <div className="mt-1 flex justify-between text-xs text-slate-400">
          <span>$100</span>
          <span>$1,500</span>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-3 rounded-2xl bg-slate-950 p-4 text-white">
          <div>
            <p className="text-xs text-slate-400">Gross / 8h shift</p>
            <p className="mt-1 text-xl font-semibold">
              {preview ? formatCurrency(preview.grossPerShiftCents) : "—"}
            </p>
          </div>
          <div className="border-l border-white/10 pl-4">
            <p className="text-xs text-slate-400">Gross / 40h week</p>
            <p className="mt-1 text-xl font-semibold">
              {preview ? formatCurrency(preview.grossWeeklyCents) : "—"}
            </p>
          </div>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-3 rounded-2xl border border-blue-100 bg-blue-50 p-4 text-blue-950">
          <div>
            <p className="text-xs text-blue-700">Est. take-home / shift</p>
            <p className="mt-1 font-semibold">{preview ? formatCurrency(preview.estimatedNetPerShiftCents) : "—"}</p>
          </div>
          <div className="border-l border-blue-200 pl-4">
            <p className="text-xs text-blue-700">Est. take-home / week</p>
            <p className="mt-1 font-semibold">{preview ? formatCurrency(preview.estimatedNetWeeklyCents) : "—"}</p>
          </div>
        </div>
        <p className="mt-3 text-xs leading-5 text-slate-500">
          Forecast only. Take-home uses a simple 80% planning assumption; neither forecast is a historical bank deposit.
        </p>

        {requestState.kind === "error" ? (
          <div role="alert" className="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            <p className="font-semibold">Couldn&apos;t load the snapshot</p>
            <p className="mt-1">{requestState.message}</p>
          </div>
        ) : null}

        <button
          type="submit"
          disabled={!isValid || requestState.kind === "loading"}
          className="mt-6 w-full rounded-xl bg-orange-600 px-5 py-3.5 font-semibold text-white transition hover:bg-orange-700 focus:outline-none focus:ring-4 focus:ring-orange-200 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {requestState.kind === "loading" ? "Loading customer snapshot…" : "Begin scenario"}
        </button>
      </form>
    </section>
  );
}

function TransactionHistory({ snapshot }: { snapshot: CustomerSnapshot }) {
  const [category, setCategory] = useState("All");
  const [direction, setDirection] = useState("all");
  const [showAll, setShowAll] = useState(false);
  const categories = [...new Set(snapshot.history.transactions.map((item) => item.category))];
  const filtered = snapshot.history.transactions.filter(
    (item) =>
      (category === "All" || item.category === category) &&
      (direction === "all" || item.direction === direction),
  );
  const visible = showAll ? filtered : filtered.slice(0, 12);

  return (
    <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm font-medium text-orange-600">Normalized ledger</p>
          <h2 className="mt-1 text-2xl font-semibold text-slate-950">90-day transaction history</h2>
        </div>
        <div className="flex gap-2">
          <select
            aria-label="Filter transactions by category"
            value={category}
            onChange={(event) => setCategory(event.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-700"
          >
            <option>All</option>
            {categories.map((item) => <option key={item}>{item}</option>)}
          </select>
          <select
            aria-label="Filter transactions by direction"
            value={direction}
            onChange={(event) => setDirection(event.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-700"
          >
            <option value="all">All activity</option>
            <option value="debit">Expenses</option>
            <option value="credit">Income</option>
          </select>
        </div>
      </div>
      {visible.length === 0 ? (
        <p className="mt-6 rounded-xl bg-slate-50 p-5 text-sm text-slate-500">No transactions match these filters.</p>
      ) : (
        <div className="mt-5 divide-y divide-slate-100">
          {visible.map((transaction) => (
            <div key={transaction.id} className="grid grid-cols-[1fr_auto] gap-4 py-3 sm:grid-cols-[1.2fr_0.8fr_auto] sm:items-center">
              <div>
                <p className="text-sm font-medium text-slate-900">
                  {transaction.merchant_display ?? transaction.description ?? "Unknown transaction"}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  {formatDate(transaction.date)} · {transaction.source.replaceAll("_", " ")}
                </p>
              </div>
              <div className="hidden sm:block">
                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600">{transaction.category}</span>
                {transaction.recurring ? <span className="ml-2 text-[10px] font-semibold uppercase text-violet-600">Recurring</span> : null}
              </div>
              <p className={`text-right font-semibold ${transaction.direction === "credit" ? "text-emerald-700" : "text-slate-950"}`}>
                {transaction.direction === "credit" ? "+" : "−"}{formatCurrency(transaction.amount_cents)}
              </p>
            </div>
          ))}
        </div>
      )}
      {filtered.length > 12 ? (
        <button type="button" onClick={() => setShowAll((value) => !value)} className="mt-5 text-sm font-semibold text-orange-700 hover:text-orange-800">
          {showAll ? "Show recent 12" : `Show all ${filtered.length} transactions`}
        </button>
      ) : null}
    </article>
  );
}

function CashFlowOutlook({ snapshot }: { snapshot: CustomerSnapshot }) {
  const points = snapshot.cash_flow.daily_balances;
  const values = points.map((point) => point.projected_balance_cents);
  const minimum = Math.min(...values, 0);
  const maximum = Math.max(...values, 1);
  const span = Math.max(maximum - minimum, 1);
  const coordinates = points
    .map((point, index) => {
      const x = points.length === 1 ? 0 : (index / (points.length - 1)) * 100;
      const y = 92 - ((point.projected_balance_cents - minimum) / span) * 82;
      return `${x},${y}`;
    })
    .join(" ");
  const zeroY = 92 - ((0 - minimum) / span) * 82;

  return (
    <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm font-medium text-orange-600">30-day baseline</p>
          <h2 className="mt-1 text-2xl font-semibold text-slate-950">Cash-flow outlook</h2>
        </div>
        <div className="text-left sm:text-right">
          <p className="text-xs text-slate-500">Ending balance</p>
          <p className="text-xl font-semibold text-slate-950">{formatCurrency(snapshot.cash_flow.ending_balance_cents)}</p>
        </div>
      </div>
      <div className="mt-6 overflow-hidden rounded-2xl bg-slate-950 p-4">
        <svg viewBox="0 0 100 100" role="img" aria-label="Projected daily balance line chart" className="h-48 w-full" preserveAspectRatio="none">
          {minimum < 0 ? <line x1="0" x2="100" y1={zeroY} y2={zeroY} stroke="#fb7185" strokeWidth="0.6" strokeDasharray="2 2" /> : null}
          <polyline points={coordinates} fill="none" stroke="#fb923c" strokeWidth="2" vectorEffect="non-scaling-stroke" />
        </svg>
        <div className="flex justify-between text-[10px] text-slate-400">
          <span>{formatDate(snapshot.cash_flow.start_date)}</span>
          <span>{formatDate(snapshot.cash_flow.end_date)}</span>
        </div>
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-500">Starting</p><p className="mt-1 font-semibold">{formatCurrency(snapshot.cash_flow.starting_balance_cents)}</p></div>
        <div className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-500">Minimum</p><p className={`mt-1 font-semibold ${snapshot.cash_flow.minimum_balance_cents < 0 ? "text-red-700" : ""}`}>{formatCurrency(snapshot.cash_flow.minimum_balance_cents)}</p></div>
        <div className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-500">Peak shortfall</p><p className="mt-1 font-semibold text-red-700">{formatCurrency(snapshot.cash_flow.peak_cash_shortfall_cents)}</p></div>
      </div>
      <div className="mt-5 space-y-2">
        {snapshot.cash_flow.events.map((event, index) => (
          <div key={`${event.date}-${event.name}-${index}`} className="flex items-center justify-between gap-4 text-sm">
            <div><span className="font-medium text-slate-800">{event.name}</span><span className="ml-2 text-xs text-slate-400">{formatDate(event.date)}</span></div>
            <span className={event.direction === "income" ? "text-emerald-700" : "text-slate-700"}>{event.direction === "income" ? "+" : "−"}{formatCurrency(event.amount_cents)}</span>
          </div>
        ))}
      </div>
      <p className="mt-5 border-t border-slate-100 pt-4 text-xs leading-5 text-slate-500">{snapshot.cash_flow.assumption}</p>
    </article>
  );
}

function SnapshotStage({
  snapshot,
  requestState,
  onRefresh,
  onBack,
  onNext,
}: {
  snapshot: CustomerSnapshot;
  requestState: RequestState;
  onRefresh: () => void;
  onBack: () => void;
  onNext: () => void;
}) {
  const refreshing = requestState.kind === "loading";
  const balance = snapshot.accounts.reduce((total, account) => total + account.balance_cents, 0);
  const maxCategory = Math.max(...snapshot.history.categories.map((item) => item.total_cents), 1);
  const depositCount = snapshot.history.transactions.filter((item) => item.direction === "credit").length;
  const essentialSpend = snapshot.history.categories
    .filter((item) => item.essential)
    .reduce((total, item) => total + item.total_cents, 0);
  const discretionarySpend = snapshot.history.spending_total_cents - essentialSpend;

  return (
    <section className="py-8">
      <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <DataBadge snapshot={snapshot} />
          <h1 className="mt-4 text-4xl font-semibold tracking-tight text-slate-950">
            {snapshot.customer.display_name}&apos;s financial snapshot
          </h1>
          <p className="mt-2 text-sm font-medium text-slate-500">
            Age {snapshot.customer.age} · {snapshot.customer.occupation} · {snapshot.customer.city}
          </p>
          <p className="mt-2 max-w-3xl text-slate-600">{snapshot.source.message}</p>
        </div>
        <button
          type="button"
          onClick={onRefresh}
          disabled={refreshing}
          className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          {refreshing ? "Refreshing…" : "Refresh snapshot"}
        </button>
      </div>

      <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ["Current balance", formatCurrency(balance), snapshot.source.banking === "nessie" ? "Read from Nessie" : "Fixture balance"],
          ["Repair quote", formatCurrency(snapshot.scenario.repair_quote_cents), "Scenario input · not paid"],
          ["Gross weekly forecast", formatCurrency(snapshot.income_projection.gross_weekly_cents), "40 hours × entered rate"],
          ["90-day spending", formatCurrency(snapshot.history.spending_total_cents), `${snapshot.history.categories.length} categories`],
        ].map(([label, value, note]) => (
          <article key={label} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
            <p className="mt-3 text-2xl font-semibold text-slate-950">{value}</p>
            <p className="mt-2 text-xs text-slate-500">{note}</p>
          </article>
        ))}
      </div>

      {requestState.kind === "error" ? (
        <div role="alert" className="mt-6 flex flex-col justify-between gap-3 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800 sm:flex-row sm:items-center">
          <div>
            <p className="font-semibold">Refresh failed</p>
            <p className="mt-1">{requestState.message} The last successful snapshot remains visible.</p>
          </div>
          <button type="button" onClick={onRefresh} className="rounded-lg bg-red-700 px-4 py-2 font-semibold text-white hover:bg-red-800">
            Retry
          </button>
        </div>
      ) : null}

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
        <div className="space-y-6">
          <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-orange-600">Historical facts</p>
                <h2 className="mt-1 text-2xl font-semibold text-slate-950">Where money went</h2>
              </div>
              <p className="text-xs text-slate-500">
                {formatDate(snapshot.history.start)}–{formatDate(snapshot.history.end)} · monthly avg ≈ total ÷ 3
              </p>
            </div>
            {snapshot.history.categories.length === 0 ? (
              <div className="mt-6 rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
                No purchase history was returned for this 90-day window.
              </div>
            ) : (
              <div className="mt-7 space-y-5">
                {snapshot.history.categories.map((item) => (
                  <div key={item.category}>
                    <div className="flex items-end justify-between gap-4">
                      <div>
                        <p className="text-sm font-medium text-slate-800">{item.category}</p>
                        <p className="text-xs text-slate-400">
                          {item.transaction_count} transactions · {item.percentage.toFixed(1)}% · {item.essential ? "essential" : "discretionary"}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-semibold text-slate-950">{formatCurrency(item.total_cents)}</p>
                        <p className="text-xs text-slate-400">≈ {formatCurrency(item.monthly_average_cents)} / mo</p>
                      </div>
                    </div>
                    <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
                      <div
                        className={`h-full rounded-full ${categoryColors[item.category] ?? "bg-slate-400"}`}
                        style={{ width: `${Math.max(4, (item.total_cents / maxCategory) * 100)}%` }}
                      />
                    </div>
                    <p className="mt-2 text-xs text-slate-400">
                      Recurring {formatCurrency(item.recurring_cents)} · irregular {formatCurrency(item.irregular_cents)}
                    </p>
                  </div>
                ))}
              </div>
            )}
            <div className="mt-7 border-t border-slate-100 pt-5 text-xs leading-5 text-slate-500">
              Essential {formatCurrency(essentialSpend)} · discretionary {formatCurrency(discretionarySpend)}. {" "}
              Historical deposits remain separate from spending totals. This window contains {depositCount} recorded
              deposit{depositCount === 1 ? "" : "s"}; future wages below are a forecast, not another deposit.
            </div>
          </article>

          <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-950">Accounts</h2>
            <div className="mt-4 divide-y divide-slate-100">
              {snapshot.accounts.map((account) => (
                <div key={account.id} className="flex items-center justify-between gap-4 py-4 first:pt-0 last:pb-0">
                  <div>
                    <p className="font-medium text-slate-900">{account.nickname ?? account.type}</p>
                    <p className="mt-1 text-xs text-slate-500">{account.type} · {account.source}</p>
                  </div>
                  <p className="text-lg font-semibold text-slate-950">{formatCurrency(account.balance_cents)}</p>
                </div>
              ))}
            </div>
          </article>
        </div>

        <div className="space-y-6">
          <article className="overflow-hidden rounded-3xl border border-slate-800 bg-slate-950 p-6 text-white shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <span className="rounded-full bg-white/10 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-orange-300">
                  Preview
                </span>
                <h2 className="mt-4 text-2xl font-semibold">Untreated cascade graph</h2>
              </div>
              <span className="font-mono text-xs text-slate-500">Build Sheet 02</span>
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              A later milestone will calculate dated consequences. Nothing here is active or analyzed yet.
            </p>
            <div className="relative mt-7 space-y-3 before:absolute before:bottom-5 before:left-[15px] before:top-5 before:w-px before:bg-slate-700">
              {["Car breaks down", "Commute may be disrupted", "Shifts and bills could be threatened"].map((label, index) => (
                <div key={label} className="relative flex items-center gap-4 rounded-2xl border border-white/10 bg-white/[0.04] p-3">
                  <span className="z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-800 font-mono text-xs text-slate-300">
                    {index + 1}
                  </span>
                  <span className="text-sm text-slate-200">{label}</span>
                </div>
              ))}
            </div>
            <p className="mt-5 rounded-xl bg-amber-400/10 p-3 text-xs leading-5 text-amber-200">
              Full financial cascade in Build Sheet 02. The repair quote is not treated as paid.
            </p>
          </article>

          <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between gap-4">
              <h2 className="text-xl font-semibold text-slate-950">Upcoming payments</h2>
              <span className="text-xs text-slate-400">Dated obligations</span>
            </div>
            {snapshot.upcoming_bills.length === 0 ? (
              <p className="mt-5 rounded-xl bg-slate-50 p-4 text-sm text-slate-500">No upcoming payments are scheduled.</p>
            ) : (
              <div className="mt-4 divide-y divide-slate-100">
                {snapshot.upcoming_bills.map((bill) => (
                  <div key={`${bill.source}-${bill.id}`} className="flex items-center justify-between gap-4 py-4">
                    <div>
                      <p className="font-medium text-slate-900">{bill.name}</p>
                      <p className="mt-1 text-xs text-slate-500">
                        Due {formatDate(bill.due_date)} ({daysBetween(snapshot.cash_flow.start_date, bill.due_date)} days) · {bill.status}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">{bill.category} · {bill.essential ? "essential" : "discretionary"}</p>
                      <span className="mt-2 inline-block rounded bg-slate-100 px-2 py-0.5 font-mono text-[10px] text-slate-500">
                        {bill.source}
                      </span>
                    </div>
                    <p className="font-semibold text-slate-950">{formatCurrency(bill.amount_cents)}</p>
                  </div>
                ))}
              </div>
            )}
          </article>

          <article className="rounded-3xl border border-blue-200 bg-blue-50 p-6">
            <p className="text-sm font-semibold text-blue-900">Upcoming income forecast</p>
            <p className="mt-2 text-3xl font-semibold text-blue-950">
              {formatCurrency(snapshot.income_projection.estimated_net_weekly_cents)}
              <span className="ml-2 text-sm font-normal text-blue-700">estimated take-home / week</span>
            </p>
            <p className="mt-3 text-sm leading-6 text-blue-800">
              Five 8-hour shifts at {formatCurrency(snapshot.income_projection.hourly_rate_cents)}/hr.
              Gross per shift: {formatCurrency(snapshot.income_projection.gross_per_shift_cents)}.
            </p>
            <div className="mt-4 divide-y divide-blue-100 rounded-xl border border-blue-100 bg-white px-4">
              {snapshot.income_projection.forecast_entries.map((entry) => (
                <div key={entry.expected_payment_date} className="flex items-center justify-between gap-4 py-3 text-xs text-blue-900">
                  <div>
                    <p className="font-semibold">Pay date {formatDate(entry.expected_payment_date)}</p>
                    <p className="mt-1 text-blue-600">Work period {formatDate(entry.work_period_start)}–{formatDate(entry.work_period_end)}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold">{formatCurrency(entry.estimated_take_home_cents)} net est.</p>
                    <p className="mt-1 text-blue-600">{formatCurrency(entry.gross_amount_cents)} gross</p>
                  </div>
                </div>
              ))}
            </div>
            <p className="mt-4 text-xs leading-5 text-blue-700">
              User-wage forecast only. Estimated take-home is 80% of gross and is not a recorded Nessie deposit.
            </p>
          </article>
        </div>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        <TransactionHistory snapshot={snapshot} />
        <CashFlowOutlook snapshot={snapshot} />
      </div>

      <div className="mt-8 flex flex-col-reverse justify-between gap-3 sm:flex-row">
        <button type="button" onClick={onBack} className="rounded-xl border border-slate-300 bg-white px-5 py-3 font-semibold text-slate-700 hover:bg-slate-50">
          ← Adjust inputs
        </button>
        <button type="button" onClick={onNext} className="rounded-xl bg-slate-950 px-5 py-3 font-semibold text-white hover:bg-slate-800">
          Preview future research →
        </button>
      </div>
    </section>
  );
}

function ResearchPreview({ onBack, onNext }: { onBack: () => void; onNext: () => void }) {
  return (
    <section className="py-10">
      <div className="rounded-[2rem] border border-slate-200 bg-white p-7 shadow-sm sm:p-10">
        <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-amber-900">
          Demo preview — not an active agent
        </span>
        <div className="mt-6 grid gap-10 lg:grid-cols-[0.9fr_1.1fr]">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-orange-600">Stage 03</p>
            <h1 className="mt-3 text-4xl font-semibold tracking-tight text-slate-950">Finding a way out</h1>
            <p className="mt-4 text-lg leading-8 text-slate-600">
              Later, a bounded agent will investigate options without pretending a listing guarantees price,
              availability, employer approval, or assistance eligibility.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {[
              ["Transportation", "Can the commute be protected without worsening the cash gap?"],
              ["Attendance", "Which work arrangements are actually available?"],
              ["Repair affordability", "What prices, timing, and payment terms are verified?"],
              ["Bill flexibility", "Which obligations have real, documented options?"],
            ].map(([title, copy]) => (
              <article key={title} className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                <h2 className="font-semibold text-slate-950">{title}</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">{copy}</p>
              </article>
            ))}
          </div>
        </div>
        <div className="mt-8 rounded-2xl border border-dashed border-orange-300 bg-orange-50 p-6">
          <p className="text-xs font-semibold uppercase tracking-wide text-orange-800">Sample question layout · preview only</p>
          <p className="mt-3 text-lg font-medium text-slate-950">Would working remotely be permitted for any threatened shift?</p>
          <p className="mt-2 text-sm text-slate-600">No answer is collected and no agent has asked this question in Build Sheet 01.</p>
        </div>
      </div>
      <div className="mt-8 flex flex-col-reverse justify-between gap-3 sm:flex-row">
        <button type="button" onClick={onBack} className="rounded-xl border border-slate-300 bg-white px-5 py-3 font-semibold text-slate-700 hover:bg-slate-50">← Back to snapshot</button>
        <button type="button" onClick={onNext} className="rounded-xl bg-slate-950 px-5 py-3 font-semibold text-white hover:bg-slate-800">Preview plan layout →</button>
      </div>
    </section>
  );
}

function PlanPreview({ onBack, onAdjust, onRestart }: { onBack: () => void; onAdjust: () => void; onRestart: () => void }) {
  return (
    <section className="py-10">
      <div className="rounded-[2rem] border border-slate-800 bg-slate-950 p-7 text-white shadow-xl sm:p-10">
        <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-300">
          Preview only · no recommendation generated
        </span>
        <div className="mt-6 max-w-3xl">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-orange-300">Stage 04</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">A coordinated plan will live here.</h1>
          <p className="mt-5 text-lg leading-8 text-slate-300">
            Build Sheet 04 will compare two or three plans by feasibility, bills protected, cash position,
            evidence, assumptions, and unresolved risk. This milestone does not rank or recommend actions.
          </p>
        </div>
        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {["Plan actions", "Cash + bills", "Evidence + risks"].map((title, index) => (
            <div key={title} className="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
              <span className="font-mono text-xs text-slate-500">0{index + 1}</span>
              <h2 className="mt-4 font-semibold text-slate-200">{title}</h2>
              <div className="mt-4 space-y-2" aria-hidden="true">
                <div className="h-2 w-full rounded bg-white/10" />
                <div className="h-2 w-4/5 rounded bg-white/10" />
                <div className="h-2 w-2/3 rounded bg-white/10" />
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:justify-between">
        <button type="button" onClick={onBack} className="rounded-xl border border-slate-300 bg-white px-5 py-3 font-semibold text-slate-700 hover:bg-slate-50">← Back to research preview</button>
        <div className="flex flex-col gap-3 sm:flex-row">
          <button type="button" onClick={onAdjust} className="rounded-xl border border-slate-300 bg-white px-5 py-3 font-semibold text-slate-700 hover:bg-slate-50">Adjust inputs</button>
          <button type="button" onClick={onRestart} className="rounded-xl bg-orange-600 px-5 py-3 font-semibold text-white hover:bg-orange-700">Restart scenario</button>
        </div>
      </div>
    </section>
  );
}

export default function ScenarioApp() {
  const [stage, setStage] = useState<Stage>(1);
  const [name, setName] = useState("Maya Rodriguez");
  const [hourlyWage, setHourlyWage] = useState(DEFAULT_HOURLY_WAGE);
  const [repairQuote, setRepairQuote] = useState(DEFAULT_REPAIR_QUOTE);
  const [snapshot, setSnapshot] = useState<CustomerSnapshot | null>(null);
  const [requestState, setRequestState] = useState<RequestState>({ kind: "idle" });

  const snapshotQuery = useMemo(() => {
    const hourlyRateCents = wageInputToCents(hourlyWage);
    if (hourlyRateCents === null || !name.trim()) return null;
    return new URLSearchParams({
      display_name: name.trim(),
      hourly_rate_cents: String(hourlyRateCents),
      repair_quote_cents: String(repairQuote * 100),
    });
  }, [hourlyWage, name, repairQuote]);

  async function loadSnapshot() {
    if (snapshotQuery === null) return;
    setRequestState({ kind: "loading" });
    try {
      const response = await fetch(`/api/customer/snapshot?${snapshotQuery.toString()}`, {
        cache: "no-store",
      });
      const body = (await response.json()) as CustomerSnapshot | { message?: string };
      if (!response.ok) {
        throw new Error("message" in body && body.message ? body.message : "Snapshot request failed.");
      }
      setSnapshot(body as CustomerSnapshot);
      setRequestState({ kind: "idle" });
      setStage(2);
    } catch (error) {
      setRequestState({
        kind: "error",
        message: error instanceof Error ? error.message : "Snapshot request failed.",
      });
    }
  }

  function restart() {
    setName("Maya Rodriguez");
    setHourlyWage(DEFAULT_HOURLY_WAGE);
    setRepairQuote(DEFAULT_REPAIR_QUOTE);
    setSnapshot(null);
    setRequestState({ kind: "idle" });
    setStage(1);
  }

  return (
    <main className="min-h-screen bg-[#f6f5f1] text-slate-950">
      <header className="border-b border-slate-200/80 bg-[#f6f5f1]/95">
        <div className="mx-auto flex max-w-7xl flex-col gap-5 px-5 py-5 sm:px-8 lg:flex-row lg:items-center lg:justify-between">
          <button type="button" onClick={() => setStage(1)} className="w-fit text-left">
            <span className="block font-mono text-[10px] font-semibold uppercase tracking-[0.24em] text-orange-600">HackTX 2026</span>
            <span className="mt-1 block text-lg font-semibold tracking-tight">One Bad Tuesday</span>
          </button>
          <StageNavigation current={stage} snapshot={snapshot} onNavigate={setStage} />
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        {stage === 1 ? (
          <StartStage
            name={name}
            hourlyWage={hourlyWage}
            repairQuote={repairQuote}
            requestState={requestState}
            onNameChange={setName}
            onWageChange={setHourlyWage}
            onRepairChange={setRepairQuote}
            onSubmit={() => void loadSnapshot()}
          />
        ) : null}
        {stage === 2 && snapshot ? (
          <SnapshotStage
            snapshot={snapshot}
            requestState={requestState}
            onRefresh={() => void loadSnapshot()}
            onBack={() => setStage(1)}
            onNext={() => setStage(3)}
          />
        ) : null}
        {stage === 3 && snapshot ? <ResearchPreview onBack={() => setStage(2)} onNext={() => setStage(4)} /> : null}
        {stage === 4 && snapshot ? <PlanPreview onBack={() => setStage(3)} onAdjust={() => setStage(1)} onRestart={restart} /> : null}
      </div>

      <footer className="border-t border-slate-200 px-5 py-6 text-center text-xs leading-5 text-slate-500">
        Synthetic finances for a HackTX prototype. No real bank connection, payment, lending, research agent, or recommendation.
      </footer>
    </main>
  );
}
