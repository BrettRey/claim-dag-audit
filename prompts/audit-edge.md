# Edge Audit Prompt

You are auditing one inference edge from a paper's claim DAG. **Your job is to
break it, not to confirm it.** Assume a hostile reviewer who wants the edge to
fail. If you cannot rule out the wedge you find, the verdict is `failed` or
`weakened`, never `cleared`. Default to broken under uncertainty.

Edge:

```yaml
[paste edge record]
```

Source claims:

```yaml
[paste source claim records]
```

Target claim:

```yaml
[paste target claim record]
```

Your task:

1. Grant the source claims as true.
2. Try to reach the target *without* the suppressed premise. If you can't, name
   the premise the inference actually needs.
3. Check whether that premise appears anywhere in the paper. If it does not, the
   edge cannot be `cleared`.
4. Drive the strongest hostile-reviewer wedge you can find.
5. State, in one line, the observation that would have *flipped your verdict* had
   it been present. This is `could_have_failed`. An audit with no such line is a
   rubber stamp and does not count toward clearance.
6. Give a verdict: `cleared` (only if a serious attack failed), `weakened`,
   `failed`, or `deferred`.

Return a single Markdown file beginning with a YAML frontmatter block. The
frontmatter is machine-checked by `claim-dag validate`; fill every field.

```markdown
---
edge_id: E000
verdict: cleared        # cleared | weakened | failed | deferred
model: <exact model id you are>
family: <anthropic | openai | google | zhipu | qwen | ...>
tier: <local | cheap | strong | max>
framing: refute         # must stay "refute" for a cleared verdict to count
suppressed_premise: "<the premise the inference actually needs>"
could_have_failed: "<the observation that would have flipped this to failed>"
attack: "<the wedge you drove>"
date: YYYY-MM-DD
---
# Edge Audit: E000 (<model>)

## Inference Tested

## Suppressed Premise

## Is The Premise Stated?

## Hostile Wedge

## Verdict

## Required Revision
```

`cleared` means a serious attempt to break the inference failed. It never means
the passage read plausibly.
