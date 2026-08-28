---
slug: public-asset-distribution
title: public-asset-distribution
category: product
tldr: Canonical public assets staged to .dadaia/agentic and projected to the Claude Code, Codex, Kimi Code and .agents roots, hash-compared by doctor.
summary: '`dadaia public {stage|install|doctor}` distributes the agentic surface from `dadaia_workspace/public/` through a staging manifest into runtime-specific roots, with hash-compare overwrite, render-at-install for core agents, whole-folder skill projection, a privacy gate and harness-profile awareness.'
tags:
- public
- assets
- distribution
- projection
- privacy
---

## The chain

`dadaia public stage` copies `dadaia_workspace/public/` into `.dadaia/agentic/<type>/` with a SHA256
manifest. `dadaia public install` projects staged assets into `.claude/`, `.codex/`, `.kimi-code/`,
`.agents/`, the workspace-root `AGENTS.md`/`CLAUDE.md` pair, scoped rule files, and the Codex hook
wrappers under `.dadaia/hooks/`. Asset directories are `agents`, `data`, `entities`, `kimi-code`,
`runtime`, `scaffold`, `schemas`, `scripts`, `skills`, `templates`; there is no `public/hooks/`,
governance hooks being the Python package `dadaia_workspace/hooks/`. Default public assets stay
generic: no private project or repo names, hostnames, IP addresses, credentials, vendor packs or
operator-local paths.

- **Install compares content, not existence** — a differing staged hash overwrites without
  `--force`, which is reserved for a projection hand-edited away from both source and staging.
- **Core agents are rendered, not copied.** The nine `agents/*.md` bodies stage generic; at install
  each is `render(staged body + resolved (model, effort))` from the agent-model policy (template
  plus the `.dadaia/states/agent_model_policy.json` overlay, precedence override > template >
  `balanced`). Codex render fails closed without a model, and the manifest keeps hashing the
  policy-free staged bytes.
- **A skill is a folder, and every file in it is projected**, to `.agents/skills/<name>/` plus
  `.claude/skills/<name>/`; Codex and Kimi Code read the shared `.agents/skills/` root natively, so
  no per-harness copy and no registry entry exist. The surface is 22 skills, each with a
  behavior-map row ([[agentic-entities]]), and a stage's procedure exists only in its skill.
- **The law reaches each harness exactly once**, decided at the projection seam; no harness ends
  with zero copies, and law files stay PROTECTED and human-only.
- **A projected script is a thin wrapper** over the package implementation, forwarding its exit
  code — the memory-atom lint lives in `features/specs/memory_lint.py` and is imported directly by
  the doctor.

## Doctor

`dadaia public doctor` runs three comparison passes — source vs staging, and staging vs projection
once per runtime target — emitting `[ok]`, `[missing]`, `[drift]` or `[foreign]` per file and a
non-zero exit on any mismatch. A core `claude:agents/*.md` label compares against
`render(staged + resolved policy)`, so an applied operator policy reads `[ok]` and a hand-edited
file `[drift]`; Codex agent TOMLs are checked structurally, never byte-compared. Doctor also runs
the public privacy gate over source and staged assets, reporting `[ok] public-privacy` only on a
clean surface, which CI treats as a release gate. Byte goldens pin policy only, while the per-file
inventory is a roster scanned from `public/**` at test time, so adding or removing an asset fails
the roster and leaves the goldens green ([[quality-assurance]]).

With `.dadaia/states/harness_profile.json` present ([[workspace-init]]), `install` without
`--target` installs only the profile's harness set plus the shared `agents` tree; an absent profile
means all four, and an explicit `--target` always overrides. Doctor scopes per-runtime expectations
to the profile, keeps shared surfaces unconditional, and emits a `[warn]`/`[drift]` line for a
runtime directory present on disk but outside the profile.

## Scaffold and consumer fan-out

The root `AGENTS.md` is a short router; specific behavior lives in scoped files under `.dadaia/`,
`specs/` and each repo. **The scaffolded `specs/` tree is the v6 canon**: `backlog/`, `bugs/`,
`memory/`, `releases/`, `audits/`, `ADRs/`, `constitution.md`, `AGENTS.md`, stamped
`specs_pattern_version: 6`, one scoped `AGENTS.md` per area, each hash-projected, doctor-compared
and carrying a behavior-map row. Operator-owned domain-scoped files are never overwritten.

**Repo templates land at `alive()`, not at install**: `repo-AGENTS.md` to the repo root and
`tests-AGENTS.md` to `<repo>/tests/AGENTS.md`, the second only when `tests/` is a real directory and
no file is already there. The template ships parameterized with `<ANGLE-BRACKET>` placeholders, so
an *installed* file still carrying them is the drift `specs doctor` reports ([[specs-doctor]]).

**Consumer-repo `AGENTS.md` fan-out is registry-detected and provenance-gated**, `public install`
alone emitting the fixed canonical banner. Three cases: absent → create; banner present → stale
canonical, restored with a distinct `[updated]` line; no banner → hand-authored and repo-owned,
`[foreign]`, never overwritten, the `CLAUDE.md` bridge following its sibling's fate. A registry
`repo_slug` is accepted only as a single, relative, non-dot path component, validated lexically
rather than through `resolve()`, so a symlinked `repos/<slug>` *directory* stays allowed while a
destination **file** that is a symlink classifies `[foreign]` and is never written through.
`public install` refuses the `dadaia-workspace` source repo root unless
`DADAIA_ALLOW_SOURCE_ROOT_PUBLIC_INSTALL=1` is set.
