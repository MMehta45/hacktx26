"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Background,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
  type NodeTypes,
} from "@xyflow/react";

import { formatCurrency, formatDate } from "@/lib/scenario";
import type { CrisisSimulation, ProblemStatus } from "@/types/simulation";

type ProblemNodeData = {
  label: string;
  status: ProblemStatus;
  revealed: boolean;
};

type FlowProblemNode = Node<ProblemNodeData, "problem">;

const positions: Record<string, { x: number; y: number }> = {
  car_breaks_down: { x: 0, y: 210 },
  car_unavailable: { x: 240, y: 210 },
  commute_disrupted: { x: 480, y: 210 },
  missed_work: { x: 720, y: 210 },
  reduced_paycheck: { x: 960, y: 210 },
  cash_shortfall: { x: 1200, y: 210 },
  bills_unpaid: { x: 1440, y: 210 },
  unexpected_repair_expense: { x: 240, y: 10 },
  cash_reserves_depleted: { x: 560, y: 10 },
  repair_delayed: { x: 880, y: 10 },
  extra_transportation_costs: { x: 760, y: 410 },
  emergency_borrowing: { x: 1200, y: 410 },
  future_debt_payments: { x: 1480, y: 410 },
  late_fees: { x: 1680, y: 210 },
};

const coreReveal = [
  "car_breaks_down",
  "car_unavailable",
  "commute_disrupted",
  "missed_work",
  "reduced_paycheck",
  "cash_shortfall",
  "bills_unpaid",
];

const statusStyles: Record<ProblemStatus, string> = {
  projected: "border-orange-400 bg-orange-50 text-slate-950 shadow-orange-100",
  conditional: "border-violet-300 bg-violet-50 text-slate-700 shadow-violet-100",
  inactive: "border-slate-200 bg-slate-50 text-slate-500 shadow-transparent",
  unresolved: "border-amber-300 bg-amber-50 text-slate-700 shadow-amber-100",
};

function ProblemGraphNode({ data, selected }: NodeProps<FlowProblemNode>) {
  return (
    <div
      className={`w-48 rounded-2xl border-2 px-4 py-3 shadow-lg transition duration-500 ${statusStyles[data.status]} ${
        data.revealed ? "translate-y-0 opacity-100" : "translate-y-2 opacity-20"
      } ${selected ? "ring-4 ring-orange-200" : ""}`}
    >
      <Handle type="target" position={Position.Left} className="!h-2 !w-2 !bg-slate-400" />
      <p className="text-[10px] font-bold uppercase tracking-[0.16em] opacity-60">
        {data.status}
      </p>
      <p className="mt-1 text-sm font-semibold leading-5">{data.label}</p>
      <Handle type="source" position={Position.Right} className="!h-2 !w-2 !bg-slate-400" />
    </div>
  );
}

const nodeTypes: NodeTypes = { problem: ProblemGraphNode };

export function CrisisGraph({ simulation }: { simulation: CrisisSimulation }) {
  const [revealedCount, setRevealedCount] = useState(0);
  const [replay, setReplay] = useState(0);
  const [selectedId, setSelectedId] = useState("car_breaks_down");

  useEffect(() => {
    let interval: number | undefined;
    const start = window.setTimeout(() => {
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        setRevealedCount(coreReveal.length);
        return;
      }
      let current = 0;
      interval = window.setInterval(() => {
        current += 1;
        setRevealedCount(current);
        if (current >= coreReveal.length && interval !== undefined) {
          window.clearInterval(interval);
        }
      }, 420);
    }, 0);
    return () => {
      window.clearTimeout(start);
      if (interval !== undefined) window.clearInterval(interval);
    };
  }, [replay, simulation]);

  const revealed = useMemo(
    () => new Set([...coreReveal.slice(0, revealedCount), ...simulation.graph_nodes.filter((item) => item.status !== "projected").map((item) => item.id)]),
    [revealedCount, simulation.graph_nodes],
  );

  const nodes: FlowProblemNode[] = useMemo(
    () =>
      simulation.graph_nodes.map((item) => ({
        id: item.id,
        type: "problem",
        position: positions[item.id] ?? { x: 0, y: 0 },
        data: {
          label: item.label,
          status: item.status,
          revealed: revealed.has(item.id) || !coreReveal.includes(item.id),
        },
      })),
    [revealed, simulation.graph_nodes],
  );

  const statusById = useMemo(
    () => Object.fromEntries(simulation.graph_nodes.map((item) => [item.id, item.status])),
    [simulation.graph_nodes],
  );
  const edges: Edge[] = useMemo(
    () =>
      simulation.graph_edges.map((item) => {
        const projected =
          statusById[item.source] === "projected" && statusById[item.target] === "projected";
        return {
          id: item.id,
          source: item.source,
          target: item.target,
          label: item.condition ?? undefined,
          animated: projected,
          markerEnd: { type: MarkerType.ArrowClosed },
          style: {
            stroke: projected ? "#f97316" : "#94a3b8",
            strokeWidth: projected ? 2.2 : 1.4,
            strokeDasharray: projected ? undefined : "5 5",
          },
          labelStyle: { fontSize: 9, fill: "#64748b" },
        };
      }),
    [simulation.graph_edges, statusById],
  );

  const selected =
    simulation.graph_nodes.find((item) => item.id === selectedId) ?? simulation.graph_nodes[0];

  return (
    <article className="overflow-hidden rounded-3xl border border-slate-800 bg-slate-950 text-white shadow-xl">
      <div className="flex flex-col justify-between gap-4 border-b border-white/10 p-6 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm font-medium text-orange-300">Projected untreated cascade</p>
          <h2 className="mt-1 text-2xl font-semibold">How one disruption travels</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
            Select any problem to inspect its evidence. Animation explains dependency order—it is
            not a live banking event.
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setRevealedCount(0);
            setReplay((value) => value + 1);
          }}
          className="rounded-xl border border-white/15 px-4 py-2 text-sm font-semibold text-slate-200 hover:bg-white/10"
        >
          Replay cascade
        </button>
      </div>

      <div className="h-[31rem] bg-slate-900/60">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodeClick={(_, node) => setSelectedId(node.id)}
          fitView
          fitViewOptions={{ padding: 0.12 }}
          minZoom={0.35}
          maxZoom={1.5}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#334155" gap={24} size={1} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>

      {selected ? (
        <div className="grid gap-4 border-t border-white/10 p-6 lg:grid-cols-[0.65fr_1.35fr]">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-orange-300">
              {selected.status} · {selected.source.replaceAll("_", " ")}
            </p>
            <h3 className="mt-2 text-xl font-semibold">{selected.label}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-300">{selected.description}</p>
          </div>
          <div className="rounded-2xl bg-white/[0.05] p-4 text-sm leading-6 text-slate-300">
            <p>{selected.evidence}</p>
            <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-400">
              {selected.activation_date ? <span>Date: {formatDate(selected.activation_date)}</span> : null}
              {selected.amount_cents !== null ? <span>Amount: {formatCurrency(selected.amount_cents)}</span> : null}
            </div>
          </div>
        </div>
      ) : null}
    </article>
  );
}
