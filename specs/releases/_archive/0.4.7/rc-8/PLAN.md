# PLAN — Release: 0.4.7

**Status:** Approved
**Release ID:** 0.4.7
**Owner:** dd-software-engineer

---

## Design (codebase-design vocabulary)

Three facts about a harness live in five places today: `core/harness_registry.py`
(`L1_ENTRY_HARNESSES`, `HARNESS_PROJECTION_DIRS`, `PROJECTION_TARGETS`, `INSTALL_TARGETS`,
`parse_harness_set`), the adapters in `infrastructure/projection_rules.py` (`ClaudeHarness`,
`CodexHarness`, `KimiHarness` and their `_claude_agent_rules` / `_codex_agent_rules` /
`_codex_hook_wrapper_rules` builders, 650 LOC), `runtime_config.py` + `runtime_transforms/`
(settings, TOML transcode, hooks.json), `cli/commands/public.py`'s `--target` vocabulary, and
`json_harness_profile_store.py`. Adding a harness edits five modules; `projection_rules`
already carries a harness-named branch (`if {"agents","codex","claude"} & set(...)`). The
interface is wide and the implementation is thin: negative depth.

- **One record per harness is the deep module.** `HarnessRecord(name, directory,
  agent_transcode, hooks)` — three fields, a closed vocabulary per field. `HARNESS_PROJECTION_DIRS`,
  `PROJECTION_TARGETS`, `INSTALL_TARGETS` and `parse_harness_set` become derivations of the
  record table, not parallel literals. The transcode and hook derivations become table-driven
  builders keyed by the record's enum value, so `cursor`, `devin` and `copilot` are three data
  rows, not three adapter classes.
- **Seam placement.** The harness seam moves from *a class per harness* to *the record's
  `agent_transcode`/`hooks` values*. `_claude_agent_rules` becomes the `claude-md-symlink`
  builder, `_codex_agent_rules` the `codex-toml` builder; the new rows reuse
  `cursor-md`/`devin-md`/`copilot-agent-md` over the same `_agents_agent_rules` authored set and
  the same `_link_rule` kind. Two adapters already exist for that kind — a real seam, not
  indirection.
- **Hook doctrine: no rule, no hook.** The workspace defines exactly four deterministic
  behaviours — root whitelist, venv guard, SDD gate (all three via `hooks/pre_gate.py`) and the
  session-start reaper (`doctor --fix --expired-only`). A harness's `hooks` value names the
  *format* the same four behaviours serialize into: `.cursor/hooks.json`, `.devin/hooks.v1.json`,
  `.github/hooks/pre-tool-use.json` + `.github/hooks/session-start.json`. No fifth behaviour is
  invented for a new harness, and a harness gets no hook file the four do not fill.
- **Deletion test.** Delete the three harness classes: complexity does not reappear at N
  callers — `projection_rules()` iterates records. Delete `public install --target`: it
  reappears once, as `harness add`, strictly smaller (one name, no `all`). Delete
  `_orphan_claude_bridge` (`spec_context/doctor.py:380`): a one-release migration for a stub no
  live generator writes.
- **Replace, don't layer.** No `--target` alias, no deprecated `all`, no "legacy default"
  branch in `init`. `init.py` gains `<dir>` and `--repo`, composing the *existing*
  `context create --main-repo` / `alive` / `bind` implementations — it calls them, never
  re-implements them.
- **Origin is one rule, not a flow engine.** `SPEC-DOC-048` in `features/specs/rules.py` +
  `doctor_release.py` parses the SPEC header the same way `_extract_status` does; the flows are
  prose in `specs/releases/AGENTS.md` and one step in `dd-release-definition`. No per-flow code
  path: `--origin` only selects which stub text `_release_new.py` writes.

## Order of work (tracer bullets)

Each task leaves `dadaia ci preflight` green and the live instance re-projectable.

1. **T-047-71 (FR2 registry)** — the tracer: `HarnessRecord` + the record table for the three
   existing harnesses, every legacy constant derived from it. No behaviour change, byte-identical
   projections. This is the shape everything else plugs into.
2. **T-047-72 (FR2 verbs)** — `harness add` / `harness list` in, `public install --target` out,
   `harness_profile.json` as the one roster of record.
3. **T-047-73 (FR1 init)** — `init <dir> --harness <name>` required; `--harness all` dies.
4. **T-047-74 (FR1 repo)** — `--repo <url>` composes clone + context create + alive + bind;
   closing notes rewritten.
