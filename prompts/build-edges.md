# Build Edges Prompt

You are given `claims.yaml` for a paper. Build the dependency DAG.

For each support relation, produce:

- `id`: E001, E002, ...
- `from`: one or more source claim IDs
- `to`: the claim supported by those sources
- `relation`: supports, requires, rebuts, or qualifies
- `suppressed_premise`: the unstated assumption that would make this edge valid
- `status`: needs-audit
- `notes`: one sentence explaining the edge

Rules:

- Edges run from supporting claims to supported claims.
- If a conclusion depends on a suppressed premise, name it explicitly.
- If a claim only decorates the prose and supports nothing, leave it with no outgoing edge.
- If an inference has no support, do not invent support. Let validation flag it.
- Keep the graph acyclic unless the paper really argues in a circle; if it does, mark the cycle.

Return YAML only.

