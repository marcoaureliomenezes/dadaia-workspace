# Tasks: Release — agents-r2-v1

> **Status:** Aprovado
> **Status note:** pending operator review of the implementation breakdown.
> **Release ID:** agents-r2-v1
> **Owner:** product-engineer
> **Created:** 2026-05-18
> **Phase:** TASKS
> **SPEC:** `specs/releases/agents-r2-v1/SPEC.md` (Aprovado).
> **PLAN:** `specs/releases/agents-r2-v1/PLAN.md` (Aprovado).
> **ADR:** `.dadaia/reports/dadaia-workspace/software-architect/2026-05-19T003956Z-adr-claude-agents-parity.html` — Option C.
> **Total tasks:** 53 (AGT-r2-01 through AGT-r2-53)

Markers: `[ ]` OPEN → `[-]` IN PROGRESS → `[x]` DONE.
Maximum **one `[-]` per agent at a time**, except where a phase note declares
parallel-safe (disjoint write sets per PLAN §4). PLAN parallel windows:
**W1 = {P1, P2, P3, P4}** (post-P0); **W2 = {P6, P7}** (post-P5);
**W3 = {P9, P10}** (post-P8); **W4 = {P11a, P11c, P12}** (post-P10).

Every public/ change MUST close with `dadaia public stage && install
--target all && doctor` (run by devops-engineer in P8 / P13; per-task verify
local with `pytest` and `dadaia specs doctor`).

---

## Phase P0 — Foundation (state-recording; already on disk)

- [x] AGT-r2-01 — Cut branch `release/agents-r2-v1` (product-engineer)
  - Acceptance: `git rev-parse --abbrev-ref HEAD` reports the branch on operator workstation.
- [x] AGT-r2-02 — Set `specs/releases/ACTIVE.md` → `release: agents-r2-v1, phase: SPEC` then advance through `PLAN` → `TASKS` (product-engineer)
  - Acceptance: file content matches current phase at each gate transition.
- [x] AGT-r2-03 — Land SPEC.md Aprovado (product-engineer)
  - Acceptance: `specs/releases/agents-r2-v1/SPEC.md` header has `**Status:** Aprovado`.
- [x] AGT-r2-04 — Land PLAN.md Aprovado (product-engineer)
  - Acceptance: `specs/releases/agents-r2-v1/PLAN.md` header has `**Status:** Aprovado`.
- [x] AGT-r2-05 — Consume software-architect ADR (product-engineer)
  - Acceptance: ADR path linked from PLAN §"Architect ADR" and resolutions §8 enumerated.

---

## Phase P1 — Workflow trim 15 → 7 (W1, parallel with P2/P3/P4)

- [x] AGT-r2-06 — `git mv` 8 deprecated workflows to `_archive/legacy-workflows/<UTC>/` (software-engineer)
  - Files moved (from `dadaia_workspace/public/workflows/`): `game-spec-definition`, `architecture-review`, `tdd-cycle`, `bug-fix-fastlane`, `game-bugfix`, `security-patch`, `deploy-validation-only`, `design-validation` (all `*.workflow.md`).
  - Acceptance: `ls dadaia_workspace/public/workflows/*.workflow.md | wc -l` → 7; archived files reachable under `specs/_archive/legacy-workflows/<UTC>/`.
  - Depends: AGT-r2-05.
  - Parallel with: P2 (AGT-r2-08..09), P3 (AGT-r2-10..11), P4 (AGT-r2-12).
- [x] AGT-r2-07 — Update workflow count fixture/test (software-engineer)
  - Files: `tests/unit/features/public/test_workflows.py` (or current schema test) + any panel test fixture asserting workflow count.
  - Acceptance: tests assert exactly 7 surviving workflows; `pytest -q tests/unit/features/public/test_workflows.py` passes; no broken refs to the 8 removed workflows in `dadaia-grill-me` skill body (`grep -rn "game-spec-definition\|architecture-review\|tdd-cycle\|bug-fix-fastlane\|game-bugfix\|security-patch\|deploy-validation-only\|design-validation" dadaia_workspace/public/skills/dadaia-grill-me/` → empty).
  - Depends: AGT-r2-06.

