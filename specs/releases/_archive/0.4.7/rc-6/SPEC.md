# SPEC — Release: 0.4.7

**Status:** Approved
**Release ID:** 0.4.7
**Owner:** project-manager
**Opened:** 2026-09-20
**Origin:** backlog:universal-context-core,projection-collapse-native-agents-md,english-only-surface,spec-context-foundation-hardening
**Consumes:** universal-context-core, projection-collapse-native-agents-md, english-only-surface, spec-context-foundation-hardening

---

## 1. Problem and context

Candidate 6 — "universal context core" — is the second of the four candidates cut by the
2026-09-18..20 grill (ADR 0017, 0020; rulings Q11, Q12, Q16, Q20–Q22, Q28–Q30, Q35). Candidate
5 (`rc-5/`) deleted the dead surfaces; this candidate rewrites how the surviving law reaches an
agent, in every harness, with one authored set. Operator order 2026-09-20: every backlog entry
becomes a candidate and is implemented on `feature/0.4.7`; the operator verifies at the end.

Measured on `rc-5` closure (37c6c6ac):

- **The law is an encyclopedia; the scoped files are orphans.** `public/data/DADAIA.md` is
  25.5 KB, always-on for every session, reached through `CLAUDE.md -> @AGENTS.md -> @DADAIA.md`
  and mirrored into `.codex/` and `.kimi-code/`. The 15 scoped `AGENTS.md` sources (36.6 KB,
  1.0–5.1 KB each) are opened by three skills only. Codex's 32 KiB cap is a live constraint.
- **Claude Code reads `AGENTS.md` natively** (2.1.277+, probe ZEBRA 2026-09-20) if and only if no
  `CLAUDE.md` sits on the path; a nested `AGENTS.md` attaches when a file in that directory is
  Read (probe KOALA). Codex 0.145 and Kimi 0.35 load the root->cwd chain. Per-entry symlinks
  `.claude/skills/<n>` and `.claude/agents/<n>.md` load (probes PANDA, FALCON). A `CLAUDE.md`
  inside `repos/<slug>/` suppresses the workspace `AGENTS.md` for a session started there.
- **Three law basenames, four harness dirs.** `LAW_BASENAMES = {DADAIA.md, AGENTS.md, CLAUDE.md}`,
  `LAW_HARNESS_DIRS = {.claude/rules, .codex, .kimi-code, .agents}`, `_law_projection_rules`,
  `DADAIA_MD_HARNESS_TARGETS`, `_guardrail_pair_rules` (root `CLAUDE.md` stub), the consumer
  `CLAUDE.md` decider in `workspace_guardrail.py`, `public/kimi-code/AGENTS.md`, `.codex/skills`
  copies, `.claude/skills` and `.claude/agents` copies: 26 lib modules and 36 tests cite
  `DADAIA.md`; 15 modules cite `kimi`.
- **Portuguese control vocabulary inside English law and code.** `core/spec_status.py`
  (`Aprovado`, `Em revisão`), the SPEC-DOC rules, 26 files, the memory scaffold
  (`TECHSTACK/QUALITY/ARCHITECTURE.md`, `product/index.md` "Catálogo de features"), the consumer
  recipe verdicts (`APROVADA/BLOQUEADA`), `specs-AGENTS.md`.
- **Vocabulary the paradigm never named.** `repo_slug`/`associated_repos` in 16 modules, the
  `context` CLI (`--repo`, `--associated`), `context show --json` keys, memory and glossary; no
  sentence anywhere says "the main repo is the repo where `specs/` lives". The spec-context
  surface carries 160 of 514 bug records; no audit names its structural weak points.

## 2. Objective

One candidate, one CLOSURE: the workspace ships exactly two rule-file kinds — the root
`AGENTS.md` map (<= 8 KB) and scoped `AGENTS.md` per governed area (<= 4 KB) — plus
`.agents/skills/dd-*` and `.agents/agents/dd-*` as the single authored source; Claude Code reads
them through native `AGENTS.md` loading and per-entry symlinks; Codex and Kimi read them
natively; no `CLAUDE.md`, no `DADAIA.md`, no `.kimi-code/`, no mirror; every public surface is
English; the context vocabulary is main-repo/associated-repos; the paradigm is written down and
the spec-context surface is frozen after a bug-history audit. `public/data/CONTEXT-MAP.md` is the
auditable balance and its ceilings are ratchets.

## 3. Scope (candidate 6)

### FR1 — The root map and the scoped system of record

