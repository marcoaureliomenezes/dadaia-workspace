---
slug: public-asset-distribution
title: public-asset-distribution
category: product
tldr: canonical public assets are staged to .dadaia/agentic and projected to Claude Code, Codex, Kimi Code, and shared .agents roots.
summary: Describes the canonical public asset chain, hash-compare install overwrite, staging-vs-projected drift detection, privacy gate, universal skills projected to one canonical .agents/skills home with no registry entry, the thin-wrapper contract that keeps every public/scripts file an entry point over the package implementation, repo templates copied at alive() (repo-AGENTS.md, with destination-file symlink refusal at every write site, plus a conditional tests/AGENTS.md), harness-profile-aware install/doctor, render-at-install of core agents (staged generic body + resolved agent-model policy composed into both L1 projections) with a policy-aware doctor render-compare, provenance-gated consumer AGENTS fan-out (banner-canonical restored vs hand-authored left [foreign]) with lexical repo-slug containment + destination-file symlink refusal, scoped AGENTS projections, source-root hygiene guard, and runtime projection contract.
tags:
- public
- assets
- distribution
- projection
- privacy
last_updated: '2026-08-18'
release_origin: v0.1.65
---

## Purpose

`dadaia public {stage|install|doctor}` distributes the public agentic surface of
`dadaia-workspace`. The 14 live asset types under `dadaia_workspace/public/` are:
`agents`, `skills`, `rules`, `workflows`, `scripts`, `schemas`, `templates`, `data`,
`scaffold`, and `runtime`
(there is no `public/commands/`
or `public/hooks/` — governance hooks are the Python package
`dadaia_workspace/hooks/`, not a projected asset type).

`public stage` copies that source into `.dadaia/agentic/<type>/` with a manifest.
`public install` projects staged assets into runtime-specific roots: `.claude/`,
`.codex/`, `.kimi-code/`, `.agents/`, workspace-root `AGENTS.md`/`CLAUDE.md`, scoped
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

**Core agents are RENDERED, not copied (v0.1.65).** The 9 core `agents/*.md` bodies are staged
generic (no `model:`/`effort:`); at install each is composed through one seam
`render(staged generic body + resolved (model, effort))` — the resolved pair comes from the
agent-model policy ([[agent-orchestration]] "Layer-1 agent model governance": 3 templates +
`.dadaia/states/agent_model_policy.json` overlay + single resolver, precedence override >
template > `balanced`). The rendered `model:` then `effort:` lines are appended as the last
frontmatter lines of `.claude/agents/<name>.md`, and the SAME resolved config feeds the codex
projection (`.codex/agents/*.toml` codex model id via the registry mapping;
`model_reasoning_effort` from the resolved effort via the D-3 clamp). Core codex render **fails
closed** when neither a staged nor a resolved model is supplied (no silent default); `--force`
re-renders to the render output (never raw staged bytes). No overlay ⇒ render `balanced`, deterministic and byte-stable across
repeated installs. The staging **manifest keeps hashing staged (policy-free) bytes** — only the
projection write/compare goes through the render seam. The new schema asset
`schemas/agent-model-policy-v1.schema.json` stages like any other asset.

**Universal skills have one canonical home and are never derived.** A universal skill is
staged from `dadaia_workspace/public/skills/<name>/SKILL.md` and installed to
`.agents/skills/<name>/` plus `.claude/skills/<name>/`; Codex and Kimi Code read it
natively from the shared `.agents/skills/` root, so no per-harness copy is produced and no
`public/entities/registry.json` entry exists for it (the registry describes derived,
per-harness entities). `dadaia-gitflow` — the single operational home of the branch,
commit, push and version contract — and `dadaia-test-stewardship` — the single operational
home of the test lifecycle — ship this way, alongside the other universal skills.

The **`dd-` lifecycle family** is distributed on that same universal path and is the
development cycle's on-demand protocol surface: `dd-backlog-definition`,
`dd-release-definition`, `dd-release-implement`, `dd-release-closure`, `dd-audit-project`,
`dd-bug-registration` and `dd-bug-fix` — one skill per stage, each the single operational
home of its stage's protocol. The always-on law carries the classification and points at
the stage's skill; the stage procedure exists only in the skill.

**One logic, one source: a projected script is a thin wrapper, never the implementation.**
Every file under `public/scripts/` is a CLI entry point that imports the package's own
implementation and forwards its exit code — it holds no logic of its own, so the package
and the projection cannot drift. The memory-atom lint is the worked example: the whole
check set lives in the package and is imported directly by the doctor, with **no subprocess
call to a projected script anywhere**, while the projected script survives only as a
standalone invocation surface preserving its flags and exit codes. The relationship is
asserted by a contract test, so script↔package drift is structurally impossible rather than
merely discouraged, and the shell-out's former "architectural exception" note was deleted
with the exception itself.

`dadaia public doctor` performs three comparison passes: source vs staging, staging
vs projected (one pass per runtime target). Any mismatch emits `[drift] <path>` and
returns a non-zero exit code, giving an accurate all-clear only when all three tiers
agree. The `dadaia-workspace-dev-guardrail` rule reflects this corrected workflow.
**Policy-aware for agents (v0.1.65):** the staging↔projected pass for a core
`claude:agents/*.md` label compares against `render(staged generic + resolved policy)`, not raw
staged bytes — so an operator policy Apply reads `[ok]` and a hand-edited `.claude/agents/*.md`
reads `[drift]`. The overlay is loaded once per doctor run (missing ⇒ silent `balanced`; invalid
⇒ an `[drift] agent-model-policy ERROR` line); `stage:agents/*.md` (generic↔generic) and every
non-agent label stay on the raw compare path. The render-compare guarantee is **claude-md-only**
— codex agent TOMLs are structural-checked only (`check_codex_drift`, no byte-compare); codex
model/effort correctness is asserted install-time by the lockstep integration test.
`features/public/model_resolution.py#check_model_resolution` validates the RESOLVED core roster
(registry + effort vocabulary).