---

## Phase P2 — PM Playbooks in `project-orchestration` skill (W1)

- [x] AGT-r2-08 — Draft 8 PM playbook stubs (product-engineer)
  - File: `dadaia_workspace/public/skills/project-orchestration/SKILL.md` — append `## PM Playbooks` section after the existing inventory.
  - One playbook per dropped workflow (≤ 20 lines each). `game-spec-definition` becomes a `scope=game` sub-entry of the `spec-refinement` playbook (per PLAN P2).
  - Acceptance: `grep -c '^### Playbook' dadaia_workspace/public/skills/project-orchestration/SKILL.md` → 8.
  - Depends: AGT-r2-05. Parallel with: P1, P3, P4.
- [x] AGT-r2-09 — Wrap playbooks into skill body + lint pass (software-engineer)
  - Acceptance: file passes `dadaia public doctor`'s skill checks; cross-reference to PM-only invocation noted (R3). No external workflow file under `public/workflows/` references these playbooks (R6 / NFR8 note).
  - Depends: AGT-r2-08.

---

## Phase P3 — Bash removal from product-engineer + software-architect (W1)

- [x] AGT-r2-10 — Strip `Bash` from product-engineer agent frontmatter (software-engineer)
  - File: `dadaia_workspace/public/agents/product-engineer.md`.
  - Body changes: delegate `dadaia specs doctor`, `dadaia context show`, `cat ACTIVE.md` invocations to PM (operator surfaces results in dispatch).
  - Acceptance: `grep -E '^\s*-\s*Bash' dadaia_workspace/public/agents/product-engineer.md` → empty; body has no `bash` fenced shell-call paragraphs initiated by PE itself.
  - Depends: AGT-r2-05. Parallel with: P1, P2, P4.
- [x] AGT-r2-11 — Strip `Bash` from software-architect agent frontmatter (software-engineer)
  - File: `dadaia_workspace/public/agents/software-architect.md`.
  - Acceptance: `grep -E '^\s*-\s*Bash' dadaia_workspace/public/agents/software-architect.md` → empty; R7 body audit confirms no shell calls.
  - Depends: AGT-r2-05.

---

## Phase P4 — Architect consult for path-scope gate pattern (W1)

- [x] AGT-r2-12 — Software-architect emits path-scope gate-pattern report (software-architect)
  - File: `.dadaia/reports/dadaia-workspace/software-architect/<UTC>-path-scope-gate-pattern.html` + sidecar.
  - Content: runtime agent-detection mechanism (env var / PreToolUse payload field / fallback per harness) + cache strategy; covers R2 fail-open.
  - Acceptance: report + `.handoff.json` sidecar emitted; sidecar validates against `handoff-v1`.
  - Depends: AGT-r2-05. Parallel with: P1, P2, P3.

---

## Phase P5 — `paths:` block on 16 agents + path-scope gate

- [x] AGT-r2-13 — Add `paths:` block to PM, auditor, code-reviewer, security-reviewer, researcher (software-engineer)
  - Files: `dadaia_workspace/public/agents/{project-manager,project-auditor,code-reviewer,security-reviewer,researcher}.md` — frontmatter gains `paths.write_allowlist` per SPEC FR2.1 row.
  - Acceptance: all 5 files contain `^paths:` + `write_allowlist:` block; values match SPEC table verbatim.
  - Depends: AGT-r2-10, AGT-r2-11.
