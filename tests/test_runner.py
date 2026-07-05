"""Tests for the runner (dispatch + writeback + promotion) and the drift
re-audit driver, using a mock dispatcher so no models are called."""
from __future__ import annotations

from pathlib import Path

import yaml

from claim_dag.audits import enforce_audit_backing
from claim_dag.io import read_frontmatter, read_yaml
from claim_dag.promote import promote
from claim_dag.runner import _argv_for, parse_output, reaudit, run_audits, write_artifact


def _spine(tmp: Path, built_by="local") -> Path:
    d = tmp / "audit"
    (d / "node-audits").mkdir(parents=True)
    (d / "edge-audits").mkdir(parents=True)
    (d / "source-manifest.yaml").write_text(yaml.safe_dump({"built_by": built_by}))
    (d / "claims.yaml").write_text(yaml.safe_dump([
        {"id": "C001", "anchor": "premise", "type": "empirical-premise",
         "section": "S", "verdict": "unaudited", "evidence": "e"},
        {"id": "C002", "anchor": "therefore", "type": "inference",
         "section": "S", "verdict": "unaudited"},
    ]))
    (d / "edges.yaml").write_text(yaml.safe_dump([
        {"id": "E001", "from": ["C001"], "to": "C002", "relation": "supports",
         "suppressed_premise": "sp", "verdict": "unaudited"},
    ]))
    return d


def _mock(verdict: str):
    def dispatch(job):
        return (f"---\nverdict: {verdict}\ncould_have_failed: if X then fail\n"
                f"attack: tried X\nsuppressed_premise: sp\n---\nreasoning prose")
    return dispatch


# --- parsing + identity stamping ---------------------------------------------

def test_parse_output_strips_fences_and_reads_frontmatter():
    fm, body = parse_output("```markdown\n---\nverdict: cleared\n---\nprose here\n```")
    assert fm["verdict"] == "cleared"
    assert "prose here" in body


def test_parse_output_no_verdict():
    fm, body = parse_output("just prose, no verdict anywhere")
    assert fm == {} and "just prose" in body


def test_parse_output_block_after_reasoning_preamble():
    # A "thinking" model emits reasoning, then the block.
    text = ("Thinking... let me work through this.\n\n"
            "---\nverdict: failed\ncould_have_failed: c\nattack: a\n---\n")
    fm, _ = parse_output(text)
    assert fm["verdict"] == "failed" and fm["attack"] == "a"


def test_parse_output_salvages_bare_lines():
    fm, _ = parse_output("My assessment:\nverdict: weakened\nattack: the wedge\n")
    assert fm["verdict"] == "weakened"


# --- effort + model are passed through to the CLIs ---------------------------

def test_argv_passes_model_and_effort():
    tmp = Path("/tmp")
    argv, stdin, _ = _argv_for("claude --model claude-opus-4-8", "PROMPT", tmp, "high")
    assert argv[:3] == ["claude", "--model", "claude-opus-4-8"]
    assert "--effort" in argv and "high" in argv and argv[-2:] == ["-p", "PROMPT"]

    argv2, _, _ = _argv_for("codex exec --sandbox read-only -m gpt-5.4", "P", tmp, "medium")
    assert "-m" in argv2 and "gpt-5.4" in argv2
    assert any(a == "model_reasoning_effort=medium" for a in argv2)


def test_codex_effort_max_maps_to_xhigh():
    argv, _, _ = _argv_for("codex exec", "P", Path("/tmp"), "max")
    assert any(a == "model_reasoning_effort=xhigh" for a in argv)


def test_no_effort_no_flag():
    argv, _, _ = _argv_for("claude --model x", "P", Path("/tmp"), None)
    assert "--effort" not in argv


def test_runner_stamps_identity_over_model_claims(tmp_path):
    d = _spine(tmp_path)
    job = {"target": "E001", "kind": "edge", "model": "claude-haiku-4-5",
           "family": "anthropic", "tier": "cheap"}
    # A model that lies about its family/tier and verdict vocabulary.
    output = ("---\nverdict: bogus\nfamily: EVIL\ntier: max\n"
              "could_have_failed: c\nattack: a\nsuppressed_premise: sp\n---\nx")
    path = write_artifact(d, job, output)
    fm = read_frontmatter(path)
    assert fm["family"] == "anthropic"   # stamped, not the model's "EVIL"
    assert fm["tier"] == "cheap"         # stamped, not the model's "max"
    assert fm["framing"] == "refute"
    assert fm["verdict"] == "deferred"   # "bogus" is not a valid verdict


# --- full run: mock audits clear the spine -----------------------------------

def test_run_audits_clears_spine(tmp_path):
    d = _spine(tmp_path)
    result = run_audits(d, dispatcher=_mock("cleared"))
    assert result["job_count"] == 4  # C001 x2 families, E001 x2 families
    verdicts = {c["id"]: c["new"] for c in result["promoted"]}
    assert verdicts["C001"] == "cleared"
    assert verdicts["E001"] == "cleared"
    assert verdicts["C002"] == "cleared"  # inference propagates from its support
    claims = read_yaml(d / "claims.yaml", [])
    edges = read_yaml(d / "edges.yaml", [])
    assert enforce_audit_backing(claims, edges, d).errors == []


def test_dry_run_writes_nothing(tmp_path):
    d = _spine(tmp_path)
    result = run_audits(d, dry_run=True, dispatcher=_mock("cleared"))
    assert "dry_run" in result and result.get("written") is None
    assert not list((d / "edge-audits").glob("*.md"))


# --- drift: reaudit breaks a cleared spine -----------------------------------

def test_reaudit_demotes_and_logs_drift(tmp_path):
    d = _spine(tmp_path)
    run_audits(d, dispatcher=_mock("cleared"))
    out = reaudit(d, dispatcher=_mock("failed"))
    assert out["demotions"], "a failing re-audit must demote the cleared targets"
    demoted = {c["id"] for c in out["demotions"]}
    assert "E001" in demoted and "C001" in demoted
    log = read_yaml(d / "drift-log.yaml", [])
    assert log and log[-1]["demotions"]


def test_promote_is_idempotent(tmp_path):
    d = _spine(tmp_path)
    run_audits(d, dispatcher=_mock("cleared"))
    assert promote(d) == []  # second promote finds nothing new to change
