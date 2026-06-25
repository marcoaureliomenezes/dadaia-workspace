# Closure: Release — pi-fourth-harness-v1

> **Status:** Aprovado
> **Release ID:** pi-fourth-harness-v1
> **Owner:** product-engineer
> **Closed:** 2026-06-25

## Summary

pi-fourth-harness-v1 makes PI (`@earendil-works/pi-coding-agent`) a **live, fully-supported
fourth second-layer harness** — peer to Claude Code, Codex, and OpenCode — selectable per
lifecycle step via `--harness pi` and `--step-harness x=pi` across every `dadaia lifecycle`
verb. From the product owner's view: the engine now drives bounded PI workers behind the same
`AgentRuntimePort` the other three harnesses sit behind, with a deterministic typed result and
a trustworthy write boundary, and a `claude implements / pi reviews` per-step mix is now a
plain adapter swap.

The release delivers the highest-confidence core of the `pi-agent-fourth-harness` EPIC —
**WS-PI-1 (the second-layer adapter) + WS-PI-2 (the result-extraction contract + real
`changed_paths`)**. PI is added as a clean adapter: `AgentRuntimeKind.PI_HEADLESS`, the
`PiHeadlessAdapter` (a structural twin of `CodexExecAdapter` driving `pi --mode json` over an
injectable subprocess runner, offline-first with no PI client imported at module load), a
total-factory `build_agent_runtime` branch, and one CLI harness-map entry. The PI write
boundary is **real**: `changed_paths` is computed from the injected git client's
`diff_name_only(cwd)`, unconditionally overwriting any model self-report, so the engine's
Ring-2 out-of-scope block actually fires for PI exactly as for Codex/OpenCode.

The release is intentionally a bounded slice. Zero engine-spine files changed
(`core/scope_match.py`, `features/lifecycle/{agent_runner,phase_workflow,pipeline}.py` are
untouched). The first-layer `.pi/` projection (WS-PI-3), the Ring-1 `.pi/` pre-disk gate
(WS-PI-4), pi-workspace retirement (WS-PI-5), telemetry (WS-PI-6), and the `--mode rpc`/TS-SDK
transports remain deferred (see Backlog returns).

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| (release definition) | Define release pi-fourth-harness-v1 (SPEC/PLAN/TASKS, grill) | `3940e8e` |
| T-PI-01 | Enum: add `AgentRuntimeKind.PI_HEADLESS` member + round-trip coverage | `a8a3e0c` |
| T-PI-02 | Adapter (minimal parser): `PiHeadlessAdapter` + `PiHeadlessConfig` | `a8a3e0c` |
| T-PI-03 | Factory branch `PI_HEADLESS` in `build_agent_runtime` (total) | `a8a3e0c` |
| T-PI-04 | CLI harness map `"pi" → PI_HEADLESS` (`--harness pi` / `--step-harness x=pi`) | `a8a3e0c` |
| T-PI-05 | Result extraction (WS-PI-2): harden `_result_from_output` (last `message_end`, string/content-block, degraded fallback, schema-gated verdict) | `a8a3e0c` |
| T-PI-06 | `changed_paths` via git `diff_name_only` (Ring-2 root-cause) + end-to-end block test | `a8a3e0c` |
| T-PI-07 | Live-`pi` integration seam (opt-in `DADAIA_PI_LIVE=1`, not CI-gated) | `a8a3e0c` |
| T-PI-08 | Full local gate green (preflight 4/4 + lint-imports 6/0) | `a8a3e0c` |
| T-PI-09 | CLOSURE (this document) + memory atoms | this closure |

