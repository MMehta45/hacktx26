"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Background, Controls, Handle, Position, ReactFlow, getBezierPath, type Edge, type EdgeProps, type Node, type NodeProps, type NodeTypes } from "@xyflow/react";
import { formatCurrency, formatDate } from "@/lib/scenario";
import type { CrisisSimulation, ProblemStatus } from "@/types/simulation";

type GraphNode = CrisisSimulation["graph_nodes"][number];
type GraphEdge = CrisisSimulation["graph_edges"][number];
type ProblemNodeData = { label: string; status: ProblemStatus; revealed: boolean; dimmed: boolean };
type FlowProblemNode = Node<ProblemNodeData, "problem">;
type CascadeEvent = { type: "node" | "edge"; id: string };

export function buildCascadeLayout(nodes: GraphNode[], edges: GraphEdge[]) {
  const incoming = new Map(nodes.map((node) => [node.id, 0]));
  edges.forEach((edge) => incoming.has(edge.target) && incoming.set(edge.target, (incoming.get(edge.target) ?? 0) + 1));
  const roots = nodes.filter((node) => (incoming.get(node.id) ?? 0) === 0);
  const preferred = nodes.find((node) => node.id === "car_breaks_down");
  const queue = [...(preferred ? [preferred, ...roots.filter((node) => node.id !== preferred.id)] : roots)].map((node) => ({ id: node.id, layer: 0 }));
  const layerById = new Map<string, number>();
  while (queue.length) {
    const current = queue.shift()!;
    if (current.layer > nodes.length) continue;
    const existing = layerById.get(current.id);
    if (existing !== undefined && existing >= current.layer) continue;
    layerById.set(current.id, current.layer);
    edges.filter((edge) => edge.source === current.id).forEach((edge) => queue.push({ id: edge.target, layer: current.layer + 1 }));
  }
  nodes.forEach((node) => { if (!layerById.has(node.id)) layerById.set(node.id, 0); });
  const layers = new Map<number, string[]>();
  nodes.forEach((node) => { const layer = Math.min(layerById.get(node.id) ?? 0, 7); layers.set(layer, [...(layers.get(layer) ?? []), node.id]); });
  const positions: Record<string, { x: number; y: number }> = {};
  layers.forEach((ids, layer) => ids.forEach((id, index) => { positions[id] = { x: ((ids.length - 1) * -280) / 2 + index * 280, y: layer * 180 }; }));
  return positions;
}

export function buildCascadeSequence(nodes: GraphNode[], edges: GraphEdge[]): CascadeEvent[] {
  const projected = new Set(nodes.filter((node) => node.status === "projected").map((node) => node.id));
  const relevant = edges.filter((edge) => projected.has(edge.source) && projected.has(edge.target));
  const incoming = new Map([...projected].map((id) => [id, 0]));
  relevant.forEach((edge) => incoming.set(edge.target, (incoming.get(edge.target) ?? 0) + 1));
  const roots = [...projected].filter((id) => (incoming.get(id) ?? 0) === 0).sort((a) => a === "car_breaks_down" ? -1 : 0);
  const events: CascadeEvent[] = roots.map((id) => ({ type: "node", id }));
  const revealed = new Set(roots); const remaining = [...relevant];
  while (remaining.length) {
    const ready = remaining.filter((edge) => revealed.has(edge.source));
    if (!ready.length) break;
    ready.forEach((edge) => { events.push({ type: "edge", id: edge.id }); if (!revealed.has(edge.target)) { events.push({ type: "node", id: edge.target }); revealed.add(edge.target); } remaining.splice(remaining.indexOf(edge), 1); });
  }
  return events;
}

const statusStyles: Record<ProblemStatus, string> = { projected: "border-[#1FBFA7] bg-[#FFF3D8] text-[#1A2122]", conditional: "border-[#7f89b9] bg-[#4B5480] text-white", inactive: "border-white/20 bg-[#252d2e] text-white/55", unresolved: "border-[#FFF3D8]/50 bg-[#4B5480] text-white" };
function ProblemGraphNode({ data, selected }: NodeProps<FlowProblemNode>) {
  return <div tabIndex={0} aria-label={`${data.label}, ${data.status}`} className={`min-h-24 w-56 rounded-[1.5rem] border px-5 py-4 shadow-xl transition-all duration-300 ${statusStyles[data.status]} ${data.revealed ? "translate-y-0 opacity-100" : "pointer-events-none translate-y-3 opacity-0"} ${data.dimmed ? "!opacity-20" : ""} ${selected ? "ring-4 ring-[#1FBFA7]/35" : ""}`}><Handle type="target" position={Position.Top} className="!h-2.5 !w-2.5 !border-0 !bg-[#1FBFA7]" /><p className="text-[10px] font-bold uppercase tracking-[0.18em] opacity-65">{data.status}</p><p className="mt-1 text-base font-semibold leading-6">{data.label}</p><Handle type="source" position={Position.Bottom} className="!h-2.5 !w-2.5 !border-0 !bg-[#1FBFA7]" /></div>;
}
function TracingEdge({ id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, style, data }: EdgeProps) {
  const [path] = getBezierPath({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition }); const visible = Boolean(data?.visible);
  return <path id={id} d={path} pathLength={1} fill="none" className="cascade-edge" style={{ ...style, opacity: data?.dimmed ? 0.12 : visible ? 1 : 0, strokeDasharray: data?.conditional ? "0.035 0.025" : "1", strokeDashoffset: visible ? 0 : 1 }} />;
}
const nodeTypes: NodeTypes = { problem: ProblemGraphNode }; const edgeTypes = { tracing: TracingEdge };

