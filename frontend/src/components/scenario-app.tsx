"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { CrisisStage } from "@/components/crisis-stage";
import { ResearchStage } from "@/components/research-stage";
import { RecoveryStage } from "@/components/recovery-stage";
import {
  DEFAULT_HOURLY_WAGE,
  DEFAULT_REPAIR_QUOTE,
  formatCurrency,
  wageInputToCents,
  wagePreview,
} from "@/lib/scenario";
import { AUSTIN_DEMO_CONTEXT, filterUnsupportedMechanicRecommendations, researchRequestBody } from "@/lib/research";
import type { CustomerSnapshot } from "@/types/customer";
import type { CrisisSimulation, CrisisSimulationResponse } from "@/types/simulation";
import type { ResearchResponse, ResearchResult } from "@/types/research";
import type { CreateRecoverySessionBody } from "@/types/recovery";

type Stage = 1 | 2 | 3 | 4;
type RequestState = { kind: "idle" } | { kind: "loading" } | { kind: "error"; message: string };

const stages: Array<{ id: Stage; short: string; label: string }> = [
  { id: 1, short: "Your situation", label: "Your situation" },
  { id: 2, short: "The ripple effect", label: "The ripple effect" },
  { id: 3, short: "Preparing recovery", label: "Preparing your recovery" },
  { id: 4, short: "Your recovery plan", label: "Your recovery plan" },
];

function todayInChicago() {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Chicago", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date());
  const value = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${value.year}-${value.month}-${value.day}`;
}

function DataBadge({ snapshot }: { snapshot: CustomerSnapshot }) {
  const live = snapshot.source.mode === "live";
  return (
    <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold ${live ? "border-[#1FBFA7]/30 bg-[#1FBFA7]/10 text-[#1A2122]" : "border-[#4B5480]/25 bg-[#4B5480]/10 text-[#4B5480]"}`}>
      <i className={`h-2 w-2 rounded-full ${live ? "bg-[#1FBFA7]" : "bg-[#4B5480]"}`} />
      {live ? "Live Nessie sandbox" : "Local fixture — not live banking data"}
    </span>
  );
}

