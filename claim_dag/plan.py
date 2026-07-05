from __future__ import annotations

from pathlib import Path
from typing import Any

from .audits import artifacts_by_target
from .io import read_yaml
from .schema import STRONG_TIERS

# Ordered tier policy, grounded in the CLIs and local models installed on this
# machine (see docs/llm-runner.md). Cheap/local first; at least one strong-tier
# family is required before a target may be promoted to `cleared`. Model names
# drift fast — verify before relying on them.
DEFAULT_POLICY: list[dict[str, str]] = [
    {"family": "local", "model": "glm-4.7-flash:q4_K_M", "tier": "local", "effort": "low",
     "runner": "ollama run glm-4.7-flash:q4_K_M"},
    {"family": "anthropic", "model": "claude-haiku-4-5", "tier": "cheap", "effort": "low",
     "runner": "claude --model claude-haiku-4-5"},
    {"family": "openai", "model": "gpt-5.5", "tier": "strong", "effort": "high",
     "runner": "codex exec --sandbox read-only"},
    {"family": "anthropic", "model": "claude-opus-4-8", "tier": "strong", "effort": "xhigh",
     "runner": "claude --model claude-opus-4-8"},
    {"family": "google", "model": "gemini", "tier": "cheap", "effort": "low",
     "runner": "gemini --yolo"},
    {"family": "anthropic", "model": "claude-fable-5", "tier": "max", "effort": "max",
     "runner": "claude --model claude-fable-5"},
]


def _jobs_for(
    tid: str,
    kind: str,
    prompt: str,
    arts: list[dict[str, Any]],
    builder_family: str | None,
    min_families: int,
    policy: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Return (audit jobs, revise-note). A dissenting artifact routes the target
    to revision instead of more audits."""
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
    node_by_id, edge_by_id = artifacts_by_target(audit_dir)

    jobs: list[dict[str, Any]] = []
    revise: list[dict[str, Any]] = []

    for claim in claims:
        if not isinstance(claim, dict) or "id" not in claim:
            continue
        if claim.get("type") == "inference":
            # Inference clearance comes from its edges + coherence, not a node audit.
            continue
        if claim.get("verdict") == "cleared":
            continue
        j, r = _jobs_for(claim["id"], "node", "prompts/audit-node.md",
                         node_by_id.get(claim["id"], []), builder_family, min_families, policy)
        jobs.extend(j)
        if r:
            revise.append(r)

    for edge in edges:
        if not isinstance(edge, dict) or "id" not in edge:
            continue
        if edge.get("verdict") == "cleared":
            continue
        j, r = _jobs_for(edge["id"], "edge", "prompts/audit-edge.md",
                         edge_by_id.get(edge["id"], []), builder_family, min_families, policy)
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
