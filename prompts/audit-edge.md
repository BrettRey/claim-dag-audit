# Edge Audit Prompt

You are auditing one inference edge from a paper's claim DAG.

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

1. Assume the source claims are true.
2. Ask whether they actually support the target claim.
3. State the suppressed premise required to make the inference valid.
4. Check whether that premise appears anywhere in the paper.
5. Identify the strongest hostile-reviewer wedge.
6. Give a verdict: cleared, weakened, failed, or deferred.

Use this format:

```markdown
# Edge Audit: E000

## Inference Tested

## Suppressed Premise

## Is The Premise Stated?

## Hostile Wedge

## Verdict

## Required Revision
```

`cleared` means the inference survived a serious attempt to break it.

