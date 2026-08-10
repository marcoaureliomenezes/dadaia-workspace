# PLAN — v0.1.61 — Audit Remediation & Memory Truth

**Status:** Aprovado

Seven waves. **W1 (memory truth pass A + constitution amendment) runs FIRST, under `ACTIVE.md` phase =
`DEFINITION`** (the MEMORY gate window) — implementers then ground on true memory. The phase flips to
`IMPLEMENTATION` only after W1 commits. Code waves W2 (A-1 wiring) → W3 (A-2 contract) are **sequential** (W3's
recorded ignore set depends on which cli→infra edges W2 removes). W4 (hygiene batch) is disjoint-file and may
run after W3. W5 gates+ship; W6 closure carries memory pass B + the disposition sweep.

## Wave map

- **W0 — definition.** SPEC/PLAN/TASKS from the 2026-07-07 code read; mandatory grill on the picked set (both
  audit lanes + 1 backlog fold), operator unavailable → 6 operator-overridable ADRs + 3 grill corrections
  (SPEC §9); the full 41-row disposition table (SPEC §6). **Dual-review fold (2026-07-07):** ARCH61-1..3 +
  QA61-1..4 + cross-release ARCHX/QAX folded with `<!-- AMEND:… -->` markers; PM Rulings 61-A..61-D recorded in
  SPEC §0 (fixed order v0.1.61→62→63→64; shared-atom closure merge order; 41-row tally; executed-path FR4).
  `Aprovado` after re-verify; definition commit. Owner: product-engineer (orchestrated).

- **W1 — FR1+FR2+FR3 memory truth pass A + PyPI atom + constitution amendment (DEFINITION phase — MEMORY gate).**
  Owner: product-engineer. Sequenced explicitly: `ACTIVE.md` stays `phase: DEFINITION` until this wave's commit.
  1. Stale-claim purge across the drifted atoms per SPEC FR1 (G-1..G-11, G-13..G-17), each edit a **dated
     drift-fix** attributed to the release that shipped the reality (v0.1.60 precedent) — never phrased as a
     v0.1.61 change; memory stays atomic (no changelog language).
  2. LINT-1: correct token_estimate frontmatter (5 atoms); allowlist the 3 flagged headings via the workspace
     heading-allowlist file under `specs/memory/` (no code change — `lint-memory-atoms.py:252`) or retitle.
  3. TREE-5: diff `specs/AGENTS.md` vs the canonical template; merge (keep local law additions, restore canonical
     structure).
  4. NEW `specs/memory/product/distribution/pypi-distribution.md` (FR2/ADR-2) + `quality-assurance.md`
     `release.yml` row + C-1 note.
  5. Constitution: §1 operational-change lane (ADR-1, incl. the memory-bearing test + #115 counter-example +
     #112/#113/#115 post-hoc ratification pointer), §13 index wording (G-19); `constitution_version` → 2.1.0.
  6. `dadaia memory catalog generate` (new atom + any tldr/summary change); `dadaia specs doctor` must exit 0
     with LINT-1/TREE-5 clean (AC-1/AC-2/AC-3/AC-4).
  - Evidence: grep transcript for every retired claim (AC-1 list) = 0 hits; doctor output. Commit, then PM flips
    phase → `IMPLEMENTATION`.

- **W2 — FR4 wire the PluginStore port (A-1; software-engineer).** RED-first. First implementation wave: **pin
  the branch-point `pytest --collect-only -q` count in this wave's fate ledger** (QA61-4/QAX-4 — the QA atom's
  4,339 bracket is stale, live ≈4.7k; brackets re-validated at closure). <!-- AMEND:QA61-4 -->
  1. NEW contract test `tests/contract/test_plugin_store_port_wired.py` — **executed-path PRIMARY (Ruling 61-D /
     QA61-1):** <!-- AMEND:QA61-1 --> CliRunner + monkeypatch/spy on `container.build_plugin_store`, asserting
     `dadaia plugin list` AND `dadaia plugin install <pack>` consume the spy's store at runtime. Secondary lens:
     AST/grep (production `JsonPluginStore(` construction only in `container.py`,
     `infrastructure/json_plugin_store.py`, and the `public_assets` default parameter; `build_plugin_store()`
     returns a `PluginStore`-satisfying object). Shown RED on the pre-fix tree (`cli/commands/plugin.py:81`
     constructs directly — the spy is never reached).
  2. `container.build_plugin_store()` factory (mirrors `HarnessProfileStore` wiring).
  3. `cli/commands/plugin.py`: consume via container; drop the `json_plugin_store` import (removes 1-2 of the
     cli→infra edges).
  4. `FileSystemPublicAssetManager(plugin_store: PluginStore = ...)` constructor injection replacing the 3 inline
     constructions (`public_assets.py:238,344` + import at `:50` retained only for the default).
  5. Port docstring now true; update `plugin.py` module docstring if it names the adapter.
  - Byte-lock: v0.1.60 plugin goldens (a)/(b), `test_plugin_projection.py`, `test_plugin_pipeline.py` E2E — all
    green with **zero golden re-baseline** (AC-5). Sabotage AC-9(a).

