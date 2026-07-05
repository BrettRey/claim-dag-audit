# Build Edges Prompt

You are given `claims.yaml` for a paper. Build the dependency DAG.

Claims:

```yaml
[paste claims.yaml]
```

Paper source:

```text
[paste paper source]
```

For each support relation, produce:

- `id`: E001, E002, ...
- `from`: one or more source claim IDs
- `to`: the claim supported by those sources
- `relation`: supports, requires, rebuts, or qualifies
- `suppressed_premise`: the unstated assumption that would make this edge valid
- `verdict`: unaudited
- `notes`: one sentence explaining the edge

Rules:

- Edges run from supporting claims to supported claims.
- If a conclusion depends on a suppressed premise, name it explicitly.
- If a claim only decorates the prose and supports nothing, leave it with no outgoing edge.
- If an inference has no support, do not invent support. Let validation flag it.
- Only `supports` and `requires` count as support; `rebuts` and `qualifies` do
  not license the target. A conjunctive premise set goes in one edge's `from`
  list (jointly support); genuinely independent routes to the same target are
  separate edges.
- Keep the graph acyclic. `claim-dag validate` treats a support cycle as an error.

Return a top-level YAML list (no code fences, no wrapper key), for example:

```yaml
- id: E001
  from: [C001, C002]
  to: C003
  relation: supports
  suppressed_premise: "..."
  verdict: unaudited
  notes: "..."
```
