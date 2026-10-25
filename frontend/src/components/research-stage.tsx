"use client";

import type { ResearchResult } from "@/types/research";

type Props = {
  research: ResearchResult | null; loading: boolean; error: string | null;
  home: string; work: string; shiftStart: string; shiftEnd: string;
  onContextChange: (field: "home" | "work" | "shiftStart" | "shiftEnd", value: string) => void;
  onRun: (force: boolean) => void; onBack: () => void; onNext: () => void;
};

const progress = [
  "Understanding the income disruption",
  "Checking transportation options",
  "Looking for flexibility around bills",
  "Exploring available support",
  "Preparing recovery choices",
];

export function ResearchStage({ loading, error, home, work, shiftStart, shiftEnd, onContextChange, onRun, onBack }: Props) {
  const fields = [["home", "Home address", home], ["work", "Work address", work], ["shiftStart", "Shift starts", shiftStart], ["shiftEnd", "Shift ends", shiftEnd]] as const;
  return <section className="mx-auto max-w-4xl py-10 sm:py-16">
    <div className="rounded-[2.25rem] bg-[#1A2122] p-7 text-white sm:p-12">
      <p className="font-brand text-sm text-[#1FBFA7]">Stage 03 · Preparing your recovery</p>
      <h1 className="font-display mt-4 text-4xl leading-tight sm:text-6xl">Finding a way through.</h1>
      <p className="mt-4 max-w-2xl text-lg leading-8 text-white/65">We&apos;ll look at the points where the chain can be interrupted, then ask only the questions that could change your options.</p>

      {!loading ? <div className="mt-10 rounded-3xl bg-white/[0.07] p-5 sm:p-7">
        <h2 className="font-brand text-xl">Confirm the commute</h2>
        <p className="mt-2 text-sm text-white/55">These details help us understand which shifts transportation could protect.</p>
        <div className="mt-5 grid gap-4 sm:grid-cols-2">{fields.map(([field, label, value]) => <label key={field} className="text-sm font-medium text-white/75">{label}<input aria-label={label} type={field.startsWith("shift") ? "time" : "text"} value={value} maxLength={150} onChange={(event) => onContextChange(field, event.target.value)} className="mt-2 w-full rounded-xl border border-white/15 bg-white px-4 py-3 text-[#1A2122] outline-none focus:border-[#1FBFA7] focus:ring-4 focus:ring-[#1FBFA7]/20" /></label>)}</div>
        {error ? <p role="alert" className="mt-4 rounded-xl bg-white/10 p-4 text-sm text-[#FFF3D8]">We couldn&apos;t finish that search. {error}</p> : null}
        <div className="mt-6 flex flex-wrap gap-3"><button type="button" onClick={() => onRun(false)} className="rounded-xl bg-[#1FBFA7] px-6 py-3 font-semibold text-[#1A2122] hover:bg-[#18aa96]">Find my way forward</button><button type="button" onClick={onBack} className="rounded-xl border border-white/20 px-5 py-3 font-semibold text-white/75">Back</button></div>
      </div> : <div role="status" aria-live="polite" className="mt-10 rounded-3xl bg-white/[0.06] p-6 sm:p-8">
        <div className="h-1.5 overflow-hidden rounded-full bg-white/10"><div className="research-pulse h-full w-1/3 rounded-full bg-[#1FBFA7]" /></div>
        <ol className="mt-7 space-y-4">{progress.map((item, index) => <li key={item} className="flex items-center gap-4 text-sm text-white/65"><span className={`grid h-7 w-7 place-items-center rounded-full ${index === 0 ? "bg-[#1FBFA7] text-[#1A2122]" : "bg-white/10 text-white/45"}`}>{index + 1}</span>{item}</li>)}</ol>
        <p className="mt-7 text-xs leading-5 text-white/45">This may take a moment. The research continues in the background; these steps describe what we&apos;re considering, not completed provider calls.</p>
      </div>}
    </div>
  </section>;
}
