# TASKS — v0.1.48 — Memory Single-Ownership + Truth + English Canon

**Status:** Aprovado

Markers: `[ ]` open · `[-]` in progress · `[x]` done. One `[-]` per owner unless write sets are
disjoint. Finding IDs refer to `specs/audits/20260702T015037Z-56b226fb/audit.md`; dispositions in
SPEC §5.

## W0 — closure of v0.1.47 + definition

- [x] T-48-01 Archive `specs/releases/v0.1.47/` → `_archive/releases/` + commit bug event (commit `6c3e086e`). Owner: orchestrator.
- [x] T-48-02 Commit audit artifact + GRILL/SPEC/PLAN/TASKS (Aprovado) + ACTIVE → v0.1.48 DEFINITION. Owner: product-engineer (orchestrated).

## W1 — memory truth fixes (write set: existing `specs/memory/**` files, `public/data/memory-AGENTS.md`, `public/scaffold/memory/AGENTS.md`, `docs/01_medium_codex.md`)

- [x] T-48-10 tech-stack.md: F-01 lockfile claim, F-02 stub model rows, F-03 plugin-scope rewrite (drop ADR-X7/X5), F-08 pytest row → [[quality-assurance]], F-09 pin drift, F-20 `--force` comment.
- [x] T-48-11 sdd atoms: F-26 SPEC-DOC-008 (both spots), F-27 six profiles, F-35 tldr 022/023, F-36 add `handoffs doctor`; F-56 bind-epoch → ancestry-chain membership in BOTH `context-management.md` and `sdd-gate-v3.md`; F-59 `bug new` → legacy note + [[sdd-bug-backlog-governance]].
- [x] T-48-12 agents atoms (keepers only): agent-comms F-41 schema → schema-path pointer, F-43/44 delete "Fora de escopo", F-48 emitter targets, F-49 LoC, F-53 delete "Referência" history+instance path; agent-monitoring F-40 events_daily, F-45 Agents tab ×2, F-50 user_version, F-51 mermaid ghost node.
- [x] T-48-13 panel/platform/philosophy: panel.md F-57 inline `<details>` truth + F-58 route grammar + F-62 loopback-validated + F-63 switcher values (verify UI first) + F-72 module list; workspace-init F-64 root-probe; repos-catalog F-65 programmatic consumer; context-management F-67 env-export claim; academy F-68 authedFetch note.
- [x] T-48-14 memory-AGENTS in THREE copies (install never overwrites the specs-tree copy — scaffold-on-missing only): F-06 frontmatter fields per schema + F-07 gate-overclaim split applied to `specs/memory/AGENTS.md` (directly), `public/data/memory-AGENTS.md`, and `public/scaffold/memory/AGENTS.md`, kept byte-identical (AC-8); then `public stage && install --target all && public doctor` exit 0 for the staged copies. F-70 docs/01_medium_codex.md pillar line (OpenCode → PI).

## W2 — ownership consolidation (write set: `specs/memory/**`, `specs/constitution.md`, `specs/_archive/memory/**`)

