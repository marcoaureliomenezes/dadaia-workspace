# SPEC: v0.1.5 rc-2 — propagation-pair + semaphore-liveness + panel-verify

**Status:** Aprovado
**Release ID:** v0.1.5
**Segment:** rc-2
**Owner:** product-engineer
**Created:** 2026-06-06
**Grill report:** `.dadaia/reports/dadaia-workspace/product-engineer/2026-06-06T013411Z-refine-specs.html` (all 4 problems resolved; mandatory grill gate satisfied)

---

## 1. Objective

Close three outstanding issues filed in `specs/bugs/` and one backlog item
(`BUG-PANEL-REPORTS-01`) that could not ship with rc-1, extending v0.1.5 under the same
tag. rc-2 covers:

1. **G2 — Propagation pair** (install-skips-existing-files + doctor-blind-to-projected-drift): fix `dadaia public install` to propagate content-hash-driven overwrites without `--force`, fix `dadaia public doctor` to detect staging-vs-projected drift with a non-zero exit, and update the `dadaia-workspace-dev-guardrail` rule to reflect the corrected behavior. HIGH.
2. **G3 — Semaphore liveness reclaim** (semaphore-no-liveness-reclaim): make `_is_stale` reclaim a semaphore whose owner process is dead or whose session file is absent (not just TTL), and extend `dadaia doctor` with a `SEM-1` semaphore invariant + `--fix`. Medium.
3. **G1 — Panel reports verify + invariant** (BUG-PANEL-REPORTS-01): verify the existing fix (commit `028ffd5`) closes RC#1-4 and the 224→2 regression; mark the bug resolved; add a `dadaia reports doctor` invariant for canonical sidecar placement and no dangling `artifact.path`; add de-dup polish only if qa finds a residual gap. HIGH.

All three groups are independently testable. A single v0.1.5 publish covers rc-1 + rc-2 (PR #38 absorbs rc-2 commits); rc-1 remains closed and superseded by rc-2 for CLOSURE purposes.

## 2. Context and background

rc-1 (CLOSED 2026-06-05) shipped the deploy-blocker fix (R1 session semaphore, env-free
binding) plus D5/R3/R4/D4. During rc-1 implementation three further bugs were observed and
filed in `specs/bugs/`:

- `specs/bugs/install-skips-existing-files.md` — install silently skips existing projected files; only `--force` overwrites.
- `specs/bugs/doctor-blind-to-projected-drift.md` — doctor compares source vs staging only; reports `[ok]` and exits 0 even when the projection is stale.
- `specs/bugs/semaphore-no-liveness-reclaim.md` — the new per-context semaphore has no PID/session-liveness check; TTL is the only reclaim path.

`BUG-PANEL-REPORTS-01` was reported 2026-06-04 (panel reports tab regression, 224→2
collapse). Commit `028ffd5` ("fix(panel): index reports from artifacts and handoffs") was
merged on `feature/0.1.5` after rc-1 CLOSURE, largely resolving the symptoms. rc-2 verifies
the fix is complete, closes the bug formally, and adds a structural invariant.

Operator decision 2026-06-06 (grill session): all four issues ship together as rc-2; one
v0.1.5 tag covers rc-1 + rc-2; deploy remains operator-gated.

## 3. Scope (in this segment)

### G2 — Propagation pair (HIGH)

**Bugs fixed:** `install-skips-existing-files` + `doctor-blind-to-projected-drift`

**T-PROP-01 — install hash-compare overwrite (software-engineer-python)**

`dadaia public install` must overwrite an existing projected file when the staged content
hash (`_src_sha`, computed at `public_assets.py` ~line 670) differs from the projected
file's content hash. Idempotent: if the hashes match, skip as before. `--force` retains its
existing semantics (clobber locally-divergent files regardless of hash comparison). The
"both hashes match" path becomes the only no-op path; the "staged ≠ projected" path is a
plain overwrite (no `--force` required).

Relevant source: `dadaia_workspace/features/public_assets/public_assets.py` lines 670, 676,
684 (the `_src_sha` computation + skip-if-exists logic).

Tests (minimum): update-propagates-without-force, no-op-when-hashes-match,
force-still-clobbers-locally-modified.

**T-PROP-02 — doctor staging-vs-projected check (software-engineer-python)**

`dadaia public doctor` must compare every staged asset's SHA256 against the corresponding
projected file for each target runtime. If any mismatch is found, emit `[drift] <path>` and
return a non-zero exit code. Today the delegate chain is:
`PublicAssetService.doctor` → manager (compares source vs staging only).

Extend the delegate chain to add a third pass: for each staged file, compute the projected
path under each runtime target (`.dadaia/scripts/`, `.claude/`, `.codex/`, `.opencode/`,
etc.) and compare hashes. Emit `[ok]` only when all three match (source↔staging +
staging↔projected). Non-zero exit on any `[drift]`.

Tests (minimum): clean-tree-exits-0, projected-drift-exits-nonzero,
staged-but-not-installed-exits-nonzero.

**T-PROP-03 — update dadaia-workspace-dev-guardrail rule (ai-engineer)**

The "Correct edit workflow" in `dadaia_workspace/public/rules/dadaia-workspace-dev-guardrail.md`
currently states `dadaia public install --target all` for step 3 and implies `--force` is
required for updates. Update the rule to reflect the fixed behavior: plain `install` now
propagates updates (hash-compare overwrite); `--force` is reserved for locally-divergent
projection repair. Resolve bug entries `install-skips-existing-files` and
`doctor-blind-to-projected-drift` (add `resolved_in: v0.1.5/rc-2` frontmatter).

This task is AI-entity authorship only (rule Markdown); no Python changes.

### G3 — Semaphore liveness reclaim (Medium)

**Bug fixed:** `semaphore-no-liveness-reclaim`

**T-SEMA-01 — _is_stale liveness check + acquire reclaim (software-engineer-python)**

Extend `semaphore.py:_is_stale` to return `True` (stale/reclaimable) when EITHER:
- current time − heartbeat > TTL (existing behavior, preserved), OR
- the owner's PID is not alive in the OS process table (resolve: semaphore `owner` field
  contains `session_id`; resolve `session_id → session file → pid`; check `os.kill(pid, 0)`
  without raising), OR
