# STATUS

**Created:** 2026-07-05
**State:** Initial standalone scaffold with working CLI.

## Current State

The tool can:

- initialize a per-paper audit directory;
- validate `claims.yaml` and `edges.yaml`;
- detect unknown edge endpoints, duplicate IDs, unsupported inference nodes,
  decorative premises, and cycles;
- generate `graph.argdown`;
- generate `report.md`.

## First Pilot

Use `papers/preprints/kinds-as-projectibility-profiles/` as the first pilot.
The first audit should focus on the central spine:

1. projectibility-profile thesis;
2. support-grade ladder;
3. demotion rules;
4. decorative-mechanism test;
5. Goodman and Ereshefsky/Reydon pressure points.

## Next Actions

- Run claim extraction on `Kinds as Projectibility Profiles`.
- Fill `claims.yaml` with a numbered claim inventory.
- Fill `edges.yaml` with support dependencies.
- Run the first edge audit on the three weakest inferences.
- Decide whether to add LLM dispatch wrappers after the manual pilot.

