# Review: Tim van Gelder (argument mapping, adoption)

## 1. One-sentence summary

`claim-dag-audit` is a file-first CLI that turns a paper into a plain-YAML
dependency graph of claims and inference edges, then supports auditing nodes
(are the claims true/grounded?) and edges (do the premises actually license the
conclusion?) separately, with `cleared` reserved for items that survived a
deliberate attack rather than items that merely read well.

## 2. Strengths

- **The node/edge split is the right core.** Most argument tools I have watched
  fail conflate "is this premise true" with "does this premise support the
  conclusion." This tool separates them at the data level: `claims.yaml` carries
  truth/grounding status, `edges.yaml` carries a `relation`
  (`supports/requires/rebuts/qualifies`) plus a `suppressed_premise` field
  (`edges.yaml`; `schema.py:25`, `schema.py:125-126`). Naming the suppressed
  premise as a first-class field operationalizes the Toulmin warrant move that
  most mapping tools bury in a link colour. That is the single best design
  decision here.

- **File-first, diffable, and it lives with the paper.** Plain YAML plus
  Markdown in the paper repo (`README.md:9-21`, `DECISIONS.md:8-10`) is the
  correct 2026 substrate. A large share of the Rationale/bCisive-era mortality
  came from proprietary, non-diffable formats locked in a standalone app; the
  map became a parallel artifact nobody could review or version. Git-diffable
  YAML means the audit travels with the manuscript, shows up in a PR, and can be
  read without the tool. This alone clears a bar that killed prior tools.

- **`cleared` is defined adversarially, and the exit standard is written down.**
  `DECISIONS.md:16-18`, `README.md:84-87`, and the `adversarial-weakest-edges.md`
  prompt make the pass condition "an attack was attempted and failed," not "the
  prose seemed plausible." Defining the exit standard as failed-attack, and
  giving the adversarial pass its own artifact channel (`adversarial/`), is the
  discipline that separates this from a diagram generator. The deferral of LLM
  automation until the manual I/O shape is known (`CLAUDE.md` dev rules) is also
  methodologically honest rather than tool-first.

## 3. Weaknesses

- **Double-entry status bookkeeping with nothing reconciling it.** An edge
  verdict is recorded in *two* places that can silently disagree: the audit
  Markdown in `edge-audits/` (where `audit.schema.yaml:4-6` requires a
  `verdict`) and the `status` field in `edges.yaml` (`schema.py:123-124`). The
  CLI has no command that records an audit or links the two: `cli.py:14-40`
  offers only `init`, `validate`, `argdown`, `report`. The optional `audit:`
  pointer (`edges.schema.yaml:24`) is never checked by `validate` (`schema.py`
  never reads it; `graph.py:21-66` never reads it). So the human writes the
  verdict once in prose and must remember to hand-flip the YAML status, and
  `validate` will happily report an edge as `cleared` with no audit file behind
  it, or an audit file saying `failed` sitting next to a YAML `status: cleared`.
  This is exactly the maintenance tax that killed solo use of earlier tools: a
  representation kept in parallel to the real work, by hand, with no forcing
  function. *Actionable:* add `claim-dag audit-edge E001 --verdict cleared` that
  writes the audit stub and sets the status in one operation, and make
  `validate` error when (a) a `cleared`/`failed`/`weakened` status has no
  matching audit file, or (b) the audit file's verdict disagrees with the YAML
  status.

- **No source pinning; anchors will rot by month two.** `source-manifest.yaml`
  stores a bare path and a timestamp (`cli.py:48-53`); it stores no content
  hash, git blob ref, or line range. Claim `anchor`s are free-text "verbatim or
  near-verbatim" strings (`claims.yaml`; `extract-claims.md:7`). A paper under
  audit is, by definition, a paper being revised. The moment the author edits
  the `.tex` in response to a referee, the anchors point at text that no longer
  exists and `validate` cannot tell, because it never opens the source. By the
  third month the graph describes a paper that is gone, and resyncing costs more
  than re-reading the manuscript, so the audit is abandoned. That is the
  canonical argument-map death. *Actionable:* record a content hash (or git blob
  SHA) of the source in the manifest, and add a `validate` check that each
  `anchor` still occurs as a substring of the current source; warn on every miss
  so drift is visible in the diff.

- **The decorative-premise check will cry wolf under the pilot's own scope.**
  `graph.py:52` flags any `definition`/`empirical-premise`/`cited-claim`/
  `stipulation` with no outgoing edge as decorative. But the pilot is explicitly
  scoped to "the central spine only" (`CLAUDE.md`, `STATUS.md:19-26`), which
  means every legitimately-off-spine framing definition, scoping stipulation, and
  background citation in the Kinds paper will light up as decorative on the first
  run. A warning channel that is mostly false positives on day one trains the
  user to ignore warnings, which is how linters die. *Actionable:* only run the
  decorative check against nodes marked in-scope (add a `spine: true` / scope
  field, or pass a scope set), or make it opt-in rather than default.

- **(Related) The suppressed premise is authored up to three times and never
  reconciled.** It is written in `edges.yaml` at build time
  (`build-edges.md:10`), re-derived in the edge audit body
  (`audit-edge.md:27`, step 3), and required again as a field of the
  `edge_audit` record (`audit.schema.yaml:5-6`). The audit is precisely the step
  where the *real* hidden premise gets found, so the `edges.yaml` copy is the one
  most likely to be wrong, and nothing flags the divergence. Fold the audited
  premise back into `edges.yaml`, or make the audit the single source of truth
  and stop storing it on the edge.

## 4. Key question

Walk me through auditing one edge end to end and name every file you touch by
hand: how many times do you retype the verdict and the suppressed premise, and
across the 6-node Kinds spine how many edges is that? Then: what in the *tool*
(not in your own discipline) keeps `claims.yaml`, `edges.yaml`, and the audit
Markdown from quietly disagreeing once the paper has been revised twice? If the
answer is "nothing yet," what makes you confident the manual pilot survives long
enough to produce the I/O requirements it is supposed to expose?

## 5. Verdict

**Revise & Resubmit.** The design is sound and the pilot is admirably small, but
as written the manual protocol has the two properties that reliably kill solo
maintenance: verdicts double-entered with no reconciliation (`cli.py:14-40`,
`schema.py:123-124`) and unpinned source anchors that go stale on the first
revision (`cli.py:48-53`). Add one recording command plus a `validate` rule that
a non-`uncleared` status requires a matching audit file, and pin the source with
a hash and an anchor-still-present check, and the pilot will survive to yield the
data it is meant to yield. Ship those two changes first; the Kinds audit is worth
running, just not exactly as designed.

*Source-grounding note:* claims above about Rationale/bCisive-era adoption
failure are my own professional recollection and judgment, not citations from a
source read in this session; treat any hard empirical claim as needing
verification before it is repeated in print.
