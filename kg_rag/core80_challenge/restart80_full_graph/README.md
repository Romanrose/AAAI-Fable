# Restart80 full-graph experiment

This protocol uses every node and edge in each selected `mechanism_graph`.
It does not reuse Mapping Plans built from effective subgraphs.

Execution order:

```bash
python3 -m kg_rag.core80_challenge.restart80_full_graph prepare
python3 -m kg_rag.core80_challenge.restart80_full_graph run-mapping --canary --workers 1
python3 -m kg_rag.core80_challenge.restart80_full_graph run-mapping --workers 4
python3 -m kg_rag.core80_challenge.restart80_full_graph aggregate-mapping
python3 -m kg_rag.core80_challenge.restart80_full_graph.story prepare
python3 -m kg_rag.core80_challenge.restart80_full_graph.story run --canary --workers 1
python3 -m kg_rag.core80_challenge.restart80_full_graph.story run --workers 4
```

The 80 Mapping Plans are frozen before the 480 story tasks are built. A failed
mapping remains an upstream failure in both mapping-conditioned story slots.

## Shared experiment boundary

New evaluation variants must use [`kg_rag/shared/<experiment-id>/`](../../shared/README.md), not this frozen restart directory. See the [shared experiment policy](../../SHARED_EXPERIMENTS.md).
