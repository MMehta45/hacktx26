import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ResearchStage } from "./research-stage";
import type { ResearchResult } from "@/types/research";

const research = {
  status: "partial",
  run_id: "test",
  simulation_fingerprint: "test",
  priority_targets: [{ node_id: "commute_disrupted", impact: 3, urgency: 3, actionability: 3, priority_score: 27, reason: "Two shifts threatened." }],
  hypotheses: [{ id: "remote_work", title: "Temporarily work remotely", mechanism: "income_preservation", target_node_ids: ["missed_work"], impact: 3, urgency: 3, actionability: 3, priority_score: 27, evidence_need: "Ask Maya", investigation_mode: "ask_user", suggested_tool: null, suggested_query: null, origin: "baseline" }],
  pathways: [{ id: "transportation", label: "Public transportation", status: "successful", target_node_ids: ["commute_disrupted"], tool_calls_used: 2, evidence_ids: ["evidence-1"], message: "Collected route evidence." }],
  research_events: [{ id: "event-1", type: "search_completed", timestamp: "2026-10-24T12:00:00Z", message: "search_web returned one result.", target_node_id: null, tool: "search_web", evidence_id: null }],
  evidence: [{ id: "evidence-1", source_type: "web", provider_engine: "google", title: "Official resource", url: "https://example.gov/resource", query: "resource", retrieved_at: "2026-10-24T12:00:00Z", facts_supported: [], limitations: ["Eligibility unknown"], snippet: null, source_domain: "example.gov", observed_cost_cents: null }],
  candidate_actions: [{ id: "candidate-1", title: "Ask about assistance", mechanism: "assistance", addresses_node_ids: ["bills_unpaid"], description: "A possible program.", requirements: [{ key: "eligibility", status: "unknown", description: "Eligibility requires confirmation", verification_source_ids: [] }], cost: { amount_cents: null, currency: "USD", status: "unknown", basis: "No quoted amount" }, timing: { earliest_start_date: null, latest_completion_date: null, duration_description: "Ask provider" }, evidence_ids: ["evidence-1"], verification_status: "conditional", remaining_unknowns: ["eligibility"], confidence_explanation: "Program listing only" }],
  clarifying_questions: [{ id: "question-1", question: "Are you eligible?", addresses_node_ids: ["bills_unpaid"], related_candidate_ids: ["candidate-1"], resolves_requirement_keys: ["eligibility"], decision_impact: 3, uncertainty: 3, top_candidate_relevance: 2, priority_score: 18, reason: "Changes viability", answer_type: "yes_no", status: "pending" }],
  initial_question_ids: ["question-1"],
  tool_calls_used: 1, cache_hits: 0, warnings: [],
} as unknown as ResearchResult;

describe("Explore stage", () => {
  it("renders evidence, unknown requirements, pending questions and recorded events", () => {
    const html = renderToStaticMarkup(<ResearchStage research={research} loading={false} error={null} home="3810 N Lamar Blvd" work="525 N Lamar Blvd" shiftStart="08:00" shiftEnd="16:00" onContextChange={() => undefined} onRun={() => undefined} onBack={() => undefined} onNext={() => undefined} />);
    expect(html).toContain("https://example.gov/resource");
    expect(html).toContain("Eligibility requires confirmation");
    expect(html).toContain("Are you eligible?");
    expect(html).toContain("search_web returned one result");
    expect(html).toContain("conditional");
    expect(html).toContain("Cedarstone Services");
    expect(html).toContain('value="08:00"');
    expect(html).toContain('value="16:00"');
    expect(html).not.toContain("bills saved");
  });
});
