# Review: Gregor Betz (Argdown, LLM argument reconstruction)

1. **One-sentence summary** of what the tool is and claims to do

`claim-dag-audit` is a file-first CLI that turns an academic paper into YAML claim and edge inventories, validates the resulting dependency graph, and emits Argdown plus Markdown reports for separate node, edge, and adversarial audits.

2. **Strengths**

- The central design distinction is correct: `CLAUDE.md:8-12` separates claim truth/source audits from edge audits, which is exactly where many reconstruction tools blur the issue.
- The edge record includes a `suppressed_premise` field (`README.md:76-81`, `schemas/edges.schema.yaml:20-21`), which is a strong protocol choice for making inferential work explicit rather than merely drawing arrows.
- The tool is appropriately file-first and pilot-oriented: plain YAML/Markdown artifacts (`README.md:6-20`) and no LLM dispatch automation before the first manual pilot (`CLAUDE.md:18-19`) are sensible constraints.

3. **Weaknesses**

- The generated Argdown is not correct Argdown for support relations and likely will not render as intended. `claim_dag/graph.py:115`, `templates/graph.argdown.j2:11`, and `examples/mini-paper/audits/claim-dag/2026-07-05/graph.argdown:14-15` emit `[C001] -> [C003]`, but Argdown relations are defined as indented child lines under a parent, and `->` is an attack/contrary-style relation, not support; support from source to target should be encoded with `+>` under the source or `<+` under the target. Also, `claim_dag/graph.py:103` and `graph.argdown:4,7,10` use `# definition; status=...` as if it were a comment, but Argdown comments are `//`, `/* ... */`, or HTML comments, while hashtags require `#tag` or `#(...)` syntax; verified against the official Argdown syntax docs: https://argdown.org/syntax/. Action: rewrite `to_argdown()` to emit statement references plus indented `+>`/`<+` relations, and use Argdown YAML data, real hashtags, or `//` comments for metadata.
- The graph model collapses statements, arguments, and inferences into one undifferentiated “claim” layer. `schemas/claims.schema.yaml:12-13` and `claim_dag/schema.py:7-13` have claim types but no distinction between statement nodes, argument nodes, reconstructed arguments, premises, conclusions, and intermediary conclusions. More seriously, `edges.yaml:2` represents `from: [C001, C002]` as one conjunctive premise set, but `to_argdown()` explodes it into two independent arrows at `claim_dag/graph.py:114-115`, which changes the reconstruction: “C001 and C002 jointly support C003” becomes “C001 independently supports C003” and “C002 independently supports C003.” Action: add explicit premise-set or argument-node semantics, e.g. one edge = one inference with conjunctive premises, distinct edges = independent support routes, and preserve that distinction in Argdown via an argument node or PCS.
- The LLM prompts are not yet precise enough to reliably produce validator-ready YAML. `prompts/extract-claims.md:5-12` lists fields but omits the required `status` field, only mentioning `uncleared` later at line 20; `prompts/build-edges.md:5` says “support relation” while line 10 allows `rebuts` and `qualifies`; neither extraction nor edge prompts explicitly says “return a top-level YAML list, no code fences, no wrapper key,” even though `schema.py:54-55` and `schema.py:92-93` require a bare list. Action: include a minimal schema-conformant YAML example in each prompt and state the exact top-level shape and enum values.

4. **Key question** you would ask at Q&A

Is an `edge` intended to represent a single inferential step with a conjunctive premise set, or merely a visual bundle of pairwise support arrows, and how will the protocol mark multiple independent routes to the same conclusion?

5. **Verdict**: Revise & Resubmit — not ready to run the Kinds pilot as designed, because the Argdown export misrepresents support and the current schema loses the premise-set/argument-node distinctions needed for serious reconstruction.