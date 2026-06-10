# TASKS: v0.1.10 — Lock Correctness + Model Registry

**Status:** Em revisão
**Release ID:** v0.1.10
**Owner:** product-engineer
**Created:** 2026-06-10

Marks: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.

Parallel execution is safe across tracks (Track A / Track B / Track C) because each
track touches disjoint file sets. Within Track A, WS-3B depends on WS-3A (coordinate
edits in `sdd_gate.py` and `context_cmd.py`). Track B is sequential (WS-4B depends on
WS-4A). Track C tasks are independent of all others.

---

## Pre-work — verification

### T-0110-VERIFY-01 — Confirm opencode-parity bug superseded by v0.1.8

- **Status:** [ ]
- **Owner:** software-engineer
- **Write set:** none (read-only verification)
- **Preconditions:** none
- **Acceptance:** Run
  `pytest -p no:cacheprovider -q tests/e2e/features/test_opencode_parity_hardening.py::TestPluginProjection::test_sdd_gate_plugin_projected`
  at HEAD. Test passes. Confirm line 129 reads `assert "sdd-spec-gate.sh" not in text`.
  Record the passing pytest output as evidence in CLOSURE. Close bug
  `opencode-parity-test-asserts-stale-bash-script-ref` as superseded-by-v0.1.8.
- **Parallelism:** Independent; can run immediately.
- **Done criterion:** Evidence (pytest pass) captured; bug record updated with
  `status: Closed` and `superseded_by: v0.1.8`.

---

### T-0110-VERIFY-02 — Confirm claude-fable-5 workaround applied (operator gate)

- **Status:** [ ]
- **Owner:** software-engineer (verification only)
- **Write set:** none (read-only verification)
- **Preconditions:** SATISFIED — operator applied the workaround 2026-06-10: `MODEL_MAP`
  has `"claude-fable-5": "gpt-5.5"`, `PRICING_TABLE` has `ModelPricing(10.00, 50.00,
  12.50, 1.00, date(2026,6,1))`, `test_model_mapping.py` updated to 5 entries, all targets
  reprojected, doctor exit 0. Five agents (product-engineer, software-engineer, qa-engineer,
  ai-engineer, project-auditor) run `claude-fable-5`. 27 catalog tests green.
- **Acceptance:**
  ```
  python -c "from dadaia_workspace.infrastructure.runtime_transforms.model_mapping import MODEL_MAP; assert 'claude-fable-5' in MODEL_MAP"
  python -c "from dadaia_workspace.features.telemetry.pricing import PRICING_TABLE; assert 'claude-fable-5' in PRICING_TABLE"
  ```
  Both pass. Grep confirms 5 agent `.md` files have `model: claude-fable-5`.
- **Parallelism:** Precondition satisfied; T-0110-05 may proceed once this task is verified.
- **Done criterion:** Both assertions pass; grep evidence recorded.

---

## Track A — Lock correctness (software-engineer)

### T-0110-01 — WS-1: Context-relative ADDITIVE classifier (gate_policy.py)

- **Status:** [ ]
- **Owner:** software-engineer
- **Write set:**
  `dadaia_workspace/features/spec_context/gate_policy.py`,
  `tests/unit/features/spec_context/test_gate_policy.py` (new sibling in existing
  `spec_context/` test directory; use the dual-session clock-injection fixture pattern
  from `tests/unit/features/spec_context/test_lease_activity_exemption.py`)
