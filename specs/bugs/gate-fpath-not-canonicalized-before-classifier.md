---
name: gate-fpath-not-canonicalized-before-classifier
status: Open
severity: MEDIUM
reported: 2026-06-09
surface: sdd-spec-gate.sh (FPATH classification)
session_id: null
---

**Symptom:** `sdd-spec-gate.sh` makes `FPATH` absolute (`[[ "$FPATH" != /* ]] && FPATH="$WS/$FPATH"`)
but does NOT canonicalize it (no `realpath`) before the bash `case` CLASS classifier
(`*/specs/memory/*`, `*/.dadaia/sessions/*`, `*/specs/_archive/*`, `*/specs/releases/*`). A
symlink from an UNGATED location into a gated subtree (e.g. a symlink whose real target is
`specs/memory/`) could be classified UNGATED instead of MEMORY/FROZEN/PROTECTED.

**Status:** Pre-existing (predates rc-4; flagged in the rc-3 and rc-4 ship-trio reviews by both
code-reviewer and security-reviewer). **No current bypass exists** — the slug resolver already
`os.path.realpath`s for context derivation, the PROTECTED glob matches the literal
`/.dadaia/sessions/` segment even on traversal variants, and the slug is `[^A-Za-z0-9_-]`-stripped
(CWE-22). Rated MEDIUM hardening, non-blocking; deliberately NOT changed in rc-4 to avoid a
late global FPATH change with regression risk.

**Repro (theoretical):** create a symlink `repos/x/link -> ../../specs/memory`; an agent Write to
`repos/x/link/atom.md` would `case`-classify on the un-canonicalized path.

**Expected:** Canonicalize `FPATH` (e.g. `os.path.realpath`, canonicalize-missing) immediately
after making it absolute, BEFORE the `case` classifier, so symlink/traversal paths classify by
their real location.

**Notes:** Both reviewers gave the same fix direction. Care: normalize consistently with `$WS`
(realpath both) so the `repos/$CONTEXT_SLUG/` reclassification and lease still match; verify the
gate integration suite stays green (some sandboxes symlink /tmp).
