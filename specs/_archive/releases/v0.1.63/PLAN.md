# PLAN — v0.1.63 — Plugin Platform Completion (uninstall + full pack skill corpora)

**Status:** Aprovado

Six waves (W0–W5). The two consumed backlog items are separable by owner and file surface: the **uninstall
machinery** (FR1–FR3, software-engineer, `plugin.py` + `public_assets.py` + `plugin_pack.py`) and the **skill
corpora** (FR4–FR5, ai-engineer, `public/plugins/**` content only). They share `pack.json` + the content
contract tests at the FR6 wiring seam, so the corpus waves land BEFORE the wiring/ref-check wave and the two
content waves never touch machinery files. Machinery first (W1) so the corpus waves can validate against a
complete install/uninstall cycle. Sequencing constraint §0 of SPEC (A-1 agnosticism; rebase-and-reverify if a
parallel release lands on shared files) applies to every wave.

## Wave map

- **W0 — definition.** SPEC/PLAN/TASKS from the 2026-07-07 code read; mandatory release-definition grill on the
  picked set (operator unavailable ⇒ §9 operator-overridable ADRs U1–U4, C1–C3); the A-1 sequencing clause
  written into FR2. **Dual-review fold (2026-07-07, REJECT):** QA63-1..3 + ARCH63-1 + ARCHX/QAX folded with
  `<!-- AMEND:… -->` markers; PM Rulings 63-A/63-B/63-F in SPEC §0 (fixed order v0.1.61→62→63→64 with v0.1.61
  named in the W1 rebase clause; generalized shared-atom closure merge order; AC-2 upgraded — absolute golden (b)
  anchor + direct `.codex` stub-restore byte asserts). `Aprovado` after re-verify; definition commit.
  Owner: product-engineer (orchestrated).

- **W1 — FR1/FR2/FR3 uninstall machinery (software-engineer; RED-first).**
  1. **Pure model:** `InstalledPlugins.with_removed(name)` in `core/models/plugin_pack.py` (mirrors
     `with_added`; removing an absent name returns `self`). Unit tests beside the existing `with_added` cases.
  2. **`uninstall_plugin`** in `infrastructure/public_assets.py` (plugin block, after `install_plugin`):
     enumerate the staged pack tree (read fact 3); profile-scoped (ADR-U3, same `_profile_harnesses` seam);
     restore the core-stub projection over each pack agent (claude md + codex toml — the same core projection
     slice); delete pack-only skill/rule projections + now-empty dirs; drift lines `[drift-restored]`/
     `[drift-removed]` per hand-edited file (ADR-U1); unstaged pack ⇒ ledger-only + non-silent line;
     **files first, ledger last** (ADR-U4). Ledger access through the same store-construction pattern
     `install_plugin` uses at the base commit (A-1-agnostic — do NOT import `core/protocols/plugin_store.py`).
  3. **CLI:** `uninstall` command in `cli/commands/plugin.py` — descriptor validation before workspace
     resolution (unknown ⇒ `BadParameter` exit 2); known-not-installed ⇒ exit 0 `no change` (ADR-U2); success
     prints restored agents.
  - **W1 rebase clause (Ruling 63-A):** rebase onto v0.1.61's landed `plugin.py`/`public_assets.py` state (the
    A-1 port wiring lands FIRST); adopt whichever store-construction pattern it left; re-run the suite
    post-rebase. **First implementation wave (QAX-4): pin the branch-point `pytest --collect-only -q` count in
    this wave's fate ledger.** <!-- AMEND:ARCHX-1 --> <!-- AMEND:QAX-4 -->
  - Tests (RED-first: no `uninstall` verb pre-fix): AC-1 CLI surface (`_norm_stderr` before stderr asserts);
    **AC-2 never-installed equivalence — UPGRADED (Ruling 63-F / QA63-1):** same-run self-relative A-vs-B
    comparison **PLUS the absolute anchor (side B's post-uninstall doctor/runtime surface vs the durable
    v0.1.60 golden (b) never-installed baseline — read-only reuse, zero regen) PLUS direct byte asserts that
    `.codex/agents/{frontend-engineer,design-specialist}.toml` equal the fresh core-stub render and zero pack
    rule projections remain, in the absent-profile (all-targets) leg** <!-- AMEND:QA63-1 -->; the equivalence
    test is `@pytest.mark.slow`, bracket ≤ ~15s (QA63-2) <!-- AMEND:QA63-2 -->;
    AC-3 idempotency + files-before-ledger + multi-pack isolation; AC-4 profile×uninstall (claude-only never
    touches `.codex/`); AC-5 drift-never-silent + `repos/**` untouched. Mutation-sanity AC-8(a)–(d) captured on
    the task line, then reverted. Fate ledger per AC-10.