- **Preconditions:** SPEC + PLAN Aprovado.
- **Acceptance:** AC-LOCK-01 and AC-LOCK-02.
  - Unit: `classify_path("repos/dadaia-workspace/specs/bugs/foo.md")` returns `PathClass.ADDITIVE`.
  - Unit: `classify_path("repos/dadaia-workspace/specs/backlog/bar.md")` returns `PathClass.ADDITIVE`.
  - Unit: `classify_path("repos/dadaia-workspace/specs/audits/20260610T000000Z-abc1234/foo.md")` returns `PathClass.ADDITIVE`.
  - Unit: `classify_path("repos/dadaia-workspace/specs/releases/v0.1.10/SPEC.md")` returns `PathClass.MUTATING` (context-relative short-circuit does not match; falls through to workspace-relative classifier).
  - Unit: `classify_path("repos/dadaia-workspace/specs/memory/architecture.md")` returns `PathClass.MEMORY` (same fall-through).
  - Unit: `classify_path("specs/bugs/foo.md")` returns `PathClass.ADDITIVE` (workspace-root ADDITIVE unaffected).
  - **Full-pipeline regression (AC-LOCK-02):** session A acquires lease; clock injected
    to advance 130 s with no Write/Edit; session B calls `gate_policy.evaluate` end-to-end
    on `repos/dadaia-workspace/specs/bugs/<slug>.md`; assert ALLOW returned AND
    `lease.read_record()` still shows session A as holder. Dual-session fixture required.
  - **Bash-vs-Python parity:** For in-repo ADDITIVE paths, the bash gate (`sdd-spec-gate.sh`)
    must not acquire a lease (returns ALLOW without lease modification). Add a parity
    assertion verifying bash gate behavior matches Python gate for this path class.
  - `pytest` passes (0 regressions).
- **Parallelism:** Independent of T-0110-02; file-disjoint. May run concurrently.

---

### T-0110-02 — WS-2: PostToolUse lease heartbeat renewal (sdd_post_gate.py)

- **Status:** [ ]
- **Owner:** software-engineer
- **Write set:**
  `dadaia_workspace/hooks/sdd_post_gate.py`,
  `tests/unit/hooks/test_sdd_post_gate.py`
- **Preconditions:** SPEC + PLAN Aprovado.
- **Acceptance:** AC-LOCK-03 and AC-LOCK-04.
  - The `renew_heartbeat` call is placed OUTSIDE the session-file existence guard in
    `sdd_post_gate.py` (no early return that skips renewal when `DADAIA_SESSION_ID` is
    set and session file is absent).
  - PostToolUse with `DADAIA_SESSION_ID=<holder>` updates `lease.read_record().heartbeat`.
  - **No-session-file variant (AC-LOCK-03):** renewal occurs even when the session file
    is absent — the holder's lease heartbeat is updated without a session file present.
  - With injected clock advanced 130 s, the lease is not stale after PostToolUse fires
    (holder can renew past TTL — the is_stale gate in `renew_heartbeat` must not block the
    confirmed holder).
  - A foreign write attempt after PostToolUse renewal gets `LockHeldError`.
  - PostToolUse with unset `DADAIA_SESSION_ID` is a no-op (no error, returns 0).
  - `pytest` passes.
- **Parallelism:** Independent of T-0110-01 and T-0110-03. File-disjoint.

---

### T-0110-03 — WS-3A: `dadaia context bind` --mode optional (CLI)

- **Status:** [ ]
- **Owner:** software-engineer
- **Write set:**
  `dadaia_workspace/cli/context_cmd.py` (or whichever file implements `context bind`),
  `tests/` (integration test for bind CLI)
- **Preconditions:** SPEC + PLAN Aprovado. Locate the bind subcommand: grep `context bind`
  in `dadaia_workspace/cli/` before editing.
- **Acceptance:** AC-LOCK-05.
  - `dadaia context bind dadaia-workspace` (no --mode) exits 0.
  - Emitted env export includes `DADAIA_MODE=read` or equivalent safe default.
  - `dadaia context bind dadaia-workspace --mode implementation` still works.
  - `dadaia context bind dadaia-workspace --mode read` still works.
  - `pytest` passes.
- **Parallelism:** Should coordinate with T-0110-04 (same CLI area); recommend sequential.

---

### T-0110-04 — WS-3B: Session-file READ-mode gate block (sdd_gate.py)

- **Status:** [ ]
- **Owner:** software-engineer
- **Write set:**
  `dadaia_workspace/hooks/sdd_gate.py`,
  `tests/unit/hooks/test_sdd_gate.py`
