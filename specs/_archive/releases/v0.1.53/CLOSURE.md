# Closure: Release — v0.1.53 — Legacy Purge

> **Status:** Aprovado
> **Release ID:** v0.1.53
> **Owner:** product-engineer
> **Closed:** 2026-07-03
> **Branch:** `feature/v0.1.53` · **Base:** `8627fdec` (v0.1.52 closure) · **Merged:** `d3f46360` (PR #95, squash of `feature/v0.1.53`)
> **Ship gates:** qa-engineer **APPROVE** (7/7) · security-reviewer **APPROVE ×2** (r1 `b1147aac` / r2 `83f21a41`) · CI 38 checks, 0 failures.

## Summary

v0.1.53 is the FINAL release of the operator's R1→R5 mandate — the mandate is now
complete. It applies the no-legacy-code law across the surface the R6–R9 refactor chain
must restructure: every inventoried legacy CLI, dead-code, and duplicated-canon target
was DELETED (or centralized/re-tuned/guarded where stated), with per-symbol
caller-verified safety. The `dadaia bug new` Markdown path and the overdue
`dadaia server dashboard` are gone; the inert `features/orchestration` package is retired
(with `dadaia orchestrate list/show` rewired onto `features/workflows` at byte-identical
`--json` output, preserving `gate=<kind>`); the never-reachable panel workflow-launcher
chain, the two never-raised backtrack exceptions, and a large audit-C dead-code inventory
(hook `main()`s, the `lease.LEASE_TTL_SECONDS` re-export, `library_workflow_catalog`,
`views/_assets.py`, `TelemetryService.list_workflows` + its unreachable handler fallback,
the aggregator's shared-`dao` mode) are all deleted. The release SemVer regex is now a
single canon in `core/specs_version.py` guarded by an identity+scan agreement test; the
Windows chmod silent no-op is closed by routing both telemetry chmods through the injected
`FilePermissionSetter`; and 28 `/home/<user>` leaks across 12 tracked bug files are
redacted. This CLOSURE completes the `agent_tier` tolerate-then-strip sequence by removing
the field from all 28 memory atoms that carried it, and records the deprecation-expiry law
this release establishes.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-53-01 | Definition (SPEC/PLAN/TASKS; dual REJECT×2 → amend → `Aprovado`) | definition commit on `feature/v0.1.53` |
| T-53-10 | FR1 — legacy CLI + package retirement (bug-new chain, server dashboard, orchestration retirement + orchestrate rewire, dead exceptions, `_deferred.py`, dead panel launcher chain + orphaned run-state infra) | `9d537d69` (+ collateral `3811dde7`) |
| T-53-11 | FR2 — dead-code sweep (hook `main()`s, `LEASE_TTL_SECONDS` re-export, `library_workflow_catalog` relocation, `_assets.py`, `list_workflows` + handler fallback, shared-`dao` mode, core.js comments) | `5984a79c` (+ collateral `3811dde7`) |
| T-53-12 | FR3 — semver canon + agreement test + `agent_tier` schema-side (tolerate) + `.import_linter_cache` relocation + perf op-count budget | RED `71e187a5` → feat `0cc3cc53` |
| T-53-13 | FR4 — `FilePermissionSetter` chmod routing + posix guard + 28-literal redaction across 12 bug files | `6d6d7891` |
| T-53-20 | W5 ship gate — consumed-backlog archival at ship; qa-engineer APPROVE (7/7) | archival `6c08dd25` |
| T-53-21 | W5 security push gate APPROVE ×2 → push → CI → PR #95 → merge; dev-server-registry SKILL.md fix | r1 `b1147aac` / r2 `83f21a41`; SKILL.md `1e902c14`; merge `d3f46360` |
| T-53-30 | W6 closure — this CLOSURE.md + `agent_tier` atom strip (28) + memory truth updates + catalog/lint + archive | (this commit) |

## Validations

Each row is a triple: description, command, evidence (SHA / stdout snippet / handoff path).

| Description | Command | Evidence |
|-------------|---------|----------|
| Full suite green (unpiped, real exit) | `pytest` (no pipe) | `4322 passed / 17 skipped, exit 0` — QA ship-gate handoff `2026-07-03T051502Z` + orchestrator run |
| Format + lint clean | `ruff format --check` · `ruff check` | clean — QA ship gate |
| Types clean | `mypy --strict` | clean — QA ship gate |
| Projection consistency | `dadaia public stage && install --target all && public doctor` | exit 0 — W3 (`0cc3cc53`) + ship gate |
| AC-1 per-symbol deletions | `python -c "from <mod> import <sym>"` (ImportError) + `path#symbol` grep | 16/16 deleted symbols carry ZERO live refs across tree + `tests/` + `public/` — QA gate |
| AC-2 orchestrate CLI contract | `dadaia orchestrate list/show --json` vs golden; `--help` | `bug` group + `server dashboard` + `run/status/resume` ABSENT; `list/show --json` byte-identical incl. `gate=<kind>` (3 SHA256 matches) — W1 `9d537d69` |
| AC-3 semver canon | identity+scan agreement/contract test | RED `71e187a5` is ancestor of feat `0cc3cc53`; both contract tests green; 3 modules import the canon |
| AC-5 redaction (redact()-shaped) | `grep -rEn "/home/[^/[:space:]]+\|/Users/[^/[:space:]]+" specs/bugs/ \| grep -vF '[REDACTED]'` | EMPTY (exit 1); 220/220 JSONL lines re-parse; `dadaia specs doctor` 0 errors — W4 `6d6d7891` |
| AC-7(a) semver mutation-sanity | plant competing `re.compile` → agreement scan | FAILED (site `scaffolder:20`); reverted → green — W3 task line |
| AC-7(b) chmod mutation-sanity | restore bare unguarded `os.chmod(` → source-scan contract | FAILED (`service.py:343`); reverted → green — W4 task line |
| AC-4 chmod guard | source-scan contract + DI-fake tests | single posix-guarded `os.chmod` at `service.py:205`; `PlatformSecurityError` → INFO Tier-2 degrade and `has_posix_chmod=False` paths covered — W4 `6d6d7891` |
| QA ship gate | `dadaia reports validate <handoff>` | **APPROVE** 7/7 — handoff `2026-07-03T051502Z-qa-engineer-v0153-ship-gate` (validated exit 0) |
| Security push gate (per push-cycle) | pre-push security-verdict chokepoint | **APPROVE ×2** keyed to pushed sha — r1 `b1147aac`, r2 `83f21a41` |
| Windows portability follow-up | lint-imports config portability | fixed on r2 `83f21a41` (Windows `-cross` lint-imports) |
| CI (PR #95) | GitHub Actions | 38 checks, 0 failures — merge gate |
| Memory atoms lint + catalog | `lint-memory-atoms.py` · `generate-memory-catalog.py` (venv python) | PENDING an orchestrator shell run — PE has no shell tool; `agent_tier` absence is tolerated schema-side (W3: dropped from `required`, retained optional in `properties`); commands surfaced in the handoff. `catalog.json` hand-reconciled for the one changed summary (context-management) + `generated_at` bump; `index.md` byte-identical (no tldr/title/slug change) |

## Drifts

### frozen-no-steal-suite-vs-fr2-tension

**Description:** SPEC §4 (Non-goals) declares "NO touching the surviving frozen no-steal
suite", while FR2 mandated deleting `lease.LEASE_TTL_SECONDS`. The two collided: FR2's
deletion forced value-identical repoints inside 4 frozen files (each moving
`lease.LEASE_TTL_SECONDS` → `kernel_tunables.LEASE_TTL_SECONDS`, value unchanged) plus a
driver repoint in `test_two_actor_lease.py` (`-m hooks.sdd_gate` → `-m hooks.pre_gate`,
the production entrypoint).

**Resolution:** Adjudicated **PASS** at the QA ship gate. The v0.1.50 freeze protects the
**no-steal invariant** (its assertions, the TTL floor of 120s, the pid veto), not the file
bytes. Every repoint is symbol-forced and invariant-preserving: assertions identical, TTL
still 120, pid-veto intact; 3 frozen paths remained zero-diff, 4 carried only the
value-identical `kernel_tunables` repoint. The invariant is fully intact. Precedent:
v0.1.52 already adjudicated a frozen-suite file *deletion* (kanban-only `is_stale_session`);
v0.1.53 extends the precedent to symbol-forced *repoints*.

**Memory updates:** `specs/memory/quality-assurance.md` — recorded the durable rule (the
frozen no-steal suite protects the invariant, not the bytes; symbol-forced repoints are
adjudicated at the QA ship gate). `specs/memory/product/sdd/sdd-gate-v3.md` — the
`lease.LEASE_TTL_SECONDS` re-export text updated to the single canonical name.

### stale-lock-liveness-session-test-reference

**Description:** SPEC §5 (Risks / archival invariants review) referenced
`tests/unit/core/test_lock_liveness_session.py` as a load-bearing file.

**Resolution:** No action — the referenced file is **absent at the merge-base too**
(a pre-existing test-consolidation, not a v0.1.53 deletion). The reference was stale at
definition time; recorded here so the ledger is honest. No behavior change.

**Memory updates:** none — no memory atom referenced this path.

### implementation-collateral-misses-caught-at-full-suite

**Description:** Two collateral deletions were missed by the wave "+tests" sweeps and only
surfaced at the W3/W4 full-suite run: (1) `test_dashboard_deprecation_warning_visible`
(e2e) asserted the banner of the deleted `server dashboard` command; (2) the FROZEN lease
e2e `test_two_actor_lease.py` hook DRIVER hand-rolled `-m hooks.sdd_gate`, which began
**silently no-opping** after the `main()` deletion (a regression vs merge-base — the
wiring pre-check grepped projections only, not `tests/`).

**Resolution:** Both fixed pre-ship in `3811dde7` (dashboard e2e deleted; driver repointed
to `-m hooks.pre_gate`, restoring the two-actor exercise). **Lesson recorded:** AC-1 grep
sweeps for a deletion MUST include `tests/` — a green suite can mask both a deleted-code
assertion and a silently no-opping driver. Not a tool bug; the gate/CI worked as
contracted. No bug event.

**Memory updates:** `specs/memory/quality-assurance.md` — the frozen-suite adjudication
line names driving the production hook entrypoint after a `main()` deletion as a
legitimate invariant-preserving repoint.

### dev-server-registry-skill-dashboard-drift

**Description:** `dev-server-registry` `SKILL.md:69,89` still documented the deleted
`dadaia server dashboard` as a live surface (a lib-originated public asset — recorded, not
fixed, during W2).

**Resolution:** Fixed in closure commit `1e902c14` (the SKILL.md dashboard references
removed; propagated through the public-asset pipeline).

**Memory updates:** none — SKILL.md is a public asset, not a memory atom.

## Memory updates

Memory describes the product **as it is now**; the change history lives here and in
`_archive/`. Written this CLOSURE (phase = CLOSURE, MEMORY gate open):

- **`agent_tier` strip (28 atoms):** the `agent_tier` frontmatter line was removed from
  every atom that carried it — completing the v0.1.53 tolerate-then-strip sequence
  (schema already made the field optional in W3). Atoms touched (frontmatter-only, no
  content/date change on 22 of them): `product/distribution/{public-asset-distribution,
  academy}.md`, `product/sdd/{lifecycle-foundation,dadaia-workflows,specs-doctor}.md`,
  `product/panel/{brand-identity,panel}.md`, `product/philosophy/{product-vision,
  spec-context-project}.md`, `product/platform/{repos-catalog,workspace-init,
  workspace-portability,workspace-doctor,multi-platform-parity,server-registry,
  cross-platform-portability}.md`, `product/harness/{harness-pi,harness-codex,
  harness-claude-code}.md`, `product/agents/{agent-monitoring,agent-comms,
  agent-orchestration}.md`.
- `specs/memory/product/platform/context-management.md` — `dadaia bug new` removed from
  the summary, CLI-surface line, and scaffolder bullet: `dadaia bugs append` is now the
  **only** bug-intake path (v0.1.53 deleted `bug new`). `last_updated`/`release_origin` →
  2026-07-03 / v0.1.53. (agent_tier stripped.)
- `specs/memory/product/sdd/sdd-bug-backlog-governance.md` — the `bug new` coexistence
  bullet replaced by "sole intake path"; recorded the new **deprecation-expiry law**
  (a deprecation promised for removal at N+1 is DEBT by N+2; deleted by the next release
  that touches its area; deprecations do not accumulate). `last_updated`/`release_origin`
  → 2026-07-03 / v0.1.53. (agent_tier stripped.)
- `specs/memory/architecture.md` — `bug` command group removed (cli count 23→22);
  `orchestration` feature bullet deleted (features 26→25); `spec_artifacts` drops
  `bug new`; `workflows` bullet records it backs `dadaia orchestrate list/show`;
  `core/specs_version.py` recorded as the single release-SemVer canon; `pre_gate` recorded
  as the SOLE hook entrypoint (standalone `sdd_gate`/`root_whitelist` `main()`s deleted);
  memory-frontmatter required list drops `agent_tier` (now deprecated-optional).
  `last_updated`/`release_origin` → 2026-07-03 / v0.1.53. (agent_tier stripped.)
- `specs/memory/tech-stack.md` — the dead `features/orchestration/` reference replaced:
  process-level concurrency runs through the lifecycle engine's bounded worker
  subprocesses. `last_updated`/`release_origin` → 2026-07-03 / v0.1.53. (agent_tier
  stripped.)
- `specs/memory/product/sdd/sdd-gate-v3.md` — the transitional `lease.LEASE_TTL_SECONDS`
  re-export text replaced by the single canonical `kernel_tunables.LEASE_TTL_SECONDS`
  name. `last_updated`/`release_origin` → 2026-07-03 / v0.1.53. (agent_tier stripped.)
- `specs/memory/quality-assurance.md` — recorded the frozen-no-steal-suite adjudication
  rule (freeze protects the invariant, not the bytes); live-scale refreshed to ≈4.3k
  (4,339 as of v0.1.53). `last_updated`/`release_origin` → 2026-07-03 / v0.1.53.
  (agent_tier stripped.)
- `specs/memory/product/catalog.json` — reconciled for the one changed summary
  (context-management) + `generated_at` bump. Authoritative regeneration + `lint-memory-
  atoms` exit-0 confirmation is a pending orchestrator shell step (PE has no shell tool).
- `specs/memory/product/index.md` — no change (byte-identical: no tldr/title/slug moved).
- `specs/memory/architecture.md`/`tech-stack.md` note: no dependency (tech-stack) or ring
  (architecture) structural change beyond the deletions above.

**Out-of-scope PUBLIC-ASSET follow-up (NOT memory, requires `dadaia public stage/install`
— surfaced to the orchestrator/devops):** FR3's CLOSURE also calls for stripping
`agent_tier` from `public/scaffold/memory/*.md` templates and the `AGENTS.md`/
`specs/memory/AGENTS.md` tri-copy field enumeration. These are PUBLIC-ASSET edits outside
the memory-guardian write scope and need the projection pipeline; they do not block (the
scaffold atoms lint clean with the field either present or absent). Tracked as a devops
follow-up, not a memory edit.

## Dispositions

All four consumed backlog entries were archived at SHIP (durable copies + ledger in the
atomic archival commit `6c08dd25`), per the R4 dead-anchor process law (this release
deletes its own consuming entries' anchors).

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/_archive/v0.1.53/consumed-backlog/legacy-surface-retirement.md` | backlog | `CONSUMED — v0.1.53` | archival `6c08dd25`; `consumed_backlog.json` |
| `specs/_archive/v0.1.53/consumed-backlog/hygiene-and-dead-code-cleanup.md` | backlog | `CONSUMED — v0.1.53` | archival `6c08dd25`; `consumed_backlog.json` |
| `specs/_archive/v0.1.53/consumed-backlog/centralize-release-semver-canon.md` | backlog | `CONSUMED — v0.1.53` | archival `6c08dd25`; `consumed_backlog.json` |
| `specs/_archive/v0.1.53/consumed-backlog/telemetry-tier2-chmod-unguarded-on-windows.md` | backlog | `CONSUMED — v0.1.53` | archival `6c08dd25`; `consumed_backlog.json` |

No bugs were picked into this release (open-bug debt was zero at pick — `candidates.md`).
No bug terminal events were appended. Dispositioned-at-definition and recorded (not
silently dropped): the persona-regex "STALE" claim (no-op), the `repos/*/.dadaia` doctor
WARN intent (REJECTED-stale — covered by root-whitelist/hygiene laws + the v0.1.47 skill
fix), and the `features/migrate` audit (KEEP both steps — reachable from `specs upgrade`).

## Backlog returns

None. All four consumed entries shipped in full. The R6–R12 conversion sequence continues
unchanged in `specs/backlog/candidates.md` (R5 row now marked **SHIPPED — v0.1.53**).

## Archive decision

**MOVE** — `specs/releases/v0.1.53/` will be moved to
`specs/_archive/releases/v0.1.53/` via `git mv` (by the orchestrator / devops-engineer;
PE issues no git mutations). `specs/releases/ACTIVE.md` will then be set to
`release: none` — **the operator's R1→R5 mandate is complete**.
