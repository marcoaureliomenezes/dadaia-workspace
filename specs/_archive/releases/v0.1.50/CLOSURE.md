# CLOSURE — v0.1.50 — Kernel Hardening

**Status:** Aprovado
**Branch:** `feature/v0.1.50` · **Base:** `918589e2` (v0.1.49 closure) · **Merged:** `7b198d49` (PR #89, 38 checks: 35 pass / 3 skipping, squash)
**Origin:** operator-approved release sequence R2 (grill 2026-07-02) disposing 1 open
bug + 2 backlog entries (which carried the 4 bugs deferred by the 2026-07-01 audit).

## Summary

The spec-context kernel is now identity-sound end to end: a harness that rotates its
session id no longer self-blocks (self-recognition rung with lineage evidence — pid
equality alone never renews), an I/O failure reading `ACTIVE.md` can no longer bypass
the pid veto (reader-seam tri-state), the doctor no longer accuses a confirmed live
holder of forgery on `.ptr` drift (same-CAS by-session index evidence), `context dead`
works on standard git repos (0444 loose objects, mismatched upstream, empty push), and
every specs-dir-taking CLI resolves the bound context through ONE shared
ancestry-threading seam — the omission class behind the resolved bug is structurally
impossible, and a workspace-root `specs/` fallback is refused (Root Law).

## Shipped (conventional commits on `feature/v0.1.50`)

- `77e6584f` docs(T-50-01) — definition (SPEC/PLAN/TASKS `Aprovado` after dual
  REJECT→amend→approve reviews: software-architect + qa-engineer; root cause of the
  consumed bug pinned at definition time).
- `0183019e` test(T-50-10) — RED: rotated-sid self-block + sentinel veto-bypass +
  sid-precedence regressions (TDD red commit, git-log-verifiable).
- `d5a5c8b8` fix(T-50-10) — FR1: lease self-recognition with lineage evidence +
  reader-seam veto decoupling (`_UNSET_RELEASE` sentinel) + sid precedence fixed once
  in `hooks/_common.resolve_session_id`.
- `f1b4ac26` fix(T-50-11) — FR2: SPEC-DOC-029 holder-confirmation + by-session index
  hygiene (RENEW-branch dangling-entry cleanup) + doctor `--specs-dir` state isolation.
- `c3ba739d` fix(T-50-12) — FR3: `context dead()` exit path — explicit refspec push
  `HEAD:<upstream-branch>`, empty-push skip, `rmtree(onexc=chmod-and-retry)`,
  pre-checks moved before the push phase.
- `185bf423` fix(T-50-13) — FR4: centralized CLI specs-dir resolution
  (`cli/_specs_resolution.resolve_specs_dir_for_cli`, all five wrappers) + root-law
  cwd guard with redaction-safe refusal.
- `df82caad` + `1c8dc70b` test — old-contract pins updated to the new kernel contract
  (the second surfaced by the QA ship-gate REJECT).
- `873b11d2` review(T-50-20) — QA ship-gate REJECT→fix→APPROVE record.

## Evidence triples (AC → command → observed)

- **AC-1 (no-steal preserved)** → `git diff --stat main..HEAD -- <9 frozen paths>` →
  **empty** (zero diffs); frozen suite green in the full run.
- **AC-2 (rotated-sid RENEW)** → `pytest tests/unit/features/spec_context/test_lease_self_recognition.py`
  → lineage-seeded RENEW passes; no-record, mismatched-pid-record, and foreign cases
  all still block.
- **AC-3 (veto integrity)** → `pytest tests/unit/core/test_lock_liveness_sentinel.py`
  → unreadable ACTIVE.md preserves the veto; readable-none and real-mismatch reclaim.
- **AC-4 (bound-session resolution)** → red test
  `test_bugs_append_resolves_bound_context_via_ancestry_chain` (verified the pinned
  cause) → green after the shared seam; workspace-root refusal regression-tested with
  no absolute path echoed.
- **AC-5 (full gates)** → unpiped `pytest` → **4,411 passed / 17 skipped, exit 0**;
  `ruff format --check` + `ruff check` + `mypy --strict` PASS (pre-push preflight);
  **PR #89: 38 checks green (35 pass / 3 skipping)**.

## Review ladder

- Definition: software-architect REJECT→APPROVE (BLOCKERs: sid seam =
  `hooks/_common.resolve_session_id`; holder-confirmation via index evidence, not
  namespace parsing; centralize the four-wrapper defect class) + qa-engineer
  REJECT→APPROVE (frozen 9-path no-steal suite; red-commit TDD ordering; pid-reuse
  edge). All amendments landed before `Aprovado`.
- Implementation ADRs (recorded in SPEC FR1): lineage-evidence conjunct on the
  self-recognition rung (pid equality alone breaks the frozen foreign-holder tests);
  veto fix at the reader seam instead of `is_stale` normalization (preserves the
  deliberate between-releases reclaim).
- Ship gate: qa-engineer REJECT→fix→APPROVE (REJECT caught 2 surviving old-contract
  pins and a `pytest | tail` exit-code mask; re-run unpiped).
- Push gate: security-reviewer **APPROVED** for `873b11d2` (0 CRITICAL/HIGH/MEDIUM/LOW,
  1 INFO; lock-security, veto integrity, sid-hijack surface, rmtree symlink
  confinement, secrets/PII, dependencies — handoff `metrics.commit_sha` validated).

## Validations

| Check | Result | Evidence |
|---|---|---|
| pytest (full suite, unpiped) | 4,411 passed / 17 skipped, exit 0 | QA ship gate + pre-push preflight |
| ruff format --check + ruff check | PASS | pre-push preflight |
| mypy --strict | PASS | pre-push preflight |
| Frozen no-steal suite (9 paths, SPEC §5 AC-1) | zero diffs, green | QA + security reviews, independently confirmed |
| lint-memory-atoms | All atoms passed lint (28) | closure run |
| memory catalog | regenerated, 25 features | closure run |
| bugs ledger | 0 open (`dadaia bugs status`) | closure run |
| Security push gate | APPROVED keyed to `873b11d2` | handoff 2026-07-02T194652Z |
| CI (PR #89) | 38/38 checks green (35 pass / 3 skipping) | merge gate |

## Drifts

- Security INFO (defence-in-depth, non-blocking): the `rmtree` `onexc` handler's
  `os.chmod(target)` would follow a symlink in a contrived hostile-clone + unlink-failure
  scenario (unreachable via git-tracked content; impact limited to a mode change on an
  operator-accessible file). Optional hardening (`if not target.is_symlink():`) left for
  a future hygiene pass.
- SPEC-DOC-031 WARNs on backlog slugs mentioned by archived releases remain the known
  ADR-6 false-positive class (mentions, not consumption) — no action.

## Backlog returns

None. Both consumed entries shipped in full; no scope was deferred back.

## Memory updates (this closure)

- `sdd-gate-v3.md`: acquire ladder gains the self-recognition rung (+ index hygiene on
  the `.ptr` branch); veto tri-state; sid-resolution precedence. `release_origin: v0.1.50`.
- `context-management.md`: `dead()` exit-path contract (refspec push, empty-push skip,
  `rmtree(onexc)`, pre-checks first); shared CLI resolution seam + root-law refusal;
  ctx_inject sid order via the shared seam. `release_origin: v0.1.50`.
- `specs-doctor.md`: SPEC-DOC-029 holder-confirmation via same-CAS index evidence;
  `--specs-dir` state isolation. `release_origin: v0.1.50`.
