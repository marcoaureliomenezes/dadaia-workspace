# TASKS — Release: 0.4.7

**Status:** Approved
**Release ID:** 0.4.7
**Owner:** software-engineer

---

## Candidate 6 — universal context core

- [x] T-047-58 — FR4: English control vocabulary. `core/spec_status.py` tokens become
  `Approved` / `In review` / `Draft` (`APPROVED_LINE`, `_TOKEN_SPELLINGS`, `CANONICAL_STATUS`
  — one authority, no compatibility branch); SPEC-DOC rules and `doctor_release` accept only
  them; the unconditional repair lane in `features/migrate/upgrade.py` rewrites the
  Portuguese tokens under `releases/<live>/**` (root + `rc-N/`), never under
  `releases/_archive/**`; archived trees validate against their stamp. Memory scaffold,
  `specs-AGENTS.md`, the recipe verdicts, CHANGELOG preamble, docstrings and test names go
  English; `public-privacy` gains the language check (AC4.1 term list).
  Seam: the status vocabulary's single definition. RED: a unit test over `extract_status`
  rejecting `Aprovado`, plus a `test_public_source_hygiene.py` case for the language check.
  Write set: `core/spec_status.py`, `features/specs/{rules,candidate,doctor_release}.py`,
  `features/migrate/upgrade.py`, `core/specs_repair.py`,
  `infrastructure/privacy_check.py`, `public/scaffold/**`, `public/templates/*-AGENTS.md`,
  `public/data/CONSUMER_VALIDATION_RECIPE.md`, `CHANGELOG.md`, `docs/**`, `tests/**`.

- [x] T-047-59 — FR5: main-repo / associated-repos, user-facing only. `dadaia context create
  --main-repo <slug> [--associated-repos a,b]` replaces `--repo`/`--associated` (no alias);
  `context show --json` emits `main_repo` / `associated_repos`; help text, `docs/cli.md`
  (regenerated), the scoped files, skills and glossary use the two terms, `repo slug` only as
  "the directory name under `repos/`". Python identifiers and the state schema are untouched
  (Q16 A). Seam: the CLI option surface over an unchanged service. RED:
  `tests/contract/cli` case asserting `--main-repo` present and `--repo` absent in
  `create --help`, and `main_repo` in `show --json`.
  Write set: `cli/commands/context.py`, `cli/redact.py`, `docs/cli.md`,
  `public/skills/dd-cli-library/**`, `public/data/*AGENTS.md`, `tests/**`.

- [x] T-047-51 — FR1a: the migration. Rewrite `public/data/AGENTS.md` as the map (<= 8192 B):
  flow, three roles, gate invariants (§3.1/3.2 only), root whitelist + output paths,
  credential boundary, the *sessions launch at the workspace root* sentence, and a one-line
  index of every scoped `AGENTS.md` and dd- skill. Move every other section into its owning
  file per SPEC §3 FR1, deduplicating against what that file already says; `memory/AGENTS.md`
  (5120 B today) and the four skills receiving §4/§7/§8.4/§10.2 shrink to fit their ceilings.
  What fits nowhere dies as slop. `DADAIA.md` still exists and still projects — preflight
  stays green. Seam: which file is the home of a statement. RED: the AC1.1 byte assertions
  (temporarily in `tests/tmp/`) plus the AC1.2 no-line-in-two-homes check.
  Write set: `public/data/AGENTS.md`, `public/data/{dadaia,handoff,states,tmp}-AGENTS.md`,
  `public/scaffold/**/AGENTS.md`, `public/templates/{specs,repo,tests}-AGENTS.md`,
  `public/skills/**`, `public/data/fixed/*.md`.

- [x] T-047-52 — FR1b: delete `public/data/DADAIA.md` and every reference to it — the
  `manifest.json` asset row, `infrastructure/{projection_rules,codex_doctor,public_assets}.py`
  citations, `tests/AGENTS.md`, and the 37 test files that cite its bytes or path (including
  `test_agents_banner_constant_matches_public_data.py`, `test_fixed_sections_canon.py`,
  `test_claude_code_law_single_load.py`, `_golden/doctor_golden_v0155.json`). Re-key `public/entities/behavior-map.json` rows from
  `§N` section titles to the map's sections and the scoped files, re-record every
  `hash_tuple`; refresh `public/templates/shipped-hashes.json` and the derived-doc markers.
  Depends on T-047-51. Seam: the entities-derivation contract. RED:
  `test_behavior_map.py` + `test_agentic_entities_derivation.py` green with the new keys;
  a repo-wide grep for `DADAIA.md` returns only release history.
  Write set: `public/data/DADAIA.md` (deleted), `public/entities/behavior-map.json`,
  `public/templates/shipped-hashes.json`, `infrastructure/**`, `core/workspace_layout.py`
  (citation comments only), `tests/**`.

