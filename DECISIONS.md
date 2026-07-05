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
