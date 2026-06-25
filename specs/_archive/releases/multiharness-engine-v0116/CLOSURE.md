# Closure: Release — multiharness-engine-v0116

> **Status:** Aprovado
> **Release ID:** multiharness-engine-v0116
> **Owner:** product-engineer
> **Closed:** 2026-06-25

## Summary

multiharness-engine-v0116 turns the half-wired lifecycle spine into a working
**multi-harness procedural lifecycle engine**. A thin entry harness (Claude Code,
Codex, or OpenCode) now calls `dadaia lifecycle` CLI verbs that run procedural Python
workflows; those workflows drive bounded agent workers behind `AgentRuntimePort`, with
the harness selectable per step. The release lands the per-step harness-selection spine
(four runtime kinds + a `build_agent_runtime` factory + adapters), wires every
single-step verb and a multi-step pipeline onto the engine, retires the reference-only
markdown-orchestrate dispatch layer that spawned nothing, and adds the engine's own
anti-slop self-governance (a directory-aware slop metric and a boundary-safe retention
sweep).

From the product owner's view: the workspace now has ONE procedural engine for the SDD
lifecycle instead of two non-converged systems. The headline capability is a single
`LifecyclePipeline` run that threads one `LifecycleRun` through
IMPLEMENTATION→QA→SECURITY→CODE→CLOSURE, each step running on its own declared harness
(claude-implements / codex-reviews mixing is a per-step adapter swap), stopping at the
first blocked gate. The Claude Agent SDK adapter ships with a real Ring-1 write boundary
derived from the same path classifier the runner's Ring-2 uses; `claude-agent-sdk`
remains an optional, operator-installed runtime extra so the build stays offline-first.

The release is intentionally a bounded slice of the EPIC: it delivers WS-1/WS-3/WS-4/
WS-6/WS-7 plus D5 and a reversible bounded subset of D12. Live Claude SDK binding
verification, phase-specific gate refinement, the full AI-surface collapse, and the live
OpenCode adapter remain deferred follow-ups (see Backlog returns).

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-016-00 | Release start: ACTIVE.md → multiharness-engine-v0116 IMPLEMENTATION (restore run-store layer boundary) | `82cc5e3` |
| T-016-01..05 | Runtime kinds (CLAUDE_SDK + OPENCODE_RUN), adapters (OpenCode/Claude SDK stubs), `build_agent_runtime` factory, FAKE integration proof — the per-step harness-selection spine | `f5a52be` |
| T-016-08 | `LifecyclePhaseWorkflow` + review verbs driven by the engine (first engine-driven verb, alpha-2) | `5207b5f` |
| T-016-09 | Every single-step verb runs the engine; dead `unavailable_workflow` stub layer deleted (alpha-3) | `050c9cc` |
| (bug registration) | Register subagent-handoff `.dadaia`-in-repo bug | `8fae7d9` |
| T-016-10 | WS-4: `ClaudeSdkAdapter` with real Ring-1 `write_permission` decider via shared `scope_match`; injectable `query_fn`; `claude-agent-sdk` optional extra | `f53fbf1` |
| T-016-11 | WS-3: retire the reference-only markdown-orchestrate dispatch layer; `.workflow.md` become docs-only; panel intact | `9123b8c` |
| T-016-12 | WS-1 multi-step: `LifecyclePipeline.run` threading one run through the phase ladder, per-step harness mixing | `0fd888d` |
| T-016-13 | WS-6: directory-aware `slop_scan` metric + `dadaia lifecycle slop`; `scope_match` moved to `core/` (lint-imports 6/0) | `7f1253f` |
| T-016-14 | WS-7: cacheable hashed `PromptPrefix` reused per step + per-step model tiers | `a92f373` |
| T-016-15 | D5: `RetentionSweep` (dry-run default, hard liveness gate, symlink-safe) + `dadaia lifecycle clean` | `290bee9` |
| T-016-16 | D12: trim engine-owned ordered mechanics out of 3 skills, keep identity/judgment (−92 lines) | `2fae946` |
| T-016-06 | Full local gate green (ruff/mypy --strict/pytest); QA review handoff recorded | satisfied throughout |
| T-016-07 | CLOSURE (this document) | this closure |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Formatting + lint (4 checks via preflight) | `/home/marco/workspace/dadaia/.dadaia/.venv/bin/dadaia ci preflight` | ```text
ruff format --check PASS; ruff check PASS; mypy --strict PASS; pytest PASS
``` |
| Production strict typing | `/home/marco/workspace/dadaia/.dadaia/.venv/bin/python -m mypy --strict dadaia_workspace` | ```text
Success: no issues found
``` |
| Full test suite | `/home/marco/workspace/dadaia/.dadaia/.venv/bin/python -m pytest -p no:cacheprovider` | ```text
3320 tests collected — PASS
``` |
| Architecture contracts | `/home/marco/workspace/dadaia/.dadaia/.venv/bin/lint-imports` | ```text
Contracts: 6 kept, 0 broken.
``` |
| Specs doctor | `/home/marco/workspace/dadaia/.dadaia/.venv/bin/dadaia specs doctor --specs-dir specs --json` | ```text
"summary": {"errors": 0, "warnings": 22}
``` |
| Public projection doctor | `/home/marco/workspace/dadaia/.dadaia/.venv/bin/dadaia public doctor` | ```text
[ok] public-privacy
[ok] model-resolution
(exit 0)
``` |
| Docs-only `.workflow.md` projection re-staged/installed | `dadaia public stage && dadaia public install --target all && dadaia public doctor` | `[ok]` (WS-3 follow-up) |
| Push: feature branch pushed at HEAD | `git push origin feature/v0.1.16` | `2fae946` — pre-push CI gate + security-verdict gate both PASSED |
| Security verdict (push gate) | security-reviewer APPROVE handoff | `.dadaia/handoff/dadaia-workspace/2026-06-25T035422Z-security-reviewer-multiharness-v0116-pushgate.handoff.json` — `metrics.commit_sha = 2fae946`, 0 HIGH/CRITICAL |