- **W2 — FR4 `frontend-design` skill corpus (ai-engineer; `public/plugins/frontend-design/**` only).**
  1. Author `design-system-authoring`, `frontend-component-architecture`, `visual-review-protocol` SKILL.md
     bodies (generic, public-privacy law; `visual-review-protocol` references `design-ctx`/`frontend-ctx` by
     name, never inlines their emit blocks).
  2. Wire: `pack.json` `skills[]` → 4 entries; agent frontmatter — `design-specialist` gains
     `design-system-authoring` + `visual-review-protocol`; `frontend-engineer` gains
     `frontend-component-architecture`.
  3. **Ceiling-constant amendment (recorded):** extend `test_plugin_content.py` `_PACK_SKILL`/`_EXPECTED_SKILLS`
     to a per-pack roster map admitting exactly this pack's 4 skills — cited on the task line with the roster
     diff (the pre-amendment RED run is the RED-first evidence).
  - Tests: AC-6 for this pack (roster == pack.json == disk; frontmatter law; adapters not inlined; privacy).
    Note: the FR6 ref check does not exist yet — frontmatter refs are asserted by the extended content contract
    in this wave, machine-checked doctor-side in W4.

- **W3 — FR5 `devops` skill corpus (ai-engineer; `public/plugins/devops/**` only; parallel-safe with W2 —
  disjoint write sets, may run as the second `[-]` only if TASKS declares it; default sequential).**
  1. Author `gitflow-release-engineering`, `container-build-and-deploy`, `cicd-security-hardening`.
  2. Wire: `pack.json` `skills[]` → 4 entries; `devops-engineer` frontmatter gains all three.
  3. Ceiling map extended for this pack (same recorded-amendment discipline as W2).
  - Tests: AC-6 for this pack; AC-8(f) sabotage (drop a skill from pack.json, keep the dir ⇒ roster contract
    FAILS → revert).

- **W4 — FR6 plugin-aware skill-ref integrity (software-engineer; `infrastructure/codex_doctor.py` +
  `public_assets.py` doctor call site).**
  1. Extend `check_agent_skill_refs` (or add a sibling on the same `[drift]` prefix — ADR-C3) to sweep
     `public/plugins/<pack>/agents/*.md`, resolving each `skills:` ref against `public/skills/` ∪ that pack's
     `plugins/<pack>/skills/`; report through the existing `public doctor` path (`public.py:47-50` ref-drift
     handling — non-zero on `[drift]`).
  2. Full-sweep content contract: every pack-agent ref resolves for BOTH packs (the W2/W3 rosters now green
     end-to-end).
  - Tests: AC-7 RED-first (pre-fix a bogus pack-agent ref yields zero lines — demonstrated; post-fix `[drift]` +
    doctor non-zero); AC-8(e) sabotage. Fate ledger: existing `check_agent_skill_refs` core-agent cases SURVIVE
    byte-identical (the extension is additive on a new directory sweep).

- **W5 — ship + reviews.** Full gates (AC-9): ruff format/check, mypy --strict, unpiped pytest, lint-imports
  (kept/ignore-cap unchanged), specs doctor, backlog doctor; `dadaia public stage` → `public doctor` →
  `public install --target all` → confirming `public doctor` (`[ok] public-privacy`, exit 0) on the live
  instance; frozen no-steal suite zero-diff confirmed. qa-engineer review at the alpha boundary; push cycles
  carry the security-reviewer APPROVE per push (release-governance). Operator ship/iterate decision at rc.

- **CLOSURE (product-engineer).** CLOSURE.md with validations/drifts/dispositions; both backlog items →
  `DELIVERED — v0.1.63`; memory edits per SPEC §8 (plugin-packs atom primary; catalog regen; PluginStore-port
  wording left to v0.1.61). **Merge order (Rulings 63-B + ARCH63-1):** closes after v0.1.61/62, before v0.1.64 —
  rebase `plugin-packs.md`, `public-asset-distribution.md`, AND `architecture.md` on the siblings' closed state
  (never revert their corrections); catalog regen includes prior deltas. <!-- AMEND:ARCH63-1 --> Archive via
  `git mv`.

