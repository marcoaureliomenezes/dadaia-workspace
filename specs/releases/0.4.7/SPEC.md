# SPEC — Release: 0.4.7

**Status:** Approved
**Release ID:** 0.4.7
**Owner:** dd-project-manager
**Opened:** 2026-09-21
**Origin:** backlog:one-line-bootstrap,harness-lazy-and-extension,three-flows-release-model
**Consumes:** one-line-bootstrap, harness-lazy-and-extension, three-flows-release-model

---

## 1. Problem and context

Candidate 8 — "bootstrap, lazy harness, three flows" — is the fourth candidate cut by the
2026-09-18..20 grill (ADR 0019, 0020; rulings Q17, Q23, Q24, Q25, Q31, Q33, Q34, Q36). The
grill cut one candidate for bootstrap + flows + launch; the launch entries (release-please,
standalone skills, public presence) need operator acts the library cannot perform (accept ADR
0021, register marketplaces, post) and are cut into candidate 9 so this candidate stays
implementable end to end.

Measured on the candidate 7 closure:

- **Bootstrap is seven stages.** `pip install`, `dadaia init` (no positional dir, creates no
  context, clones nothing), `context create --main-repo`, `context alive`, `context bind`,
  `dadaia doctor`, `ci install-hook`. `init --harness {all|claude|codex|kimi-code}` defaults to
  `all`, so every workspace gets three harness dirs nobody asked for.
- **Harness extension is a code change.** `L1_ENTRY_HARNESSES`, `HARNESS_PROJECTION_DIRS`,
  `PROJECTION_TARGETS`/`INSTALL_TARGETS`, the Claude/Codex adapters in `projection_rules.py`
  and the hook wrappers are five places; `public install --target <name>` is the only way to
  add a harness after init. Cursor, Devin CLI and GitHub Copilot (research 2026-09-20) all read
  the root `AGENTS.md` and `.agents/skills` natively; Devin reads `.agents/agents` too; each
  has its own hook format (`.cursor/hooks.json`, `.devin/hooks.v1.json`, `.github/hooks/*.json`)
  and its own agent transcode (`.cursor/agents`, `.devin/agents`, `.github/agents/*.agent.md`).
- **The flow admits one origin.** The root map says a feature enters through the backlog or an
  operator demand recorded in the SPEC `Origin`, but no doctor rule requires `Origin`, a
  bug-composition candidate has no shape, and the memory-pass weight per flow is unwritten.

## 2. Objective

One candidate, one CLOSURE: `dadaia init <dir> [--repo <url>] --harness <name>` scaffolds a
whole workspace in one line (venv, zones, law, the chosen harness, hooks; with `--repo` the
first context is born ALIVE and bound in the same step); `dadaia harness add <name>` is the
one verb that adds a harness later (`public install --target` retires, `all` dies); the
harness registry is one record per harness (directory, agent transcode, hook derivation) and
gains `cursor`, `devin` and `copilot` as records, with contract tests proving each reads the
authored set; the three flows are law and doctor-checked (`Origin` required on every SPEC, a
bug-composition candidate shape, memory-pass weight per flow); the CLI is audited (a new verb
in, an old one out).

## 3. Scope (candidate 8)

### FR1 — One-line bootstrap

- `dadaia init <dir> --harness <name> [--repo <url>]`: `<dir>` required and validated (a
  directory name, created if absent, refused if it holds a foreign tree); provisions the venv,
  every zone the registry says `init` creates, the root map, `.agents/{skills,agents}`, the
  chosen harness's directory, hooks and git chokepoints, stages and installs the public assets;
  idempotent on re-run. With `--repo <url>`: clones into `repos/<slug>/`, creates the context
  with `--main-repo <slug>`, `alive`s it, binds the shell (`--print-env` line printed), installs
  the pre-push hook. Without: prints the two closing lines from candidate 6 plus one line that
  says where projects live and the one command that creates the first context.
- A single-repo workspace is the degenerate multi-repo case: no verb of the context lifecycle
  is visible before the second project (the closing note names only `context create`).
- `dadaia doctor` on a fresh `init <dir> --harness claude --repo <url>` exits 0.
- **AC1.1** In a clean container: `pip install <wheel> && dadaia init demo --harness claude
  --repo <public url>` then `cd demo && dadaia doctor` exit 0 and `dadaia context show --json`
  shows the repo as `main_repo` ALIVE — `tests/e2e/test_one_line_bootstrap.py`.

### FR2 — Lazy harness and `harness add`

- `init --harness <name>` is required (no default, no `all`); `dadaia harness add <name>`
  replaces `public install --target <name>` (one verb in, one out; `public install` keeps only
  the shared authored set + the harnesses already registered in
  `.dadaia/states/harness_profile.json`); `harness add` stages if needed, installs that
  harness's set, records it in the profile; `harness list` shows the registered ones.