- [x] AGT-r2-14 — Add `paths:` block to design-specialist, product-engineer, software-engineer (software-engineer)
  - Files: `…/design-specialist.md`, `…/product-engineer.md`, `…/software-engineer.md`.
  - Acceptance: 3 files have `paths:` block; PE includes `specs/**` (except `_archive/`) and PE/SE include `.dadaia/reports/<ctx>/<self>/**` per SPEC table.
  - Depends: AGT-r2-13.
- [x] AGT-r2-15 — Add `paths:` block to backend-engineer, frontend-engineer, qa-engineer (software-engineer)
  - Files: `…/backend-engineer.md`, `…/frontend-engineer.md`, `…/qa-engineer.md`.
  - Acceptance: FE includes `specs/assets/**`; QA includes `tests/**` + own report dir.
  - Depends: AGT-r2-13.
- [x] AGT-r2-16 — Add `paths:` block to devops-engineer, software-architect (software-engineer)
  - Files: `…/devops-engineer.md`, `…/software-architect.md`.
  - Acceptance: devops gains `.github/**`, `services/**`; software-architect restricted to own report dir.
  - Depends: AGT-r2-13.
- [x] AGT-r2-17 — Add `paths:` block to game-developer, game-designer, game-tester (software-engineer)
  - Files: `…/game-{developer,designer,tester}.md`.
  - Acceptance: all 3 scoped to `repos/redacted-slug/**` (per sub-domain globs) + own report dir.
  - Depends: AGT-r2-13.
- [x] AGT-r2-18 — Audit `paths:` coverage across all 16 agents (software-engineer)
  - Acceptance: `grep -L "^paths:" dadaia_workspace/public/agents/*.md` → empty; `tests/unit/features/agents/test_agent_reader.py` parses `paths.write_allowlist` from each frontmatter.
  - Depends: AGT-r2-13..AGT-r2-17.
- [x] AGT-r2-19 — Implement path-scope check in `sdd-spec-gate.sh` (software-engineer)
  - File: `dadaia_workspace/public/scripts/sdd-spec-gate.sh` — add path-scope step **after** the TASKS-marker step per ADR pattern (AGT-r2-12).
  - Behaviour: mismatch → `{"decision":"block","reason":"[PATH SCOPE ERROR] agent <X> cannot write to <path>. write_allowlist: <list>."}`; fail-open with `/tmp/sdd-gate.log` warning when no agent persona is detected (NFR3 / SPEC FR2.4).
  - Acceptance: shellcheck passes; gate's new branch is reachable from `Write/Edit/MultiEdit` PreToolUse path.
  - Depends: AGT-r2-12, AGT-r2-18.
- [x] AGT-r2-20 — Author `tests/unit/gate/test_path_scope.py` (software-engineer)
  - File: `tests/unit/gate/test_path_scope.py` covering: (a) accept inside allowlist, (b) reject outside allowlist with exact error string, (c) fail-open when agent persona absent + log line written.
  - Acceptance: `pytest -q tests/unit/gate/test_path_scope.py` green; coverage hits the new path-scope branch.
  - Depends: AGT-r2-19.

---

## Phase P6 — Audit-verify Bash removal closure (W2, parallel with P7)

- [x] AGT-r2-21 — Verify PE + software-architect body has no leftover Bash invocations (software-engineer)
  - Acceptance: ripgrep for fenced shell blocks attributed to PE or software-architect persona → empty; SPEC C6 + C7 satisfied.
  - Depends: AGT-r2-19. Parallel with: AGT-r2-22..AGT-r2-23.

---

## Phase P7 — Test updates (W2)

- [x] AGT-r2-22 — Update agent + workflow test fixtures (software-engineer)
  - Files: `tests/unit/features/public/test_workflows.py` (count 7), `tests/unit/features/agents/test_agent_reader.py` (parses `paths.write_allowlist`), any panel test asserting workflow count.
  - Acceptance: full unit test sweep `pytest -q tests/` green.
  - Depends: AGT-r2-07, AGT-r2-20.
