# Closure: Release — v0.4.0

> **Status:** Aprovado
> **Release ID:** v0.4.0
> **Owner:** product-engineer
> **Closed:** 2026-08-10

## Summary

v0.4.0 removes the plugin subsystem from dadaia-workspace. The operator decreed the
demolition on 2026-08-10 as an explicit, confirmed order: the three plugin agents
(`frontend-engineer`, `design-specialist`, `devops-engineer`), both packs
(`frontend-design`, `devops`), and all the machinery around them — the `dadaia plugin` verb
group, pack manifests and installation, plugin projection and its precedence rule, the
plugin ledger/state, the plugin doctor checks and schemas, and the plugin test surface.

The subsystem never carried a real demand. No pack was ever installed in a real workspace,
so the three agents existed only to emit `[PLUGIN REQUIRED]` and hand the task back — while
every routing table in the product still sent browser frontend and CI-YAML work to them.
That routing is now returned to `software-engineer`, the generic implementer, which is
where the work actually landed all along. The `plugin` model tier was renamed `standard`:
it named a distribution status, never a cost class.

`specs/constitution.md` was bumped **3.1.0 → 4.0.0** with the operator's explicit
confirmation — withdrawing the plugin-agent tier and the pack-extension law is a breaking
governance change. The agent roster is now nine core personas, in the agent bodies, in
`public/entities/registry.json`, and in the constitution alike.

This CLOSURE, like the SPEC/PLAN/TASKS beside it, is a **retroactive record**: the
implementation was completed under the operator's direct order on `feature/v0.4.0` before
the release documents were authored.

## Metrics

| Metric | Before | After | Δ |
|---|---|---|---|
| Net line delta on `feature/v0.4.0` (`29ab43b8`, `b0998b75`) | — | — | **net −5,901** |
| Tests passed | 2,074 | 1,998 | −76 |
| Core agent bodies in `public/agents/` | 12 | 9 | −3 |
| Personas in `public/entities/registry.json` | 12 | 9 | −3 |
| Plugin packs shipped | 2 | 0 | −2 |
| CLI verb groups | `plugin` present | `plugin` absent | −1 |
| Model tier name | `plugin` | `standard` | renamed |
| Constitution version | 3.1.0 | 4.0.0 | MAJOR bump |

## Tasks completed

All six tasks are `[x]` on branch `feature/v0.4.0`. Per-task SHAs are the branch history;
the work landed in two commits.

| Task ID | Description | Final commit |
|---|---|---|
| T-40-01 | Sever the CLI and asset-chain machinery | `29ab43b8` |
| T-40-02 | Delete the three plugin agents and both packs | `29ab43b8` |
| T-40-03 | Rename the `plugin` model tier to `standard` | `29ab43b8` |
| T-40-04 | Law, routing and prose sweep | `29ab43b8` |
| T-40-05 | Constitution 4.0.0, quality gates, metrics | `b0998b75` |
| T-40-06 | Memory atoms and CLOSURE | this commit |

## Validations

| Description | Command | Evidence |
|---|---|---|
| Full Python suite green after the cut | `.dadaia/.venv/bin/python -m pytest -p no:cacheprovider -q` | `1998 passed` (T-40-05) |
| Strict type check | `mypy --strict` | clean (T-40-05) |
| Format + lint | `ruff format --check` / `ruff check` | clean (T-40-05) |
| Import contracts | `lint-imports --config setup.cfg --no-cache` | green, zero unmatched ignores (T-40-05) |
| Public projection round-trip with no plugin step | `dadaia public stage && dadaia public install --target all && dadaia public doctor` | green, `[ok] public-privacy` (T-40-01/T-40-04) |
| Nine-persona roster | `public/agents/*.md` = 9 bodies; `public/entities/registry.json` = 9 personas | entities-derivation check + derivation contract test green (T-40-02) |
| Tier rename is total | `core/model_registry.py` → `Tier = Literal["deep", "dispatch", "fast", "standard"]` | `_CODEX_TIER_EFFORT` / `_CODEX_TIER_ORDER` cover every literal exactly once (T-40-03) |
| Constitution version | `specs/constitution.md` frontmatter | `constitution_version: 4.0.0` (T-40-05) |
| Memory residue | `grep -ri plugin specs/memory/` | zero matches (T-40-06) |