- `core/harness_registry.py`: one record per harness — `directory`, `agent_transcode`
  (`none | claude-md-symlink | codex-toml | cursor-md | devin-md | copilot-agent-md`),
  `hooks` (`none | claude-settings | codex-hooks | kimi-hooks | cursor-hooks | devin-hooks | copilot-hooks`; `kimi-hooks` = the user-level shims and the managed `config.toml` block);
  `HARNESS_PROJECTION_DIRS`, `PROJECTION_TARGETS`, `INSTALL_TARGETS` and the adapters derive
  from it; `ProjectionRule` tables come from the record, never from a per-harness `if`.
- **AC2.1** `dadaia init demo` without `--harness` exits 2 with one `fix:` line; `dadaia
  public install --target` is gone from `--help`; `dadaia harness add codex` on a Claude-only
  workspace yields the `.codex/` set and `public doctor` exit 0.

### FR3 — Cursor, Devin CLI, GitHub Copilot

- Three registry records: `cursor` (`.cursor/`, agents `.cursor/agents/*.md`, hooks
  `.cursor/hooks.json`), `devin` (`.devin/`, agents native `.agents/agents`, hooks
  `.devin/hooks.v1.json`), `copilot` (`.github/`, agents `.github/agents/*.agent.md`, hooks
  `.github/hooks/*.json`). Each reads the root `AGENTS.md` and `.agents/skills` natively (CONTEXT-
  MAP §1 rows); the hook derivation implements the four deterministic behaviours (root
  whitelist, venv guard, SDD gate, session-start reaper) in that harness's format — a hook
  exists only as the per-harness implementation of a behaviour the workspace defines.
- `public doctor` validates each record's projection; `dadaia certify` gains a
  `<harness>-live-probe` that is UNVERIFIED when the binary is absent (no version floor).
- **AC3.1** `dadaia harness add cursor|devin|copilot` on the live instance each exit 0 with
  `public doctor` exit 0; `tests/contract/test_harness_registry_records.py` proves every record
  has a directory, an agent transcode and a hook derivation, and that the projection table has
  no harness-named branch.

### FR4 — Three flows as law and doctor rule

- `SPEC-DOC-048`: every live SPEC carries `**Origin:** operator-demand | backlog:<slug>[,..] |
  bugs:<id>[,..]`; `backlog:` slugs must exist in `BACKLOG.json` or the histo; `bugs:` ids must
  be open records.
- Flow 2 shape: `release.py new <id> --origin bugs:<id>,...` seeds the SPEC with one FR per
  bug (title + repro line); the memory pass is "surgical or none"; a single bug stays Arm B.
- Flow weights written once in `specs/releases/AGENTS.md` (Flow 1 default, Flow 2 surgical
  memory, Flow 3 heaviest); `dd-release-definition` step 1 names the origin.
- **AC4.1** A SPEC without `Origin` is a doctor error with a `fix:` naming the line; this
  repo's live and rc-N SPECs pass.

### FR5 — CLI audit and closure

- Verb audit: every verb in `dadaia help tree` is cited by a skill, agent or the map, or dies;
  `init`, `harness`, `context`, `public`, `ci`, `doctor`, `reports`, `certify`, `export`,
  `import`, `reconcile`, `migrate`, `capabilities`, `help`, `specs` remain; count ≤ 30.
- Memory pass (`workspace-init`, `harness-*` incl. three new atoms, `context-management`,
  `sdd-bug-backlog-governance`, `agentic-entities`, `public-asset-distribution`), CHANGELOG
  "Candidate 8", `_RELEASE.json` log, live instance reflected, dd-code-review, PR #260 updated.
- **AC5.1** Every CI job green; review APPROVED; `dadaia doctor` exit 0 on the live instance;
  the `_orphan_claude_bridge` migration branch (candidate 6 review F4) is deleted here.

## 4. Out of scope

- release-please, standalone skills repo and marketplaces, docs site/video/Show HN — candidate 9
  (operator acts: accept ADR 0021, register marketplaces, publish).
- Hook multi-harness study beyond the four behaviours each new harness implements.

## 5. Decisions and constraints

- ADR 0019 (flows) and ADR 0020 (lazy harness, roster extension) accepted 2026-09-20.
- D1 (operator): `CLAUDE_API_KEY` + required check — PR #260 stays red on it.
- D2 (operator, candidate 9): accept ADR 0021 (supersedes 0005/0006/0008/0009/0014).

## 6. Traceability

| Requirement | Tasks |
|---|---|
| FR1 | T-047-71, T-047-72 |
| FR2 | T-047-73, T-047-74 |
| FR3 | T-047-75, T-047-76 |
| FR4 | T-047-77 |
| FR5 | T-047-78, T-047-79 |
