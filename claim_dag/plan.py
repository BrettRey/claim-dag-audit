from __future__ import annotations

from pathlib import Path
from typing import Any

from .audits import artifacts_by_target
from .io import read_yaml
from .policy import DEFAULT_POLICY
from .schema import STRONG_TIERS
from .source import artifact_matches_source


def _jobs_for(
    tid: str,
    kind: str,
    prompt: str,
    arts: list[dict[str, Any]],
    builder_family: str | None,
    source_sha: str | None,
    min_families: int,
    policy: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Return (audit jobs, revise-note). A dissenting artifact routes the target
    to revision instead of more audits."""
    if source_sha:
        arts = [a for a in arts if artifact_matches_source(a, source_sha)]
    dissent = [a for a in arts if a.get("verdict") in {"failed", "weakened"}]
    if dissent:
        worst = "failed" if any(a.get("verdict") == "failed" for a in dissent) else "weakened"
        return [], {"target": tid, "kind": kind, "verdict": worst,
                    "reason": "an independent audit broke it; revise before re-auditing"}

    cleared = [a for a in arts if a.get("verdict") == "cleared"]
    have_families = {a.get("family") for a in cleared if a.get("family")}
    have_families -= {builder_family} if builder_family else set()
    have_strong = any(
        a.get("tier") in STRONG_TIERS for a in cleared if a.get("family") in have_families
    )

    jobs: list[dict[str, Any]] = []
    assigned: set[str] = set(have_families)
    strong_ok = have_strong
    for entry in policy:
        if len(assigned) >= min_families and strong_ok:
            break
        fam = entry["family"]
        if fam == builder_family or fam in assigned:
            continue
        # Only add a cheap-tier family if we still need families; always allow a
        # strong-tier family through until one is present.
        need_family = len(assigned) < min_families
        need_strong = not strong_ok and entry["tier"] in STRONG_TIERS
        if not (need_family or need_strong):
            continue
        jobs.append({
            "target": tid, "kind": kind, "action": "audit",
            "framing": "refute", "prompt": prompt,
            "model": entry["model"], "family": fam, "tier": entry["tier"],
            "effort": entry["effort"], "runner": entry["runner"],
        })
        assigned.add(fam)
        if entry["tier"] in STRONG_TIERS:
            strong_ok = True
    return jobs, None


def build_plan(
    claims: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    audit_dir: Path,
    min_families: int = 2,
    policy: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    policy = policy or DEFAULT_POLICY
    manifest = read_yaml(audit_dir / "source-manifest.yaml", {})
    builder_family = manifest.get("built_by") if isinstance(manifest, dict) else None
    source_sha = manifest.get("source_sha256") if isinstance(manifest, dict) else None
    node_by_id, edge_by_id = artifacts_by_target(audit_dir)

    jobs: list[dict[str, Any]] = []
    revise: list[dict[str, Any]] = []

    for claim in claims:
        if not isinstance(claim, dict) or "id" not in claim:
            continue
        if claim.get("type") == "inference":
            # Inference clearance comes from its edges + coherence, not a node audit.
            continue
        j, r = _jobs_for(claim["id"], "node", "prompts/audit-node.md",
                         node_by_id.get(claim["id"], []), builder_family, source_sha,
                         min_families, policy)
        jobs.extend(j)
        if r:
            revise.append(r)

    for edge in edges:
        if not isinstance(edge, dict) or "id" not in edge:
            continue
        j, r = _jobs_for(edge["id"], "edge", "prompts/audit-edge.md",
                         edge_by_id.get(edge["id"], []), builder_family, source_sha,
                         min_families, policy)
        jobs.extend(j)
        if r:
            revise.append(r)

    return {
        "audit_dir": str(audit_dir),
        "min_families": min_families,
        "builder_family": builder_family,
        "job_count": len(jobs),
        "jobs": jobs,
        "revise": revise,
    }
