# PLAN: v0.1.5 rc-2 — propagation-pair + semaphore-liveness + panel-verify

**Status:** Aprovado
**Release ID:** v0.1.5
**Segment:** rc-2
**Owner:** product-engineer
**Created:** 2026-06-06

---

## 1. Strategy

Three independent fix groups ship on the existing `feature/0.1.5` branch. Each group
is sequenced to minimize churn on shared files (`doctor.py` in particular is touched
by G2, G3, and G1). G2 lands first because the hash-compare install fix makes all
subsequent propagation verifiable without `--force`; G3 lands second (pure runtime
behavior, no shared files with G2); G1 lands last (qa verify can run against the
stabilized branch).

Implementation order: **G2 → G3 → G1 → SHIP**.

No new dependencies are introduced. All changes are within the existing Python code
(`dadaia_workspace/`) and the lib-originated rules surface (`dadaia_workspace/public/rules/`).

## 2. Layers affected

| Layer | Files touched | Group |
|---|---|---|
| `features/public_assets/public_assets.py` | install skip logic (lines 676, 684), `_src_sha` (line 670) | G2 T-PROP-01 |
| `features/public_assets/public_assets.py` | doctor delegate — add staging↔projected pass | G2 T-PROP-02 |
| `public/rules/dadaia-workspace-dev-guardrail.md` | "Correct edit workflow" section | G2 T-PROP-03 |
| `features/spec_context/semaphore.py` | `_is_stale` + `acquire_context_semaphore` | G3 T-SEMA-01 |
| `features/spec_context/doctor.py` | SEM-1 semaphore invariant + `--fix` | G3 T-SEMA-02 |
| `features/panel/views/api.py` | (read-only for T-PANEL-01 verify; only touched if gap found) | G1 T-PANEL-01/02 |
| `features/panel/views/api.py` or `features/specs/doctor.py` | RPT-1 invariant (reports doctor) | G1 T-PANEL-02 |
| Tests | new unit + integration tests per group | all groups |

## 3. Group design direction

### G2 — Propagation pair

**T-PROP-01 (install hash-compare).**
In `public_assets.py`, the current skip guard is approximately:

```python
if dst.exists() and not force:
    logger.info("[skip] %s", dst)
    return
```

Replace with a hash-compare guard:

```python
if dst.exists() and not force:
    dst_sha = hashlib.sha256(dst.read_bytes()).hexdigest()
    if dst_sha == _src_sha:          # _src_sha already computed at line 670
        logger.info("[skip] %s", dst)
        return
    # hashes differ → fall through to overwrite (content-driven update)
```

`--force` path: clobbers regardless of hash match (existing semantics, unchanged).
This appears at lines 676 and 684 (two call paths — apply to both). Verify with
`diff` that the projected file equals the source after a plain install.

**T-PROP-02 (doctor staging↔projected).**
`PublicAssetService.doctor` calls the manager which today only validates source↔staging.
Add a new pass immediately after the existing checks. For each entry in the staging
manifest, compute the expected projected path(s) for each target runtime (`.dadaia/scripts/`,
`.claude/`, `.codex/`, `.opencode/`, etc.) using the same path-resolution logic `install`
uses. For each expected projected path that exists: compare its SHA256 against the staged
hash; emit `[drift] <path>` and set a `has_drift` flag on mismatch. For each expected
projected path that does not exist: emit `[missing] <path>`. Return non-zero exit if
`has_drift or has_missing`.

This is additive: the existing source↔staging pass is unchanged. The new pass runs
after it and may independently add failures.

### G3 — Semaphore liveness

**T-SEMA-01 (`_is_stale` extension).**
`semaphore.py` currently holds a field `owner` containing `session_id` (string). The
session file for a session is `.dadaia/sessions/<session_id>.json` and contains a `pid`
field. Extend `_is_stale` to:

1. Resolve `session_file = Path(".dadaia/sessions/") / f"{semaphore.owner}.json"`.
2. If `session_file` does not exist → return `True` (owner gone).
3. Read `pid = session_data["pid"]`.
4. Check `os.kill(pid, 0)`: if `OSError` (ESRCH/EPERM-variant that means dead process)
   → return `True`. Use `try/except OSError` to distinguish dead-process from alive-but-no-permission.
5. Existing TTL check runs only if liveness passes.

