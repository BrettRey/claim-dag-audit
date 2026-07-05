from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

CLAIM_TYPES = {
    "definition",
    "empirical-premise",
    "cited-claim",
    "inference",
    "stipulation",
}

CLAIM_STATUSES = {
    "uncleared",
    "needs-audit",
    "in-progress",
    "cleared",
    "weakened",
    "failed",
    "deferred",
}

EDGE_RELATIONS = {"supports", "requires", "rebuts", "qualifies"}
EDGE_STATUSES = CLAIM_STATUSES

CLAIM_ID = re.compile(r"^C[0-9]{3,}$")
EDGE_ID = re.compile(r"^E[0-9]{3,}$")


@dataclass
class ValidationResult:
    errors: list[str]
    warnings: list[str]

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

        for key in ("anchor", "type", "section", "status"):
            if key not in claim:
                errors.append(f"{cid or label}: missing {key}")

        if "anchor" in claim and not str(claim["anchor"]).strip():
            errors.append(f"{cid or label}: anchor is empty")
        if claim.get("type") not in CLAIM_TYPES:
            errors.append(f"{cid or label}: type must be one of {sorted(CLAIM_TYPES)}")
        if claim.get("status") not in CLAIM_STATUSES:
            errors.append(f"{cid or label}: status must be one of {sorted(CLAIM_STATUSES)}")
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
        if edge.get("status") not in EDGE_STATUSES:
            errors.append(f"{eid or label}: status must be one of {sorted(EDGE_STATUSES)}")
        if "suppressed_premise" not in edge:
            warnings.append(f"{eid or label}: no suppressed_premise recorded")

    return ValidationResult(errors, warnings)

