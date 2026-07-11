# CLOSURE — Release v0.1.76 — Lock liberation (advisory presence)

**Shipped:** PR #149, squash-merged to main as `5dbe209c` (2026-07-11). All PR checks
green; post-merge main CI green.

## Delivered

All 7 FRs of the NO-LOCKS DOCTRINE (4 operator-ratified decisions, 2026-07-10):
- FR1 gate never blocks on concurrency — advisory presence upsert + one throttled
  warning; `LockHeldError` block path deleted.
- FR2 lease demolition — `lease.py` 1,056 → 261 lines (diagnostics-only);
  acquire/six-rung tree/O_EXCL CAS/adopt_if_own_lineage/by-session index/`lock steal`
  CLI deleted; new `presence.py` (upsert/others_alive/renew/clear/sweep/stale_records,
  fail-soft, `_valid_name`-guarded).
- FR3 pre-commit WARN-only — detection kept, ALLOW always; pre-push security gate + CI
  preflight untouched.
- FR4 mode strictly self-scoped — context-incumbent fallback deleted (audit P1-1).
- FR5 PI presence parity — stable `pi-session-<uuid>` (CSPRNG) on both hooks;
  anon-session never creates presence.
- FR6 platform seam — 3 in-body `sys.platform` checks → `PLATFORM.has_fcntl`;
  5s micro-locks kept per doctrine decision 3.
- FR7 surfaces repoint — doctor PRESENCE-GC, `context show` presence field, lifecycle
  preflight lease rows → advisory `warnings`, PRESENCE_* audit events; SPEC-DOC-029
  retired with its authority.
- Doctrine doc sweep: 29 public-corpus assets rewritten (rules/skills/agents/
  workflows/AGENTS.md/fragments), projected, `[ok] public-privacy`.

## Dispositions

- **Bug `layer1-rebind-adopts-lease-to-synthetic-session-self-block` (CRITICAL):
  RESOLVED** — `resolved` event appended with executed-path evidence
  (`test_gate_never_blocks_doctrine.py` drives the real hook subprocess with the bug's
  exact post-adoption topology; never blocks on any rebind; PI anon facet guarded;
  two-actor e2e).
- **Audit `2026-07-10-lock-risk-audit-cross-harness` (P0): fully dispositioned,
  archived** as `_archive/...--dispositioned-v0.1.76.md`. Finding map (recorded in the
  delivered backlog entry): P0-1/P0-3/P1-1/P1-4/P1-5 fixed; P0-2 superseded by the
  doctrine (exactly-one-mutator deliberately retired; anon presence guarded);
  P1-2/P1-3/P2-1/P2-2 moot-by-removal; P3-1 kept as designed.
- Backlog `lock-lease-session-identity-kernel` (absorbing
  `platform-seam-todo-retirement`): **delivered**, archived.
- New bug filed during the release: `perf-hygiene-scan-rss-ceiling-flaky-in-sandbox`
  (LOW, open — pre-existing flake, reproduced on parent commits).

## Frozen-suite re-baseline (QA-adjudicated, AC4)

The v0.1.75 successor-baseline rows covering lease/no-steal invariants are RETIRED
WITH the machinery they pinned: 16 test files (~41 fns) deleted — full list with
rationale in the release-branch artifact `v0176-t3-retired-tests.md` (T-3 handoff).
QA spot-verified no still-meaningful invariant lost coverage: micro-lock file
integrity keeps `tests/unit/test_spec_context_locking.py`; the successor invariant
suite is `test_presence.py` (25) + `test_gate_never_blocks_doctrine.py` (11) +
`test_pre_commit_decision.py` (all-ALLOW matrix) + `test_two_actor_presence.py` (4).

## Validations

- Full suite 2,803 passed / 10 skipped (single flake = the registered LOW bug).
- mypy --strict clean (322 files); ruff clean; lint-imports 9 contracts kept —
  ignore-edge cap ratcheted DOWN 36 → 31 (5 suppressed layering violations died with
  the code they excused).
- specs doctor 0 errors; public doctor 0 (privacy ok); backlog doctor clean.
- QA review APPROVED (HIGH doc finding closed in-release by the doctrine sweep).
- Security APPROVED ×5 (initial + 4 re-keys, each verified at token level); LOW
  throttle-path guard fixed in-release with a pinning test.

## Deviations

- None of scope. Three ship-gate catches required in-release fixes (stale
  import-linter ignores; fragment golden; consumed-backlog refs) — all were CI/gate
  systems correctly detecting consequences of the deletion, fixed root-cause.
