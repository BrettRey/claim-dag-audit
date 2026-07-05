# LLM-Run Auditing: Architecture

This document reformulates `claim-dag-audit` for a world with no human
auditors. Every node audit, edge audit, and adversarial pass is run by a
language model. The tool's job is no longer to help a person keep a graph
tidy; it is to define an audit *contract* strict enough that a fleet of
models cannot rubber-stamp its way to a `cleared` verdict, and to enforce
that contract mechanically.

It is grounded in the 2026-07-05 review board (`reviews/review-board-2026-07-05/`)
and the discussions before it. The board's five reviewers converged on one
defect: `cleared` was a hand-editable label with no enforced link to any
audit, and no field recording whether an attack *could have failed*. The
all-LLM pivot makes that defect both more dangerous and easier to fix.

## What the pivot changes

Two of the board's objections dissolve; one sharpens into the core design problem.

- **van Gelder's maintenance tax dissolves.** His worry was that no human
  keeps `claims.yaml` current through month three. With the runner writing
  the YAML, there is no human bookkeeping to abandon. Re-running is a cron
  job, not a chore.
- **Fidler's two-auditor reliability study becomes nearly free.** She wanted
  independent extraction and edge audits by two coders, with agreement
  logged. Two coders are now two model families, and a third is another API
  call. Inter-auditor agreement is a byproduct of the normal run.
- **Unearned confidence sharpens into the design problem.** The risk is not
  mainly flattery. Frontier models in 2026 are far less sycophantic than the
  instruction-tuned models that made "ask if it survived, hear yes" a cliché,
  so that specific failure is real but shrinking. The durable problems survive
  a perfectly sincere auditor: correlated blind spots (a model shares the
  failure modes of its own family, so its agreement with a same-family builder
  is near-duplicate evidence, not a second opinion), and Mayo severity (a test
  a false claim would have passed clears nothing, whether or not the auditor
  wanted to please). Mercier's argumentative-reasoning result is about myside
  bias, not flattery: solo scrutiny is weak at catching one's own errors. If
  severity is not engineered, an all-LLM audit manufactures false assurance at
  scale, not because the models fawn but because agreement among near-identical
  reasoners reads as corroboration and isn't.

So the design centers on one question: **what makes a model-run `cleared`
verdict severe rather than performed?** Three mechanisms, all enforced in
code, answer it.

## Mechanism 1: adversarial framing (never ask "did it survive?")

Audit prompts never ask a model to confirm. They ask it to *break* the node
or edge, and they default to broken on uncertainty. The verdict a model
returns is the outcome of an attempt to refute, not an assessment of
plausibility. An audit artifact only counts toward `cleared` if it records
`framing: refute` and a non-empty `could_have_failed` line naming the
observation that would have flipped it. A test a false claim would pass with
high probability is worthless; the `could_have_failed` field is where the
model has to show its probe had teeth.

## Mechanism 2: independence via model diversity

Correlated error is worst when the auditor shares the blind spot of the
builder. So clearance requires **cross-family** audits: the models that clear
a node or edge must come from at least two distinct families, and none may be
the family that built the claim graph (`built_by` in the source manifest).
Two Anthropic models agreeing is one perspective run twice; Anthropic plus
OpenAI plus a local model agreeing is three. Diversity of failure mode, not
redundancy of the same one, is what buys severity here.

## Mechanism 3: dissent breaks clearance

Redundancy only helps if a single break counts. If any independent audit
returns `failed` or `weakened`, the node or edge cannot be `cleared` — its
verdict is capped at the worst independent result. This is the
loop-until-someone-breaks-it stance: we are not taking a majority vote on
whether an argument holds; one credible refutation is enough to demote it.
Combined with framing and independence, a `cleared` verdict means: at least
K models from ≥2 families each tried to break it, each stated what would have
broken it, and none succeeded.

The tool enforces all three in `claim-dag validate`. A `cleared` node or edge
with missing artifacts, insufficient family diversity, a builder-family
auditor, a non-refute framing, an empty `could_have_failed`, or any
dissenting artifact is a validation **error**, not a warning.

## The model ladder

The two API families are driven through their **subscription CLIs** (`claude`
for Claude Code, `codex` for Codex), not the metered API, so there is no
per-token charge — the constraint is subscription rate limits and wall-clock,
not dollars. Local models are free and unmetered. That makes the ladder purely
about matching model strength to task difficulty and preserving independence.
Model IDs below are current as of 2026-07 (verify before relying on them; LLM
naming drifts fast).

