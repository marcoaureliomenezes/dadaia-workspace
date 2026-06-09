# Release 0.1.7 — Implementation Rot Remediation

**Status:** Aprovado
**Release ID:** 0.1.7
**Owner:** product-engineer
**Branch:** feature/0.1.7
**Opened:** 2026-06-08

---

## Objective

Eliminate the implementation rot identified by the deep audit (`20260608T035551Z-da1a1b2c`)
and the subsequent architect review. The audit scored the library at 7.0/10 overall and the
architecture at 6.5/10. This release restores the library to full conformance with the
declared three-ring architecture, removes dead/stale code, corrects two memory atom
inaccuracies, fixes one gate bug, and bumps the package version to match the shipped 0.1.6.

No new user-visible features. Every change is behavior-preserving unless the existing
behavior was a bug (e.g. `_WORKSPACE_ROOT` writing to `repos/.dadaia/`).

---

## Canonical Evidence

All findings in this release trace to one of two evidence sources:

- `repos/dadaia-workspace/specs/audits/20260608T035551Z-da1a1b2c/index.md`
  — scorecard 7.0/10, findings D-01..D-10.
- `repos/dadaia-workspace/specs/audits/20260608T035551Z-da1a1b2c/architect-review.md`
  — architecture review 6.5/10; findings AR-01..AR-08.

---

## Pillars this Release Restores

1. **Strong layers / boundary enforcement** — panel DI violations fixed (AR-01, AR-02, AR-03)
2. **Single source of truth / no duplication** — CANONICAL_AGENTS derived/updated (D-01/AR-05);
   guardrail-pair collapse (AR-04b); staleness predicate extracted (AR-08)
3. **Block-by-block encapsulation** — no service constructed inside another service (AR-02/AR-03)
4. **No dead/stale code** — HTML-era classes deleted (D-04/AR-07); deprecated CLI stubs removed (D-10)
5. **Human-friendly + UML-derivable** — panel module maps cleanly to UML after DI fix
6. **Simplicity first** — guardrail-pair triplication collapsed; god-module partial decomposition

---

## Product Deltas

This release makes zero changes to externally visible behavior. All changes are internal:
one bug fix (workspace root derivation), one correctness fix (CANONICAL_AGENTS), one gate fix
(backlog-ownership persona resolution), and six structural refactors/cleanups. The only
visible change to operators is that `dadaia reports next` will correctly parse PLAN.md files
authored after the 15→9 agent consolidation.

---

## Architecture Deltas

| Component | Before | After |
|-----------|--------|-------|
| `panel/service.py` imports | 3 concrete sibling-feature class imports | 3 protocol interfaces from `core/protocols/` |
| `PanelService.__init__` | instantiates `WorkflowsService` internally | receives `WorkflowsService` via DI injection |
| `container.py:289` | accesses `service._workflows_service` private attr | injects `WorkflowsService` directly |
| `panel/views/api.py` | imports concrete types + constructs `ReportRetentionService` per-request | receives only `PanelService` + DTOs; `ReportRetentionService` moved into `PanelService` |
| `core/protocols/` | no panel protocols | adds `ContextProjectProvider`, `ServerRegistryProvider`, `WorkflowProvider` |
| `core/lock_liveness.py` | staleness predicate only for leases | adds `is_stale_session()` exported for panel kanban |
| `public_assets.py` | 3 triplicated guardrail-pair install functions (~330 lines) | 1 function with `targets` param (~60 lines) |
| `public_assets.py` | 2 duplicate consumer-repo discovery functions | 1 module-level function |

---

## Tech-Stack Deltas

None. No new dependencies introduced. `pyproject.toml` version field is bumped from `0.1.5`
to `0.1.7` (skipping the unpublished 0.1.6 intermediate).

---

## Security / Operations Deltas

**Bug fixed (D-02/AR-06):** `cli/main.py`'s `_WORKSPACE_ROOT` static derivation wrote exception
reports to `repos/.dadaia/bugs/reported.json` (a boundary violation: `.dadaia/` must not exist
inside any repo). After this release, `_safe_app()` calls `resolve_workspace_root()` and
catches `WorkspaceNotInitializedError` gracefully. No secret leak was present; the fix removes
the boundary violation and ensures `dadaia doctor` can find exception reports.

---

## Scope of the 15 Tasks