## Layers affected

| Layer | Files | Change |
|---|---|---|
| core | `core/models/plugin_pack.py` | `InstalledPlugins.with_removed` (pure) |
| infrastructure | `public_assets.py` (plugin block), `codex_doctor.py` | `uninstall_plugin`; plugin-aware ref sweep |
| cli | `cli/commands/plugin.py` | `uninstall` command |
| public content | `public/plugins/{frontend-design,devops}/**` | 6 new skills + pack.json + agent frontmatter |
| tests | see fate ledger | new + extended suites |

No new layer edge: `with_removed` is core-pure; `uninstall_plugin` mirrors `install_plugin`'s existing imports;
the CLI verb reuses `plugin.py`'s existing imports. lint-imports kept/ignore-cap counts re-read at
implementation base (they may have moved if v0.1.61 landed first) and asserted **unchanged by this release**.

## Execution order

W0 → W1 → W2 → W3 → W4 → W5 → CLOSURE. Shared files force sequencing: `public_assets.py` is touched in W1 and
W4 only (disjoint blocks, still sequential); `test_plugin_content.py` is touched in W2, W3, W4 (sequential);
W2/W3 have disjoint `public/plugins/<pack>/**` write sets (parallel-eligible only if TASKS declares it).

## Fate ledger — v0.1.60 plugin test suites (mandatory adjudication, AC-10)

| Suite | Fate |
|---|---|
| `tests/unit/core/test_plugin_pack.py` | EXTENDED — gains `with_removed` cases; existing cases SURVIVE |
| `tests/unit/cli/test_plugin_cli.py` | EXTENDED — gains uninstall verb cases; existing install/list/doctor cases SURVIVE byte-identical |
| `tests/unit/infrastructure/test_json_plugin_store.py` | SURVIVES untouched (ledger schema unchanged) |
| `tests/unit/infrastructure/test_plugin_content.py` | AMENDED (recorded) — ceiling constants → per-pack roster map (W2/W3); all other asserts SURVIVE; the amendment commit cites the roster diff |
| `tests/integration/test_plugin_projection.py` | SURVIVES untouched (install-side mechanism unchanged) |
| `tests/integration/test_plugin_install_goldens.py` + golden (b) fixture | SURVIVES untouched — golden (b) stays the durable never-installed baseline AND becomes AC-2's read-only **absolute anchor** for side B (Ruling 63-F — reuse, never regen) <!-- AMEND:QA63-1 --> |
| `tests/e2e/features/test_plugin_pipeline.py` | EXTENDED — gains the install→uninstall→reinstall leg; existing legs SURVIVE |
| `tests/contract/test_plugin_install_residue.py` | ASSESS at W1 — if it pins "no removal path exists", it is AMENDED with rationale; otherwise SURVIVES |
| `tests/contract/test_agent_tier_taxonomy.py` | SURVIVES untouched (tier/model unchanged) |
| v0.1.50 frozen no-steal suite | ZERO-DIFF (no lease/gate path touched) |

## Technical risks

1. **Stub-restore fidelity (W1):** the restored projection must be byte-identical to a fresh core install's stub
   projection (claude md copy + codex stub render). Covered by AC-2's self-relative comparison — any fidelity gap
   is a byte diff.
2. **Deletion blast radius (W1):** removal set strictly = staged pack tree enumeration; asserted by AC-2/AC-3
   (other pack + core skills intact) and AC-5 (`repos/**` untouched).
3. **Parallel-release rebase (all waves):** v0.1.61/62/64 may land on shared files first; each wave re-runs its
   suite after rebase; FR2's construction-pattern clause absorbs the A-1 outcome.
4. **Content slop (W2/W3):** ceiling BY NAME + recorded constant amendment + reference-not-duplicate contract;
   ai-engineer sole author; qa review at the alpha boundary.

## Validation plan

Per-wave: the wave's new/extended tests + full unpiped pytest + ruff + mypy --strict + lint-imports. W5 adds the
live-instance stage/install/doctor cycle and specs/backlog doctors. Evidence recorded per task (commit SHAs,
RED-first captures, sabotage captures) into CLOSURE's Validations table.
