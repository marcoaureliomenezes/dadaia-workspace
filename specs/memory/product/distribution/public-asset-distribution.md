---
slug: public-asset-distribution
title: public-asset-distribution
tldr: Public assets staged once, projected into the authored set (root map, scoped AGENTS.md, .agents/skills, .agents/agents); .claude/ entries are symlinks.
summary: The stage, install and doctor chain distributing the agentic surface into runtime roots, with hash-compare overwrite, rendered agents, whole-folder skills and a privacy gate.
tags: [public, assets, distribution, projection, privacy]
---

## The chain

- `dadaia public stage` copies `dadaia_workspace/public/` into `.dadaia/agentic/<type>/` with a SHA256 manifest.
- `dadaia public install` projects staged assets into the authored set — the root `AGENTS.md` map, the scoped `AGENTS.md` family, `.agents/skills/`, `.agents/agents/` — plus `.claude/settings.json` and per-entry symlinks under `.claude/`, `.codex/{config.toml,hooks.json,rules,agents/*.toml}`, `.cursor/{hooks.json,agents/*.md}`, `.devin/hooks.v1.json`, `.github/{hooks/*.json,agents/*.agent.md}` and every hook wrapper under `.dadaia/hooks/<harness>-*`; Kimi Code's own set is empty (ADR 0017).
- `projection_rules(plan, harnesses)` builds one `ProjectionRule(label, harness, dst, render, compare, mode)` table; `install` writes it, `doctor` compares it and the install ledger is its destination list — no second derivation of the managed set.
- `core/harness_registry.HARNESS_RECORDS` is the one home of a harness: one `HarnessRecord(name, directory, agent_transcode, hooks)` per harness (six at 0.4.7 c8), the `agent_transcode` builders in `infrastructure/agent_transcodes.py` and the `HOOK_DIALECTS` table in `runtime_transforms/hook_wrappers.py` derive every rule from the record — the projection table has no harness-named branch, and adding a harness is one data row; a `ProjectionRule` is a file, a relative symlink (`link_to`) or its hash-verified copy fallback, and the install ledger records each entry's kind (`file|symlink|copy`) so a copy never passes as a link.
- The renderer is the only verifier: a rule's `render` maps the bytes on disk to the bytes that belong there, so a `bytes` rule is a plain compare while an `owned-slice` or `managed-block` rule is a fixed point that leaves an operator's own keys alone.
- There is no `public/hooks/`: governance hooks are the Python package `dadaia_workspace/hooks/`.
- Install compares content, not existence — a differing staged hash overwrites without `--force`, which is reserved for a hand-edited projection.
- The three `agents/dd-*.md` bodies stage generic and render once into `.agents/agents/` as `render(staged body + resolved (model, effort) + activity_class privileges)`, precedence override > template > `balanced` over `.dadaia/states/agent_model_policy.json`; a retired persona key in that JSON migrates on read.
- Codex render fails closed without a model, and the manifest keeps hashing the policy-free staged bytes.
- A skill is a folder and every file in it is projected once to `.agents/skills/<name>/`; `.claude/skills/<name>` is a relative symlink to it; Codex and Kimi Code read the shared root natively ([[agentic-entities]]).
- `stage` renders five placeholders from `core/workspace_layout.py` through `render_registry_tables` — `<!-- zones -->` and `<!-- canon -->` in the `.dadaia/AGENTS.md` and `.dadaia/states/AGENTS.md` fragments, `<!-- root -->` in the root map, `<!-- repo-excluded -->` in `repo-AGENTS.md` and `<!-- specs-canon -->` in `specs-AGENTS.md` — so every canon table in the projected law is the registry, pinned row for row by `tests/contract/test_zone_registry.py` ([[workspace-doctor]]); scripts are staged under `agentic/scripts` and never projected — git hooks and CI execute the package copy, and the memory-atom lint lives in `features/specs/memory_lint.py`.

## Doctor

- `dadaia public doctor` compares source against staging, then staging against each runtime projection, emitting `[ok]`, `[missing]`, `[drift]` or `[foreign]` per file and a non-zero exit on any mismatch.
- A core `agents:agents/dd-*.md` label compares against `render(staged + resolved policy)`, so an applied policy reads `[ok]` and a hand-edit `[drift]`; a Codex TOML is byte-compared to its transcode; `SYMLINK-TARGET-1` attests every ledgered link entry of every harness: a symlink resolving to its canonical `.agents/` path or a hash-equal copy, anything else one finding with `fix: .dadaia/.venv/bin/dadaia public install --force`.
- The privacy gate runs over source and staged assets, reporting `[ok] public-privacy` only on a clean surface, which CI treats as a release gate.
- `install` and `doctor` cover the roster in `.dadaia/states/harness_profile.json` plus the shared authored set; `dadaia harness add <name>` is the one way a harness joins the roster (`public install --target` died at 0.4.7 c8), and a missing profile is read once as the harness directories present at the root ([[workspace-init]]).
- Doctor builds its rule table for the profile's harnesses only; an entry inside a harness dir that the install ledger does not name is `dadaia doctor`'s `WS-<harness>-slop`, never a `public doctor` line ([[workspace-doctor]]).

## Scaffold and consumer fan-out

- The scaffolded `specs/` tree is the v6 canon — `backlog/`, `bugs/`, `memory/`, `releases/`, `audits/`, `ADRs/`, `constitution.md`, `AGENTS.md` — stamped `specs_pattern_version: 6`.
- The scaffolded `specs/AGENTS.md` (`templates/specs-AGENTS.md`) is a statement list — load order pointing at `dd-spec-navigator`, the authority table, escalation — with no gate claim and no root `_archive/`; every scoped scaffold `AGENTS.md` is the system of record of its area (<= 4096 B; the root map <= 8192 B; every `SKILL.md` <= 6144 B — `tests/contract/test_context_map.py`, `public/data/CONTEXT-MAP.md`), and `TREE-5` heals each by shipped hash ([[workspace-doctor]]).
- Each scoped `AGENTS.md` is hash-projected and doctor-compared; operator-owned domain-scoped files are never overwritten.
- Repo templates land at `alive()`, not at install: `repo-AGENTS.md` to the repo root, `tests-AGENTS.md` only when `tests/` is a real directory holding no such file.
- Templates ship parameterized, so an installed file still carrying `<ANGLE-BRACKET>` placeholders is the finding `dadaia doctor`'s `specs` section reports (`AGENTS-PLACEHOLDER-1`, `MEM-PLACEHOLDER-1`; [[workspace-doctor]]).
- Consumer-repo `AGENTS.md` fan-out is provenance-gated by the canonical banner: absent creates, a stale banner is restored as `[updated]`, a bannerless file is `[foreign]` and never overwritten.
- A registry `repo_slug` is accepted only as a single, relative, non-dot path component validated lexically, so a symlinked `repos/<slug>` directory is allowed while a symlinked destination file is `[foreign]`.
- `public install` refuses the `dadaia-workspace` source repo root unless `DADAIA_ALLOW_SOURCE_ROOT_PUBLIC_INSTALL=1` is set.
