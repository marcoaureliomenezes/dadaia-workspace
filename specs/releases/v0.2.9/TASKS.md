# TASKS — Release v0.2.9 — Hermes real-use convergence (zero-bug gate)

> **Status:** Aprovado

**Release ID:** v0.2.9
**Owner:** product-engineer
**Source PLAN:** `specs/releases/v0.2.9/PLAN.md`
**Workflow:** release-definition / tasks_create

## Task status markers

- `[ ]` OPEN
- `[-]` IN PROGRESS
- `[x]` DONE

## Tasks

- [x] **T1 - backlog_author acceptance requires an authored delta (F1)**

**Owner role:** software-engineer

**Preconditions:** SPEC/PLAN `Aprovado`.

**Write set:**

- `dadaia_workspace/features/lifecycle/workflows/backlog_definition.py`
- `tests/unit/features/lifecycle/test_backlog_materialization.py`

**Description:**

After `runner.evaluate_gate_with_result` returns unblocked for the
`backlog_author` step, require `self._authored_backlog_paths()` to be non-empty;
when empty, block AT THE STEP with the worker diagnostic and the bounded
structural-correction retry semantics (same posture as the 0.3.1 deliverable
block). A worker that writes or edits a real item stays accepted. Register the
bug (`codex-backlog-author-no-materialization-regression-040`) reported+resolved.

**Validation:**

- `cd /home/ubuntu/workspace/repos/dadaia-workspace && ../../.dadaia/.venv/bin/python -m pytest -p no:cacheprovider tests/unit/features/lifecycle/ -q`

---

- [x] **T2 - scaffold emits no invalid placeholder atom; upgrade/--fix repairs it (F2)**

**Owner role:** software-engineer

**Preconditions:** T1 `[x]` (independent in practice; order kept for one-hermes-round batching).

**Write set:**

- `dadaia_workspace/features/specs/scaffolder.py`
- `dadaia_workspace/features/specs/doctor.py`
- `dadaia_workspace/cli/commands/specs.py`
- `tests/unit/features/specs/test_scaffold_placeholder_repair.py`

**Description:**

`specs init` stops emitting the raw `memory/product/feature.md` placeholder
(unreplaced `*_PLACEHOLDER` markers); a fresh tree is doctor-clean 0/0 with a
valid empty catalog. Add a shared repair that detects atoms with unsubmitted
placeholder markers and removes/replaces them — wired into BOTH `specs upgrade`
and `specs doctor --fix`, documented in their help. Register
`scaffold-repair-cannot-remediate-invalid-placeholder-atom` resolved.

**Validation:**

- `cd /home/ubuntu/workspace/repos/dadaia-workspace && ../../.dadaia/.venv/bin/python -m pytest -p no:cacheprovider tests/unit/features/specs/ -q`
- Fresh `specs init` + `specs doctor` → 0 errors 0 warnings; seeded-placeholder tree + `upgrade` and `--fix` → 0/0.

---

- [x] **T3 - pain sweep: release-definition honest terminal state**

**Owner role:** software-engineer

**Preconditions:** T1 `[x]`.

**Write set:**

- `dadaia_workspace/features/lifecycle/` (stall investigation target)
- `tests/unit/features/lifecycle/` (regression)

**Description:**

Reproduce the hermes-observed "release-definition stalled after writing only
SPEC.md with no terminal state/diagnostic". Root-cause (likely a blocked step
whose `blocked` detail is not persisted/surfaced) and make the terminal state
honest (completed or blocked with the reason). Register the bug.

**Validation:**

- Repro test passes; `tests/unit/features/lifecycle/` green.

---

- [x] **T4 - pain sweep: bounded rejection-correction digest for retries**

**Owner role:** software-engineer

**Preconditions:** T3 `[x]`.

**Write set:**

- `dadaia_workspace/features/lifecycle/` (retry/resume digest path)
- `tests/unit/features/lifecycle/` (regression)

**Description:**

The implementation-reviews retry prompt can exceed the Codex context window.
Bound the rejection-correction digest with an explicit token/line budget and a
deterministic truncation contract (head + tail markers), keeping the rejection
semantics. Register the bug.

**Validation:**

- Digest-budget unit tests; lifecycle suites green.

---

- [x] **T5 - pain sweep: release-id canon at workflow intake + skills/CLI syntax audit + root-exceptions guidance**

**Owner role:** software-engineer

**Preconditions:** T4 `[x]`.

**Write set:**

- `dadaia_workspace/cli/commands/lifecycle.py` (or the intake resolver)
- `dadaia_workspace/public/skills/` (divergent syntax fixes)
- `dadaia_workspace/features/spec_context/doctor.py` (error text guidance)
- `tests/unit/cli/`, `tests/unit/features/spec_context/`

**Description:**

(a) Workflows reject release ids outside `core/specs_version.RELEASE_SEMVER_RE`
(the canon `specs doctor` enforces) at intake with a clear message. (b) Grep-audit
projected skills against CLI help; fix syntax divergences that induce misuse.
(c) The loose-root-file doctor/reconcile error text gains the
`root_exceptions.txt` guidance line. Register each fixed class.

**Validation:**

- Canon rejection test; skill-audit report clean; error text test; suites green.

---

- [ ] **T6 - Recipe v2: real-use matrix section**

**Owner role:** product-engineer

**Preconditions:** T1–T5 `[x]`.

**Write set:**

- `dadaia_workspace/public/data/CONSUMER_VALIDATION_RECIPE.md`

**Description:**

Add the "Real-use matrix" section: the live Codex chain (clean context → backlog
→ release → implementation/review → audit/closure) with per-link
artifact+handoff assertions; backlog materialization canary; fresh/old-context
doctor-clean statements; B3/CVM-style real-demand backlog; bug register→fix→
retest. Explicit statement: deterministic certification alone NEVER approves a
release.

**Validation:**

- Recipe ships in the wheel; hermes reads and executes it.

---

- [ ] **T7 - Hermes convergence rounds until zero real-use failures**

**Owner role:** qa-engineer

**Preconditions:** T1–T6 `[x]`.

**Write set:**

- `.dadaia/tmp/` (candidate staging only)

**Description:**

Build the candidate wheel, stage to hermes (`candidate/` + `CANDIDATE.txt`),
submit the expanded contract round via the task journal + worker socket.
Root-cause every finding (product bug vs docs/misuse vs false positive), fix
classes, register bugs, re-run. Iterate until one complete round reports zero
failures on the real-use inventory. Sweep for the same defect class across
sibling surfaces before reporting any round done.

**Validation:**

- Final hermes verdict: zero failures on the full real-use matrix.

---

- [ ] **T8 - Docs, memory, 0.4.1 gates, deploy**

**Owner role:** product-engineer

**Preconditions:** T7 `[x]`; ACTIVE.md phase CLOSURE for memory writes.

**Write set:**

- `README.md`, `specs/memory/product/harness/` (hermes support atom or equivalent),
  `specs/memory/product/catalog.json`, `specs/memory/product/index.md`,
  `specs/releases/v0.2.9/CLOSURE.md`, `pyproject.toml`

**Description:**

Declare Hermes a supported environment (only after T7's zero round); bump
`pyproject.toml` to 0.4.1; CLOSURE.md with the rounds table; run the standard
gates (full pytest, ruff, mypy, security review handoff, push, PR, CI,
release-gate approval, deploy).

**Validation:**

- PyPI `dadaia-workspace==0.4.1` published; tag `v0.4.1` on main.