- **Preconditions:** T-0110-03 complete (same context area).
- **Acceptance:** AC-LOCK-06 and AC-LOCK-07.
  - Mode resolution order verified: (1) `DADAIA_MODE` env var fast-path; (2) session-file
    `mode` field lookup; (3) default `IMPLEMENTATION` when both absent.
  - With `DADAIA_MODE=READ` in env (fast-path): Write to `specs/releases/v0.1.10/SPEC.md`
    returns BLOCK with read-mode message.
  - With session file recording `mode: READ` (no env var): Write to a MUTATING path
    returns BLOCK.
  - With `DADAIA_MODE` absent AND no session file: gate defaults to IMPLEMENTATION;
    holder session's MUTATING writes proceed as today (AC-LOCK-06 default-path test).
  - With mode READ: Write to `specs/bugs/foo.md` returns ALLOW (AC-LOCK-07).
  - PROTECTED paths remain BLOCK regardless of `DADAIA_MODE`.
  - `pytest` passes.
- **Parallelism:** After T-0110-03.

---

## Track B — Model registry (software-engineer)

### T-0110-05 — WS-4A: core/model_registry.py + refactor MODEL_MAP + PRICING_TABLE

- **Status:** [ ]
- **Owner:** software-engineer
- **Write set:**
  `dadaia_workspace/core/model_registry.py` (new),
  `dadaia_workspace/infrastructure/runtime_transforms/model_mapping.py`,
  `dadaia_workspace/features/telemetry/pricing.py`
- **Preconditions:** T-0110-VERIFY-02 verified (precondition satisfied). SPEC + PLAN Aprovado.
- **Acceptance:** AC-MODEL-01, AC-MODEL-02.
  - `core/model_registry.py` exists and defines `ModelEntry` (with `pricing: list[ModelPricing]`)
    and `_REGISTRY`.
  - `ModelPricing` moved to `core/` (or re-exported from `core/`); `pricing.py` imports
    from `core/`.
  - `MODEL_MAP` and `PRICING_TABLE` key sets are identical (both derived from registry).
  - `PRICING_TABLE` uses the most-recent `ModelPricing` row per model.
  - `PRICING_TABLE` contains `claude-haiku-4-5-20251001` (not `claude-haiku-3-5`).
  - `PRICING_TABLE` contains `claude-fable-5` with correct pricing row.
  - `pytest` passes. `mypy --strict` passes. `import-linter` passes.
- **Parallelism:** After T-0110-VERIFY-02. Independent of Track A.

---

### T-0110-06 — WS-4B: features/public/ doctor check for model frontmatter resolution

- **Status:** [ ]
- **Owner:** software-engineer
- **Write set:**
  `dadaia_workspace/features/public/doctor.py` (or the appropriate `features/public/`
  doctor module — locate before editing),
  `tests/unit/features/public/test_model_registry_doctor.py` (new; includes the
  key-set parity assertion: `assert MODEL_MAP.keys() == set(PRICING_TABLE.keys())`)
- **Preconditions:** T-0110-05 complete. Import-linter contract for
  `features/public/ → core/model_registry` verified (add exception if needed before editing).
- **Acceptance:** AC-MODEL-03, AC-MODEL-04.
  - `dadaia public doctor` emits error for an agent frontmatter with `model: claude-nonexistent-99`.
  - With all current agent frontmatter models in the registry (including `claude-fable-5`),
    doctor exits 0 for the model-consistency check.
  - `MODEL_MAP.keys() != set(PRICING_TABLE.keys())` triggers a doctor error (key-set
    parity check in the doctor module, also asserted in `test_model_registry_doctor.py`).
  - `pytest` passes.
- **Parallelism:** After T-0110-05.

---

## Track C — Shell gates (software-engineer)

### T-0110-07 — WS-5: sdd-spec-gate.sh FPATH realpath canonicalization