- [x] AGT-r2-23 — Author `tests/unit/features/public/test_workspace_guardrail_pair.py` placeholder (qa-engineer)
  - Skeleton with 6 placeholder cases (4-target projection write; 3 skip variants — no-marker / no-`agentic/` / self-slug; nested-pair non-interference; doctor 4-line output). Real assertions land in P9 once installer is built.
  - Acceptance: file imports and collects under pytest; cases marked `@pytest.mark.xfail(reason="implemented in P9")` or `pytest.skip()` with clear reason.
  - Depends: AGT-r2-22. Parallel with: AGT-r2-21.

---

## Phase P8 — Stage + install + doctor checkpoint #1

- [x] AGT-r2-24 — `dadaia public stage && install --target all && doctor` (devops-engineer)
  - Pre-state: P1 trim, P3 paths blocks, P5 path-scope gate, P6/P7 tests landed.
  - Acceptance: `dadaia public doctor` `[ok]` everywhere; stale workflow projections deleted from each target (R4); consumer-repo sweep #1 reports `[ok]` for projected files.
  - Depends: AGT-r2-06, AGT-r2-09, AGT-r2-11, AGT-r2-20, AGT-r2-21, AGT-r2-23.

---

## Phase P9 — Build `_install_workspace_guardrail_pair` (W3, parallel with P10)

- [x] AGT-r2-25 — Implement `_install_workspace_guardrail_pair` in `infrastructure/public_assets.py` (software-engineer)
  - Function signature: `(agentic_dir, workspace_root, force, installed)`.
  - Reads single source `data/AGENTS.md`; enumerates `(workspace_root/"repos").iterdir()` filtered by `(p/".dadaia").is_dir() and (p/".dadaia"/"agentic").is_dir()` (R13); self-skips via `package_version` match in `<repo>/.dadaia/agentic/manifest.json` (R14); writes 4 files per round (workspace root × 2 + each consumer × 2) via existing `_copy_file`.
  - Marker-less consumer → emit `[skip] <path> (no .dadaia/ marker)`; never raises.
  - Legacy `_install_agents_md` / `_agents_md_source` remain in place for the `templates/AGENTS.md` scaffolder.
  - Acceptance: function importable; unit test `test_workspace_guardrail_pair.py` (real assertions) passes its 6 cases.
  - Depends: AGT-r2-24. Parallel with: P10 (AGT-r2-29..AGT-r2-32).
- [x] AGT-r2-26 — Wire `_runtime_expectations` to emit 4 tuples per call (software-engineer)
  - Labels: `root:AGENTS.md`, `root:CLAUDE.md`, `repos/<slug>:AGENTS.md`, `repos/<slug>:CLAUDE.md`.
  - Acceptance: doctor harness produces exactly 4 lines per source; cross-checked by `tests/integration/test_public_doctor_parity.py` (added in this task).
  - Depends: AGT-r2-25.
- [x] AGT-r2-27 — Replace placeholder cases in `test_workspace_guardrail_pair.py` with real assertions (qa-engineer)
  - Cases: 4-target write (byte-identical, single SHA-256); no-`.dadaia/` skip; no-`.dadaia/agentic/` skip; self-slug `package_version` skip; nested-pair non-interference fixture (`services/CLAUDE.md` untouched); doctor 4-line output exactly.
  - Acceptance: `pytest -q tests/unit/features/public/test_workspace_guardrail_pair.py` green; ADR items 2, 4, 5 covered.
  - Depends: AGT-r2-26.
- [x] AGT-r2-28 — Add nested-pair integration fixture (qa-engineer)
  - File: `tests/integration/test_public_install_e2e.py` — verifies `services/CLAUDE.md` + `services/AGENTS.md` exist before install and are byte-identical after install (i.e. NOT overwritten); also asserts byte-identical pair at every projection target (single SHA-256).
  - Acceptance: integration suite green; covers ADR item 5 end-to-end.
  - Depends: AGT-r2-27.

