<p align="center">
  <img src="assets/logo-wordmark.svg" alt="claim-dog" width="360">
</p>

# Claim DAG Audit

Claim DAG Audit turns a paper into a dependency graph of claims, then audits
nodes and inference edges separately. Auditing is done by language models; the
tool's job is to define an audit *contract* strict enough that a fleet of
models cannot rubber-stamp its way to a `cleared` verdict, and to enforce that
contract mechanically. See `docs/llm-runner.md` for the architecture.

The tool is deliberately file-first. It creates and validates plain YAML and
Markdown artifacts that can live inside a paper repository:

```text
audits/
  claim-dag/
    2026-07-05/
      source-manifest.yaml     # paper, source hash, built_by (builder family)
      claims.yaml
      edges.yaml
      graph.argdown
      node-audits/             # one Markdown+frontmatter file per (claim, model)
      edge-audits/             # one Markdown+frontmatter file per (edge, model)
      adversarial/
      report.md
```

## Install

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Use

```bash
# Initialize (records a source hash and the builder family, excluded from clearance)
claim-dag init /path/to/paper/audits/claim-dag/2026-07-05 \
  --paper-title "Kinds as Projectibility Profiles" \
  --source /path/to/paper/main.tex \
  --built-by local

claim-dag validate /path/to/paper/audits/claim-dag/2026-07-05   # structure + audit backing
claim-dag plan     /path/to/paper/audits/claim-dag/2026-07-05   # audit jobs still needed to clear
claim-dag promote  /path/to/paper/audits/claim-dag/2026-07-05   # verdicts <- artifacts (no models)
claim-dag argdown  /path/to/paper/audits/claim-dag/2026-07-05   # valid Argdown
claim-dag report   /path/to/paper/audits/claim-dag/2026-07-05
```

The core `claim-dag` never calls a model. A separate console script,
`claim-dag-run`, is the dispatcher:

```bash
claim-dag-run audit   /path/.../2026-07-05 --dry-run   # preview jobs, no model calls
claim-dag-run audit   /path/.../2026-07-05             # dispatch, write artifacts, promote
claim-dag-run reaudit /path/.../2026-07-05             # re-attack cleared targets, log drift
```

`claim-dag-run` stamps each artifact's identity fields (model, family, tier,
framing) from the job rather than trusting the model's self-report, and writes
`verdict: deferred` when a model's output has no recoverable verdict — so a
rambling model never fabricates a clearance. See `docs/llm-runner.md`.

## Data Contract

`claims.yaml`:

```yaml
- id: C001
  anchor: "Homeostatic control is a subcase, not the default."
  type: inference
  section: Abstract
  verdict: unaudited      # unaudited | cleared | weakened | failed | deferred
```

`edges.yaml`:

```yaml
- id: E001
  from: [C001, C002]      # multiple ids = one joint (conjunctive) premise set
  to: C003
  relation: supports      # only supports/requires count as support
  suppressed_premise: "If these achievements come apart, no single label should name all of them."
  verdict: unaudited
```

Audit artifacts are Markdown with a YAML frontmatter block (see
`schemas/audit.schema.yaml`).

## Audit Standard

`cleared` means an adversarial audit failed to break the node or edge. It is
enforced, not asserted. `claim-dag validate` errors unless a `cleared` node or
edge is backed by:

- audit artifacts from **≥2 model families**, none the builder family (`built_by`);
- **≥1 strong-tier** audit (cheap/local agreement is not enough);
- each with `framing: refute` and a non-empty `could_have_failed`;
- **no** dissenting artifact — one `failed`/`weakened` result breaks clearance.

It also errors on support cycles and on any conclusion cleared above weaker
support (verdict coherence).

The intended first pilot is `papers/preprints/kinds-as-projectibility-profiles/`.
