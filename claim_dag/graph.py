from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .io import read_yaml
from .schema import (
    NON_SUPPORTING_RELATIONS,
    SUPPORTING_RELATIONS,
    validate_claims,
    validate_edges,
)


def load_audit(audit_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    claims = read_yaml(audit_dir / "claims.yaml", [])
    edges = read_yaml(audit_dir / "edges.yaml", [])
    return claims, edges


def claim_map(claims: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {claim["id"]: claim for claim in claims if isinstance(claim, dict) and "id" in claim}


def _edge_endpoints(edge: dict[str, Any]) -> tuple[str | None, list[str]]:
    target = edge.get("to")
    sources = edge.get("from", [])
    if not isinstance(target, str) or not isinstance(sources, list):
        return None, []
    return target, [s for s in sources if isinstance(s, str)]


def analyze(claims: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, Any]:
    ids = set(claim_map(claims))
    claims_by_id = claim_map(claims)
    claim_result = validate_claims(claims)
    edge_result = validate_edges(edges, ids)

    # Only supporting relations build the support graph. rebuts/qualifies are
    # tracked separately so a rebuttal never counts as support (Rushby, Mayo).
    incoming: dict[str, set[str]] = defaultdict(set)
    outgoing: dict[str, set[str]] = defaultdict(set)
    adjacency: dict[str, set[str]] = defaultdict(set)
    challenges: dict[str, set[str]] = defaultdict(set)

    for edge in edges:
        if not isinstance(edge, dict):
            continue
        target, sources = _edge_endpoints(edge)
        if target is None:
            continue
        relation = edge.get("relation")
        for source in sources:
            if relation in SUPPORTING_RELATIONS:
                outgoing[source].add(target)
                incoming[target].add(source)
                adjacency[source].add(target)
            elif relation in NON_SUPPORTING_RELATIONS:
                challenges[target].add(source)

    unsupported = []
    decorative = []
    for claim in claims:
        if not isinstance(claim, dict) or "id" not in claim:
            continue
        cid = claim["id"]
        ctype = claim.get("type")
        if ctype == "inference" and not incoming[cid]:
            unsupported.append(cid)
        # Decorative check only fires on non-background premises, so off-spine
        # framing does not cry wolf (van Gelder). Warning, never an error.
        if (
            ctype in {"definition", "empirical-premise", "cited-claim", "stipulation"}
            and not outgoing[cid]
            and not claim.get("background", False)
        ):
            decorative.append(cid)

    cycles = find_cycles(adjacency, ids)
    coherence = verdict_coherence(claims_by_id, edges, incoming)

    return {
        "claim_errors": claim_result.errors,
        "claim_warnings": claim_result.warnings,
        "edge_errors": edge_result.errors,
        "edge_warnings": edge_result.warnings,
        "unsupported_inferences": unsupported,
        "decorative_premises": decorative,
        "cycles": cycles,
        "coherence_errors": coherence,
        "incoming": {key: sorted(value) for key, value in incoming.items()},
        "outgoing": {key: sorted(value) for key, value in outgoing.items()},
        "challenges": {key: sorted(value) for key, value in challenges.items()},
    }


def verdict_coherence(
    claims_by_id: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    incoming: dict[str, set[str]],
) -> list[str]:
    """A node cannot be more cleared than its weakest support. A `cleared`
    inference must have at least one supporting incoming edge, every such edge
    must be `cleared`, and every source claim of those edges must be `cleared`.
    (Mayo: propagate the ceiling; Rushby: a conclusion cannot outrank a failed
    premise.)"""
    errors: list[str] = []
    supporting_edges: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        target, _ = _edge_endpoints(edge)
        if target is not None and edge.get("relation") in SUPPORTING_RELATIONS:
            supporting_edges[target].append(edge)

    for cid, claim in claims_by_id.items():
        if claim.get("verdict") != "cleared":
            continue
        if claim.get("type") != "inference":
            continue
        edges_in = supporting_edges.get(cid, [])
        if not edges_in:
            errors.append(f"{cid}: cleared inference has no supporting edge to clear it")
            continue
        for edge in edges_in:
            eid = edge.get("id", "E???")
            if edge.get("verdict") != "cleared":
                errors.append(
                    f"{cid}: cleared but supporting edge {eid} is {edge.get('verdict', 'unaudited')}"
                )
            _, sources = _edge_endpoints(edge)
            for src in sources:
                src_verdict = claims_by_id.get(src, {}).get("verdict", "unaudited")
                if src_verdict != "cleared":
                    errors.append(
                        f"{cid}: cleared but source {src} (via {eid}) is {src_verdict}"
                    )
    return errors


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


def _hashtags(claim: dict[str, Any]) -> str:
    tags = []
    ctype = claim.get("type")
    if ctype:
        tags.append(f"#{ctype}")
    verdict = claim.get("verdict")
    if verdict:
        tags.append(f"#verdict-{verdict}")
    return (" " + " ".join(tags)) if tags else ""


def to_argdown(claims: list[dict[str, Any]], edges: list[dict[str, Any]]) -> str:
    """Emit valid Argdown. Support edges become premise-conclusion arguments so
    a conjunctive premise set (from: [C001, C002]) reads as one joint inference,
    not two independent arrows (Betz). rebuts becomes an incoming attack `<-`;
    qualifies is rendered as a note, since Argdown has no qualify relation and
    an attack arrow would misrepresent it."""
    claims_by_id = claim_map(claims)
    lines = ["# Claim DAG", "", "// Statements", ""]
    for claim in claims:
        cid = claim.get("id", "C???")
        anchor = str(claim.get("anchor", "")).replace("\n", " ")
        lines.append(f"[{cid}]: {anchor}{_hashtags(claim)}")
    lines.extend(["", "// Arguments (supporting edges: joint premises -> conclusion)", ""])

    for edge in edges:
        if not isinstance(edge, dict):
            continue
        relation = edge.get("relation")
        if relation not in SUPPORTING_RELATIONS:
            continue
        target, sources = _edge_endpoints(edge)
        if target is None or not sources:
            continue
        eid = edge.get("id", "E???")
        verdict = edge.get("verdict", "unaudited")
        lines.append(f"<{eid}>: {relation} #verdict-{verdict}")
        lines.append("")
        n = 0
        for src in sources:
            n += 1
            lines.append(f"({n}) [{src}]")
        suppressed = edge.get("suppressed_premise")
        if suppressed:
            n += 1
            supp = str(suppressed).replace("\n", " ")
            lines.append(f"({n}) {supp}  // suppressed premise")
        lines.append("-----")
        lines.append(f"({n + 1}) [{target}]")
        lines.append("")

    attacks = [e for e in edges if isinstance(e, dict) and e.get("relation") == "rebuts"]
    quals = [e for e in edges if isinstance(e, dict) and e.get("relation") == "qualifies"]
    if attacks or quals:
        lines.extend(["// Attacks and qualifications", ""])
    for edge in attacks:
        target, sources = _edge_endpoints(edge)
        if target is None:
            continue
        lines.append(f"[{target}]")
        for src in sources:
            lines.append(f"  <- [{src}]  // {edge.get('id', 'E???')} rebuts")
        lines.append("")
    for edge in quals:
        target, sources = _edge_endpoints(edge)
        if target is None:
            continue
        joined = ", ".join(sources)
        lines.append(f"[{target}]")
        lines.append(f"  // qualified by {joined} via {edge.get('id', 'E???')}")
        lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"