---

## Phase P10 — Inline scope rules + archive 4 rule files (W3)

- [x] AGT-r2-29 — Inline `project-manager-scope.md` into `project-manager.md` body (software-engineer)
  - Add `## Scope and forbidden actions` section copied verbatim from the rule file.
  - Acceptance: `## Scope and forbidden actions` present in `dadaia_workspace/public/agents/project-manager.md`; `wc -l` ≤ 300.
  - Depends: AGT-r2-05. Parallel with: P9 (AGT-r2-25..AGT-r2-28).
- [x] AGT-r2-30 — Inline `project-auditor-scope.md` into `project-auditor.md` body (software-engineer)
  - Acceptance: `## Scope and forbidden actions` section present; rule content preserved verbatim.
  - Depends: AGT-r2-05.
- [x] AGT-r2-31 — Inline `design-specialist-scope.md` into `design-specialist.md` body (software-engineer)
  - Acceptance: `## Scope and forbidden actions` section present; rule content preserved verbatim.
  - Depends: AGT-r2-05.
- [x] AGT-r2-32 — Archive 4 deprecated rule files (software-engineer)
  - `git mv` to `specs/_archive/legacy-rules/<UTC>/`: `project-manager-scope.md`, `project-auditor-scope.md`, `design-specialist-scope.md`, `dadaia-workspace-dev-guardrail.md`.
  - Note: `dadaia-workspace-dev-guardrail.md` content folds into the P11a AGENTS.md rewrite (not into an agent).
  - Acceptance: `ls dadaia_workspace/public/rules/ | wc -l` → 2 (only `game-agents-coordination.md` + `game-developer-scope.md` remain); archived directory contains the 4 moved files.
  - Depends: AGT-r2-29, AGT-r2-30, AGT-r2-31.

---

## Phase P11a — Rewrite `data/AGENTS.md` (W4, parallel with P11c + P12)

- [x] AGT-r2-33 — Rewrite `data/AGENTS.md` to ≤ 280 lines, lib-general scope only (product-engineer)
  - File: `dadaia_workspace/public/data/AGENTS.md` — apply SPEC FR7.9 11-section structure; absorb `dadaia-workspace-dev-guardrail.md` content (per AGT-r2-32 note).
  - Forbidden strings (SPEC FR7.2): no occurrences of `Hostinger`, `redacted-infra`, `redacted-infra`, `Traefik`, `redacted-host`, `redacted-infra-jobs`, `redacted-infra-shopping`, `mistralai`, IP `0.0.0.0`, IP `0.0.0.0` — verified by pre-commit grep exiting 1 on hit.
  - Acceptance: `wc -l dadaia_workspace/public/data/AGENTS.md` ≤ 280; pre-commit forbidden-strings grep returns clean; C16 + C17 + C18 + C19 + C21 + C22 + C23 satisfied.
  - Depends: AGT-r2-32. Parallel with: P11c (AGT-r2-37..AGT-r2-38), P12 (AGT-r2-39..AGT-r2-42).
- [x] AGT-r2-34 — Assert absence of `data/CLAUDE.md` source (product-engineer)
  - Acceptance: `! test -e dadaia_workspace/public/data/CLAUDE.md` (Option C invariant). Captured as a unit assertion in `tests/unit/features/public/test_workspace_guardrail_pair.py`.
  - Depends: AGT-r2-33.

---

## Phase P11b — Wire installer + doctor for Option C

- [x] AGT-r2-35 — Dispatch install call site to `_install_workspace_guardrail_pair` (software-engineer)
  - Replace legacy `_install_agents_md` call for `data/AGENTS.md` only (templates scaffolder retains its own call).
  - Acceptance: a single call to `_install_workspace_guardrail_pair` per workspace; trace via test that 4 files write per round.
  - Depends: AGT-r2-25, AGT-r2-33.
