"""Tests for the load-bearing audit logic. The review board flagged that the
happy-path smoke run in `make test` could not catch the relation-semantics,
coherence, or clearance-enforcement bugs. These cover exactly those.

Run: . .venv/bin/activate && pip install pytest && pytest -q
"""
from __future__ import annotations

from pathlib import Path

import yaml

from claim_dag.audits import enforce_audit_backing
from claim_dag.graph import analyze, to_argdown
from claim_dag.schema import validate_claims, validate_edges


def _claim(cid, ctype="empirical-premise", verdict="unaudited", **extra):
    base = {"id": cid, "anchor": f"anchor {cid}", "type": ctype,
            "section": "S1", "verdict": verdict}
    base.update(extra)
    return base


def _edge(eid, src, dst, relation="supports", verdict="unaudited", **extra):
    base = {"id": eid, "from": src, "to": dst, "relation": relation,
            "verdict": verdict, "suppressed_premise": "x"}
    base.update(extra)
    return base


# --- relation semantics: a rebut must not count as support -------------------

def test_rebuts_is_not_support():
    claims = [_claim("C001"), _claim("C002", ctype="inference")]
    edges = [_edge("E001", ["C001"], "C002", relation="rebuts")]
    result = analyze(claims, edges)
    assert result["unsupported_inferences"] == ["C002"], (
        "an inference whose only incoming edge is a rebuttal must read as unsupported"
    )
    assert "C001" in result["challenges"].get("C002", [])


def test_supports_counts_as_support():
    claims = [_claim("C001"), _claim("C002", ctype="inference")]
    edges = [_edge("E001", ["C001"], "C002", relation="supports")]
    result = analyze(claims, edges)
    assert result["unsupported_inferences"] == []


# --- cycles must be detected -------------------------------------------------

def test_two_node_cycle_detected():
    claims = [_claim("C001", ctype="inference"), _claim("C002", ctype="inference")]
    edges = [_edge("E001", ["C001"], "C002"), _edge("E002", ["C002"], "C001")]
    result = analyze(claims, edges)
    assert result["cycles"], "a support cycle must be reported"


# --- verdict coherence: a conclusion cannot outrank its support --------------

def test_cleared_inference_needs_cleared_edge():
    claims = [
        _claim("C001", verdict="cleared"),
        _claim("C002", ctype="inference", verdict="cleared"),
    ]
    edges = [_edge("E001", ["C001"], "C002", verdict="weakened")]
    result = analyze(claims, edges)
    assert any("E001" in e for e in result["coherence_errors"])


def test_cleared_inference_needs_cleared_source():
    claims = [
        _claim("C001", verdict="failed"),
        _claim("C002", ctype="inference", verdict="cleared"),
    ]
    edges = [_edge("E001", ["C001"], "C002", verdict="cleared")]
    result = analyze(claims, edges)
    assert any("C001" in e for e in result["coherence_errors"])


def test_coherent_cleared_chain_ok():
    claims = [
        _claim("C001", verdict="cleared"),
        _claim("C002", ctype="inference", verdict="cleared"),
    ]
    edges = [_edge("E001", ["C001"], "C002", verdict="cleared")]
    result = analyze(claims, edges)
    assert result["coherence_errors"] == []


# --- clearance enforcement (the board's #1 finding) --------------------------

def _artifact(tmp: Path, kind: str, name: str, fm: dict) -> None:
    d = tmp / ("edge-audits" if kind == "edge" else "node-audits")
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text("---\n" + yaml.safe_dump(fm) + "---\n# audit\n", encoding="utf-8")


def _manifest(tmp: Path, built_by="local"):
    (tmp / "source-manifest.yaml").write_text(
        yaml.safe_dump({"built_by": built_by}), encoding="utf-8")


def _clear_fm(edge_id, family, tier="strong"):
    return {"edge_id": edge_id, "verdict": "cleared", "model": f"m-{family}",
            "family": family, "tier": tier, "framing": "refute",
            "could_have_failed": "if X then fail", "suppressed_premise": "sp",
            "attack": "tried X", "date": "2026-07-05"}