| Task | Finding | Short title |
|------|---------|-------------|
| T-017-01 | D-01/AR-05 | Fix stale `CANONICAL_AGENTS` (12-name public set) |
| T-017-02 | D-02/AR-06 | Replace `_WORKSPACE_ROOT` with `resolve_workspace_root()` + clean residue |
| T-017-03 | D-04/AR-07 | Delete dead HTML-era classes in `specs/doctor.py:266-350` |
| T-017-04 | D-10 | Remove 4 hidden deprecated `context` stubs + tests |
| T-017-05 | D-08/D-09 | Test slop: merge duplicate contrast tests, delete dead dashboard test, relocate misplaced test |
| T-017-06 | AR-02 | Panel DI: remove `WorkflowsService` self-construct, inject it; fix `container.py:289` |
| T-017-07 | D-03/AR-01 | Panel protocols: declare 3 `core/protocols/` interfaces; annotate `panel/service.py` |
| T-017-08 | AR-03 | Panel views: move `ReportRetentionService` into `PanelService`; inject `ADAPTER_REGISTRY` |
| T-017-09 | D-06/AR-04 | Collapse triplicated guardrail-pair + duplicate consumer-repo discovery |
| T-017-10 | AR-08 | Extract session-staleness predicate to `core/lock_liveness.py` |
| T-017-11 | D-06 (W-8b) | `public_assets.py` module split (staged; finish or explicit rc-gate defer) |
| T-017-12 | D-05 | Correct `architecture.md:268` session-file claim |
| T-017-13 | D-07 | Fix `quality-assurance.md` broken test path reference |
| T-017-14 | W-5 | Bump `pyproject.toml` 0.1.5 → 0.1.7 |
| T-017-15 | NEW (gate bug) | Fix backlog-ownership gate persona session-pointer fallback |

---

## Memory Files Affected at Closure

- `specs/memory/architecture.md` — correct session-file retention claim (T-017-12; applied in
  DEFINITION phase per §13) + update lock_liveness module entry at CLOSURE
- `specs/memory/quality-assurance.md` — fix broken `test_gate_session_locks.py` path reference
  (T-017-13; applied in DEFINITION phase per §13)

---

## Acceptance Criteria

Each criterion is independently verifiable:

| # | Criterion | Verification |
|---|-----------|-------------|
| AC-01 | `CANONICAL_AGENTS` in `reports_next/service.py` equals the 12-name set (9 core + 3 plugins) | `grep -A30 'CANONICAL_AGENTS' dadaia_workspace/features/reports_next/service.py` |
| AC-02 | `_WORKSPACE_ROOT` constant deleted from `cli/main.py` | `grep '_WORKSPACE_ROOT' dadaia_workspace/cli/main.py` returns empty |
| AC-03 | No `.dadaia/bugs/` directory inside `repos/` | `[ ! -d repos/.dadaia ]` exits 0 |
| AC-04 | `_MemoryHtmlSummary`, `_MemoryParser`, `_parse_memory_html` absent from codebase | `grep -r '_MemoryHtmlSummary\|_MemoryParser\|_parse_memory_html' dadaia_workspace/` returns empty |
| AC-05 | `activate`, `deactivate`, `promote`, `use` hidden commands absent from `context.py` | `grep -n 'def activate\|def deactivate\|def promote\|def use' dadaia_workspace/cli/commands/context.py` returns empty |
| AC-06 | No duplicate `test_contrast.py` + `test_panel_css_contrast.py`; only one file remains | directory listing shows exactly one contrast test file |
| AC-07 | `tests/unit/test_dashboard.py` deleted | `[ ! -f tests/unit/test_dashboard.py ]` exits 0 |
| AC-08 | `tests/test_orchestration_registry.py` deleted from root; relocated to `tests/unit/features/specs/` | file absent at old path, present at new path |
| AC-09 | `WorkflowsService(workspace_root)` instantiation absent from `PanelService.__init__` | `grep 'WorkflowsService(workspace_root)' dadaia_workspace/features/panel/service.py` returns empty |
| AC-10 | `container.py` does not access `service._workflows_service` | `grep '_workflows_service' dadaia_workspace/container.py` returns empty |
| AC-11 | `core/protocols/` contains at minimum `ContextProjectProvider`, `ServerRegistryProvider`, `WorkflowProvider` | `ls dadaia_workspace/core/protocols/*.py` shows these files |
| AC-12 | `panel/service.py` imports from `core/protocols/` not from sibling features | `grep -E 'from dadaia_workspace.features.(server_registry|spec_context|workflows)' dadaia_workspace/features/panel/service.py` returns empty |
| AC-13 | `ReportRetentionService` not instantiated inside any view closure | `grep 'ReportRetentionService(' dadaia_workspace/features/panel/views/api.py` returns empty |
| AC-14 | `core/lock_liveness.py` exports `is_stale_session`; `kanban.py` imports it | `grep 'is_stale_session' dadaia_workspace/features/panel/views/kanban.py` shows import |
| AC-15 | Triplicated guardrail-pair functions (`_install_workspace_guardrail_pair`, `_install_workspace_root_guardrail_pair`, `_install_consumer_repos_guardrail_pair`) replaced by single function | `grep 'def _install_workspace_guardrail_pair\|def _install_workspace_root_guardrail_pair\|def _install_consumer_repos_guardrail_pair' dadaia_workspace/infrastructure/public_assets.py` returns ≤1 hit |
| AC-16 | `dadaia public doctor` exits 0 after T-017-09 and T-017-11 | `dadaia public doctor && echo OK` |
| AC-17 | Full pytest suite exits 0 | `pytest` |
| AC-18 | `pyproject.toml` declares `version = "0.1.7"` | `grep 'version = ' pyproject.toml` |
| AC-19 | `sdd-spec-gate.sh` backlog branch resolves project-manager persona via session-pointer fallback | manual test: PM agent can write to `specs/backlog/` without gate error |
| AC-20 | `architecture.md:268` no longer claims session files were removed; states they are retained for Kanban | `grep 'sess_\*' specs/memory/architecture.md` shows retention claim |
| AC-21 | `quality-assurance.md` Dependências section references real `tests/unit/gate/` and `tests/integration/gate/` paths | `grep 'test_gate_session_locks' specs/memory/quality-assurance.md` shows corrected path |

