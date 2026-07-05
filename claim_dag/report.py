from __future__ import annotations

from collections import Counter
from typing import Any

from .graph import analyze, claim_map


def build_report(claims: list[dict[str, Any]], edges: list[dict[str, Any]]) -> str:
    analysis = analyze(claims, edges)
    claims_by_id = claim_map(claims)
    claim_types = Counter(claim.get("type", "unknown") for claim in claims if isinstance(claim, dict))
    claim_statuses = Counter(claim.get("status", "unknown") for claim in claims if isinstance(claim, dict))
    edge_statuses = Counter(edge.get("status", "unknown") for edge in edges if isinstance(edge, dict))

    lines = [
        "# Claim DAG Audit Report",
        "",
        "## Summary",
        "",
        f"- Claims: {len(claims)}",
        f"- Edges: {len(edges)}",
        f"- Claim validation errors: {len(analysis['claim_errors'])}",
        f"- Edge validation errors: {len(analysis['edge_errors'])}",
        f"- Unsupported inference nodes: {len(analysis['unsupported_inferences'])}",
        f"- Decorative premise nodes: {len(analysis['decorative_premises'])}",
        f"- Cycles: {len(analysis['cycles'])}",
        "",
        "## Claim Types",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in sorted(claim_types.items()))
    lines.extend(["", "## Claim Statuses", ""])
    lines.extend(f"- {key}: {value}" for key, value in sorted(claim_statuses.items()))
    lines.extend(["", "## Edge Statuses", ""])
    lines.extend(f"- {key}: {value}" for key, value in sorted(edge_statuses.items()))

    add_messages(lines, "Claim Errors", analysis["claim_errors"])
    add_messages(lines, "Claim Warnings", analysis["claim_warnings"])
    add_messages(lines, "Edge Errors", analysis["edge_errors"])
    add_messages(lines, "Edge Warnings", analysis["edge_warnings"])
    add_claim_list(lines, "Unsupported Inference Nodes", analysis["unsupported_inferences"], claims_by_id)
    add_claim_list(lines, "Decorative Premise Nodes", analysis["decorative_premises"], claims_by_id)

    lines.extend(["", "## Cycles", ""])
    if analysis["cycles"]:
        lines.extend("- " + " -> ".join(cycle) for cycle in analysis["cycles"])
    else:
        lines.append("- none")

    lines.extend([
        "",
        "## Next Audit Moves",
        "",
        "- Fill missing suppressed premises on edge records.",
        "- Audit every unsupported inference or rewrite the graph.",
        "- Decide whether decorative premises should be connected, cut, or marked as background.",
        "- Send the three weakest uncleared edges to an adversarial pass.",
    ])
    return "\n".join(lines) + "\n"


def add_messages(lines: list[str], title: str, messages: list[str]) -> None:
    lines.extend(["", f"## {title}", ""])
    if messages:
        lines.extend(f"- {message}" for message in messages)
    else:
        lines.append("- none")


def add_claim_list(
    lines: list[str],
    title: str,
    claim_ids: list[str],
    claims_by_id: dict[str, dict[str, Any]],
) -> None:
    lines.extend(["", f"## {title}", ""])
    if not claim_ids:
        lines.append("- none")
        return
    for cid in claim_ids:
        anchor = claims_by_id.get(cid, {}).get("anchor", "")
        lines.append(f"- `{cid}`: {anchor}")

