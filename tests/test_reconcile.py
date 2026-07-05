from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from claim_dag.io import read_yaml
from claim_dag.reconcile import graph_diff, reconcile_candidate
from claim_dag.runner import reconstruct


def _audit(tmp: Path) -> Path:
    d = tmp / "audit"
    d.mkdir()
    source = tmp / "paper.md"
    source.write_text("Alpha supports beta. Therefore beta follows.", encoding="utf-8")
    (d / "source-manifest.yaml").write_text(yaml.safe_dump({
        "paper_title": "T",
        "source": str(source),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "built_by": "local",
    }), encoding="utf-8")
    (d / "claims.yaml").write_text(yaml.safe_dump([
        {"id": "C001", "anchor": "Alpha supports beta.", "type": "empirical-premise",
         "section": "S", "verdict": "cleared", "notes": "human annotation"},
        {"id": "C002", "anchor": "Therefore beta follows.", "type": "inference",
         "section": "S", "verdict": "cleared"},
    ]), encoding="utf-8")
    (d / "edges.yaml").write_text(yaml.safe_dump([
        {"id": "E001", "from": ["C001"], "to": "C002", "relation": "supports",
         "suppressed_premise": "Alpha licenses beta.", "verdict": "cleared"},
    ]), encoding="utf-8")
    return d


def _candidate(run_dir: Path, suffix: str = "test-model") -> tuple[Path, Path]:
    claims = run_dir / f"claims.{suffix}.yaml"
    edges = run_dir / f"edges.{suffix}.yaml"
    claims.write_text(yaml.safe_dump([
        {"id": "C001", "anchor": "Alpha supports beta.", "type": "empirical-premise",
         "section": "S", "verdict": "unaudited"},
        {"id": "C002", "anchor": "Therefore beta follows.", "type": "inference",
         "section": "S", "verdict": "unaudited"},
        {"id": "C003", "anchor": "New claim.", "type": "stipulation",
         "section": "S", "verdict": "unaudited"},
    ]), encoding="utf-8")
    edges.write_text(yaml.safe_dump([
        {"id": "E001", "from": ["C001"], "to": "C002", "relation": "supports",
         "suppressed_premise": "Alpha licenses beta.", "verdict": "unaudited"},
        {"id": "E002", "from": ["C003"], "to": "C002", "relation": "qualifies",
         "resolution": "open", "verdict": "unaudited"},
    ]), encoding="utf-8")
    return claims, edges


def test_graph_diff_reports_added_claim_and_edge(tmp_path):
    d = _audit(tmp_path)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    claims_path, edges_path = _candidate(run_dir)
    diff = graph_diff(
        read_yaml(d / "claims.yaml", []),
        read_yaml(d / "edges.yaml", []),
        read_yaml(claims_path, []),
        read_yaml(edges_path, []),
        d,
    )
    assert diff["claim_changes"]["added"][0]["id"] == "C003"
    assert diff["edge_changes"]["added"] == ["E002"]
    assert any(item["id"] == "C003" for item in diff["unsafe_changes"])


def test_reconcile_requires_candidate_when_multiple(tmp_path):
    d = _audit(tmp_path)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _candidate(run_dir, "a")
    _candidate(run_dir, "b")
    result = reconcile_candidate(d, run_dir)
    assert result["ok"] is False
    assert "multiple candidates" in result["error"]


def test_reconcile_write_applies_selected_candidate(tmp_path):
    d = _audit(tmp_path)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _candidate(run_dir, "a")
    result = reconcile_candidate(d, run_dir, candidate_id="a", write=True)
    assert result["ok"] is True
    claims = read_yaml(d / "claims.yaml", [])
    edges = read_yaml(d / "edges.yaml", [])
    assert {c["id"] for c in claims} == {"C001", "C002", "C003"}
    assert {e["id"] for e in edges} == {"E001", "E002"}
    assert next(c for c in claims if c["id"] == "C001")["notes"] == "human annotation"
    verdicts = {c["id"]: c["verdict"] for c in claims}
    assert verdicts["C002"] == "unaudited"  # new qualifier touches the target
    assert read_yaml(d / "reconciliation-log.yaml", [])


def test_reconstruct_writes_candidate_artifacts(tmp_path):
    d = _audit(tmp_path)
    policy = [{
        "family": "test",
        "model": "m",
        "tier": "strong",
        "effort": "low",
        "runner": "mock",
    }]

    def dispatch(job):
        if job["kind"] == "extract-claims":
            return yaml.safe_dump([
                {"id": "C001", "anchor": "Alpha supports beta.", "type": "empirical-premise",
                 "section": "S", "verdict": "unaudited"},
                {"id": "C002", "anchor": "Therefore beta follows.", "type": "inference",
                 "section": "S", "verdict": "unaudited"},
            ])
        return yaml.safe_dump([
            {"id": "E001", "from": ["C001"], "to": "C002", "relation": "supports",
             "suppressed_premise": "Alpha licenses beta.", "verdict": "unaudited"},
        ])

    out = reconstruct(d, policy=policy, dispatcher=dispatch)
    assert out["ok"] is True
    run_dir = Path(out["run_dir"])
    assert (run_dir / "claims.test-m.yaml").exists()
    assert (run_dir / "edges.test-m.yaml").exists()
    assert (run_dir / "reconciliation.yaml").exists()
