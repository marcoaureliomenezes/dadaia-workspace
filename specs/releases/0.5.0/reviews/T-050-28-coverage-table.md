# T-050-28 — FR17 coverage table: the memory trio's Part 1 / Part 2 split

**Author role:** product-engineer · **Task:** T-050-28 · **Release:** 0.5.0, segment `S4`
**Acceptance covered:** A17.1 (two top-level parts, in order), A17.2 (`P-NN` + `Measured by:`
+ `ADR:` per entry), **A17.3 (this table — no law dropped silently)**, A17.4 (`product/**`
atoms carry no architecture principle), A17.5 (no `Changelog`/`History`/`Histórico`/
`Versions`; no commit shas; current-state only).

**Inputs:** `specs/releases/0.5.0/reviews/S4-principle-inventory.md` §4 (the binding split
plan; every `U-n` / `B-n` / `STALE` id below is that file's), SPEC FR17/FR18, ruling D13,
the pre-rewrite state of `specs/memory/{ARCHITECTURE,QUALITY,TECHSTACK}.md` at HEAD.

**Line numbers** in the first column are the **pre-rewrite** file's, so a reviewer can diff
old → new row by row.

**Legend.** `P1` = promoted to Part 1 as the named principle · `P2` = re-homed into Part 2 ·
`DELETED` = removed from memory with the reason stated · `STALE→P2` = contradicted the tree
and was rewritten in Part 2 · `U-n` = the inventory's unmeasured-prose id (22 of them; every
one is accounted for below and none appears under `## Part 1`).

**Part-1 counts written:** `ARCHITECTURE.md` **17** (P-01…P-17) · `QUALITY.md` **10**
(P-18…P-27) · `TECHSTACK.md` **1** (P-28) · total **28**, one ADR each
(`specs/ADRs/0001…0028`), every entry carrying `ADR: NNNN (proposed)` — the operator flips
them at T-050-31.

---

## 1. `specs/memory/ARCHITECTURE.md` — 38 rows