def test_cleared_with_no_artifacts_fails(tmp_path):
    _manifest(tmp_path)
    claims = [_claim("C001"), _claim("C009", ctype="inference", verdict="cleared")]
    edges = [_edge("E001", ["C001"], "C009", verdict="cleared")]
    r = enforce_audit_backing(claims, edges, tmp_path)
    assert any("E001" in e and "no audit artifact" in e for e in r.errors)


def test_cleared_needs_two_families(tmp_path):
    _manifest(tmp_path)
    _artifact(tmp_path, "edge", "E001.a.md", _clear_fm("E001", "anthropic"))
    _artifact(tmp_path, "edge", "E001.b.md", _clear_fm("E001", "anthropic"))
    claims = [_claim("C001"), _claim("C009", ctype="inference", verdict="cleared")]
    edges = [_edge("E001", ["C001"], "C009", verdict="cleared")]
    r = enforce_audit_backing(claims, edges, tmp_path)
    assert any("independent families" in e for e in r.errors)


def test_cleared_excludes_builder_family(tmp_path):
    _manifest(tmp_path, built_by="anthropic")
    _artifact(tmp_path, "edge", "E001.a.md", _clear_fm("E001", "anthropic"))
    _artifact(tmp_path, "edge", "E001.b.md", _clear_fm("E001", "openai"))
    claims = [_claim("C001"), _claim("C009", ctype="inference", verdict="cleared")]
    edges = [_edge("E001", ["C001"], "C009", verdict="cleared")]
    r = enforce_audit_backing(claims, edges, tmp_path)
    assert any("builder family" in e for e in r.errors)


def test_dissent_breaks_clearance(tmp_path):
    _manifest(tmp_path)
    _artifact(tmp_path, "edge", "E001.a.md", _clear_fm("E001", "anthropic"))
    _artifact(tmp_path, "edge", "E001.b.md", _clear_fm("E001", "openai"))
    dissent = _clear_fm("E001", "google")
    dissent["verdict"] = "failed"
    _artifact(tmp_path, "edge", "E001.c.md", dissent)
    claims = [_claim("C001"), _claim("C009", ctype="inference", verdict="cleared")]
    edges = [_edge("E001", ["C001"], "C009", verdict="cleared")]
    r = enforce_audit_backing(claims, edges, tmp_path)
    assert any("dissent breaks clearance" in e for e in r.errors)


def test_cleared_needs_strong_tier(tmp_path):
    _manifest(tmp_path)
    _artifact(tmp_path, "edge", "E001.a.md", _clear_fm("E001", "anthropic", tier="cheap"))
    _artifact(tmp_path, "edge", "E001.b.md", _clear_fm("E001", "openai", tier="cheap"))
    claims = [_claim("C001"), _claim("C009", ctype="inference", verdict="cleared")]
    edges = [_edge("E001", ["C001"], "C009", verdict="cleared")]
    r = enforce_audit_backing(claims, edges, tmp_path)
    assert any("strong-tier" in e for e in r.errors)


def test_clean_clearance_passes(tmp_path):
    _manifest(tmp_path)
    _artifact(tmp_path, "edge", "E001.a.md", _clear_fm("E001", "anthropic", tier="cheap"))
    _artifact(tmp_path, "edge", "E001.b.md", _clear_fm("E001", "openai", tier="strong"))
    claims = [_claim("C001"), _claim("C009", ctype="inference", verdict="cleared")]
    edges = [_edge("E001", ["C001"], "C009", verdict="cleared")]
    r = enforce_audit_backing(claims, edges, tmp_path)
    assert r.errors == []


# --- Argdown: joint premises stay one argument -------------------------------

def test_argdown_preserves_premise_set():
    claims = [_claim("C001"), _claim("C002"), _claim("C003", ctype="inference")]
    edges = [_edge("E001", ["C001", "C002"], "C003")]
    text = to_argdown(claims, edges)
    # One argument node, both premises under it, and no attack arrow for support.
    assert "<E001>" in text
    assert "(1) [C001]" in text and "(2) [C002]" in text
    assert "-> [C003]" not in text  # the old invalid attack-arrow rendering


def test_schema_rejects_bad_verdict():
    r = validate_claims([_claim("C001", verdict="bogus")])
    assert not r.ok
    r2 = validate_edges([_edge("E001", ["C001"], "C002", verdict="bogus")], {"C001", "C002"})
    assert not r2.ok
