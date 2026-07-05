# STATUS

**Created:** 2026-07-05
**State:** Shipped to public GitHub; runner + all four dispatch adapters proven live.

### 2026-07-05 Session Notes (afternoon)
- Evaluated the tool, ran a 5-person review board (Opus + Codex), reformulated
  for all-LLM auditing (see `docs/llm-runner.md`), and built the external runner
  (`claim-dag-run` audit/reaudit) plus model-free `claim-dag promote`.
- Enforced the `cleared` contract; fixed relation semantics, coherence, cycles,
  Argdown; added a pytest suite (26 tests).
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
- **enforce the `cleared` contract**: independent cross-family, strong-tier,
  refute-framed audit artifacts with no dissent;
- emit a dispatch `plan` (which model/family/tier is needed to clear);
- promote verdicts from artifacts (model-free, idempotent);
- generate valid Argdown (joint premises preserved) and a report.

The runner (`claim-dag-run`, a separate console script) can:

- dispatch plan jobs to the CLIs (`ollama`/`claude`/`codex`/`copilot`/`gemini`),
  assembling prompts with a source-text window and writing artifacts back;
- stamp identity fields from the job (a model cannot mislabel its family/tier);
- default to `deferred` on unparseable output (never fabricates a clearance);
- `reaudit`: re-attack cleared targets with a stronger ladder and log demotions
  to `drift-log.yaml` (the calibration loop).

Verified: 23 unit tests, a live ollama dispatch, and CLI dry-run all pass.

Architecture for the LLM-run design: `docs/llm-runner.md`.
Review board that drove the reformulation: `reviews/review-board-2026-07-05/`.

## Not Yet Built

- A cron wrapper that runs `claim-dag-run reaudit` on a schedule (the driver
  exists; only the scheduling is external).
- CLI-flag exercise of the live `claude`/`codex` dispatch adapters (proven for
  `ollama`; the others are best-effort and may need per-CLI flag tweaks).

## First Pilot

Use `papers/preprints/kinds-as-projectibility-profiles/`. Audit the central
spine only: projectibility-profile thesis, support-grade ladder, demotion
rules, decorative-mechanism test, Goodman and Ereshefsky/Reydon pressure points.

## Next Actions

- Build the runner (plan -> CLI dispatch -> artifact writeback).
- Run extraction on the Kinds paper; fill claims.yaml / edges.yaml.
- `claim-dag plan`, dispatch the cheap+local first pass, then escalate.
