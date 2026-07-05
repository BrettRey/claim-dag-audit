# Claim Extraction Prompt

Read the paper and extract substantive claims, not paragraphs.

For each claim, produce:

- `id`: C001, C002, ...
- `anchor`: a verbatim or near-verbatim text anchor from the paper
- `type`: one of definition, empirical-premise, cited-claim, inference, stipulation
- `section`: section title or location
- `warrant`: source-check, data-check, edge-audit, or stipulation-check
- `notes`: one short note on why this claim matters

Rules:

- Split compound statements when the parts could fail independently.
- Do not extract rhetorical transitions as claims.
- Do not merge an inference with its premise.
- Prefer too many claims over too few in the first pass; consolidation happens later.
- Mark claims as `uncleared` unless they have already been adversarially audited.

Return YAML only.