- the owner session file does not exist.

`acquire_context_semaphore` must silently reclaim a stale-by-liveness semaphore (log audit
trail, then overwrite) so the caller acquires without waiting the full TTL.

Tests (minimum): dead-pid-reclaims-immediately, missing-session-reclaims-immediately,
live-holder-still-blocks, ttl-still-reclaims-after-expiry.

**T-SEMA-02 — doctor SEM invariant + --fix (software-engineer-python)**

`spec_context/doctor.py` must grow a new invariant `SEM-1`:

- **SEM-1**: any `ctx_locks/*.semaphore.json` that is orphaned (no matching alive context)
  or stale-by-liveness (as defined in T-SEMA-01) is flagged with `[stale-semaphore]`.
  `dadaia doctor --fix` reclaims it (delete file + log audit entry).

Tests (minimum): clean-state-no-warning, orphan-semaphore-flagged,
stale-semaphore-flagged, fix-reclaims-and-logs.

### G1 — Panel reports verify + invariant (HIGH)

**Bug addressed:** `BUG-PANEL-REPORTS-01`

**T-PANEL-01 — qa verify of commit 028ffd5 (qa-engineer)**

qa-engineer reproduces the four original symptoms (RC#1-4) and the 224→2 regression
against current `feature/0.1.5` code. Ground truth of what 028ffd5 delivered (from grill
inspection, `api.py:910-944`):

- RC#1 (sidecar-less reports invisible): fixed — `_view` rglobs `*.html` directly.
- RC#2 (self-referential `artifact.path`): fixed — only enriches when `artifact_path` starts with `.dadaia/reports/` and is a real `.html`.
- RC#3 (224→2 regression): fixed — reads both `.dadaia/handoff` and `.dadaia/reports` (api.py:893).
- RC#4 (no de-duplication): fixed — `results_by_path.setdefault` de-dups.

If all RC#1-4 and the regression are confirmed fixed: mark `BUG-PANEL-REPORTS-01` resolved
in `specs/backlog/candidates.md` (add `resolved_in: v0.1.5/rc-2` annotation) and emit
handoff with `verdict: APPROVED`. If any residual gap is found: document it in the handoff
and T-PANEL-02 must address the gap before qa re-verifies.

**T-PANEL-02 — dadaia reports doctor invariant + dedup polish (software-engineer-python)**

Regardless of T-PANEL-01 outcome, add the following invariant to `dadaia reports doctor`
(or extend `dadaia specs doctor` if the reports-doctor surface does not yet exist):

- **RPT-1**: every HTML report under `.dadaia/reports/` has at most one canonical sidecar
  (`.handoff.json`) at the path `.dadaia/handoff/<context>/<UTC>-<agent>-<slug>.handoff.json`;
  any sidecar whose `artifact.path` points at a non-HTML file or at the sidecar itself is
  flagged as `[dangling-artifact-path]`.

If T-PANEL-01 finds a real de-dup gap, T-PANEL-02 also addresses it. If qa finds zero
residual gaps, T-PANEL-02 is scoped to the RPT-1 invariant + unit tests only.

Unit tests (minimum): invariant-clean-passes, dangling-artifact-path-flagged,
missing-html-sidecar-not-flagged (a sidecar-less HTML is valid).

### SHIP gate

**T-SHIP-01 — Pre-ship CI gate (software-engineer-python or devops-engineer)**

Run locally on `feature/0.1.5` before any review dispatch:
- `ruff format --check dadaia_workspace/`
- `ruff check dadaia_workspace/`
- `mypy --strict dadaia_workspace`
- `pytest -p no:cacheprovider`

All must pass. Block push on any failure (mirrors rc-1 pre-push gate).

**T-SHIP-02 — QA review (qa-engineer)**
**T-SHIP-03 — Code review (code-reviewer)**
**T-SHIP-04 — Security review (security-reviewer)**

All three must emit `verdict: APPROVED` handoffs. Any REJECTED verdict blocks the ship
gate and requires the relevant task to reopen for rework.

**T-SHIP-05 — CLOSURE + deploy gate (product-engineer)**

Write `specs/releases/v0.1.5/rc-2/CLOSURE.md`. Deploy (push, PR, merge, git tag v0.1.5,
PyPI publish) remains operator-gated and is NOT triggered by CLOSURE alone.

## 4. Out of scope for rc-2

- Any new features not described above.
- R4b (generic-agent trims) — deferred; R4 audit is closed in rc-1.
- Memory atom updates — CLOSURE phase only.
- `ai-harness-opencode` skill — deferred from v0.1.4.6.
- Changes to session model or gate scripts beyond what G3 requires.
- Any `dadaia public` asset chain changes beyond T-PROP-01/02/03 and T-PANEL-02's doctor invariant.

## 5. Acceptance (segment-level)

- **G2 (install):** `dadaia public install --target all` overwrites a projected file when staged hash ≠ projected hash; is a no-op when hashes match; `--force` still clobbers locally-modified files. Tests green.
- **G2 (doctor):** `dadaia public doctor` exits non-zero on any staging-vs-projected mismatch and emits `[drift]`; exits 0 on a clean workspace. Tests green.
- **G2 (guardrail):** `dadaia-workspace-dev-guardrail` rule correctly describes the new install/doctor behavior; both bugs marked resolved.
- **G3 (liveness):** A bind behind a dead-PID semaphore acquires immediately (no TTL wait). `dadaia doctor --fix` reclaims orphan/stale semaphores. Tests green.
- **G1 (verify):** qa-engineer confirms RC#1-4 and the 224→2 regression are resolved; `BUG-PANEL-REPORTS-01` marked resolved.
- **G1 (invariant):** `dadaia reports doctor` (or equivalent) detects dangling `artifact.path` values. Tests green.
- **CI gate:** ruff format+check, mypy --strict, pytest all pass locally before push.
- **Ship trio:** qa-engineer + code-reviewer + security-reviewer all `APPROVED`.

## 6. Decisions from grill session (ADRs)

| ADR | Decision | Source |
|---|---|---|
| rc2-segment | Extend v0.1.5 as rc-2; one v0.1.5 publish covers rc-1+rc-2; rc-1 superseded by rc-2 CLOSURE | Operator (2026-06-06 grill) |
| d-panel-verify | Verify 028ffd5 via qa-engineer before authoring any new panel code; add only the RPT-1 invariant | Operator |
| d-prop | hash-compare overwrite on install (no --force for updates); doctor gains staging↔projected check | Operator |
| d-sema | PID liveness + session-file check in _is_stale; doctor SEM-1 invariant + --fix reclaim | Operator (default accepted) |
| impl-order | G2 → G3 → G1 → SHIP (doctor.py touched by all three groups; sequence to avoid churn) | Product-engineer |