- [x] AGT-r2-36 — Update `.dadaia/agentic/manifest.json` for Option C (software-engineer)
  - Recompute SHA-256 of `data/AGENTS.md` post-P11a; manifest entry updated; **no** `data/CLAUDE.md` entry exists.
  - Acceptance: `grep -c '"data/CLAUDE.md"' .dadaia/agentic/manifest.json` → 0; `dadaia public doctor` reports `[ok]` for `data/AGENTS.md`; C24 + C25 satisfied.
  - Depends: AGT-r2-35.

---

## Phase P11c — Author FR10 operator manual-migration checklist (W4)

- [x] AGT-r2-37 — Create CLOSURE.md stub with `## Operator manual migration (FR10)` section (product-engineer)
  - File: `specs/releases/agents-r2-v1/CLOSURE.md` (stub; full sections finalised in P14).
  - Section content (literal commands): (1) capture pre-r2 workspace-root `CLAUDE.md` SHA; (2) author `services/CLAUDE.md` with redacted-infra / redacted-infra / Traefik sections; (3) mirror to `services/AGENTS.md`, verify byte-identical via `sha256sum`; (4) run `dadaia public stage && install --target all && doctor`; (5) post-verify: workspace-root pair sha256-match, forbidden-strings grep on root `CLAUDE.md` exits 1, same grep on `services/CLAUDE.md` exits 0.
  - Acceptance: section present with the 5 numbered command groups; PR description (AGT-r2-44) cross-references this section.
  - Depends: AGT-r2-05. Parallel with: P11a, P12.
- [x] AGT-r2-38 — Cross-reference FR10 section from SPEC + PLAN (product-engineer)
  - Acceptance: `grep "Operator manual migration" specs/releases/agents-r2-v1/{SPEC,PLAN}.md` → at least 1 hit each (links to CLOSURE section).
  - Depends: AGT-r2-37.

---

## Phase P12 — Skill orphan wiring + verification script (W4)

- [x] AGT-r2-39 — Wire `dadaia-workspace-doctor` skill into devops-engineer + project-manager (software-engineer)
  - Files: `dadaia_workspace/public/agents/{devops-engineer,project-manager}.md` — `skills:` frontmatter gains `dadaia-workspace-doctor`.
  - Acceptance: `grep "dadaia-workspace-doctor" dadaia_workspace/public/agents/devops-engineer.md dadaia_workspace/public/agents/project-manager.md` → ≥ 2 hits.
  - Depends: AGT-r2-32. Parallel with: P11a, P11c.
- [x] AGT-r2-40 — Wire `dev-server-registry` skill into frontend-engineer (software-engineer)
  - File: `dadaia_workspace/public/agents/frontend-engineer.md` — `skills:` frontmatter gains `dev-server-registry`.
  - Acceptance: `grep "dev-server-registry" dadaia_workspace/public/agents/frontend-engineer.md` → 1 hit.
  - Depends: AGT-r2-32.
- [x] AGT-r2-41 — Author orphan-skill detection script (software-engineer)
  - File: `tests/scripts/check_skill_orphans.py` (≤ 50 lines). Asserts every skill in `dadaia_workspace/public/skills/<name>/` is referenced by ≥ 1 agent frontmatter in `dadaia_workspace/public/agents/*.md`.
  - Acceptance: script exits 0 against the post-P11a/P12 tree; exits 1 if a seeded orphan is present.
  - Depends: AGT-r2-39, AGT-r2-40.
- [x] AGT-r2-42 — Self-test for orphan-detection script (qa-engineer)
  - File: `tests/unit/scripts/test_check_skill_orphans.py` — seeds a fake-orphan and a fake-wired skill in a tmp tree, asserts detector flags only the orphan (R11).
  - Acceptance: `pytest -q tests/unit/scripts/test_check_skill_orphans.py` green; CI hook (pytest collection) catches future orphans.
  - Depends: AGT-r2-41.

