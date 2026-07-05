"""External audit runner. Reads `claim-dag plan`, assembles the prompt for each
job, dispatches it to the relevant CLI (ollama / claude / codex / copilot /
gemini), and writes a validated audit artifact back. This is the one part of the
system that calls models; the core `claim-dag` tool never does. The dispatcher
is injectable so it can be tested offline and overridden by an orchestrating
agent.

Identity fields (model, family, tier, framing, target id, date) are stamped by
the runner from the job, not trusted from the model's own output — a model
cannot mislabel its family or tier to slip past the independence bar.
"""
from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import yaml

from .audits import DEFAULT_MIN_FAMILIES, artifacts_by_target
from .graph import _edge_endpoints, claim_map, load_audit
from .io import read_yaml, write_text, write_yaml
from .plan import DEFAULT_POLICY, build_plan
from .promote import promote
from .schema import STRONG_TIERS, VERDICTS

_TOOL_ROOT = Path(__file__).resolve().parent.parent
_PROMPTS = _TOOL_ROOT / "prompts"

Dispatcher = Callable[[dict], str]  # (job-with-prompt) -> raw model output


# --- prompt assembly ---------------------------------------------------------

def _source_window(audit_dir: Path, source: str | None, anchor: str, radius: int = 900) -> str:
    if not source or not anchor:
        return ""
    candidates = [Path(source), _TOOL_ROOT / source, audit_dir / source]
    text = None
    for cand in candidates:
        if cand.exists() and cand.is_file():
            text = cand.read_text(encoding="utf-8", errors="replace")
            break
    if text is None:
        return ""
    needle = " ".join(anchor.split())[:60]
    hay = " ".join(text.split())
    idx = hay.lower().find(needle.lower())
    if idx == -1:
        return ""
    lo, hi = max(0, idx - radius), idx + len(needle) + radius
    return hay[lo:hi]


def assemble_prompt(
    job: dict[str, Any],
    claims_by_id: dict[str, dict],
    edges_by_id: dict[str, dict],
    audit_dir: Path,
) -> str:
    kind = job["kind"]
    tid = job["target"]
    template = (_PROMPTS / ("audit-node.md" if kind == "node" else "audit-edge.md")).read_text(
        encoding="utf-8"
    )
    dump = lambda o: yaml.safe_dump(o, sort_keys=False, allow_unicode=True).strip()

    if kind == "edge":
        edge = edges_by_id[tid]
        _, sources = _edge_endpoints(edge)
        target_claim = claims_by_id.get(edge.get("to", ""), {})
        template = template.replace("[paste edge record]", dump(edge))
        template = template.replace(
            "[paste source claim records]",
            dump([claims_by_id[s] for s in sources if s in claims_by_id]),
        )
        template = template.replace("[paste target claim record]", dump(target_claim))
    else:
        claim = claims_by_id[tid]
        manifest = read_yaml(audit_dir / "source-manifest.yaml", {})
        window = _source_window(audit_dir, manifest.get("source"), str(claim.get("anchor", "")))
        template = template.replace("[paste claim record]", dump(claim))
        template = template.replace(
            "[paste local passage plus surrounding paragraphs]",
            window or "[source passage unavailable; audit the claim as recorded]",
        )
    return template


# --- CLI dispatch ------------------------------------------------------------

# Codex reasoning-effort accepts minimal/low/medium/high/xhigh; it has no
# "max", so map the policy's max onto xhigh.
_CODEX_EFFORT = {"low": "low", "medium": "medium", "high": "high", "xhigh": "xhigh", "max": "xhigh"}