- [x] T-047-53 — FR2a: every dd- skill whose behaviour touches a governed area opens that
  area's scoped `AGENTS.md` as **step 1**, naming the path relative to the workspace root
  (`dd-backlog-definition` -> `specs/backlog/AGENTS.md`, `dd-bug-registration` and
  `dd-bug-resolution` -> `specs/bugs/AGENTS.md`, `dd-release-definition` and
  `dd-release-implementation` -> `specs/releases/AGENTS.md`, `dd-audit-project` ->
  `specs/audits/AGENTS.md`, `dd-handoff-emitter` -> `.dadaia/handoff/AGENTS.md`,
  `dd-spec-navigator` -> `specs/AGENTS.md`, `dd-code-review` -> `specs/memory/AGENTS.md`,
  `dd-cli-library` -> `.dadaia/AGENTS.md`). Every `SKILL.md` <= 6144 B. Depends on
  T-047-51. Seam: the skill procedure's first step. RED: the step-1 half of
  `test_context_map.py`, landed here as a failing assertion over the skill corpus.
  Write set: `public/skills/*/SKILL.md`, `public/entities/behavior-map.json`, `tests/**`.

- [ ] T-047-54 — FR2b: `public/data/CONTEXT-MAP.md` (a library document, projected nowhere) —
  one row per surface (root map, each scoped `AGENTS.md`, each skill, each persona): purpose,
  what belongs there, byte ceiling, measured bytes at closure, per-harness load trigger; plus
  the 10-harness compatibility table from the 2026-09-20 research. New
  `tests/contract/test_context_map.py`: the AC1.1 ceilings (8192 / 4096 / 6144); every
  scaffolded scoped `AGENTS.md` cited by the map or a skill's step 1; every skill step 1
  naming an existing file; every row naming an existing surface and every surface having a
  row. Depends on T-047-53. Seam: the map is the auditable balance of the migration.
  Write set: `public/data/CONTEXT-MAP.md`, `tests/contract/test_context_map.py`,
  `public/entities/behavior-map.json`.

- [ ] T-047-55 — FR3a: collapse the law-projection surface. `LAW_BASENAMES = {"AGENTS.md"}`;
  delete `LAW_HARNESS_DIRS`, `DADAIA_MD_HARNESS_TARGETS`, `_law_projection_rules`, the
  `CLAUDE.md` half of `_guardrail_pair_rules` + `_CLAUDE_MD_STUB`, the consumer `CLAUDE.md`
  decider/pair logic in `workspace_guardrail.py`, `public/kimi-code/`, the `.codex/DADAIA.md`
  mirror and the `.codex/skills` copy rules; `HARNESS_DIRS = {.agents, .claude, .codex}`
  declared directly (no longer derived); `kimi-code` stays in `L1_ENTRY_HARNESSES` with an
  empty own-projection set. Root whitelist drops `CLAUDE.md`, `DADAIA.md`, `.kimi-code`, so
  `dadaia doctor --fix` reaps them as `WS-root-slop` on a live instance; add the repo-level
  reap for orphan `repos/<slug>/CLAUDE.md`. PROTECTED law rows = the projected `AGENTS.md`
  set; the gate still blocks exactly three things. Depends on T-047-52. Seam:
  `gate_policy._is_law_path`. RED: `test_gate_policy.py` asserting a root `CLAUDE.md` write
  is no longer PROTECTED; `test_workspace_layout_single_authority.py` and `test_zone_registry.py`
  green with the new constants.
  Write set: `core/{workspace_layout,harness_registry}.py`, `hooks/**`,
  `infrastructure/**`, `features/spec_context/{gate_policy,doctor}.py`,
  `features/specs/doctor_coherence.py`,
  `public/kimi-code/**` (deleted), `public/runtime/codex/**`, `cli/commands/public.py`, `tests/**`.

