# Audit — Specs & Memory Content-Scoping Review

- **Date:** 2026-07-02 (UTC)
- **Auditor session:** 56b226fb (Claude Layer-1, 5 parallel review lanes, no dadaia-workflows)
- **Scope:** `specs/constitution.md`, `specs/memory/architecture.md`, `specs/memory/quality-assurance.md`, `specs/memory/tech-stack.md`, `specs/memory/AGENTS.md`, all 31 `specs/memory/product/<area>/*.md` atoms, `product/catalog.json` + `product/index.md`, plus specs-tree hygiene.
- **Question:** is every fact in its owning file, scoped per the memory contract, direct, unambiguous, divergence-free — and true against the code at `b8c40708` (post v0.1.47)?
- **Baseline:** lint-memory-atoms 34 atoms 0/0; catalog 31↔31 in sync; zero broken wikilinks; all doctors green.
- **Disposing release:** v0.1.48 (this audit's findings are fully dispositioned there — see `SPEC.md §Dispositions`).

## Scorecard

| Surface | Verdict |
|---|---|
| constitution.md | CLEAN (3 minor mechanism leaks) |
| quality-assurance.md | CLEAN (repetition + 1 PT paragraph) |
| architecture.md | NEEDS-WORK (roster re-enumeration, mechanism depth, version-tagged headings) |
| tech-stack.md | NEEDS-WORK (3 verified-false claims, misplaced mechanism) |
| memory/AGENTS.md | NEEDS-WORK (frontmatter guidance contradicts schema; gate overclaim) |
| product/sdd/ | 3 CLEAN / 3 NEEDS-WORK (specs-doctor 008 contradiction; lifecycle changelog-style; hotfix-track = history atom) |
| product/agents/ | 1 BLOCKER (codex matcher), 4 skill-mirror atoms to delete, 1 merge, 2 keep+rewrite |
| product/harness/ | ALL CLEAN — verified accurate; sole harness-truth owners |
| product/platform/ | 3 CLEAN / 4 NEEDS-WORK (bind-epoch stale ×2, deprecated bug CLI taught, fact duplication) |
| product/panel/ | NEEDS-WORK (expand + routing claims false; history column) |
| product/distribution/ | CLEAN |
| product/philosophy/ | 1 CLEAN / 2 minor (misfiled utility atom; normative-source delta) |
| catalog.json + index.md | sync perfect; generator GFM bug (registered: `memory-index-table-broken-gfm`); 3 no-signal fields; 13 PT / 17 EN split |

## Systemic finding

Every major divergence traces to one structural defect: **a fact with more than one home**. The Codex PreToolUse matcher lived in 3 places (one went stale — the BLOCKER); bind-epoch semantics in 2 (both went stale together after v0.1.47 W1c); lease mechanics in 2; Codex hook-wrapper registration in 4. The memory contract already prescribes single ownership + `[[wikilinks]]`; the content predates the discipline.

## Findings

IDs F-01..F-84. Severity: BLOCKER / MAJOR / MINOR. Location cites are against `b8c40708`.

### BLOCKER
- **F-39** `product/agents/ai-harness-codex.md:63-64` — states Codex PreToolUse matcher `^(apply_patch|Edit|Write)$`; deployed truth is `^(apply_patch|Edit|Write|Bash)$` (`infrastructure/runtime_config.py:183`). Erases the venv-guard Bash leg. Root cause: triple maintenance surface (skill file → mirror atom → harness atom).

### MAJOR — verified-false or divergent truth
- **F-01** `tech-stack.md:52,155` — "claude-agent-sdk não entra em poetry.lock" is false (`poetry.lock:204`; optional extra `claude-sdk`).
- **F-02** `tech-stack.md:91-93` — plugin-stub model rows fabricated; stubs carry no `model:` frontmatter.
- **F-03** `tech-stack.md:97-104` — plugin-scope rule misdescribed; dangling ADR-X7/X5 cites.
- **F-06** `memory/AGENTS.md:44-45` — instructs 4 frontmatter fields; schema `memory-frontmatter-v1` requires 10 with `additionalProperties: false`.
- **F-07** `memory/AGENTS.md:19` — "write-lock enforced by the SDD gate" overclaims; gate enforces the phase half only.
- **F-26** `product/sdd/specs-doctor.md:33,87` — SPEC-DOC-008 described 3 incompatible ways; code truth: live memory-atomicity forbidden-heading ERROR (`features/specs/doctor.py:1989-2017`).
- **F-27** `product/sdd/lifecycle-foundation.md:122-125` — "five built-in profiles"; code has six (`model_profiles.py:58-108`, incl. `pi-openrouter-kimi-high`).
- **F-40** `product/agents/agent-monitoring.md:77` — `events_daily` retention/compaction/deletion machinery does not exist; only a `window_days=180` query default.
- **F-41** `product/agents/agent-comms.md:43` — handoff schema misstated ×3 (findings[] optional; artifact requires only `type`; schema_version is an enum).
- **F-43/F-44** `product/agents/agent-comms.md:97,101` — shipped `reports next` listed as deferred; ghost agents (`backend-engineer`, `game-*`).
- **F-45** `product/agents/agent-monitoring.md:65,84` — references the removed panel "Agents" tab.
- **F-56** `product/platform/context-management.md:88-96,200` AND `product/sdd/sdd-gate-v3.md:128-133` — bind-epoch marker described as single pid; code writes an ancestry pid chain with membership matching (v0.1.47 W1c; `session_identity.py:215-244`, `ctx_inject.py:134-166`).
- **F-57** `product/panel/panel.md:49,109-112` — card expand claimed via `#workflows?detail=` + API fetch; code renders inline `<details>` server-side; `GET /api/workflows/<name>` is UI-unconsumed.
- **F-58** `product/panel/panel.md:38,47` — hash-routing grammar overstated (only `#workflows`/`#reports`/`#academy` handled; `core.js:249-264`).
- **F-59** `product/platform/context-management.md:24-25,37,171` — teaches deprecated `dadaia bug new` as the current bug path.

### MAJOR — ownership / duplication structure
- **F-42** delete 4 skill-mirror atoms (`ai-harness-codex`, `ai-harness-claude-code`, `ai-context-engineering`, `harness-primitives`) — lossy duplicates of their SKILL.md sources; migrate unique facts to `harness/harness-codex.md` / tech-stack first.
- **F-46** `agent-sdd-alignment.md` ≈40% verbatim overlap with `agent-orchestration.md` (constitution §9 prose) — merge uniques, delete.
- **F-30** `sdd-hotfix-track.md` — self-declared "historical reference only" atom; violates the memory contract; current truth already in `sdd-bug-backlog-governance.md`. Archive + remove dangling wikilink.
- **F-60** lease mechanics stated in full in both `context-management.md` and `sdd-gate-v3.md` (~40 lines each).
- **F-61** Codex hook-wrapper/matcher/install-`--force`/`.pi/`-surface facts restated across 4 atoms (workspace-init, cross-platform-portability, multi-platform-parity, public-asset-distribution).
- **F-05** `architecture.md:261,277-283` — re-enumerates the Layer-2 roster + all `AgentRuntimeKind` members vs constitution §0 single-source (tension with §4 posture tables).
- **F-28** `lifecycle-foundation.md` restates the workflow roster owned by `dadaia-workflows.md`, with zero `[[dadaia-workflows]]` links.
- **F-29** `lifecycle-foundation.md:6-37,110,285-358` — changelog-style narrative; live-proof story told 3×; commit-hash archaeology.
- **F-66** `philosophy/repos-catalog.md` — a platform CLI utility misfiled under philosophy/.

### MAJOR — catalog / language
- **F-73** generated `product/index.md` table is broken GFM (blank line after separator; both renderer implementations). Registered as bug `memory-index-table-broken-gfm`.
- **F-74** memory speaks two languages: 13 PT / 17 EN / 1 mixed catalog entries; PT canon headings over EN bodies. Operator decision 2026-07-02: **English canon**.

### MINOR (grouped)
- Truth/wording: F-08 (tech-stack pytest row omits taxonomy owner), F-09 (version-pin drift), F-20 (`--force` comment vs dev-guardrail), F-35 (specs-doctor tldr implies 022/023 emitted), F-36 (CLI surface omits `handoffs doctor`), F-48 (emitter projection targets wrong for `.codex/`/`.pi/`), F-49 (stale LoC claim), F-50 (`user_version=5` vs 6), F-51 (mermaid cites ghost `reader/workflows.py`), F-53 (history section + instance-path leak), F-62 ("hard-coded" vs loopback-validated `--bind`), F-63 (runtime switcher 2 vs 3 values), F-64 (workspace-init root-probe claim wrong), F-65 (repos-catalog omits programmatic consumer), F-67 (`DADAIA_CONTEXT` export claim), F-68 (`authedFetch` naming), F-70 (`docs/01_medium_codex.md` pillar still says OpenCode), F-72 (panel module inventory omissions).
- Scoping: F-04 (ctx-inject mechanism inside tech-stack's Bash row), F-10 (import-linter fact ×3 files), F-11/F-12/F-13 (constitution mechanism leaks + "never enumerates" ambiguity), F-14/F-15 (architecture mechanism nuggets), F-16 (version tags in headings), F-17 (negative store inventory), F-18 (telemetry runtime set ×2), F-19 (§13 "ADRs" promise unmet), F-21 (handoff schema section in tech-stack), F-22 (PI facts ×2 in one file), F-23 (QA intra-file repetition), F-33 (gate-v3 pre-commit hook enumeration incomplete), F-34 (gate-v3 states path-class facts twice), F-47 (orchestration restates harness atoms), F-52 (broken relative link; moot via F-43), F-69 (brand-identity history column), F-71 (panel no-auth/kanban stated 4×).
- Catalog/meta: F-75 (area invisible — all `category: product`), F-76 (`agent_tier` dead metadata), F-77 (`rank` = file order, injected into session digests), F-78 (docstring drift `product/*.md`), F-79 (heading-allowlist dead strings; no EN canon), F-80 (token_estimate drift ≤19%), F-84 (two renderer implementations diverge in field order/timestamp shape), F-25 (quality-assurance `category: product` vs trio `core`).
- Hygiene: F-81 (`specs/releases/v0.1.23/` delivered v0.1.28/29-era, never archived), F-82 (14 orphan PNGs in `specs/backlog/img/`, referenced by nothing), F-83 (empty untracked `docs/img`).
- Language/residual: F-24 (`quality-assurance.md:70-73` — one Portuguese paragraph inside an otherwise English body), F-54 (PT/EN mixing within single atoms — e.g. `agent-comms.md` full-EN schema paragraph + EN headers inside a PT body; `product-vision.md` EN prose under PT canon headings), F-38 (`sdd/dadaia-workflows.md:56-70` — "Fluxo de uso" steps briefly restate engine mechanics owned by `lifecycle-foundation`; trim toward pure references), F-31 (`sdd/sdd-hotfix-track.md:74` — vintage cutoff "≤ 2026-05-17" vs code `RELEASE_VINTAGE_CUTOFF = 2026-06-04`), F-32 (`sdd/sdd-hotfix-track.md:84` — cites a constitution hotfix mention that no longer exists post-v0.1.47 rewrite), F-37 (`sdd/sdd-hotfix-track.md:5-8` — `summary` duplicates `tldr` verbatim), F-55 (`agents/ai-harness-claude-code.md:67-68` — cites instance-local `.dadaia/academy/06_claude/` instead of the library source `features/academy/knowledge_basis/06_claude_code/`).

## Verified-clean (no action)
constitution.md invariants (0 runtime-enum tokens, 0 OpenCode, SPEC-DOC-037 live); quality-assurance.md claims vs CI (10+5 jobs, markers, 80% CI-only gate); `harness/{claude-code,codex,pi}.md` (every spot-check matched code); `sdd/dadaia-workflows.md`, `sdd/sdd-bug-backlog-governance.md`, `sdd/sdd-gate-v3.md` mechanism sections; `platform/{workspace-doctor,server-registry,workspace-portability}.md`; `distribution/{public-asset-distribution,academy}.md`; `philosophy/spec-context-project.md`; catalog sync core (31↔31, wikilinks, `depends_on`, lint 0/0, freshness).
