# Review: Deborah Mayo (severe testing)

*Source-grounding note: the one external work I lean on is my own* Statistical
Inference as Severe Testing *(2018). I am reconstructing its severity account
from memory in this session, not re-reading it; treat the formulation below as
the framework's standard sense, to be verified against the book if quoted.*

Before the criticism, the design as I understand it. The tool decomposes a paper
into a claim DAG and then keeps three audit levels strictly apart (`CLAUDE.md`):
node audits (is the claim true, sourced, consistent), edge audits (do the cited
premises actually license the target), and an adversarial pass (attack the
weakest unresolved edges). The governing stipulation, stated in four places
(`README.md:86`, `DECISIONS.md:17`, `CLAUDE.md`, `prompts/audit-edge.md:50`), is
that `cleared` is an *adversarial* verdict: an attack was mounted and failed, not
that the prose read well. That is exactly the right target. It is, almost
verbatim, the distinction between a claim that survived a probe and a claim that
was merely not challenged. The structural checks in `graph.py` (unsupported
inferences, decorative premises, cycles) are genuine severity in miniature:
automated tests with the *capacity to return a negative*. So the instinct is
sound, and the vocabulary already names the thing I would insist on. My quarrel
is not with the aim. It is that the artifact format does not yet make the aim
true of anything.

## 1. One-sentence summary

`claim-dag-audit` is a file-first CLI that turns a paper into a plain-YAML/Markdown
dependency graph of claims and inference edges, validates the graph's structure,
and records per-node and per-edge audit verdicts under the standard that
`cleared` means an adversarial attack was attempted and failed.

## 2. Strengths

- **The load-bearing distinction is drawn at the right joint.** Separating node
  truth from edge validity, and both from an adversarial pass, is precisely the
  decomposition error-statistics needs: a true premise plus a fallacious link is
  a different failure from a false premise, and the tool refuses to let one
  clear the other. `prompts/audit-edge.md:24-30` even forces the auditor to
  *assume the premises true* before asking whether they support the conclusion,
  which isolates the inference for testing.
- **Some checks can actually fail, and run without the auditor's cooperation.**
  `graph.py:43-54` flags inference nodes with no incoming support and premises
  with no outgoing edge; `find_cycles` catches circular support. These are the
  seed of the right idea: probes with real error capacity, applied by the
  machine rather than asserted by the person being audited.
- **The evidence-pointer warnings gesture at grounding.** `schema.py:79-82`
  warns when a `cited-claim` names no source and when an `empirical-premise`
  names no evidence. That is severity-adjacent: it demands the *handle* by which
  a check could later be run.

## 3. Weaknesses

- **`cleared` is a free-floating token; nothing couples it to evidence that a
  test occurred, let alone that the test had power.** The validator checks only
  that `status` is a member of the enum (`schema.py:15-23`, `77-78`). The CLI
  never reads `node-audits/`, `edge-audits/`, or `adversarial/`: `cmd_validate`
  (`cli.py:63-74`) calls `load_audit`, which loads *only* `claims.yaml` and
  `edges.yaml` (`graph.py:11-14`). I confirmed the consequence empirically: set
  every node and edge to `status: cleared`, provide no audit artifacts at all,
  and `validate` returns exit 0 with zero errors. So an auditor can clear the
  entire spine of the Kinds paper without a single attack having been mounted,
  and the tool reports success. The adversarial meaning of `cleared` lives in
  prose (`README.md:86`) but is enforced nowhere in the format. That is the gap
  between a stipulation and a test, and it is the whole ballgame.
- **Even where an attack is recorded, no field captures whether it *could have
  failed*.** `audit.schema.yaml` requires `attack` (edges) and `test` (nodes),
  which is a start, but (a) the schema is never loaded by any command, so it is
  aspirational, and (b) both are free-text strings with no requirement that the
  probe had teeth. A pro-forma "I considered whether X, and it holds" satisfies
  the field. `prompts/audit-node.md:19` does ask for the falsifier ("State what
  would make the claim false"), but the prompt then jumps to a verdict
  (`:23`) without ever requiring the auditor to confirm that the falsifying
  condition was *searched for and found absent*. The severe middle step, the
  probe that would have caught the error had one been present, is exactly the
  step the format does not record. A test that a false claim would pass with high
  probability is worthless, and nothing here lets you tell such a test from a
  stringent one.
- **A downgraded edge does not contaminate its conclusion, and no auditor
  independence is required.** `analyze()` validates topology but never checks
  *status coherence*: a `cleared` inference node whose only incoming edge is
  `failed` or `weakened` raises no error (`graph.py:43-66`). Epistemically a
  conclusion can be no more cleared than its weakest supporting edge; the DAG is
  the perfect structure to propagate that ceiling, and it is left on the table.
  Relatedly, `audit.schema.yaml` requires an `auditor` field but permits
  `auditor: self`. An author clearing their own claim is a low-severity probe by
  construction: it would very probably pass a false claim, because the tester
  shares the blind spot that produced it. For an eventual LLM auditor the base
  rate of "cleared" is higher still, since a model asked "did this survive a
  serious attack?" tends to oblige. Without an independence requirement and a
  forced falsifier-then-search, the automated pass has severity near zero.

## 4. Key question

Show me two edge audits that both end in `cleared`, one severe and one a rubber
stamp. Which field in `edges.yaml` or the audit artifact differs between them,
and which line of `validate` reads that field? If the answer is "none" and "no
line," then `cleared` records that critique was performed, not that the claim
would have been caught had it been false, and the tool measures diligence, not
severity.

A severity requirement in this file format need not be heavy. Add a required
block to each audit artifact: `falsifier` (the observable that would obtain if
the claim/edge were bad), `probe` (what was actually done to look for it),
`probe_outcome`, `could_have_failed` (one line naming the result that would have
flipped the verdict), and `auditor_independence` (`author` | `independent-human`
| `independent-model`), with a rule that author-only clearing caps status below
`cleared`. Then make `validate` refuse `status: cleared` on any node or edge
unless a matching artifact exists with a non-empty `could_have_failed`, and add a
status-coherence check so a `cleared` node cannot outrank its weakest incoming
edge.

## 5. Verdict

**Revise & Resubmit.** As designed the pilot will run and produce diffable
artifacts, but it cannot deliver its headline claim: the format has no tripwire
that distinguishes a severe audit from a rubber stamp, so clearing the Kinds
spine would *look* like passing adversarial verdicts while recording no evidence
of probativeness. Add the minimal severity block and the status-artifact link
first, so the pilot becomes a severe test of the protocol rather than a
low-severity test that passes everything and feels productive.