- **Status:** [ ]
- **Owner:** software-engineer
- **Write set:**
  `dadaia_workspace/public/scripts/sdd-spec-gate.sh`,
  `tests/integration/test_sdd_gate_symlink.py` (new; pytest fixture creates symlink in
  `tmp_path`, invokes shell gate via subprocess, asserts MEMORY classification — manual
  smoke alone is insufficient per AC-GATE-01),
  bash-vs-python gate parity check (can be part of `test_sdd_gate_symlink.py` or a
  sibling test file) verifying that for in-repo ADDITIVE paths, the bash gate returns
  ALLOW without lease modification.
- **Preconditions:** SPEC + PLAN Aprovado.
- **Acceptance:** AC-GATE-01.
  - Automated integration test: symlink in `tmp_path` pointing to MEMORY path → shell gate
    returns MEMORY (blocked), not UNGATED.
  - Bash-vs-python parity test: `repos/<ctx>/specs/bugs/<slug>.md` → bash gate returns
    ALLOW (no lease acquired).
  - Canonicalization fallback order: `realpath --canonicalize-missing` → `readlink -f` →
    Python one-liner (no silent `echo "$FPATH"` last resort).
  - Existing gate integration tests pass (no regression on normal paths).
  - After change: `dadaia public stage && dadaia public install --target all`.
    `dadaia public doctor` exits 0.
- **Parallelism:** Independent of all other tracks.

---

### T-0110-08 — WS-6: pre-push-ci-gate.sh workspace venv probe

- **Status:** [ ]
- **Owner:** software-engineer
- **Write set:**
  `dadaia_workspace/public/scripts/pre-push-ci-gate.sh`,
  `tests/unit/public/test_pre_push_gate_venv_probe.py` (new; fake filesystem tree fixture
  verifies: DADAIA_BIN override honored first; workspace-walk finds `.dadaia/.venv/bin/dadaia`
  when DADAIA_BIN absent; error raised when no runner found — manual smoke alone is
  insufficient per AC-PRE-PUSH-01)
- **Preconditions:** SPEC + PLAN Aprovado.
- **Acceptance:** AC-PRE-PUSH-01.
  - Unit test (fake filesystem): DADAIA_BIN override is honored (highest priority).
  - Unit test: workspace-walk probe finds `.dadaia/.venv/bin/dadaia`.
  - Unit test: gate fails with clear error when no runner is found.
  - Priority order in script: DADAIA_BIN → workspace-level venv → poetry → repo-relative
    .venv.
  - Manual smoke: in the self-hosting layout (workspace venv at
    `<ws>/.dadaia/.venv/bin/dadaia`, no poetry on PATH), `git push` from
    `repos/dadaia-workspace/` runs the CI suite without `--no-verify`.
  - After change: `dadaia public stage && dadaia public install --target all`.
    `dadaia public doctor` exits 0.
- **Parallelism:** Independent of all other tracks.

---

## Final gate (all tracks)

### T-0110-09 — Release final gate

- **Status:** [ ]
- **Owner:** software-engineer
- **Write set:** none (gate verification only)
- **Preconditions:** All T-0110-01 through T-0110-08 complete.
- **Acceptance:**
  1. `pytest -p no:cacheprovider` — 0 failures.
  2. `ruff format --check && ruff check` — clean.
  3. `mypy --strict` — 0 errors, 0 unignored warnings.
  4. `import-linter` — 0 violations.
  5. `dadaia public doctor` — exit 0 (model-registry doctor check included).
  6. `dadaia specs doctor` — exit 0.
  7. **Registry key-set parity assertion** (pytest, in `tests/unit/features/public/test_model_registry_doctor.py`):
     `assert MODEL_MAP.keys() == set(PRICING_TABLE.keys())` — replaces the grep check.
  8. `pytest` on `test_model_registry_doctor.py` confirms `claude-haiku-3-5` is NOT a
     key in `PRICING_TABLE` (haiku desync corrected).
  9. `dadaia context bind dadaia-workspace` (no --mode) — exits 0.

---

## Public-asset propagation note

Tasks T-0110-07 and T-0110-08 modify files under `dadaia_workspace/public/scripts/`.
After either task, the implementer must run:

```
dadaia public stage && dadaia public install --target all
dadaia public doctor
```

This is a required step before the final gate.
