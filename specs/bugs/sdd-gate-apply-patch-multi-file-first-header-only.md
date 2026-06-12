---
name: sdd-gate-apply-patch-multi-file-first-header-only
status: Open
severity: MEDIUM
reported: 2026-06-11
surface: dadaia_workspace/hooks/_common.py target_path() (SDD gate path classification on Codex)
session_id: null
---

**Symptom:** `hooks/_common.target_path()` extracts the write-target from a Codex
`apply_patch` payload by scanning the patch text for `*** Add/Update/Delete File:`
headers — but returns on the FIRST header found. A multi-file patch whose first file
is an allowed path and whose second file is FROZEN (`specs/_archive/`) or PROTECTED
(`.dadaia/sessions/`) is classified solely by the first file, so the gate allows the
whole patch and the protected write goes through.

**Repro:** Feed the gate a PreToolUse payload with
`tool_input.command = "*** Begin Patch\n*** Update File: README.md\n...\n*** Update
File: specs/_archive/x.md\n...\n*** End Patch"` — `target_path()` returns `README.md`;
the FROZEN branch never evaluates. (Live Codex payload shape confirmed 2026-06-11:
apply_patch arrives as `tool_input.command` patch text with no `file_path` key.)

**Expected:** Every file header in an `apply_patch` patch is classified; the most
restrictive verdict wins (one FROZEN/PROTECTED/blocked-MUTATING file blocks the whole
patch).

**Notes:** Found during T-013-08 live Codex contract verification (v0.1.13 alpha-2);
evidence and real payload sample in the WS-CDX-VERIFY FACTS file. Affects the Codex
runtime only (Claude file tools carry `file_path` directly).
