# Test Rules — dadaia-workspace

These rules override general workspace guidance for everything under `tests/`.
Agents creating or editing tests must follow them. Full protocol: skill
`dadaia-test-stewardship`.

## Architecture

- `tests/unit/**`: pure or near-pure tests only. No `CliRunner`, real subprocess
  execution, server threads, public stage/install, full workspace init, network,
  sleeps, or real git remotes. Process-boundary units may patch the runner; they
  must not spawn a process.
- `tests/contract/**`: public CLI/API/schema/security/projection/gate contracts.
- `tests/integration/**`: multi-component tests using tmp filesystem, service
  wiring, or CLI runner.
- `tests/e2e/**`: named end-to-end journeys only. Every file names an owner.
- `tests/tmp/**`: temporary debugging reproductions only; excluded from default
  collection and deleted or promoted before closure.

## Intent taxonomy, admission, deletion

- Every test declares intent in its module docstring — `Intent: <KIND> — <AC id |
  bug-id | task-id>` — **never** as a pytest marker (the marker namespace already
  binds `contract` to the layer `tests/contract/`). An undeclared test is
  **SCAFFOLD** — it expires at its originating task/release closure.
- **Mechanical enforcement (v0.4.3 T-043-27, FR19).** `tests/scripts/
  check_test_intent_declared.py`, wired into the gating pytest run via
  `tests/integration/scripts/test_check_test_intent_declared.py`, refuses any
  `tests/e2e/**` test file (Python `test_*.py` or Playwright `*.spec.ts`) with no
  `Intent:` line — the shape accepted is exactly this section's: a module docstring
  (Python) or a header block comment (TypeScript) containing `Intent: <KIND> — <ref>`.
  Size is declared by directory placement (the table below), never a per-file field.
  Scope is `tests/e2e/**` only — the LARGE tier the v0.4.3 census (T-043-24..26) fully
  backfilled; the wider suite carries no mechanical gate yet. Non-test support modules
  (`__init__.py`, `rendezvous.py`, `conftest.py`) are excluded — zero collected items.
- CONTRACT (permanent, asserts an AC or a bug) / SENTINEL (permanent, the single
  integration test of one seam) / SCAFFOLD (temporary) / QUARANTINE (flaky, carries
  a registered bug id).
- **Admission filter.** A new test enters the permanent suite only if it compiles
  and runs, is deterministic, and adds real detection — covers previously-uncovered
  behavior or kills a mutant no current test kills. Prohibited: change-detector
  tests, tautologies (expected value re-derived from the code under test),
  reflex-regenerated snapshots.
- **Deletion criteria** — delete, with `file:line` evidence in the commit, a test
  that: (a) tests a removed feature; (b) duplicates existing coverage (cite
  `file:line`); (c) is a tautology/no-op; (d) is a reflex-regenerated snapshot with
  no review; (e) has a failure→defect ratio ≈ 0; (f) is an expired
  quarantine/skip with no owner action.
- **Tombstone ban.** A test whose central assertion is the *absence* of something
  removed — a deleted feature now errors, a module became a stub, a directory/repo
  was removed, an old migration no longer exists, an old wiring string was
  replaced — validates a historical event, not a live behavior. It is SCAFFOLD of
  the release that removed the thing and dies at that release's closure; the memory
  of the removal belongs to CLOSURE/changelog, never the suite.
- **Separation of powers.** The implementer never prunes to go green. Pruning is a
  `qa-engineer` verdict carrying the evidence above; `software-engineer` executes
  the commit, quoting the verdict.

## Size tiers and cost

| Tier (marker) | Directory | Timeout default | Owner rule |
|---|---|---|---|
| `unit` | `tests/unit/**` | 10 s | — |
| `contract` | `tests/contract/**` | 30 s | — |
| `integration` | `tests/integration/**` | 60 s | — |
| `e2e` (LARGE) | `tests/e2e/**` | 120 s | every file names an owner |

A test that needs more time than its tier's default is **mis-tiered** — fix the
tier, never raise the default (mechanical enforcement: T-070-05). LARGE cap for
this repo: **30**, declared and measured as a WARN (current ~84 is the companion
release's remediation target), never a hard failure in this release.

`flaky` and `quarantine` markers are mechanically wired (T-070-05): both are
registered in `pyproject.toml`, a `quarantine` marker without `bug="<bug-slug>"`
refuses collection, and every gating selector (CI jobs, release jobs, the pre-push
preflight) excludes the quarantine lane. Diagnosis runs use `-m quarantine`
explicitly.

## No Slop

- Do not add tests that only prove deleted code remains deleted (see the tombstone
  ban above).
- Do not add tests for retired invariants, old aliases, migration residue, or
  private implementation strings unless they protect a documented security or
  compatibility contract.
- Do not duplicate private constants in tests as the source of truth.
- Do not write coverage-padding tests.
- Do not name test files after PRs, tasks, releases, or QA gaps. Name current
  behavior instead.

## Markers And Cost

- Layer markers are applied automatically by directory via `tests/conftest.py`.
- Add `@pytest.mark.slow(reason="...")` to any test over 1 second or any test
  that starts a subprocess/server.
- The local loop is:

```bash
pytest -q -m "unit and not slow" tests/unit
```

Coverage is not the default loop. Use explicit coverage only for curated
unit/contract runs:

```bash
pytest -q -m "unit or contract" --cov=dadaia_workspace --cov-report=term-missing --cov-fail-under=80
```

## Good Test Standard

A test is allowed only if it can fail for a meaningful regression in current
product behavior, public contract, security boundary, data integrity, or a real
user journey. If it mainly records implementation history, put it in release
notes or delete it.
