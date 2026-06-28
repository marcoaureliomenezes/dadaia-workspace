---
name: release-definition-artifact-paths-accept-traversal-release-id
status: Closed
severity: HIGH
reported: 2026-06-28
surface: lifecycle release define / canonical artifact gate / fake runtime
session_id: sess_6a2bcfe7
---

**Symptom:** Security review rejected `v0.1.35` because release-definition canonical
artifact paths were derived from `release_id` without validating path separators or
re-confining the resolved path.

**Repro:** Review the path construction for release-definition create-step artifacts and
fake-runtime writes. A release id containing traversal segments could be incorporated into
`specs/releases/<release-id>/<artifact>` and then exposed as an allowed path.

**Expected:** Release IDs and active segment names used as path components are validated
as single safe components before any artifact path is exposed to worker scope or written
by the fake runtime.

**Root cause:** `_expected_release_artifact_path()` concatenated `self._release_id` into
a filesystem path directly. The new fake runtime writes the request allowed path, so the
path generation must be safe by construction.

**Notes:** Reported by Codex security-reviewer handoff
`.dadaia/handoff/dadaia-workspace/2026-06-28T041254Z-security-reviewer-v0135-security.handoff.json`.

## Resolution

Fixed in `v0.1.35`.

Fix: release-definition now validates `release_id` and active `segment` as single
path-safe components before constructing canonical artifact paths. The final artifact
path is resolved and required to remain under the resolved release directory before it is
returned to prompt scope or fake-runtime writes.

Evidence:

- `tests/integration/cli/test_release_definition_workflow.py::test_release_definition_rejects_traversal_release_id`