| # | Old section (pre-rewrite line) | Disposition | New home / reason |
|---|---|---|---|
| A1 | Frontmatter (1–22) | P2 | Rewritten for the two-tier shape: `tldr`/`summary` describe Part 1 + Part 2, `last_updated: '2026-08-27'`, `release_origin: 0.5.0`; schema fields unchanged |
| A2 | Overview (24–43) — three-ring mermaid, ring responsibilities | P2 | `Part 2 › Overview` (mermaid kept verbatim) |
| A3 | Overview (45–46) — "New feature code depends on ports" | **P1** | **P-01** (`features-no-infrastructure`) |
| A4 | Overview (47–51) — accepted-ignore cap ratchets down, same-commit rationale | **P1** | **P-10** (`test_import_linter_ignore_cap.py`) |
| A5 | Overview (43) — "`container.py` is the only general composition root" (**U-1**) | P2 | `Part 2 › Overview`, reworded to "the general composition root the CLI and the panel build through" — no check asserts singularity, so the absolute claim is not made |
| A6 | Overview (51–53) — function-scoped lazy-import idiom (**U-2**) | P2 | `Part 2 › Overview`, as the idiom the capped edges use |
| A7 | Overview (55–58) — "ships no agent-execution runtime" (**U-3**) | P2 | `Part 2 › Overview` (product posture, no measure) |
| A8 | Overview (49–51) — "net direction … reviewable number in that release's CLOSURE" | **DELETED** | `CLOSURE.md` retired (T-050-21); the accounting has exactly one home, `QUALITY.md` Part 2's `closure-size-accounting` note — restating it here would be a second home |
| A9 | `## Primary Subsystems` (60) — grouping heading | **DELETED** | Grouping-only heading; its children are now `###` siblings inside Part 2 (A17.1 needs exactly two `##`) |
| A10 | Context and SDD (62–70) | P2 | `Part 2 › Context and SDD` (+ the ctx-inject digest pointer to [[tech-stack]]) |
| A11 | Context and SDD (66) — "There is no lease or locking module" (**U-4**) | P2 | `Part 2 › Context and SDD`, with the law pointer to `DADAIA.md` §3; no restatement of the law |
| A12 | The resolution seam (72–84) — single authority, three sanctioned importers | **P1** | **P-09** (`bind-resolution-seam-is-a-single-home`); the seam's description stays in Part 2 |
| A13 | The resolution seam (84–88) — "no hook imports `container`" | **P1** | **P-12** (`test_hook_import_surface.py`) |
| A14 | The resolution seam (90–94) — exit codes, injected git identity (**U-5**) | P2 | `Part 2 › Context and SDD` |
| A15 | Git chokepoints (96–101) — script list | P2 | `Part 2 › Git chokepoints` |
| A16 | chokepoints purity (103–104) — "spawns no subprocess" | **P1** | **P-02** (`features-no-subprocess`) |
| A17 | chokepoints purity (103–110) — "imports no `infrastructure` module" (**STALE**) | **STALE→P2** | False today (`setup.cfg` declares the lazy `chokepoints.service → infrastructure.jsonl_log_rotation`). Rewritten: no module-load-time edge; one function-scoped edge, declared and capped under P-10 |
| A18 | `GitObjectReader` port contract (112–121) | P2 | `Part 2 › Git chokepoints` |
| A19 | `core/redaction.py` (123–131) | P2 | `Part 2 › Git chokepoints`, with the file-I/O set reference repointed to P-11 |
| A20 | Handoffs and reports (133–138) | P2 | `Part 2 › Handoffs and reports` |
| A21 | Panel (140–146) | P2 | `Part 2 › Panel` |
| A22 | Public assets (148–168) — projection chain, "never edited in place", underived surface forbidden (**B-1**, **B-2**) | P2 | `Part 2 › Public assets`, each rule now citing its check (`test_agentic_entities_derivation.py`, `test_public_scripts_thin_wrapper.py`) — Tier-B, promotable at the FR20 sitting |
| A23 | Specs and memory (170–182) — one lint implementation, derived catalog, closed frontmatter (**B-3**) | P2 | `Part 2 › Specs and memory`, citing `test_memory_catalog_render_contract.py`; the `agent_tier`-is-rejected sentence kept verbatim in meaning (pinned by `test_memory_agents_doc_schema_consistency.py`) |
| A24 | Specs and memory (183–190) — SpecsDoctor coordinator + drift-guard | **P1** + P2 | **P-13** carries the drift-guard; the coordinator description stays in Part 2 |
| A25 | Other feature domains (194) — "event-sourced bug state" (**STALE**) | **STALE→P2** | Retired by FR2/D11. Rewritten: one record per bug, appended once, with an enumerated set of mutable governance fields |
| A26 | Other feature domains (194–206) — ACTIVE/LEDGER has one owner (**U-6**) | P2 | `Part 2 › Other feature domains`; no check asserts a single parser, so it stays description |
| A27 | Concurrency (208–216) — no-lock rule (**U-7**) | P2 | `Part 2 › Concurrency`, pointing at `DADAIA.md` §3 as the law's one home and recording only how the code embodies it |
| A28 | Runtime State (218–257) — `.dadaia/` table, legacy sweeps, repo hygiene (**B-4**) | P2 | `Part 2 › Runtime state`, hygiene now citing `dadaia doctor` ROOT-4 + `test_source_repo_hygiene.py` |
| A29 | Core file-I/O authorized set (259–266) | **P1** + P2 | **P-11**; the six-module set stays in Part 2 as the current membership |
| A30 | `atomic_write` rationale (268–279) | P2 | `Part 2 › Core file-I/O authorized set`; the hooks-latency clause repointed to P-12 |
| A31 | "One writer, proven by scan" (281–285) (**B-5**) | P2 | `Part 2`, now naming its check (`tests/unit/core/test_atomic_write_census.py`) — Tier-B, promotable at the sitting |
| A32 | Agent Surface (287–295) — roles, SDD ownership | P2 | `Part 2 › Agent surface`; the artifact list "`ACTIVE.md`, SPEC, PLAN, TASKS, CLOSURE" rewritten to "SPEC, PLAN, TASKS and the release's own `RELEASE.jsonl` fold" (both retired at T-050-21/21A) |
| A33 | Agent Surface (297–313) — 120–220-line persona target, per-persona line counts (**U-8**) | P2 (partial **DELETE**) | Target and the four-inside/five-above split kept in `Part 2 › Agent surface`; **the five per-persona line numbers and the 2,095 fleet total are deleted** — a point-in-time measurement with no check, which memory cannot keep true |
| A34 | Agent Surface (314–317) — "`rules-skills-map.json` … one contract test" (**STALE**) | **STALE→P1** | Retired by T-050-19. Rewritten onto `public/entities/behavior-map.json` and promoted as **P-17** (`test_behavior_map.py`) |
| A35 | Agent Surface (319–323) — "the law reaches each harness exactly once" (**U-9**) | P2 | `Part 2 › Agent surface` |
| A36 | Architecture Diagrams intro (327) — the FR1/T-050-06 retirement narrative | P2 (partial **DELETE**) | `Part 2 › Architecture diagrams` states the current fact (no `assets/` member; diagrams live in-doc). **The migration narrative is deleted** — history, not current truth (A17.5) |
| A37 | `SpecsDoctor` diagram (329–413) and panel diagram (484–563) | P2 | Mermaid blocks and their pinned `###` headings kept **verbatim**; regeneration laws repointed to P-13. **Deleted from both:** the "Release origin: v0.1.55 / FR2 / FR3" provenance lines (history) |
| A38 | Package-map diagram (415–482) | P2, **REGENERATED** | Deleted: the three retired package nodes (`ai_surface`, `lifecycle`, `workflows`), the `lifecycle -. governed_catalog seam .-> workflows` edge, the `lifecycle-no-workflows` sentence (that contract was removed in v0.3.0), the "ignore-cap 26 = 9/4/13" figure (stale; P-10's cap has one home, its test), the v0.1.55/FR3 provenance and the `note1` edge annotation (history). The live count **24** is now stated in the body |

## 2. `specs/memory/QUALITY.md` — 32 rows

| # | Old section (pre-rewrite line) | Disposition | New home / reason |
|---|---|---|---|
| Q1 | Frontmatter (1–31) | P2 | Rewritten for the two-tier shape; `last_updated: '2026-08-27'`, `release_origin: 0.5.0`. The old `summary`'s "LARGE census re-pinned at its measured value" clause is **deleted** with the claim itself (row Q7/Q19) |
| Q2 | Purpose (33–37) — hermetic; never a paid binary without opt-in (**U-10**) | P2 | `Part 2 › Purpose` (conftest backstops exist, but no contract asserts the rule itself) |
| Q3 | Layers table (41–47) | P2 | `Part 2 › Layers` |
| Q4 | Layers (49–63) — four-token intent taxonomy, undeclared = SCAFFOLD | **P1** + P2 | **P-24** carries the measured floor; the taxonomy prose stays in `Part 2 › Intent taxonomy`, pointing at `tests/AGENTS.md` |
| Q5 | Layers (65–75) — "enforced over `tests/e2e/**` and nowhere else" (**B-6**, **STALE**) | **STALE→P2** | V27 now measures suite-wide. Rewritten as two arms: the e2e collection gate (`check_test_intent_declared.py`) plus P-24's suite-wide floor |
| Q6 | Layers (77–84) — conftest autouse backstops, the 4 conditional skips | P2 | `Part 2 › Safety backstops` |
| Q7 | Layers (85–87) — "The broad LARGE census is **100**" | **DELETED** | Second numeric home for the LARGE cap (A18.6 / P-26). `PARAMETERS.md` is the only literal home; V29's competing-home count drops toward its target of 0 |
| Q8 | Layers (89–99) — derived-inventory rule (**U-11**) | P2 | `Part 2 › Derived inventories` |
| Q9 | Layers (101–107) — scan-vacuity two-line convention (**U-12**) | P2 | `Part 2 › Derived inventories` |
| Q10 | Root Cause, Always (109–116) — "a `resolved` **event** is refused unless…" (**U-13**, **STALE**) | **STALE→P2** | FR2 retired the event stream. Rewritten to the record model (cause, causing release, resolution set on the one `BUGS.jsonl` record) — discipline, so it stays Part 2 |
| Q11 | Root Cause, Always (117–120) — recurrence evidence, removal preferred | P2 | `Part 2 › Root cause, always` |
| Q12 | Redaction At Authoring (122–136) (**U-14**) | P2 | `Part 2 › Redaction at authoring` |
| Q13 | Redaction At Authoring (138–145) — gate render boundary (**B-7**) | P2 | Same section, now citing `tests/contract/test_push_gate_wiring.py` |
| Q14 | Satisfiable Diagnostics (147–153) (**U-15**) | P2 | `Part 2 › Satisfiable diagnostics` |
| Q15 | Satisfiable Diagnostics (155–174) — "append-only, **event-sourced** store", compensating event (**STALE**) | **STALE→P2** | Rewritten to the append-only *record* model (D11): the healing action is the append the store already accepts |
| Q16 | Browser Validation (176–183) (**U-16**) | P2 | `Part 2 › Browser validation` |
| Q17 | Flake Policy (185–193) — quarantine bug-gated; closed marker set | **P1** + P2 | **P-22** (quarantine) and **P-28** (marker set, in `TECHSTACK.md`); the mechanics stay in `Part 2 › Flake policy` |
| Q18 | Flake Policy (195–202) — cap 8, 30-day escalation, 3 reruns, flake < 0.5 % / 1 % (**U-17**) | P2, numbers **DELETED** | Four unmeasured numbers removed; `Part 2 › Flake policy` now references `dadaia-test-stewardship`'s `PARAMETERS.md` as their one home (P-26) |
| Q19 | Flake Policy (204–209) — pass-on-retry CI step (**B-8**) | P2 | Same section, now citing `tests/contract/test_ci_workflow_hygiene.py` |
| Q20 | Test Health (213–216) — three metrics, trigger-based audit (**U-18**) | P2 | `Part 2 › Test health` |
| Q21 | Test Health (218–233) — tier timeout table, two justified exceptions | **P1** + P2 | **P-21**; the table and the two exceptions stay in `Part 2 › Test health` |
| Q22 | Test Health (235–243) — "The **census is 100** … that measured number **is** the ceiling" | **DELETED** | The claim is false at birth and unmeasured (no check compares the census to a cap). Replaced by a reference to `PARAMETERS.md` plus the honest statement that the tree does not meet that cap today |
| Q23 | Test Health (245–248) — wall-clock baselines, `timeout-minutes` (**U-19**) | P2 | `Part 2 › Test health`; "release CLOSURE" repointed to "the release's closure record" |
| Q24 | Test Health (250–255) — `mutmut==3.7.0`, off the push path (**B-9**) | P2 | `Part 2 › Test health`, its push-path absence stated as pinned by a contract test |
| Q25 | Test Health (257–260) — exact-pin rule for third-party tooling (**U-20**) | P2 | `Part 2 › Test health`; the "first arrival under it" clause deleted as narrative |
| Q26 | CI (267–272) — job list | P2 | `Part 2 › CI` |
| Q27 | CI (274–282) — quarantine excluded from every selector, durations, 80 % floor (**B-10**) | **P1** (arm) + P2 | The exclusion arm belongs to **P-22**; the selector/duration/coverage detail stays in `Part 2 › CI` |
| Q28 | CI (284–303) — `pr-source-guard`, security-verdict gate (**B-11**) | P2 | `Part 2 › CI`, citing `test_ci_v2_gitflow_pr_gate.py` and `test_pr_verdict_check_gate.py`. **Deleted:** "a job introduced on a feature branch cannot run on the PR that introduces it, so its first PR is advisory" — release mechanics, not product truth |
| Q29 | CI (305–308) — preflight/CI parity (**B-12**) | P2 | `Part 2 › CI`, citing `test_ci_preflight_ci_gating_parity.py` — the strongest Tier-B promotion candidate at the sitting |
| Q30 | CI (310–314) — bug-surface delta in every verdict (**U-21**) | P2 | `Part 2 › CI`; roster corrected to include `security-reviewer` (FR24) |
| Q31 | CI (316–320) — consumer-side approval (**B-13**) | P2 | `Part 2 › CI`, citing `test_consumer_validation_recipe.py` |
| Q32 | Complexity And Size (324–342) + Anti-Slop (346–349) + Dependencies (351–353) | **P1** + P2 | **P-19** carries the ratchet; the literals `max-complexity = 63` / `max-nested-blocks = 6` are **deleted from memory** (`pyproject.toml` is their one home). The mandatory `## Size accounting` (**U-22**) is repointed from the retired `CLOSURE.md` to the `RELEASE.jsonl` `closure-size-accounting` note. Anti-Slop (**B-14**) now cites `test_source_repo_hygiene.py`; Dependencies unchanged |

## 3. `specs/memory/TECHSTACK.md` — 10 rows

| # | Old section (pre-rewrite line) | Disposition | New home / reason |
|---|---|---|---|
| T1 | Frontmatter (1–10) | P2 | Two-tier `tldr`/`summary`; `last_updated: '2026-08-27'`, `release_origin: 0.5.0` |
| T2 | Snapshot (14) — "the bootstrap injects only the top of this file" | P2 | Moved to the **last** Snapshot bullet so the digest window is spent on content; the same fact is restated once in `specs/memory/AGENTS.md` as an authoring constraint |
| T3 | Snapshot (16) — version lives in `pyproject.toml` only (**B-15**) | P2 | `Part 2 › Snapshot`, bullet 1 (unchanged) |
| T4 | Snapshot (17) — dependency roster | P2 | `Part 2 › Snapshot`, bullet 2 (unchanged) |
| T5 | Snapshot (18) — harness roster, `L1_ENTRY_HARNESSES` (**B-16**) | P2 | `Part 2 › Snapshot`, bullet 3 (unchanged) |
| T6 | Snapshot (19) — agent model policy | P2 | `Part 2 › Snapshot`, bullet 4 (unchanged) |
| T7 | Snapshot (20) — the closed eight-marker set | **P1** + P2 | **P-28**; the roster stays in bullet 5 with the `(P-28)` pointer |
| T8 | Snapshot (20) — coverage ≥ 80 %, `-p no:cacheprovider`, venv guard (**B-14**) | P2 | `Part 2 › Snapshot`, bullet 5 (unchanged) |
| T9 | Snapshot (21) — prohibitions; "features reach infrastructure via ports" | P2 | Bullet 6, now a **pointer** to [[architecture]] P-01/P-08 instead of a restatement |
| T10 | Canonical Commands (23–36), Packaging Notes (38–47), Dependencies (49–52) | P2 | `Part 2 › Canonical commands` / `Packaging notes` / `Dependencies`, content unchanged, headings demoted to `###` |

## 4. `specs/memory/product/**` — 1 row (A17.4)

| # | Scope | Disposition | New home / reason |
|---|---|---|---|
| P1 | All 26 product atoms + `index.md`, scanned for architecture principles and implementation tours (`import-linter`, `lint-imports`, ratchet/cap language, `tests/contract/*` citations, composition-root claims) | **No move, no rewrite** | Zero atoms carry a Part-1 principle: every hit is a *functional* description that already names the check measuring it (`agentic-entities.md`'s derivation contract, `public-asset-distribution.md`'s thin-wrapper test, `sdd-gate-v3.md`'s manifest contract, `agent-comms.md`'s adoption test, `academy.md`'s DI note). Each is now also cited from `ARCHITECTURE.md` Part 2 where the trio describes the same seam. A17.4 is satisfied by inspection — recorded here so the reviewer can re-run the same scan |

**Total rows: 81** (ARCHITECTURE 38 · QUALITY 32 · TECHSTACK 10 · product 1).
**Unmeasured prose rules (U-1…U-22): 22 of 22 accounted** — 18 moved to Part 2 intact
(U-1…U-7, U-9…U-16, U-18…U-21), 3 moved with their unmeasured numbers deleted (U-8, U-17,
U-20's narrative clause), 1 repointed to its surviving home (U-22 → the `RELEASE.jsonl`
closure note). **None appears under `## Part 1`.**

---

## 5. Residuals — paired edits this task cannot make (product code / tests)

`product-engineer` writes no production code or tests. Each row below is required for the
S4 commit to be green and is named for its owner.

| # | What | Owner | Why |
|---|---|---|---|
| R1 | Add the two Part headings — `Part 1 — Principles` and `Part 2 — Implementation` — to `memory_lint.py`'s heading allowlist (the SPEC's declared 85 → 87) | `software-engineer` | Until then LINT-1 reports the two headings as *unknown* (WARNING, not ERROR — `specs doctor`'s memory lane still passes, but the warning is noise the SPEC already budgeted for). Library home, not the workspace `.heading-allowlist` extension, because the trio shape is canon for every consumer |
| R2 | The FR17 file-shape contract test (the release's one permitted new test) must accept `ADR: NNNN (proposed)` as A17.2's ADR line until T-050-31 flips the ADRs to `accepted` | `software-engineer` | Writing `Accepted by: ADR NNNN` today would assert an acceptance the operator has not given — the exact fabrication this release outlaws. The line becomes `accepted` at T-050-31 |
| R3 | `_FEATURES_HEADING` in `tests/contract/test_architecture_diagrams_current.py` still reads `— package map (26 packages)`; the live count is **24** | `software-engineer`, in T-050-29 (its write set already includes `tests/contract/**`) | The heading is the drift-guard's lookup key, so the memory heading and the test constant must move in the **same** commit. This task regenerated the diagram body (24 nodes, three retired nodes removed) and states the live count there; changing the heading alone would turn the contract test red. Corrects the architect's `[MEDIUM]` finding, which assumed "zero code" |
| R4 | Propagate the two-tier law to the library copies of the memory rules — `dadaia_workspace/public/data/memory-AGENTS.md` and `dadaia_workspace/public/scaffold/memory/AGENTS.md` | `ai-engineer` | `specs/memory/AGENTS.md` is the instance copy; a consumer workspace scaffolds from the library ones, and both are pinned by `tests/unit/scripts/test_memory_agents_doc_schema_consistency.py` (keep the `agent_tier`-is-rejected sentence) |
| R5 | Re-pin `_V29_COMPETING_HOME_CEILING` from 1 to **0** | `software-engineer`, in T-050-29 | Row Q7/Q22 deleted `QUALITY.md`'s competing LARGE-cap number; the ceiling is ratchet-down-only and its own docstring names T-050-29 as the re-pin site |
| R6 | Intake candidate (no backlog entry written — PM's intake report decides): a **reverse** package check for the package-map diagram | PM → operator | P-13's guard is forward-only for packages, which is exactly why three retired nodes survived in the diagram until this rewrite. A new check is outside A18.3's letter for this release |
