# TASKS — Release v0.4.0 — Demolition of the plugin subsystem

> **Status:** Aprovado

**Release ID:** v0.4.0
**Owner:** product-engineer
**Source PLAN:** `specs/releases/v0.4.0/PLAN.md`
**Provenance:** retroactive record. Every task below was executed on `feature/v0.4.0`
(commits `29ab43b8`, `b0998b75`) under the operator's decree and is recorded here as
`[x]` DONE at the state it shipped in.

## Task status markers

- `[ ]` OPEN
- `[-]` IN PROGRESS
- `[x]` DONE

## Standing rules for this release

- **Machinery first, agents next, prose last.** Every task ends with an importable
  package and a collectable suite.
- **Deletion is driven by the explicit file list, never by grepping "plugin".** The grep is
  the residue authority; unrelated hits (Markdown renderer, `playwright` MCP, academy
  lessons) are classified, not deleted.
- **No `skip`/`xfail` placeholders** in place of deleted tests. Delete the file.
- **History is never rewritten**: `specs/bugs/**`, `specs/_archive/**` and the historical
  `CHANGELOG.md` entries are excluded from every sweep.

---

- [x] **T-40-01 — Sever the CLI and asset-chain machinery**

**Owner role:** software-engineer

**Write set:** `dadaia_workspace/cli/main.py` (drop the `plugin` import + `add_typer`);
`cli/commands/plugin.py` (delete); the pack installation/projection code in the public
asset chain including `_project_installed_plugins` and its precedence rule, the plugin
ledger/state, the pack manifest models and the plugin schemas; the plugin checks in
`public doctor` / `doctor`; the plugin test surface; install goldens.

**Description:** Cut every executable edge before touching the agents. Golden regen is
legitimate here and only for projections whose source asset this task deleted — each diff
explained in the commit message.

**Done criterion:** package imports; `dadaia --help` lists no `plugin` verb group;
`dadaia public stage/install/doctor` green with no plugin step; suite green.

---

- [x] **T-40-02 — Delete the three plugin agents and both packs**

**Owner role:** ai-engineer

**Preconditions:** T-40-01 `[x]`.

**Write set:** `dadaia_workspace/public/agents/{frontend-engineer,design-specialist,devops-engineer}.md`
(delete); the `frontend-design` and `devops` pack trees (delete); their projection dirs;
`public/entities/registry.json` (nine personas); the derivation contract test and the
`entities-derivation` doctor check.

**Description:** The registry pin and the entities it names change in the **same** commit —
a pin that outlives its entity leaves the suite red across a task boundary and is
indistinguishable from a demolition mistake.

**Done criterion:** nine agent bodies, nine registry personas; derivation contract and
`entities-derivation` green; every harness projection matches.

---

- [x] **T-40-03 — Rename the `plugin` model tier to `standard`**

**Owner role:** ai-engineer

**Preconditions:** T-40-02 `[x]`.

**Write set:** `dadaia_workspace/core/model_registry.py` (`Tier` literal,
`_CODEX_TIER_EFFORT`, `_CODEX_TIER_ORDER`, every `ModelEntry` label); the model-registry
and model-policy tests and goldens.

**Description:** Atomic rename. `plugin` named a distribution status; `standard` names the
cost class the tier always was. `_CODEX_TIER_EFFORT` and `_CODEX_TIER_ORDER` require every
`Tier` literal exactly once, so a partial rename breaks the Codex tier views.

**Done criterion:** `Tier = Literal["deep", "dispatch", "fast", "standard"]`; tier views
and `_codex_id_for_tier` invariants green; no model id, price or band moved.

---

- [x] **T-40-04 — Law, routing and prose sweep**

**Owner role:** ai-engineer

**Preconditions:** T-40-03 `[x]`.

**Write set:** `dadaia_workspace/public/data/DADAIA.md` (§2: delete the plugin-agent
paragraph and the `[PLUGIN REQUIRED]` block); the scoped `AGENTS.md` sources; the nine core
agent bodies (routing rows); the skills; `README.md` and `docs/` hits; projections via
`dadaia public stage` / `install --target all` (never hand-edited).

**Description:** Browser frontend (HTML/CSS/TS/React) and CI YAML
(`.github/workflows/*.yml`) return to `software-engineer`, the generic implementer, in
every routing table that named a plugin agent.

**Done criterion:** no product asset names `frontend-engineer`, `design-specialist` or
`devops-engineer`; `dadaia public doctor` reports `[ok] public-privacy` and zero drift; the
projected `DADAIA.md` copies are byte-identical to the source.

---

- [x] **T-40-05 — Constitution 4.0.0, quality gates, metrics**

**Owner role:** product-engineer (constitution) / qa-engineer (gates)

**Preconditions:** T-40-04 `[x]`; **explicit operator confirmation** for the constitution
edit.

**Write set:** `specs/constitution.md` (3.1.0 → 4.0.0); `CHANGELOG.md`.

**Description:** Drop the plugin-agent tier and the pack-extension law; restate the roster
as the nine core personas. MAJOR bump — a governance promise is withdrawn. Then run the
full acceptance list of SPEC §6 and measure the line delta and suite count for CLOSURE.

**Done criterion:** `constitution_version: 4.0.0`; suite, ruff, mypy `--strict`,
`lint-imports`, `dadaia doctor`, `specs doctor`, `public doctor`, `certify --json` all
green; metrics recorded in CLOSURE.

---

- [x] **T-40-06 — Memory atoms and CLOSURE**

**Owner role:** product-engineer

**Preconditions:** T-40-05 `[x]`; `ACTIVE.md` phase `CLOSURE` (memory writes are
phase-gated).

**Write set:** `specs/memory/product/agents/plugin-packs.md` (retire);
`specs/memory/product/agents/agent-orchestration.md`,
`specs/memory/product/distribution/public-asset-distribution.md`,
`specs/memory/{architecture.md,tech-stack.md}`;
`specs/memory/product/{index.md,catalog.json}` (regenerate);
`specs/releases/v0.4.0/CLOSURE.md`.

**Description:** Memory describes the product **after** the demolition — no changelog, no
"we used to have plugin packs". Record the disposition sweep in CLOSURE.

**Done criterion:** zero `plugin` matches under `specs/memory/`; `dadaia specs doctor`
green; CLOSURE.md complete with the T-40-05 metrics.
