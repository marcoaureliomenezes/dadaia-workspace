---
name: handoff-artifact-path-cannot-reference-specs-audits
status: Closed
closed: 2026-06-11
fixed_by: v0.1.11
severity: MEDIUM
session_id: null
reported: 2026-06-10
surface: reports_validation (handoff-v1.1 schema + artifact path resolver)
---

**Symptom:** A handoff JSON whose `artifact.path` points at the canonical auditor channel (`repos/<slug>/specs/audits/<UTC>/audit.md`) can never validate. Three constraints make the location unrepresentable:
1. The schema pattern rejects absolute paths (leading `/`) and `..` segments.
2. The resolver (`reports_validation/service.py:_resolve_artifact_path`) workspace-roots only paths prefixed `.dadaia/`; any other relative path resolves from the **handoff file's own directory** (legacy behavior), so `repos/...` becomes `.dadaia/handoff/<ctx>/repos/...` → `missing_artifact`.
3. Therefore no spellable path reaches `repos/<slug>/specs/audits/` from `.dadaia/handoff/<ctx>/`.

**Repro:**
1. Write an audit report to `repos/<slug>/specs/audits/<UTC>/audit.md` (the canonical committed auditor channel per the lifecycle model).
2. Emit a handoff under `.dadaia/handoff/<slug>/` with `artifact.path: repos/<slug>/specs/audits/<UTC>/audit.md` and correct sha256.
3. `dadaia reports validate <handoff>` → `artifact.content_hash: artifact hash check failed: missing_artifact`.
4. Retry with an absolute path → schema pattern rejection. Retry with `../../..` → pattern rejection.

**Expected:** The lifecycle contract designates `specs/audits/<ts>/` (committed) as the auditor's report channel, and handoff-v1.1 requires `artifact` with `content_hash` verification. These two contracts must compose: workspace-relative resolution should cover `repos/...` (or any workspace-rooted path), not only `.dadaia/...`.

**Notes:** Workaround used: duplicate the audit MD under `.dadaia/reports/<ctx>/<agent>/` and point `artifact.path` there — which forks the artifact into two copies and defeats `content_hash` as a single-source integrity check. Suggested fix: in `_resolve_artifact_path`, treat any relative path that exists under `workspace_root` as workspace-rooted (keeping the handoff-dir fallback for legacy), or extend the prefix allowlist to `repos/`. Environment: dadaia-workspace v0.1.10 line, self-hosting workspace. No operator-local paths in this record.

**Resolution (v0.1.11, 2026-06-11):** `_resolve_artifact_path` resolves ANY relative
`artifact.path` that exists under `workspace_root` as workspace-rooted (covers
`repos/<slug>/specs/audits/<UTC>/…`); legacy handoff-dir fallback kept; workspace-root
wins when both exist; absolute/`..` still schema-rejected (T-011-07, schema unchanged).
Named regression tests:
`tests/unit/features/reports_validation/test_resolve_artifact_path.py` —
`test_resolve_repos_specs_audits_artifact_validates`,
`test_resolve_legacy_handoff_dir_relative_still_validates`,
`test_workspace_root_wins_when_path_resolvable_both_ways`,
`test_absolute_path_outside_workspace_rejected`, `test_dotdot_escape_path_rejected`.
Verified at `feature/v0.1.11 @ e1f2de3`. Duplicate record
`handoff-artifact-path-resolver-ignores-workspace-root-contract` stays Closed,
superseded by this one.
