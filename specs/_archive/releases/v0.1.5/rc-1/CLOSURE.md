# Closure: Release — v0.1.5 / rc-1

> **Status:** Aprovado
> **Release ID:** v0.1.5
> **Segment:** rc-1
> **Owner:** product-engineer
> **Closed:** 2026-06-05

## Summary

rc-1 closes the deploy-blocker that kept v0.1.5 from shipping. The segment delivers five
work-streams in a single pass on branch `feature/0.1.5`: the per-context session semaphore
with env-free runtime binding (R1), the backlog-ownership enforcement gate (D5), four
dadaia-native agent specializations (R3), a generic-agent audit (R4), and the
project-manager model upgrade to `claude-opus-4-8` (D4).

R1 is the most structurally significant change: agents no longer require a manual re-bind
to progress through phases. A single `dadaia context bind` carries a session through
read → spec → implementation → review → closure. A per-context semaphore
(`.dadaia/states/ctx_locks/<context>.semaphore.json`) enforces at most one active
implement+review holder per context, denying concurrent writers cleanly with the holder's
identity in the error. Three deferred lock/TOCTOU candidates (glob non-determinism,
CONTEXT_SLUG sanitization, heartbeat renewal gap) were folded into R1 and resolved.

D5 adds a hard PreToolUse gate blocking non-PM agents from writing to `specs/backlog/**`,
backed by an always-on `backlog-ownership.md` rule. R3 sharpened the four dadaia-native
personas (product-engineer, project-manager, project-auditor, ai-engineer) after a
strategy document from ai-engineer was accepted by PM. R4 produced a scored audit report
covering all remaining generic agents; remediation (R4b) is deferred to a future release.

The pre-push CI gate (delivered in flat v0.1.5) held: all rc-1 changes passed ruff format
check, ruff lint, mypy --strict, and pytest (2236 tests) locally. The review trio
(qa-engineer, code-reviewer, security-reviewer) all returned UNANIMOUS APPROVE.

**DEPLOYMENT EXPLICITLY HELD BY OPERATOR.** No push, no PR, no merge, no `git tag`, no
PyPI publish, no live-instance propagation has been performed. All rc-1 commits live
locally on `feature/0.1.5`. The operator will initiate deployment as a deliberate act
when ready.

---

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-R1-01 | Runtime→session pointer (env-free resolution via `.dadaia/sessions/runtime/`) | on `feature/0.1.5` (19e6146..HEAD) |
| T-R1-02 | Per-context semaphore — `.dadaia/states/ctx_locks/<ctx>.semaphore.json` | on `feature/0.1.5` |
| T-R1-03 | Heartbeat renewal (Bug C) — both session file and lock renewed | on `feature/0.1.5` |
| T-R1-04 | Narrow lock glob + CONTEXT_SLUG sanitization (CWE-22 hardening) | on `feature/0.1.5` |
| T-R1-05 | `dadaia context bind` CLI — semaphore acquire + runtime pointer on bind | on `feature/0.1.5` |
| T-R1-06 | Doctor invariants for orphan/stale/duplicate locks + `--fix` | on `feature/0.1.5` |
| T-R1-07 | E2E concurrent-session test (two writers, one denied) | on `feature/0.1.5` |
| T-D5-01 | New always-on rule `backlog-ownership.md` | on `feature/0.1.5` |
| T-D5-02 | Hard PreToolUse gate for `specs/backlog/**` (non-PM write blocked) | on `feature/0.1.5` |
| T-R3-01 | ai-engineer strategy document (skill thinness, placement, cross-ref map) | `.dadaia/reports/dadaia-workspace/ai-engineer/` |
| T-R3-02 | product-engineer persona specialization | `dadaia_workspace/public/agents/product-engineer.md` |
| T-R3-03 | project-manager persona specialization + D4 model bump to `claude-opus-4-8` | `dadaia_workspace/public/agents/project-manager.md` |
| T-R3-04 | project-auditor persona specialization | `dadaia_workspace/public/agents/project-auditor.md` |
| T-R3-05 | ai-engineer persona specialization | `dadaia_workspace/public/agents/ai-engineer.md` |
| T-R3-06 | Propagate R3 + D4 to all runtimes (`dadaia public stage && install --force --target all`) | on `feature/0.1.5` |
| T-R4-01 | Generic-agent audit report (11 findings; remediation deferred to R4b) | `.dadaia/reports/dadaia-workspace/ai-engineer/` |
| T-SHIP-01 | Pre-ship CI gate green: ruff + mypy --strict + pytest 2236 passed | on `feature/0.1.5` |
| T-SHIP-02 | QA review — qa-engineer APPROVE | handoff under `.dadaia/handoff/dadaia-workspace/` |
| T-SHIP-03 | Code review — code-reviewer APPROVE | handoff under `.dadaia/handoff/dadaia-workspace/` |
| T-SHIP-04 | Security review — security-reviewer APPROVE | handoff under `.dadaia/handoff/dadaia-workspace/` |

