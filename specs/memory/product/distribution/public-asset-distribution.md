---
slug: public-asset-distribution
title: public-asset-distribution
category: product
tldr: Canonical public assets staged to .dadaia/agentic and projected to the Claude Code, Codex, Kimi Code and .agents roots, hash-compared by doctor.
summary: The stage, install and doctor chain distributing the agentic surface into runtime roots, with hash-compare overwrite, rendered agents, whole-folder skills and a privacy gate.
tags: [public, assets, distribution, projection, privacy]
---

## The chain

- `dadaia public stage` copies `dadaia_workspace/public/` into `.dadaia/agentic/<type>/` with a SHA256 manifest.
- `dadaia public install` projects staged assets into `.claude/`, `.codex/`, `.kimi-code/`, `.agents/`, the root law pair, scoped rule files and the Codex hook wrappers under `.dadaia/hooks/`.
- `projection_rules(plan)` builds one `ProjectionRule(label, dst, render, compare, ownership)` table; `install` writes it, `doctor` compares it and the install ledger is its destination list — no second derivation of the managed set.
- `HarnessProjection` has three production adapters — Claude Code, Codex, Kimi Code — each contributing its own rules plus the doctor lines a byte-compare cannot express.
- The renderer is the only verifier: a rule's `render` maps the bytes on disk to the bytes that belong there, so a `bytes` rule is a plain compare while an `owned-slice` or `managed-block` rule is a fixed point that leaves an operator's own keys alone.
- There is no `public/hooks/`: governance hooks are the Python package `dadaia_workspace/hooks/`.
- Install compares content, not existence — a differing staged hash overwrites without `--force`, which is reserved for a hand-edited projection.
- The nine `agents/*.md` bodies stage generic and render at install as `render(staged body + resolved (model, effort))`, precedence override > template > `balanced` over `.dadaia/states/agent_model_policy.json`.
- Codex render fails closed without a model, and the manifest keeps hashing the policy-free staged bytes.
- A skill is a folder and every file in it is projected, to `.agents/skills/<name>/` plus `.claude/skills/<name>/`; Codex and Kimi Code read the shared root natively, with no per-harness copy ([[agentic-entities]]).
- `stage` fills the `<!-- zones -->` and `<!-- canon -->` placeholders of the `.dadaia/AGENTS.md` and `.dadaia/states/AGENTS.md` fragments from the zone registry, so the projected tables are the registry ([[workspace-doctor]]); scripts are staged under `agentic/scripts` and never projected — git hooks and CI execute the package copy, and the memory-atom lint lives in `features/specs/memory_lint.py`.

## Doctor

- `dadaia public doctor` compares source against staging, then staging against each runtime projection, emitting `[ok]`, `[missing]`, `[drift]` or `[foreign]` per file and a non-zero exit on any mismatch.
- A core `claude:agents/*.md` label compares against `render(staged + resolved policy)`, so an applied policy reads `[ok]` and a hand-edit `[drift]`; a Codex TOML is byte-compared to its render exactly as a Claude agent is.
- The privacy gate runs over source and staged assets, reporting `[ok] public-privacy` only on a clean surface, which CI treats as a release gate.
- With `.dadaia/states/harness_profile.json` present, `install` without `--target` covers the profile's harnesses plus the shared `agents` tree; an absent profile means all four ([[workspace-init]]).
- Doctor builds its rule table for the profile's harnesses only; an entry inside a harness dir that the install ledger does not name is `dadaia doctor`'s `WS-<harness>-slop`, never a `public doctor` line ([[workspace-doctor]]).

## Scaffold and consumer fan-out

- The scaffolded `specs/` tree is the v6 canon — `backlog/`, `bugs/`, `memory/`, `releases/`, `audits/`, `ADRs/`, `constitution.md`, `AGENTS.md` — stamped `specs_pattern_version: 6`.
- Each scoped `AGENTS.md` is hash-projected and doctor-compared; operator-owned domain-scoped files are never overwritten.
- Repo templates land at `alive()`, not at install: `repo-AGENTS.md` to the repo root, `tests-AGENTS.md` only when `tests/` is a real directory holding no such file.
- Templates ship parameterized, so an installed file still carrying `<ANGLE-BRACKET>` placeholders is the drift `specs doctor` reports ([[specs-doctor]]).
- Consumer-repo `AGENTS.md` fan-out is provenance-gated by the canonical banner: absent creates, a stale banner is restored as `[updated]`, a bannerless file is `[foreign]` and never overwritten.
- A registry `repo_slug` is accepted only as a single, relative, non-dot path component validated lexically, so a symlinked `repos/<slug>` directory is allowed while a symlinked destination file is `[foreign]`.
- `public install` refuses the `dadaia-workspace` source repo root unless `DADAIA_ALLOW_SOURCE_ROOT_PUBLIC_INSTALL=1` is set.
