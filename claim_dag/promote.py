"""Derive claim/edge verdicts from audit artifacts. Pure and model-free: it
reads what the auditors returned and writes the implied verdicts back into
claims.yaml / edges.yaml. `cleared` requires the same bar validate enforces;
dissent (any failed/weakened artifact) demotes; inference verdicts propagate
from their supporting edges and sources (a conclusion is only as cleared as its
weakest support)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .audits import DEFAULT_MIN_FAMILIES, artifacts_by_target
from .graph import _edge_endpoints, load_audit
from .io import read_yaml, write_yaml
from .schema import (
    NON_SUPPORTING_RELATIONS,
    REFUTE_FRAMING,
    RESOLVED_DEFEATERS,
    STRONG_TIERS,
    SUPPORTING_RELATIONS,
)
from .source import artifact_matches_source


CLEARED_SEVERITY_FIELDS = (
    "could_have_failed",
    "failure_mode",
    "attack",
    "evidence_checked",
    "source_span",
)


def implied_verdict(
    arts: list[dict[str, Any]],
    builder_family: str | None,
    min_families: int,
    source_sha: str | None = None,
) -> str | None:
    """Verdict implied by a target's own audit artifacts, or None if they do
    not yet establish one. Mirrors audits.enforce_audit_backing."""
    dissent = [a for a in arts if a.get("verdict") in {"failed", "weakened"}]
    if dissent:
        return "failed" if any(a.get("verdict") == "failed" for a in dissent) else "weakened"
    clears = [
        a
        for a in arts
        if a.get("verdict") == "cleared"
        and a.get("framing") == REFUTE_FRAMING
        and all(str(a.get(key, "")).strip() for key in CLEARED_SEVERITY_FIELDS)
        and str(a.get("tier", "")).strip()
        and artifact_matches_source(a, source_sha)
    ]
    families = {a.get("family") for a in clears if a.get("family")}
    independent = families - ({builder_family} if builder_family else set())
    strong = any(a.get("tier") in STRONG_TIERS for a in clears if a.get("family") in independent)
    if len(independent) >= min_families and strong:
        return "cleared"
    return None


def _defeater_caps(edges: list[dict]) -> dict[str, str]:
    caps: dict[str, str] = {}
    for edge in edges:
        if not isinstance(edge, dict) or edge.get("relation") not in NON_SUPPORTING_RELATIONS:
            continue
        target, _ = _edge_endpoints(edge)
        if target is None:
            continue
        resolution = edge.get("resolution", "open")
        if resolution == "accepted":
            caps[target] = "weakened"
        elif resolution not in RESOLVED_DEFEATERS:
            caps.setdefault(target, "unaudited")
    return caps


def _cap(verdict_value: str, cap: str | None) -> str:
    if cap is None:
        return verdict_value
    if verdict_value in {"failed", "weakened"}:
        return verdict_value
    if verdict_value == "cleared":
        return cap
    if verdict_value == "unaudited" and cap == "weakened":
        return "weakened"
    return verdict_value


def _propagate(
    verdict: dict[str, str], claims: list[dict], edges: list[dict], caps: dict[str, str]
) -> None:
    """Resolve inference verdicts from their supporting edges + sources, to a
    fixpoint so chains of inferences settle."""
    supporting = [e for e in edges if isinstance(e, dict)
                  and e.get("relation") in SUPPORTING_RELATIONS]
    inferences = [c["id"] for c in claims if isinstance(c, dict)
                  and c.get("type") == "inference" and "id" in c]
    changed = True
    while changed:
        changed = False
        for cid in inferences:
            inputs: list[str] = []
            for edge in supporting:
                target, sources = _edge_endpoints(edge)
                if target != cid:
                    continue
                inputs.append(verdict.get(edge.get("id", ""), "unaudited"))
                inputs.extend(verdict.get(s, "unaudited") for s in sources)
            if not inputs:
                new = "unaudited"
            elif any(i == "failed" for i in inputs):
                new = "failed"
            elif any(i == "weakened" for i in inputs):
                new = "weakened"
            elif all(i == "cleared" for i in inputs):
                new = "cleared"
            else:
                new = "unaudited"
            new = _cap(new, caps.get(cid))
            if verdict.get(cid) != new:
                verdict[cid] = new
                changed = True


def compute_verdicts(
    claims: list[dict], edges: list[dict], audit_dir: Path, min_families: int
) -> dict[str, str]:
    manifest = read_yaml(audit_dir / "source-manifest.yaml", {})
    builder = manifest.get("built_by") if isinstance(manifest, dict) else None
    source_sha = manifest.get("source_sha256") if isinstance(manifest, dict) else None
    node_arts, edge_arts = artifacts_by_target(audit_dir)
    caps = _defeater_caps(edges)

    verdict: dict[str, str] = {}
    for edge in edges:
        if isinstance(edge, dict) and "id" in edge:
            verdict[edge["id"]] = implied_verdict(
                edge_arts.get(edge["id"], []), builder, min_families, source_sha) or "unaudited"
    for claim in claims:
        if not isinstance(claim, dict) or "id" not in claim:
            continue
        if claim.get("type") == "inference":
            verdict[claim["id"]] = "unaudited"  # resolved by propagation
        else:
            own_verdict = implied_verdict(
                node_arts.get(claim["id"], []), builder, min_families, source_sha
            ) or "unaudited"
            verdict[claim["id"]] = _cap(own_verdict, caps.get(claim["id"]))

    _propagate(verdict, claims, edges, caps)
    return verdict


def promote(
    audit_dir: Path, min_families: int = DEFAULT_MIN_FAMILIES, write: bool = True
) -> list[dict[str, str]]:
    """Recompute every verdict from artifacts and write the changes back.
    Returns the list of changes (id, old, new)."""
    claims, edges = load_audit(audit_dir)
    verdict = compute_verdicts(claims, edges, audit_dir, min_families)

    changes: list[dict[str, str]] = []
    for record in [*claims, *edges]:
        if not isinstance(record, dict) or "id" not in record:
            continue
        rid = record["id"]
        old = record.get("verdict", "unaudited")
        new = verdict.get(rid, "unaudited")
        if new != old:
            changes.append({"id": rid, "old": old, "new": new})
            record["verdict"] = new

    if write and changes:
        write_yaml(audit_dir / "claims.yaml", claims)
        write_yaml(audit_dir / "edges.yaml", edges)
    return changes
