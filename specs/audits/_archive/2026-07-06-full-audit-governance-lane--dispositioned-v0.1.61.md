# Full Audit 2026-07-06 — GOVERNANCE + SPECS + MEMORY compliance lane

- **Auditor:** project-auditor (Tier-1, ADDITIVE — measured, did not fix)
- **Date:** 2026-07-06 (operator-ordered full audit)
- **Baseline:** `repos/dadaia-workspace` @ `main` `4a433063` (post-v0.1.60 closure, post-PyPI 0.2.1, post fable-5 retier PR#115); workspace root `/home/marco/workspace/dadaia`
- **State:** `specs/releases/ACTIVE.md` = `release: none / phase: none`; bug ledger 0 open (`dadaia bugs status`)

## Scope

Audited: (1) all 29 memory atoms (`specs/memory/` root ×3 + `product/` tree ×26) vs implementation truth; (2) `specs/constitution.md` + the 8-rule corpus (source vs projection vs code); (3) SDD structural health (4 doctors, ACTIVE/_archive integrity, backlog); (4) handoff hygiene (5 newest); (5) `catalog.json`/`index.md` coherence. Excluded (other lanes): code quality, security posture, test-suite depth, dead production code. Evidence: two delegated read-only sweeps (architecture atom; platform/sdd/harness/philosophy/agents atoms — mutually cross-checked) + direct verification for every HIGH finding.

Cross-check note: one sub-agent claim ("`plugin-scope.md` still says not-yet-distributed") was **rejected** — direct read + `diff` of `dadaia_workspace/public/rules/plugin-scope.md` vs `.claude/rules/plugin-scope.md` shows both carry the v0.1.60 install-gated wording, byte-identical.

---

## Area 1 — Memory atoms vs implementation truth

Verdict distribution over 29 atoms: **17 FRESH · 9 MINOR-DRIFT · 3 STALE** (`tech-stack.md`, `product-vision.md`, and `agent-orchestration.md` §model claims). `architecture.md` is very fresh (v0.1.60 plugin subsystem fully covered; decompositions verified byte-precisely). Every finding classified STALE-CLAIM / MISSING-COVERAGE / CONTRADICTION.

| ID | Sev | Class | Atom claim (evidence) | Reality (evidence) | Remediation direction |
|---|---|---|---|---|---|
| G-1 | HIGH | STALE-CLAIM | `tech-stack.md:72-74` "the **9 core agents** run on `claude-opus-4-8` … no model-cost split"; `:97-102` "**Reserved entry (used by no agent)** … zero core agents resolve to [claude-fable-5] … the operator rule is **NEVER** pin an agent to Fable-5"; `:104-114` per-agent table = 9× opus-4-8 | Retier `4a433063` (PR#115, operator-ordered 2026-07-06): 5 agents now `model: claude-fable-5` + per-agent `effort:` (`public/agents/{product-engineer,project-auditor}:high, ai-engineer:medium, {software-engineer,qa-engineer}:low`); 4 remain opus-4-8. Registry carries fable-5 tier=deep (`core/model_registry.py:108`); `tests/contract/test_agent_tier_taxonomy.py` updated in-commit, 4 passed | product-engineer rewrites §Model assignments (split table, drop "reserved/never-pin" text, document `effort:` frontmatter) in the remediation release CLOSURE |
| G-2 | HIGH | CONTRADICTION (intra-atom + cross-atom) | `tech-stack.md:124` Plugin inventory: `frontend-design` "**Not yet distributed** … No install command exists yet — tracked by backlog `plugin-packs-and-install-command`" | Contradicts the same atom's `:76` ("When a pack installs … v0.1.60") and `plugin-packs.md` (whole atom, fresh) + `plugin-scope` rule; `dadaia plugin install/list/doctor` exists (`cli/commands/plugin.py:99-153`), packs on disk (`public/plugins/{frontend-design,devops}/pack.json`) | Rewrite the Plugin-inventory rows (installed-gated status; add `devops` pack row) |
| G-3 | HIGH | STALE-CLAIM | `product-vision.md:109-111` "no install command exists yet"; `:178` "Plugin packs (frontend-design, devops) are not yet distributed" | Same evidence as G-2 — shipped in v0.1.60 | Update Known-limits section |
| G-4 | HIGH | STALE-CLAIM | `product-vision.md:171-172` "Only 4 workflow verbs are operator-invocable today; audit/research/bug_report have real bodies with no verb" | All 12 verbs wired: `cli/commands/lifecycle.py:1172` (audit), `:1229` (research), `:1283` (bug_report), `:1441` (implement-review) … (shipped v0.1.56/R8) — contradicts `dadaia-workflows.md` tldr ("all operator-invocable since v0.1.56"), which is correct | Update Known-limits; `product-vision.md` is the single STALE-heavy atom |
| G-5 | MEDIUM | STALE-CLAIM | `agent-orchestration.md:96` "the 9 core resolve to `dispatch`/opus"; `:224` "`ai-engineer` model assignment: `claude-opus-4-8`" | Retier evidence as G-1 (`public/agents/ai-engineer.md`: fable-5/medium) | Same memory pass as G-1 |
| G-6 | MEDIUM | CONTRADICTION (intra-atom) | `architecture.md:36` "cli/ — typer app + **22 subcommands**" (roster omits `plugin`) | `cli/main.py:61` registers `plugin` → 23; the atom itself documents `cli/commands/plugin.py` at `architecture.md:73` | Fix count + roster |
| G-7 | MEDIUM | CONTRADICTION | `dadaia-workflows.md` availability table marks `implementation` and `closure` "available"; text "already AVAILABLE for all 7" | `governed_catalog.py:677,681` = `AVAILABILITY_PARTIAL` for both (ADR-E vocabulary distinguishes available vs partial); the 12-verb invocability claim itself is true | Correct availability labels for 2/7 |
| G-8 | MEDIUM | STALE-CLAIM ×3 | `agent-monitoring.md:29` "`store/schema.open_connection` … not wired into the real connection paths"; `:74` route `GET /api/sessions/<runtime>/<id>`; `:36-37,67` implies a Sessions list | Wired since v0.1.52 (`features/telemetry/service.py:304,316`, `aggregator/queries.py:67`); detail route deleted (`features/panel/handler.py:241` — only `^/api/sessions$`); Sessions tab is dashboard-only (`views/sessions.py:1-17`) — `panel.md` already states all of this correctly (atom-vs-atom disagreement) | Refresh agent-monitoring to v0.1.52+ panel truth |
| G-9 | MEDIUM | CONTRADICTION | `server-registry.md:20` CLI surface "`dadaia server {list,register,unregister,clean,scan}`" | No `unregister` verb; actual: `list,next,register,release,show,clean,scan` (`cli/commands/server.py:35,94,120,147,174,215,229`) | Fix verb roster (phantom `unregister`; omitted `next/show/release`) |
| G-10 | MEDIUM | MISSING-COVERAGE | `multi-platform-parity.md:70-82` public-surface table covers plugin agents only as "stubs … no behavior until installed" (no install story); heading "counts (v0.2.0)" | Plugin subsystem shipped (`plugin.py:99-153`, ledger `infrastructure/json_plugin_store.py`); `pyproject.toml:3` = 0.2.1. All surface counts re-verified correct (12 agents / 8 personas / 8 rules / 18 skills / 2 workflow docs / 7 workflows) | Add install-gated wording; bump heading |
| G-11 | MEDIUM | STALE-CLAIM (cluster) | `cross-platform-portability.md:121-122` "legacy standalone `main()`s still exist; removal tracked in backlog"; also `:84` panel.token residue, `:92` chmod guard follow-up, `:155-156` 3-OS job names, `:165` legacy `.sh` scripts | All completed: no `def main` in `hooks/sdd_gate.py`/`root_whitelist.py`; zero `panel.token` hits in `features/telemetry/`; guard landed (`features/telemetry/service.py:109,159-160`); cross legs are `unit-fast-cross`/`contract-coverage-cross` (`ci.yml:174,197`) | One refresh pass — atom describes completed follow-ups as pending |
| G-12 | MEDIUM | MISSING-COVERAGE | No memory atom owns **PyPI distribution**: package version `0.2.1` (`pyproject.toml:3`), the `release.yml` auto tag+publish workflow (`.github/workflows/release.yml:1-30`), or the version-scheme split (SDD releases `v0.1.x` vs package `0.2.x`); `quality-assurance.md:264-269` enumerates only `ci.yml` + `secret-scan.yml` | PyPI publication is live product behavior since PR#112/#113 (2026-07-04/05); only incidental mentions in `cross-platform-portability.md:30,152` (classifier) | New/extended distribution atom + quality-assurance workflow inventory row |
| G-13 | LOW | CONTRADICTION (intra-atom) | `panel.md:185` "Mermaid remains loaded only inside the memory-view iframes" | Contradicts `panel.md:171` ("mermaid fences entity-escaped … no client renderer exists") and `views/_md_render.py:7,114` ("no Mermaid client ships") | Delete the line-185 residue |
| G-14 | LOW | MISSING-COVERAGE | `public-asset-distribution.md:21-25` lists 13 live asset types | `public/` has 14 subdirs — `plugins/` omitted from the list (though §Plugin-pack projection `:119-128` covers the mechanics) | Add `plugins` to the type list |
| G-15 | LOW | STALE-CLAIM (cluster) | `sdd-gate-v3.md:32` "legacy `main()`s kept for one release"; `:154` "`features/lease.py`"; `specs-doctor.md:32,88` "010/011 are no-op stubs"; `workspace-init.md:9-11,30,63` "ctx-inject.sh … still present"; `brand-identity.md:19` "`views/_assets.py` retains legacy constants" | main()s removed (`hooks/pre_gate.py:13-15`); real path `features/spec_context/lease.py`; 010/011 exist only as a comment (`features/specs/doctor.py:151`); no `ctx-inject.sh` shipped (`features/workspace/service.py:110-111`); `views/_assets.py` does not exist | Batch of one-line memory corrections |
| G-16 | LOW | CONTRADICTION (partial) | `harness-pi.md:40-41` "auth … NOT an Anthropic key" | PI worker env allowlist deliberately passes `ANTHROPIC_API_KEY` (`infrastructure/pi_runtime.py:42-43`; `headless_adapter_base.py:282`) | Qualify the auth claim |
| G-17 | INFO | misc | `architecture.md:63` "each ≤ 429 lines" (`api_agents.py` = 430, still under the 450 ratchet); `workspace_guardrail.py` home module unnamed at `:73`; `workspace-doctor.md:37-38` INV-5 prose says WARN, table says AUTO-FIX (code: `fixable=True`, `features/spec_context/doctor.py:581-583`); `lifecycle-foundation.md:437-439` `is_review_phase` helper phrasing (pipeline branches on the field directly, `pipeline.py:527,539`); `workspace-portability.md:19` omits `--list/--skip-mnt/--dry-run` flags | — | Polish items, fold into the same memory pass |

**Confirmed fresh (spot-verified, no drift):** `plugin-packs.md`, `sdd-bug-backlog-governance.md`, `specs-doctor.md` (invariant roster exact; coordinator exactly 224 lines), `dadaia-workflows.md` (7 workflows/12 verbs/`--model` gone), `lifecycle-foundation.md`, all 3 harness atoms (retier-safe: none asserts all-opus), `harness-codex` tier views hold post-retier (deep→high explains `qa-engineer.toml` effort=high vs Claude effort=low — registry-derived, not drift), `agent-comms.md` (handoff-v1.1 validated live), `panel.md` (port 4999 `cli/commands/panel.py:119`, 6 tabs `views/index.py:109-114`, exactly 7 JS files, kanban zero hits), `context-management.md`, `repos-catalog.md` (3000-3999 `features/server_registry/service.py:12-13`; `repos.xlsx` `features/repos/service.py:13`), `quality-assurance.md` (10+5 CI jobs match `ci.yml` exactly), `spec-context-project.md`, `academy.md`, `workspace-doctor.md` (codes incl. EFF-1 all present).

---

## Area 2 — Constitution + rules corpus vs reality

| ID | Sev | Class | Claim | Reality | Remediation direction |
|---|---|---|---|---|---|
| G-18 | HIGH | GOVERNANCE / process drift | Constitution §1 (`constitution.md:50-55`): "Production changes require an approved release gate … and a reserved task" | PRs **#112** (`13c85eea`, version 0.1.7→0.2.0 + PyPI deploy), **#113** (`b1cb28dc`, README/0.2.1), **#115** (`4a433063`, agent retier — touched `public/agents/*` + contract test + backlog, NOT memory) all landed with `ACTIVE.md = release: none` and no SPEC/PLAN/TASKS. Mitigants: operator-ordered, sha-matched security APPROVE handoffs exist and validate (5/5 exit 0), CI green, contract test updated in-commit. This ungated span is the root cause of G-1/G-5 (no CLOSURE memory pass ran) and G-12 | project-manager: fold #112/#113/#115 into this audit's mandated remediation release (audit-disposition law) with a product-engineer memory pass; operator to ratify the post-hoc exception |
| G-19 | MEDIUM | STALE-CLAIM | Constitution §13 (`constitution.md:188-190`): "`specs/memory/product/**` (one atom per production feature + `index.md` **with vision/users/catalog/capability-map/limits**)" | `product/index.md` is a generated features-by-area table only (`index.md:1-6`, "Generated automatically … do not edit"); vision/users/capability-map/limits live in `philosophy/product-vision.md` | PATCH-level constitution wording amendment (§15 process) |
| G-20 | INFO | convention | Constitution §7 (`constitution.md:105,112-113`): audit output path `specs/audits/<ts>-<sid8>/` | `specs/audits/_archive/` shows mixed naming (4 legacy `2026-06-10T…` entries, one `…-00000000`); this lane's report is an operator-specified flat file | Tolerated; normalize naming on archive |

**Rules corpus:** all 8 files byte-identical source↔projection (`diff` = OK ×8). `plugin-scope.md` carries the v0.1.60 install-gated rewrite (source `public/rules/plugin-scope.md:11-49`) — verified against `cli/commands/plugin.py` and the `installed_plugins.json` ledger contract. Sampled mechanical claims in `workspace-protocol` (8 hook modules, 2 git-chokepoint `.sh`, matcher tables), `release-governance` (pre-push verdict gate — 5 sha-keyed security handoffs on disk), `harness-skill-scope` (the 3 restricted skills exist among the 18), `dadaia-workspace-dev-guardrail` (manifest + stage/install/doctor) — all hold. No mechanically-false rule claim found.

---

## Area 3 — SDD structural health

Doctor exits (all commands run with captured exit codes, no pipes): `specs doctor` **0** (14 warnings) · `backlog doctor` **0** (clean) · `public doctor` **0** (incl. `[ok] public-privacy`, `[ok] model-resolution`) · `dadaia doctor` **0** (4 issues listed; bare-doctor exit-0 is the documented contract).

### specs doctor — all 14 warnings enumerated + classified

| # | Warning | Classification |
|---|---|---|
| 1 | TREE-5: `specs/AGENTS.md` drifted from canonical template (sha `5cd7e718…` vs `c4f20914…`) | **Actionable (LOW)** — known tri-copy hand-sync debt; review diff + merge |
| 2 | LINT-1: 7 atoms warned — token_estimate drift ×5 (`architecture` 29%, `quality-assurance` 48%, `plugin-packs` 22%, `public-asset-distribution` 57%, `lifecycle-foundation` 26%) + unknown headings ×3 (`tech-stack` "Model assignments (9 core + 3 plugin)", `workspace-init` "Harness profiles", `lifecycle-foundation` "Prompt-assembly canon (v0.1.57)") | **Actionable (LOW)** — PE fixes frontmatter estimates + allowlists headings in the same memory pass as Area 1 |
| 3-4 | SPEC-DOC-027 ×2: legacy release dir names (`multiharness-engine-v0116`, `pi-fourth-harness-v1`) | **Accepted debt** — explicitly "preserved until renamed" |
| 5 | SPEC-DOC-029: stale lease `sample-games` (dead session `a8f129a6…`) | **Actionable (transient)** — `dadaia doctor --fix`; same item as LOCK-GC below |
| 6-14 | SPEC-DOC-031 ×9: backlog entries with status `candidate` referenced by archived releases (`fast-tier-persona-validation`, `golden-platform-normalization-layer`, `layer1-selfpull-handoff-audit-line`, `plugin-pack-content-libraries`, `plugin-uninstall`, `response-guard-chip-presence-hardening`, `selfrepo-agents-md-doubled-header`, `tier-taxonomy-rename`, `workflow-spawn-entry-harness-autodefault`) | **Accepted debt / known false-positive class (ADR-6)** — all 9 are the deliberately-live "backlog returns" enumerated in `ACTIVE.md` |

### Workspace doctor (4 issues, exit 0)

| ID | Sev | Issue | Remediation direction |
|---|---|---|---|
| G-21 | MEDIUM | ROOT-1/ROOT-2: workspace root contains `.mypy_cache/` (forbidden cache dir, fixable) and `bug-space-war` (non-whitelisted entry, manual) | `dadaia doctor --fix` for the cache; operator triages `bug-space-war` (operator-created → add to `root_exceptions.txt`; else relocate) |
| G-22 | LOW | LOCK-GC: stale `sample-games` lease (= SPEC-DOC-029) | `dadaia doctor --fix` |
| — | INFO | LOCK-5: BLOCKED_ATTEMPT event on `lock-events.jsonl:98` | Historical telemetry; no action |

### Releases / archive integrity

- `ACTIVE.md = none` **coherent**: v0.1.60 archived with full SPEC/PLAN/TASKS/CLOSURE (`_archive/releases/v0.1.60/`); R1–R12 complete; 0 open bugs (matches ACTIVE.md claim); no open audits (`specs/audits/` contains only `_archive/` ×16 — disposition law satisfied).
- `consumed_backlog.json` present under `specs/_archive/<version>/` for v0.1.47–v0.1.60 ✓.
- **G-23 (MEDIUM):** `_archive/releases/v0.1.41/` contains ONLY `GRILL.md` + `OQ-DECISIONS.md` — no SPEC/PLAN/TASKS/CLOSURE (abandoned v0.1.40-42 residue). Violates the every-archived-release-has-CLOSURE expectation; specs doctor does not flag it (**INFO:** possible doctor coverage gap for partial archived release dirs). Direction: product-engineer dispositions the residue (relocate to a `wip/`-style annex or complete the record); consider a doctor invariant.

---

## Area 4 — Handoff/report hygiene

`dadaia reports validate` on the 5 newest handoffs in `.dadaia/handoff/dadaia-workspace/` — **5/5 exit 0** (`2026-07-06T011500Z…fable5-retier-rekey-push-gate`, `2026-07-06T010000Z…fable5-retier-push-gate`, `2026-07-05T030000Z…pypi-021-push-gate`, `2026-07-05T020000Z…pypi-020-push-gate`, `2026-07-05T013000Z…v0160-closure-push-gate`). All are sha-keyed security push-gate verdicts, consistent with the pre-push chokepoint contract. No findings.

---

## Area 5 — Catalog coherence

- `specs/memory/product/catalog.json`: `generated_at 2026-07-05T01:15:34Z` (newer than every atom's `last_updated 2026-07-04`), 26 features, every `path` resolves to an existing atom; 26 atoms on disk (product tree minus `index.md`) ↔ 26 entries — **no orphan in either direction**.
- `index.md` is generator-owned (`dadaia memory catalog generate`) and consistent with catalog tldrs; CAT-1 doctor check green. No findings (the §13 wording mismatch is filed as G-19 against the constitution, not the catalog).

---

## Recommended actions (severity-ordered; auditor never fixes)

1. **G-18 (HIGH):** `project-manager` opens the audit-mandated remediation release folding PRs #112/#113/#115 governance regularization + all findings' dispositions (audit-disposition law: this audit must be fully dispositioned before archiving).
2. **G-1/G-5 (HIGH/MEDIUM):** `product-engineer` (CLOSURE/DEFINITION phase of that release) rewrites `tech-stack.md` §Model assignments + `agent-orchestration.md` model lines to the 5×fable-5(+effort)/4×opus split.
3. **G-2/G-3/G-4 (HIGH):** `product-engineer` purges all "not yet distributed / no install command / only 4 verbs" residue (`tech-stack.md:124`, `product-vision.md:109-111,171-178`).
4. **G-12 (MEDIUM):** `product-engineer` adds PyPI-distribution coverage (0.2.x package versioning, `release.yml`) to memory; `quality-assurance.md` workflow inventory row.
5. **G-6..G-11, G-13..G-17, G-19 (MEDIUM/LOW):** batch memory-correction pass + constitution §13 PATCH amendment; LINT-1 token estimates + heading allowlist in the same pass.
6. **G-21..G-23:** `dadaia doctor --fix` (cache + stale lease); operator triage of `bug-space-war`; disposition of the `v0.1.41` archive residue (+ optional new doctor invariant).

## Lane scorecard

| Area | Score (0-10) | Basis |
|---|---|---|
| 1. Memory atoms vs implementation | **6** | 4 HIGH stale/contradiction findings concentrated in 3 atoms (retier + plugin-pack shipping unabsorbed); 17/29 atoms fully fresh; architecture atom near-exact |
| 2. Constitution + rules corpus | **8** | Rules corpus byte-synced + mechanically true; one stale §13 claim; process law intact on paper |
| 3. SDD structural health | **8** | 0 doctor errors; warnings mostly accepted-debt/false-positive class; v0.1.41 archive residue + root hygiene items |
| 4. Release governance (post-closure span) | **5** | 3 production PRs landed release-less against §1 (operator-ordered, security-gated, but memory pass skipped — the drift engine behind Area 1) |
| 5. Handoff/report hygiene | **10** | 5/5 validate; sha-keyed push-gate chain intact |
| 6. Catalog coherence | **10** | 26/26 bidirectional, regenerated post-closure |
| **Overall (lane)** | **7** | Weighted by drift mass: healthy skeleton, stale skin — every HIGH is a memory/spec statement, none is a code defect |

Finding counts: **HIGH 5** (G-1, G-2, G-3, G-4, G-18) · **MEDIUM 10** (G-5..G-12, G-21, G-23) · **LOW 6** (G-13..G-16, G-15 cluster, G-22, TREE-5/LINT-1) · **INFO 6** (G-17 cluster, G-20, LOCK-5, doctor-gap note, SPEC-DOC-027/031 classes).

Per the audit-disposition law (constitution §7 / `release-governance`), this audit generates exactly one remediation release; every G-id above requires an explicit disposition (fixed / superseded / deferred-with-reason) before this file archives.

## Evidence sources

- Delegated sweep A (architecture.md vs tree) and sweep B (22 platform/sdd/harness/philosophy/agents atoms) — read-only, findings returned inline and cross-verified; sweep C (sdd+harness deep pass) corroborated sweep B.
- Direct: `public/agents/*.md` frontmatter, `core/model_registry.py`, `cli/commands/{plugin,lifecycle,server,panel}.py`, `governed_catalog.py:672-684`, `views/index.py`, `_md_render.py`, `ci.yml`/`release.yml`, `pyproject.toml`, git `13c85eea`/`b1cb28dc`/`4a433063`.
- Doctor logs captured with real exit codes (specs/backlog/public/workspace); `dadaia reports validate` ×5; `pytest tests/contract/test_agent_tier_taxonomy.py` (4 passed).
