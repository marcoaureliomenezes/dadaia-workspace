# PLAN — Release v0.4.0 — Demolition of the plugin subsystem

> **Status:** Aprovado

**Release ID:** v0.4.0
**Owner:** product-engineer
**Source SPEC:** `specs/releases/v0.4.0/SPEC.md`
**Provenance:** retroactive record of the executed plan on `feature/v0.4.0`.

## 1. Planning problem

The subsystem is small compared to v0.3.0's engine (≈6k lines, not ≈60k), but it is
**wider**: it touches the CLI, the public asset chain, the model registry, the entity
registry, the constitution, the workspace law and every core agent body. The failure mode
is therefore not a cascade — it is **residue**: a routing row, a projection dir, a tier
label or an agent name that survives the cut and keeps advertising a surface that no
longer exists.

The plan is consequently **code first, prose last, grep as the authority**: the removal is
driven by explicit file lists, and the sweep is closed by a residue grep rather than by a
checklist.

## 2. Execution lanes

### Lane A — Sever the machinery (agents still present, tree green)

1. **CLI edge** — drop the `plugin` import + `add_typer` in `cli/main.py`; delete
   `cli/commands/plugin.py` and its tests.
2. **Asset chain** — delete pack installation/projection from the public asset chain,
   including `_project_installed_plugins` and its "packs override core" precedence rule,
   the plugin ledger/state entries, the pack manifest models and the plugin schemas.
   Install goldens are regenerated **only** for projections whose source asset this lane
   deleted; every regenerated line is explained in the commit message.
3. **Doctor** — remove the plugin checks from `public doctor` / `doctor` and their tests.

After Lane A nothing but the agent bodies and prose knows the subsystem exists.

### Lane B — Delete the agents and packs

4. Delete `public/agents/{frontend-engineer,design-specialist,devops-engineer}.md`, both
   pack trees, and every projection dir they fed. Drop the three personas from
   `public/entities/registry.json` (nine remain) and update the derivation contract test
   and the `entities-derivation` doctor check to the nine-persona roster in the same
   commit — a registry pin that outlives its entity leaves the suite red across a task
   boundary.

### Lane C — Tier rename

5. `core/model_registry.py`: `plugin` → `standard` across the `Tier` literal, the
   tier→effort map, `_CODEX_TIER_ORDER` and every `ModelEntry`. Mechanical and total: a
   half-renamed tier breaks `_codex_id_for_tier` and the Codex tier views, which is why
   the rename is one commit and not a sweep.

### Lane D — Law, routing and prose

6. `public/data/DADAIA.md` §2: delete the plugin-agent paragraph and the
   `[PLUGIN REQUIRED]` refusal block; the owner table keeps the nine roles. Re-project
   (`public stage` → `install --target all` → `doctor`) — the projected law files are
   PROTECTED and are never hand-edited.
7. Routing sweep across the core agent bodies, the scoped `AGENTS.md` files and the
   skills: browser frontend and CI YAML are `software-engineer`'s surface.
8. `specs/constitution.md` → 4.0.0, with the operator's explicit confirmation.

### Lane E — Gates and metrics

9. Full suite, ruff, mypy `--strict`, `lint-imports --no-cache`; `dadaia doctor`,
   `specs doctor`, `public doctor`, `certify --json`; the residue grep; the line-delta and
   suite-count measurement for CLOSURE.

## 3. Risk points

**Residue, not cascade.** The word "plugin" survives legitimately in unrelated places —
the Markdown renderer's plugins, the `playwright` MCP plugin in `qa-engineer.md`, the
academy's harness lessons. Deletion is driven by the explicit file list; the grep is the
*residue* authority, and each surviving hit is classified, not auto-deleted.

**Projection precedence.** `_project_installed_plugins` ran *after* the core projection so
packs could override core files. Removing it must not disturb the surviving ordering
invariant (`install_dadaia_md` runs after the per-harness projections, so `copy_tree`
prunes orphans). Goldens are the check.

**Tier rename is a contract, not a label.** `_CODEX_TIER_EFFORT` and `_CODEX_TIER_ORDER`
require every `Tier` literal exactly once; the rename lands atomically with its tests.

**Constitution is a MAJOR bump.** Removing the plugin-agent tier and the pack-extension
law invalidates a governance promise, so 3.1.0 → **4.0.0**, and the edit waits on explicit
operator confirmation.

## 4. Validation strategy

- Per-lane: `pytest -p no:cacheprovider -q`; the package imports and the suite collects at
  the end of every task.
- After Lane B: nine agent bodies, nine registry personas, derivation contract green.
- After Lane D: `dadaia public doctor` reports `[ok] public-privacy` and zero drift; the
  projected `DADAIA.md` copies are byte-identical to the source.
- Lane E: the full SPEC §6 acceptance list, then the standard ship gates (security review
  handoff → push → PR → CI green).
