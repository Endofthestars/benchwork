# Phase 2 final acceptance scenario

This example freezes the M17 golden path without invoking a background model.
The interactive Host is simulated at the typed MCP boundary; Athanor and
Chronicle remain real.

The scenario starts with an intentionally under-specified draft Protocol.
Codex opens `bench.study.audit`, reads the registered scientific objects with
native/typed read tools, and completes the Task with a structured `REPAIR`
recommendation. Athanor accepts the Agent Result and returns a Receipt.

The Host then drafts a replacement Protocol with a registered analysis
specification. The Protocol and final Decision each use preview, explicit human
confirmation, and commit. The cycle registers implementation, Pilot and Formal
Runs, including one failed Run and one excluded outcome. Alembic computes the
Result Bundle. The Assessment and unresolved critical Issue lead to a sealed
`REPAIR` Decision.

Run the deterministic acceptance:

```bash
python3 -m unittest \
  tests.mcp.test_runtime.MCPRuntimeTest.test_complete_repair_cycle_uses_only_control_plane_tools
```

The test proves:

```text
Codex workflow -> MCP -> Athanor -> Receipt -> Chronicle replay
```

`scenario.json` is the machine-readable checklist. IDE and external Review
exceptions remain independently recorded and do not weaken this path.
