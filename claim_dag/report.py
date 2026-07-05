from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .audits import enforce_audit_backing
from .graph import analyze, claim_map


def build_report(
    claims: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    audit_dir: Path | None = None,
) -> str:
    analysis = analyze(claims, edges)
    claims_by_id = claim_map(claims)
    claim_types = Counter(claim.get("type", "unknown") for claim in claims if isinstance(claim, dict))
    claim_verdicts = Counter(claim.get("verdict", "unknown") for claim in claims if isinstance(claim, dict))
    edge_verdicts = Counter(edge.get("verdict", "unknown") for edge in edges if isinstance(edge, dict))
    relations = Counter(edge.get("relation", "unknown") for edge in edges if isinstance(edge, dict))

    backing = enforce_audit_backing(claims, edges, audit_dir) if audit_dir is not None else None

    lines = [
        "# Claim DAG Audit Report",
        "",
        "## Summary",
        "",
        f"- Claims: {len(claims)}",
        f"- Edges: {len(edges)}",
        f"- Claim validation errors: {len(analysis['claim_errors'])}",
        f"- Edge validation errors: {len(analysis['edge_errors'])}",
        f"- Coherence errors: {len(analysis['coherence_errors'])}",
        f"- Defeater errors: {len(analysis['defeater_errors'])}",
        f"- Unsupported inference nodes: {len(analysis['unsupported_inferences'])}",
        f"- Decorative premise nodes: {len(analysis['decorative_premises'])}",
        f"- Cycles: {len(analysis['cycles'])}",
    ]
    if backing is not None:
        lines.append(f"- Audit-backing errors: {len(backing.errors)}")
    lines.extend(["", "## Claim Types", ""])
    lines.extend(f"- {key}: {value}" for key, value in sorted(claim_types.items()))
    lines.extend(["", "## Claim Verdicts", ""])
    lines.extend(f"- {key}: {value}" for key, value in sorted(claim_verdicts.items()))
    lines.extend(["", "## Edge Relations", ""])
    lines.extend(f"- {key}: {value}" for key, value in sorted(relations.items()))
    lines.extend(["", "## Edge Verdicts", ""])
    lines.extend(f"- {key}: {value}" for key, value in sorted(edge_verdicts.items()))

    add_messages(lines, "Claim Errors", analysis["claim_errors"])
    add_messages(lines, "Claim Warnings", analysis["claim_warnings"])
    add_messages(lines, "Edge Errors", analysis["edge_errors"])
    add_messages(lines, "Edge Warnings", analysis["edge_warnings"])
    add_messages(lines, "Coherence Errors", analysis["coherence_errors"])
    add_messages(lines, "Defeater Errors", analysis["defeater_errors"])
    if backing is not None:
        add_messages(lines, "Audit-Backing Errors", backing.errors)
        add_messages(lines, "Audit-Backing Warnings", backing.warnings)
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
        "- Run `claim-dag plan` to emit the audit jobs still needed to clear.",
        "- Audit every unsupported inference or rewrite the graph.",
        "- Decide whether decorative premises should be connected, cut, or marked `background: true`.",
        "- Route any failed/weakened target to revision before re-auditing.",
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
