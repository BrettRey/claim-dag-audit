# Review Board Synthesis — 2026-07-05

Non-redundant blend: van Gelder, Mayo, Fidler on Opus (Claude subagents);
Betz, Rushby on Codex (gpt-5.5, read-only sandbox). Personas and watch-fors
from ADVISORY-BOARD.md. Verdicts: 5/5 Revise & Resubmit, judged against
"ready to run the Kinds pilot as designed?" None recommended Reject; all
five said the pilot is worth running after fixes.

## Opus consensus

All three treat the node/edge decomposition and the adversarial definition
of `cleared` as the right design, and all three converge on the same core
defect: `cleared` is a hand-editable scalar with no enforced link to any
audit artifact. Mayo and Fidler independently ran the same falsification
test (set everything to `cleared`, provide zero audit files, `validate`
exits 0). Distinctive contributions:

- **van Gelder:** double-entry verdicts (audit Markdown + YAML status) with
  no reconciling command is the classic solo-maintenance killer; source
  manifest stores a bare path with no content hash, so claim anchors rot
  silently on the first paper revision; the decorative-premise check will
  be mostly false positives under the spine-only pilot scope and will
  train the user to ignore warnings; the suppressed premise is authored in
  up to three places with nothing reconciling them.
- **Mayo:** no field records whether an audit *could have failed*; proposes
  a required severity block (falsifier / probe / probe_outcome /
  could_have_failed / auditor_independence), with author-only clearing
  capped below `cleared`, and status coherence so a conclusion cannot
  outrank its weakest incoming support.
- **Fidler:** the status enum conflates workflow states with outcome states,
  and the 7-value node/edge enum does not map onto the 4-value verdict
  vocabulary in audit.schema.yaml; no codebook, so two auditors cannot
  code reliably; no history, confidence field, or outcome signal, so a
  `cleared` verdict can never be shown wrong; run the pilot itself as a
  two-auditor agreement study.

## Codex consensus

Both accept the design premises and attack the machinery:

- **Betz:** the generated .argdown is not valid Argdown (`->` is an attack
  relation; support needs indented `+>`/`<+`; `#` is a hashtag/heading, not
  a comment), verified against argdown.org/syntax. Sharper and new: a
  conjunctive premise set (`from: [C001, C002]`) is exploded by
  `to_argdown()` into two *independent* support arrows, which changes the
  reconstruction; the schema has no premise-set or argument-node semantics
  at all. The prompts would not reliably yield validator-ready YAML
  (extract-claims omits the required `status` field; no prompt states the
  bare-list top-level shape).
- **Rushby:** relations have no downstream semantics; `analyze()` treats
  every edge as positive dependency, so a `rebuts` edge counts as support
  for an inference node. Defeaters are prompted as free text but never
  managed as objects (no list, status, owner, resolution, residual risk).
  `cleared` neither requires an audit record nor propagates: a conclusion
  can be `cleared` above `failed` premises.

## Cross-model consensus

1. `cleared` is unenforced: no artifact link, no verdict reconciliation
   (van Gelder, Mayo, Fidler, Rushby).
2. Status must interact with the graph: failed/weakened support should cap
   downstream status (Mayo, Rushby).
3. The strengths are real and shared by all five: the node/edge/adversarial
   decomposition, `suppressed_premise` as a first-class field, file-first
   diffable artifacts, and the deferral of LLM automation.

## Contradictions and tensions (the interesting part)

- **Fidler vs van Gelder.** Fidler wants more required fields (auditor,
  elapsed time, numeric confidence, append-only history); van Gelder's
  central warning is that every hand-authored field raises the maintenance
  tax that kills solo tools. Partial resolution: a recording command
  (`claim-dag audit-edge E001 --verdict ...`) can capture auditor, date,
  and history automatically, leaving only confidence as a new manual entry.
- **Betz vs the project's minimalism.** Betz wants argument-node/premise-set
  semantics approaching a full reconstruction format; the development rules
  say plain YAML and small commands. The minimal concession that preserves
  correctness: keep one-edge-equals-one-inference-with-conjunctive-premises
  as the stipulated semantics, and fix the Argdown emitter to respect it.
- **Mayo vs Goodhart.** Her severity block is itself fillable pro forma; she
  concedes free text has no teeth. The block buys audit trail, not severity;
  severity ultimately rides on auditor independence, which is a protocol
  choice, not a schema field.

## Prioritized revisions (top 5)

1. Enforce the status–artifact link: `validate` errors when a node/edge
   status is `cleared`/`weakened`/`failed` without a matching audit file
   whose verdict agrees; add `claim-dag audit-edge` / `audit-node` recording
   commands so verdicts are entered once. (4/5 reviewers.)
2. Give relations semantics in `analyze()`: only `supports`/`requires`
   count as support; add status coherence so a conclusion cannot outrank
   its weakest incoming support edge. (Rushby, Mayo.)
3. Rewrite `to_argdown()`: valid Argdown relations (`+>`/`<+` indented),
   `//` comments or hashtags, and premise sets rendered as one inference
   (argument node or PCS), not independent arrows. (Betz.)
4. Pin the source: content hash (or git blob SHA) in source-manifest.yaml
   plus a `validate` check that each anchor still occurs in the source, so
   drift is loud. (van Gelder, Fidler.)
5. Write the status codebook: split workflow axis from outcome axis, align
   the 7-value enum with the 4-value verdict vocabulary, one-sentence
   definition plus boundary case per value; and run the pilot as a
   two-auditor (or two-model) agreement study with a disagreement log.
   (Fidler.)

Honourable mentions: scope-gate the decorative-premise check (`spine:` flag
or opt-in) before it cries wolf on the spine-only pilot (van Gelder); add
schema-conformant YAML examples and exact top-level shape to the prompts
(Betz); single source of truth for the suppressed premise (van Gelder).

## Self-check and contamination notes

- Verdict unanimity (5/5 R&R) is suspiciously tidy; treat it as "the board
  found the same load points from five angles," not as field consensus.
  The content diverged by lens, which is what the board is for.
- Steering: reviewer prompts carried the board's watch-fors, so some
  findings were pointed at (Rushby: rebuts-as-support and artifact
  enforcement; Betz: Argdown validity; Mayo: severity). Findings *not*
  steered, and therefore stronger evidence: Betz's premise-set explosion,
  van Gelder's anchor rot / double-entry / warning false positives, Fidler's
  two-vocabulary status finding and missing history, Mayo's
  could-have-failed field.
- Mild contamination: DECISIONS.md (read by both Codex reviewers) names the
  board and its risk-surface labels. Neither Codex review shows signs of
  using it beyond its assigned focus.
- Mayo's and Fidler's `cleared`-with-no-artifacts exploit was verified by
  actually running `validate`; Betz's Argdown claims were verified against
  argdown.org. Reviewers' from-memory literature references (GSN, Bloomfield/
  Bishop, repliCATS specifics, Rationale-era adoption history) are flagged
  in their reviews as unverified.
- Per the skill: the board judged execution, not whether the idea is worth
  pursuing. Nothing here bears on the latter; all five affirmed the core
  decomposition.
