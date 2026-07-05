# Advisory Board (aspirational)

Five people whose perspectives cover the tool's main risk surfaces. Not
contacted; this is a note about whose work to read and whose objections to
pre-empt. Names and affiliations from model memory (early 2026); verify
before any outreach.

## The board

1. **Tim van Gelder** (Melbourne) — argument mapping, SWARM/IARPA CREATE.
   Covers: why argument-mapping tools historically fail adoption; what the
   audit workflow must feel like to survive month three.

2. **Gregor Betz** (KIT DebateLab) — Argdown, LLM-based argument
   reconstruction. Covers: the deferred automation path (claim extraction,
   edge audits by LLM); Argdown format correctness; what reconstruction
   granularity is stable.

3. **John Rushby** (SRI) — assurance cases, epistemology of certification.
   Covers: decades of engineering practice on adversarially audited claim
   graphs (GSN, eliminative argumentation); defeaters; confirmation bias in
   safety-style arguments. `cleared` semantics should be checked against
   eliminative argumentation (Goodenough & Weinstock, SEI).

4. **Deborah Mayo** (Virginia Tech, emerita) — severe testing. Covers: what
   makes an edge audit severe rather than performed; the philosophical
   grounding for "cleared means an attack failed."

5. **Fiona Fidler** (Melbourne) — repliCATS, structured elicitation on
   claim replicability. Covers: calibration and outcome feedback (do
   `cleared` edges survive?); protocol design for group claim assessment.

## Runners-up

- **Hugo Mercier** — argumentative theory of reasoning; solo vs. interactive
  adversarial audit (bears directly on the LLM-dispatch decision).
- **Philip Tetlock** — calibration discipline; base rates for cleared-then-
  failed edges.
- **Beth Barnes / Geoffrey Irving** — obfuscated-arguments problem: the known
  theoretical limit of edge-local auditing.
- **Joel Chan** (Maryland) — discourse graphs; nearest neighbouring data
  model and community.

## Standing objections to pre-empt

- van Gelder: nobody maintains the map once the novelty wears off.
- Rushby: audits inherit the auditor's confirmation bias unless defeaters
  are enumerated systematically.
- Mayo: an attack that couldn't have succeeded clears nothing.
- Fidler: without outcome tracking, `cleared` is unfalsifiable bookkeeping.
- Barnes/Irving: a paper can be wrong nowhere-locally; edge audits can all
  pass on a false conclusion.