- `public/data/AGENTS.md` is rewritten as the map: the flow (§1), the three roles (§2), the gate
  invariants (three blocks, path classes, `fix:` line — §3.1/3.2 only), where things are written
  (§5.1 root whitelist, §5.2 paths), the credential boundary (§9), the law sentence *sessions
  launch at the workspace root*, and an index of every scoped `AGENTS.md` and every dd- skill
  with one line each. Statements, no prose; <= 8 KB; the header says it is projected.
- Every other `DADAIA.md` section migrates to the scoped file that governs it, deduplicated
  against what that file already states (a rule lives in one home): §3.3–3.5 and §8.1, §8.2,
  §8.5 -> `.dadaia/AGENTS.md`; §4 -> `dd-gitflow-default`; §5.3–5.4 -> `.dadaia/handoff/AGENTS.md`
  and `repo-AGENTS.md`; §6.1–6.2 -> `specs/AGENTS.md`; §6.3, §6.7 -> `releases/AGENTS.md`;
  §6.4 -> `memory/AGENTS.md`; §6.5 -> `ADRs/AGENTS.md`; §6.6 -> `backlog/AGENTS.md`;
  §6.8 -> `audits/AGENTS.md`; §7.1, §7.5, §7.6 -> `dd-code-review` (SLOP.md for 7.6);
  §7.2 -> `dd-test-stewardship`; §7.3 -> `bugs/AGENTS.md`; §7.4 -> `dd-release-implementation`;
  §8.3 -> `repo-AGENTS.md`; §8.4 -> `dd-cli-library`; §10.2 glossary, trimmed to the terms the
  map uses -> `dd-spec-navigator`. What fits nowhere dies as slop.
- Every scoped `AGENTS.md` source is <= 4 KB after the migration (`memory/AGENTS.md` is 5.1 KB
  today and must shrink); every `SKILL.md` <= 6 KB.
- `public/data/DADAIA.md` is deleted; `public/entities/behavior-map.json` rows are re-keyed to
  the map's sections and the scoped files, hash tuples re-recorded; `shipped-hashes.json`
  records the new scaffold law hashes; derived-doc markers re-recorded.
- **AC1.1** `wc -c` of the installed root `AGENTS.md` <= 8192; of every scaffolded scoped
  `AGENTS.md` <= 4096; of every `SKILL.md` <= 6144 — pinned by `tests/contract/test_context_map.py`.
- **AC1.2** No sentence of `DADAIA.md` survives in two homes: a contract test asserts no line of
  the deleted file (normalised) appears in more than one shipped rule file or skill.

### FR2 — Skills open their scoped law; CONTEXT-MAP and the ratchets

