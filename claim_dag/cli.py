from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from .graph import analyze, load_audit, to_argdown
from .io import write_text, write_yaml
from .report import build_report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="claim-dag")
    sub = parser.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser("init", help="initialize a per-paper audit directory")
    init_p.add_argument("audit_dir", type=Path)
    init_p.add_argument("--paper-title", required=True)
    init_p.add_argument("--source", type=Path, required=True)

    validate_p = sub.add_parser("validate", help="validate claims.yaml and edges.yaml")
    validate_p.add_argument("audit_dir", type=Path)

    argdown_p = sub.add_parser("argdown", help="generate graph.argdown")
    argdown_p.add_argument("audit_dir", type=Path)
    argdown_p.add_argument("-o", "--output", type=Path)

    report_p = sub.add_parser("report", help="generate report.md")
    report_p.add_argument("audit_dir", type=Path)
    report_p.add_argument("-o", "--output", type=Path)

    args = parser.parse_args(argv)
    if args.command == "init":
        cmd_init(args.audit_dir, args.paper_title, args.source)
    elif args.command == "validate":
        cmd_validate(args.audit_dir)
    elif args.command == "argdown":
        cmd_argdown(args.audit_dir, args.output)
    elif args.command == "report":
        cmd_report(args.audit_dir, args.output)


def cmd_init(audit_dir: Path, paper_title: str, source: Path) -> None:
    audit_dir.mkdir(parents=True, exist_ok=True)
    for child in ("node-audits", "edge-audits", "adversarial"):
        (audit_dir / child).mkdir(exist_ok=True)

    manifest = {
        "paper_title": paper_title,
        "source": str(source),
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


def cmd_validate(audit_dir: Path) -> None:
    claims, edges = load_audit(audit_dir)
    result = analyze(claims, edges)
    for key in ("claim_errors", "edge_errors", "claim_warnings", "edge_warnings"):
        for message in result[key]:
            print(f"{key}: {message}")
    print(f"claims={len(claims)} edges={len(edges)}")
    print(f"unsupported_inferences={len(result['unsupported_inferences'])}")
    print(f"decorative_premises={len(result['decorative_premises'])}")
    print(f"cycles={len(result['cycles'])}")
    if result["claim_errors"] or result["edge_errors"]:
        raise SystemExit(1)


def cmd_argdown(audit_dir: Path, output: Path | None) -> None:
    claims, edges = load_audit(audit_dir)
    out = output or audit_dir / "graph.argdown"
    write_text(out, to_argdown(claims, edges))
    print(out)


def cmd_report(audit_dir: Path, output: Path | None) -> None:
    claims, edges = load_audit(audit_dir)
    out = output or audit_dir / "report.md"
    write_text(out, build_report(claims, edges))
    print(out)

