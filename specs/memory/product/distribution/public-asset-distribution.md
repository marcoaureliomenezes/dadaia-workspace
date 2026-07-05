---
slug: public-asset-distribution
title: public-asset-distribution
category: product
tldr: canonical public assets are staged to .dadaia/agentic and projected to Claude Code, Codex, PI, and shared .agents roots.
summary: Describes the canonical public asset chain, hash-compare install overwrite, staging-vs-projected drift detection, privacy gate, harness-profile-aware install/doctor, plugin-pack projection with installed-plugins ledger + core-install precedence, provenance-gated consumer AGENTS fan-out (banner-canonical restored vs hand-authored left [foreign]), scoped AGENTS projections, source-root hygiene guard, and runtime projection contract.
tags:
- public
- assets
- distribution
- projection
- privacy
token_estimate: 1010
last_updated: '2026-07-04'
release_origin: v0.1.60
---

## Purpose

`dadaia public {stage|install|doctor}` distributes the public agentic surface of
`dadaia-workspace`. The live asset types under `dadaia_workspace/public/` are:
`agents`, `skills`, `rules`, `workflows`, `scripts`, `schemas`, `templates`, `data`,
`scaffold`, `runtime`, `personas`, `lifecycle_fragments`, and `pi` (there is no
`public/commands/` or `public/hooks/` — governance hooks are the Python package
`dadaia_workspace/hooks/`, not a projected asset type).

`public stage` copies that source into `.dadaia/agentic/<type>/` with a manifest.
`public install` projects staged assets into runtime-specific roots: `.claude/`,
`.codex/`, `.pi/`, `.agents/`, workspace-root `AGENTS.md`/`CLAUDE.md`, scoped
runtime rule files, and the Codex hook wrappers under `.dadaia/hooks/`.

## Differentiator

Default public assets must be generic and safe for any consumer. They must not
ship private project names, private repo paths, hostnames, IP addresses,
credentials, vendor/domain packs, or personal operational rules.

`dadaia public install` performs a SHA256 content-hash comparison before skipping
an existing projected file. When the staged hash differs from the projected file's
hash, the file is overwritten without requiring `--force`. This makes plain `install`
the correct propagation step for all legitimate source edits. `--force` is reserved
for repairing locally-divergent projections (e.g. a file an operator edited in-place).

`dadaia public doctor` performs three comparison passes: source vs staging, staging
vs projected (one pass per runtime target). Any mismatch emits `[drift] <path>` and
returns a non-zero exit code, giving an accurate all-clear only when all three tiers
agree. The `dadaia-workspace-dev-guardrail` rule reflects this corrected workflow.

`dadaia public doctor` also includes a public privacy gate. It scans source/staged
public assets with a denylist for private identifiers and reports
`[ok] public-privacy` only when the distributed surface is clean. CI treats this
as a release gate.

Install-all and doctor are **harness-profile-aware**. When
`.dadaia/states/harness_profile.json` exists (written by `dadaia init --harness <set>` —
[[workspace-init]]), `install` with no `--target` (and `--target all`) installs only the
profile's harness set (plus the shared `agents` tree); an **absent profile ⇒ all-four**
(back-compat, byte-identical to the pre-profile behaviour, golden-locked). An explicit
`--target claude|codex|pi|agents` always overrides regardless of profile. `doctor` scopes
its per-runtime expectations to the profile: the inline projection comparison for `.claude/`
`settings.json`, the `.codex/` hooks/config/rules/wrappers (**including** the codex-parity
drift block `check_codex_drift` / D-CX-1..10 that would otherwise emit
`[missing] codex:agents/*.toml` for any codex-absent tree), and the `.pi/` tree each run
only when their harness is in the profile. The shared surfaces stay unconditional
(agents/`.agents` skills, the AGENTS.md guardrail pair, the harness-independent git
chokepoint scripts, `_check_public_privacy`, the git-dirty check). **Out-of-profile is
never silent:** a runtime directory that physically EXISTS on disk but is outside the
profile (e.g. an operator hand-installed `.codex/`, or a re-profiled all-four workspace)
emits a non-silent `[warn]`/`[drift]` line — pure silence (zero lines) is reserved only for
a harness whose directory is genuinely absent. "Green" is mechanical: no
`[missing]`/`[drift]`/`[fail]` line for the profile's out-of-scope harnesses AND, via the
CLI, `dadaia public doctor` exit 0.

## Usage flow

The root `AGENTS.md` is a short global router. Specific behavior lives in
scoped AGENTS files:

- `.dadaia/AGENTS.md` — runtime control-plane ownership.
- `.dadaia/tmp/AGENTS.md` — temporary artifact policy.
- `.dadaia/states/AGENTS.md` — machine-owned state policy.
- `.dadaia/reports/AGENTS.md` — human-readable report policy.
- `.dadaia/handoff/AGENTS.md` — machine-readable handoff policy.
- `specs/AGENTS.md` and repo-local `AGENTS.md` — SDD and production-source scope.

The installer and doctor manage only lib-originated projections. Operator-owned
domain-scoped AGENTS files are not overwritten.

**Consumer-repo `AGENTS.md` fan-out (registry-detected, provenance-gated).** The workspace-law
pair (`data/AGENTS.md` → root `AGENTS.md` + a 1-line `CLAUDE.md` bridge) fans out to every Spec
Context repo. Consumer repos are detected from `.dadaia/states/spec_contexts.json` via a
**defensive `json.loads`** (never-raises: a malformed/old registry cannot crash the fan-out
or doctor) — `repos/<repo_slug>/` for each context whose directory exists on disk (alive OR
dead), minus the self-repo (`dadaia-workspace` source keeps its hand-synced copy).

