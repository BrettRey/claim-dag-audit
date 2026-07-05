"""Tests for the runner (dispatch + writeback + promotion) and the drift
re-audit driver, using a mock dispatcher so no models are called."""
from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from claim_dag.audits import enforce_audit_backing
from claim_dag.io import read_frontmatter, read_yaml
from claim_dag.plan import build_plan
from claim_dag.policy import load_policy, policy_doctor
from claim_dag.promote import promote
from claim_dag.runner import _argv_for, parse_output, reaudit, run_audits, write_artifact
from claim_dag.source import refresh_source


def _spine(tmp: Path, built_by="local") -> Path:
    d = tmp / "audit"
    (d / "node-audits").mkdir(parents=True)
    (d / "edge-audits").mkdir(parents=True)
    source = tmp / "paper.md"
    source.write_text(
        "The premise is grounded. If the premise is grounded, therefore the conclusion follows.",
        encoding="utf-8",
    )
    (d / "source-manifest.yaml").write_text(
        yaml.safe_dump({
            "built_by": built_by,
            "source": str(source),
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        })
    )
    (d / "claims.yaml").write_text(yaml.safe_dump([
        {"id": "C001", "anchor": "premise is grounded", "type": "empirical-premise",
         "section": "S", "verdict": "unaudited", "evidence": "e"},
        {"id": "C002", "anchor": "therefore the conclusion follows", "type": "inference",
         "section": "S", "verdict": "unaudited"},
    ]))
    (d / "edges.yaml").write_text(yaml.safe_dump([
        {"id": "E001", "from": ["C001"], "to": "C002", "relation": "supports",
         "suppressed_premise": "sp", "verdict": "unaudited"},
    ]))
    return d


def _mock(verdict: str):
    def dispatch(job):
        return (f"---\nverdict: {verdict}\n"
                f"failure_mode: missing bridge premise\n"
                f"could_have_failed: source context lacked the bridge\n"
                f"attack: tried X\n"
                f"evidence_checked: checked provided source context\n"
                f"source_span: paper.md:1 bridge premise\n"
                f"suppressed_premise: sp\n---\nreasoning prose")
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
            "---\nverdict: failed\ncould_have_failed: c\nattack: a\n"
            "failure_mode: f\nevidence_checked: e\nsource_span: s\n---\n")
    fm, _ = parse_output(text)
    assert fm["verdict"] == "failed" and fm["attack"] == "a"


def test_parse_output_salvages_bare_lines():
    fm, _ = parse_output("My assessment:\nverdict: weakened\nattack: the wedge\n")
    assert fm["verdict"] == "weakened"


def test_parse_output_ignores_prompt_templates():
    for prompt in ("prompts/audit-node.md", "prompts/audit-edge.md"):
        fm, _ = parse_output(Path(prompt).read_text(encoding="utf-8"))
        assert fm == {}


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


def test_policy_file_loads(tmp_path):
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.safe_dump({"policy": [{
        "family": "test",
        "model": "m",
        "tier": "strong",
        "effort": "low",
        "runner": "python -m this",
    }]}), encoding="utf-8")
    policy = load_policy(path)
    assert policy == [{
        "family": "test",
        "model": "m",
        "tier": "strong",
        "effort": "low",
        "runner": "python -m this",
    }]


def test_policy_doctor_reports_missing_command():
    out = policy_doctor([{
        "family": "test",
        "model": "m",
        "tier": "strong",
        "effort": "low",
        "runner": "__claim_dag_missing_command__ run",
    }])
    assert out["ok"] is False
    assert out["missing_commands"] == ["__claim_dag_missing_command__"]


def test_runner_stamps_identity_over_model_claims(tmp_path):
    d = _spine(tmp_path)
    job = {"target": "E001", "kind": "edge", "model": "claude-haiku-4-5",
           "family": "anthropic", "tier": "cheap"}
    # A model that lies about its family/tier and verdict vocabulary.
    output = ("---\nverdict: bogus\nfamily: EVIL\ntier: max\n"
              "could_have_failed: c\nfailure_mode: f\nattack: a\n"
              "evidence_checked: e\nsource_span: s\nsuppressed_premise: sp\n---\nx")
    path = write_artifact(d, job, output)
    fm = read_frontmatter(path)
    assert fm["family"] == "anthropic"   # stamped, not the model's "EVIL"
    assert fm["tier"] == "cheap"         # stamped, not the model's "max"
    assert fm["framing"] == "refute"
    assert fm["verdict"] == "deferred"   # "bogus" is not a valid verdict


def test_prompt_echo_does_not_clear_target(tmp_path):
    d = _spine(tmp_path)
    result = run_audits(d, dispatcher=lambda job: job["prompt"])
    assert result["promoted"] == []
    claims = read_yaml(d / "claims.yaml", [])
    edges = read_yaml(d / "edges.yaml", [])
    assert {c["verdict"] for c in claims} == {"unaudited"}
    assert {e["verdict"] for e in edges} == {"unaudited"}


