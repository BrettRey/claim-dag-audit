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