> Note: T-PI-01..T-PI-08 were delivered in a single implementation commit `a8a3e0c`; the
> release range is `9de9c08..a8a3e0c`.

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Format + lint + strict-type + tests (4 checks) | `/home/marco/workspace/dadaia/.dadaia/.venv/bin/dadaia ci preflight` | ```text
ruff format --check PASS; ruff check PASS; mypy --strict PASS; pytest PASS (4/4)
``` |
| Architecture contracts (layering) | `/home/marco/workspace/dadaia/.dadaia/.venv/bin/lint-imports` | ```text
Contracts: 6 kept, 0 broken.
``` |
| PI test subset | `/home/marco/workspace/dadaia/.dadaia/.venv/bin/python -m pytest -p no:cacheprovider tests/unit/infrastructure/test_pi_runtime.py tests/unit/core/test_agent_runtime_kind.py tests/unit/test_build_agent_runtime.py tests/integration/pi_live` | ```text
39 passed, 1 skipped
``` (the 1 skip = opt-in `DADAIA_PI_LIVE=1` live contract test) |
| Targeted security suite run | (security-reviewer push-gate run) | ```text
64 passed / 64
``` |
| Push: feature branch pushed at HEAD | `git push origin feature/pi-fourth-harness-v1` | `a8a3e0c` — pre-push CI gate + security-verdict gate both PASSED |
| CI (GitHub Actions): all jobs green for `a8a3e0c` | GitHub Actions for `a8a3e0c` | 15/15 jobs success (incl. Windows + macOS legs + Dual-approval verdict gate); 2 conditional jobs skipped (hotfix-SemVer, PR-title) |
| QA gate | qa-engineer APPROVE handoff | `.dadaia/handoff/dadaia-workspace/2026-06-25T053911Z-qa-engineer-pi-fourth-harness-v1-gate.handoff.json` |
| Security verdict (push gate) | security-reviewer APPROVE handoff | `.dadaia/handoff/dadaia-workspace/2026-06-25...-security-reviewer-pi-fourth-harness-v1-pushgate.handoff.json` — `metrics.commit_sha = a8a3e0c`, 0 findings |

## Drifts

### ac6-baseline-snapshot-vs-result-time-diff

**Description:** TASKS AC6 wording says the adapter "snapshots a git baseline before spawn"
and computes the post-run diff. The implementation instead computes `changed_paths` via
`diff_name_only(cwd)` at result time — the union of working-tree + staged + untracked
(non-ignored) files — rather than diffing against a captured pre-spawn baseline. This is an
equivalent-or-stronger write-boundary signal (it captures every path the worker touched,
including new untracked files, without depending on a clean pre-run tree), and it still feeds
the exact `structured_output["changed_paths"]` field the Ring-2 runner splits on. The
acceptance intent — `changed_paths` sourced from git, never a model self-report, with the
Ring-2 block demonstrably firing on an out-of-scope set — is fully met.

**Resolution:** Accepted; the implemented result-time `diff_name_only` union is recorded as
the truth. The model self-report is unconditionally overwritten regardless.

**Memory updates:** `specs/memory/product/sdd/lifecycle-foundation.md` (PI Ring-2 boundary
described as result-time git-diff `changed_paths`); `specs/memory/architecture.md`
(`git_subprocess.GitSubprocessClient.diff_name_only` recorded as the new git surface).

### non-zero-exit-with-valid-terminal-message-succeeds