def test_write_artifact_preserves_prior_runs(tmp_path):
    d = _spine(tmp_path)
    job = {"target": "E001", "kind": "edge", "model": "gpt-5.4",
           "family": "openai", "tier": "strong"}
    output = ("---\nedge_id: E001\nverdict: cleared\ncould_have_failed: c\n"
              "failure_mode: f\nattack: a\nevidence_checked: e\nsource_span: s\n"
              "suppressed_premise: sp\n---\nbody")
    first = write_artifact(d, job, output)
    second = write_artifact(d, job, output)
    assert first != second
    assert first.exists() and second.exists()


def test_edge_prompt_includes_source_context(tmp_path):
    d = _spine(tmp_path)
    source = tmp_path / "paper.md"
    source.write_text("The premise supports a bridge. Therefore the conclusion follows.", encoding="utf-8")
    (d / "source-manifest.yaml").write_text(
        yaml.safe_dump({"built_by": "local", "source": str(source)}), encoding="utf-8"
    )
    claims = read_yaml(d / "claims.yaml", [])
    claims[0]["anchor"] = "premise supports"
    claims[1]["anchor"] = "conclusion follows"
    (d / "claims.yaml").write_text(yaml.safe_dump(claims), encoding="utf-8")
    captured = {}

    def dispatch(job):
        captured.update(job)
        return _mock("cleared")(job)

    run_audits(d, tiers={"strong"}, limit=2, dispatcher=dispatch)
    assert "Relevant paper context" in captured["prompt"]
    assert "premise supports" in captured["prompt"]
    assert captured["source_context_available"] is True


def test_cleared_edge_without_source_context_defers(tmp_path):
    d = _spine(tmp_path)
    (d / "source-manifest.yaml").write_text(yaml.safe_dump({"built_by": "local"}), encoding="utf-8")
    result = run_audits(d, tiers={"strong"}, limit=2, dispatcher=_mock("cleared"))
    assert result["promoted"] == []
    artifact = next((d / "edge-audits").glob("*.md"))
    fm = read_frontmatter(artifact)
    assert fm["verdict"] == "deferred"


# --- full run: mock audits clear the spine -----------------------------------

def test_run_audits_clears_spine(tmp_path):
    d = _spine(tmp_path)
    result = run_audits(d, dispatcher=_mock("cleared"))
    # C001 and E001 each get 2 free local families + 1 strong = 3 jobs.
    assert result["job_count"] == 6
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


def test_plan_does_not_trust_stale_cleared_labels(tmp_path):
    d = _spine(tmp_path)
    claims = read_yaml(d / "claims.yaml", [])
    edges = read_yaml(d / "edges.yaml", [])
    for record in [*claims, *edges]:
        record["verdict"] = "cleared"
    (d / "claims.yaml").write_text(yaml.safe_dump(claims), encoding="utf-8")
    (d / "edges.yaml").write_text(yaml.safe_dump(edges), encoding="utf-8")
    plan = build_plan(claims, edges, d)
    assert plan["job_count"] == 6
    assert {j["target"] for j in plan["jobs"]} == {"C001", "E001"}


def test_plan_ignores_old_source_artifacts(tmp_path):
    d = _spine(tmp_path)
    run_audits(d, dispatcher=_mock("cleared"))
    manifest = read_yaml(d / "source-manifest.yaml", {})
    manifest["source_sha256"] = "f" * 64
    (d / "source-manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    claims = read_yaml(d / "claims.yaml", [])
    edges = read_yaml(d / "edges.yaml", [])
    plan = build_plan(claims, edges, d)
    assert plan["job_count"] == 6


def test_refresh_source_invalidates_stale_verdicts(tmp_path):
    d = _spine(tmp_path)
    run_audits(d, dispatcher=_mock("cleared"))
    claims = read_yaml(d / "claims.yaml", [])
    edges = read_yaml(d / "edges.yaml", [])
    source = Path(read_yaml(d / "source-manifest.yaml", {})["source"])
    old_sha = source.read_bytes()
    assert old_sha
    source.write_text("The premise changed, and therefore the conclusion changed.", encoding="utf-8")
    status = refresh_source(d, claims, edges, write=True)
    assert status["changed"] is True
    assert {item["id"] for item in status["invalidated"]} == {"C001", "C002", "E001"}
    updated_claims = read_yaml(d / "claims.yaml", [])
    updated_edges = read_yaml(d / "edges.yaml", [])
    assert {c["verdict"] for c in updated_claims} == {"unaudited"}
    assert {e["verdict"] for e in updated_edges} == {"unaudited"}
    assert read_yaml(d / "invalidation-log.yaml", [])


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
    assert log[-1]["reaudit_tier"] == "max"
    assert log[-1]["reaudit_tiers"] == ["max"]
    assert log[-1]["reaudited"] == 2
    assert log[-1]["targets"]


def test_promote_is_idempotent(tmp_path):
    d = _spine(tmp_path)
    run_audits(d, dispatcher=_mock("cleared"))
    assert promote(d) == []  # second promote finds nothing new to change