export function CrisisGraph({ simulation }: { simulation: CrisisSimulation }) {
  const sequence = useMemo(() => buildCascadeSequence(simulation.graph_nodes, simulation.graph_edges), [simulation]);
  const layout = useMemo(() => buildCascadeLayout(simulation.graph_nodes, simulation.graph_edges), [simulation]);
  const containerRef = useRef<HTMLElement>(null);
  const [started, setStarted] = useState(false); const [step, setStep] = useState(0); const [paused, setPaused] = useState(false); const [selectedId, setSelectedId] = useState<string | null>(null);
  useEffect(() => { const element = containerRef.current; if (!element || started) return; const observer = new IntersectionObserver(([entry]) => { if (entry.isIntersecting && entry.intersectionRatio >= 0.35) { setStarted(true); observer.disconnect(); } }, { threshold: [0.35, 0.5] }); observer.observe(element); return () => observer.disconnect(); }, [started]);
  useEffect(() => { if (!started) return; const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches; if (paused || step >= sequence.length) return; const timer = window.setTimeout(() => setStep((value) => reduced ? sequence.length : value + 1), reduced ? 0 : sequence[step]?.type === "node" ? 650 : 220); return () => window.clearTimeout(timer); }, [paused, sequence, started, step]);
  const visibleNodes = new Set(sequence.slice(0, step).filter((event) => event.type === "node").map((event) => event.id));
  const visibleEdges = new Set(sequence.slice(0, step).filter((event) => event.type === "edge").map((event) => event.id));
  const related = selectedId ? new Set([selectedId, ...simulation.graph_edges.filter((edge) => edge.source === selectedId).map((edge) => edge.target), ...simulation.graph_edges.filter((edge) => edge.target === selectedId).map((edge) => edge.source)]) : new Set(simulation.graph_nodes.map((node) => node.id));
  const complete = step >= sequence.length; const statuses = Object.fromEntries(simulation.graph_nodes.map((item) => [item.id, item.status]));
  const nodes: FlowProblemNode[] = simulation.graph_nodes.map((item) => ({ id: item.id, type: "problem", position: layout[item.id], data: { label: item.label, status: item.status, revealed: complete || visibleNodes.has(item.id), dimmed: !related.has(item.id) } }));
  const edges: Edge[] = simulation.graph_edges.map((item) => ({ id: item.id, type: "tracing", source: item.source, target: item.target, data: { visible: complete || visibleEdges.has(item.id), conditional: statuses[item.target] !== "projected", dimmed: !(related.has(item.source) && related.has(item.target)) }, style: { stroke: statuses[item.target] === "projected" ? "#1FBFA7" : "#98a09f", strokeWidth: statuses[item.target] === "projected" ? 2.5 : 1.4 } }));
  const selected = simulation.graph_nodes.find((item) => item.id === selectedId) ?? simulation.graph_nodes[0];
  return <article ref={containerRef} className="overflow-hidden rounded-[2rem] bg-[#1A2122] text-white shadow-2xl"><div className="flex flex-col justify-between gap-5 border-b border-white/10 p-6 sm:flex-row sm:items-end sm:p-8"><div><p className="font-brand text-sm text-[#1FBFA7]">The ripple effect</p><h2 className="font-display mt-1 text-3xl">Watch one disruption spread</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-white/60">Each line reaches a consequence before it appears. Select a node for a short explanation.</p></div><div className="flex flex-wrap gap-2"><button type="button" onClick={() => setPaused((v) => !v)} className="graph-control">{paused ? "Resume" : "Pause"}</button><button type="button" onClick={() => { setStarted(true); setPaused(false); setStep(0); setSelectedId(null); }} className="graph-control">Replay</button><button type="button" onClick={() => { setStarted(true); setStep(sequence.length); }} className="graph-control">Skip animation</button></div></div><div className="relative h-[46rem] bg-[#151b1c] sm:h-[54rem]"><ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} edgeTypes={edgeTypes} onNodeClick={(_, node) => setSelectedId(node.id)} fitView fitViewOptions={{ padding: 0.08 }} minZoom={0.42} maxZoom={1.6} nodesDraggable={false} nodesConnectable={false} elementsSelectable proOptions={{ hideAttribution: true }}><Background color="#384142" gap={28} size={1} /><Controls showInteractive={false} /></ReactFlow>{selectedId && selected ? <aside className="absolute bottom-5 left-5 right-5 z-10 max-w-md rounded-2xl border border-white/10 bg-[#1A2122]/95 p-5 shadow-2xl backdrop-blur sm:right-auto"><button type="button" aria-label="Close problem details" onClick={() => setSelectedId(null)} className="absolute right-4 top-3 text-lg text-white/50 hover:text-white">×</button><h3 className="font-brand pr-6 text-lg">{selected.label}</h3><p className="mt-2 text-sm leading-6 text-white/65">{selected.description}</p>{selected.amount_cents !== null || selected.activation_date ? <p className="mt-3 text-xs text-[#1FBFA7]">{selected.amount_cents !== null ? formatCurrency(selected.amount_cents) : ""}{selected.amount_cents !== null && selected.activation_date ? " · " : ""}{selected.activation_date ? formatDate(selected.activation_date) : ""}</p> : null}<details className="mt-3 text-xs text-white/50"><summary className="cursor-pointer">Why this appears</summary><p className="mt-2 leading-5">{selected.evidence}</p></details></aside> : null}</div></article>;
}
