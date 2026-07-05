# Graph Extraction/Reconciliation Plan
## Goal
Add the missing graph-maintenance loop: after source changes, the tool should not only invalidate stale verdicts, but help rebuild and reconcile `claims.yaml` / `edges.yaml` from independent model reconstructions while keeping the core audit contract file-first and model-free.
## Design Principles
- Keep `claim-dag` model-free. Core commands validate, diff, promote, refresh, and report; `claim-dag-run` is the only model dispatcher.

- Treat extraction as auditable evidence, not invisible preprocessing. Every model reconstruction is written to disk before reconciliation.

- Never overwrite the canonical graph without an explicit command.

- Make omissions visible. The output should expose added/missing/changed claims, changed edges, unresolved mapping decisions, and anchors that no longer exist.

- Preserve the distinctive object: source claims to target claim edges. Reconciliation must not collapse edge audit into ordinary prose review.

## New Artifact Layout
```text
audits/claim-dag/2026-07-05/
  reconstructions/
    2026-07-05T153000/
      manifest.yaml
      claims.anthropic-claude-haiku-4-5.yaml
      edges.anthropic-claude-haiku-4-5.yaml
      claims.openai-gpt-5.4.yaml
      edges.openai-gpt-5.4.yaml
      reconciliation.yaml
      graph-diff.anthropic-claude-haiku-4-5.yaml
      graph-diff.openai-gpt-5.4.yaml
```

Each reconstruction manifest records source path/hash, policy entries used, model/family/tier, timestamps, and write paths.
## New Core Commands
### `claim-dag graph-diff <audit_dir> --claims <candidate> --edges <candidate>`
Compare candidate graph files against canonical `claims.yaml` / `edges.yaml`.

Output:

- claims added, removed, anchor changed, type changed, section changed;

- edges added, removed, endpoint changed, relation changed, suppressed premise changed;

- missing anchors in the current source;

- unsafe changes requiring invalidation.


This command is model-free and should also power report output later.
### `claim-dag reconcile <audit_dir> <run_dir> --write`
Read candidate files produced by the runner. Without `--write`, print the canonical graph changes it would apply. With `--write`, update `claims.yaml` and `edges.yaml`, set changed/touched verdicts to `unaudited`, preserve existing local annotations unless a candidate explicitly changes a graph field, and log the operation in `reconciliation-log.yaml`.

No model calls here.
## New Runner Command
### `claim-dag-run reconstruct <audit_dir> --policy model-policy.yaml --families anthropic --families openai`
Model-dispatched workflow:

1. Read the current source from `source-manifest.yaml`.

2. Dispatch `prompts/extract-claims.md` independently to selected policy entries.

3. Write each model's `claims.*.yaml` candidate.

4. Dispatch `prompts/build-edges.md` using each model's claims candidate.

5. Write each model's `edges.*.yaml` candidate.

6. Produce per-candidate `graph-diff.*.yaml` files against the current canonical graph.

7. Produce `reconciliation.yaml` as a run summary. Candidate choice remains explicit; no majority merge is attempted.


This command can be `--dry-run`, `--limit`, `--family`, and `--tier` like audit dispatch.
## Reconciliation Rules
- Exact anchor matches are safe to preserve claim identity.

- Changed anchors are unsafe by default and reset that claim's verdict to `unaudited`.

- Any edge touching a changed/new/removed claim resets to `unaudited`.

- Any changed edge endpoints, relation, or suppressed premise resets edge verdict to `unaudited`.

- New claims/edges start `unaudited`.

- Removed claims/edges are not silently deleted in the first implementation; they are reported as removals requiring `--accept-removals`.

- Conflicting independent reconstructions are reported, not auto-merged.

## Implementation Phases
1. Add model-free graph-diff utilities and tests.

2. Add `claim-dag graph-diff` CLI.

3. Add reconstruction writer/parser helpers in the runner.

4. Add `claim-dag-run reconstruct --dry-run` and real dispatch.

5. Add deterministic reconciliation output.

6. Add `claim-dag reconcile --write`.

7. Update docs, prompts, schemas, and mini example.

## First Pass Scope
Implemented phases 1-7 for the conservative path: independent candidates, per-candidate diffs, explicit candidate selection, and `reconcile --write`. Automatic cross-candidate matching/majority merge remains out of scope.
## Explicit Non-Goals
- No interactive UI.

- No database.

- No semantic embedding dependency.

- No automatic acceptance of model-generated graph changes without a model-free diff/reconcile command.