function StageNavigation({ current, simulation, hasResearch, onNavigate }: { current: Stage; simulation: CrisisSimulation | null; hasResearch: boolean; onNavigate: (stage: Stage) => void }) {
  return (
    <nav aria-label="Scenario stages" className="overflow-x-auto pb-1">
      <ol className="flex min-w-max items-center gap-1 rounded-full border border-[#4B5480]/15 bg-white/55 p-1">
        {stages.map((stage) => {
          const disabled = (stage.id > 1 && simulation === null) || (stage.id === 4 && !hasResearch);
          const active = stage.id === current;
          return (
            <li key={stage.id}>
              <button type="button" disabled={disabled} aria-current={active ? "step" : undefined} aria-label={stage.label} onClick={() => onNavigate(stage.id)} className={`rounded-full px-4 py-2 text-sm font-medium transition ${active ? "bg-[#4B5480] text-white" : "text-[#1A2122]/60 hover:bg-white disabled:cursor-not-allowed disabled:opacity-35"}`}>
                <span className="mr-2 text-[10px] opacity-60">0{stage.id}</span>{stage.short}
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

function StartStage({
  name, hourlyWage, repairQuote, breakdownDate, snapshot, requestState,
  onNameChange, onWageChange, onRepairChange, onBreakdownDateChange, onSubmit,
}: {
  name: string; hourlyWage: string; repairQuote: number; breakdownDate: string;
  snapshot: CustomerSnapshot | null; requestState: RequestState;
  onNameChange: (value: string) => void; onWageChange: (value: string) => void;
  onRepairChange: (value: number) => void; onBreakdownDateChange: (value: string) => void;
  onSubmit: () => void;
}) {
  const wageCents = wageInputToCents(hourlyWage);
  const preview = wageCents === null ? null : wagePreview(wageCents);
  const nameIsValid = name.trim().length > 0 && name.trim().length <= 80;
  const isValid = nameIsValid && preview !== null;
  const selectedAccount = snapshot?.accounts[0];

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isValid) onSubmit();
  }

  return (
    <section className="grid gap-10 py-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-start lg:py-14">
      <div className="lg:sticky lg:top-6">
        <p className="font-brand text-sm text-[#4B5480]">A financial resilience prototype</p>
        <h1 className="font-display mt-5 max-w-3xl text-5xl leading-[1.06] tracking-[-0.035em] text-[#1A2122] sm:text-7xl">One bad day shouldn&apos;t become a bad month.</h1>
        <p className="mt-7 max-w-xl text-lg leading-8 text-[#4B5480]">See how a sudden car problem could affect Maya&apos;s next month—and find the clearest ways through it.</p>
        <div className="mt-6 max-w-xl rounded-3xl border border-[#4B5480]/15 bg-white/75 p-5 shadow-sm">
          {snapshot ? <><DataBadge snapshot={snapshot} /><div className="mt-4 flex items-end justify-between gap-4"><div><p className="text-sm font-semibold text-slate-900">{selectedAccount?.nickname ?? selectedAccount?.type ?? "Checking account"}</p><p className="mt-1 text-xs text-slate-500">Selected account · {selectedAccount?.type ?? "Checking"}</p></div><div className="text-right"><p className="text-xs text-slate-500">Current balance</p><p className="mt-1 text-2xl font-semibold text-slate-950">{selectedAccount ? formatCurrency(selectedAccount.balance_cents) : "—"}</p></div></div></> : <p className="text-sm text-slate-500">Connecting to the seeded customer snapshot…</p>}
        </div>
        {snapshot ? <details className="mt-3 max-w-xl rounded-2xl border border-[#4B5480]/15 bg-white/55 p-4"><summary className="cursor-pointer text-sm font-semibold text-[#4B5480]">View banking details</summary><div className="mt-4 grid grid-cols-2 gap-3 text-sm"><div><p className="text-xs text-[#1A2122]/55">90-day spending</p><p className="font-semibold">{formatCurrency(snapshot.history.spending_total_cents)}</p></div><div><p className="text-xs text-[#1A2122]/55">Upcoming bills</p><p className="font-semibold">{snapshot.upcoming_bills.length}</p></div><div className="col-span-2 text-xs text-[#1A2122]/55">{snapshot.history.transactions.length} normalized transactions remain available in the ripple-effect details.</div></div></details> : null}
      </div>

      <form onSubmit={submit} className="rounded-[2rem] border border-[#4B5480]/15 bg-white/85 p-6 shadow-xl shadow-[#4B5480]/10 sm:p-8">
        <div className="mb-7"><p className="font-brand text-sm text-[#4B5480]">Maya&apos;s situation</p><h2 className="font-display mt-1 text-3xl text-[#1A2122]">What changed?</h2></div>
        <label htmlFor="name" className="block text-sm font-medium text-slate-700">Display name</label>
        <input id="name" name="name" value={name} maxLength={80} onChange={(event) => onNameChange(event.target.value)} aria-invalid={!nameIsValid} className="mt-2 w-full rounded-xl border border-[#4B5480]/25 px-4 py-3 text-[#1A2122] outline-none transition focus:border-[#1FBFA7] focus:ring-4 focus:ring-[#1FBFA7]/20" />
        <label htmlFor="wage" className="mt-6 block text-sm font-medium text-slate-700">Hourly wage <span className="font-normal text-slate-400">($ / hour)</span></label>
        <div className="relative mt-2"><span className="absolute left-4 top-3 text-[#4B5480]">$</span><input id="wage" name="wage" type="number" inputMode="decimal" min="0.01" max="500" step="0.01" value={hourlyWage} onChange={(event) => onWageChange(event.target.value)} aria-describedby="wage-help" aria-invalid={wageCents === null} className="w-full rounded-xl border border-[#4B5480]/25 py-3 pl-8 pr-4 text-[#1A2122] outline-none transition focus:border-[#1FBFA7] focus:ring-4 focus:ring-[#1FBFA7]/20" /></div>
        <p id="wage-help" className="mt-2 text-xs text-slate-500">40 hours/week. Take-home is estimated at 80%, not inferred as a new bank deposit.</p>
        <div className="mt-6 flex items-center justify-between gap-4"><label htmlFor="repair-quote" className="text-sm font-medium text-slate-700">Unpaid repair quote</label><div className="flex items-center gap-3"><span className="text-lg font-semibold text-slate-950">{formatCurrency(repairQuote * 100)}</span><button type="button" onClick={() => onRepairChange(DEFAULT_REPAIR_QUOTE)} className="text-xs font-medium text-slate-500 underline decoration-slate-300 underline-offset-4 hover:text-slate-950">Reset</button></div></div>
        <input id="repair-quote" type="range" min="100" max="1500" step="50" value={repairQuote} onChange={(event) => onRepairChange(Number(event.target.value))} className="mt-3 w-full accent-[#1FBFA7]" />
        <div className="mt-1 flex justify-between text-xs text-slate-400"><span>$100</span><span>$1,500</span></div>
        <label htmlFor="breakdown-date" className="mt-6 block text-sm font-medium text-slate-700">Breakdown date</label>
        <input id="breakdown-date" type="date" min={snapshot?.cash_flow.start_date ?? breakdownDate} max={snapshot?.cash_flow.end_date ?? undefined} value={breakdownDate} onChange={(event) => onBreakdownDateChange(event.target.value)} className="mt-2 w-full rounded-xl border border-[#4B5480]/25 bg-white px-4 py-3 text-[#1A2122]" />
        <div className="mt-6 grid grid-cols-2 gap-3 rounded-2xl bg-slate-950 p-4 text-white"><div><p className="text-xs text-slate-400">Gross / week</p><p className="mt-1 text-xl font-semibold">{preview ? formatCurrency(preview.grossWeeklyCents) : "—"}</p></div><div className="border-l border-white/10 pl-4"><p className="text-xs text-slate-400">Est. net / shift</p><p className="mt-1 text-xl font-semibold">{preview ? formatCurrency(preview.estimatedNetPerShiftCents) : "—"}</p></div></div>
        {requestState.kind === "error" ? <div role="alert" className="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"><p className="font-semibold">Simulation failed</p><p className="mt-1">{requestState.message}</p></div> : null}
        <button type="submit" disabled={!isValid || requestState.kind === "loading"} className="mt-6 w-full rounded-xl bg-[#1FBFA7] px-5 py-3.5 font-semibold text-[#1A2122] transition hover:bg-[#18a892] focus:outline-none focus:ring-4 focus:ring-[#1FBFA7]/25 disabled:cursor-not-allowed disabled:bg-slate-300">{requestState.kind === "loading" ? "Simulating dated cash flow…" : "See the ripple effect"}</button>
      </form>
    </section>
  );
}

export default function ScenarioApp() {
  const [stage, setStage] = useState<Stage>(1);
  const [name, setName] = useState("Maya Rodriguez");
  const [hourlyWage, setHourlyWage] = useState(DEFAULT_HOURLY_WAGE);
  const [repairQuote, setRepairQuote] = useState(DEFAULT_REPAIR_QUOTE);
  const [breakdownDate, setBreakdownDate] = useState(todayInChicago);
  const [snapshot, setSnapshot] = useState<CustomerSnapshot | null>(null);
  const [simulation, setSimulation] = useState<CrisisSimulation | null>(null);
  const [requestState, setRequestState] = useState<RequestState>({ kind: "idle" });
  const [research, setResearch] = useState<ResearchResult | null>(null);
  const [researchState, setResearchState] = useState<RequestState>({ kind: "idle" });
  const [routeContext, setRouteContext] = useState({ home: AUSTIN_DEMO_CONTEXT.home, work: AUSTIN_DEMO_CONTEXT.work, shiftStart: AUSTIN_DEMO_CONTEXT.shiftStart, shiftEnd: AUSTIN_DEMO_CONTEXT.shiftEnd });
  const snapshotQuery = useMemo(() => new URLSearchParams({ display_name: "Maya Rodriguez", hourly_rate_cents: "2000", repair_quote_cents: "40000" }), []);
  const recoveryRequest = useMemo<CreateRecoverySessionBody | null>(() => {
    const hourlyRateCents = wageInputToCents(hourlyWage);
    if (hourlyRateCents === null) return null;
    return {
      scenario: { display_name: name.trim(), hourly_rate_cents: hourlyRateCents, repair_quote_cents: repairQuote * 100, breakdown_date: breakdownDate },
      research,
      context: { city: AUSTIN_DEMO_CONTEXT.city, home_location: routeContext.home, work_location: routeContext.work, shift_start_local: routeContext.shiftStart, shift_end_local: routeContext.shiftEnd, timezone: AUSTIN_DEMO_CONTEXT.timezone },
    };
  }, [breakdownDate, hourlyWage, name, repairQuote, research, routeContext]);

  useEffect(() => {
    const controller = new AbortController();
    async function preloadSnapshot() {
      try {
        const response = await fetch(`/api/customer/snapshot?${snapshotQuery.toString()}`, { cache: "no-store", signal: controller.signal });
        if (response.ok) setSnapshot((await response.json()) as CustomerSnapshot);
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return;
      }
    }
    void preloadSnapshot();
    return () => controller.abort();
  }, [snapshotQuery]);

  async function runSimulation() {
    const hourlyRateCents = wageInputToCents(hourlyWage);
    if (hourlyRateCents === null || !name.trim()) return;
    setRequestState({ kind: "loading" });
    setResearch(null);
    try {
      const response = await fetch("/api/simulations/crisis", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ display_name: name.trim(), hourly_rate_cents: hourlyRateCents, repair_quote_cents: repairQuote * 100, breakdown_date: breakdownDate }) });
      const body = (await response.json()) as CrisisSimulationResponse | { message?: string };
      if (!response.ok) throw new Error("message" in body && body.message ? body.message : "Simulation request failed.");
      const result = body as CrisisSimulationResponse;
      setSnapshot(result.snapshot);
      setSimulation(result.simulation);
      setRequestState({ kind: "idle" });
      setStage(2);
    } catch (error) {
      setRequestState({ kind: "error", message: error instanceof Error ? error.message : "Simulation request failed." });
    }
  }

  async function runResearch(force: boolean) {
    const hourlyRateCents = wageInputToCents(hourlyWage);
    if (hourlyRateCents === null || !simulation) return;
    setResearchState({ kind: "loading" });
    try {
      const response = await fetch("/api/research/interventions", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(researchRequestBody({ displayName: name.trim(), hourlyRateCents, repairQuoteCents: repairQuote * 100, breakdownDate }, routeContext, force)) });
      const body = (await response.json()) as ResearchResponse | { message?: string };
      if (!response.ok) throw new Error("message" in body && body.message ? body.message : "Research request failed.");
      const result = body as ResearchResponse;
      setSnapshot(result.snapshot);
      setSimulation(result.simulation);
      setResearch(filterUnsupportedMechanicRecommendations(result.research));
      setResearchState({ kind: "idle" });
    } catch (error) {
      setResearchState({ kind: "error", message: error instanceof Error ? error.message : "Research request failed." });
    }
  }

  function changeRouteContext(field: "home" | "work" | "shiftStart" | "shiftEnd", value: string) {
    setRouteContext((previous) => ({ ...previous, [field]: value }));
    setResearch(null);
  }

  function restart() {
    setName("Maya Rodriguez"); setHourlyWage(DEFAULT_HOURLY_WAGE); setRepairQuote(DEFAULT_REPAIR_QUOTE); setBreakdownDate(todayInChicago()); setSimulation(null); setResearch(null); setRouteContext({ home: AUSTIN_DEMO_CONTEXT.home, work: AUSTIN_DEMO_CONTEXT.work, shiftStart: AUSTIN_DEMO_CONTEXT.shiftStart, shiftEnd: AUSTIN_DEMO_CONTEXT.shiftEnd }); setRequestState({ kind: "idle" }); setStage(1);
  }

  return (
    <main className="min-h-screen bg-[#FFF3D8] text-[#1A2122]">
      <header className="sticky top-0 z-50 border-b border-[#4B5480]/10 bg-[#FFF3D8]/90 backdrop-blur-xl"><div className="mx-auto flex max-w-7xl flex-col gap-5 px-5 py-4 sm:px-8 lg:flex-row lg:items-center lg:justify-between"><button type="button" onClick={() => setStage(1)} className="w-fit text-left"><span className="block font-brand text-[10px] uppercase tracking-[0.2em] text-[#4B5480]">HackTX 2026</span><span className="font-display mt-1 block text-xl tracking-tight">Breakingpoint</span></button><StageNavigation current={stage} simulation={simulation} hasResearch={Boolean(research)} onNavigate={setStage} /></div></header>
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        {stage === 1 ? <StartStage name={name} hourlyWage={hourlyWage} repairQuote={repairQuote} breakdownDate={breakdownDate} snapshot={snapshot} requestState={requestState} onNameChange={(value) => { setName(value); setResearch(null); }} onWageChange={(value) => { setHourlyWage(value); setResearch(null); }} onRepairChange={(value) => { setRepairQuote(value); setResearch(null); }} onBreakdownDateChange={(value) => { setBreakdownDate(value); setResearch(null); }} onSubmit={() => void runSimulation()} /> : null}
        {stage === 2 && snapshot && simulation ? <CrisisStage snapshot={snapshot} simulation={simulation} repairQuote={repairQuote} loading={requestState.kind === "loading"} error={requestState.kind === "error" ? requestState.message : null} onRepairChange={(value) => { setRepairQuote(value); setResearch(null); }} onRerun={() => void runSimulation()} onBack={() => setStage(1)} onNext={() => setStage(3)} /> : null}
        {stage === 3 && simulation && !research ? <ResearchStage research={research} loading={researchState.kind === "loading"} error={researchState.kind === "error" ? researchState.message : null} home={routeContext.home} work={routeContext.work} shiftStart={routeContext.shiftStart} shiftEnd={routeContext.shiftEnd} onContextChange={changeRouteContext} onRun={(force) => void runResearch(force)} onBack={() => setStage(2)} onNext={() => setStage(4)} /> : null}
        {stage === 3 && simulation && research && recoveryRequest ? <RecoveryStage mode="questions" request={recoveryRequest} research={research} onBack={() => setStage(2)} onAdjust={() => setStage(1)} onRestart={restart} onContinue={() => setStage(4)} /> : null}
        {stage === 4 && simulation && recoveryRequest ? <RecoveryStage mode="plans" request={recoveryRequest} research={research} onBack={() => setStage(3)} onAdjust={() => setStage(1)} onRestart={restart} /> : null}
      </div>
      <footer className="border-t border-[#4B5480]/15 px-5 py-6 text-center text-xs leading-5 text-[#1A2122]/55"><span className="font-display mr-2 text-[#1A2122]">Breakingpoint.</span> One bad day shouldn&apos;t become a bad month.</footer>
    </main>
  );
}
