# Claim Extraction Prompt

Read the paper and extract substantive claims, not paragraphs.

Paper source:

```text
[paste paper source]
```

For each claim, produce:

- `id`: C001, C002, ...
- `anchor`: a verbatim text span from the paper (copy it exactly, so drift is detectable)
- `type`: one of definition, empirical-premise, cited-claim, inference, stipulation
- `section`: section title or location
- `verdict`: unaudited
- `warrant`: source-check, data-check, edge-audit, or stipulation-check
- `notes`: one short note on why this claim matters
- `background: true` (optional): mark off-spine framing/scoping claims so the
  decorative-premise check does not flag them

Rules:

- Split compound statements when the parts could fail independently.
- Do not extract rhetorical transitions as claims.
- Do not merge an inference with its premise.
- Prefer too many claims over too few in the first pass; consolidation happens later.
- Every claim starts `verdict: unaudited`; it changes only when an adversarial audit clears, weakens, or fails it.

Return a top-level YAML list (no code fences, no wrapper key).
