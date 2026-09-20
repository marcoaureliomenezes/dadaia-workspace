# PLAN — Release: 0.4.7

**Status:** Approved
**Release ID:** 0.4.7
**Owner:** software-engineer

---

## Design (codebase-design vocabulary)

Candidate 6 replaces one deep-but-wrong module — the 25.5 KB always-on `DADAIA.md` — with
the shape the harnesses already implement natively. Its interface is "read everything before
acting": negative leverage (half of Codex's 32 KiB cap) and false locality (a backlog rule
next to a hook rule, while `backlog/AGENTS.md` states it again). Replace, don't layer: the
root map keeps what no governed area owns, every other statement moves into its owning area
and is deduplicated there, `public/data/DADAIA.md` is deleted. Nothing is wrapped.

- **Seam moved.** Law delivery goes from *one projected file per harness dir* to *one
  authored `AGENTS.md` per governed area, read by the harness's own root->cwd chain*. Its
  adapters collapse from four (`_law_projection_rules`, `DADAIA_MD_HARNESS_TARGETS`,
  `_guardrail_pair_rules`' CLAUDE.md half, `public/kimi-code/`) to zero.
- **Seam narrowed.** `LAW_BASENAMES` stays the gate's PROTECTED origin test
  (`gate_policy._is_law_path`) and shrinks to `{AGENTS.md}`; the gate still blocks three things.
- **Seam replaced by the filesystem.** `.claude/skills/*` and `.claude/agents/*` become
  per-entry symlinks into `.agents/*`; two copy trees and their byte-drift doctor classes
  die, one `SYMLINK-TARGET-1` check replaces them. The hash-verified copy fallback exists
  only because `os.symlink` can raise.
- **Depth kept.** `render_claude_agent` remains the one place model/effort/permission fields
  are appended; the `dd-<persona>` rename lands in one task because `CORE_AGENTS`, the
  behavior map, the grants and the skills' subagent names are one fact in four files.
- **Deletion test.** FR1/FR3 delete outright; FR4/FR5 are renames, zero net lines.
  `CONTEXT-MAP.md` + `test_context_map.py` are the only net additions and earn their keep:
  without a measured ceiling the migration is unverifiable and drifts back.

## Order of work (tracer bullets)

Each task leaves `dadaia ci preflight` green.

1. **T-047-58 (FR4), T-047-59 (FR5)** — independent of the migration; renaming tokens and
   context vocabulary first means every file the migration rewrites is already English.
2. **T-047-51 (FR1a)** — migrate each section into its scoped `AGENTS.md`/skill and rewrite
   the root map; `DADAIA.md` still exists and still projects.
3. **T-047-52 (FR1b)** — delete `DADAIA.md`, re-key the behavior map, re-record hashes. The
   rewrite precedes it; the projection collapse follows it.
4. **T-047-53, T-047-54 (FR2)** — skills gain step 1; then CONTEXT-MAP and its contract test,
   written against final bytes.
5. **T-047-55 (FR3a)** constants + projection rules collapse; **T-047-56 (FR3b)** symlinks +
   persona rename; **T-047-57 (FR3c)** `public doctor` classes + `dadaia init` print.
6. **T-047-60 (FR6)** audit, freeze, paradigm. **T-047-61/62 (FR7)** ratchets, then closure.

## Verification

- `dadaia ci preflight` green after every task; full suite green at closure.
- New `tests/contract/test_context_map.py`; amended `test_copy_drift_scoped_law.py`,
  `test_claude_scaffold_is_loadable.py`, `test_behavior_map.py`,
  `test_agentic_entities_derivation.py`, `test_workspace_layout_single_authority.py`,
  `test_zone_registry.py`, `test_gate_policy.py`, `test_every_block_carries_a_fix.py`,
  `test_claude_code_law_single_load.py`, `test_slop_ratchets.py`.
- Live instance: `public stage` -> `public install --target all` -> `public doctor` ok ->
  `dadaia doctor --fix` exit 0, no root `CLAUDE.md`/`DADAIA.md`/`.kimi-code/`.
- AC2.2 headless probes (Claude, Codex) from `tests/tmp/`, results in the closure log.

## Risks

- V35 (`_V35_LINE_CEILING = 2906`, `_V35_DIR_CEILING = 18`) goes UP: FR1 pushes §4, §7.1–7.6,
  §8.4 and the glossary into skills. T-047-51 deletes as much skill prose as it adds. Never
  raise the ceiling.
- 37 test files pin `DADAIA.md` bytes or path — incl. `test_agents_banner_constant_matches_
  public_data.py`, `test_fixed_sections_canon.py`, `test_claude_code_law_single_load.py` and
  the `_golden/doctor_golden_v0155.json` fixture; a missed golden goes red at push.
- `hooks/{_common,ctx_inject,root_whitelist}.py` name `kimi`/`DADAIA.md`: the injection
  prefix must not point at a deleted file, and `_WHITELIST` is identity-asserted against
  `workspace_layout` — change the constant, never the hook's copy.
- Stall risk: `_is_law_path` keeps the projected root `AGENTS.md` PROTECTED — author under
  `dadaia_workspace/public/`, reach the root only through `public install`.
- `_guardrail_pair_rules` fans out into consumer repos; dropping its `CLAUDE.md` half leaves
  orphan `repos/<slug>/CLAUDE.md` stubs and `WS-root-slop` has no repo twin today.
- The install ledger must record a projected entry's *kind*, or a copy silently satisfies a
  symlink row (`read_bytes()` follows the target, so the digest alone cannot tell).
- FR4's token rewrite must exclude `releases/_archive/**` by path, not heuristic, or pre-push
  refuses the rewritten range.
- The persona rename changes `.codex/agents/*.toml` filenames — verify the stale-removal path
  deletes the old three instead of leaving six.