---

## Out of Scope

- New user-visible features or behavioral changes
- Full W-8 god-module decomposition (T-017-11 is STAGED: either finish if safe in this release
  or make an explicit rc-gate decision to defer to 0.1.8; it is NOT dropped)
- Memory atoms beyond `architecture.md` and `quality-assurance.md`
- Codex/OpenCode projection changes (public_assets.py behavior preserved, only internal structure changes)
- `pyproject.toml` version history or changelog

---

## Dependencies and Risks

| Item | Risk | Mitigation |
|------|------|-----------|
| T-017-06..08 (panel DI) | Tests may fail if panel unit tests mock concrete classes | software-architect provides design notes; SE writes tests before flipping `[x]` |
| T-017-09 (guardrail collapse) | `dadaia public doctor` may show drift if hash comparison changes | Run `dadaia public doctor` after each collapsed function |
| T-017-11 (module split) | Module split changes import paths; any non-updated caller breaks | Must verify with `mypy --strict` and `pytest` green before closing; rc-gate defer is the safe option if not confident |
| T-017-15 (gate fix) | `sdd-spec-gate.sh` is lib-originated; must re-project after fix | Run `dadaia public stage && dadaia public install --target all` after fix |

---

## Grill Assumptions

The following assumptions were made inline (no blocking operator Q&A; operator mandate is "solve every finding"):

- **GA-01:** `CANONICAL_AGENTS` immediate fix strategy (strategy 2 from AR-05) is used. The
  medium-term registry-derived strategy is noted in AC-01 comments for the next refactor pass.
- **GA-02:** The backlog-ownership gate bug (T-017-15) is treated as a library bug in
  `dadaia_workspace/public/scripts/sdd-spec-gate.sh`. The fix adds a persona session-pointer
  fallback in the backlog branch so that a `project-manager` agent (whose persona may be
  resolved via a `.ptr` file) is correctly identified as the legitimate backlog owner.
- **GA-03:** pyproject version bumps from `0.1.5` directly to `0.1.7`. The 0.1.6 intermediate
  was never published to PyPI. This is consistent with the operator's decision to skip 0.1.6
  PyPI publication.
- **GA-04:** T-017-11 (W-8b module split) is included in this release as STAGED. The SE should
  attempt the split and provide an explicit decision at the end of the task: either "split
  complete, doctor exit 0" or "deferred to 0.1.8 due to [reason]". The latter is acceptable
  and must be documented in TASKS.md.
- **GA-05:** Memory fixes T-017-12 and T-017-13 are applied in the DEFINITION phase (not
  deferred to CLOSURE) because they correct current-truth inaccuracies that active agents are
  reading, per constitution §13 DEFINITION-phase authorization.

---

## rc-3 scope addition — Unlock the Workflow (2026-06-09)

**Status:** Aprovado (operator directive 2026-06-09; folded from the drafted 0.1.8).

