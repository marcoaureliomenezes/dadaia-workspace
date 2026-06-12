# Closure: Release — v0.1.14

> **Status:** Aprovado
> **Release ID:** v0.1.14 — Deterministic Lifecycle Kernel
> **Owner:** product-engineer
> **Closed:** 2026-06-12

## Summary

v0.1.14 re-architected the lifecycle kernel around one concurrency invariant (N ADDITIVE
/ 1 MUTATING per Spec Context) with a binding zero-false-block requirement (ADR-G1).
Enforcement moved to deterministic **git chokepoints**: a pre-commit lease gate (DP-4
holder-identity chain via the new read-only `ProcessAncestry` port) and a mechanical
pre-push security-verdict gate (`security-reviewer` APPROVE with `metrics.commit_sha`
per pushed sha) — both harness-independent, covering headless Codex. Context injection
became strictly **bind-driven** (bind-epoch marker; first-ALIVE deleted from injection).
A narrow **venv guard** blocks mis-rooted `dadaia`/`pip`/`python -m dadaia_workspace`
Bash invocations. Hooks consolidated into ONE PreToolUse entrypoint (`pre_gate`,
root-whitelist → venv-guard → SDD, first-block-wins) with same-CAS by-session heartbeat
index, `core/kernel_tunables.py` single home, and hook-latency telemetry. Law docs
(constitution §8/§11, workspace-protocol, release-governance) were updated in the same
release; the alpha-N/trio-at-rc-push model is abolished per G6-as-amended (full gate
ladder codification deferred to v0.1.15).

## Tasks completed

All 22 tasks (TG-1..TG-7) are `[x]` in TASKS.md. Commit attribution per task group
follows the implementation ledger in the PM dispatch briefing (branch `feature/v0.1.14`):

| Task group | Tasks | Evidence commit |
|---|---|---|
| TG-1 — W4 substrate (tunables, `pre_gate`, multi-file patch, telemetry, wiring) | T-014-01..05 | `bd6a1f7` |
| TG-2 — W4 lease correctness (`ProcessAncestry`, same-CAS index, release-drops-lease) | T-014-06..08 | `15723f6` |
| TG-3 — W2 bind-driven injection (bind-epoch, ctx_inject rewrite, seed-3 e2e) | T-014-09..11 | `f94e953` |
| TG-4 — W3 venv guard + doctor VENV-1 | T-014-12..13 | `45254ed` |
| TG-5 — W1 chokepoints (pre-commit lease gate, push verdict gate, reconciler) | T-014-14..16 | `2e33b9e` |
| TG-6 — W5 law/docs/personas/backlog | T-014-17..20 | `b08a4a3` |
| TG-7 — Projection + final verification | T-014-21..22 | `a3d6f74` + `0bce563` |
| Gate-remediation fixes (TG-1/3/5 REJECT → fix cycles) | — | `4134f45`, `851533d`, `9036a4c` |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Full test suite green (incl. lease regression canon, seeds 1–5 e2e) | `.dadaia/.venv/bin/python -m pytest -p no:cacheprovider` | `3148 passed, 0 failed, 10 skipped` |
| SDD structure + ledger invariants (incl. SPEC-DOC-029/031/032) | `dadaia specs doctor` | `0 ERROR` |
| Projection chain consistent, privacy clean | `dadaia public doctor` | exit 0 incl. `[ok] public-privacy` |
| PR #56 CI (3-OS matrix + lint + contract jobs) | `gh pr checks 56` | `16 pass / 2 skip` |
| Push boundary mechanically gated (seed 2) | pre-push hook → `dadaia ci push-gate-check` | push of `feature/v0.1.14` flowed only under an APPROVED security-reviewer handoff matching the pushed sha (gate history below) |
| Hook-latency telemetry live (seed-5 dynamic proof) | inspect `.dadaia/logs/hook-latency.jsonl` | one `{ts, hook, event, duration_ms}` record per `pre_gate` invocation on the live instance |

## Gate history

- **TG-1, TG-3, TG-5:** qa gate returned **REJECT** on first pass; each was fixed and
  re-gated to **APPROVE** (fix commits `4134f45`, `851533d`, `9036a4c`). The TG-5 cycle
  included a **live-reproduced ADR-G1 false block** (the legitimate holder was blocked by
  the new chokepoint) — root-caused and fixed before APPROVE; the zero-false-block
  binding requirement held at closure.
- **TG-7:** gated **post-hoc** — projection/verification ran before its gate verdict was
  recorded; the gate then passed on the as-built state. Recorded as a process deviation,
  not a quality gap.
- **SE self-commit deviation (MEDIUM):** software-engineer committed work directly
  during implementation instead of routing through the PM-coordinated commit step.
  Outcome unaffected (all gates green); recorded for the v0.1.15 governance sweep.

## Drifts

### package-version-vs-release-id

**Description:** The PyPI package version remains `0.1.6` while the internal release id
is `v0.1.14` — internal release cadence outpaced published versions.

**Resolution:** Deliberate operator guardrail: no version bump or PyPI publish without
explicit operator approval (release cadence law). The internal id is the SDD ledger key;
the package version is a separate, operator-gated artifact.

**Memory updates:** none — versioning policy lives in release-governance, not memory.

### tg-gate-reject-cycles

**Description:** TG-1/3/5 did not pass their qa gate first-pass (see Gate history),
including one reproduced ADR-G1 false block.

**Resolution:** Fix-and-re-gate cycles to APPROVE; the false-block repro became a
regression test. No spec change required.