## Drifts

### retroactive-documents

**Description:** The release was executed under a direct operator decree and completed
before SPEC/PLAN/TASKS existed. The normal gate order (SPEC `Aprovado` → PLAN → TASKS →
implementation) did not run.

**Resolution:** The documents were authored afterwards as a faithful record of the decreed
and executed scope, each marked `Aprovado`, with the provenance stated in every header.
This is the same posture `specs/releases/v0.3.0/` takes for the engine demolition. No
document claims to have gated the work.

**Memory updates:** none.

### software-engineer-prose-residue

**Description:** `dadaia_workspace/public/agents/software-engineer.md` now grants
`Browser frontend and CI YAML | Write (generic implementer surface)` in its write table
(FR4, as intended), but two older statements survive the sweep and contradict it: the
frontmatter `description:` still ends "No frontend/AI-entity/specs/CI.", and the body
intro still says the agent "never touch[es] browser frontend".

**Resolution:** Cosmetic, not behavioural — the write table is the authoritative surface
and the gate reads paths, not prose. Routed to the backlog rather than widened into this
release's write set at CLOSURE time (see *Backlog returns*).

**Memory updates:** none — the memory atoms were written from the write table, which is
correct.

## Memory updates

Applied during this CLOSURE phase; `grep -ri plugin specs/memory/` returns zero matches.

- `specs/memory/product/agents/plugin-packs.md` — **retired**; the subsystem it described
  no longer exists.
- `specs/memory/product/agents/agent-orchestration.md` — nine core Layer-1 roles, two
  dispatchers; no plugin tier and no `[PLUGIN REQUIRED]` refusal path.
- `specs/memory/product/distribution/public-asset-distribution.md` — the plugin projection
  step and the pack-over-core precedence rule removed from the install chain description.
- `specs/memory/architecture.md` — plugin machinery removed from the module map and the
  runtime-state table.
- `specs/memory/tech-stack.md` — model tier restated as `standard`; no pack distribution.
- `specs/memory/product/index.md` + `specs/memory/product/catalog.json` — regenerated:
  the `plugin-packs` atom removed from the catalog, every `depends_on` edge to it dropped,
  tldr/summary rows refreshed for the rewritten atoms.
- Untouched, with reason: every other product atom — none carried a plugin claim.

## Dispositions

No backlog item and no bug drove this release; the origin is the operator decree of
2026-08-10, recorded in SPEC §Source. There is therefore nothing to flip terminal from a
picked set.

| File | Kind | Terminal status | Evidence |
|---|---|---|---|
| — (operator decree; no picked backlog or bug set) | — | n/a | SPEC §Source; Summary above |

Open backlog entries carried from v0.3.0 (`20260806-clean-architecture-remediation.md`
Items 4/5/6, `20260806-dadaia-md-workspace-system-prompt.md` named-migrations acceptance,
`20260715-bugfix-workflow-tdd.md` routed to PM, `20260810-security-low-carryforwards-v030.md`)
are **untouched by this release** and remain the project-manager's to pick.

## Backlog returns

- `backlog/candidates.md` ← **`software-engineer.md` prose residue.** Retire the
  "No frontend/AI-entity/specs/CI" frontmatter `description:` clause and the "never touch
  browser frontend" body sentence, both of which now contradict the agent's own write
  table. Cosmetic, zero behavioural risk. See drift *software-engineer-prose-residue*.

## Archive decision

**MOVE** — after `feature/v0.4.0` is reviewed, pushed, merged and CI is green, move the
release directory to `specs/_archive/releases/v0.4.0/` via `git mv` and repoint
`specs/releases/ACTIVE.md`. **Deliberately not performed now:** archiving is a `git mv`
into a FROZEN path (product-engineer has no `Bash`), and it is the operator's ship
decision. `specs/releases/v0.3.0/` is archived in the same sweep — its own CLOSURE lists
the mechanical steps still pending there.
