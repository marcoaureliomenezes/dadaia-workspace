---
name: handoff-artifact-path-resolver-ignores-workspace-root-contract
status: Rejected
rejected_reason: duplicate of handoff-artifact-path-cannot-reference-specs-audits (2026-06-10, same root cause and repro)
session_id: null
severity: MEDIUM
reported: 2026-06-11
surface: dadaia reports validate (features/reports_validation/service.py)
---

> **DUPLICATE** — see `handoff-artifact-path-cannot-reference-specs-audits.md` (reported 2026-06-10). Independent rediscovery on 2026-06-11 during the portifolio full audit confirms the repro; track the original.

**Symptom:** A handoff JSON whose `artifact.path` references a committed audit
artifact (`repos/<slug>/specs/audits/<ts>/<file>.md`, correct `content_hash`)
fails validation with `artifact.content_hash: artifact hash check failed:
missing_artifact`, even though the file exists at that path under the
workspace root.

**Repro:**
1. Write any file at `repos/<slug>/specs/audits/<ts>/report.md`.
2. Emit `.dadaia/handoff/<ctx>/<ts>-agent-x.handoff.json` with
   `artifact.path = "repos/<slug>/specs/audits/<ts>/report.md"` and its real
   sha256 as `content_hash`.
3. Run `dadaia reports validate <handoff>` → `INVALID … missing_artifact`.

**Expected:** The handoff schema documents `artifact.path` as "Relative path
from workspace root to the artifact file." A workspace-root-relative path to
an existing file with a matching hash must validate.

**Root cause:** `_resolve_artifact_path`
(`dadaia_workspace/features/reports_validation/service.py:166-173`) resolves
from the workspace root **only** when the ref starts with `.dadaia/`. All
other relative refs take the legacy branch and resolve from the handoff
file's parent dir (`.dadaia/handoff/<ctx>/repos/...` → nonexistent). The
schema's path pattern forbids absolute paths and `..` segments, so there is
**no expressible path** that lets a handoff reference a `repos/<slug>/specs/audits/`
artifact and validate — yet the canonical lifecycle model designates committed
`specs/audits/<ts>/` markdown as a first-class report channel.

**Notes:** Workaround used: emit the v1.1 handoff-first form without
`artifact.path`/`content_hash` and carry the artifact location in `scope`
prose. Fix direction: resolve any non-`.dadaia/` relative ref from the
workspace root first and fall back to handoff-dir resolution only if the
root-relative candidate does not exist (preserving legacy behavior).
