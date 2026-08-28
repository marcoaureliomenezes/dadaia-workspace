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
last_updated: '2026-08-28'
release_origin: 0.5.0
---

## Purpose

`dadaia public stage` copies `dadaia_workspace/public/` into `.dadaia/agentic/<type>/`
with a SHA256 manifest. `dadaia public install` projects staged assets into `.claude/`,
`.codex/`, `.kimi-code/`, `.agents/`, the workspace-root `AGENTS.md`/`CLAUDE.md` pair,
scoped rule files, and the Codex hook wrappers under `.dadaia/hooks/`.

Asset directories on disk: `agents`, `data`, `entities`, `kimi-code`, `runtime`,
`scaffold`, `schemas`, `scripts`, `skills`, `templates`. There is no `public/hooks/` —
governance hooks are the Python package `dadaia_workspace/hooks/`, not a projected asset.

Default public assets stay generic: no private project or repo names, hostnames, IP
addresses, credentials, vendor packs or operator-local paths.

## Current behavior

**Install compares content, not existence.** A SHA256 comparison precedes any skip; a
staged hash differing from the projected file overwrites without `--force`. Plain `install`
is therefore the propagation step for every legitimate source edit; `--force` is for a
projection an operator hand-edited away from both source and staging.

**Core agents are rendered, not copied.** The nine `agents/*.md` bodies stage generic (no
`model:`/`effort:`); at install each is composed as `render(staged body + resolved (model,
effort))` from the agent-model policy — template plus the
`.dadaia/states/agent_model_policy.json` overlay, precedence override > template >
`balanced`. The rendered lines are appended as the last frontmatter lines of
`.claude/agents/<name>.md`, and the same resolved pair feeds `.codex/agents/*.toml`. Codex
render **fails closed** when neither a staged nor a resolved model is supplied. The staging
manifest keeps hashing the policy-free staged bytes; only the projection write and compare
go through the render seam.

**A skill is a folder, and every file in it is projected.** A universal skill stages from
`public/skills/<name>/` and installs to `.agents/skills/<name>/` plus
`.claude/skills/<name>/`; Codex and Kimi Code read the shared `.agents/skills/` root
natively, so no per-harness copy exists and no `registry.json` entry is created. Staging,
install and doctor cover every disclosed sibling, each tracked in the manifest. The surface
is 22 skills, each carrying a row in `public/entities/behavior-map.json`
([[agentic-entities]]).

The `dd-` lifecycle family is distributed on that same universal path, one skill per stage:
`dd-backlog-definition`, `dd-release-definition`, `dd-release-implement` (disclosed to
`RC-FLOW.md`, `RELEASE-EVENTS.md`, `MEMORY-UPDATE.md`), `dd-audit-project` (disclosed to
`PILLAR-BUGS.md`, `PILLAR-SPECS.md`, `PILLAR-MEMORY.md`, `FINDINGS-FORMAT.md`),
`dd-bug-registration`, `dd-bug-resolution` and `dd-diagnose` (disclosed to `LINEAGE.md`).
The law carries the classification and points at the stage's skill; the procedure exists
only in the skill. Harness literacy has one home, `dd-ai-eng-knowhow`, whose
`ai-engineer`-only depth siblings link to vendor documentation rather than reproduce it.

**The law reaches each harness exactly once.** Which surface carries `DADAIA.md` is decided
at the projection seam: a harness whose constitution resolves an import chain to the law
needs no rules-directory mirror, and one that reads `AGENTS.md` natively keeps its own path.
No harness ends with zero copies, and the law files stay PROTECTED and human-only.

**A projected script is a thin wrapper, never the implementation.** Every file under
`public/scripts/` is a CLI entry point that imports the package implementation and forwards
its exit code, asserted by `tests/contract/test_public_scripts_thin_wrapper.py`. The
memory-atom lint is the worked example: the check set lives in
`features/specs/memory_lint.py` and is imported directly by the doctor, with no subprocess
to a projected script; `public/scripts/lint-memory-atoms.py` survives only as a standalone
invocation surface.

## Doctor

`dadaia public doctor` runs three comparison passes — source vs staging, and staging vs
projection once per runtime target — emitting `[ok]`, `[missing]`, `[drift]` or `[foreign]`
per file and a non-zero exit on any mismatch. `__pycache__/` and `*.pyc` are filtered.

The staging↔projection pass for a core `claude:agents/*.md` label compares against
`render(staged + resolved policy)`, so an applied operator policy reads `[ok]` and a
hand-edited `.claude/agents/*.md` reads `[drift]`. The overlay is loaded once per run
(absent ⇒ `balanced`; invalid ⇒ an `agent-model-policy` error line). Codex agent TOMLs are
structurally checked (`check_codex_drift`), never byte-compared;
`features/public/model_resolution.py` validates the resolved core roster against the
registry and effort vocabulary.

Doctor also runs the public privacy gate, scanning source and staged assets with a denylist
for private identifiers and reporting `[ok] public-privacy` only on a clean surface. CI
treats it as a release gate.