`dadaia public doctor` also includes a public privacy gate. It scans source/staged
public assets with a denylist for private identifiers and reports
`[ok] public-privacy` only when the distributed surface is clean. CI treats this
as a release gate.

Install-all and doctor are **harness-profile-aware**. When
`.dadaia/states/harness_profile.json` exists (written by `dadaia init --harness <set>` —
[[workspace-init]]), `install` with no `--target` (and `--target all`) installs only the
profile's harness set (plus the shared `agents` tree); an **absent profile ⇒ all-four**
(back-compat, byte-identical to the pre-profile behaviour, golden-locked). An explicit
`--target claude|codex|kimi-code|agents` always overrides regardless of profile. `doctor` scopes
its per-runtime expectations to the profile: the inline projection comparison for `.claude/`
`settings.json`, the `.codex/` hooks/config/rules/wrappers (**including** the codex-parity
drift block `check_codex_drift` / D-CX-1..10 that would otherwise emit
`[missing] codex:agents/*.toml` for any codex-absent tree), each runtime tree per run
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

**Repo templates land at `alive()`, not at install.** `features/spec_context` copies
`public/templates/repo-AGENTS.md` to the Spec Context repo root and
`public/templates/tests-AGENTS.md` to `<repo>/tests/AGENTS.md` — the second **only** when
`<repo>/tests/` is a real directory (a symlinked `tests/` is refused, since it escapes the
repo tree) and no `tests/AGENTS.md` already exists. The copy never creates the `tests/`
directory and never overwrites an operator file; the installed bytes are identical to the
template, which ships parameterized (`<ANGLE-BRACKET>` placeholders for tier timeouts, the
LARGE cap and the wall-clock baseline) and carries no workspace-specific literal. Because
the template ships with placeholders **by design**, an *installed* `tests/AGENTS.md` still
carrying `<PLACEHOLDER>` tokens is the drift worth reporting — and `specs doctor` reports
exactly that, against the installed consumer file and never against the canonical template
([[specs-doctor]]).

**The repo-`AGENTS.md` destination refuses a symlink, at every write site.** The same
doctrine the consumer fan-out applies below now holds on the repo-template write: a
destination **file** that is a symlink — dangling included — is never written through,
neither by the copy nor by the atomic writer, and a dangling link is refused rather than
treated as "absent → create". This closes the gap between what this atom claimed and what
the seam did: the claim is now true at the seam, not only at its neighbour.

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

**The fan-out write path is contained (defense-in-depth).** A registry `repo_slug` is
never trusted verbatim: `_consumer_repos_for_root` applies **lexical slug validation** —
a slug is rejected unless it is a single, relative, non-dot path component (rejects `/`
or `\` carriers, `.`/`..`, POSIX/Windows absolute incl. drive/UNC forms; both
`PurePosixPath` and `PureWindowsPath` parts are checked, platform-independent). A
rejected slug is **non-silent** — one stderr line
`[reject] repo_slug '<slug>' (unsafe path component) — skipped` — and the derivation
stays fail-open (never raises); the validation protects both consumers of the helper
(install fan-out AND doctor). `_install_guardrail_pair` adds a **write-time containment
assert** (the lexical join's parent must be `repos/`; failure = the same `[reject]`
line, skip, never write). The validation is deliberately **lexical, not
`resolve()`-based on the consumer dir**: a symlinked `repos/<slug>` DIRECTORY is a
legitimate first-party pattern (the CI panel bootstrap does `ln -sfn "$PWD"
repos/dadaia-workspace`) and stays allowed.

**Destination-file symlinks are refused, never written through.** When a consumer
`AGENTS.md` or `CLAUDE.md` destination **file** is a symlink (`Path.is_symlink()`,
including dangling), the fan-out never writes through it — neither `shutil.copy2` nor
the atomic writer — and classifies it `[foreign] <path> — left untouched (symlink)`; the
paired file follows its sibling's fate (no orphan drop). A dangling symlink is refused
too (never treated as "absent → create"). `_doctor_consumer_pair_lines` classifies
symlinked pair files `[foreign]` (never `[ok]`/`[drift]`/`[missing]`), so `public
doctor` exits 0 and never prescribes an install that would be refused. The regular-file
provenance ladder below is unchanged.

**Doctor is provenance-aware on the PAIR.** A single consumer-classification authority
(`_doctor_consumer_pair_lines`) is the ONLY path that doctors consumer repos — `manager.doctor()`
calls it after the runtime loop and `_doctor_guardrail_pair` delegates to it (no parallel legacy
path). For a hand-authored consumer, **both** the `AGENTS.md` and the paired `CLAUDE.md` doctor
lines report `[foreign]` (never `[missing]`/`[drift]`), so `dadaia public doctor` **exits 0**
instead of perpetually red; a banner-bearing (canonical) copy keeps `[ok]`/`[drift]`/`[missing]`
on both lines. The memory/scaffold `AGENTS.md` tri-copy (`specs/AGENTS.md`,
`specs/memory/AGENTS.md`) is untouched by this fan-out.

## Runtime state touched

The `dadaia-workspace` source repo must stay free of root runtime projections
and local harness files. Generated/local artefacts such as `.dadaia/`,
`.agents/`, `.claude/`, `.codex/`, `.kimi-code/`, `CLAUDE.md`,
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
