from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .io import read_yaml, write_yaml
from .schema import BACKED_VERDICTS
from .source import source_status

COMPARE_FIELDS = ("anchor", "type", "section", "warrant", "source", "evidence", "notes")
EDGE_COMPARE_FIELDS = ("from", "to", "relation", "suppressed_premise", "resolution", "notes")


def _records_by_id(records: list[dict]) -> dict[str, dict[str, Any]]:
    return {r["id"]: r for r in records if isinstance(r, dict) and isinstance(r.get("id"), str)}


def _normalize(text: Any) -> str:
    return " ".join(str(text or "").split()).lower()


def _field_changes(old: dict[str, Any], new: dict[str, Any], fields: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    changes: dict[str, dict[str, Any]] = {}
    for field in fields:
        if old.get(field) != new.get(field):
            changes[field] = {"old": old.get(field), "new": new.get(field)}
    return changes


def graph_diff(
    claims: list[dict],
    edges: list[dict],
    candidate_claims: list[dict],
    candidate_edges: list[dict],
    audit_dir: Path | None = None,
) -> dict[str, Any]:
    base_claims = _records_by_id(claims)
    cand_claims = _records_by_id(candidate_claims)
    base_edges = _records_by_id(edges)
    cand_edges = _records_by_id(candidate_edges)

    base_anchors = {_normalize(c.get("anchor")): cid for cid, c in base_claims.items() if c.get("anchor")}
    added_claims = []
    for cid, claim in sorted(cand_claims.items()):
        if cid in base_claims:
            continue
        anchor_match = base_anchors.get(_normalize(claim.get("anchor")))
        added_claims.append({
            "id": cid,
            "anchor": claim.get("anchor"),
            "matches_existing_anchor": anchor_match,
        })

    changed_claims = []
    for cid in sorted(base_claims.keys() & cand_claims.keys()):
        changes = _field_changes(base_claims[cid], cand_claims[cid], COMPARE_FIELDS)
        if changes:
            changed_claims.append({"id": cid, "changes": changes})

    changed_edges = []
    for eid in sorted(base_edges.keys() & cand_edges.keys()):
        changes = _field_changes(base_edges[eid], cand_edges[eid], EDGE_COMPARE_FIELDS)
        if changes:
            changed_edges.append({"id": eid, "changes": changes})

    missing_anchors: list[str] = []
    if audit_dir is not None:
        status = source_status(audit_dir, candidate_claims, candidate_edges)
        missing_anchors = status["missing_anchors"]

    unsafe = []
    unsafe.extend({"id": c["id"], "kind": "claim", "reason": "added"} for c in added_claims)
    unsafe.extend(
        {"id": cid, "kind": "claim", "reason": "removed"}
        for cid in sorted(base_claims.keys() - cand_claims.keys())
    )
    unsafe.extend({"id": c["id"], "kind": "claim", "reason": "changed"} for c in changed_claims)
    unsafe.extend(
        {"id": eid, "kind": "edge", "reason": "added"}
        for eid in sorted(cand_edges.keys() - base_edges.keys())
    )
    unsafe.extend(
        {"id": eid, "kind": "edge", "reason": "removed"}
        for eid in sorted(base_edges.keys() - cand_edges.keys())
    )
    unsafe.extend({"id": e["id"], "kind": "edge", "reason": "changed"} for e in changed_edges)
    unsafe.extend({"id": cid, "kind": "claim", "reason": "missing_anchor"} for cid in missing_anchors)

    return {
        "claim_changes": {
            "added": added_claims,
            "removed": sorted(base_claims.keys() - cand_claims.keys()),
            "changed": changed_claims,
        },
        "edge_changes": {
            "added": sorted(cand_edges.keys() - base_edges.keys()),
            "removed": sorted(base_edges.keys() - cand_edges.keys()),
            "changed": changed_edges,
        },
        "missing_anchors": missing_anchors,
        "unsafe_changes": unsafe,
    }


def reconstruction_candidates(run_dir: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for claims_path in sorted(run_dir.glob("claims.*.yaml")):
        suffix = claims_path.name.removeprefix("claims.").removesuffix(".yaml")
        edges_path = run_dir / f"edges.{suffix}.yaml"
        if edges_path.exists():
            out.append({"id": suffix, "claims": claims_path, "edges": edges_path})
    return out


def _reset_verdict(record: dict[str, Any]) -> None:
    if record.get("verdict") in BACKED_VERDICTS:
        record["verdict"] = "unaudited"


def _edge_claim_ids(edge: dict[str, Any]) -> set[str]:
    ids = set()
    target = edge.get("to")
    if isinstance(target, str):
        ids.add(target)
    sources = edge.get("from", [])
    if isinstance(sources, list):
        ids.update(source for source in sources if isinstance(source, str))
    return ids


def _invalidate_touched_records(
    claims: list[dict],
    edges: list[dict],
    old_edges: list[dict],
    claim_changes: list[dict[str, str]],
    edge_changes: list[dict[str, str]],
) -> None:
    claim_ids = {c["id"] for c in claim_changes if c["action"] in {"added", "changed", "removed"}}
    edge_ids = {e["id"] for e in edge_changes if e["action"] in {"added", "changed", "removed"}}
    claim_by_id = _records_by_id(claims)
    old_edge_by_id = _records_by_id(old_edges)

    for edge in edges:
        if not isinstance(edge, dict) or "id" not in edge:
            continue
        endpoints = _edge_claim_ids(edge)
        if edge["id"] in edge_ids or endpoints & claim_ids:
            _reset_verdict(edge)
        if edge["id"] in edge_ids:
            for cid in endpoints:
                if cid in claim_by_id:
                    _reset_verdict(claim_by_id[cid])

    for eid in edge_ids:
        old_edge = old_edge_by_id.get(eid)
        if not old_edge:
            continue
        for cid in _edge_claim_ids(old_edge):
            if cid in claim_by_id:
                _reset_verdict(claim_by_id[cid])


def _merge_records(
    base_records: list[dict],
    candidate_records: list[dict],
    fields: tuple[str, ...],
    accept_removals: bool,
) -> tuple[list[dict], list[dict[str, str]]]:
    base = _records_by_id(base_records)
    candidate = _records_by_id(candidate_records)
    merged: list[dict] = []
    changes: list[dict[str, str]] = []

    for rid in sorted(base.keys() | candidate.keys()):
        if rid in base and rid not in candidate:
            if accept_removals:
                changes.append({"id": rid, "action": "removed"})
                continue
            merged.append(dict(base[rid]))
            changes.append({"id": rid, "action": "kept_removed_candidate"})
            continue
        if rid not in base and rid in candidate:
            record = dict(candidate[rid])
            record["verdict"] = "unaudited"
            merged.append(record)
            changes.append({"id": rid, "action": "added"})
            continue

        old = base[rid]
        candidate_record = candidate[rid]
        # Reconstructors usually emit only graph fields. Preserve local
        # annotations/metadata while applying explicit graph-field changes.
        new = dict(old)
        for field in fields:
            if field in candidate_record:
                new[field] = candidate_record[field]
        field_changes = _field_changes(old, new, fields)
        if field_changes:
            _reset_verdict(new)
            changes.append({"id": rid, "action": "changed"})
        else:
            new["verdict"] = old.get("verdict", candidate_record.get("verdict", "unaudited"))
        merged.append(new)

    return merged, changes


def reconcile_candidate(
    audit_dir: Path,
    run_dir: Path,
    candidate_id: str | None = None,
    write: bool = False,
    accept_removals: bool = False,
) -> dict[str, Any]:
    candidates = reconstruction_candidates(run_dir)
    if not candidates:
        return {"ok": False, "error": "no reconstruction candidates found", "candidates": []}
    if candidate_id is None:
        if len(candidates) != 1:
            return {
                "ok": False,
                "error": "multiple candidates; pass --candidate",
                "candidates": [c["id"] for c in candidates],
            }
        selected = candidates[0]
    else:
        selected = next((c for c in candidates if c["id"] == candidate_id), None)
        if selected is None:
            return {
                "ok": False,
                "error": f"unknown candidate {candidate_id}",
                "candidates": [c["id"] for c in candidates],
            }

    claims = read_yaml(audit_dir / "claims.yaml", [])
    edges = read_yaml(audit_dir / "edges.yaml", [])
    candidate_claims = read_yaml(selected["claims"], [])
    candidate_edges = read_yaml(selected["edges"], [])
    diff = graph_diff(claims, edges, candidate_claims, candidate_edges, audit_dir)

    new_claims, claim_changes = _merge_records(
        claims, candidate_claims, COMPARE_FIELDS, accept_removals
    )
    new_edges, edge_changes = _merge_records(
        edges, candidate_edges, EDGE_COMPARE_FIELDS, accept_removals
    )
    _invalidate_touched_records(new_claims, new_edges, edges, claim_changes, edge_changes)
    result = {
        "ok": True,
        "candidate": selected["id"],
        "diff": diff,
        "claim_changes": claim_changes,
        "edge_changes": edge_changes,
        "write": write,
    }
    if not write:
        return result

    write_yaml(audit_dir / "claims.yaml", new_claims)
    write_yaml(audit_dir / "edges.yaml", new_edges)
    log = read_yaml(audit_dir / "reconciliation-log.yaml", [])
    if not isinstance(log, list):
        log = []
    log.append({
        "date": datetime.now().astimezone().isoformat(timespec="seconds"),
        "run_dir": str(run_dir),
        "candidate": selected["id"],
        "accept_removals": accept_removals,
        "claim_changes": claim_changes,
        "edge_changes": edge_changes,
    })
    write_yaml(audit_dir / "reconciliation-log.yaml", log)
    return result