The fan-out is **provenance-gated**: it only ever restores a consumer `AGENTS.md` it can PROVE
is a stale canonical projection. `workspace_guardrail.py` holds a fixed module constant
`_CANONICAL_AGENTS_BANNER` (the generated `public/data/AGENTS.md` banner block — only
`public install` emits it), byte-equality-asserted against the shipped banner by a contract
test (no runtime read of `public/data`). Three cases per consumer `AGENTS.md`: **absent** →
create + `[ok]`; **existing, carries the canonical banner** → stale canonical → restore + a
DISTINCT `[updated] <path> (overwrote divergent workspace-law copy)` line; **existing, no
canonical banner** → **FOREIGN (hand-authored, repo-owned)** → `[foreign] <path> — left
untouched`, **never overwritten** (this replaces the v0.1.58 "consumer root is lib-owned
canonical / every divergent copy is restored" behavior — a hand-authored root `AGENTS.md` is
the repo's own scoped governance file per the workspace-law text). The `CLAUDE.md` bridge
**follows its sibling's fate** — written only when the `AGENTS.md` was created/restored; when
`AGENTS.md` is `[foreign]`, no `CLAUDE.md` is dropped.

**Doctor is provenance-aware on the PAIR.** A single consumer-classification authority
(`_doctor_consumer_pair_lines`) is the ONLY path that doctors consumer repos — `manager.doctor()`
calls it after the runtime loop and `_doctor_guardrail_pair` delegates to it (no parallel legacy
path). For a hand-authored consumer, **both** the `AGENTS.md` and the paired `CLAUDE.md` doctor
lines report `[foreign]` (never `[missing]`/`[drift]`), so `dadaia public doctor` **exits 0**
instead of perpetually red; a banner-bearing (canonical) copy keeps `[ok]`/`[drift]`/`[missing]`
on both lines. The memory/scaffold `AGENTS.md` tri-copy (`specs/AGENTS.md`,
`specs/memory/AGENTS.md`) is untouched by this fan-out.

**Plugin-pack projection ([[plugin-packs]]).** `public/plugins/<pack>/` is staged into
`.dadaia/agentic/plugins/<pack>/` like every other asset type. `dadaia plugin install <pack>`
projects a pack's agents/skills/rules into the runtime roots (profile-scoped, exactly like core
`install --target all`), overwriting the projected core stub agent with the pack's real body,
and records the pack in the per-workspace ledger `.dadaia/states/installed_plugins.json`.
**Projection precedence:** core `public install` reads that ledger and re-projects the pack body
(not the stub) for any installed plugin, so a later core install never silently reverts an
installed pack agent. `plugin doctor` reports `[ok]`/`[drift]`/`[missing]` per installed-pack
file; with no plugin installed the install/doctor surface is byte-identical to the no-plugin
baseline (golden-locked).

## Runtime state touched

The `dadaia-workspace` source repo must stay free of root runtime projections
and local harness files. Generated/local artefacts such as `.dadaia/`,
`.agents/`, `.claude/`, `.codex/`, `.pi/`, `CLAUDE.md`,
`Makefile`, root `playwright.config.ts`, `playwright-report/`, and
`test-results/` are ignored and guarded by tests/CI.

`public install` refuses to install projections into the source repo root unless
the operator explicitly opts in with `DADAIA_ALLOW_SOURCE_ROOT_PUBLIC_INSTALL=1`.
Staged temp workspaces remain supported.

## Dependencies

- Claude Code: `.claude/agents`, `.claude/skills`, `.claude/rules`,
  `.claude/workflows`, `.claude/settings.json` (hook registration).
- Codex: `.codex/config.toml`, `.codex/hooks.json` (referencing the `.dadaia/hooks/codex-*`
  wrappers), `.codex/agents`, `.codex/rules`, `.codex/skills`, reference workflows, and
  `AGENTS.md` context.
- PI: `.pi/` Layer-1 surface — exactly `SYSTEM.md`, `settings.json`,
  `prompts/dadaia-context.md`, and `extensions/dadaia-sdd-gate.ts` (post-trust
  executable). This atom is the sole owner of the `.pi/` surface inventory.
- Shared: `.agents/skills` and workspace/repo AGENTS.md/CLAUDE.md pairs.

`public doctor` compares canonical source, staging, and projections across three
passes; filters cache files such as `__pycache__/` and `*.pyc`; and reports drift
as actionable `[missing]`, `[drift]`, `[ok]`, or reference-only runtime status. A
non-zero exit code is returned on any source↔staging or staging↔projected mismatch.

Codex hook projection writes the nested Codex hook schema under `.codex/hooks.json`,
whose command strings point at the self-locating executable wrappers
`.dadaia/hooks/codex-{pre-gate,post-gate,ctx-inject,ctx-inject-session-start}`
(Codex direct-execs hook strings; each wrapper resolves the workspace venv Python
relative to its own path and carries its env, e.g. `DADAIA_HOOK_OUTPUT=codex-json`).
`PreToolUse` matches `^(apply_patch|Edit|Write|Bash)$`; PostToolUse is matcher-less
(Codex match-all); ctx-inject registers on `SessionStart` (`startup|resume`) and
`UserPromptSubmit`. Forced Codex installs remove stale generated `.codex/agents/*.toml`
and `.codex/workflows/*.workflow.md` files that no longer exist in canonical public
assets.
