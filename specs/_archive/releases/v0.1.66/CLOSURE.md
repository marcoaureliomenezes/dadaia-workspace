# Closure: Release — v0.1.66 — Layer-2 Worker Path Remediation

> **Status:** Aprovado
> **Release ID:** v0.1.66
> **Owner:** product-engineer
> **Closed:** 2026-07-08
> **Branch:** `feature/v0.1.66` · **Merged:** `70c9760c` (PR #126, squash, 2026-07-08, all CI green incl. post-merge `main`) · **Closure branch:** `chore/v0.1.66-closure`
> **Ship gates:** qa-engineer **APPROVED** (ship-gate handoff `2026-07-08T170000Z-qa-engineer-v0166-validation.handoff.json` — full suite 4970 passed/0 failed; all 7 AC(repro) tests independently RED→GREEN re-verified at each fix's parent commit; real-binary pi/codex smoke; no-workaround audit clean) · security-reviewer **APPROVED** (push-gate keyed to `753f1f19`, 0 findings above INFO) · CI **all checks green**.
> **Mandate:** bug-driven release (no backlog consumption) — 7 registered bugs (`specs/bugs/20260708T15Z-00.jsonl`) surfaced by a remote user blocked on both Layer-2 worker paths (`pi`, `codex`) through `dadaia lifecycle pipeline`. Operator hard mandate: RED-first executed-path reproduction + root-cause fix only, no workarounds/config band-aids/test-only shims, per FR — see SPEC.md "Reproduction & TDD mandate".

## Summary

v0.1.66 fixes the 7 root-cause defects that made both Layer-2 worker paths (`pi` and
`codex`) unusable end-to-end when driven through `dadaia lifecycle pipeline`: a pi setup
failure silently collapsing into a generic block reason, a too-strict worker-result
contract that rejected a valid worker output, an invalid built-in OpenRouter model id, a
missing codex trust flag, a codex sandbox default that fails under container `bwrap`, a
`resume` command that lied about advancing a blocked run, and an `implement` step whose
write scope structurally could never cover a production/test path. Every fix followed a
non-negotiable release-wide mandate: a RED-first executed-path reproduction test driving
the real `dadaia lifecycle` CLI (never a helper call), a root-cause fix with zero
workarounds, and the same test GREEN after the fix — closing off exactly the class of
local mitigation (PATH-shim wrappers, model-alias files, `--dangerously-bypass-*`
wrappers) the intake reports had resorted to.

Beyond the 7 fixes, the release adds an observability guarantee (FR8): when a worker
result legitimately lacks artifact evidence, the block detail is now enriched with a
`validated_handoff_path` when an independently-validating handoff file exists on disk —
without ever turning a genuine no-op worker into a pass. Two new MEDIUM/HIGH bugs were
discovered and registered mid-release, both about a shared test-infrastructure gotcha
(the adapters' `runner: Runner = subprocess.run` default binds at class-definition time,
so a `monkeypatch.setattr` on the module attribute silently falls through to the real
binary); they are next-pick debt, not fixed here.

## Tasks completed

All implementation landed on `feature/v0.1.66` and merged as squash `70c9760c` (PR #126).
Per-task RED-first evidence, root-cause description, and AC-MUT proof-of-bite are in
`TASKS.md` completion notes.

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-66-01 | FR3 — valid OpenRouter kimi model id (`kimi-2.7` → `moonshotai/kimi-k2.5`, 3 coordinated locations) | `70c9760c` |
| T-66-02 | FR4 — codex adapter passes `--skip-git-repo-check` | `70c9760c` |
| T-66-03 | FR5 — codex sandbox env override `DADAIA_CODEX_SANDBOX` via `CodexExecConfig.__post_init__` choke point | `70c9760c` |
| T-66-04 | FR1 — pi non-zero exit reported as FAILED (`_result_from_output` guard widened) | `70c9760c` |
| T-66-05 | FR2 — tolerant worker-result contract (`schema_version` equivalence + singular `artifact.path` fallback), no-op invariant preserved | `70c9760c` |
| T-66-06 | FR8 — precise upstream failure detail enrichment (`validated_handoff_path`) | `70c9760c` |
| T-66-07 | FR6 — `resume` reports the real run status (BLOCKED, non-zero exit) | `70c9760c` |
| T-66-08 | FR7 — implement step write scope union via `--write-scope`, gated on `is_review` | `70c9760c` |
| T-66-09 | QA wave — executed-path re-verification + golden regression + import-linter + AC-MUT + real-binary smoke | (verification only, no source write) |

## Validations

Each row is a triple: description, command, evidence (SHA / stdout snippet / handoff path).

| Description | Command | Evidence |
|-------------|---------|----------|
| Full suite green | `pytest -p no:cacheprovider -q` (unpiped, real exit) | **4970 passed, 18 skipped, 0 failed** (up from pre-fix baseline 4967 passed/2 failed) — T-66-09 |
| Format clean | `ruff format --check .` | 844 files clean — T-66-09 |
| Lint clean | `ruff check --no-cache .` | all checks passed — T-66-09 |
| Types clean | `mypy --strict dadaia_workspace/` | 0 issues, 319 files — T-66-09 |
| Import contracts | `lint-imports --config setup.cfg --no-cache` | 9 kept / 0 broken — T-66-09 |
| AC1(repro) — pi non-zero exit surfaces real stderr | `test_pi_pipeline_surfaces_real_setup_failure_not_generic_block` | RED→GREEN independently re-captured by QA at the FR1 parent commit — T-66-04/T-66-09 |
| AC2(repro) + AC2(repro-negative) — tolerant contract, no-op invariant survives | `test_pi_pipeline_accepts_schema_version_and_singular_artifact_result` + `test_pi_pipeline_still_blocks_on_genuine_noop_worker` | RED→GREEN + baseline-PASS-before-and-after independently re-verified — T-66-05/T-66-09 |
| AC2.4 — invariant-pinning tests byte-identical | `git diff 7758de1f..HEAD -- tests/unit/infrastructure/test_pi_runtime.py` | the two named tests absent from the diff hunks — zero changes — T-66-09 |
| AC3(repro) — kimi id reaches real argv | `test_pi_openrouter_kimi_profile_reaches_command_with_valid_id` | RED (`kimi-2.7` captured) → GREEN (`moonshotai/kimi-k2.5` captured) — T-66-01/T-66-09 |
| AC4(repro) — codex trust flag unblocks untrusted dir | `test_codex_pipeline_untrusted_dir_no_longer_blocks_on_trust_error` | RED (trust error) → GREEN (flag present, advances) — T-66-02/T-66-09 |
| AC5(repro) — sandbox override avoids container bwrap failure | `test_codex_pipeline_sandbox_override_avoids_container_bwrap_failure` | RED (`read-only` reaches argv regardless of env) → GREEN (`danger-full-access`/`workspace-write` reaches argv) — T-66-03/T-66-09 |
| AC6(repro) — resume exits non-zero on still-BLOCKED run | `test_lifecycle_resume_cli_exits_nonzero_on_still_blocked_run` | RED (`exit_code==0`, `"OK resumed"`) → GREEN (non-zero, real block reason) — T-66-07/T-66-09 |
| AC7(repro) — implement write-scope covers reserved task | `test_implement_pipeline_write_scope_covers_reserved_task_production_path` | RED (out-of-scope block) → GREEN (`--write-scope` reaches `allowed_paths`) — T-66-08/T-66-09 |
| AC8(repro) — block detail carries `validated_handoff_path`, run stays BLOCKED | `test_pipeline_block_detail_carries_validated_handoff_path_when_refs_empty` | RED (`detail == {}`) → GREEN (`detail["validated_handoff_path"]` populated, `status == BLOCKED`) — T-66-06/T-66-09 |
| AC-MUT proof-of-bite (all 8 FRs) | per-task local revert → re-run unit test → confirm FAIL → re-apply → confirm GREEN | recorded per-task in TASKS.md DONE notes; cross-checked by QA against the diff shape — T-66-01..08/T-66-09 |
| No-workaround audit | full `git diff 7758de1f..HEAD` read against the forbidden-shape list (try/except swallow, config band-aid, PATH shim, alias file, wrapper script) | zero violations; the one new `try/except HandoffSchemaError` (FR8, `container._build_handoff_lookup`) is a narrow, documented, non-authoritative observability degrade — T-66-09 |
| Real-binary smoke (beyond SPEC mandate, operator's explicit ask) | `pi --list-models kimi --provider openrouter`; `codex exec --help`; full `codex exec --ignore-user-config --skip-git-repo-check --sandbox danger-full-access` from a non-trusted temp dir; `pi --mode json` real invocation | `moonshotai/kimi-k2.5` confirmed a real OpenRouter model; `--skip-git-repo-check` + `--sandbox {read-only,workspace-write,danger-full-access}` confirmed real codex flags; real codex invocation exit 0, no trust/bwrap failure; real pi invocation exit 0, clean `message_end` — T-66-09 |
| Golden regression | `test_pipeline_runs_to_closure_on_fake` (part of the 4970-passed run) | unmodified, green — T-66-09 |
| QA ship gate | `dadaia reports validate <handoff>` | **APPROVED** — `.dadaia/handoff/dadaia-workspace/2026-07-08T170000Z-qa-engineer-v0166-validation.handoff.json` |
| Security push gate (per push-cycle) | pre-push security-verdict chokepoint | **APPROVED** — sha `753f1f19`, 0 findings above INFO |
| CI (PR #126) | GitHub Actions | all checks green on `70c9760c` incl. post-merge `main` |

### Reproduction & no-workaround compliance

Per the operator's hard mandate (SPEC.md "Reproduction & TDD mandate"): every one of the
7 fixes (FR1, FR3, FR4, FR5, FR6, FR7 as source fixes, plus FR2's contract widening) was
proven RED-first on the **real executed path** — `CliRunner` + `dadaia_workspace.cli.main.app`
driving the real `container.build_agent_runtime` / `LifecycleAgentRunner` /
`LifecycleStateMachine` chain, with only the outermost subprocess seam or an injected
`FakeAgentRuntime` result faked at the adapter boundary — never a bare helper-function
call. Each RED capture named the exact reason the remote user hit (real stderr text,
invalid model id, missing trust flag, bwrap failure text, stale `OK` exit, out-of-scope
block), and the identical test (never a rewritten weaker variant) went GREEN in the same
commit as its root-cause fix. QA (T-66-09) independently re-verified all 8 AC(repro)
tests RED→GREEN at each fix's own parent commit via a detached worktree, then ran a full
`git diff` no-workaround audit against the forbidden-shape list — zero violations. This
was the operator's explicit hard mandate, not a discretionary practice, and is recorded
here as closure evidence per that mandate.

## Drifts

### dadaia-codex-sandbox-env-allowlist-registration (T-66-09 QA step 1)

**Description:** FR5's real production `os.environ` read of `DADAIA_CODEX_SANDBOX`
(inside `CodexExecConfig.__post_init__`) tripped the pre-existing harness-env contract
test `tests/contract/test_harness_env_contract.py::test_no_file_writes_non_allowlisted_dadaia_env`,
which fails closed on any file-level `DADAIA_*` env read that is not registered in
`tests/fixtures/harness_env.py::ALLOWLISTED_DADAIA_ENV`.

**Resolution:** governance working as designed, not a defect. QA added the allowlist
entry for `DADAIA_CODEX_SANDBOX` with a one-line justification naming the production
reader (`CodexExecConfig.__post_init__`). No source behavior changed by this drift; it
is a required registration step, not a workaround.

**Memory updates:** `specs/memory/tech-stack.md` — none needed (the harness-env
allowlist itself is not memory-documented product truth, it is a test-infra contract);
`specs/memory/product/harness/harness-codex.md` documents the `DADAIA_CODEX_SANDBOX`
env var itself as product behavior (see "Memory updates" below).

### pi-codex-adapter-subprocess-default-binding-false-positive (T-66-01 discovery, carried through Wave A/B)

**Description:** while writing T-66-01's (FR3) executed-path reproduction, the
implementer discovered that `PiHeadlessAdapter.__init__`'s `runner: Runner =
subprocess.run` keyword default is evaluated **once**, at class-definition time — so
`monkeypatch.setattr("...pi_runtime.subprocess.run", fake)` never reaches an
already-constructed adapter's `self._runner`; the adapter keeps calling the real
`subprocess.run` function object it captured at import. `CodexExecAdapter` carries the
identical pattern. The **pre-existing** CLI-level pi test
(`test_pipeline_runs_first_step_on_pi_harness_end_to_end`) was a latent false positive:
it "passed" because its only assertion on the block reason was loose/truthy, and the
real local `pi` binary's own auth-failure stderr happened to satisfy that assertion —
the test never actually verified the injected fake stream drove the block.

**Resolution:** routed around, not fixed, for every new executed-path repro test this
release needed (T-66-01 through T-66-08): construct the adapter directly with an
explicit `runner=fake_run` via a patched `container.build_agent_runtime` branch — the
same constructor-injection seam `test_pi_runner_ring2.py` / `test_codex_exec_runtime.py`
already used — while keeping the CLI, `--step-model` resolution, and the full
`LifecyclePipeline`/gate chain real. This is a legitimate test-infrastructure pattern,
not a source workaround (the SPEC's no-workaround mandate governs *source* fixes; this
is a test-double wiring correction). The underlying adapter default-binding pattern
itself is deliberately **not** touched in this release (Wave A/B/C scope is the 7 named
FRs' source fixes only) — it is registered as next-pick debt (see "Bug dispositions"
below), consistent with the SPEC's "no fix may be a workaround" mandate not extending to
scope decisions about *which* defects this release fixes.

**Memory updates:** `specs/memory/quality-assurance.md` — the executed-path law gains
this concrete instance (a loose truthy assertion + a default-bound test double both
independently mask a false positive); see "Memory updates" below.

## Memory updates

Memory describes the product **as it is now**; the change history lives here and in
`_archive/`. All edits landed in this CLOSURE phase (MEMORY gate open), rebased on the
current v0.1.65-closed truth (each atom read before editing; no sibling truth reverted).
`release_origin: v0.1.66` + `last_updated: 2026-07-08` set on every edited atom.
**Catalog regen required** (PM follow-up: `dadaia memory catalog generate`) — `tldr`
changed on `harness-pi`.

- `specs/memory/product/harness/harness-pi.md` — **primary.** Corrected the documented
  Layer-2 model set: `kimi-2.7:high` → `moonshotai/kimi-k2.5:high` (FR3) in both the
  Usage flow and Typical trigger sections. Added the FR1 result-classification fact: a
  non-zero pi subprocess exit now maps to `FAILED` unconditionally (previously only when
  stdout was also empty), with the real (redacted) stderr threaded into `result.error`.
  Added the FR2 tolerant-contract fact: the shared extraction now also accepts
  `schema_version` as an equivalent label and a singular `artifact.path` as a one-element
  fallback, with the no-op-worker invariant unchanged (a genuine no-op still BLOCKs).
- `specs/memory/product/harness/harness-codex.md` — **primary.** Documented the new
  `--skip-git-repo-check` flag now unconditionally in the fixed argv (FR4) alongside
  `--ignore-user-config`. Documented the new `DADAIA_CODEX_SANDBOX` env-var override
  (FR5): resolved once at `CodexExecConfig.__post_init__`, validated against
  `{read-only, workspace-write, danger-full-access}`, an explicit caller value always
  wins over the env var, the compiled-in default remains `read-only` when unset — the
  outer `dadaia lifecycle` gate (not codex's own sandbox flag) remains the real
  write/access security boundary.
- `specs/memory/product/sdd/lifecycle-foundation.md` — **primary.** Documented FR6:
  `resume_run` now inspects the loaded run's persisted status and returns a real
  `BLOCKED` result (non-zero CLI exit, real `blocked.reason`) instead of an unconditional
  `OK`, routed through the existing `_emit_command_result`/`_exit_for_command_result`
  machinery. Documented FR7: `PipelineStep` gained an additive-optional
  `extra_allowed_paths` field and a new repeatable `--write-scope PATH` CLI option on
  `implement`/`pipeline`; `_scope` computes the `implement` step's `allowed_paths` as the
  union of the handoff-dir glob and `extra_allowed_paths` — review steps
  (`review_qa`/`review_security`/`review_code`) stay handoff-only, never gaining
  production write rights. Documented FR8: the `_blocked_result`'s
  `not result.artifact_refs` branch now enriches `detail` with a
  `validated_handoff_path` key when a matching, independently-validating handoff file
  exists on disk — observability only, never converts a block into a pass.
- `specs/memory/quality-assurance.md` — **primary.** Recorded the executed-path lesson
  as a durable law addition: (1) a test whose only assertion on a block/failure reason is
  loose/truthy can be satisfied by an unrelated real failure and is a **false positive**
  even though it reports green (the pi CLI-level test precedent); (2) a subprocess-runner
  keyword default (`runner: Runner = subprocess.run`) is bound **once at
  class-definition/import time** — a `monkeypatch.setattr` on the module attribute after
  that point never reaches an already-constructed instance's bound default, so tests
  needing to fake that seam must inject the fake explicitly at construction time (or
  patch the factory that constructs the adapter), never rely on a post-hoc module-level
  monkeypatch of a class-default-bound callable. Refreshed the live-scale bracket: suite
  collects 4970 passed + 18 skipped as of v0.1.66 (up from 4941+18 at v0.1.65).
- `specs/memory/architecture.md` — **no change: assessed.** No new cross-layer import
  edge (verified in PLAN.md's import-linter safety table and re-confirmed by QA's
  `lint-imports` 9 kept / 0 broken); every touched module stayed within its existing
  layer. No structural design change to record.
- `specs/memory/tech-stack.md` — **no change: assessed.** No new dependency, no
  language/runtime version change. The `moonshotai/kimi-k2.5` model-id correction and the
  `pi --list-models`/`codex exec --help` real-binary facts are per-harness truth,
  recorded in `harness-pi.md`/`harness-codex.md` rather than duplicated here (tech-stack
  §Agent runtimes already points to those atoms as the per-runtime source; no update
  needed there since the section states the model set lives in the harness atoms, not
  inline).
- `specs/memory/product/catalog.json` — PM regen (`dadaia memory catalog generate`)
  picks up the `harness-pi` tldr delta.

## Dispositions

Disposition sweep per the ADR-11 vocabulary. This is a **bug-driven** release — no
backlog item was picked or superseded, so there is no consumed-backlog ledger. All 7
target bugs already carry `resolved --release v0.1.66` terminal events (appended during
implementation, per task). The 2 bugs discovered mid-release are **left open** as
next-pick debt — not dispositioned by this release.

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `pi-headless-nonzero-exit-misreported` (`specs/bugs/20260708T15Z-00.jsonl`) | bug HIGH | `resolved --release v0.1.66` | FR1, T-66-04, AC1(repro) |
| `lifecycle-agent-run-result-extraction-too-strict` (`specs/bugs/20260708T15Z-00.jsonl`) | bug HIGH | `resolved --release v0.1.66` | FR2, T-66-05, AC2(repro) |
| `pi-openrouter-kimi-profile-invalid-model-id` (`specs/bugs/20260708T15Z-00.jsonl`) | bug HIGH | `resolved --release v0.1.66` | FR3, T-66-01, AC3(repro) |
| `codex-exec-adapter-missing-skip-git-repo-check` (`specs/bugs/20260708T15Z-00.jsonl`) | bug HIGH | `resolved --release v0.1.66` | FR4, T-66-02, AC4(repro) |
| `codex-exec-sandbox-default-fails-in-container` (`specs/bugs/20260708T15Z-00.jsonl`) | bug HIGH | `resolved --release v0.1.66` | FR5, T-66-03, AC5(repro) |
| `lifecycle-resume-reports-ok-without-advancing` (`specs/bugs/20260708T15Z-00.jsonl`) | bug MEDIUM | `resolved --release v0.1.66` | FR6, T-66-07, AC6(repro) |
| `lifecycle-implement-step-write-scope-too-narrow` (`specs/bugs/20260708T15Z-00.jsonl`) | bug MEDIUM | `resolved --release v0.1.66` | FR7, T-66-08, AC7(repro) |
| `pi-executed-path-cli-tests-invoke-real-pi-binary` (`specs/bugs/20260708T15Z-00.jsonl`) | bug MEDIUM | **OPEN** (no terminal event — next-pick debt) | discovered T-66-01; routed around per-task, not fixed; see Drift `pi-codex-adapter-subprocess-default-binding-false-positive` |
| `pi-e2e-test-false-positive-loose-blocked-reason-assertion` (`specs/bugs/20260708T15Z-00.jsonl`) | bug HIGH | **OPEN** (no terminal event — next-pick debt) | discovered T-66-05; routed around per-task, not fixed; see Drift `pi-codex-adapter-subprocess-default-binding-false-positive` |

No consumed-backlog ledger — this release consumed no backlog item.

## Backlog returns

None filed by this closure. The two open next-pick bugs above are tracked via the bug
ledger itself (event-sourced JSONL), not duplicated into `backlog/`. The
`lifecycle-tasks-md-write-set-parser`, `lifecycle-resume-redrive-blocked-step`, and
`codex-exec-sandbox-capability-probe` forward pointers named in SPEC.md's "Out of scope"
section remain future backlog candidates, unfiled by this closure (assessed: not yet
prioritized against the open-bug debt above).

## Deviations

**None.** This release touched no plugin-domain surface and required no uninstalled
plugin pack.

## Archive decision

**MOVE** — `specs/releases/v0.1.66/` moves to `specs/_archive/releases/v0.1.66/` via
`git mv` (PM/operator; PE issues no git mutations and runs no shell). PM then executes,
in order:

1. `dadaia memory catalog generate` (**required** — `tldr` changed on `harness-pi`).
2. `dadaia specs doctor` + `dadaia backlog doctor` (both must exit 0).
3. the release-dir `git mv specs/releases/v0.1.66 specs/_archive/releases/v0.1.66`.
4. advance `ACTIVE.md` → `release: none`, `phase: none`, noting the next-pick debt: the
   2 open bugs above (`pi-executed-path-cli-tests-invoke-real-pi-binary`,
   `pi-e2e-test-false-positive-loose-blocked-reason-assertion`) plus the carried-forward
   `dispatch-band-legacy-fallback-removal`, `platform-seam-todo-retirement`,
   `specs-doctor-partial-archive-invariant` (unchanged by this release).

**Order law honored:** the memory rebase lands BEFORE `ACTIVE.md` leaves CLOSURE; the
catalog regen (step 1) runs BEFORE the `ACTIVE.md` advance (step 4).