- [ ] T-047-56 — FR3b: one authored set, projected by symlink, and the persona rename.
  `.agents/agents/dd-<persona>.md` is the rendered persona (`render_claude_agent` stays the
  one render seam); `_claude_agent_rules` and `_skills_tree_rules` emit relative symlinks for
  `.claude/agents/dd-*.md` and `.claude/skills/dd-*`, falling back to a hash-verified copy
  when `os.symlink` raises; the install ledger records the entry kind, not only the digest.
  Personas renamed `dd-project-manager`, `dd-software-engineer`, `dd-code-reviewer` across
  `CORE_AGENTS`, `_FABLE_FORBIDDEN_AGENT`, the harness/model registry, the behavior map
  owner rows and grants, and every subagent name inside the skills — one commit, one fact.
  `.codex/agents/*.toml` transcode follows, old filenames removed by the stale path. Depends
  on T-047-55. Seam: the per-entry projection rule. RED:
  `test_claude_scaffold_is_loadable.py` resolving frontmatter through the symlink; a unit
  test forcing `os.symlink` to raise `OSError` and asserting the hash-equal copy.
  Write set: `infrastructure/{projection_rules,install_helpers,codex_*}.py`,
  `core/{agent_model_templates,model_registry,harness_registry}.py`,
  `core/models/install_ledger.py`, `public/agents/**`, `public/entities/**`,
  `public/skills/**`, `tests/**`.

- [ ] T-047-57 — FR3c: `public doctor` and init. Delete the per-harness byte-drift classes
  that died with the collapsed copies; add `SYMLINK-TARGET-1` (a `.claude/` entry is a
  symlink resolving to its canonical `.agents/*` path, or a hash-equal copy);
  `public-privacy`, `entities-derivation`, `rule-corpus`, `trust-boundary` stay. `dadaia init`
  prints once the recommendation to set `instructionFiles: claude-md-and-agents-md` in the
  Claude user settings (never writes them) and the sessions-launch-at-the-root sentence; no
  harness version floor anywhere. Depends on T-047-56. Seam: the public-doctor check list.
  RED: an integration case over a hand-broken `.claude/skills/dd-*` symlink target.
  Write set: `infrastructure/{entity_doctor,codex_doctor,public_assets}.py`,
  `cli/commands/{public,init}.py`, `docs/**`, `tests/**`.

- [ ] T-047-60 — FR6: spec-context audit, freeze, paradigm. Run the bug-history audit of the
  spec_context surface (every `BUGS.jsonl` record and `_archive/` closure whose surface or
  title names context, bind, session or presence): weak points, repeated symptoms, which
  fixes were symptom patches, structural fixes still owed, every bug id judged; no code
  change follows unless a confirmed bug (Arm B). This task lands the evidence and the two
  non-memory texts: the freeze statement in `public/data/dadaia-AGENTS.md` (no new
  context verb, no new state file, no new session field; a single-repo context is the
  degenerate multi-repo case) and the founding paradigm opening `README.md`. The atom-side
  writes it feeds — the *Bug history* section of `context-management` and the paradigm
  statement in `product-vision` — are authored by `project-manager` in the closure memory
  pass (RC-FLOW step 5), never as implementation. Uses FR5's vocabulary. Seam: none —
  documentation of an existing one. Evidence: the audit findings recorded in the handoff.
  Write set: `public/data/dadaia-AGENTS.md`, `README.md`.

- [ ] T-047-61 — FR7a: ratchets. V35 holds its 18-dir / 2906-line ceiling by deleting the
  skill prose the migrated statements replace; new ratchets pin the AC1.1 byte ceilings in
  `test_context_map.py`; V26/V32/V33 re-pinned downward where the deletions allow;
  `import-linter` pins re-measured; `test_module_size_ceiling.py` and
  `test_test_suite_ratchets.py` re-pinned. Depends on T-047-57.
  Write set: `tests/contract/**`, `setup.cfg`, `pyproject.toml`.

- [ ] T-047-62 — FR7b: closure. CHANGELOG "Candidate 6 — universal context core";
  `_RELEASE.json` log with the AC2.2 probe results and the measured bytes per surface; live
  instance reflected (stage -> install --target all -> public doctor -> `dadaia doctor --fix`
  exit 0); preflight; push; CI green; `dd-code-review` three axes + six lenses; PR #260
  updated. The closure memory pass (atoms `harness-claude-code`, `harness-codex`,
  `harness-kimi-code`, `public-asset-distribution`, `context-management`, `product-vision`,
  `agentic-entities`, ARCHITECTURE/TECHSTACK/QUALITY Part 2, `brand-identity` rehomed) is
  `project-manager`'s CLOSURE procedure, run after this task, not inside it.
  Write set: `CHANGELOG.md`, `specs/releases/0.4.7/_RELEASE.json`.
