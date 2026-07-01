---
name: stale-legacy-software-engineer-lint-inverts-roster
status: Closed
severity: LOW
reported: 2026-06-11
resolved_in: v0.1.13
surface: codex_doctor.lint_legacy_software_engineer (T-35 lint)
session_id: null
---

**Symptom:** The dormant T-35 lint flags `subagent_type: software-engineer` in public
assets and instructs authors to use `software-engineer-python|node` — agent names that
were DELETED in the 15→9 roster consolidation. `software-engineer` is now the single
canonical implementer, so the lint inverts the current roster: the first public asset
that legitimately references `subagent_type: software-engineer` gets a deterministic
wrong doctor error whose remedy names dead agents.

**Repro:** Add `subagent_type: software-engineer` to any file under
`dadaia_workspace/public/`; run `dadaia public doctor` — the lint fires with a
dead-name remedy.

**Expected:** Doctor lints reflect the current 9-agent roster (constitution §14).
The lint should be deleted (or inverted to flag the dead `-python|-node` names).

**Notes:** Found by the Codex runtime fidelity audit (F-10),
`specs/audits/2026-06-12T001813Z/codex-runtime-fidelity-review.md`. Currently dormant
(no matching literal in `public/`), but a deterministic misfire-in-waiting.

**Resolution (v0.1.13, T-013-11):** the stale T-35 lint no longer flags the canonical
`subagent_type: software-engineer`; it was removed/inverted per the current 9-agent
roster (constitution §14), with tests covering the canonical name passing. Evidence in
`specs/_archive/releases/v0.1.13/CLOSURE.md` (Dispositions).
