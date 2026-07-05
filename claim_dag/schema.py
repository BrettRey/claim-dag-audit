from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

CLAIM_TYPES = {
    "definition",
    "empirical-premise",
    "cited-claim",
    "inference",
    "stipulation",
}

# One axis, outcome only. The former workflow states (uncleared, needs-audit,
# in-progress) collapse into `unaudited`: a target needs auditing iff its
# verdict is unaudited. Fidler flagged the two-axis conflation; this resolves
# it (see docs/llm-runner.md).
VERDICTS = {"unaudited", "cleared", "weakened", "failed", "deferred"}

# Verdicts that assert an audit occurred and therefore must be backed by an
# audit artifact. `unaudited` and `deferred` do not require backing.
BACKED_VERDICTS = {"cleared", "weakened", "failed"}

# Relation semantics. Only supporting relations count as incoming support for
# an inference node and propagate clearance to it. `rebuts` is an attack;
# `qualifies` limits scope. Rushby and Mayo flagged that analyze() treated all
# relations as support.
SUPPORTING_RELATIONS = {"supports", "requires"}
NON_SUPPORTING_RELATIONS = {"rebuts", "qualifies"}
EDGE_RELATIONS = SUPPORTING_RELATIONS | NON_SUPPORTING_RELATIONS
DEFEATER_RESOLUTIONS = {"open", "answered", "defeated", "accepted"}
RESOLVED_DEFEATERS = {"answered", "defeated"}

# Adversarial framing required of any audit that counts toward `cleared`.
REFUTE_FRAMING = "refute"

# Tiers that count as an escalation. Clearance requires at least one audit from
# a strong (or max) tier, so a `cleared` verdict is never trusted from cheap or
# local models alone (see docs/llm-runner.md, escalation ladder).
STRONG_TIERS = {"strong", "max"}

CLAIM_ID = re.compile(r"^C[0-9]{3,}$")
EDGE_ID = re.compile(r"^E[0-9]{3,}$")


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _require_mapping(item: Any, label: str, errors: list[str]) -> bool:
    if not isinstance(item, dict):
        errors.append(f"{label} must be a mapping")
        return False
    return True


def validate_claims(claims: Any) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    seen: set[str] = set()

    if not isinstance(claims, list):
        return ValidationResult(["claims.yaml must contain a list"], warnings)

    for index, claim in enumerate(claims, start=1):
        label = f"claim #{index}"
        if not _require_mapping(claim, label, errors):
            continue
        cid = claim.get("id")
        if not isinstance(cid, str) or not CLAIM_ID.match(cid):
            errors.append(f"{label}: id must look like C001")
        elif cid in seen:
            errors.append(f"{cid}: duplicate claim id")
        else:
            seen.add(cid)

        for key in ("anchor", "type", "section", "verdict"):
            if key not in claim:
                errors.append(f"{cid or label}: missing {key}")

        if "anchor" in claim and not str(claim["anchor"]).strip():
            errors.append(f"{cid or label}: anchor is empty")
        if claim.get("type") not in CLAIM_TYPES:
            errors.append(f"{cid or label}: type must be one of {sorted(CLAIM_TYPES)}")
        if claim.get("verdict") not in VERDICTS:
            errors.append(f"{cid or label}: verdict must be one of {sorted(VERDICTS)}")
        if claim.get("type") == "cited-claim" and "source" not in claim:
            warnings.append(f"{cid or label}: cited-claim should name a source")
        if claim.get("type") == "empirical-premise" and "evidence" not in claim:
            warnings.append(f"{cid or label}: empirical-premise should name evidence/data")

    return ValidationResult(errors, warnings)


def validate_edges(edges: Any, claim_ids: set[str]) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    seen: set[str] = set()

    if not isinstance(edges, list):
        return ValidationResult(["edges.yaml must contain a list"], warnings)

    for index, edge in enumerate(edges, start=1):
        label = f"edge #{index}"
        if not _require_mapping(edge, label, errors):
            continue
        eid = edge.get("id")
        if not isinstance(eid, str) or not EDGE_ID.match(eid):
            errors.append(f"{label}: id must look like E001")
        elif eid in seen:
            errors.append(f"{eid}: duplicate edge id")
        else:
            seen.add(eid)

        from_ids = edge.get("from")
        to_id = edge.get("to")
        if not isinstance(from_ids, list) or not from_ids:
            errors.append(f"{eid or label}: from must be a non-empty list")
            from_ids = []
        if not isinstance(to_id, str):
            errors.append(f"{eid or label}: to must be a claim id")
            to_id = ""

        for cid in from_ids:
            if cid not in claim_ids:
                errors.append(f"{eid or label}: unknown source claim {cid}")
        if to_id and to_id not in claim_ids:
            errors.append(f"{eid or label}: unknown target claim {to_id}")
        if edge.get("relation") not in EDGE_RELATIONS:
            errors.append(f"{eid or label}: relation must be one of {sorted(EDGE_RELATIONS)}")
        if edge.get("resolution") is not None and edge.get("resolution") not in DEFEATER_RESOLUTIONS:
            errors.append(
                f"{eid or label}: resolution must be one of {sorted(DEFEATER_RESOLUTIONS)}"
            )
        if edge.get("verdict") not in VERDICTS:
            errors.append(f"{eid or label}: verdict must be one of {sorted(VERDICTS)}")
        if edge.get("relation") in SUPPORTING_RELATIONS and "suppressed_premise" not in edge:
            warnings.append(f"{eid or label}: no suppressed_premise recorded")
        if edge.get("relation") in NON_SUPPORTING_RELATIONS and "resolution" not in edge:
            warnings.append(
                f"{eid or label}: non-supporting edge has no resolution "
                f"(defaults to open and blocks clearance of its target)"
            )

    return ValidationResult(errors, warnings)