**Why rc-3 reopens IMPLEMENTATION.** rc-1/rc-2 tried to *satisfy* the backlog-ownership
persona gate (GA-02 / T-017-15: a `.dadaia/sessions/runtime/<session>.persona` fallback). That
approach is unfixable: there is **no key**. Persona can only reach the `PreToolUse` hook from
the hook-process env (harness-only — no harness sets it for agents) or from a `.persona`
pointer that **no `dadaia` CLI verb ever writes**; an agent writing it itself is correctly
blocked as forgery (`.dadaia/sessions/**` PROTECTED, SEC-01). Reproduced live under **Claude
Code** (not just Codex) — see
`specs/bugs/codex-dispatched-agent-persona-not-propagated-to-sdd-gate.md` (REPRO 1–3). The
"owner-only" backlog gate therefore locks out the legitimate owner in **every** harness.

**Operator ruling.** This kind of lock is not tolerated. No workflow (research,
backlog-definition, release-definition, implementation+review, audits) may ever be
lock-blocked, and `project-manager` must always spawn and write freely. The **only** tolerated
deterministic lock is the single-session-per-Spec-Context **lease** (release-definition /
implementation+review), keyed by `.dadaia/sessions/runtime/<ctx>.ptr` — which is the real
reason `.dadaia/sessions/**` stays PROTECTED (lease-identity integrity, not persona).

**rc-3 supersedes GA-02 / T-017-15.** The persona session-pointer fallback is removed together
with the whole backlog-ownership block. Backlog becomes a plain ADDITIVE-allow path; ownership
is re-expressed as a PM coordination convention (rule reworded, no gate). The dormant RULE-D
write-allowlist deny path (fail-open, never fires for an agent) is also removed as pure
simplification. The lease, MEMORY phase gate, FROZEN archive rule, and root-whitelist gate are
untouched.

**Lock inventory after rc-3:** exactly one deterministic lock — the single-session lease.
`.dadaia/sessions/**` PROTECTED and `specs/_archive/**` FROZEN remain as **integrity**
boundaries (not workflow locks); the MEMORY phase gate remains a content-integrity rule that
does not block any enumerated workflow.

**Trade-off (operator-requested).** Removing the backlog lock lets any (trusted, operator-
spawned) agent write `specs/backlog/**`. Accepted: ownership is a convention, not a defence
against an adversary; the genuine integrity boundaries are preserved; two no-key/fail-open
branches are deleted, reducing race surface rather than adding it.

**rc-3 functional requirements:**
- FR-rc3-1 — `specs/backlog/**` writes are ALLOWED from any session regardless of persona.
- FR-rc3-2 — `project-manager`/dispatched agents author backlog with Write/Edit, no env var,
  no pointer, no operator intervention.
- FR-rc3-3 — the single-session lease is unchanged (foreign live session still blocked on
  MUTATING; holder always RENEWs).
- FR-rc3-4 — `.dadaia/sessions/**` stays agent-write-protected, re-justified on lease integrity.
- FR-rc3-5 — `backlog-ownership` rule + root `AGENTS.md` + gate-model memory describe exactly
  one lock (the lease); no "backlog hard gate" claim remains.
- FR-rc3-6 — the previously-blocked `harness-agentic-entities-and-determinism-parity` backlog
  item is registered through the now-unblocked flow; both persona bugs close `resolved_in:
  0.1.7` (rc-3).

**rc-3 acceptance:** REPRO 1 returns ALLOW; gate test asserts backlog ALLOW (was block,
including the rc-2 codex-path assertion from T-017-20); lease negative test still blocks a
foreign live session; `test_protected_sessions.py` green; `dadaia public doctor` exit 0
`[ok] public-privacy`; full `dadaia ci preflight` green.

---

## rc-4 scope addition — Bug root-cause sweep (2026-06-09)

**Status:** Aprovado (operator goal 2026-06-09: solve the root cause of ALL reported bugs in the
active release; mandatory `dadaia-grill-me` run — report
`.dadaia/reports/dadaia-workspace/product-engineer/2026-06-09T033120Z-refine-specs.html`).

After sanitizing the bug backlog (26 files → 8 genuinely-open; 7 panel bugs + `init-ignores-
workspace-flag` verified already-fixed and Closed; `lease-cross-context-false-positive-block`
superseded as a duplicate), three specialists investigated root causes. One **single
architectural root cause** unites the CRITICAL bugs:

> **Runtime identity & context are never reliably propagated to the deterministic hooks.** The
> SDD gate, the lease, and `ctx-inject` each independently re-derive "which context / which
> session" from unreliable ambient signals — env vars no harness exports into the hook
> subprocess, a first-ALIVE fallback, a per-hook PID. Each mangles identity differently →
> cross-context false locks, per-prompt memory-bootstrap spam, and governance doc drift.

