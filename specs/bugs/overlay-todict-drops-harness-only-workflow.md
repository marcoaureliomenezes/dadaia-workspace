---
name: overlay-todict-drops-harness-only-workflow
status: Closed
severity: MEDIUM
reported: 2026-06-27
resolved: 2026-06-27
resolved_in: v0.1.30
surface: infrastructure/json_workflow_model_policy_store.py WorkflowModelPolicyOverlay.to_dict
session_id: null
---

**Resolution (v0.1.30, Wave C T-30-C-05):** `to_dict()` now serializes the UNION of all
three context maps (`contexts | default_harness_overlay | step_harness_overlay`) plus
declared `extends` parents — mirroring the union the WMP doctor and panel `_semantic_check`
already use — so a save/load round-trip is identity for harness-only overlays and
extends-only contexts. Regression test:
`tests/unit/infrastructure/test_json_workflow_model_policy_store.py::test_save_then_load_round_trips_harness_only_workflow`.
The fix is in C-03's declared write set (`json_workflow_model_policy_store.py`).

**Symptom:** `WorkflowModelPolicyOverlay.to_dict()` silently drops a per-workflow default
harness or per-step harness override when that workflow has **no** entry in the
profile-override `contexts` map. `to_dict` iterates only `self.contexts.items()`, so a
harness-only workflow (a workflow named only in `default_harness_overlay` /
`step_harness_overlay`) is never emitted. After `save()` → `load()` the harness override is
gone — a save/load round-trip is **not** identity for harness-only overlays.

**Repro:**
```python
from dadaia_workspace.infrastructure.json_workflow_model_policy_store import (
    JsonWorkflowModelPolicyStore, WorkflowModelPolicyOverlay,
)
overlay = WorkflowModelPolicyOverlay(
    policy_id="default",
    contexts={},
    default_harness_overlay={"default": {"implementation": "pi"}},
)
store = JsonWorkflowModelPolicyStore(workspace_root)
store.save(overlay)
loaded = store.load()
assert loaded.workflow_default_harness("default", "implementation") == "pi"  # FAILS: None
```

**Expected:** `to_dict()` must serialize every workflow that appears in ANY of the three
context maps (`contexts | default_harness_overlay | step_harness_overlay`), mirroring the
union the WMP doctor (`_resolve_overlay`) and the panel `_semantic_check` already use, so a
save/load round-trip is identity for harness-only overlays too.

**Notes:** Pre-existing in v0.1.29 (the harness-overlay maps were added then; `to_dict`
was not updated to union them). Discovered during v0.1.30 Wave C (T-30-C-05) while testing
panel/doctor agreement. Out of Wave C's declared write set, so registered rather than fixed
inline. Low blast radius today: the panel PUT path persists overlays the operator edits in
the UI, which normally carry a profile `steps` entry; a pure harness-only override is the
trigger. No secret/PII involved.
