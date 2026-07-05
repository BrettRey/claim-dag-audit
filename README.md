# Claim DAG Audit

Claim DAG Audit turns a paper into a dependency graph of claims, then audits
nodes and inference edges separately.

The tool is deliberately file-first. It creates and validates plain YAML and
Markdown artifacts that can live inside a paper repository:

```text
audits/
  claim-dag/
    2026-07-05/
      source-manifest.yaml
      claims.yaml
      edges.yaml
      graph.argdown
      node-audits/
      edge-audits/
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

Initialize an audit directory:

```bash
claim-dag init /path/to/paper/audits/claim-dag/2026-07-05 \
  --paper-title "Kinds as Projectibility Profiles" \
  --source /path/to/paper/main.tex
```

Validate claims and edges:

```bash
claim-dag validate /path/to/paper/audits/claim-dag/2026-07-05
```

Generate Argdown:

```bash
claim-dag argdown /path/to/paper/audits/claim-dag/2026-07-05
```

Generate a report:

```bash
claim-dag report /path/to/paper/audits/claim-dag/2026-07-05
```

## Data Contract

`claims.yaml` is a list of claims:

```yaml
- id: C001
  anchor: "Homeostatic control is a subcase, not the default."
  type: inference
  section: Abstract
  status: uncleared
  warrant: edge-audit
```

`edges.yaml` is a list of support relations:

```yaml
- id: E001
  from: [C001, C002]
  to: C003
  relation: supports
  suppressed_premise: "If these achievements come apart, no single label should name all of them."
  status: needs-audit
```

## Audit Standard

`cleared` means someone tried to break the claim or edge and failed. It does not
mean the passage read plausibly.

The intended first pilot is `papers/preprints/kinds-as-projectibility-profiles/`.

