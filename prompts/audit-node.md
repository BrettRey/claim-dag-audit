# Node Audit Prompt

You are auditing one claim from a paper. **Your job is to break it, not to
confirm it.** Assume a hostile reviewer. If you cannot rule out the way it
fails, the verdict is `failed` or `weakened`, never `cleared`. Default to
broken under uncertainty.

Claim:

```yaml
[paste claim record]
```

Relevant paper context:

```text
[paste local passage plus surrounding paragraphs]
```

Your task:

1. State what would make the claim false, misleading, or overstrong.
2. If it is a cited claim, name exactly what source text must be checked, and
   check it. Do not clear a citation you have not read.
3. If it is empirical, name exactly what data or script output must be checked.
4. If it is a definition or stipulation, check whether the paper uses it
   consistently and non-circularly.
5. Record the severity of the attempted test in structured fields:
   `failure_mode`, `attack`, `evidence_checked`, `source_span`, and
   `could_have_failed`.
6. Give a verdict: `cleared`, `weakened`, `failed`, or `deferred`. If you did
   not have the evidence needed to test the claim, return `deferred`.

Return a single Markdown file beginning with a YAML frontmatter block, which
`claim-dag validate` machine-checks:

```markdown
---
claim_id: C000
verdict: cleared        # cleared | weakened | failed | deferred
model: <exact model id you are>
family: <anthropic | openai | google | zhipu | qwen | ...>
tier: <local | cheap | strong | max>
framing: refute         # must stay "refute" for a cleared verdict to count
failure_mode: "<the specific way this claim could be false, misleading, or overstrong>"
could_have_failed: "<the observation that would have flipped this to failed>"
attack: "<the way you tried to break it>"
evidence_checked: "<what source text, data, or consistency check you actually inspected>"
source_span: "<the passage, source location, or data output that grounds this audit>"
date: YYYY-MM-DD
---
# Node Audit: C000 (<model>)

## Test

## Attack

## Evidence Checked

## Source Span

## Verdict

## Required Revision
```

`cleared` means an attack was attempted and failed. It never means the passage
read plausibly.
