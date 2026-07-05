from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

from .io import read_yaml, write_yaml
from .schema import BACKED_VERDICTS

TOOL_ROOT = Path(__file__).resolve().parent.parent


def source_candidates(audit_dir: Path, source: str) -> list[Path]:
    path = Path(source)
    if path.is_absolute():
        return [path]
    candidates = [path, TOOL_ROOT / path, audit_dir / path, audit_dir.parent / path]
    out: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key not in seen:
            out.append(candidate)
            seen.add(key)
    return out


def resolve_source(audit_dir: Path, source: str | None) -> Path | None:
    if not source:
        return None
    return next((p for p in source_candidates(audit_dir, source) if p.is_file()), None)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current_source_sha(audit_dir: Path, manifest: dict[str, Any] | None = None) -> str | None:
    data = manifest if manifest is not None else read_yaml(audit_dir / "source-manifest.yaml", {})
    if not isinstance(data, dict):
        return None
    found = resolve_source(audit_dir, data.get("source"))
    return sha256_file(found) if found else None


def source_text(audit_dir: Path, manifest: dict[str, Any] | None = None) -> str | None:
    data = manifest if manifest is not None else read_yaml(audit_dir / "source-manifest.yaml", {})
    if not isinstance(data, dict):
        return None
    found = resolve_source(audit_dir, data.get("source"))
    return found.read_text(encoding="utf-8", errors="replace") if found else None


def artifact_matches_source(artifact: dict[str, Any], source_sha: str | None) -> bool:
    if not source_sha:
        return True
    return artifact.get("source_sha256") == source_sha


def source_status(audit_dir: Path, claims: list[dict], edges: list[dict]) -> dict[str, Any]:
    manifest = read_yaml(audit_dir / "source-manifest.yaml", {})
    manifest = manifest if isinstance(manifest, dict) else {}
    recorded = manifest.get("source_sha256")
    current = current_source_sha(audit_dir, manifest)
    text = source_text(audit_dir, manifest) or ""
    normalized = " ".join(text.split()).lower()

    anchors: list[dict[str, Any]] = []
    for claim in claims:
        if not isinstance(claim, dict) or "id" not in claim:
            continue
        anchor = str(claim.get("anchor", "")).strip()
        needle = " ".join(anchor.split()).lower()
        anchors.append({
            "id": claim["id"],
            "anchor_found": bool(needle and needle in normalized),
            "verdict": claim.get("verdict", "unaudited"),
        })

    invalidated: list[dict[str, str]] = []
    if recorded and current and recorded != current:
        for record in [*claims, *edges]:
            if not isinstance(record, dict) or "id" not in record:
                continue
            verdict = record.get("verdict", "unaudited")
            if verdict in BACKED_VERDICTS:
                invalidated.append({"id": record["id"], "old": verdict, "new": "unaudited"})

    return {
        "source": manifest.get("source"),
        "source_found": current is not None,
        "recorded_sha256": recorded,
        "current_sha256": current,
        "changed": bool(recorded and current and recorded != current),
        "anchors": anchors,
        "missing_anchors": [a["id"] for a in anchors if not a["anchor_found"]],
        "would_invalidate": invalidated,
    }


def refresh_source(audit_dir: Path, claims: list[dict], edges: list[dict], write: bool) -> dict[str, Any]:
    status = source_status(audit_dir, claims, edges)
    if not write or not status["changed"]:
        return status

    for record in [*claims, *edges]:
        if not isinstance(record, dict) or "id" not in record:
            continue
        if record.get("verdict") in BACKED_VERDICTS:
            record["verdict"] = "unaudited"

    manifest = read_yaml(audit_dir / "source-manifest.yaml", {})
    manifest = manifest if isinstance(manifest, dict) else {}
    old_sha = manifest.get("source_sha256")
    manifest["previous_source_sha256"] = old_sha
    manifest["source_sha256"] = status["current_sha256"]
    manifest["updated"] = datetime.now().astimezone().isoformat(timespec="seconds")

    log = read_yaml(audit_dir / "invalidation-log.yaml", [])
    if not isinstance(log, list):
        log = []
    log.append({
        "date": manifest["updated"],
        "reason": "source_sha256 changed",
        "old_source_sha256": old_sha,
        "new_source_sha256": status["current_sha256"],
        "invalidated": status["would_invalidate"],
        "missing_anchors": status["missing_anchors"],
    })

    write_yaml(audit_dir / "source-manifest.yaml", manifest)
    write_yaml(audit_dir / "claims.yaml", claims)
    write_yaml(audit_dir / "edges.yaml", edges)
    write_yaml(audit_dir / "invalidation-log.yaml", log)
    status["invalidated"] = status["would_invalidate"]
    return status