- [x] T-48-20 F-42 migrate unique facts (codex tier-views, D-CX-4, live-test harness → harness-codex/tech-stack), then delete `ai-harness-codex.md`, `ai-harness-claude-code.md`, `ai-context-engineering.md`, `harness-primitives.md`; keep skill-roster pointer lines in agent-orchestration.
- [x] T-48-21 F-46 merge `agent-sdd-alignment.md` uniques (phase table + ai-engineer carve-out, step0 read order, memory-format law) into `agent-orchestration.md`; delete atom; re-home the live inbound wikilink `product-vision.md:195 [[agent-sdd-alignment]]` → `[[agent-orchestration]]`. F-47 shrink runtime-dispatch section to wikilinks.
- [x] T-48-22 F-30 archive `sdd-hotfix-track.md` → `specs/_archive/memory/`; remove dangling wikilink + fold `specs hotfix open` coexistence into sdd-bug-backlog-governance.
- [x] T-48-23 F-60 lease single-home (gate-v3 owns acquire/liveness/heartbeat; context-management keeps bind/release/session lifecycle + wikilink); F-61 codex-wrapper/install/`.pi/` facts → public-asset-distribution, cite from workspace-init/cross-platform-portability/multi-platform-parity; F-33/F-34 gate-v3 dedup + pre-commit completeness.
- [x] T-48-24 architecture.md: F-05 de-enumeration (G7), F-14/15 mechanism trims, F-16 heading version tags, F-17 negative inventory, F-18 telemetry set once, F-10 import-linter single statement. tech-stack.md: F-04 Bash-row mechanism out, F-21 handoff section → pointer, F-22 PI facts once.
- [x] T-48-25 constitution.md: F-11 registry-validation abstraction, F-12 commit_sha field abstraction, F-13 "never enumerates" rephrase (G7), F-19 §13 ADR wording. quality-assurance.md F-23 repetition compress. panel F-69 brand history column + F-71 no-auth/kanban compress. F-66 `git mv` repos-catalog → `product/platform/`. F-28/F-29 lifecycle-foundation de-changelog + roster → [[dadaia-workflows]]; F-38 trim `dadaia-workflows.md` "Fluxo de uso" engine restatements toward references. Then `dadaia memory catalog generate` + lint 0/0.

## W3 — code (write set: PLAN §Write sets W3)

- [x] T-48-30 F-73 GFM fix both renderers + contract test pinning table shape; F-84 align output shape between implementations; F-78 docstrings.
- [x] T-48-31 F-75 `area` derived from parent dir (catalog field + index.md grouping); F-77 drop `rank` from `_DIGEST_FIELDS`; F-25 quality-assurance `category: core`.
- [x] T-48-32 F-79 lint-memory-atoms: English Group-A canon added, dead strings pruned, PT legacy kept; tests assert both canons pass. core.js stale `#agents` comment. Bug `specs-doctor-tree5m-remediation-wrong`: fix TREE-5M remediation text in `features/specs/doctor.py` (~2503-2520) to state the real repair (edit the file/scaffold copies; install does not project it).
- [x] T-48-33 Full gate: pytest (minus performance), ruff format --check, ruff check, mypy --strict — all green; regenerate catalog/index with fixed generator. NOTE: 1 pre-existing e2e failure (`test_lifecycle_engine_smoke::test_temp_workspace_lifecycle_engine_smoke`) reproduced at HEAD 78012790 with W3 changes stashed — caused by W0/W2 tree state outside the W3 write set (SPEC-DOC-006 ×2 on `specs/_archive/releases/v0.1.47/CLOSURE.md`; SPEC-DOC-024 ACTIVE.md phase vs [x]-majority), not by W3 code.

## W4 — English canon (write set: surviving `specs/memory/**` + regenerated catalog/index)

- [ ] T-48-40 Translate set A (platform 7 + panel 2 + distribution 2 + philosophy 2): bodies, frontmatter, Group-A headings → English canon; token_estimate refresh.
- [ ] T-48-41 Translate set B (agents 3 keepers + sdd 5 + harness 3 + architecture/tech-stack/quality-assurance residual PT): same contract.
- [ ] T-48-42 Regenerate catalog + index; LINT-1 0/0; CAT-1 clean; AC-4 greps = 0.

## W5 — hygiene

- [ ] T-48-50 F-81 `git mv specs/releases/v0.1.23 specs/_archive/releases/`; F-82 delete `specs/backlog/img/`; F-83 delete `docs/img`; specs+backlog+public+workflow doctors green.

## W6 — ship

- [ ] T-48-60 ACTIVE → CLOSURE; CLOSURE.md (incl. deletion list per G10); terminal `resolved --release v0.1.48` events for BOTH picked bugs (`memory-index-table-broken-gfm`, `specs-doctor-tree5m-remediation-wrong`); audit → `specs/audits/_archive/` + DISPOSITION.md; backlog `hygiene-and-dead-code-cleanup` gains agent_tier item (F-76).
- [ ] T-48-61 qa-engineer release checkpoint (APPROVE required); security-reviewer handoff keyed to final sha; push (nohup+Monitor); CI watch until every job green; open PR.