---

## Phase P13 — Stage + install + doctor checkpoint #2 + consumer-repo audit

- [x] AGT-r2-43 — `dadaia public stage && install --target all && doctor` against final state (devops-engineer)
  - Acceptance: `dadaia public doctor` reports `[ok]` everywhere; stale rule projections deleted from each target (R12); doctor emits exactly 4 parity lines per source (`root:AGENTS.md`, `root:CLAUDE.md`, `repos/<slug>:AGENTS.md`, `repos/<slug>:CLAUDE.md`), all `[ok]`; `sha256sum` cross-check confirms all projected `{AGENTS,CLAUDE}.md` share one unique hash per workspace+consumer (R9).
  - Depends: AGT-r2-28, AGT-r2-36, AGT-r2-42.
- [x] AGT-r2-44 — Consumer-repo audit sweep (devops-engineer)
  - For each marker-bearing consumer (`redacted-slug`, `redacted-slug`, `workflow-tools`): verify both `AGENTS.md` and `CLAUDE.md` at repo root share the source SHA-256; verify `dadaia-workspace` self-skipped (R14 / `package_version` match).
  - Acceptance: 6 `[ok]` lines (3 consumers × 2 files); 1 `[skip]` for `dadaia-workspace`; nested `services/{AGENTS,CLAUDE}.md` untouched (byte-equal to pre-install snapshot).
  - Depends: AGT-r2-43.
  - Finding: none of `redacted-slug`, `redacted-slug`, `workflow-tools` have `.dadaia/agentic/` marker — installer correctly emits `[skip]` for all 7 repos under `repos/`. workspace-root pair verified: `root:AGENTS.md` + `root:CLAUDE.md` both SHA `930d26eb…` ✓. `dadaia-workspace` self-skipped (package_version=0.1.0) ✓. `services/{AGENTS,CLAUDE}.md` absent (operator has not yet authored them — FR10 manual step) ✓ non-interference.
- [x] AGT-r2-45 — Open PR with description linking CLOSURE FR10 section (devops-engineer)
  - PR body MUST link `specs/releases/agents-r2-v1/CLOSURE.md#operator-manual-migration` (R10).
  - Acceptance: PR exists; description contains the anchor link; CI green.
  - Depends: AGT-r2-44.

---

## Phase P14 — CLOSURE (final phase)

- [-] AGT-r2-46 — Flip `ACTIVE.md` to `phase: CLOSURE` to unlock memory writes (product-engineer)
  - Acceptance: `cat specs/releases/ACTIVE.md` reports `phase: CLOSURE` for `release: agents-r2-v1`.
  - Depends: AGT-r2-45.
- [ ] AGT-r2-47 — Dispatch qa-engineer for `dadaia panel` smoke (qa-engineer via product-engineer)
  - Validates: 16 agents visible, 7 workflows visible, FR10 operator-migration commands executed in dry-run.
  - Acceptance: smoke report at `.dadaia/reports/dadaia-workspace/qa-engineer/<UTC>-agents-r2-v1-panel-smoke.html` + sidecar; screenshot embedded; C8 satisfied.
  - Depends: AGT-r2-46.
