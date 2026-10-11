# Job 6 — one frontmatter parser, CRLF-tolerant; the Codex projection's private parser leaves (FR16)

**Status:** Draft

Wave 1. REBUILD of the persona parser (PLAN §1 row 20): two earlier fixes on this surface (`sa-frontmatter-split-five-ways`, then `sa-persona-model-read-by-two-parsers`, whose `caused_by` is the first) were symptom patches; the structural fix is one parser. `core.frontmatter.FRONTMATTER_RE` becomes CRLF-tolerant (`\r?\n`) and is the one reader; the other readers of that regex (`core/gitflow.py`, `core/specs_version.py`, `features/migrate/upgrade.py`) then accept CRLF files too (operator-confirmed).

- `core.frontmatter.fields(text)` is the consumer-facing read: the parsed mapping, or `{}` when `parse` returns an error. The five consumers use it; `persona_read_only` takes the YAML boolean.
- The text-splice consumers (`copilot_agent_md_bytes`, `render_claude_agent`, `codex_agent_toml_bytes`) split with `FRONTMATTER_RE` and `text[m.end():]`.
- Test-side first: T1, T2. Then T3; then T4, T5, T6 in parallel; T7 after them.
- Commit body of T4: `git grep -n -E '_parse_agent_frontmatter|_split_frontmatter|_parse_skills_from_frontmatter' -- dadaia_workspace tests` (about 30 hits before, 0 after).
- The vacuous test `test_every_wired_core_hook_derives_from_a_deterministic_behavior` of the diet list leaves with T6 (same file); Job 9 later reworks the registry tests.
- Net production lines ≤ 0 for the job (measured: the parser block is 98 lines and the regexes and whitelist about 12).
- Ledger transitions of this job's bugs (`bugs.py resolve`) are made at the Reconciliation, which owns `specs/bugs/BUGS.jsonl`; this job's fix commits echo the Phase 0 block.

Tasks: 7 (2 jr, 5 sr). `who` names the dispatched role (SPEC FR5 of rc-13, `dd-release-definition` §5).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J6.T1 | sr | AC16.1 | `tests/core/test_frontmatter.py` | RED, unit: `parse` of the same document on LF and on CRLF returns equal `data` and `body` (modulo the line ending of the body); a quoted scalar is unquoted. Owner `test_frontmatter.py` |
| J6.T2 | sr | AC16.1 | `tests/infrastructure/runtime_transforms/test_codex_assets.py` | RED, unit: the Codex agent blocks and `codex_agent_toml_bytes` of a persona on CRLF equal those of the same persona on LF, and a `description: "a: b"` is rendered without its quotes. Owner `test_codex_assets.py` |
| J6.T3 | sr | AC16.1 | `dadaia_workspace/core/frontmatter.py` | `FRONTMATTER_RE` tolerates `\r\n`; add `fields(text)`. Owner T1 |
| J6.T4 | sr | AC16.1 | `dadaia_workspace/infrastructure/runtime_transforms/codex_assets.py`, `dadaia_workspace/infrastructure/projection_rules.py` | REBUILD: delete `_split_frontmatter`, `_parse_agent_frontmatter`, `_parse_skills_from_frontmatter`, their three regexes and `_TOML_SAFE_AGENT_FIELDS`; `_render_agents_config_file_blocks` and `projection_rules` read `fields`. Owner T2. After T3. Fix commit of the CRLF bug; body echoes the Phase 0 block (`caused_by: sa-persona-model-read-by-two-parsers`, `prior diffs read: 638751add`, `rebuild: the persona parser`) |
| J6.T5 | sr | AC16.1 | `dadaia_workspace/infrastructure/agent_transcodes.py`, `dadaia_workspace/infrastructure/install_helpers.py` | the splice consumers split with `FRONTMATTER_RE`; `persona_read_only` accepts the YAML booleans and still fails closed otherwise; the model and description reads use `fields`. Owner T2. After T3 |
| J6.T6 | jr | AC16.1, AC9.1 | `dadaia_workspace/infrastructure/entity_doctor.py`, `tests/infrastructure/test_entity_doctor__agentic_entities_derivation.py` | the entity doctor reads persona fields and skills through `fields`; delete the vacuous `test_every_wired_core_hook_derives_from_a_deterministic_behavior` (the diet list). After T3 |
| J6.T7 | jr | AC16.1 | `tests/infrastructure/test_install_helpers.py`, `scripts/guards/suite.py` | port the two private-name imports of `_parse_agent_frontmatter` to `fields`; lower `PRIVATE_IMPORT_STATEMENTS` and `PRIVATE_IMPORT_FILES` by the measured delta in the same commit. Owner `python scripts/guards/run.py` exit 0. After T4 |
