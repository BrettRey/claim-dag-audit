from __future__ import annotations

import argparse
import hashlib
from datetime import datetime
from pathlib import Path

from .audits import DEFAULT_MIN_FAMILIES, enforce_audit_backing
from .graph import analyze, load_audit, to_argdown
from .io import write_text, write_yaml
from .plan import build_plan
from .policy import load_policy
from .promote import promote
from .reconcile import graph_diff, reconcile_candidate
from .report import build_report
from .source import refresh_source


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="claim-dag")
    sub = parser.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser("init", help="initialize a per-paper audit directory")
    init_p.add_argument("audit_dir", type=Path)
    init_p.add_argument("--paper-title", required=True)
    init_p.add_argument("--source", type=Path, required=True)
    init_p.add_argument("--built-by", default=None,
                        help="model family that will build the graph (excluded from clearance)")

    validate_p = sub.add_parser("validate", help="validate claims, edges, and audit backing")
    validate_p.add_argument("audit_dir", type=Path)
    validate_p.add_argument("--k", type=int, default=DEFAULT_MIN_FAMILIES,
                            help="independent families required to clear (default 2)")

    argdown_p = sub.add_parser("argdown", help="generate graph.argdown")
    argdown_p.add_argument("audit_dir", type=Path)
    argdown_p.add_argument("-o", "--output", type=Path)

    report_p = sub.add_parser("report", help="generate report.md")
    report_p.add_argument("audit_dir", type=Path)
    report_p.add_argument("-o", "--output", type=Path)

    plan_p = sub.add_parser("plan", help="emit audit dispatch jobs still needed to clear")
    plan_p.add_argument("audit_dir", type=Path)
    plan_p.add_argument("--k", type=int, default=DEFAULT_MIN_FAMILIES)
    plan_p.add_argument("--policy", type=Path, default=None)
    plan_p.add_argument("-o", "--output", type=Path)

    promote_p = sub.add_parser("promote", help="update verdicts from audit artifacts (no model calls)")
    promote_p.add_argument("audit_dir", type=Path)
    promote_p.add_argument("--k", type=int, default=DEFAULT_MIN_FAMILIES)
    promote_p.add_argument("--dry-run", action="store_true")

    source_p = sub.add_parser(
        "refresh-source",
        help="check source hash drift and optionally invalidate stale verdicts",
    )
    source_p.add_argument("audit_dir", type=Path)
    source_p.add_argument("--write", action="store_true",
                          help="update source-manifest.yaml and reset stale verdicts")

    diff_p = sub.add_parser("graph-diff", help="compare a candidate graph to the canonical graph")
    diff_p.add_argument("audit_dir", type=Path)
    diff_p.add_argument("--claims", type=Path, required=True)
    diff_p.add_argument("--edges", type=Path, required=True)
    diff_p.add_argument("-o", "--output", type=Path)

    reconcile_p = sub.add_parser("reconcile", help="apply a selected reconstruction candidate")
    reconcile_p.add_argument("audit_dir", type=Path)
    reconcile_p.add_argument("run_dir", type=Path)
    reconcile_p.add_argument("--candidate", default=None)
    reconcile_p.add_argument("--write", action="store_true")
    reconcile_p.add_argument("--accept-removals", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "init":
        cmd_init(args.audit_dir, args.paper_title, args.source, args.built_by)
    elif args.command == "validate":
        cmd_validate(args.audit_dir, args.k)
    elif args.command == "argdown":
        cmd_argdown(args.audit_dir, args.output)
    elif args.command == "report":
        cmd_report(args.audit_dir, args.output)
    elif args.command == "plan":
        cmd_plan(args.audit_dir, args.k, args.output, args.policy)
    elif args.command == "promote":
        cmd_promote(args.audit_dir, args.k, args.dry_run)
    elif args.command == "refresh-source":
        cmd_refresh_source(args.audit_dir, args.write)
    elif args.command == "graph-diff":
        cmd_graph_diff(args.audit_dir, args.claims, args.edges, args.output)
    elif args.command == "reconcile":
        cmd_reconcile(args.audit_dir, args.run_dir, args.candidate, args.write, args.accept_removals)


def _source_sha256(source: Path) -> str | None:
    if not source.exists() or not source.is_file():
        return None
    return hashlib.sha256(source.read_bytes()).hexdigest()


def cmd_init(audit_dir: Path, paper_title: str, source: Path, built_by: str | None) -> None:
    audit_dir.mkdir(parents=True, exist_ok=True)
    for child in ("node-audits", "edge-audits", "adversarial"):
        (audit_dir / child).mkdir(exist_ok=True)

    manifest = {
        "paper_title": paper_title,
        "source": str(source),
        "source_sha256": _source_sha256(source),
        "built_by": built_by,
        "created": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "initialized",
    }
    if not (audit_dir / "source-manifest.yaml").exists():
        write_yaml(audit_dir / "source-manifest.yaml", manifest)
    if not (audit_dir / "claims.yaml").exists():
        write_yaml(audit_dir / "claims.yaml", [])
    if not (audit_dir / "edges.yaml").exists():
        write_yaml(audit_dir / "edges.yaml", [])
    print(f"initialized {audit_dir}")


def cmd_validate(audit_dir: Path, k: int) -> None:
    claims, edges = load_audit(audit_dir)
    result = analyze(claims, edges)
    backing = enforce_audit_backing(claims, edges, audit_dir, min_families=k)

    for key in ("claim_errors", "edge_errors", "coherence_errors", "defeater_errors",
                "claim_warnings", "edge_warnings"):
        for message in result[key]:
            print(f"{key}: {message}")
    for message in backing.errors:
        print(f"audit_error: {message}")
    for message in backing.warnings:
        print(f"audit_warning: {message}")
    for cid in result["unsupported_inferences"]:
        print(f"unsupported_inference: {cid} has no supporting edge")
    for cycle in result["cycles"]:
        print("cycle: " + " -> ".join(cycle))

    print(f"claims={len(claims)} edges={len(edges)}")
    print(f"unsupported_inferences={len(result['unsupported_inferences'])}")
    print(f"decorative_premises={len(result['decorative_premises'])}")
    print(f"cycles={len(result['cycles'])}")

    fatal = (
        result["claim_errors"]
        or result["edge_errors"]
        or result["coherence_errors"]
        or result["defeater_errors"]
        or result["unsupported_inferences"]
        or result["cycles"]
        or backing.errors
    )
    if fatal:
        raise SystemExit(1)


def cmd_argdown(audit_dir: Path, output: Path | None) -> None:
    claims, edges = load_audit(audit_dir)
    out = output or audit_dir / "graph.argdown"
    write_text(out, to_argdown(claims, edges))
    print(out)


def cmd_report(audit_dir: Path, output: Path | None) -> None:
    claims, edges = load_audit(audit_dir)
    out = output or audit_dir / "report.md"
    write_text(out, build_report(claims, edges, audit_dir))
    print(out)


def cmd_plan(audit_dir: Path, k: int, output: Path | None, policy_path: Path | None) -> None:
    claims, edges = load_audit(audit_dir)
    plan = build_plan(claims, edges, audit_dir, min_families=k, policy=load_policy(policy_path))
    if output:
        write_yaml(output, plan)
        print(output)
    else:
        import yaml  # local import: only the CLI stdout path needs it
        print(yaml.safe_dump(plan, sort_keys=False, allow_unicode=True), end="")


def cmd_promote(audit_dir: Path, k: int, dry_run: bool) -> None:
    changes = promote(audit_dir, min_families=k, write=not dry_run)
    if not changes:
        print("no verdict changes")
        return
    verb = "would change" if dry_run else "changed"
    for change in changes:
        print(f"{verb} {change['id']}: {change['old']} -> {change['new']}")


def cmd_refresh_source(audit_dir: Path, write: bool) -> None:
    claims, edges = load_audit(audit_dir)
    status = refresh_source(audit_dir, claims, edges, write=write)
    import yaml  # local import: only this CLI output path needs it
    print(yaml.safe_dump(status, sort_keys=False, allow_unicode=True), end="")


def cmd_graph_diff(audit_dir: Path, claims_path: Path, edges_path: Path, output: Path | None) -> None:
    import yaml
    claims, edges = load_audit(audit_dir)
    candidate_claims = yaml.safe_load(claims_path.read_text(encoding="utf-8")) or []
    candidate_edges = yaml.safe_load(edges_path.read_text(encoding="utf-8")) or []
    diff = graph_diff(claims, edges, candidate_claims, candidate_edges, audit_dir)
    if output:
        write_yaml(output, diff)
        print(output)
    else:
        print(yaml.safe_dump(diff, sort_keys=False, allow_unicode=True), end="")


def cmd_reconcile(
    audit_dir: Path,
    run_dir: Path,
    candidate: str | None,
    write: bool,
    accept_removals: bool,
) -> None:
    import yaml
    result = reconcile_candidate(audit_dir, run_dir, candidate, write, accept_removals)
    print(yaml.safe_dump(result, sort_keys=False, allow_unicode=True), end="")
    if not result.get("ok"):
        raise SystemExit(1)