def _argv_for(
    runner: str, prompt: str, tmpdir: Path, effort: str | None = None
) -> tuple[list[str], str | None, Callable[[str], str]]:
    """Build (argv, stdin_text, read_output) for a runner string. The prompt is
    passed as an argument to the agentic CLIs (claude/codex/copilot/gemini) —
    piping it on stdin makes them fall back to an interactive session that
    ignores the task. Only ollama takes the prompt on stdin. The job's effort is
    passed through where the CLI supports it (claude --effort, codex
    model_reasoning_effort)."""
    tokens = shlex.split(runner)
    cli = tokens[0] if tokens else ""
    if cli == "ollama":
        return tokens, prompt, lambda out: out
    if cli == "claude":
        extra = ["--effort", effort] if effort else []
        return tokens + extra + ["-p", prompt], None, lambda out: out
    if cli == "codex":
        outfile = tmpdir / "codex-out.md"
        extra = ["-c", f"model_reasoning_effort={_CODEX_EFFORT.get(effort, effort)}"] if effort else []
        argv = tokens + extra + ["-o", str(outfile), prompt]
        return argv, None, lambda out: outfile.read_text(encoding="utf-8") if outfile.exists() else out
    if cli in {"copilot", "gemini"}:
        return tokens + ["-p", prompt], None, lambda out: out
    return tokens, prompt, lambda out: out


def cli_dispatch(job: dict[str, Any], timeout: int = 300) -> str:
    prompt = job["prompt"]
    with tempfile.TemporaryDirectory() as td:
        argv, stdin_text, read_out = _argv_for(
            job["runner"], prompt, Path(td), job.get("effort")
        )
        try:
            # Run in a neutral empty cwd so the audited paper's or tool's repo
            # context never bleeds into the audit.
            result = subprocess.run(
                argv, input=stdin_text, capture_output=True, text=True,
                timeout=timeout, cwd=td,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
            return f"---\nverdict: deferred\n---\ndispatch error: {exc}"
        if result.returncode != 0:
            return f"---\nverdict: deferred\n---\ndispatch exit {result.returncode}: {result.stderr[:400]}"
        return read_out(result.stdout)


# --- output parsing + artifact writeback -------------------------------------

_FM_RE = re.compile(r"(?ms)^---[ \t]*$(.*?)^---[ \t]*$")
_FENCE_RE = re.compile(r"(?ms)```(?:yaml|markdown|yml)?[ \t]*\n(.*?)```")
_VERDICT_RE = re.compile(r"verdict:\s*[\"']?(cleared|weakened|failed|deferred)", re.I)


def _load_mapping(block: str) -> dict[str, Any] | None:
    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) and "verdict" in data else None


def _salvage(text: str) -> dict[str, Any] | None:
    """Last resort: pull fields line-by-line from messy prose. Only returns a
    verdict if one is unambiguously present, so nothing silently clears."""
    m = _VERDICT_RE.search(text)
    if not m:
        return None
    out: dict[str, Any] = {"verdict": m.group(1).lower()}
    for key in ("could_have_failed", "attack", "suppressed_premise"):
        km = re.search(rf"{key}:\s*[\"']?(.+)", text)
        if km:
            out[key] = km.group(1).strip().strip("\"'")
    return out


def parse_output(text: str) -> tuple[dict[str, Any], str]:
    """Extract the audit fields a model returned, tolerant of reasoning
    preambles, code fences, and block-anywhere placement. Returns ({}, text)
    when no verdict can be found — write_artifact then records `deferred`
    rather than fabricating a clearance."""
    s = text.strip()
    # 1. an explicit --- frontmatter block, anywhere in the output
    for m in _FM_RE.finditer(s):
        data = _load_mapping(m.group(1))
        if data:
            return data, (s[m.end():].strip() or s)
    # 2. inside a fenced code block
    for m in _FENCE_RE.finditer(s):
        inner = m.group(1)
        fm = _FM_RE.search(inner)
        data = _load_mapping(fm.group(1) if fm else inner)
        if data:
            return data, s
    # 3. bare key: value lines in prose
    salvaged = _salvage(s)
    return (salvaged or {}), s


