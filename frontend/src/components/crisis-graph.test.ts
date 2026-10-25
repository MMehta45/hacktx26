import { describe, expect, it } from "vitest";
import { buildCascadeLayout, buildCascadeSequence } from "./crisis-graph";
import type { CrisisSimulation } from "@/types/simulation";

const node = (id: string, status: "projected" | "conditional" = "projected") => ({ id, label: id, description: id, status, activation_date: null, evidence: id, amount_cents: null, source: "projection" as const });
const nodes = [node("car_breaks_down"), node("car_unavailable"), node("commute_disrupted"), node("missed_work"), node("transport_cost", "conditional")];
const edges = [
  { id: "e1", source: "car_breaks_down", target: "car_unavailable", condition: null },
  { id: "e2", source: "car_unavailable", target: "commute_disrupted", condition: null },
  { id: "e3", source: "commute_disrupted", target: "missed_work", condition: null },
  { id: "e4", source: "commute_disrupted", target: "transport_cost", condition: "if used" },
] as CrisisSimulation["graph_edges"];

describe("causal graph presentation", () => {
  it("lays dependencies top-to-bottom and branches on the same layer", () => {
    const layout = buildCascadeLayout(nodes, edges);
    expect(layout.car_breaks_down.y).toBeLessThan(layout.car_unavailable.y);
    expect(layout.car_unavailable.y).toBeLessThan(layout.commute_disrupted.y);
    expect(layout.missed_work.y).toBe(layout.transport_cost.y);
  });

  it("draws each edge before revealing its dependent node", () => {
    const sequence = buildCascadeSequence(nodes, edges);
    expect(sequence[0]).toEqual({ type: "node", id: "car_breaks_down" });
    for (const edge of edges.slice(0, 3)) {
      expect(sequence.findIndex((event) => event.type === "edge" && event.id === edge.id)).toBeLessThan(sequence.findIndex((event) => event.type === "node" && event.id === edge.target));
    }
    expect(sequence.some((event) => event.id === "transport_cost")).toBe(false);
  });
});
