---
name: root-whitelist-misses-nested-new-toplevel-writes
status: Open
severity: MEDIUM
reported: 2026-06-26
surface: hooks.root_whitelist (PreToolUse root-whitelist policy)
session_id: null
---

**Symptom:** The root-whitelist policy under-enforces its stated contract. AGENTS.md /
the policy docstring say it "blocks file-tool writes that would create a new top-level
root entry not in the whitelist." In practice `_root_violation` only blocks a write whose
**immediate parent resolves to exactly the workspace root**. A write to a path *nested*
under a new forbidden top-level dir is ALLOWED, even though it creates that top-level dir.

Verified (v0.1.24, WORKSPACE_ROOT=/home/[REDACTED]/workspace/dadaia):
- `Write /home/[REDACTED]/workspace/dadaia/.opencode`            → BLOCK ✓ (direct, parent == root)
- `Write /home/[REDACTED]/workspace/dadaia/.opencode/agents/foo.md` → ALLOW ✗ (parent == `.opencode`, not root) — but this write DOES create the forbidden top-level `.opencode/`.
- Same for any `<root>/<forbidden-dir>/<subpath>`.

**Repro:**
```
cd repos/dadaia-workspace
WORKSPACE_ROOT=/home/[REDACTED]/workspace/dadaia .dadaia/.venv/bin/python - <<'PY'
from dadaia_workspace.hooks import root_whitelist as rw
print(rw.evaluate_payload({"tool_name":"Write","tool_input":{"file_path":"/home/[REDACTED]/workspace/dadaia/.opencode/agents/foo.md","content":"x"}}))  # -> None (ALLOW)
PY
```

**Expected:** A file-tool write whose path's FIRST component below the workspace root is a
non-whitelisted new entry should block — regardless of how deep the file sits. The gate
should compute the top-level component of the target relative to the workspace root and
check THAT against the whitelist, not only the immediate parent.

**Impact:** A harness (or buggy tool) that writes `<root>/.opencode/...`, `<root>/build/...`,
etc. silently creates a forbidden top-level entry; the deterministic backstop misses it.
Real-world exposure for v0.1.24 is low because `dadaia public install` no longer projects
`.opencode/` (removed from valid targets), so nothing *intends* to create it — but the
gate is supposed to be the safety net and currently is not for nested writes.

**Notes:** Pre-existing behavior (not introduced by v0.1.24); discovered during the
v0.1.24 operator live-validation of the `.opencode/` block. `_root_violation` is in
`dadaia_workspace/hooks/root_whitelist.py` (the `is_at_root = fpath.parent.resolve() ==
workspace.resolve()` check at ~line 113). Fix is local to that function. Also fixed in
this session (separate, not a code bug): the stale `opencode.json` entry in
`.dadaia/states/root_exceptions.txt` was removed (left over from before OpenCode removal).
