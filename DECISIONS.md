# DECISIONS

2026-07-05 - Build Claim DAG Audit as a standalone tool under
`tools/claim-dag-audit/`, with per-paper audit artifacts stored in each paper
repo. Reason: the protocol should generalize beyond one paper, but the audit
record belongs with the paper whose argument is being cleared.

2026-07-05 - Keep the first version file-first: YAML claims and edges,
Markdown audits, generated Argdown, and generated reports. Reason: the method
needs inspectable, diffable artifacts more than a database or web UI.

2026-07-05 - Use `Kinds as Projectibility Profiles` as the first pilot. Reason:
it is recent, compact, and conceptually central, with known edge-pressure
points around Goodman, Ereshefsky/Reydon, support grades, and demotion rules.

2026-07-05 - Treat `cleared` as an adversarial status, not a readability
status. Reason: an audit node or edge is cleared only when an attack has failed,
not when the prose seems plausible.

2026-07-05 - Name a five-person aspirational advisory board (van Gelder, Betz,
Rushby, Mayo, Fidler) in ADVISORY-BOARD.md. Reason: the board enumerates the
tool's risk surfaces (adoption, automation, audit rigour, severity, calibration)
and the standing objections each perspective supplies; not an outreach list.

2026-07-05 - Reformulate for all-LLM auditing (no human auditors). Architecture
in docs/llm-runner.md. Reason: the pivot dissolves van Gelder's maintenance-tax
and Fidler's two-coder-cost objections, and makes model sycophancy (Mayo,
Mercier) the central threat. Severity is engineered via three enforced
mechanisms: adversarial (refute) framing, cross-family independence, and
dissent-breaks-clearance.

2026-07-05 - `cleared` is now machine-enforced. validate errors unless a cleared
node/edge is backed by audit artifacts from >=2 model families (excluding the
builder family in source-manifest.built_by), >=1 strong-tier, each with
framing: refute and a non-empty could_have_failed, and with no dissenting
failed/weakened artifact. Reason: the review board's unanimous finding that
cleared was an unbacked scalar (Mayo/Fidler reproduced the exploit).

2026-07-05 - Give edge relations semantics. Only supports/requires count as
support; rebuts/qualifies do not. Added verdict-coherence (a cleared conclusion
cannot outrank its weakest support) and made support cycles a validation error.
Reason: Rushby/Mayo (rebuts-as-support), and cycles in a tool named for a DAG.

2026-07-05 - Fix the Argdown emitter to valid syntax and preserve premise sets:
a conjunctive `from` list renders as one PCS argument, not independent arrows;
rebuts renders as an incoming attack, qualifies as a note. Reason: Betz showed
`->` meant attack and the old output exploded joint premises into independent
support.

2026-07-05 - Collapse the status vocabulary to a single verdict axis
(unaudited/cleared/weakened/failed/deferred); pin the source with a sha256 in
the manifest; scope the decorative check to non-background nodes; delete the
unused Jinja templates; add a pytest suite. Reason: Fidler (two conflated
axes, no codebook), van Gelder (anchor rot, decorative false positives), Betz
(dead templates), board-wide (no unit tests).

2026-07-05 - Build the external runner as a separate console script
(claim-dag-run) with audit/reaudit subcommands, plus a model-free
claim-dag promote. Reason: the core tool must never call models (keeps dispatch
out of the audit record and lets the contract be tested offline). The runner
stamps identity fields (model/family/tier/framing) from the job rather than
trusting model self-report, and writes verdict: deferred on unparseable output,
so a rambling model cannot fabricate a clearance. Verified with mock tests, a
live ollama dispatch, and a CLI dry-run.

2026-07-05 - reaudit escalates to the strongest available auditor (max tier,
e.g. claude-fable-5) and appends demotions to drift-log.yaml. Reason: the drift
loop needs a genuinely stronger attacker even when the strong families already
cleared a target; a break from any credible model demotes (dissent breaks
clearance), giving the dated calibration signal Fidler and Tetlock asked for.

2026-07-05 - Auditing runs under subscription auth (Claude Code + Codex CLIs),
not the metered API. Reason: no per-token cost; the real budget is subscription
rate limits and wall-clock, so the ladder is about capability + independence,
and the runner needs no API keys (the CLIs carry auth).

2026-07-05 - Treat local ollama models as distinct families: glm=Zhipu,
qwen=Alibaba, gemma=Google (gemma shares the google family with the Gemini API).
Reason: they are genuinely different training lineages, so they satisfy the
cross-family independence bar for free; a typical clearance then spends just one
metered strong-tier call. Dropped the flaky gemini API entry.

2026-07-05 - Drop claude-fable-5 from the ladder for now (no Fable credits);
Opus 4.8 at max effort stands in as the drift/max-tier attacker. Restore Fable
(tier max) when credits return. Reason: user constraint.

2026-07-05 - Wire the policy's effort field through to the CLIs (claude
--effort, codex model_reasoning_effort) and dial strong/max down; a refutation
pass does not need top-of-dial reasoning. OpenAI strong auditor = gpt-5.4 at
medium (gpt-5.4 / gpt-5.4-mini confirmed via codex -m).

2026-07-05 - codex must be invoked with --skip-git-repo-check. The runner runs
it in a neutral non-git cwd (to keep repo context out of the audit), and without
the flag codex hangs on its git-repo check. An earlier "codex is too slow"
finding was a mis-invocation, not a speed problem: with the flag a real gpt-5.4
audit returns in ~29s. Verified live via a subagent (real `failed` verdict).

2026-07-05 - Published to public GitHub: https://github.com/BrettRey/claim-dag-audit
Added a cute "claim-dog" logo (assets/logo.svg, logo-wordmark.svg), with the
wordmark theme-aware so it reads on dark grounds.
