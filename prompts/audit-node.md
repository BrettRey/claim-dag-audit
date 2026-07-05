# Node Audit Prompt

You are auditing one claim from a paper.

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
2. If it is a cited claim, specify exactly what source text must be checked.
3. If it is empirical, specify exactly what data or script output must be checked.
4. If it is a definition or stipulation, check whether the paper uses it consistently.
5. Give a verdict: cleared, weakened, failed, or deferred.

Use this format:

```markdown
# Node Audit: C000

## Test

## Attack

## Evidence Checked

## Verdict

## Required Revision
```

`cleared` means an attack was attempted and failed.