- Every dd- skill whose behaviour touches a governed area opens that area's scoped `AGENTS.md`
  as **step 1** of its procedure (`dd-backlog-definition` -> `backlog/AGENTS.md`,
  `dd-bug-registration`/`dd-bug-resolution` -> `bugs/AGENTS.md`, `dd-release-definition`/
  `dd-release-implementation` -> `releases/AGENTS.md`, `dd-audit-project` -> `audits/AGENTS.md`,
  `dd-handoff-emitter` -> `.dadaia/handoff/AGENTS.md`, `dd-spec-navigator` -> `specs/AGENTS.md`,
  `dd-code-review` -> `memory/AGENTS.md`, `dd-cli-library` -> `.dadaia/AGENTS.md`); the step
  names the path relative to the workspace root so it works from any harness with any config
  (Claude attaches it on Read; Codex and Kimi read it on the skill's instruction).
- `public/data/CONTEXT-MAP.md` (new, projected nowhere — a library document): one row per
  surface (root map, each scoped file, each skill, each persona): purpose, what belongs there,
  byte ceiling, measured bytes at closure, per-harness load trigger; plus the 10-harness
  compatibility table from the 2026-09-20 research (root `AGENTS.md`, nested trigger,
  `.agents/skills`, `.agents/agents`, own dirs).
- `tests/contract/test_context_map.py`: every scaffolded scoped `AGENTS.md` is cited by the map
  or by at least one skill's step 1; every dd- skill's step 1 names an existing scoped file when
  it claims one; the ceilings of AC1.1 hold; every CONTEXT-MAP row names an existing surface and
  every surface has a row.
- **AC2.1** The contract test is green on the library and on the live instance after install.
- **AC2.2** Headless probe on the live instance, Claude Code: a session at the workspace root
  reports a token written only in the root map; a session that Reads `specs/bugs/BUGS.jsonl`
  reports a token written only in `specs/bugs/AGENTS.md`. Codex: same two tokens with
  cwd = root and cwd = `specs/bugs`. Kimi: deferred (no provider on this machine); the CONTEXT-MAP
  row cites the source-verified chain. Probe scripts under `tests/tmp/` (gitignored), results in
  the closure log.

### FR3 — One authored set, projected by symlink

- `LAW_BASENAMES = {AGENTS.md}`; `DADAIA_MD_HARNESS_TARGETS`, `LAW_HARNESS_DIRS`,
  `_law_projection_rules`, `_guardrail_pair_rules`' `CLAUDE.md` half, the consumer `CLAUDE.md`
  decider and stub, `public/kimi-code/`, the `.codex/skills` copy rules and the `.codex/DADAIA.md`
  mirror are deleted. PROTECTED law rows = the projected `AGENTS.md` set (root and `.dadaia/**`);
  the gate still blocks exactly three things.
- `HARNESS_DIRS` = `.agents .claude .codex`; `kimi-code` stays in `L1_ENTRY_HARNESSES` with an
  empty own-projection set (it reads `.agents/*` natively; its hooks are user-level). Root
  whitelist = `.agents/ .claude/ .codex/ .dadaia/ .git/ repos/ .env .gitignore AGENTS.md
  prompt.md`; `CLAUDE.md`, `DADAIA.md`, `.kimi-code/` at the root are slop the doctor reaps
  (`WS-root-slop`), so `dadaia doctor --fix` migrates a live instance.
- `.agents/agents/dd-<persona>.md` is the rendered persona (model, effort, permission fields
  appended by the one render seam); `.claude/agents/dd-<persona>.md` and
  `.claude/skills/dd-<skill>` are per-entry symlinks to them (relative targets); when
  `os.symlink` raises, the entry is a copy verified by hash. `.codex/agents/*.toml` stays a
  transcode of `.agents/agents/`. Personas are renamed `dd-project-manager`,
  `dd-software-engineer`, `dd-code-reviewer` (`CORE_AGENTS`, registry, behavior map, grants,
  subagent names in skills).
- `public doctor`: the per-harness byte-drift classes die with the collapsed files; a
  symlink-target check (`SYMLINK-TARGET-1`: entry is a symlink whose resolved target is the
  canonical `.agents/*` path, or a hash-equal copy) replaces them for `.claude/`;
  `public-privacy`, `entities-derivation`, `rule-corpus`, `trust-boundary` stay.
- `dadaia init` prints, once, the recommendation to set `instructionFiles:
  claude-md-and-agents-md` in the Claude user settings, and the law sentence that sessions
  launch at the workspace root. No harness version floor anywhere (Q35).
- **AC3.1** After `public stage -> public install --target all -> public doctor` on the live
  instance: no `CLAUDE.md`, `DADAIA.md`, `.kimi-code/`, `.codex/DADAIA.md`, `.codex/skills/`;
  `.claude/skills/*` and `.claude/agents/*` are symlinks into `.agents/`; `dadaia doctor` exit 0.
- **AC3.2** `tests/contract/test_claude_scaffold_is_loadable.py` proves the symlinked entries
  carry valid frontmatter at the resolved path; a unit test proves the copy fallback when
  `os.symlink` raises.

### FR4 — 100 % English surface

- Canonical status tokens become `Approved`, `In review`, `Draft` (`core/spec_status.py`); the
  SPEC-DOC rules accept only the English tokens; `dadaia specs upgrade` rewrites the Portuguese
  tokens in every SPEC/PLAN/TASKS under `releases/<live>/**` (root and `rc-N/`) in its
  unconditional repair lane; `releases/_archive/**` is published history and is never rewritten;
  the doctor validates archived trees against the token set of their stamp.
- Memory scaffold (`TECHSTACK.md`, `QUALITY.md`, `ARCHITECTURE.md`, `product/index.md`),
  `specs-AGENTS.md`, the consumer validation recipe (verdicts `APPROVED`, `BLOCKED`,
  `APPROVED WITH EXPLICIT EXCEPTION`), the CHANGELOG preamble, docstrings and test names that
  carry Portuguese control vocabulary become English. The operator's private rules and memory
  are untouched.
- `public doctor` `public-privacy` gains a language check: the control tokens `Aprovado`,
  `Em revisão`, `Rascunho`, `Catálogo`, `APROVADA`, `BLOQUEADA`, `em progresso` never appear
  under `dadaia_workspace/public/`.
- **AC4.1** `grep -rE 'Aprovado|Em revis|Rascunho|Catálogo|APROVADA|BLOQUEADA' dadaia_workspace
  docs README.md CHANGELOG.md` returns nothing except the `specs upgrade` rewrite table and its
  tests; this repo's `specs/releases/0.4.7/**` reads `Approved` after `dadaia specs upgrade`.

### FR5 — main-repo / associated-repos (user-facing)

- The paradigm names its parts: **main repo** — the repo where `specs/` lives; **associated
  repos** — the other repos the context owns. `dadaia context create --main-repo <slug>
  [--associated-repos a,b]`; `context show --json` keys `main_repo`, `associated_repos`; the
  map, the scoped files, the skills, `docs/`, memory atoms and the glossary use the two terms;
  `repo slug` survives only as "the directory name under `repos/`".
- Python identifiers and the state-file schema stay as they are (Q16 A: user-facing only);
  `docs/cli.md` regenerated.
- **AC5.1** `dadaia context create --help` shows `--main-repo`/`--associated-repos` and no
  `--repo`/`--associated`; `context show --json` on the live instance carries `main_repo`.

### FR6 — Spec-context foundation: audit, freeze, paradigm

- Bug-history audit of the spec_context surface (`specs/bugs/BUGS.jsonl` records whose surface
  or title names context, bind, session or presence; `_archive/` closures): weak points,
  repeated symptoms, which fixes were symptom patches, structural fixes still owed — written as
  the *Bug history* section of `specs/memory/product/context/context-management.md` (or the atom
  that owns the surface); no code change in this candidate follows from it unless it is a
  confirmed bug (Arm B).
- Freeze statement in that atom and in `.dadaia/AGENTS.md`: no new context verb, no new
  state file, no new session field; a single-repo context is the degenerate case of multi-repo.
- The founding paradigm becomes the first statement of `specs/memory/product/product-vision.md`
  and the opening of `README.md`: one workspace folder, an agent opened there, projects in repos
  inside it, governance (`AGENTS.md`, skills, `.dadaia/`) outside every repo, multi-project ×
  multi-repo, never a monorepo, the main repo hosts `specs/`.
- **AC6.1** The three texts exist, cite the same terms as FR5, and the audit section lists every
  spec-context bug id it judged.

### FR7 — Closure

- Ratchets: V35 (skill corpus) holds its ceiling by deleting the skill prose the migrated
  statements replace; new ratchets root/scoped/SKILL.md bytes (AC1.1); V26/V32/V33 re-pinned
  downward where the deletions allow; `import-linter` pins re-measured.
- CHANGELOG "Candidate 6 — universal context core"; memory pass (atoms `harness-claude-code`,
  `harness-codex`, `harness-kimi-code`, `public-asset-distribution`, `context-management`,
  `product-vision`, `agentic-entities`, ARCHITECTURE/TECHSTACK/QUALITY Part 2; `brand-identity`
  moves out of `product/panel/`); `_RELEASE.json` log; live instance reflected (AC3.1); push;
  dd-code-review three axes + six lenses; PR #260 updated.
- **AC7.1** Every CI job green on the push; the review verdict APPROVED; `dadaia doctor` exit 0
  on the live instance; AC2.2 probe results recorded.

## 4. Out of scope

- Any new harness (Cursor, Devin CLI, GitHub Copilot) — candidate 8 (ADR 0020).
- Ledger verbs to skill scripts — candidate 7.
- Hooks beyond re-pointing existing wiring at the surviving files (hook doctrine: a hook exists
  only as the per-harness implementation of a deterministic behaviour; study deferred).
- Renaming Python identifiers or the context state schema.
- Rewriting `releases/_archive/**` or `_histo.jsonl` content.

## 5. Decisions and constraints

- ADR 0017 (accepted 2026-09-20) governs FR1–FR3; ADR 0020 governs the harness registry shape.
- **D1 (operator):** `CLAUDE_API_KEY` secret and the required `security-review` check — still
  open; PR #260 stays red on that check until then.
- **D2 (operator, on the user settings):** set `instructionFiles: claude-md-and-agents-md` in
  `~/.claude/settings.json` so a stray `CLAUDE.md` in a repo never hides the workspace map; the
  library prints the recommendation, never writes user settings.
- Tests for deletions live in `tests/tmp/` (gitignored); the committed proof is the ratchet and
  the contract tests named per task.

## 6. Traceability

| Requirement | Tasks |
|---|---|
| FR1 | T-047-51, T-047-52 |
| FR2 | T-047-53, T-047-54 |
| FR3 | T-047-55, T-047-56, T-047-57 |
| FR4 | T-047-58 |
| FR5 | T-047-59 |
| FR6 | T-047-60 |
| FR7 | T-047-61, T-047-62 |