def write_artifact(
    audit_dir: Path, job: dict[str, Any], output: str, fallback_suppressed: str = ""
) -> Path:
    fm, body = parse_output(output)
    verdict = fm.get("verdict")
    if verdict not in VERDICTS:
        verdict = "deferred"
    today = datetime.now().date().isoformat()

    stamped: dict[str, Any] = {
        ("edge_id" if job["kind"] == "edge" else "claim_id"): job["target"],
        "verdict": verdict,
        "model": job["model"],
        "family": job["family"],
        "tier": job["tier"],
        "framing": "refute",
        "could_have_failed": str(fm.get("could_have_failed", "")).strip(),
        "attack": str(fm.get("attack", "")).strip(),
        "date": today,
    }
    if job["kind"] == "edge":
        stamped["suppressed_premise"] = str(fm.get("suppressed_premise", "") or fallback_suppressed).strip()

    slug = re.sub(r"[^A-Za-z0-9]+", "-", job["model"]).strip("-")
    subdir = "edge-audits" if job["kind"] == "edge" else "node-audits"
    path = audit_dir / subdir / f"{job['target']}.{job['family']}-{slug}.md"
    content = "---\n" + yaml.safe_dump(stamped, sort_keys=False, allow_unicode=True) + "---\n"
    content += body or output.strip() + "\n"
    write_text(path, content)
    return path


# --- orchestration -----------------------------------------------------------

def run_audits(
    audit_dir: Path,
    min_families: int = DEFAULT_MIN_FAMILIES,
    tiers: set[str] | None = None,
    limit: int | None = None,
    dry_run: bool = False,
    dispatcher: Dispatcher | None = None,
) -> dict[str, Any]:
    dispatcher = dispatcher or cli_dispatch
    claims, edges = load_audit(audit_dir)
    claims_by_id = claim_map(claims)
    edges_by_id = {e["id"]: e for e in edges if isinstance(e, dict) and "id" in e}

    plan = build_plan(claims, edges, audit_dir, min_families=min_families)
    jobs = plan["jobs"]
    if tiers:
        jobs = [j for j in jobs if j["tier"] in tiers]
    if limit is not None:
        jobs = jobs[:limit]

    written: list[str] = []
    previews: list[dict[str, str]] = []
    for job in jobs:
        job = {**job, "prompt": assemble_prompt(job, claims_by_id, edges_by_id, audit_dir)}
        if dry_run:
            previews.append({"target": job["target"], "kind": job["kind"],
                             "model": job["model"], "family": job["family"], "runner": job["runner"]})
            continue
        fallback = ""
        if job["kind"] == "edge":
            fallback = str(edges_by_id.get(job["target"], {}).get("suppressed_premise", ""))
        output = dispatcher(job)
        written.append(str(write_artifact(audit_dir, job, output, fallback)))

    result: dict[str, Any] = {
        "audit_dir": str(audit_dir),
        "job_count": len(jobs),
        "revise": plan["revise"],
    }
    if dry_run:
        result["dry_run"] = previews
    else:
        result["written"] = written
        result["promoted"] = promote(audit_dir, min_families=min_families)
    return result


