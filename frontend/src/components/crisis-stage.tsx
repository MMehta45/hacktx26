"use client";

import { CrisisGraph } from "@/components/crisis-graph";
import { formatCurrency, formatDate } from "@/lib/scenario";
import type { CustomerSnapshot } from "@/types/customer";
import type { CrisisSimulation } from "@/types/simulation";

function BalanceComparison({ simulation }: { simulation: CrisisSimulation }) {
  const values = simulation.cashflow.flatMap((point) => [
    point.normal_balance_cents,
    point.crisis_balance_cents,
  ]);
  const minimum = Math.min(...values, 0);
  const maximum = Math.max(...values, 1);
  const span = Math.max(maximum - minimum, 1);
  const coordinates = (key: "normal_balance_cents" | "crisis_balance_cents") =>
    simulation.cashflow
      .map((point, index) => {
        const x = (index / Math.max(simulation.cashflow.length - 1, 1)) * 100;
        const y = 91 - ((point[key] - minimum) / span) * 80;
        return `${x},${y}`;
      })
      .join(" ");
  const zeroY = 91 - ((0 - minimum) / span) * 80;

  return (
    <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="font-brand text-sm text-[#4B5480]">30-day comparison</p>
          <h2 className="mt-1 text-2xl font-semibold text-slate-950">Normal vs untreated cash flow</h2>
        </div>
        <div className="flex gap-4 text-xs text-slate-600">
          <span className="flex items-center gap-2"><i className="h-0.5 w-5 bg-[#1FBFA7]" />Normal</span>
          <span className="flex items-center gap-2"><i className="h-0.5 w-5 bg-[#4B5480]" />Crisis</span>
        </div>
      </div>
      <div className="mt-5 rounded-2xl bg-slate-950 p-4">
        <svg
          viewBox="0 0 100 100"
          role="img"
          aria-label="Normal and untreated crisis projected balances over 30 days"
          className="h-64 w-full"
          preserveAspectRatio="none"
        >
          <line x1="0" x2="100" y1={zeroY} y2={zeroY} stroke="#FFF3D8" strokeWidth="0.7" strokeDasharray="2 2" />
          <polyline points={coordinates("normal_balance_cents")} fill="none" stroke="#1FBFA7" strokeWidth="2" vectorEffect="non-scaling-stroke" />
          <polyline points={coordinates("crisis_balance_cents")} fill="none" stroke="#8f9ac9" strokeWidth="2.4" vectorEffect="non-scaling-stroke" />
        </svg>
        <div className="flex justify-between text-[10px] text-slate-400">
          <span>{formatDate(simulation.scenario.scenario_start_date)}</span>
          <span>Zero-dollar line</span>
          <span>{formatDate(simulation.scenario.forecast_end_date)}</span>
        </div>
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl bg-[#1FBFA7]/10 p-3">
          <p className="text-xs text-[#4B5480]">Normal ending</p>
          <p className="mt-1 font-semibold text-[#1A2122]">{formatCurrency(simulation.normal_ending_balance_cents)}</p>
        </div>
        <div className="rounded-xl bg-[#4B5480]/10 p-3">
          <p className="text-xs text-[#4B5480]">Projected crisis ending</p>
          <p className="mt-1 font-semibold text-[#1A2122]">{formatCurrency(simulation.crisis_ending_balance_cents)}</p>
        </div>
        <div className="rounded-xl bg-blue-50 p-3">
          <p className="text-xs text-blue-700">Constrained cash</p>
          <p className="mt-1 font-semibold text-blue-950">{formatCurrency(simulation.constrained_ending_cash_cents)}</p>
        </div>
      </div>
      <p className="mt-4 text-xs leading-5 text-slate-500">
        Raw negative values measure required funding. The constrained ledger never treats an
        unfunded bill as paid and never claims the Nessie account actually overdrafted.
      </p>
    </article>
  );
}

function EventLedger({ simulation }: { simulation: CrisisSimulation }) {
  return (
    <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <p className="font-brand text-sm text-[#4B5480]">What changes, and when</p>
      <h2 className="mt-1 text-2xl font-semibold text-slate-950">Projection event ledger</h2>
      <div className="mt-5 max-h-[30rem] divide-y divide-slate-100 overflow-y-auto pr-1">
        {simulation.events.map((event) => (
          <div key={event.id} className="grid grid-cols-[1fr_auto] gap-4 py-3">
            <div>
              <p className="text-sm font-medium text-slate-900">{event.description}</p>
              <p className="mt-1 text-xs text-slate-500">
                {formatDate(event.date)} · {event.type.replaceAll("_", " ")} · {event.source.replaceAll("_", " ")}
              </p>
            </div>
            <p className={`text-right font-semibold ${event.signed_amount_cents >= 0 ? "text-[#1FBFA7]" : "text-slate-950"}`}>
              {event.signed_amount_cents >= 0 ? "+" : "−"}{formatCurrency(Math.abs(event.signed_amount_cents))}
            </p>
          </div>
        ))}
      </div>
    </article>
  );
}

function BankingContext({ snapshot }: { snapshot: CustomerSnapshot }) {
  return (
    <details className="rounded-3xl border border-slate-200 bg-white shadow-sm">
      <summary className="cursor-pointer list-none p-6">
        <p className="font-brand text-sm text-[#4B5480]">Banking details</p>
        <div className="mt-1 flex items-center justify-between gap-4">
          <h2 className="text-2xl font-semibold text-slate-950">Accounts, spending, bills and history</h2>
          <span className="text-sm font-semibold text-slate-500">Open details ↓</span>
        </div>
      </summary>
      <div className="grid gap-6 border-t border-slate-100 p-6 xl:grid-cols-2">
        <section>
          <h3 className="font-semibold text-slate-950">90-day spending</h3>
          <p className="mt-1 text-sm text-slate-500">{formatCurrency(snapshot.history.spending_total_cents)} total; averages are context only.</p>
          <div className="mt-4 space-y-3">
            {snapshot.history.categories.map((item) => (
              <div key={item.category} className="rounded-xl bg-slate-50 p-3">
                <div className="flex justify-between gap-4 text-sm">
                  <span className="font-medium">{item.category}</span>
                  <span className="font-semibold">{formatCurrency(item.total_cents)}</span>
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  {item.transaction_count} transactions · {formatCurrency(item.monthly_average_cents)}/mo · {item.percentage.toFixed(1)}%
                </p>
              </div>
            ))}
          </div>
        </section>
        <section>
          <h3 className="font-semibold text-slate-950">Accounts and upcoming schedule</h3>
          <div className="mt-4 space-y-3">
            {snapshot.accounts.map((account) => (
              <div key={account.id} className="flex justify-between rounded-xl bg-slate-950 p-4 text-white">
                <div><p className="font-medium">{account.nickname ?? account.type}</p><p className="mt-1 text-xs text-slate-400">{account.type} · {account.source}</p></div>
                <p className="font-semibold">{formatCurrency(account.balance_cents)}</p>
              </div>
            ))}
            {snapshot.upcoming_bills.map((item) => (
              <div key={`${item.source}-${item.id}`} className="flex justify-between rounded-xl border border-slate-200 p-3">
                <div><p className="text-sm font-medium">{item.name}</p><p className="mt-1 text-xs text-slate-500">Due {formatDate(item.due_date)} · {item.source.replaceAll("_", " ")}</p></div>
                <p className="text-sm font-semibold">{formatCurrency(item.amount_cents)}</p>
              </div>
            ))}
          </div>
        </section>
        <section className="xl:col-span-2">
          <h3 className="font-semibold text-slate-950">Normalized 90-day transaction history</h3>
          <div className="mt-4 max-h-96 divide-y divide-slate-100 overflow-y-auto rounded-xl border border-slate-200 px-4">
            {snapshot.history.transactions.map((item) => (
              <div key={item.id} className="grid grid-cols-[1fr_auto] gap-4 py-3 sm:grid-cols-[1.2fr_0.8fr_auto]">
                <div><p className="text-sm font-medium">{item.merchant_display ?? item.description ?? "Transaction"}</p><p className="mt-1 text-xs text-slate-500">{formatDate(item.date)} · {item.source.replaceAll("_", " ")}</p></div>
                <p className="hidden text-xs text-slate-500 sm:block">{item.category}{item.recurring ? " · recurring" : ""}</p>
                <p className={`text-right text-sm font-semibold ${item.direction === "credit" ? "text-[#1FBFA7]" : ""}`}>{item.direction === "credit" ? "+" : "−"}{formatCurrency(item.amount_cents)}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </details>
  );
}

export function CrisisStage({
  snapshot,
  simulation,
  error,
  onBack,
  onNext,
}: {
  snapshot: CustomerSnapshot;
  simulation: CrisisSimulation;
  repairQuote: number;
  loading: boolean;
  error: string | null;
  onRepairChange: (value: number) => void;
  onRerun: () => void;
  onBack: () => void;
  onNext: () => void;
}) {
  const lostTakeHome = simulation.income_lost_by_payday.reduce(
    (total, item) => total + item.take_home_lost_cents,
    0,
  );
  const live = simulation.source.banking_mode === "live";
  const missedShifts = simulation.shift_records.filter((shift) => shift.attendance === "projected_missed");
  const repair = simulation.repair_projection;

  return (
    <section className="py-8">
      <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
        <div>
          <span className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold ${live ? "border-[#1FBFA7]/30 bg-[#1FBFA7]/10 text-[#1A2122]" : "border-[#4B5480]/25 bg-[#4B5480]/10 text-[#4B5480]"}`}>
            {live ? "Live Nessie balance + projected crisis" : "Fixture balance + projected crisis"}
          </span>
          <p className="font-brand mt-4 text-sm text-[#4B5480]">Stage 02 · The ripple effect</p>
          <h1 className="font-display mt-2 text-4xl tracking-tight text-[#1A2122] sm:text-5xl">See what happens if nothing changes</h1>
          <p className="mt-3 max-w-3xl text-[#4B5480]">Here&apos;s how Maya&apos;s finances could change over the next 30 days.</p>
        </div>
        <button type="button" onClick={onBack} className="rounded-xl border border-[#4B5480]/25 bg-white/70 px-4 py-2.5 text-sm font-semibold text-[#4B5480] hover:bg-white">Edit situation</button>
      </div>

      <div className="mt-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {[
          ["Live current balance", formatCurrency(simulation.source.current_balance_cents), live ? "Nessie sandbox" : "Fixture fallback"],
          ["Repair projection", formatCurrency(simulation.scenario.repair_quote_cents), repair.modeled_payment_date ? `Modeled ${formatDate(repair.modeled_payment_date)}` : "Unresolved · $0 deducted"],
          ["Lost take-home", formatCurrency(lostTakeHome), `${missedShifts.length} calculated missed 8h shifts · 80% estimate`],
          ["Peak raw gap", formatCurrency(simulation.peak_funding_gap_cents), "Required funding, not an overdraft"],
          ["Essential bills unpaid", formatCurrency(simulation.unpaid_essential_total_cents), `${simulation.unpaid_bills.length} projected obligation(s)`],
        ].map(([label, value, note]) => (
          <article key={label} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
            <p className="mt-3 text-2xl font-semibold text-slate-950">{value}</p>
            <p className="mt-2 text-xs leading-5 text-slate-500">{note}</p>
          </article>
        ))}
      </div>

      {error ? <div role="alert" className="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div> : null}
      {simulation.warnings.length ? <details className="mt-5 rounded-xl bg-[#4B5480]/10 p-4 text-sm text-[#4B5480]"><summary className="cursor-pointer font-semibold">Forecast notes</summary>{simulation.warnings.map((warning) => <p className="mt-2" key={warning}>{warning}</p>)}</details> : null}

      <div className="mt-8"><CrisisGraph simulation={simulation} /></div>

      <details className="mt-6 rounded-3xl border border-[#4B5480]/15 bg-white/70">
        <summary className="cursor-pointer list-none p-6"><div className="flex items-center justify-between gap-4"><div><p className="font-brand text-sm text-[#4B5480]">Behind the forecast</p><h2 className="font-display mt-1 text-2xl">Shifts, payroll and repair timing</h2></div><span className="text-sm font-semibold text-[#4B5480]">Open details ↓</span></div></summary>
      <div className="grid gap-6 border-t border-[#4B5480]/10 p-6 xl:grid-cols-2">
        <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="font-brand text-sm text-[#4B5480]">Your work calendar</p>
          <h2 className="mt-1 text-2xl font-semibold text-slate-950">Scheduled shifts</h2>
          <div className="mt-4 max-h-72 divide-y divide-slate-100 overflow-y-auto">
            {simulation.shift_records.map((shift) => <div key={shift.id} className="flex items-center justify-between gap-4 py-3"><div><p className="text-sm font-semibold text-slate-900">{formatDate(shift.date)} · 08:00–16:00</p><p className="mt-1 text-xs text-slate-500">Paid {formatDate(shift.associated_payday)} · {shift.reason}</p></div><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${shift.attendance === "worked" ? "bg-[#1FBFA7]/10 text-[#1A2122]" : "bg-[#4B5480]/10 text-[#4B5480]"}`}>{shift.attendance.replaceAll("_", " ")}</span></div>)}
          </div>
        </article>
        <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="font-brand text-sm text-[#4B5480]">When pay arrives</p>
          <h2 className="mt-1 text-2xl font-semibold text-slate-950">Friday paychecks</h2>
          <div className="mt-4 max-h-72 divide-y divide-slate-100 overflow-y-auto">
            {simulation.payroll_records.map((payroll) => <div key={payroll.id} className="py-3"><div className="flex justify-between gap-4"><p className="text-sm font-semibold text-slate-900">{formatDate(payroll.payday)}</p><p className="text-sm font-semibold text-slate-900">{formatCurrency(payroll.actual_projected_take_home_cents)}</p></div><p className="mt-1 text-xs text-slate-500">Work {formatDate(payroll.work_period_start)}–{formatDate(payroll.work_period_end)} · {payroll.worked_shift_count} worked / {payroll.missed_shift_count} missed · {formatCurrency(payroll.lost_take_home_cents)} lost</p></div>)}
          </div>
          <div className="mt-4 rounded-xl bg-slate-50 p-4 text-sm text-slate-700"><p className="font-semibold">Repair: {repair.funding_status.replaceAll("_", " ")}</p><p className="mt-1 text-xs leading-5 text-slate-500">{repair.blocked_reason ?? `${formatCurrency(repair.quote_cents)} is modeled once on ${formatDate(repair.modeled_payment_date!)} after protected bills.`}</p></div>
        </article>
      </div>
      </details>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <BalanceComparison simulation={simulation} />
        <EventLedger simulation={simulation} />
      </div>

      <article className="mt-6 rounded-3xl border border-red-200 bg-red-50 p-6">
        <p className="text-sm font-medium text-red-700">Constrained due-date allocation</p>
        <h2 className="mt-1 text-2xl font-semibold text-red-950">Projected bills at risk</h2>
        {simulation.unpaid_bills.length ? (
          <div className="mt-5 grid gap-3 md:grid-cols-2">
            {simulation.unpaid_bills.map((item) => (
              <div key={item.obligation_id} className="rounded-2xl border border-red-200 bg-white p-4">
                <div className="flex justify-between gap-4"><h3 className="font-semibold text-slate-950">{item.name}</h3><p className="font-semibold text-red-700">{formatCurrency(item.unpaid_cents)} uncovered</p></div>
                <p className="mt-2 text-xs text-slate-500">Due {formatDate(item.due_date)} · {formatCurrency(item.funded_cents)} funded of {formatCurrency(item.amount_cents)} · priority {item.payment_priority}</p>
              </div>
            ))}
          </div>
        ) : <p className="mt-4 text-sm text-red-900">Every essential bill can be funded on its due date under these inputs.</p>}
        <p className="mt-4 text-xs leading-5 text-red-800">Paychecks are processed first each day; essential bills precede discretionary bills, then IDs break same-day ties. Unpaid amounts remain obligations and are not deducted as if paid.</p>
      </article>

      <div className="mt-6"><BankingContext snapshot={snapshot} /></div>

      <div className="mt-8 flex flex-col-reverse justify-between gap-3 sm:flex-row">
        <button type="button" onClick={onBack} className="rounded-xl border border-slate-300 bg-white px-5 py-3 font-semibold text-slate-700 hover:bg-slate-50">← Adjust scenario</button>
        <button type="button" onClick={onNext} className="rounded-xl bg-slate-950 px-5 py-3 font-semibold text-white hover:bg-slate-800">Preview future research →</button>
      </div>
    </section>
  );
}