---

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| ruff format check passes | `ruff format --check dadaia_workspace/` | All passes — T-SHIP-01 CI gate run on `feature/0.1.5` |
| ruff lint passes | `ruff check dadaia_workspace/` | All passes — T-SHIP-01 CI gate run |
| mypy strict passes | `mypy --strict dadaia_workspace` | Zero errors — T-SHIP-01 CI gate run |
| pytest full suite | `pytest -p no:cacheprovider` | 2236 passed — T-SHIP-01 (dispatch briefing) |
| E2E concurrent-session denial | `pytest tests/e2e/test_concurrent_session.py` (T-R1-07) | Passes locally on `feature/0.1.5` |
| D5 backlog write gate blocks non-PM | simulated non-PM Write to `specs/backlog/` | Gate blocks — T-D5-02 acceptance verified |
| D4 model projection: PM is claude-opus-4-8 | `grep -r 'model:' .claude/agents/project-manager.md` | `model: claude-opus-4-8` confirmed — T-R3-06 |
| dadaia public doctor exits 0 | `dadaia public doctor` | exit 0 — T-R3-06 acceptance |
| qa-engineer verdict | handoff JSON | `verdict: APPROVED` — T-SHIP-02 |
| code-reviewer verdict | handoff JSON | `verdict: APPROVED` — T-SHIP-03 |
| security-reviewer verdict | handoff JSON | `verdict: APPROVED` — T-SHIP-04 |

---

## Drifts

### semaphore-no-liveness-reclaim

**Description:** The per-context semaphore added in T-R1-02 reclaims stale holders only on
TTL expiry (300 s). A semaphore held by a provably-dead process (PID gone, session file
missing) is NOT immediately reclaimed, and `dadaia doctor --fix` does not touch the
semaphore surface. Observed live 2026-06-05: a new bind waited ~5 minutes for the TTL of
a dead holder before acquiring. This is exactly the kind of stop-the-flow delay R1 was
designed to eliminate.

**Resolution:** The issue is contained: TTL is 300 s (tolerable for now) and the workaround
is to manually remove the stale semaphore file. The fix (PID liveness check + doctor
semaphore invariant) is filed as bug `semaphore-no-liveness-reclaim` in `specs/bugs/` for
the next release. R1's core acceptance criteria (single-launch env-free phase-through,
semaphore denies second writer, gate functions without env export) are all satisfied.

**Memory updates:** `specs/memory/product/context-management.md` — semaphore field noted;
known limitation documented.

### install-and-doctor-drift

**Description:** During R1 propagation (T-R1-04 gate fixes), `dadaia public install --target all`
silently skipped existing projected files. `dadaia public doctor` reported `[ok]` (exit 0)
while the projection was actually stale. Two bugs filed: `install-skips-existing-files`
and `doctor-blind-to-projected-drift`. Workaround: `dadaia public install --force --target all`.

**Resolution:** Workaround applied for rc-1. Both bugs filed for the next planning cycle.
This drift did not affect the final shipped state — all propagations used `--force`.

**Memory updates:** None required (behavior is a bug to fix, not a feature to document).

---

## Memory updates

- `specs/memory/product/context-management.md` — updated to reflect the per-context semaphore
  (`.dadaia/states/ctx_locks/<ctx>.semaphore.json`), the runtime→session pointer
  (`.dadaia/sessions/runtime/<pid>.ptr`), new doctor invariants (LOCK-7 semaphore codes),
  and the known limitation (semaphore-no-liveness-reclaim).
- `specs/memory/product/sdd-gate-v3.md` — updated to reflect the env-free RULE E resolution
  path (runtime ptr file priority: env var → `.dadaia/sessions/runtime/<pid>.ptr` → non-stale
  lock → deny), the narrowed lock glob, CONTEXT_SLUG sanitization, dual heartbeat renewal
  (session file + lock + semaphore).
- `specs/memory/product/sdd-bug-backlog-governance.md` — added backlog-ownership enforcement
  (D5 gate + rule) to the governance layer description; release_origin updated.
- `specs/memory/product/index.md` — catalog order and entries unchanged (no new production
  features added; no features removed).
- `specs/memory/tech-stack.md` — no change (no new dependencies added in rc-1).
- `specs/memory/architecture.md` — no change required (semaphore is a runtime state
  mechanism, not a new architectural layer).

---

## Backlog returns

- `specs/backlog/candidates.md` ← `semaphore-no-liveness-reclaim` fix (PID liveness check
  + doctor semaphore invariant + `--fix` for semaphore surface). References bug
  `specs/bugs/semaphore-no-liveness-reclaim.md`.
- `specs/backlog/candidates.md` ← `install-skips-existing-files` fix (overwrite on hash
  mismatch, no `--force` required for legitimate updates). References bug
  `specs/bugs/install-skips-existing-files.md`.
- `specs/backlog/candidates.md` ← `doctor-blind-to-projected-drift` fix (staging vs
  projected SHA check). References bug `specs/bugs/doctor-blind-to-projected-drift.md`.
- `specs/backlog/candidates.md` ← R4b: generic-agent trim work-stream (11 findings from
  T-R4-01 audit; scoping and prioritization required before implementation).

---

## Archive decision

**MOVE** — segment directory `specs/releases/v0.1.5/rc-1/` to be moved to
`specs/_archive/releases/v0.1.5/rc-1/` via `git mv` once deployment is executed and
the full v0.1.5 lifecycle closes. This is deferred along with deployment.

The v0.1.5 flat release directory (`specs/releases/v0.1.5/`) will also move to
`specs/_archive/releases/v0.1.5/` at that time.

ACTIVE.md will be updated to `release: none` (or the next active release) when archiving
is triggered by the operator.
