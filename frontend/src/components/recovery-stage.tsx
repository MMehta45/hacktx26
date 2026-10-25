"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { formatCurrency } from "@/lib/scenario";
import type { ResearchResult } from "@/types/research";
import type { CreateRecoverySessionBody, RecoveryPlan, RecoveryQuestion, RecoverySession } from "@/types/recovery";

type Props = {
  request: CreateRecoverySessionBody;
  research: ResearchResult | null;
  onBack: () => void;
  onAdjust: () => void;
  onRestart: () => void;
};

type Status = { kind: "loading" | "idle" | "error"; message?: string };

class RecoveryApiError extends Error {
  constructor(message: string, readonly status: number, readonly code?: string) {
    super(message);
  }
}

function signedMoney(cents: number) {
  return `${cents > 0 ? "+" : ""}${formatCurrency(cents)}`;
}

async function api<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  const body = (await response.json()) as T | { message?: string; code?: string };
  if (!response.ok) {
    const message = typeof body === "object" && body !== null && "message" in body && typeof body.message === "string" ? body.message : null;
    const code = typeof body === "object" && body !== null && "code" in body && typeof body.code === "string" ? body.code : undefined;
    throw new RecoveryApiError(message ?? `Request failed (${response.status}).`, response.status, code);
  }
  return body as T;
}

function QuestionCard({ question, busy, onAnswer }: { question: RecoveryQuestion; busy: boolean; onAnswer: (value: boolean | number | string) => void }) {
  const [value, setValue] = useState("");
  function submit(event: FormEvent) {
    event.preventDefault();
    if (!value) return;
    onAnswer(question.answer_type === "number" ? Number(value) : value);
  }
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-wide text-orange-600">Question · {question.priority_score}/27 impact</p>
      <h3 className="mt-2 text-lg font-semibold text-slate-950">{question.prompt}</h3>
      <p className="mt-2 text-sm leading-6 text-slate-600">{question.reason}</p>
      {question.answer_type === "yes_no" ? (
        <div className="mt-4 flex gap-3">
          <button disabled={busy} type="button" onClick={() => onAnswer(true)} className="rounded-lg bg-slate-950 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">Yes</button>
          <button disabled={busy} type="button" onClick={() => onAnswer(false)} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 disabled:opacity-50">No</button>
        </div>
      ) : (
        <form onSubmit={submit} className="mt-4 flex flex-col gap-2 sm:flex-row">
          <input type={question.answer_type === "date" ? "date" : question.answer_type === "number" ? "number" : "text"} min={question.answer_type === "number" ? "1" : undefined} step={question.answer_type === "number" ? "1" : undefined} value={value} onChange={(event) => setValue(event.target.value)} className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          <button disabled={busy || !value} className="rounded-lg bg-slate-950 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">Save answer</button>
        </form>
      )}
    </article>
  );
}

function Metric({ label, before, after }: { label: string; before: number; after: number }) {
  return <div className="rounded-xl bg-slate-100 p-3"><p className="text-xs text-slate-500">{label}</p><p className="mt-1 text-sm"><span className="text-slate-500 line-through">{formatCurrency(before)}</span><span className="ml-2 font-semibold text-slate-950">{formatCurrency(after)}</span></p></div>;
}

