from collections import defaultdict

from app.research_models import PriorityTarget
from app.simulation_models import SimulationResult

MECHANISMS = (
    ("commute_disrupted", "missed_work", "reduced_paycheck"),
    ("bills_unpaid", "cash_shortfall"),
    ("unexpected_repair_expense", "repair_delayed", "car_unavailable"),
    ("extra_transportation_costs", "future_debt_payments"),
)


def rank_targets(simulation: SimulationResult) -> tuple[list[PriorityTarget], list[str]]:
    nodes = {node.id: node for node in simulation.graph_nodes}
    reverse: dict[str, list[str]] = defaultdict(list)
    for edge in simulation.graph_edges:
        reverse[edge.target].append(edge.source)
    unpaid = bool(simulation.unpaid_bills) and nodes["bills_unpaid"].status == "projected"
    root = "bills_unpaid" if unpaid else "cash_shortfall"
    visited: set[str] = set()
    stack = [root]
    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        stack.extend(sorted(reverse[current], reverse=True))

    warnings = (
        []
        if unpaid
        else [
            "No essential bill is currently projected unpaid; research targets near-term risk only."
        ]
    )
    selected: list[PriorityTarget] = []
    for group in MECHANISMS:
        options: list[PriorityTarget] = []
        for node_id in group:
            node = nodes.get(node_id)
            if (
                node_id not in visited
                or node is None
                or node.status not in {"projected", "conditional"}
            ):
                continue
            if node.status == "conditional" and node_id not in {
                "unexpected_repair_expense",
                "repair_delayed",
            }:
                continue
            impact = (
                3
                if unpaid
                and node_id
                in {
                    "commute_disrupted",
                    "missed_work",
                    "reduced_paycheck",
                    "bills_unpaid",
                    "cash_shortfall",
                }
                else 2
            )
            urgency = (
                3
                if node_id in {"commute_disrupted", "missed_work", "bills_unpaid"} and unpaid
                else 2
            )
            actionability = 3 if node_id in {"commute_disrupted", "bills_unpaid"} else 2
            if node.status == "conditional":
                impact = 1
            reason = f"{node.label}: {node.evidence} " + (
                f"{simulation.unpaid_essential_total_cents} cents of essential bills are uncovered on due dates."
                if unpaid
                else "No essential bill is projected unpaid."
            )
            options.append(
                PriorityTarget(
                    node_id=node_id,
                    impact=impact,
                    urgency=urgency,
                    actionability=actionability,
                    priority_score=impact * urgency * actionability,
                    reason=reason,
                )
            )
        if options:
            selected.append(
                min(options, key=lambda item: (-item.priority_score, -item.urgency, item.node_id))
            )
    return sorted(selected, key=lambda item: (-item.priority_score, -item.urgency, item.node_id))[
        :4
    ], warnings