- [ ] AGT-r2-48 — Finalize `CLOSURE.md` Summary + Tasks + Validations + Drifts (product-engineer)
  - Sections per `dadaia-release-closure` skill: Summary, Tasks completed (SHAs), Validations (triples), Drifts (per-slug), Memory updates, Backlog returns, Archive: MOVE.
  - Acceptance: file passes `dadaia specs doctor` CLOSURE-evidence invariant; FR10 manual-migration evidence (operator's before/after `sha256sum`) embedded in `## Validations`.
  - Depends: AGT-r2-47.
- [ ] AGT-r2-49 — Update `specs/memory/architecture.html` (product-engineer)
  - `<section id="layers">` gains 3 notes per SPEC FR5: path-scope gate is now active; `paths:` is enforced per-agent; rule-file inlining moved 3 scopes into agent bodies.
  - Acceptance: rendered HTML lints clean (`dadaia specs doctor`); memory atomicity preserved (no Changelog section).
  - Depends: AGT-r2-48.
- [ ] AGT-r2-50 — Update `specs/memory/product/index.html` + `agent-orchestration.html` (product-engineer)
  - `product/index.html`: catalog reflects workflow count = 7.
  - `product/agent-orchestration.html`: 16 agents + 7 workflows + 8 PM playbooks + path-scope gate + 2 rules + Option C dual-name projection note.
  - Acceptance: both HTMLs render with current state only; no history sections; `dadaia specs doctor` clean.
  - Depends: AGT-r2-48.
- [ ] AGT-r2-51 — Record FR9 decision + backlog returns (product-engineer)
  - `CLOSURE.md` `## Backlog returns` adds: `--repos-only` / `--workspace-only` flags → `specs/backlog/candidates.md`; per-projection opt-out marker → `specs/backlog/ideas.md`.
  - Files written: `specs/backlog/candidates.md` (append), `specs/backlog/ideas.md` (append).
  - Acceptance: both backlog files contain the new bullets; CLOSURE links them.
  - Depends: AGT-r2-48.
- [ ] AGT-r2-52 — Final `dadaia specs doctor` → 0/0 (product-engineer)
  - Acceptance: `dadaia specs doctor` exits clean (0 errors, 0 warnings); output captured into the PE report.
  - Depends: AGT-r2-49, AGT-r2-50, AGT-r2-51.
- [ ] AGT-r2-53 — Archive release + reset `ACTIVE.md` (product-engineer)
  - `git mv specs/releases/agents-r2-v1 specs/_archive/releases/agents-r2-v1`.
  - Update `specs/releases/ACTIVE.md` → `release: none, phase: none`.
  - Acceptance: archive dir exists; `specs/releases/` no longer contains the release; ACTIVE.md reset; all 26 acceptance criteria satisfied (C1–C26).
  - Depends: AGT-r2-52.

---

## Risky tasks flagged by PE

- **AGT-r2-19** — Path-scope gate must fail-open cleanly when the runtime cannot determine the active agent (NFR3). The ADR pattern from AGT-r2-12 is the source of truth; if the harness env-var/payload field choice is wrong, the gate either blocks human top-level invocations (bad) or silently allows everything (worse). Mitigate via the explicit `/tmp/sdd-gate.log` warning + a unit test that asserts the fail-open path emits the warning string.
- **AGT-r2-25 / AGT-r2-27** — `_install_workspace_guardrail_pair` interacts with the existing `_install_agents_md` function. R14 self-projection (`package_version` match) is silent: a faulty manifest check could either self-clobber the workspace's own `data/AGENTS.md` source (catastrophic) or skip a legitimate consumer that happens to ship a coincidentally-matching version string. Mitigate via two distinct fixture scenarios in AGT-r2-27 and a P13 cross-check on consumer-repo audit (AGT-r2-44).
- **AGT-r2-33** — Forbidden-strings grep (Hostinger / redacted-infra / redacted-infra / Traefik / `mistralai` / public IPs) on `data/AGENTS.md` is the bright-line invariant for Option C. If a single string slips through, the lib leaks operator-specific deployment data into every projection. Pre-commit hook plus the explicit grep in acceptance row must run on every commit touching this file.
- **AGT-r2-37 / AGT-r2-44** — FR10 is a manual operator task. The CLOSURE-section commands must be **literal** (copy-paste ready) and the P13 audit must surface any case where `services/{CLAUDE,AGENTS}.md` were silently touched by install (R5). Nested-pair non-interference is verified at both unit (AGT-r2-27) and integration (AGT-r2-28) layers, but the live operator step is uncovered until P14 smoke.