**Memory updates:** none beyond the planned atoms (the shipped behavior matches SPEC).

## Memory updates

- `specs/memory/architecture.md` — merged `pre_gate` hook package, chokepoint envelope,
  v0.1.14 lease model (by-session index, `context release`, bind-epoch), multi-harness
  enforcement matrix, runtime-state list (`bind_epoch/`, `ctx_locks/by-session/`,
  `hook-latency.jsonl`), contracts table (chokepoints row + `kernel_tunables`
  import-linter leaf contract).
- `specs/memory/product/sdd/sdd-gate-v3.md` — full rewrite to the two-layer model
  (merged `pre_gate` + git chokepoints), DP-4/DP-5 chains, by-session heartbeat,
  per-harness enforcement matrix.
- `specs/memory/product/platform/context-management.md` — bind-epoch marker, bind-driven
  injection, `context release` drops lease, by-session index, kernel_tunables.
- `specs/memory/product/platform/workspace-init.md` — single PreToolUse command
  (`pre_gate`), 8-module hooks package, chokepoints installed via `dadaia ci install-hook`.
- `specs/memory/product/platform/workspace-doctor.md` — VENV-1 check added; LOCK-GC /
  SENTINEL-GC / PTR-GC current semantics.
- `specs/memory/product/platform/multi-platform-parity.md` — headless Codex
  "chokepoints only", OpenCode "advisory + chokepoint-protected" (ADR-G3), single
  PreToolUse hook entry, rules count corrected to 8; `release_origin` → v0.1.14.
- `specs/memory/product/philosophy/spec-context-project.md` — bind/enforce steps updated
  to bind-epoch + `pre_gate` + chokepoints; removed the false "gate checks `[-]` markers"
  claim.
- `specs/memory/product/sdd/sdd-bug-backlog-governance.md` — review cadence rewritten to
  G6-as-amended (trio-at-rc-push abolished; mechanical security push gate; qa/code-review
  remain PM discipline until v0.1.15); pre-push gate section gains `push-gate-check`.
- `specs/memory/product/index.md` — catalog tldr lines synced for the touched atoms.
- `specs/memory/tech-stack.md` — no change: release added no external dependency
  (telemetry is stdlib JSONL; mistune et al. unchanged).
- `specs/memory/product/catalog.json` — **regeneration required** (`dadaia memory
  catalog generate`) before the closure commit: tldr/summary mirrors of the touched
  atoms are stale (PE has no shell; PM runs it).

## Dispositions

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/bugs/ctx-inject-ignores-session-bind-first-alive-proxy.md` | bug | `Closed` | TG-3 (`f94e953`); seed-3 e2e regression |
| `specs/bugs/context-release-leaves-lease-heartbeat-renewing.md` | bug | `Closed` | TG-2 (`15723f6`); both-flow repro tests |
| `specs/bugs/sdd-gate-apply-patch-multi-file-first-header-only.md` | bug | `Closed` | TG-1 (`bd6a1f7`); most-restrictive-verdict matrix |
| `specs/bugs/codex-exec-hooks-do-not-fire-headless.md` | bug | `Closed` (per its option (b) + chokepoints) | TG-5 (`2e33b9e`) + §8 enforcement matrix (TG-6 `b08a4a3`); harness-independence e2e |
| `specs/bugs/bug-guardrail-template-omits-required-session-id.md` | bug | `Closed` | TG-6 (`b08a4a3`); post-stage contract test |
| `specs/bugs/agents-md-instructs-html-report-validation-unsupported.md` | bug | `Closed` (duplicate) | Sanitization — duplicate of `reports-validate-rejects-html-despite-agents-md-contract` (which stays Open, not picked) |
| `specs/backlog/deterministic-lifecycle-kernel-v0114.md` | backlog | `DELIVERED — v0.1.14` | PR #56; this CLOSURE |
| `specs/backlog/lease-shell-write-coverage-gap.md` | backlog | `SUPERSEDED — deterministic-lifecycle-kernel-v0114` | Chokepoint architecture (ADR-G2) |
| `specs/backlog/harness-agentic-entities-and-determinism-parity.md` | backlog | stays OPEN — narrowed (ADR-G3 note + shipped-note recorded) | Enforcement-parity statement + chokepoint half delivered by W1/W5; remaining scope: identity propagation / OpenCode plugin shim |

## Backlog returns — deferred to v0.1.15

Discovered during implementation/review; out of this release's scope. All routed to the
v0.1.15 governance sweep (`specs/backlog/sdd-governance-v2-agents-lifecycle.md`) or
carried as review findings:

- `bind_epoch` marker refresh via `touch`/`os.utime` instead of rewrite — LOW.
- `venv_guard` corrected-command construction should use `shlex.join` — LOW.
- `pid_probe=None` conservatism in one lease call-path (falls back TTL-only more often
  than necessary) — MEDIUM.
- Residual trio/first-ALIVE wording in `dadaia-task-manager`, `dadaia-release-closure`,
  `project-orchestration` skills + `project-manager`/`product-engineer` personas +
  `release-ship` workflow — v0.1.15 governance sweep (law docs and memory are already
  clean; these are public-asset wording residues).

## Archive decision

**MOVE** — `git mv specs/releases/v0.1.14 specs/_archive/releases/v0.1.14` (executed by
PM after this CLOSURE lands; PE has no shell). `ACTIVE.md` set to `release: none`.

**Package-version note:** internal release id `v0.1.14`; published PyPI version remains
`0.1.6` — bump/publish is operator-gated (see Drifts).