- **W3 — FR5 `cli-no-infrastructure` contract (A-2; software-engineer, software-architect countersign).**
  1. **Re-enumerate at implementation truth** (post-W2): grep all `cli → infrastructure` imports; record the
     exact set (SPEC read fact 3 minus W2 removals; expect ≤ 10 sites).
  2. `setup.cfg`: new `forbidden` contract, source `dadaia_workspace.cli`, forbidden
     `dadaia_workspace.infrastructure`, recorded edges as ignores (comment each with its wiring rationale, per
     the F10 pattern).
  3. Extend `tests/contract/test_import_linter_ignore_cap.py`: new family cap pinned; stale-above-reality
     ratchet-down covers it; per-family assertions extended.
  - `lint-imports --no-cache` = **9 kept / 0 broken** (AC-6). RED probe: temporary unrecorded import breaks the
    contract (captured, reverted). Sabotages AC-9(b)(b′).

- **W4 — FR6 hygiene batch (software-engineer + ai-engineer, disjoint files).**
  1. (SE) T-1: convert the class-scoped instance-method fixture in
     `tests/integration/test_telemetry_corrupt_db.py` per the pytest deprecation doc → full suite 0 warnings.
  2. (SE) CI-1+CI-2: NEW `tests/contract/test_ci_workflow_hygiene.py` RED-first (asserts: no
     `primary_context.json` under `.github/workflows/`; both `ci.yml` + `release.yml` call
     `.github/scripts/bootstrap-panel-ws.sh`; no inline duplicate body). Then: extract the 39-line bootstrap to
     the shared script; delete the `primary_context.json` heredocs from both workflows.
  3. (ai-engineer) D-1: drop `agent_tier` from `public/schemas/memory/memory-frontmatter-v1.schema.json`
     (public-asset flow: stage → install → doctor); pin `"agent_tier"` absent in the schema contract test.
  4. (ai-engineer) Backlog fold: sanctioned hand-sync of `repos/dadaia-workspace/AGENTS.md` — collapse the
     doubled workspace-law header to the single canonical short header (successor to the v0.1.47 T-47-32
     exception; the `_is_self_repo` skip is why only a hand-sync works). Grep AC: exactly one canonical banner.
  - Sabotages AC-9(c)(d)(e).

