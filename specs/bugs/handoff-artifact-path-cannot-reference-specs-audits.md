---
name: handoff-artifact-path-cannot-reference-specs-audits
status: Open
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