| Tier | Models | Auth | Role |
|------|--------|------|------|
| Local | `glm-4.7-flash`, `gemma3:12b`, `qwen3:8b` (ollama) | none, on-device | First-pass breaker on every target; free, private, unmetered |
| Cheap | `claude-haiku-4-5`, Copilot (Haiku) | subscription | Bulk cross-family audits |
| Strong | `claude-opus-4-8`, `codex` (gpt-5.5) | subscription | Escalation on contested or freshly-cleared targets |
| Max | `claude-fable-5` | subscription | Reserved for the hardest edges (Goodman, Ereshefsky/Reydon) |

**Escalation ladder.** Every target first gets a local-tier refute pass and a
cheap cross-family refute pass. A `cleared` result is not trusted from the
cheap tier alone: promoting a target to `cleared` requires at least one
strong-tier audit from a family distinct from the cheap-tier clearers. A
`failed`/`weakened` result from any tier stops the ladder — the target is
demoted and routed to revision, not re-audited until it changes. This escalates
to a strong model only where cheap models already agree it holds, which is
exactly where a hidden flaw is most costly.

**Effort.** Local and cheap tiers run at low effort (mechanical refutation
attempts). Strong and max tiers run at high/xhigh — the edges that reach them
are the ones where reasoning depth changes the verdict.

## Budget, concretely

Under subscription auth the real budget is **rate limits and time**, not money.
A fully redundant, escalated spine audit (20 targets, K=2 families, ~20%
escalated to strong) is a few dozen CLI invocations — trivial for local models,
and a modest dent in a Claude Code / Codex subscription window. At portfolio
scale (many papers on a recurring cron) the binding constraint is the
subscription's messages-per-window cap, so the driver should front-load the
local tier (unmetered) and pace the subscription tiers across windows rather
than bursting. The lever worth tuning is K (how many independent families
clearance needs); with local models bearing most of the volume, raising K is
nearly free.

## Re-running: drift as the outcome signal

Fidler's sharpest point was that `cleared` is unfalsifiable without an outcome
loop, and Tetlock's was that no one tracks how often cleared things later
fail. The pivot supplies the loop for free. Re-audit the spine on a cron with
a *stronger* ladder than last time (or a newly released model). If an edge
that was `cleared` last month `fails` under this month's stronger auditor,
that is a recorded, dated demotion — the calibration signal the manual design
could never produce. The tool keeps every audit artifact, so the history of a
verdict (who cleared it, when, which model later broke it) is diffable in git.

This also bounds the known limit of the whole approach. Barnes and
Christiano's obfuscated-arguments result shows an argument can be wrong
somewhere with no locally-attackable step; edge-local auditing cannot catch
that class. Re-auditing with escalating model strength is the practical
hedge: a flaw no model could localize last quarter may be localizable by a
stronger model this quarter. The tool should never report a spine as
"cleared, done" — only "cleared under the strongest ladder run so far."

## The two entry points

Dispatch is kept out of the core tool. `claim-dag` (validate, plan, promote,
argdown, report) never calls a model; `claim-dag-run` (a separate console
script) is the only part that does. This keeps model-specific plumbing out of
the audit record and lets the whole contract be tested offline.

**`claim-dag plan`** emits the audit jobs still needed to reach clearance, each
with an assigned model, family, tier, and framing.

**`claim-dag-run audit <dir>`** reads the plan, assembles each prompt (the
node/edge records, plus a window of the source text around the claim's anchor),
dispatches it to the relevant CLI (`ollama run`, `claude`, `codex`, `copilot`,
`gemini`), writes a validated audit artifact back, and runs promotion. Two
safety rules matter:

- **Identity is stamped, not trusted.** The runner writes `model`, `family`,
  `tier`, `framing`, target id, and date from the job it dispatched, overwriting
  whatever the model claimed. A model cannot relabel its own family or tier to
  slip past the independence bar.
- **Unparseable output defers, never clears.** If a model returns reasoning with
  no recoverable verdict block, the artifact is written `verdict: deferred` with
  empty fields — which `validate` will not count toward clearance. Small local
  models that ramble simply don't contribute; they never fabricate a pass.

**`claim-dag promote <dir>`** (model-free) recomputes every verdict from the
artifacts on disk and writes them back: a target clears only if it meets the
bar, dissent demotes, and inference verdicts propagate from their supporting
edges and sources. It is idempotent.

**`claim-dag-run reaudit <dir>`** is the drift loop. It re-attacks every
currently-`cleared` target with the strongest available auditor from a family
that has not already cleared it (escalating to the `max` tier), promotes, and
appends any demotions to `drift-log.yaml` with a date. Run it on a cron: a flaw
that no model could localize last quarter may be localizable by a stronger model
this quarter, and every such demotion is a dated, recorded calibration signal.
The tool never reports a spine as finished — only "cleared under the strongest
ladder run so far."
