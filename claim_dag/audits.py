from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .graph import claim_map
from .io import read_artifacts, read_yaml
from .schema import (
    BACKED_VERDICTS,
    REFUTE_FRAMING,
    STRONG_TIERS,
    VERDICTS,
    ValidationResult,
)

# Clearance bar. A `cleared` verdict needs this many audit artifacts from
# distinct model families (excluding the builder family). Tunable via
# claim-dag validate --k. See docs/llm-runner.md.
DEFAULT_MIN_FAMILIES = 2

_COMMON_FIELDS = ("verdict", "model", "family", "date")
_NODE_FIELDS = ("claim_id",)
_EDGE_FIELDS = ("edge_id", "suppressed_premise", "attack")


def artifacts_by_target(audit_dir: Path) -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    """Group audit frontmatter by the claim_id / edge_id it targets."""
    node_by_id: dict[str, list[dict]] = defaultdict(list)
    edge_by_id: dict[str, list[dict]] = defaultdict(list)
    for _, fm in read_artifacts(audit_dir / "node-audits"):
        tid = fm.get("claim_id")
        if isinstance(tid, str):
            node_by_id[tid].append(fm)
    for _, fm in read_artifacts(audit_dir / "edge-audits"):
        tid = fm.get("edge_id")
        if isinstance(tid, str):
            edge_by_id[tid].append(fm)
    return node_by_id, edge_by_id


def _validate_artifact(fm: dict[str, Any], path: Path, kind: str, errors: list[str]) -> str | None:
    """Check one artifact's frontmatter. Returns the target id (claim_id or
    edge_id) if usable, else None."""
    name = path.name
    if not fm:
        errors.append(f"{name}: no parseable frontmatter (need a --- YAML block)")
        return None
    required = _COMMON_FIELDS + (_NODE_FIELDS if kind == "node" else _EDGE_FIELDS)
    for key in required:
        if key not in fm or str(fm.get(key, "")).strip() == "":
            errors.append(f"{name}: missing {key}")
    if fm.get("verdict") not in VERDICTS:
        errors.append(f"{name}: verdict must be one of {sorted(VERDICTS)}")
    if fm.get("verdict") == "cleared":
        if fm.get("framing") != REFUTE_FRAMING:
            errors.append(f"{name}: a cleared audit must set framing: {REFUTE_FRAMING}")
        if not str(fm.get("could_have_failed", "")).strip():
            errors.append(f"{name}: a cleared audit must record a non-empty could_have_failed")
        if not str(fm.get("tier", "")).strip():
            errors.append(f"{name}: a cleared audit must record its tier")
    target_key = "claim_id" if kind == "node" else "edge_id"
    tid = fm.get(target_key)
    return tid if isinstance(tid, str) and tid.strip() else None


def _enforce_target(
    tid: str,
    verdict: str,
    arts: list[dict[str, Any]],
    builder_family: str | None,
    min_families: int,
    errors: list[str],
    warnings: list[str],
) -> None:
    if verdict in BACKED_VERDICTS and not arts:
        errors.append(f"{tid}: verdict {verdict} but no audit artifact backs it")
        return

    if verdict == "cleared":
        dissent = [a for a in arts if a.get("verdict") in {"failed", "weakened"}]
        if dissent:
            errors.append(
                f"{tid}: cleared, but {len(dissent)} independent audit(s) returned "
                f"failed/weakened — dissent breaks clearance"
            )
        clears = [
            a
            for a in arts
            if a.get("verdict") == "cleared"
            and a.get("framing") == REFUTE_FRAMING
            and str(a.get("could_have_failed", "")).strip()
        ]
        families = {a.get("family") for a in clears if a.get("family")}
        if builder_family and builder_family in families:
            errors.append(
                f"{tid}: cleared by the builder family '{builder_family}'; "
                f"independence requires a different family"
            )
        independent = families - ({builder_family} if builder_family else set())
        if len(independent) < min_families:
            errors.append(
                f"{tid}: cleared needs >={min_families} independent families, "
                f"has {sorted(independent) or 'none'}"
            )
        if not any(a.get("tier") in STRONG_TIERS for a in clears if a.get("family") in independent):
            errors.append(
                f"{tid}: cleared needs at least one strong-tier audit; "
                f"cheap/local agreement is not enough"
            )
    elif verdict in {"failed", "weakened"}:
        if not any(a.get("verdict") == verdict for a in arts):
            errors.append(f"{tid}: recorded {verdict} but no artifact returns that verdict")
    elif verdict == "unaudited" and arts:
        warnings.append(
            f"{tid}: has audit artifact(s) but verdict is still unaudited "
            f"(promote it or run claim-dag plan)"
        )


def enforce_audit_backing(
    claims: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    audit_dir: Path,
    min_families: int = DEFAULT_MIN_FAMILIES,
) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    manifest = read_yaml(audit_dir / "source-manifest.yaml", {})
    builder_family = manifest.get("built_by") if isinstance(manifest, dict) else None
    if not builder_family:
        warnings.append(
            "source-manifest.yaml has no built_by; cannot exclude the builder "
            "family from clearance (set built_by to the family that extracted the graph)"
        )

    node_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    edge_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for path, fm in read_artifacts(audit_dir / "node-audits"):
        tid = _validate_artifact(fm, path, "node", errors)
        if tid:
            node_by_id[tid].append(fm)
    for path, fm in read_artifacts(audit_dir / "edge-audits"):
        tid = _validate_artifact(fm, path, "edge", errors)
        if tid:
            edge_by_id[tid].append(fm)

    claim_ids = set(claim_map(claims))
    edge_ids = {e.get("id") for e in edges if isinstance(e, dict)}
    for tid in node_by_id:
        if tid not in claim_ids:
            warnings.append(f"node-audit references unknown claim {tid}")
    for tid in edge_by_id:
        if tid not in edge_ids:
            warnings.append(f"edge-audit references unknown edge {tid}")

    for claim in claims:
        if not isinstance(claim, dict) or "id" not in claim:
            continue
        # Inference nodes are cleared by their edges + verdict coherence, not a
        # node audit; skip artifact-backing for them (graph.verdict_coherence
        # is their gate). A stray node audit on an inference is still allowed.
        if claim.get("type") == "inference" and not node_by_id.get(claim["id"]):
            continue
        _enforce_target(
            claim["id"], claim.get("verdict", "unaudited"),
            node_by_id.get(claim["id"], []), builder_family, min_families, errors, warnings,
        )
    for edge in edges:
        if not isinstance(edge, dict) or "id" not in edge:
            continue
        _enforce_target(
            edge["id"], edge.get("verdict", "unaudited"),
            edge_by_id.get(edge["id"], []), builder_family, min_families, errors, warnings,
        )

    return ValidationResult(errors, warnings)
