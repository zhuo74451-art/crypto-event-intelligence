# Extension B: Run Lineage Graph

The `parent_child_graph.json` in every audit bundle provides the structured
lineage data needed to reconstruct the parent-child DAG.

## Structure

```json
{
  "parents": [
    {
      "parent_run_id": "a1b2c3d4...",
      "parent_status": "completed",
      "child_count": 3,
      "children": [
        {"run_id": "child1", "status": "completed", "ordinal": 1},
        {"run_id": "child2", "status": "degraded", "ordinal": 2},
        {"run_id": "child3", "status": "completed", "ordinal": 3}
      ]
    }
  ]
}
```

## DOT format (conceptual)

```
digraph run_lineage {
  "parent1" [label="parent1\ncompleted"];
  "parent1" -> "child1" [label="ordinal 1"];
  "parent1" -> "child2" [label="ordinal 2"];
  "parent1" -> "child3" [label="ordinal 3"];
}
```

The graph is exported as structured JSON only — no rendering service is started.
