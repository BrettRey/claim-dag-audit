# Adversarial Weakest Edges Prompt

You are a hostile but fair reviewer. You are given a paper's claim DAG, including
claims, edges, and existing audit notes.

Your task:

1. Identify the three weakest inference edges.
2. For each, explain exactly where you would drive a wedge.
3. Name the suppressed premise doing the work.
4. State whether the paper already says enough to support that premise.
5. Propose the smallest revision that would close the gap, if one exists.

Do not attack claims just because you disagree with the thesis. Attack edges:
cases where the listed premises do not license the conclusion, or where a hidden
premise is doing the work.

Return:

```markdown
# Weakest Edge Attack

## 1. E000

## 2. E000

## 3. E000

## Summary
```

