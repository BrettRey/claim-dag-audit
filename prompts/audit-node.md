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
5. State, in one line, the observation that would have *flipped your verdict*
   had it been present. This is `could_have_failed`; an audit without it is a
   rubber stamp and does not count toward clearance.
6. Give a verdict: `cleared`, `weakened`, `failed`, or `deferred`.

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
could_have_failed: "<the observation that would have flipped this to failed>"
attack: "<the way you tried to break it>"
date: YYYY-MM-DD
---
# Node Audit: C000 (<model>)

## Test

## Attack

## Evidence Checked

## Verdict

## Required Revision
```

`cleared` means an attack was attempted and failed. It never means the passage
read plausibly.