- **W5 — FR7 + gates + ship (T-61-60).** Owner: software-engineer (gates) + qa-engineer (ship-gate) +
  security-reviewer (push-gate); operator/PM shell for the FR7 items.
  1. FR7: `dadaia doctor --fix` (`.mypy_cache/`, stale `sample-games` lease); surface `bug-space-war` to the
     operator (record the triage or the explicit deferral); delete stale `dist/` contents; request `git mv` of
     the v0.1.41 residue → `specs/_archive/wip-abandoned/v0.1.41/` + README breadcrumb (operator/PM — `_archive`
     is FROZEN for file tools).
  2. Full gates (AC-10): unpiped `pytest` (0 warnings) + ruff format/check + `mypy --strict` +
     `lint-imports --no-cache` (9/0) + `specs doctor` + `backlog doctor`; self-hosting reconcile
     `public stage → doctor → install --target all → doctor` (`[ok] public-privacy`) — required by W4's schema
     edit + hand-sync. Frozen v0.1.50 no-steal suite zero-diff.
  3. QA ship-gate; security push-gate keyed to the pushed sha; push; **watch CI until every job green** — incl.
     the e2e-panel leg on BOTH workflows (CI-2's shared script must prove itself on GHA; if `release.yml` does
     not fire this push, record the evidence plan at ship). PR; merge.
  *(PE runs no shell — all commands surfaced to PM/operator or devops routing per plugin-scope.)*

- **W6 — FR8 closure (CLOSURE phase; T-61-70).** Owner: product-engineer. `ACTIVE.md` phase = `CLOSURE`.
  1. CLOSURE.md (Summary, Tasks + SHAs, Validations triples, Drifts, Memory updates, **Dispositions = the full
     40-row §6 table with evidence**, Backlog returns, Archive decision).
  2. **Memory pass B:** `architecture.md` (9 contracts + cap + `build_plugin_store` + wired seam),
     `quality-assurance.md` (CI notes), `plugin-packs.md` (verify seam wording). Catalog regen if needed.
  3. Backlog returns: `platform-seam-todo-retirement` (A-3), `specs-doctor-partial-archive-invariant` (G-23 gap)
     — routed through PM curation. `selfrepo-agents-md-doubled-header` → `DELIVERED — v0.1.61`.
  4. Archive both audit files → `specs/audits/_archive/` with normalized names referencing v0.1.61 (G-20,
     SPEC-DOC-030/036) via `git mv` (operator/PM).
  5. `dadaia specs doctor` clean; `git mv specs/releases/v0.1.61 → specs/_archive/releases/`; `ACTIVE.md` →
     `release: none`. **Order law: memory edits + catalog regen BEFORE `ACTIVE.md` leaves CLOSURE.**
  6. **Cross-release closure clauses (Rulings 61-B + ARCH61-3):** this release closes FIRST in the fixed order;
     the shared-atom merge-order clause (SPEC §8) binds the later-closing siblings, not this closure. CLOSURE.md
     records that ADR-1's operational-change lane is **judgment-enforced only** (human PR review + the reactive
     next-release memory pass; no mechanical gate). <!-- AMEND:ARCH61-3 -->

## Write sets (disjoint per wave; shared files force order)

| Wave | Files |
|---|---|
| W1 | `specs/memory/**` (FR1 atoms + NEW `pypi-distribution.md` + heading-allowlist file + `quality-assurance.md`), `specs/AGENTS.md`, `specs/constitution.md`, `specs/memory/product/{catalog.json,index.md}` (regen) |
| W2 | `dadaia_workspace/container.py`, `cli/commands/plugin.py`, `infrastructure/public_assets.py`, NEW `tests/contract/test_plugin_store_port_wired.py` |
| W3 | `setup.cfg`, `tests/contract/test_import_linter_ignore_cap.py` |
| W4 | `tests/integration/test_telemetry_corrupt_db.py`; `.github/workflows/{ci,release}.yml` + NEW `.github/scripts/bootstrap-panel-ws.sh` + NEW `tests/contract/test_ci_workflow_hygiene.py`; `public/schemas/memory/memory-frontmatter-v1.schema.json` (+ its contract test); `repos/dadaia-workspace/AGENTS.md` (self-repo root) |
| W5 | (gates; no `specs/**` change; operator shell: root/dist/archive-mv hygiene) |
| W6 | `specs/releases/v0.1.61/CLOSURE.md`, `specs/memory/**` (pass B), `specs/backlog/**` (returns + DELIVERED), `specs/audits/**` (archive mv), `ACTIVE.md` |

