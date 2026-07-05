# CLAUDE.md

## Project

`claim-dag-audit` is a file-first tool for auditing academic arguments as
dependency graphs of claims.

The tool should preserve a strict distinction between:

- claim/node audits: truth, source grounding, data warrant, definitional consistency;
- edge audits: whether the source claims actually support the target claim;
- adversarial passes: attacks on the weakest unresolved edges.

## Development Rules

- Keep the data artifacts plain YAML and Markdown unless there is a strong
  reason to add another format.
- Do not add LLM dispatch automation until the manual Kinds pilot has exposed
  stable input/output requirements.
- `cleared` means an adversarial audit failed to break the node or edge. It
  does not mean the prose sounded plausible.
- Prefer small, composable CLI commands over a web app or database.

## Test Commands

```bash
. .venv/bin/activate
claim-dag validate examples/mini-paper/audits/claim-dag/2026-07-05
claim-dag argdown examples/mini-paper/audits/claim-dag/2026-07-05
claim-dag report examples/mini-paper/audits/claim-dag/2026-07-05
```

## First Pilot

Use `papers/preprints/kinds-as-projectibility-profiles/`.

The first pilot should audit the central spine only: projectibility-profile
thesis, support-grade ladder, demotion rules, decorative-mechanism test,
Goodman pressure, and Ereshefsky/Reydon overlap.