## Drifts

### scope-match-layering-break-moved-to-core

**Description:** WS-4 (T-016-10) created the shared Ring-1/Ring-2 matcher as
`features/lifecycle/scope_match.py` and imported it from
`infrastructure/claude_sdk_runtime.py`. That is an illegal upward layering edge
(`infrastructure → features`), caught by `lint-imports` (the `infrastructure-no-upper-layers`
contract) — invisible to `dadaia ci preflight`, which does not run `lint-imports`. Filed as
bug `infrastructure-claude-sdk-imports-features-scope-match`.

**Resolution:** `scope_match` is a pure function with no dependencies, so it was relocated
`features/lifecycle/scope_match.py → core/scope_match.py` (the correct layer — both
`features/` and `infrastructure/` may import `core/`) within T-016-13. `lint-imports` now
reports 6 kept / 0 broken. The TASKS.md write-set for T-016-10 still names the original
`features/lifecycle/scope_match.py` path; current truth is `core/scope_match.py`.

**Memory updates:** `specs/memory/architecture.md` (features/infrastructure inventory now
lists `core/scope_match.py`), `specs/memory/product/sdd/lifecycle-foundation.md` (one shared
classifier, two boundaries).

### candidates-md-tracked-file-hygiene

**Description:** `specs/backlog/candidates.md` was git-tracked (committed in `824c290`,
re-touched in the v0.1.15 closure), violating the `.gitignore:98` `/specs/*` policy that
intends non-canonical backlog scratch content to stay local. The hygiene contract
(`tests/contract/test_source_repo_hygiene.py`) failed, which blocked this release's pre-push
CI gate. Filed as bug `backlog-candidates-md-tracked-violates-noncanonical-gitignore`.

**Resolution:** `git rm --cached specs/backlog/candidates.md` (untracked; file kept on disk).
It now matches the ignore policy and both hygiene contracts pass. Pre-existing defect,
unrelated to engine work, fixed here only because it blocked the push.

**Memory updates:** None — repo hygiene, not product truth.

### uniform-approved-verdict-gate-simplification

**Description:** The runner applies a uniform APPROVED-verdict gate to every phase, so
non-review phases (implement/define) also require the worker to emit an APPROVED handoff.
Phase-specific gating (e.g. implement needs evidence, not self-approval) is the correct
target but was not implemented this release.

**Resolution:** Accepted as a tracked simplification — recorded in TASKS.md (T-016-09 known
simplification) and carried to Backlog returns as a deferred runner refinement. No code was
weakened; the gate is real, just uniform.

**Memory updates:** `specs/memory/product/sdd/lifecycle-foundation.md` notes the uniform
APPROVED-verdict gate as current behavior with the refinement deferred.

### orchestrate-dispatch-layer-retired

**Description:** PLAN assumed the reference-only `dadaia orchestrate` dispatch layer (four
`AgentDispatcher`s that spawned nothing + the orchestrate execution path) would be retired by
WS-3. Reality matched, but it required deleting `core/protocols/agent_dispatcher.py`,
`infrastructure/{claude,cli,codex}_agent_dispatcher.py`, and
`features/orchestration/{runner,resolver}.py`, plus migrating ~60 tests — a larger surface
than the PLAN line implied. `dadaia orchestrate run <wf>` now exits 0 steering to
`dadaia lifecycle`; `.workflow.md` are docs-only; the panel was verified intact.

**Resolution:** Completed in T-016-11; the docs-only `.workflow.md` projection was
re-staged/installed and `dadaia public doctor` reports `[ok]`.

**Memory updates:** `specs/memory/architecture.md` — the infrastructure inventory no longer
lists `claude_agent_dispatcher`/`cli_agent_dispatcher`; the orchestrate dispatch path is
recorded as retired (read-only listing only).

### live-claude-sdk-binding-unverified

**Description:** The exact `claude-agent-sdk` `query()`/`can_use_tool` binding in
`_default_query_fn` could not be live-verified — this is an offline, lock-pinned build with no
network, and `claude-agent-sdk` is an optional extra that is not installed. All
engine-depended logic (the Ring-1 write-permission decider + result mapping) is real and
tested via an injected `query_fn`; only the single SDK call line is unverified.