`public_assets.py` is W2-only. `setup.cfg` is W3-only (after W2 lands — the ignore set depends on it). No
parallel `[-]` except the W4 SE/ai-engineer split, whose write sets are disjoint (declared above).

## Test strategy

- **RED-first for every new guard:** the port-wired **executed-path spy** contract (W2 — the executed-path law,
  Ruling 61-D), the cli-no-infrastructure contract probe (W3), the CI-workflow hygiene contract (W4) are each
  shown failing against the pre-fix tree before the fix.
- **Suite-count baseline (QA61-4/QAX-4):** W2 (first implementation wave) pins the branch-point
  `pytest --collect-only -q` count in its fate ledger; re-validated at closure.
- **Memory acceptance is negative AND positive greps (QA61-2):** the AC-1 transcript carries both the
  retired-claim zero-hit greps and the per-finding positive greps (G-6/7/8/10/11/13-17) — doctor validates
  structure, the greps validate semantics.
- **Golden-first inversion:** this release CAPTURES no new goldens — it must not MOVE any. The v0.1.60 plugin
  goldens (a)/(b), the v0.1.58 install/doctor goldens, and the panel goldens are the byte-locks proving W2/W4
  are behavior-preserving. Zero golden re-baseline is an explicit AC (AC-5); any golden diff is a STOP-and-
  adjudicate, never a regen.
- **Existing-test fate ledger (file-enumerated per wave):**
  - W2: `tests/unit/cli/test_plugin_cli.py` — SURVIVES (CLI behavior unchanged; construction path may need a
    container monkeypatch seam — adjudicate, don't weaken); `tests/unit/infrastructure/test_json_plugin_store.py`
    — SURVIVES verbatim (adapter untouched); `tests/integration/test_plugin_projection.py` +
    `tests/e2e/features/test_plugin_pipeline.py` — SURVIVE byte-identical (goldens).
  - W3: `tests/contract/test_import_linter_ignore_cap.py` — AMENDED deliberately (new family; recorded, never
    silent); all other contract tests SURVIVE.
  - W4: `tests/integration/test_telemetry_corrupt_db.py` — AMENDED (fixture form only; assertions invariant);
    the memory-frontmatter schema contract test — AMENDED (adds the `agent_tier`-absent pin); e2e-panel CI legs
    — behavior-invariant (same steps via shared script; proven on GHA).
  - W1/W6 (memory): no pytest surface — evidence is grep transcripts + `specs doctor` exit 0 + catalog regen.
- **Mutation-sanity (AC-9):** each new test sabotaged → FAIL → reverted, captured on its task line: (a) re-inline
  `JsonPluginStore()` in the CLI; (b) unrecorded cli→infra import; (b′) cap lowered below reality; (c)
  `primary_context.json` heredoc restored; (d) `agent_tier` re-added; (e) T-1 fixture reverted (0-warnings gate).
- **Frozen suite:** v0.1.50 no-steal suite untouched (A-3 deferred precisely to avoid the locking path) —
  confirm zero-diff at gates.
- **CI truth:** the CI-2 shared script is only proven when the e2e-panel legs run green ON GHA (Rich-box/width/
  env class of failures never reproduces locally — QA-atom law). Watch both workflows.

## Platform seam note (3-OS CI)

W2/W3 are import-graph-only (no I/O change). W4's bootstrap script is bash on ubuntu-only jobs (e2e-panel legs
run on ubuntu; no Windows leg executes it — verify the job matrix at implementation and keep the script POSIX).
No symlink, lock, or `os.utime` surface touched.

## Rollback

Single feature branch `feature/v0.1.61`. W1/W6 are specs-only commits (revert = git revert; catalog regen
re-run). W2 reverts to inline construction (contract test removed with it). W3 reverts setup.cfg + cap test
(8 kept / 0 broken restored). W4 items are independent one-commit reverts (script inlining back, schema property
restore, fixture form, hand-sync). No data migration; no state file format change. The only cross-instance step
is the W5 `public install` reconcile — re-run stage/install/doctor to reconcile, never hand-edit projections.
