# TASKS — v0.1.61 — Audit Remediation & Memory Truth

**Status:** Aprovado

Markers: `[ ]` open · `[-]` in progress · `[x]` done. W1 runs under `ACTIVE.md` phase = `DEFINITION` (MEMORY
gate); phase flips to `IMPLEMENTATION` only after T-61-10 commits. W2 → W3 sequential (`setup.cfg` ignore set
depends on W2's edge removals). W4's two tasks (SE / ai-engineer) have disjoint write sets — parallel `[-]`
explicitly declared safe. Every implementation task: **no `specs/backlog/**` staged** (returns + DELIVERED land
at CLOSURE, T-61-70). AC-9 mutation-sanity: each new test sabotaged → shown to FAIL → reverted, captured on the
task line. **Zero golden re-baseline** across the whole release — any golden diff is a STOP.

## W0 — definition

- [x] T-61-01 SPEC/PLAN/TASKS authored from the 2026-07-07 **code read** (audit citations spot-verified:
  tech-stack stale block byte-confirmed; PluginStore port zero-consumer + self-contradicting docstring confirmed;
  cli→infra = 11 sites / 9 modules by grep; v0.1.41 residue confirmed; LINT-1 heading allowlist =
  specs/memory-side file, no code change; `constitution_version` 2.0.0). Mandatory release-definition grill on
  the picked set (both audit lanes + backlog fold); operator unavailable → **ADR-1..ADR-6 recorded
  operator-overridable (SPEC §9)** + 3 grill corrections (A-3 tracking claim stale — anchor consumed at R6;
  module count 8→9; LINT-1 mechanism). Full disposition table (SPEC §6) — **41 rows post-Ruling 61-C: fixed 31 /
  superseded 1 / deferred 2 (tracked) / rejected 7 (reasoned)** (the ERA001/noqa-inventory row restored per
  ARCH61-1). **Dual-review fold (2026-07-07):** ARCH61-1..3 + QA61-1..4 + ARCHX/QAX folded with greppable
  `<!-- AMEND:… -->` markers; PM Rulings 61-A..61-D in SPEC §0 (fixed order v0.1.61→62→63→64; shared-atom
  closure merge order; 41-row tally + 28/12/1 lane relabel; FR4 executed-path upgrade). `Aprovado` after
  re-verify; definition commit. Owner: product-engineer (orchestrated).

## W1 — memory truth pass A + PyPI atom + constitution (DEFINITION phase)

- [ ] T-61-10 FR1+FR2+FR3 — stale-claim purge + LINT-1/TREE-5 + NEW `pypi-distribution.md` + constitution 2.1.0.
  Owner: product-engineer. **Phase guard: `ACTIVE.md` must read `phase: DEFINITION` for this task's whole span.**
  Write set: `specs/memory/**` (SPEC §8 DEFINITION list), `specs/AGENTS.md`, `specs/constitution.md`,
  `specs/memory/product/{catalog.json,index.md}` (regen). Checklist:
  - G-1/G-5: `tech-stack.md` §Model assignments → 5×fable-5(+effort)/4×opus split; delete the "Reserved
    entry / NEVER pin" block; fix the per-agent table; document `effort:` frontmatter. Same split in
    `agent-orchestration.md:96,224`.
  - G-2/G-3/G-4: purge "not yet distributed / no install command exists / only 4 verbs" from `tech-stack.md:124`
    (+ add the `devops` pack row) and `product-vision.md:109-111,171-178`.
  - G-6..G-11: `architecture.md` 23 subcommands; `dadaia-workflows.md` PARTIAL labels ×2; `agent-monitoring.md`
    v0.1.52+ refresh; `server-registry.md` verb roster; `multi-platform-parity.md` install story + heading;
    `cross-platform-portability.md` completed-follow-ups.
  - G-13..G-17: `panel.md:185` delete; `public-asset-distribution.md` 14 types; the G-15 one-liner cluster;
    `harness-pi.md` auth qualification; the G-17 polish items.
  - LINT-1: token_estimate frontmatter ×5; heading allowlist file extended (or headings retitled). TREE-5:
    `specs/AGENTS.md` diff-merged to canonical.
  - FR2: NEW `specs/memory/product/distribution/pypi-distribution.md` (0.2.x package, `release.yml` pipeline,
    wheel content contract, version-scheme split — ADR-2); `quality-assurance.md` `release.yml` row + C-1 note.
  - FR3: constitution §1 operational-change lane (ADR-1; memory-bearing test; #115 named counter-example;
    #112/#113/#115 ratification pointer) + §13 index wording (G-19); `constitution_version: 2.1.0`.
  - Catalog + index regen (`dadaia memory catalog generate` — surfaced to PM/operator; PE runs no shell);
    regenerated `tldr` within the length cap.
  - **AC evidence (AC-1..AC-4):** grep transcript = 0 hits for every retired claim **PLUS the per-finding
    POSITIVE greps (QA61-2 — G-6 "23 subcommands"+`plugin`; G-7 exactly 2 PARTIAL labels; G-8 dashboard-only
    sessions truth; G-10 `dadaia plugin install` named; G-11 cross-leg names, no pending-follow-up residue;
    G-13 zero "Mermaid remains loaded"; G-14 `plugins` in the 14-type list; G-15 `features/spec_context/lease.py`;
    G-16 the `ANTHROPIC_API_KEY` qualification; G-17 INV-5 prose==table) in the same transcript**
    <!-- AMEND:QA61-2 -->; `dadaia specs doctor` exit 0, LINT-1/TREE-5 clean. **Sabotage line (manual, memory has
    no pytest):** leave ONE retired phrase in a scratch run ⇒ the AC-1 negative grep shows the hit ⇒ fix; drop one
    positive-grep target ⇒ that AC-1 positive grep FAILS ⇒ fix; doctor LINT-1 warn on a wrong token_estimate ⇒
    fix. Captured here.
  - Each edit dated to its originating release (drift-fix language, no changelog sections). Commit
    `docs(T-61-10): memory truth pass A + pypi atom + constitution 2.1.0`. PM then flips phase → IMPLEMENTATION.

## W2 — wire the PluginStore port (A-1)

- [ ] T-61-20 FR4 — container factory + constructor injection + port-wired contract test (RED-first,
  **executed-path primary** — Ruling 61-D). Owner: software-engineer. Write set: `dadaia_workspace/container.py`,
  `cli/commands/plugin.py`, `infrastructure/public_assets.py`, NEW
  `tests/contract/test_plugin_store_port_wired.py`. **First implementation wave: pin the branch-point
  `pytest --collect-only -q` count in this task's fate ledger (QA61-4/QAX-4).** <!-- AMEND:QA61-4 --> Checklist:
  - Contract test FIRST, shown **RED** on the pre-fix tree (`plugin.py:81` constructs `JsonPluginStore()`
    directly): <!-- AMEND:QA61-1 --> **(primary, executed-path)** CliRunner + monkeypatch/spy on
    `container.build_plugin_store` — `dadaia plugin list` AND `dadaia plugin install <pack>` must consume the
    spy's store at runtime (call recorded; store's `read`/`write` invoked); **(secondary lens)** AST/grep:
    production construction sites limited to `container.py` + `json_plugin_store.py` + the `public_assets`
    default parameter; `container.build_plugin_store()` exists → `PluginStore`-satisfying.
  - `build_plugin_store()` factory (mirror `HarnessProfileStore` wiring); `cli/commands/plugin.py` consumes via
    container (drop the direct adapter import); `FileSystemPublicAssetManager` gains `plugin_store: PluginStore`
    constructor param (default `JsonPluginStore()`), replacing the inline constructions at `:238,344`.
  - Fix the port + CLI docstrings to match (the "never on the adapter directly" claim becomes true).
  - **Byte-lock (AC-5):** plugin goldens (a)/(b) + `test_plugin_projection.py` + `test_plugin_pipeline.py` green,
    **zero golden re-baseline**; `dadaia plugin install/list/doctor` behavior unchanged.
  - **AC-9(a) sabotage (capture → revert):** re-inline `JsonPluginStore()` in `cli/commands/plugin.py`
    (bypass the container) ⇒ the executed-path spy test FAILS (and the secondary AST lens too).
    <!-- AMEND:QA61-1 -->
  - Fate ledger: `test_plugin_cli.py` SURVIVES (adjudicate any construction-seam monkeypatch, don't weaken);
    `test_json_plugin_store.py` SURVIVES verbatim; integration/E2E SURVIVE byte-identical.
  - Gates: ruff format/check, `mypy --strict`, `lint-imports --no-cache` (8/0 — contract lands in W3), full
    unpiped pytest. Commit `refactor(T-61-20): wire PluginStore port through the composition root (A-1)`.

## W3 — cli-no-infrastructure contract (A-2)

- [ ] T-61-30 FR5 — capped import-linter contract + bidirectional cap pin. Owner: software-engineer
  (software-architect countersign at review — ADR-4). Write set: `setup.cfg`,
  `tests/contract/test_import_linter_ignore_cap.py`. Checklist:
  - **Re-enumerate the post-W2 edge set by grep** (expect ≤ 10 sites; SPEC read fact 3 is definition-time truth,
    the implementation grep is the pin). Record each ignore with a one-line rationale comment (F10 pattern).
  - Add `[importlinter:contract:cli-no-infrastructure]` (type `forbidden`; NOT self-referential — the
    import-linter self-referential-forbidden rejection does not apply).
  - Extend the ignore-cap test: new family cap + per-family assertion + stale-above-reality ratchet-down.
  - **AC-6 evidence:** `lint-imports --no-cache` = **9 kept / 0 broken**. **RED probe (capture → revert):** add a
    temporary unrecorded cli→infra import ⇒ contract broken.
  - **AC-9(b)(b′) sabotages (capture → revert):** (b) the RED probe above; (b′) lower the recorded cap by 1 ⇒
    the stale-cap/per-family test FAILS.
  - Fate ledger: `test_import_linter_ignore_cap.py` AMENDED deliberately (recorded); all sibling contracts
    SURVIVE (8 existing contracts untouched).
  - Gates: full gate set green. Commit `feat(T-61-30): cap the cli→infrastructure edge class (A-2)`.

## W4 — hygiene batch (parallel-safe: disjoint write sets)

- [ ] T-61-40 FR6(SE half) — T-1 pytest-10 fixture + CI-1/CI-2 workflow hygiene (RED-first).
  Owner: software-engineer. Write set: `tests/integration/test_telemetry_corrupt_db.py`,
  `.github/workflows/ci.yml`, `.github/workflows/release.yml`, NEW `.github/scripts/bootstrap-panel-ws.sh`,
  NEW `tests/contract/test_ci_workflow_hygiene.py`. Checklist:
  - NEW hygiene contract test FIRST, **RED** on the pre-fix tree: (a) zero `primary_context.json` under
    `.github/workflows/`; (b) both workflows call `.github/scripts/bootstrap-panel-ws.sh`; (c) no inline
    duplicate of the bootstrap body.
  - Extract the 39-line e2e-panel bootstrap (`ci.yml:291-329` ↔ `release.yml:112-150`) to the shared POSIX
    script; delete the `primary_context.json` heredocs (`ci.yml:314-320`, `release.yml:135-141`).
  - T-1: convert the class-scoped instance-method fixture (`TestHandlerDegradedResponses`) per the pytest
    deprecation doc; assertions invariant; full suite → **0 warnings**.
  - **AC-9(c)(e) sabotages (capture → revert):** (c) restore the heredoc in `ci.yml` ⇒ hygiene test FAILS;
    (e) revert the fixture form ⇒ `PytestRemovedIn10Warning` returns (0-warnings gate evidence).
  - Fate ledger: `test_telemetry_corrupt_db.py` AMENDED (form only); e2e-panel legs behavior-invariant — **GHA is
    the proof surface** (local green does not prove the script; watch CI at ship — QA-atom Rich/width law).
  - Gates: full local gate set. Commit `chore(T-61-40): CI bootstrap dedup + legacy state drop + pytest-10 fix`.

- [ ] T-61-41 FR6(ai-engineer half) — D-1 schema property drop + self-repo AGENTS.md hand-sync.
  Owner: ai-engineer. Write set: `public/schemas/memory/memory-frontmatter-v1.schema.json` (+ its contract
  test), `repos/dadaia-workspace/AGENTS.md`. Parallel-safe with T-61-40 (disjoint). Checklist:
  - D-1: remove the expired `agent_tier` property (deprecated v0.1.53; zero carriers verified); pin
    `"agent_tier" not in schema["properties"]` in the schema contract test; propagate via
    `dadaia public stage → install --target all → doctor` (surfaced to PM/operator; `[ok] public-privacy`).
  - Backlog fold: collapse the doubled workspace-law header on `repos/dadaia-workspace/AGENTS.md` to the single
    canonical short header (sanctioned hand-sync — successor to the v0.1.47 T-47-32 exception; the
    `_is_self_repo` fan-out skip is why no install pass ever fixes it). **AC-7 grep:** exactly ONE canonical
    banner block; content otherwise byte-preserved.
  - **AC-9(d) sabotage (capture → revert):** re-add `agent_tier` to the schema ⇒ the contract pin FAILS.
  - Fate ledger: schema contract test AMENDED (adds the absence pin); no atom edits (zero carriers).
  - Gates: full local gate set; `public doctor` exit 0. Commit
    `chore(T-61-41): drop expired agent_tier property + self-repo AGENTS.md header hand-sync`.

## W5 — workspace hygiene + gates + ship

- [ ] T-61-60 FR7 + AC-10 full gates + ship. Owner: software-engineer (gates) + qa-engineer (ship-gate) +
  security-reviewer (push-gate) + operator/PM (shell hygiene). Write set: none in `specs/**`. Checklist:
  - FR7 (operator/PM shell): `dadaia doctor --fix` (clears `.mypy_cache/` + the stale `tauan-games` lease —
    verify, both may be transient-cleared already); surface `bug-space-war` for operator triage (record decision
    or explicit deferral — §6 row 15); delete stale `dist/` contents (D-2); `git mv
    specs/_archive/releases/v0.1.41 → specs/_archive/wip-abandoned/v0.1.41` + one-line README breadcrumb (G-23).
  - **AC-10 gates:** unpiped `pytest` (real exit, **0 warnings**) · `ruff format --check` · `ruff check
    --no-cache` · `mypy --strict` · `lint-imports --no-cache` = **9 kept / 0 broken** · `dadaia specs doctor`
    exit 0 · `dadaia backlog doctor` exit 0 · self-hosting reconcile `public stage → doctor → install --target
    all → doctor` (`[ok] public-privacy`, exit 0). Frozen v0.1.50 no-steal suite **zero-diff**. Zero golden
    re-baseline confirmed (`git diff` on every `_golden/` dir = empty).
  - QA ship-gate APPROVE; security push-gate keyed to the pushed sha; push; **watch CI until every job green** —
    explicitly including the e2e-panel legs exercising the new shared bootstrap script; if `release.yml` does not
    fire on this push (no version bump), record the GHA evidence plan for its leg in the ship notes. PR; merge.
  - *(PE runs no shell — every command above is surfaced to PM/operator; devops-domain routing per plugin-scope
    noted: devops pack not installed in this workspace ⇒ software-engineer owns the YAML under the recorded
    audit-routing exception, or the operator installs the pack first.)*

## W6 — closure (CLOSURE phase)

- [ ] T-61-70 FR8 — CLOSURE.md + memory pass B + disposition sweep + archive. Owner: product-engineer.
  Write set: `specs/releases/v0.1.61/CLOSURE.md`, `specs/memory/**` (pass B), `specs/backlog/**`,
  `specs/audits/**` (mv), `ACTIVE.md`. Checklist:
  - Set `ACTIVE.md` phase = `CLOSURE`. Write CLOSURE.md (Summary, Tasks + SHAs, Validations triples, Drifts,
    Memory updates, **Dispositions = the full 40-row SPEC §6 table with per-row evidence**, Backlog returns,
    Archive decision MOVE).
  - **Memory pass B:** `architecture.md` (enforcement → 9 contracts + cli cap; `build_plugin_store`; wired plugin
    seam; composition-root exception documented), `quality-assurance.md` (shared bootstrap script; no legacy
    state file), `plugin-packs.md` (verify/align seam wording). Catalog regen only if tldr/summary/area change;
    `release_origin` → v0.1.61 on edited atoms. **Order law: memory edits + catalog regen BEFORE ACTIVE.md
    leaves CLOSURE.**
  - **Backlog:** file returns `platform-seam-todo-retirement` (A-3 — new tracked anchor; the audit's cited anchor
    was consumed at R6) + `specs-doctor-partial-archive-invariant` (G-23 doctor gap) via PM curation; mark
    `selfrepo-agents-md-doubled-header` → `DELIVERED — v0.1.61`.
  - **Audit archive (G-20/SPEC-DOC-030/036):** `git mv` both lane reports →
    `specs/audits/_archive/2026-07-06-full-audit-{governance,architecture}-lane--dispositioned-v0.1.61.md`
    (operator/PM), each already carrying the disposing-release reference via this CLOSURE.
  - No open bugs at pick; if any bug was filed mid-release, append its terminal event now (bug-always-solved).
  - **ADR-1 enforcement honesty (ARCH61-3):** <!-- AMEND:ARCH61-3 --> record in CLOSURE.md that the
    operational-change lane is **judgment-enforced only** — human PR review + the reactive next-release
    memory-truth pass; no mechanical gate (doctor/hook) enforces it.
  - **Cross-release closure order (Ruling 61-B):** this release closes FIRST; the SPEC §8 shared-atom
    merge-order clause binds the later-closing siblings (they rebase shared atoms, never revert this closure's
    corrections; catalog regen accumulates prior deltas).
  - `dadaia specs doctor` clean; request `git mv specs/releases/v0.1.61 → specs/_archive/releases/` (operator/
    PM); set `ACTIVE.md` → `release: none` (or per PM's four-release phase schedule).