**Resolution:** Isolated the unverified binding in `_default_query_fn` with an actionable
`pip install claude-agent-sdk` message when the package is absent; carried to Backlog returns
as a first-networked-install verification follow-up.

**Memory updates:** `specs/memory/tech-stack.md` records `claude-agent-sdk` as an optional,
operator-installed runtime extra (lazy-imported, not locked).

## Memory updates

- `specs/memory/product/sdd/lifecycle-foundation.md` — extended to current truth: the engine
  is now multi-harness (4 `AgentRuntimeKind` + `build_agent_runtime` factory + four adapters),
  single-step verbs plus the multi-step `LifecyclePipeline` with per-step harness mixing,
  Ring-1 Claude write boundary via the shared `core/scope_match` classifier, cacheable hashed
  `PromptPrefix` + per-step model tiers, directory-aware slop metric, and boundary-safe
  retention sweep. Kept atomic (current product state, no changelog).
- `specs/memory/architecture.md` — updated the CLI/features/infrastructure inventory: new
  `features/lifecycle/{pipeline,phase_workflow,prompt_builder}.py` and
  `features/lifecycle/antislop/{slop_scan,retention}.py`; `core/scope_match.py` (moved from
  features); new `infrastructure/{opencode_runtime,claude_sdk_runtime}.py`; the orchestrate
  dispatch layer (`agent_dispatcher` protocol + the three dispatcher adapters +
  orchestration runner/resolver) recorded as retired.
- `specs/memory/tech-stack.md` — recorded `claude-agent-sdk` as an OPTIONAL,
  operator-installed runtime extra (NOT a locked/pinned dependency; offline-first build
  preserved; lazy-imported by the Claude SDK adapter).
- `specs/memory/product/index.md` and `specs/memory/product/catalog.json` — NOT hand-edited;
  the coordinator regenerates these with the generator script after this closure.

## Dispositions

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/bugs/infrastructure-claude-sdk-imports-features-scope-match.md` | bug | `Closed` | T-016-13 commit `7f1253f`; `scope_match` moved to `core/`; lint-imports 6/0 (Drift: scope-match-layering-break-moved-to-core) |
| `specs/bugs/backlog-candidates-md-tracked-violates-noncanonical-gitignore.md` | bug | `Closed` | `git rm --cached specs/backlog/candidates.md`; source-repo-hygiene contract green (Drift: candidates-md-tracked-file-hygiene) |
| `specs/bugs/codex-config-emits-invalid-approved-commands.md` | bug | `Open` (carried forward — not fixed this release; deferred cosmetic cleanup) | unchanged frontmatter `status: Open` |
| `specs/bugs/subagent-handoff-resolves-dadaia-inside-repo-cwd.md` | bug | `Open` (carried forward — filed this release, LOW; deferred) | unchanged frontmatter `status: Open` |
| `specs/backlog/sdk-lifecycle-engine-multiharness-antislop.md` | backlog | `PARTIALLY CONSUMED — multiharness-engine-v0116` | Delivered WS-1/WS-3/WS-4/WS-6/WS-7 + D5 + bounded D12; remaining scope deferred (see Backlog returns). Left in place for PM re-curation. |

## Backlog returns

The EPIC `specs/backlog/sdk-lifecycle-engine-multiharness-antislop.md` is **PARTIALLY
CONSUMED**; the following remaining scope is deferred and left in the EPIC for PM
re-curation (do not close the EPIC):

- `backlog/candidates.md` ← Live Claude Agent SDK binding verification (first networked
  install of `claude-agent-sdk`: confirm `query()`/`can_use_tool` in `_default_query_fn`) +
  provider cache-control marker wiring in the live Claude adapter.
- `backlog/candidates.md` ← Phase-specific gate refinement: drop the uniform APPROVED-verdict
  requirement for non-review phases (implement/define need evidence, not self-approval).
- `backlog/candidates.md` ← Full shadow-validated AI-surface collapse (the PARTIAL skills +
  rules + AGENTS.md collapse), once the engine can drive live releases for shadow validation.
- `backlog/candidates.md` ← Rewire legacy `dadaia clean` / `reports cleanup` onto
  `RetentionSweep`; persist explicit per-run tmp working-dir claims in `LifecycleRun` so the
  liveness provider keys on a registered workdir rather than `expected_artifacts`.
- `backlog/candidates.md` ← Live OpenCode `opencode run` adapter (currently a documented stub
  behind the port).
- `backlog/ideas.md` ← Add `lint-imports` to `dadaia ci preflight` so layering breaks are
  caught by the local pre-push gate, not only the CI `lint` job (root cause of the WS-4
  layering break slipping past local validation).

## Archive decision

**MOVE** — the release directory will be moved to
`specs/_archive/releases/multiharness-engine-v0116/` via `git mv`, and
`specs/releases/ACTIVE.md` reset to `release: none` / `phase: none`. The coordinator
executes the `git mv` and the ACTIVE.md reset (and regenerates `product/index.md` +
`catalog.json`) after this closure; product-engineer does not run git or archive.