**Grill ADRs (operator decisions, 2026-06-09):**
1. **Context = write-target path.** Resolve `CONTEXT_SLUG` from `repos/<slug>/…`; if the path is
   under no repo → UNGATED (no lease). The resource's repo is deterministic; the session's
   declared context is not.
2. **Session id = harness-native.** Populate `.dadaia/sessions/runtime/<ctx>.ptr` from the
   harness-native id (`CLAUDE_CODE_SESSION_ID`; Codex stdin-JSON `session_id`) directly;
   `DADAIA_SESSION_ID` becomes an optional override. The env-export channel is unreachable.
3. **Shell-bypass of the lease = DEFERRED** to a separate backlog item
   (`lease-shell-write-coverage-gap`). The lease mediates only agent Write/Edit tools; closing
   the Bash/CLI gap needs an fs-level/policy mechanism that would also catch legitimate git use.
4. **Memory writes = DEFINITION+CLOSURE** (gate already correct); fix the one drifted skill that
   says CLOSURE-only and add a `specs doctor` single-source lint so governance facts can't drift.

**rc-4 functional requirements:**
- FR-rc4-1 — A MUTATING write resolves its lease context from the target path (`repos/<slug>/`).
  Two sessions on different repos NEVER lease-block each other; same repo + live foreign → BLOCK.
  (Fixes `gate-cross-context-lock-contamination` + superseded dup.)
- FR-rc4-2 — `ctx-inject` derives session identity from the harness-native id and writes the
  `.ptr`; the full memory bootstrap injects at most once per logical session; the already-fired
  path emits nothing (no leaked context line). (Fixes `repeated-visible-userpromptsubmit-memory-injection`.)
- FR-rc4-3 — Canonical memory-write phase is DEFINITION+CLOSURE across constitution, personas,
  skills, rules; a `specs doctor` lint flags divergence. (Fixes `constitution-persona-single-source-drift`.)
- FR-rc4-4 — `dadaia public install` prunes orphan projections across ALL copy strategies; `public
  doctor` reports orphans; `public stage` fails on broken agent→skill refs. (Fixes
  `install-does-not-prune-orphan-projections` + `agent-skill-surface-slop` projection side.)
- FR-rc4-5 — `dadaia specs doctor` prints one authoritative overall verdict; `dadaia specs
  upgrade` only fails/advises-restore on errors the migration NEWLY introduced. (Fixes
  `specs-doctor-dual-error-counter` + `specs-upgrade-fails-on-preexisting`.)
- FR-rc4-6 — `dadaia ci preflight` fails gracefully when `poetry` is absent (no raw traceback).
  (Fixes `ci-preflight-raw-traceback-when-poetry-absent`.)
- FR-rc4-7 — Panel verification follow-ups closed (store injection always wired; per-request slug;
  residual auth tuple removed). Persona dangling skill-refs cleaned (library side of
  `agent-skill-surface-slop`).

**rc-4 acceptance:** every targeted bug flipped to Closed with `resolved_in: 0.1.7` (rc-4);
new integration test proves two-repo no-cross-block + same-repo foreign-live block; ctx-inject
hook test proves single-injection + silent already-fired; `dadaia public/specs doctor` exit 0;
full `pytest` green; ship-trio re-review APPROVE before ship.

## rc-4 review record (2026-06-09)

Ship-trio re-review of the rc-4 changeset (8 bug fixes) — **unanimous APPROVE**:
- **security-reviewer — APPROVE.** No CRITICAL/HIGH. Retained boundaries intact (PROTECTED
  `.ptr`, FROZEN, MEMORY phase); the path-derived context fix verified to stop cross-context
  contamination; slug `[^A-Za-z0-9_-]`-stripped (CWE-22); no secrets in public assets. One
  MEDIUM hardening (FPATH realpath, no current bypass) + one LOW dev-only pip CVE.
- **code-reviewer — APPROVE.** bash -n clean both scripts; gate path-derivation + ctx-inject
  sentinel correct and complete; RULE-D/persona-gate/backlog-block fully excised; new tests
  genuine. Corroborated the same MEDIUM FPATH-realpath hardening (pre-existing).
- **qa-engineer — APPROVE.** Full suite 2298 passed; all 8 regression tests genuine (not slop).

The single MEDIUM (FPATH not canonicalized before the bash classifier) is **pre-existing and
non-blocking** (no current bypass) — registered as `specs/bugs/gate-fpath-not-canonicalized-
before-classifier.md` for a dedicated fix rather than a late rc-4 change. rc-4 is **ship-ready**
pending operator ship/iterate + commit.