**Byte goldens pin policy; a derived roster pins the inventory.** The install-target and
profile-doctor goldens assert target mapping, banners and mode/newline conventions, and
carry no per-file inventory. The inventory is a roster scanned from
`dadaia_workspace/public/**` at test time on the asset manager's own include/exclude walk,
so adding or removing an asset fails the roster and leaves both goldens green. The skill
inventory rides one derived oracle extracted from that roster ([[quality-assurance]]).

**Install and doctor are harness-profile-aware.** With `.dadaia/states/harness_profile.json`
present ([[workspace-init]]), `install` without `--target` installs only the profile's
harness set plus the shared `agents` tree; an absent profile means all four. An explicit
`--target claude|codex|kimi-code|agents` always overrides. Doctor scopes its per-runtime
expectations to the profile while keeping shared surfaces unconditional. Out-of-profile is
never silent: a runtime directory that exists on disk but sits outside the profile emits a
`[warn]`/`[drift]` line — silence is reserved for a genuinely absent harness.

## Usage flow

The root `AGENTS.md` is a short router; specific behavior lives in scoped files —
`.dadaia/AGENTS.md`, `.dadaia/tmp/AGENTS.md`, `.dadaia/states/AGENTS.md`,
`.dadaia/reports/AGENTS.md`, `.dadaia/handoff/AGENTS.md`, `specs/AGENTS.md`, and each
repo-local `AGENTS.md`.

**The scaffolded `specs/` tree is the v6 canon.** A fresh scaffold emits exactly
`backlog/`, `bugs/`, `memory/`, `releases/`, `audits/`, `ADRs/`, `constitution.md` and
`AGENTS.md`, stamped `specs_pattern_version: 6`, with one scoped `AGENTS.md` per area. No
`README.md` survives in the scaffold, and there is no `specs/assets/` or
`backlog/remote-bugs/`. Every scoped rule file is hash-projected and doctor-compared, and
carries a behavior-map row.

The installer and doctor manage only lib-originated projections; operator-owned
domain-scoped `AGENTS.md` files are never overwritten.

**Repo templates land at `alive()`, not at install.** `features/spec_context` copies
`public/templates/repo-AGENTS.md` to the Spec Context repo root and
`public/templates/tests-AGENTS.md` to `<repo>/tests/AGENTS.md` — the second only when
`tests/` is a real directory and no file is already there. The copy never creates `tests/`
and never overwrites an operator file. The template ships parameterized with
`<ANGLE-BRACKET>` placeholders, so an *installed* `tests/AGENTS.md` still carrying them is
the drift `specs doctor` reports — against the installed file, never the template
([[specs-doctor]]).

**Consumer-repo `AGENTS.md` fan-out is registry-detected and provenance-gated.** Consumer
repos come from `.dadaia/states/spec_contexts.json` through a never-raising `json.loads`;
the self-repo is excluded. `infrastructure/workspace_guardrail.py` holds the fixed
`_CANONICAL_AGENTS_BANNER` constant that `public install` alone emits, byte-asserted against
the shipped banner by a contract test. Three cases: absent → create; banner present → stale
canonical, restored with a distinct `[updated]` line; no banner → hand-authored and
repo-owned, `[foreign]`, never overwritten. The `CLAUDE.md` bridge follows its sibling's
fate.

The write path is contained: a registry `repo_slug` is accepted only as a single, relative,
non-dot path component (rejecting separator carriers, `.`/`..`, and POSIX/Windows absolute
forms via both `PurePosixPath` and `PureWindowsPath`), with a non-silent `[reject]` line and
fail-open derivation, plus a write-time assert that the join's parent is `repos/`. The
validation is lexical rather than `resolve()`-based, so a symlinked `repos/<slug>`
*directory* stays allowed. A destination **file** that is a symlink — dangling included — is
never written through and classifies `[foreign]`. `_doctor_consumer_pair_lines` is the one
consumer-classification authority, so a hand-authored consumer keeps `public doctor` at
exit 0.

## Runtime state touched

- Projections: `.claude/agents`, `.claude/skills`, `.claude/settings.json`;
  `.codex/config.toml`, `.codex/hooks.json`, `.codex/agents`, `.codex/rules`,
  `.codex/skills`, `.codex/DADAIA.md`; `.kimi-code/`; the shared `.agents/skills` root and
  the workspace/repo `AGENTS.md`/`CLAUDE.md` pairs.
- Codex hook projection writes the nested schema in `.codex/hooks.json`, pointing at the
  self-locating wrappers `.dadaia/hooks/codex-{pre-gate,post-gate,ctx-inject,ctx-inject-session-start}`,
  each resolving the workspace venv Python relative to its own path. `PreToolUse` matches
  `^(apply_patch|Edit|Write|Bash)$`; PostToolUse is matcher-less; ctx-inject registers on
  `SessionStart` (`startup|resume`) and `UserPromptSubmit`. A forced Codex install removes
  stale generated `.codex/agents/*.toml` no longer present in source.
- The `dadaia-workspace` source repo stays free of root runtime projections and local
  harness files; `public install` refuses to install into the source repo root unless
  `DADAIA_ALLOW_SOURCE_ROOT_PUBLIC_INSTALL=1` is set.