`acquire_context_semaphore`: before returning a "context locked" error, call `_is_stale`
on the existing semaphore. If stale, log an audit entry (reason: liveness or TTL),
delete the semaphore file, and retry the acquire. The retry must be a single attempt
(no loop), raising if a concurrent holder has re-acquired.

**T-SEMA-02 (doctor SEM-1).**
`spec_context/doctor.py` already has LOCK-3/LOCK-7 invariants for implementation locks.
Add a new invariant family `SEM-1` that globs `ctx_locks/*.semaphore.json` and checks
each:
- Orphaned: semaphore's `context` field has no matching alive context entry in
  `spec_contexts.json` → flag `[orphan-semaphore]`.
- Stale-by-liveness: call the same liveness logic as T-SEMA-01 → flag `[stale-semaphore]`.

`dadaia doctor --fix`: delete flagged semaphores and write an audit log entry in
`.dadaia/states/audit/semaphore-reclaims.jsonl`.

### G1 — Panel verify + invariant

**T-PANEL-01 (qa verify).**
qa-engineer reads `api.py:910-944` and tests the four symptom paths against current
`feature/0.1.5`:
- RC#1: request `/api/reports` with an HTML that has no sidecar → must appear in list.
- RC#2: no row must link to a `.handoff.json` or a source-code file path.
- RC#3: count of rows must be > 2 (all reports from both `.dadaia/reports/` and
  `.dadaia/handoff/` should be indexed).
- RC#4: a report with both HTML and sidecar appears as exactly one row.

If all four pass: emit `verdict: APPROVED` handoff, mark bug resolved. If any fail:
emit `verdict: REJECTED` with specific gaps for T-PANEL-02.

**T-PANEL-02 (RPT-1 invariant).**
Add invariant `RPT-1` to either `dadaia reports doctor` (if that CLI surface exists) or
as a new check function in `features/specs/doctor.py` reachable via `dadaia specs doctor`:

```
For every *.handoff.json under .dadaia/handoff/ and .dadaia/reports/:
  if artifact.path is set:
    if not artifact.path.endswith(".html"):
      emit [dangling-artifact-path] <sidecar> → <artifact.path>
    elif not Path(artifact.path).exists():
      emit [dangling-artifact-path] <sidecar> → <artifact.path> (file missing)
```

This is purely additive: it does not change report discovery, only validates sidecar
correctness. Scope: unit tests only (no E2E panel startup required).

If T-PANEL-01 reports a residual de-dup gap, T-PANEL-02 also patches `api.py` to close it.

## 4. Execution order

```
G2: T-PROP-01 → T-PROP-02 → T-PROP-03
        ↓
G3: T-SEMA-01 → T-SEMA-02
        ↓
G1: T-PANEL-01 (qa) → T-PANEL-02 (polishes if gap found)
        ↓
SHIP: T-SHIP-01 (CI gate) → T-SHIP-02/03/04 (review trio) → T-SHIP-05 (CLOSURE)
```

T-PROP-01 and T-PROP-02 may be developed in the same work session (same file); commit
separately for clean history. T-SEMA-01 and T-SEMA-02 are sequenced (doctor uses the same
liveness logic as the semaphore module). T-PANEL-01 must complete before T-PANEL-02 to
determine its full scope.

## 5. Technical risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Doctor staging pass is slow (hash all projected files) | Medium | Hash only files in staging manifest (bounded set); no filesystem walk |
| `os.kill(pid, 0)` behavior differs on non-Linux | Low | Linux is the declared runtime; add OS guard comment |
| T-PANEL-01 finds a residual gap requiring api.py rewrite | Low | 028ffd5 already addressed all four RC items; residual gap is unlikely but T-PANEL-02 covers it |
| ruff/mypy regressions from G2/G3 additions | Low | Run CI gate (T-SHIP-01) before review dispatch |

## 6. Validation plan

Each group has unit tests covering the positive and negative cases (see SPEC §3 per task).
Integration test: `pytest -p no:cacheprovider` passes on the full suite (T-SHIP-01).
Review trio (T-SHIP-02/03/04) validates correctness, code quality, and security.
No E2E panel startup is required for G2/G3 (pure Python unit tests). G1 verify
(T-PANEL-01) may start the panel process to live-test the Reports tab; that is
qa-engineer's call.