5. **T-047-75 (FR3 records)** — the three new rows and their agent transcodes.
6. **T-047-76 (FR3 hooks + probes)** — the four behaviours in three formats, `<harness>-live-probe`.
7. **T-047-77 (FR4)** — `SPEC-DOC-048`, `--origin`, flow weights in law.
8. **T-047-78 (FR5)** — CLI verb audit, `docs/cli.md`, the `registry.py` split (candidate 7
   review F5), `_orphan_claude_bridge` deletion.
9. **T-047-79 (FR5)** — AC1.1 e2e, CHANGELOG, `_RELEASE.json` log, live instance, closure.

## Verification

- `dadaia ci preflight` (`ruff format --check`, `ruff check`, `mypy --strict`, `pytest`) green
  before every push; every CI job watched to green (AC5.1).
- Per-AC: AC1.1 `tests/e2e/test_one_line_bootstrap.py`; AC2.1 integration over `harness add` +
  `public doctor`; AC3.1 `tests/contract/test_harness_registry_records.py` (three fields per
  record; no harness-name literal outside the table) + a projection golden per new harness;
  AC4.1 unit tests over `SPEC-DOC-048` plus this repo's own `specs/`; AC5.1 `dadaia doctor` and
  `public doctor` exit 0 on the live instance.
- Byte-golden guard for T-047-71: the rule table rendered before and after the refactor must be
  identical for `claude`, `codex`, `kimi-code` — the refactor is proven by equality, not by
  re-asserting the expected files.

## Risks

**Bug history (standing rule).** `grep`ping `BUGS.jsonl` for `init|install|harness|projection|
profile|origin|alive|bind` returns **94 records** — the largest family in the ledger. The
`public-install` / `init` / `alive` ones name the structure: *public install overwrites a
consumer repo's hand-authored AGENTS.md*; *public install restores zone AGENTS.md with old
mtimes, re-blocking preflight*; *public install skips self-projection so the library repo's
AGENTS.md drifts*; *per-harness install skipped chokepoint scripts, leaving kimi-only workspaces
without managed scripts*; *re-running init with a harness subset silently orphans existing
projections*; *init --harness claude --skip-assets writes a settings.json with no PreToolUse
hook*; *init creates a bare venv, dadaia_workspace never installed*; *context alive commits
unrelated worktree changes*; *context alive copies the scaffold image wholesale*;
*install-target doctor goldens stale after skill additions*. Every one is a per-harness or
per-target *branch* disagreeing with another branch: the profile says one thing, the target
vocabulary another, the adapter a third. One record per harness with no per-harness `if` removes
the disagreement by construction — one place to be wrong, and the AC3.1 contract test fails when
a branch reappears. The candidate must end with a **smaller** `projection_rules.py`; if it grows,
the record table was not the fix.
- **Hook doctrine.** Three new harnesses must implement exactly the four behaviours, no more:
  `cursor` -> `.cursor/hooks.json`; `devin` -> `.devin/hooks.v1.json`; `copilot` ->
  `.github/hooks/pre-tool-use.json` + `.github/hooks/session-start.json`. A format that cannot
  express one of the four is recorded as an UNVERIFIED probe, never faked with a fifth hook.
- **Codex hooks never fire headless** — a `<harness>-live-probe` proves the binary answers, not
  that the hook ran; the probe is UNVERIFIED when the binary is absent, with no version floor.
- **Windows symlink fallback** — the new agent transcodes reuse `_link_rule`'s hash-verified
  copy fallback; no new symlink kind, no platform branch.
- **AC1.1 must not hit the network** — the e2e builds a local **bare git repo** in `tmp_path`
  and passes its path as `--repo`, installing the package source (not a PyPI fetch) into a tmp
  venv. No container, no remote; LARGE tier, one test, justified inline.
- **Ratchets that could rise** — V32 (governance ids in production comments, ceiling 686): new
  docstrings carry no `T-`/`FR`/ADR id. V35 (skill corpus, 18 dirs / 2,880 lines): FR4's flow
  weights go in `specs/releases/AGENTS.md`, and `dd-release-definition` gains one line, not a
  section. Module ceilings: `init.py` (100) and `projection_rules.py` (650) must be split by
  responsibility — record table, rule builders, harness verbs — never grown past their ceilings.
- **Pinned surfaces** — `docs/cli.md` and `tests/contract/test_cli_help_quality.py` pin the verb
  count (35 today, ceiling 30 after the audit); `harness_profile.json` schema v1 gains no field
  without a migration step in T-047-72 (the store is the one writer).
- **Candidate 7 review F5** — the `scripts/registry.py` split folds into T-047-78's CLI audit so
  one task owns every script/verb boundary change.
