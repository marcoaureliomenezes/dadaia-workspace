# SPEC — Release v0.4.0 — Demolition of the plugin subsystem

> **Status:** Aprovado

**Release ID:** v0.4.0
**Owner:** product-engineer
**Source:** operator decree, 2026-08-10 — explicit, confirmed order to demolish the plugin
subsystem in full (agents, packs, machinery).
**Provenance:** **retroactive record.** Implementation was carried out under the operator's
direct order and completed on `feature/v0.4.0` before this SPEC was written. The document
records the decreed scope faithfully as executed; it did not gate the work. This mirrors
how `specs/releases/v0.3.0/` records the engine demolition.

## 1. Problem

The plugin subsystem promised an extension surface the workspace never used. Two packs
(`frontend-design`, `devops`) and three agents (`frontend-engineer`, `design-specialist`,
`devops-engineer`) shipped as **stubs**: in every real workspace the packs were absent, so
the agents existed only to emit `[PLUGIN REQUIRED]` and bounce the task back to a core
agent or the operator. Around those stubs stood real machinery — a `dadaia plugin` verb
group, pack manifests and installation, plugin projection and precedence in the public
asset chain, a `plugin` model tier, doctor checks, a memory atom, and plugin routing rows
in every core agent body and in the workspace law.

The cost was paid by every agent and every reader: a routing table that sent frontend and
CI-YAML work to an agent that does not exist here, a second projection precedence rule in
`public install`, and a tier name that described distribution rather than cost. The
benefit was zero — no pack was ever installed. The same law v0.3.0 proved empirically
applies: **no mechanism for a demand that does not need one.** The operator ruled:
demolish.

## 2. Objective

Remove the plugin subsystem from the repository — agents, packs, CLI, projection, tier,
doctor checks, schemas, memory and prose — so that no product surface refers to plugin
agents or plugin packs. Return frontend and CI-YAML implementation to `software-engineer`,
the generic implementer, which is where the work actually lands today.

## 3. Scope

### FR1 — Delete the three plugin agents

`dadaia_workspace/public/agents/{frontend-engineer,design-specialist,devops-engineer}.md`
and their projections. The core agent roster becomes exactly nine:
`project-manager`, `product-engineer`, `software-architect`, `software-engineer`,
`qa-engineer`, `code-reviewer`, `security-reviewer`, `ai-engineer`, `project-auditor`.

**Acceptance:** `dadaia_workspace/public/agents/` holds nine bodies; every harness
projection matches; `public/entities/registry.json` lists **nine** personas.

### FR2 — Delete both packs and all plugin machinery

The `frontend-design` and `devops` pack trees, the `dadaia plugin` CLI verb group
(`cli/commands/plugin.py`) and its wiring in `cli/main.py`, pack manifest models and
installation/projection code in the public asset chain (`_project_installed_plugins` and
its precedence rule), the plugin ledger/state, the plugin doctor checks, the plugin
schemas, and the whole plugin test surface.

**Acceptance:** `dadaia --help` lists no `plugin` verb group; `grep -ri plugin` over
`dadaia_workspace/` matches nothing about the subsystem (Markdown-renderer and MCP-plugin
mentions are unrelated survivors); `dadaia public stage/install/doctor` green with no
plugin step.

### FR3 — Rename the `plugin` model tier to `standard`

`core/model_registry.py`: the `Tier` literal, the tier→effort map, the ordered tier
presentation and every `ModelEntry` label. `plugin` named a distribution status, not a
cost class; `standard` names what the tier always was — the mid-cost general
implementation tier.

**Acceptance:** `Tier = Literal["deep", "dispatch", "fast", "standard"]`; the Codex tier
views and `_codex_id_for_tier` invariants hold; model-policy goldens explained.

### FR4 — Return frontend and CI-YAML routing to `software-engineer`

Every routing table that named a plugin agent is repointed: browser frontend
(HTML/CSS/TS/React) and CI YAML (`.github/workflows/*.yml`) are the generic implementer's
surface. Severed in the same sweep: the `[PLUGIN REQUIRED]` refusal block and the plugin
agent rows in `DADAIA.md` §2, in the scoped `AGENTS.md` files, in the core agent bodies
and in the skills.

**Acceptance:** no product asset names `frontend-engineer`, `design-specialist` or
`devops-engineer`; `software-engineer`'s write table grants browser frontend and CI YAML.

### FR5 — Constitution 4.0.0

`specs/constitution.md` drops the plugin-agent tier and the pack-extension law, and
restates the agent roster as the nine core personas. This is a breaking governance change,
so the version is bumped **3.1.0 → 4.0.0**. Written with the operator's explicit
confirmation, per the constitution-edit rule.

**Acceptance:** frontmatter `constitution_version: 4.0.0`; no plugin prose remains;
`dadaia specs doctor` green.

## 4. Out of scope (non-goals)

- The **nine core agents' own mandates** — only plugin routing rows change.
- **Model governance beyond the rename** — no model id, price or band moves.
- **The MCP surface** and the Markdown renderer's "plugins" — unrelated to this subsystem.
- **Git history rewrite** — `specs/bugs/**`, `specs/_archive/**` and `CHANGELOG.md`
  history stay verbatim; CHANGELOG is the one place the names legitimately survive.

## 5. Memory atoms affected at closure

- **Delete** `product/agents/plugin-packs.md` (the subsystem's atom) and drop it from
  `product/index.md` + `product/catalog.json`.
- **Rewrite** `product/agents/agent-orchestration.md` (nine roles, no plugin tier),
  `product/distribution/public-asset-distribution.md` (no plugin projection or
  precedence), `architecture.md` and `tech-stack.md` (no plugin machinery, tier renamed).
- `specs/constitution.md` → 4.0.0 (FR5) — **operator-confirmed**.

## 6. Acceptance criteria (release-level)

1. Full suite green: `pytest -p no:cacheprovider -q`.
2. `ruff format --check`, `ruff check`, `mypy --strict`, `lint-imports --no-cache` green.
3. `dadaia doctor`, `dadaia specs doctor`, `dadaia public doctor`, `dadaia certify --json`
   green on a clean workspace.
4. Nine agent bodies, nine registry personas, zero plugin references in any product
   surface.
5. Quantified removal recorded in CLOSURE (net line delta, suite count).