export function RecoveryPlanView({ plan, baseline, onConfirm, busy }: { plan: RecoveryPlan; baseline: RecoverySession["evaluation"]["baseline"]; onConfirm: (requirementId: string, accepted: boolean) => void; busy: boolean }) {
  const conditional = plan.feasibility !== "ready_with_confirmed_conditions";
  const baselineNodes = new Map(baseline.graph_nodes.map((node) => [node.id, node]));
  const changedNodes = plan.result.graph_nodes.filter((node) => baselineNodes.get(node.id)?.status !== node.status);
  const missedBefore = baseline.shift_records.filter((shift) => shift.attendance === "projected_missed").length;
  const missedAfter = plan.result.shift_records.filter((shift) => shift.attendance === "projected_missed").length;
  const cashCheckpoints = plan.result.cashflow.filter((point, index, all) => point.raw_shortfall || index === 0 || index === all.length - 1).slice(0, 5);
  return (
    <article className="rounded-[1.5rem] border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3"><span className="font-mono text-xs text-slate-500">PLAN {plan.rank}</span><span className={`rounded-full px-3 py-1 text-xs font-semibold ${conditional ? "bg-amber-100 text-amber-900" : "bg-emerald-100 text-emerald-800"}`}>{conditional ? "Conditional" : "Conditions confirmed"}</span></div>
      <h3 className="mt-3 text-xl font-semibold text-slate-950">{plan.name}</h3>
      <p className="mt-2 text-sm font-medium text-amber-800">{plan.conditional_label}</p>
      <p className="mt-2 text-sm leading-6 text-slate-600">{plan.explanation}</p>
      <ul className="mt-4 space-y-2 text-sm text-slate-700">{plan.actions.map((action) => <li key={action.id}>• <strong>{action.title}</strong>{action.evidence_status ? ` · ${action.evidence_status.replaceAll("_", " ")}` : ""}</li>)}</ul>
      <div className="mt-4 grid gap-2 sm:grid-cols-3">
        <Metric label="Unfunded essential bills" before={baseline.unpaid_essential_total_cents} after={plan.result.unpaid_essential_total_cents} />
        <Metric label="Peak funding gap" before={baseline.peak_funding_gap_cents} after={plan.result.peak_funding_gap_cents} />
        <Metric label="Ending raw balance" before={baseline.crisis_ending_balance_cents} after={plan.result.crisis_ending_balance_cents} />
      </div>
      <div className="mt-4 flex flex-wrap gap-2 text-xs"><span className="rounded-full bg-emerald-50 px-3 py-1 text-emerald-800">Income preserved {formatCurrency(plan.delta.income_preserved_cents)}</span><span className="rounded-full bg-slate-100 px-3 py-1 text-slate-700">Action cost {formatCurrency(plan.delta.incremental_cost_cents)}</span><span className="rounded-full bg-slate-100 px-3 py-1 text-slate-700">Gap change {signedMoney(plan.delta.peak_funding_gap_change_cents)}</span></div>
      <div className="mt-4 grid gap-2 sm:grid-cols-3"><div className="rounded-xl border border-slate-200 p-3 text-sm"><p className="text-xs text-slate-500">Missed shifts</p><p className="mt-1 font-semibold">{missedBefore} → {missedAfter}</p></div><div className="rounded-xl border border-slate-200 p-3 text-sm"><p className="text-xs text-slate-500">Modeled repair</p><p className="mt-1 font-semibold">{baseline.repair_projection.modeled_payment_date ?? "Not affordable"} → {plan.result.repair_projection.modeled_payment_date ?? "Not affordable"}</p></div><div className="rounded-xl border border-slate-200 p-3 text-sm"><p className="text-xs text-slate-500">Unfunded bills</p><p className="mt-1 font-semibold">{baseline.unpaid_bills.length} → {plan.result.unpaid_bills.length}</p></div></div>
      {plan.conditional_assumptions.length ? <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4"><p className="text-xs font-semibold uppercase tracking-wide text-amber-900">What must still happen</p><ul className="mt-2 space-y-1 text-sm text-amber-950">{plan.conditional_assumptions.map((item) => <li key={item}>• {item}</li>)}</ul><div className="mt-3 flex flex-wrap gap-2">{plan.unresolved_requirement_ids.map((id) => <span key={id} className="inline-flex gap-1"><button disabled={busy} onClick={() => onConfirm(id, true)} className="rounded-md bg-amber-900 px-2 py-1 text-xs font-semibold text-white">Confirm</button><button disabled={busy} onClick={() => onConfirm(id, false)} className="rounded-md border border-amber-300 px-2 py-1 text-xs font-semibold text-amber-950">Not available</button></span>)}</div></div> : null}
      <div className="mt-5 grid gap-5 md:grid-cols-2"><div><h4 className="text-sm font-semibold text-slate-900">Next steps</h4><ol className="mt-2 space-y-2 text-sm text-slate-600">{plan.next_steps.map((step, index) => <li key={step}>{index + 1}. {step}</li>)}</ol></div><div><h4 className="text-sm font-semibold text-slate-900">Evidence</h4>{plan.sources.length ? <ul className="mt-2 space-y-2 text-sm">{plan.sources.map((source) => <li key={source.evidence_id}>{source.url ? <a className="font-medium text-orange-700 underline" href={source.url} target="_blank" rel="noreferrer">{source.title}</a> : source.title}<p className="text-xs text-slate-500">{source.limitations.join(" ")}</p></li>)}</ul> : <p className="mt-2 text-sm text-slate-500">This plan uses user answers and deterministic scenario data; no public source is asserted.</p>}</div></div>
      <div className="mt-5 rounded-xl border border-slate-200 p-4"><h4 className="text-sm font-semibold text-slate-900">Cascade changes</h4>{changedNodes.length ? <ul className="mt-2 space-y-1 text-sm text-slate-600">{changedNodes.map((node) => <li key={node.id}>• {node.label}: {baselineNodes.get(node.id)?.status} → <strong>{node.status}</strong></li>)}</ul> : <p className="mt-2 text-sm text-slate-500">No problem-node status changes; financial deltas above still reflect the full dated rerun.</p>}</div>
      <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200 p-4"><h4 className="text-sm font-semibold text-slate-900">Dated cash checkpoints</h4><table className="mt-2 w-full min-w-[30rem] text-left text-xs"><thead className="text-slate-500"><tr><th className="py-1">Date</th><th>Untreated</th><th>This plan</th><th>Spendable after allocation</th></tr></thead><tbody>{cashCheckpoints.map((point) => { const before = baseline.cashflow.find((item) => item.date === point.date); return <tr key={point.date} className="border-t border-slate-100"><td className="py-2">{point.date}</td><td>{before ? formatCurrency(before.crisis_balance_cents) : "—"}</td><td>{formatCurrency(point.crisis_balance_cents)}</td><td>{formatCurrency(point.constrained_available_cents)}</td></tr>; })}</tbody></table></div>
    </article>
  );
}

export function RecoveryStage({ request, research, onBack, onAdjust, onRestart }: Props) {
  const [session, setSession] = useState<RecoverySession | null>(null);
  const [status, setStatus] = useState<Status>({ kind: "loading" });
  const storageKey = useMemo(() => `obt-recovery:${request.scenario.display_name}:${request.scenario.breakdown_date}:${request.scenario.hourly_rate_cents}:${request.scenario.repair_quote_cents}:${research?.run_id ?? "no-research"}`, [request, research]);

  useEffect(() => {
    let live = true;
    async function load() {
      setStatus({ kind: "loading" });
      try {
        const saved = window.localStorage.getItem(storageKey);
        let next: RecoverySession | null = null;
        if (saved) {
          try {
            next = await api<RecoverySession>(`/api/recovery/sessions/${saved}`);
          } catch (error) {
            if (error instanceof RecoveryApiError && error.code === "RECOVERY_SESSION_NOT_FOUND") {
              window.localStorage.removeItem(storageKey);
            } else {
              throw error;
            }
          }
        }
        // A saved baseline session must never displace a completed Explore run.
        if (next && next.research_run_id !== (research?.run_id ?? null)) {
          window.localStorage.removeItem(storageKey);
          next = null;
        }
        if (!next) next = await api<RecoverySession>("/api/recovery/sessions", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(request) });
        if (!live) return;
        window.localStorage.setItem(storageKey, next.id);
        setSession(next); setStatus({ kind: "idle" });
      } catch (error) {
        if (live) setStatus({ kind: "error", message: error instanceof Error ? error.message : "Recovery session failed." });
      }
    }
    void load();
    return () => { live = false; };
  }, [request, research?.run_id, storageKey]);

  async function mutate(path: string, body: object) {
    if (!session) return;
    setStatus({ kind: "loading" });
    try {
      const next = await api<RecoverySession>(`/api/recovery/sessions/${session.id}/${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      setSession(next); setStatus({ kind: "idle" });
    } catch (error) { setStatus({ kind: "error", message: error instanceof Error ? error.message : "Update failed." }); }
  }

  async function researchMore(candidateIds: string[]) {
    if (!session) return;
    setStatus({ kind: "loading" });
    try {
      const result = await api<{ session: RecoverySession; message: string }>(`/api/recovery/sessions/${session.id}/research`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_version: session.version, candidate_ids: candidateIds.slice(0, 3) }) });
      setSession(result.session); setStatus({ kind: "idle", message: result.message });
    } catch (error) { setStatus({ kind: "error", message: error instanceof Error ? error.message : "Targeted research failed." }); }
  }

  if (!session) return <section className="py-12"><div className="rounded-2xl border border-slate-200 bg-white p-8"><h1 className="text-2xl font-semibold">Building recalculated recovery plans…</h1>{status.kind === "error" ? <div role="alert" className="mt-3"><p className="text-red-700">{status.message}</p><button type="button" onClick={() => window.location.reload()} className="mt-4 rounded-lg bg-slate-950 px-4 py-2 text-sm font-semibold text-white">Retry recovery setup</button></div> : <p className="mt-3 text-slate-600">Starting a versioned planning session with the authoritative simulator.</p>}</div></section>;
  const questions = session.next_question_ids.map((id) => session.questions.find((item) => item.id === id)).filter((item): item is RecoveryQuestion => Boolean(item));
  const leads = session.candidate_actions.filter((item) => !item.quantified);
  return (
    <section className="py-10">
      <div className="rounded-[2rem] bg-slate-950 p-7 text-white sm:p-10"><p className="font-mono text-xs uppercase tracking-[0.22em] text-orange-300">Stage 04 · interactive recovery</p><h1 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">Compare plans, then confirm what is actually possible.</h1><p className="mt-4 max-w-3xl text-slate-300">Every card reruns the dated shift, Friday-payroll, bill-allocation, and repair-affordability engine. Conditional outcomes show what happens only if their listed dependencies succeed.</p><div className="mt-6 flex flex-wrap gap-3 text-xs text-slate-300"><span>{session.evaluation.evaluated_plan_count} combinations evaluated</span><span>•</span><span>Up to 3 actions per plan</span><span>•</span><span>Session v{session.version}</span></div></div>
      {status.kind === "error" ? <div role="alert" className="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{status.message}</div> : status.message ? <div className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">{status.message}</div> : null}
      {!research ? <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950"><p className="font-semibold">Baseline options only</p><p className="mt-1">Explore has not been run for these scenario inputs. Return to Explore to research location-specific options, or continue with the clearly labeled built-in baseline actions.</p></div> : <div className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">Using Explore run <span className="font-mono">{research.run_id.slice(0, 8)}</span> with {research.evidence.length} evidence record(s) and {research.candidate_actions.length} researched candidate(s).</div>}
      {questions.length ? <div className="mt-8"><h2 className="text-2xl font-semibold">Resolve the highest-impact unknowns</h2><p className="mt-2 text-sm text-slate-600">Your answer can unlock a draft or mark an option possible. It never records third-party approval unless you explicitly confirm it.</p><div className="mt-4 grid gap-4 lg:grid-cols-2">{questions.map((question) => <QuestionCard key={question.id} question={question} busy={status.kind === "loading"} onAnswer={(value) => void mutate("answers", { session_version: session.version, question_id: question.id, value })} />)}</div></div> : null}
      {session.answers.length ? <details className="mt-5 rounded-xl border border-slate-200 bg-white p-4"><summary className="cursor-pointer text-sm font-semibold">Review or revise {session.answers.length} recorded answer(s)</summary><div className="mt-3 space-y-3">{session.answers.map((answer) => { const question = session.questions.find((item) => item.id === answer.question_id); return <div key={answer.question_id} className="flex flex-col justify-between gap-2 border-t border-slate-100 pt-3 text-sm sm:flex-row sm:items-center"><div><p className="font-medium">{question?.prompt ?? answer.question_id}</p><p className="text-slate-500">Current answer: {String(answer.value)}</p></div>{typeof answer.value === "boolean" ? <div className="flex gap-2"><button disabled={status.kind === "loading"} onClick={() => void mutate("answers", { session_version: session.version, question_id: answer.question_id, value: true })} className="rounded-md border border-slate-300 px-2 py-1 text-xs">Change to yes</button><button disabled={status.kind === "loading"} onClick={() => void mutate("answers", { session_version: session.version, question_id: answer.question_id, value: false })} className="rounded-md border border-slate-300 px-2 py-1 text-xs">Change to no</button></div> : null}</div>; })}</div></details> : null}
      {session.outreach_drafts.length ? <div className="mt-8"><h2 className="text-2xl font-semibold">Prepared outreach — not sent</h2><div className="mt-4 grid gap-4 lg:grid-cols-2">{session.outreach_drafts.map((draft) => <article key={draft.id} className="rounded-2xl border border-blue-200 bg-blue-50 p-5"><p className="text-xs font-semibold uppercase text-blue-800">Draft only</p><h3 className="mt-2 font-semibold">{draft.subject}</h3><p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-700">{draft.body}</p><button onClick={() => void navigator.clipboard.writeText(`Subject: ${draft.subject}\n\n${draft.body}`)} className="mt-4 rounded-lg bg-blue-900 px-3 py-2 text-xs font-semibold text-white">Copy draft</button><p className="mt-2 text-xs text-blue-900">{draft.disclaimer}</p></article>)}</div></div> : null}
      <div className="mt-10"><div className="flex flex-wrap items-end justify-between gap-3"><div><h2 className="text-2xl font-semibold">Ranked recovery strategies</h2><p className="mt-2 text-sm text-slate-600">Ranked by feasibility, unfunded essentials, bill count, funding gap, recovered shifts, and cost—in that order.</p></div></div><div className="mt-5 space-y-5">{session.evaluation.plans.length ? session.evaluation.plans.map((plan) => <RecoveryPlanView key={plan.id} plan={plan} baseline={session.evaluation.baseline} busy={status.kind === "loading"} onConfirm={(requirementId, accepted) => void mutate("requirements", { session_version: session.version, requirement_id: requirementId, status: accepted ? "user_reported_confirmed" : "rejected", source: "user_confirmation", effective_dates: [] })} />) : <div className="rounded-2xl border border-slate-200 bg-white p-6 text-slate-600">No compatible quantified action combinations are available yet. Answer a question or run targeted research on a lead.</div>}</div></div>
      {leads.length ? <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-6"><h2 className="text-lg font-semibold">Unquantified research leads</h2><p className="mt-2 text-sm text-slate-600">These findings are not recommendations and do not change the ledger. Targeted research may verify timing, fare, eligibility, or actual positive pricing evidence.</p><ul className="mt-4 space-y-3">{leads.slice(0, 5).map((lead) => <li key={lead.id} className="flex flex-col justify-between gap-3 border-t border-slate-100 pt-3 sm:flex-row sm:items-center"><div><p className="font-medium">{lead.title}</p><p className="text-xs text-slate-500">{lead.description}</p></div><button disabled={status.kind === "loading"} onClick={() => void researchMore([lead.id])} className="shrink-0 rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold">Research this dependency</button></li>)}</ul><p className="mt-4 text-xs text-slate-500">Targeted calls used: {session.research_calls_used}; cache hits: {session.research_cache_hits}.</p></div> : null}
      {session.warnings.length ? <div className="mt-6 rounded-xl bg-amber-50 p-4 text-sm text-amber-900"><ul>{session.warnings.map((warning) => <li key={warning}>• {warning}</li>)}</ul></div> : null}
      <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:justify-between"><button type="button" onClick={onBack} className="rounded-xl border border-slate-300 bg-white px-5 py-3 font-semibold text-slate-700">← Back to Explore</button><div className="flex gap-3"><button type="button" onClick={onAdjust} className="rounded-xl border border-slate-300 bg-white px-5 py-3 font-semibold text-slate-700">Adjust inputs</button><button type="button" onClick={onRestart} className="rounded-xl bg-orange-600 px-5 py-3 font-semibold text-white">Restart</button></div></div>
    </section>
  );
}