def reaudit(
    audit_dir: Path,
    min_families: int = DEFAULT_MIN_FAMILIES,
    dispatcher: Dispatcher | None = None,
    policy: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Re-attack currently-cleared targets with a fresh strong/max-tier auditor
    from a family not already among their clearers. A break (failed/weakened)
    demotes the target on promote; demotions are appended to drift-log.yaml.
    This is the outcome-feedback loop from docs/llm-runner.md."""
    dispatcher = dispatcher or cli_dispatch
    policy = policy or DEFAULT_POLICY
    # Strongest first, so re-audits escalate: prefer a max-tier attacker.
    strong_entries = sorted(
        [p for p in policy if p["tier"] in STRONG_TIERS],
        key=lambda p: 0 if p["tier"] == "max" else 1,
    )
    claims, edges = load_audit(audit_dir)
    claims_by_id = claim_map(claims)
    edges_by_id = {e["id"]: e for e in edges if isinstance(e, dict) and "id" in e}
    manifest = read_yaml(audit_dir / "source-manifest.yaml", {})
    builder = manifest.get("built_by") if isinstance(manifest, dict) else None
    node_arts, edge_arts = artifacts_by_target(audit_dir)

    def _fresh_strong(existing_families: set[str]) -> dict[str, str] | None:
        # Prefer a strong/max family that has not cleared this target (adds
        # independence); otherwise re-attack with the strongest available
        # auditor (a stronger model re-testing an old clearance is the point).
        for entry in strong_entries:
            if entry["family"] != builder and entry["family"] not in existing_families:
                return entry
        for entry in strong_entries:
            if entry["family"] != builder:
                return entry
        return None

    jobs: list[dict[str, Any]] = []
    for claim in claims:
        if not isinstance(claim, dict) or claim.get("verdict") != "cleared":
            continue
        if claim.get("type") == "inference":
            continue  # covered by re-auditing its edges/premises
        fams = {a.get("family") for a in node_arts.get(claim["id"], []) if a.get("verdict") == "cleared"}
        entry = _fresh_strong(fams)
        if entry:
            jobs.append({"target": claim["id"], "kind": "node", "prompt_file": "audit-node.md", **entry})
    for edge in edges:
        if not isinstance(edge, dict) or edge.get("verdict") != "cleared":
            continue
        fams = {a.get("family") for a in edge_arts.get(edge["id"], []) if a.get("verdict") == "cleared"}
        entry = _fresh_strong(fams)
        if entry:
            jobs.append({"target": edge["id"], "kind": "edge", "prompt_file": "audit-edge.md", **entry})

    for job in jobs:
        job = {**job, "prompt": assemble_prompt(job, claims_by_id, edges_by_id, audit_dir)}
        fallback = str(edges_by_id.get(job["target"], {}).get("suppressed_premise", "")) if job["kind"] == "edge" else ""
        write_artifact(audit_dir, job, dispatcher(job), fallback)

    changes = promote(audit_dir, min_families=min_families)
    demotions = [c for c in changes if c["old"] == "cleared" and c["new"] != "cleared"]
    if demotions:
        log = read_yaml(audit_dir / "drift-log.yaml", [])
        if not isinstance(log, list):
            log = []
        log.append({
            "date": datetime.now().date().isoformat(),
            "reaudit_tier": "strong",
            "demotions": demotions,
        })
        write_yaml(audit_dir / "drift-log.yaml", log)
    return {"reaudited": len(jobs), "changes": changes, "demotions": demotions}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="claim-dag-run",
                                     description="Dispatch audit jobs to model CLIs")
    sub = parser.add_subparsers(dest="command", required=True)

    a = sub.add_parser("audit", help="run the pending audit jobs and promote verdicts")
    a.add_argument("audit_dir", type=Path)
    a.add_argument("--k", type=int, default=DEFAULT_MIN_FAMILIES)
    a.add_argument("--tier", action="append", help="restrict to a tier (repeatable)")
    a.add_argument("--limit", type=int, default=None)
    a.add_argument("--dry-run", action="store_true", help="show jobs without calling models")
    a.add_argument("--timeout", type=int, default=300)

    r = sub.add_parser("reaudit", help="re-attack cleared targets with a stronger ladder")
    r.add_argument("audit_dir", type=Path)
    r.add_argument("--k", type=int, default=DEFAULT_MIN_FAMILIES)
    r.add_argument("--timeout", type=int, default=300)

    args = parser.parse_args(argv)
    if args.command == "audit":
        disp = (lambda job: cli_dispatch(job, timeout=args.timeout))
        out = run_audits(args.audit_dir, min_families=args.k,
                         tiers=set(args.tier) if args.tier else None,
                         limit=args.limit, dry_run=args.dry_run, dispatcher=disp)
    else:
        disp = (lambda job: cli_dispatch(job, timeout=args.timeout))
        out = reaudit(args.audit_dir, min_families=args.k, dispatcher=disp)
    print(yaml.safe_dump(out, sort_keys=False, allow_unicode=True), end="")
