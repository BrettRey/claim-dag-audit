from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .io import read_yaml
from .schema import validate_claims, validate_edges


def load_audit(audit_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    claims = read_yaml(audit_dir / "claims.yaml", [])
    edges = read_yaml(audit_dir / "edges.yaml", [])
    return claims, edges


def claim_map(claims: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {claim["id"]: claim for claim in claims if isinstance(claim, dict) and "id" in claim}


def analyze(claims: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, Any]:
    ids = set(claim_map(claims))
    claim_result = validate_claims(claims)
    edge_result = validate_edges(edges, ids)

    incoming: dict[str, set[str]] = defaultdict(set)
    outgoing: dict[str, set[str]] = defaultdict(set)
    adjacency: dict[str, set[str]] = defaultdict(set)

    for edge in edges:
        if not isinstance(edge, dict):
            continue
        target = edge.get("to")
        sources = edge.get("from", [])
        if not isinstance(target, str) or not isinstance(sources, list):
            continue
        for source in sources:
            if isinstance(source, str):
                outgoing[source].add(target)
                incoming[target].add(source)
                adjacency[source].add(target)

    unsupported = []
    decorative = []
    for claim in claims:
        if not isinstance(claim, dict) or "id" not in claim:
            continue
        cid = claim["id"]
        ctype = claim.get("type")
        if ctype == "inference" and not incoming[cid]:
            unsupported.append(cid)
        if ctype in {"definition", "empirical-premise", "cited-claim", "stipulation"} and not outgoing[cid]:
            decorative.append(cid)

    cycles = find_cycles(adjacency, ids)
    return {
        "claim_errors": claim_result.errors,
        "claim_warnings": claim_result.warnings,
        "edge_errors": edge_result.errors,
        "edge_warnings": edge_result.warnings,
        "unsupported_inferences": unsupported,
        "decorative_premises": decorative,
        "cycles": cycles,
        "incoming": {key: sorted(value) for key, value in incoming.items()},
        "outgoing": {key: sorted(value) for key, value in outgoing.items()},
    }


def find_cycles(adjacency: dict[str, set[str]], ids: set[str]) -> list[list[str]]:
    seen: set[str] = set()
    stack: list[str] = []
    in_stack: set[str] = set()
    cycles: list[list[str]] = []

    def visit(node: str) -> None:
        seen.add(node)
        stack.append(node)
        in_stack.add(node)
        for nxt in adjacency.get(node, set()):
            if nxt not in ids:
                continue
            if nxt not in seen:
                visit(nxt)
            elif nxt in in_stack:
                start = stack.index(nxt)
                cycles.append(stack[start:] + [nxt])
        stack.pop()
        in_stack.remove(node)

    for node in sorted(ids):
        if node not in seen:
            visit(node)
    return cycles


def to_argdown(claims: list[dict[str, Any]], edges: list[dict[str, Any]]) -> str:
    lines = ["# Claim DAG", ""]
    for claim in claims:
        cid = claim.get("id", "C???")
        anchor = str(claim.get("anchor", "")).replace("\n", " ")
        ctype = claim.get("type", "unknown")
        lines.append(f"[{cid}]: {anchor}")
        lines.append(f"  # {ctype}; status={claim.get('status', 'unknown')}")
        lines.append("")
    lines.append("# Edges")
    lines.append("")
    for edge in edges:
        target = edge.get("to", "C???")
        sources = edge.get("from", [])
        if not isinstance(sources, list):
            sources = []
        label = edge.get("id", "E???")
        relation = edge.get("relation", "supports")
        for source in sources:
            lines.append(f"[{source}] -> [{target}] # {label}; {relation}; status={edge.get('status', 'unknown')}")
    return "\n".join(lines) + "\n"

