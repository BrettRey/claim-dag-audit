# STATUS

**Created:** 2026-07-05
**State:** Shipped to public GitHub; core contract tightened after second review-board pass.

### 2026-07-05 Session Notes (afternoon)
- Evaluated the tool, ran a 5-person review board (Opus + Codex), reformulated
  for all-LLM auditing (see `docs/llm-runner.md`), and built the external runner
  (`claim-dag-run` audit/reaudit) plus model-free `claim-dag promote`.
- Enforced the `cleared` contract; fixed relation semantics, coherence, cycles,
  Argdown; added and expanded a pytest suite (38 tests).
- Tuned the model policy under subscription auth: local models as distinct
  families (Zhipu/Alibaba/Google) for free independence; gpt-5.4/medium strong
  auditor; effort wired through; Fable dropped (no credits) → Opus-max stands in.
- Fixed a real bug: codex needs `--skip-git-repo-check` (was mis-invoked, not
  slow). All four families proven live: gemma 14s, qwen, haiku, codex gpt-5.4 29s.
- Added the claim-dog logo; published https://github.com/BrettRey/claim-dag-audit

## Current State

The tool can:

- initialize a per-paper audit directory (with a source hash and builder family);
- validate `claims.yaml` and `edges.yaml` (single verdict axis);
- give edge relations semantics (only supports/requires count as support);
- enforce verdict coherence (a conclusion cannot outrank its weakest support);
- treat support cycles as errors;
- treat unsupported inference nodes and unresolved incoming defeaters as errors;
- **enforce the `cleared` contract**: independent cross-family, strong-tier,
  refute-framed audit artifacts with structured severity fields and no dissent;
- emit a dispatch `plan` (which model/family/tier is needed to clear);
- load an editable model policy (`model-policy.yaml`) for plan/dispatch;
- promote verdicts from artifacts (model-free, idempotent);
- generate valid Argdown (joint premises preserved) and a report.
- detect source-hash drift, report missing anchors, and invalidate stale
  verdicts with `claim-dag refresh-source --write`.
- compare candidate graphs with `claim-dag graph-diff` and apply one selected
  reconstruction with `claim-dag reconcile --write`.

The runner (`claim-dag-run`, a separate console script) can:

- dispatch plan jobs to the CLIs (`ollama`/`claude`/`codex`/`copilot`/`gemini`),
  assembling prompts with source-text windows, including edge context, and
  writing artifacts back;
- stamp identity fields from the job (a model cannot mislabel its family/tier);
- default to `deferred` on unparseable output (never fabricates a clearance);
- `reaudit`: re-attack cleared targets with a stronger ladder and log the full
  denominator plus demotions to `drift-log.yaml` (the calibration loop).
- `doctor`: check whether configured runner commands exist on the current
  machine before dispatching.
- `reconstruct`: dispatch independent claim/edge graph reconstruction jobs and
  write candidate artifacts plus graph diffs under `reconstructions/`.

Verified: 46 unit tests, example validate/Argdown/report smoke checks,
`claim-dag-run doctor`, reconstruction dry-run, graph diff, and source refresh
all pass.

Architecture for the LLM-run design: `docs/llm-runner.md`.
Review board that drove the reformulation: `reviews/review-board-2026-07-05/`.

## Not Yet Built

- A cron wrapper that runs `claim-dag-run reaudit` on a schedule (the driver
  exists; only the scheduling is external).
- Better automatic reconciliation heuristics across multiple independent
  reconstructions. The current implementation requires an explicit candidate
  selection instead of model-majority merging.
- CLI-flag exercise of every live dispatch adapter through `model-policy.yaml`.

## First Pilot

Use https://github.com/BrettRey/kinds-as-projectibility-profiles. Audit the
central spine only: projectibility-profile thesis, support-grade ladder,
demotion rules, decorative-mechanism test, Goodman and Ereshefsky/Reydon
pressure points.

## Next Actions

- Run extraction on the Kinds paper; fill claims.yaml / edges.yaml.
- `claim-dag plan`, dispatch the cheap+local first pass, then escalate.