**Description:** When `pi` exits non-zero but the JSONL stream still carries a valid terminal
`message_end` event, the adapter maps the run to **SUCCEEDED** — the terminal assistant
message is trusted over the raw process exit code (deliberate precedence). Downstream gates
(the runner's verdict gate + Ring-2 `changed_paths` classification + the git chokepoints) are
unaffected and still apply.

**Resolution:** Accepted as a deliberate precedence rule, documented here and in memory. It
mirrors the robustness-over-strictness posture of the degraded fallback: a usable terminal
result is not discarded because of a noisy exit code, and the real write/verdict boundaries
remain downstream.

**Memory updates:** `specs/memory/product/sdd/lifecycle-foundation.md` (PI result mapping:
valid terminal `message_end` ⇒ SUCCEEDED even on non-zero exit; downstream gates still apply).

## Memory updates

- `specs/memory/product/sdd/lifecycle-foundation.md` — harness inventory extended to FOUR
  runtime kinds (FAKE, CODEX_EXEC, CLAUDE_SDK, OPENCODE_RUN, **PI_HEADLESS**); PI driven
  headless via `pi --mode json` (subprocess, offline-first, injectable runner, no PI client at
  module load); PI Ring-2 write boundary from result-time git-diff `changed_paths` (never a
  model self-report); terminal-`message_end`-over-exit-code precedence; PI Ring-1 (`.pi/`
  extension) + first-layer `.pi/` projection recorded as deferred (WS-PI-3/4).
- `specs/memory/architecture.md` — added `infrastructure/pi_runtime.py`
  (`PiHeadlessAdapter`/`PiHeadlessConfig`) to the agent-runtime adapter inventory behind
  `AgentRuntimePort`; added `PI_HEADLESS` to the `build_agent_runtime` factory enumeration;
  noted `GitSubprocessClient.diff_name_only` as the new git surface.
- `specs/memory/tech-stack.md` — recorded `pi` / `@earendil-works/pi-coding-agent` as an
  OPTIONAL operator-installed external CLI runtime (Node + `ANTHROPIC_API_KEY`), invoked as an
  external binary, never a pinned Python/Node dependency (offline-first preserved); recorded
  that the live `pi --mode json` event schema is the one unverified seam, verified via the
  `DADAIA_PI_LIVE=1` opt-in integration test, and that the exact verified `pi` version must be
  captured the first time the live seam runs in a networked env (not pinnable offline now).
- `specs/memory/product/index.md` and `specs/memory/product/catalog.json` — **NOT
  hand-edited**; the coordinator regenerates the catalog (`generate-memory-catalog.py`) after
  this closure. No new feature atom is added (PI is a fourth value of the existing
  `lifecycle-foundation` harness-selection surface), so the catalog set is unchanged.

## Dispositions

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/backlog/pi-agent-fourth-harness.md` | backlog (EPIC) | `PARTIALLY CONSUMED — pi-fourth-harness-v1` | Delivered WS-PI-1 + WS-PI-2 (commit `a8a3e0c`); WS-PI-3/4/5/6 + RPC/SDK transports deferred (see Backlog returns). Left in place for PM re-curation. |
| `specs/backlog/adr-pi-headless-vs-rpc.md` | backlog (ADR) | Left in place as the binding decision record | Cited from SPEC (`Decision 1`: `pi --mode json` headless; `Decision 2`: Ring-2-now/Ring-1-later, `changed_paths` from git diff). Not consumed/closed — it is a durable decision record. |

No bugs were picked into this release (none referenced the PI surface).

## Backlog returns

The EPIC `specs/backlog/pi-agent-fourth-harness.md` is **PARTIALLY CONSUMED**; the following
remaining scope is deferred and left in the EPIC for PM re-curation (do not close the EPIC):

- `backlog/candidates.md` ← WS-PI-3: first-layer `.pi/` projection target (`public/pi/`,
  `dadaia public install --target pi`, doctor PI drift checks).
- `backlog/candidates.md` ← WS-PI-4: Ring-1 `.pi/extensions/dadaia-sdd-gate.ts` pre-disk
  `tool_call` gate (post-trust; High risk; Ring-2 + chokepoints are the backstop).
- `backlog/candidates.md` ← WS-PI-5: absorb/retire `dadaia-pi-workspace` (curation; salvage
  its specs, DEAD-mark the context, never delete the repo).
- `backlog/candidates.md` ← WS-PI-6: telemetry adapter + academy doc — only if a real local PI
  session source exists (anti-slop: no placeholder telemetry).
- `backlog/candidates.md` ← `pi --mode rpc` transport + the TypeScript SDK in-process path —
  rejected for the primary path per ADR Decision 1; deferred behind a concrete future need.
- `backlog/candidates.md` ← Live `pi --mode json` schema verification: on first networked
  install with `ANTHROPIC_API_KEY` + Node `pi`, run the `DADAIA_PI_LIVE=1` seam, confirm the
  `AgentMessage.content` shape (string vs content-block array), and record the verified `pi`
  version pin into `tech-stack.md`.

## Archive decision

**MOVE** — the release directory will be moved to
`specs/_archive/releases/pi-fourth-harness-v1/` via `git mv`, and
`specs/releases/ACTIVE.md` reset to `release: none` / `phase: none`. The coordinator executes
the `git mv` and the `ACTIVE.md` reset (and regenerates `product/index.md` + `catalog.json`)
after this closure; product-engineer does not run git or archive.
