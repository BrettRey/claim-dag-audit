# CLAUDE.md

## Project

`claim-dag-audit` is a file-first tool for auditing academic arguments as
dependency graphs of claims.

The tool should preserve a strict distinction between:

- claim/node audits: truth, source grounding, data warrant, definitional consistency;
- edge audits: whether the source claims actually support the target claim;
- adversarial passes: attacks on the weakest unresolved edges.

## Development Rules

- Auditing is LLM-run (no human auditors). The design is in `docs/llm-runner.md`.
- Keep the data artifacts plain YAML and Markdown unless there is a strong
  reason to add another format.
- The tool defines and *enforces* the audit contract and emits a dispatch
  `plan`; it does **not** call models. Model dispatch stays in an external
  runner so model-specific plumbing never enters the audit record. Keep it that
  way unless there is a strong reason to fold dispatch in.
- `cleared` means an adversarial audit failed to break the node or edge, and it
  is enforced: `validate` requires independent cross-family, strong-tier,
  refute-framed backing with no dissent. It never means the prose sounded
  plausible.
- Prefer small, composable CLI commands over a web app or database.

## Test Commands

```bash
make test        # pytest (tests/) + smoke run on the example
make plan        # show the dispatch plan for the example
```

## First Pilot

Use `papers/preprints/kinds-as-projectibility-profiles/`.

The first pilot should audit the central spine only: projectibility-profile
thesis, support-grade ladder, demotion rules, decorative-mechanism test,
Goodman pressure, and Ereshefsky/Reydon overlap.

