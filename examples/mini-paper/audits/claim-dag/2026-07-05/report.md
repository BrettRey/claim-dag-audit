# Claim DAG Audit Report

## Summary

- Claims: 3
- Edges: 1
- Claim validation errors: 0
- Edge validation errors: 0
- Coherence errors: 0
- Unsupported inference nodes: 0
- Decorative premise nodes: 0
- Cycles: 0
- Audit-backing errors: 0

## Claim Types

- definition: 1
- inference: 1
- stipulation: 1

## Claim Verdicts

- cleared: 3

## Edge Relations

- supports: 1

## Edge Verdicts

- cleared: 1

## Claim Errors

- none

## Claim Warnings

- none

## Edge Errors

- none

## Edge Warnings

- none

## Coherence Errors

- none

## Audit-Backing Errors

- none

## Audit-Backing Warnings

- none

## Unsupported Inference Nodes

- none

## Decorative Premise Nodes

- none

## Cycles

- none

## Next Audit Moves

- Run `claim-dag plan` to emit the audit jobs still needed to clear.
- Audit every unsupported inference or rewrite the graph.
- Decide whether decorative premises should be connected, cut, or marked `background: true`.
- Route any failed/weakened target to revision before re-auditing.
