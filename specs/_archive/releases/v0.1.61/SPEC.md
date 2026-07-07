# SPEC — v0.1.61 — Audit Remediation & Memory Truth

**Status:** Aprovado
**Branch:** `feature/v0.1.61` (base: post-v0.1.60 `main` @ `4a433063` lineage — the orchestrator branches after `Aprovado`)
**Origin:** Audit-mandated remediation release for the **2026-07-06 full audit** (audit-disposition law,
constitution §7 / `release-governance`): governance lane `specs/audits/2026-07-06-full-audit-governance-lane.md`
(G-1..G-23 + tally extras) + architecture lane `specs/audits/2026-07-06-full-audit-architecture-lane.md`
(A-1..A-3, D-1..D-3, T-1, C-1, CI-1..CI-2, smoke-matrix, noqa-inventory). **Every finding of both lanes receives an
explicit disposition in §6 — no silent drops.** Also consumes backlog `selfrepo-agents-md-doubled-header`
(natural doc-hygiene fold).
**Definition-time inspection** (product-engineer code read, 2026-07-07): every finding this SPEC fixes was
spot-checked against source — audit citations held (see §9 grill corrections for the two that did not hold fully).
**Release-definition grill** (mandatory) run on the picked set before this SPEC; operator unavailable —
code-unanswerable decisions pre-ruled as operator-overridable ADRs (§9).

## 0. PM binding rulings — dual-review fold (2026-07-07)

Dual DEFINITION review returned REJECT (software-architect ARCH61-1..3 + ARCHX-1..3, returned inline to PM;
qa-engineer QA61-1..4 + QAX-1..4 — report
`.dadaia/reports/dadaia-workspace/qa-engineer/2026-07-07T020000Z-v0161-64-definition-review.md`). Every finding
is folded in place with greppable `<!-- AMEND:… -->` markers. PM binding rulings, numbered per release:

- **Ruling 61-A (RULING A — ARCHX-1 + QAX-1 + QA61-3).** <!-- AMEND:ARCHX-1 --> <!-- AMEND:QA61-3 -->
  Implementation order across the parallel-defined set is **FIXED: v0.1.61 → v0.1.62 → v0.1.63 → v0.1.64.**
  File overlaps declared honestly for this release: `cli/commands/plugin.py` + `infrastructure/public_assets.py`
  are written by **v0.1.61 W2 FIRST, THEN v0.1.63 W1** (v0.1.63's rebase clause names v0.1.61 explicitly). The
  12 agent bodies are NOT in this release's write set, but AC-1 pins the tech-stack model table to
  `public/agents/*` frontmatter byte-truth — **the AC-1 frontmatter cross-check is re-run after any sibling
  lands on the agent bodies** (v0.1.62 W3 prose, v0.1.64 W3 `tier:`→`dispatch_band:` rename; the rename does not
  change `model:`/`effort:` values, so the cross-check is expected to hold — verify, don't assume). Any
  undeclared collision discovered mid-wave is a STOP-and-rescope to PM.
- **Ruling 61-B (RULING B — ARCHX-2 + QAX-2).** <!-- AMEND:ARCHX-2 --> CLOSURE sequencing follows the same
  release order (v0.1.61 closes first). §8 carries the shared-atom merge-order clause. `ACTIVE.md` is a single
  pointer — the four releases never hold DEFINITION/CLOSURE phases concurrently; PM owns the phase schedule.
- **Ruling 61-C (RULING C — ARCH61-1 HIGH + ARCH61-2 LOW).** <!-- AMEND:ARCH61-1 --> <!-- AMEND:ARCH61-2 -->
  The §6 disposition table had silently dropped the architecture lane's ERA001/noqa-inventory INFO finding —
  the row is restored as `rejected — clean inventory, all noqa carry rationale, working as designed`; the tally
  becomes **fixed 32 / superseded 1 / deferred 2 / rejected 6 = 41 rows**; the lane split is relabeled
  **governance 28 / architecture 12 / backlog 1**, with the note that the audit's own tally buckets
  under-counted G-19 (filed as a finding, never tallied) and this SPEC restores it to the governance-lane count.
- **Ruling 61-D (RULING D — QA61-1 HIGH, executed-path law).** <!-- AMEND:QA61-1 --> FR4's acceptance is
  upgraded from static-only to an **EXECUTED-PATH test**: a `CliRunner` test spies/monkeypatches
  `container.build_plugin_store` at the composition root and asserts `dadaia plugin list` AND one mutating verb
  (`plugin install`) consume it at runtime, plus the bypass sabotage (construct `JsonPluginStore()` directly in
  `plugin.py` ⇒ the wiring test FAILS). The AST/grep check survives as a **secondary lens** only. Folded into
  FR4, AC-5, AC-9(a).
- **Mechanical folds (no ruling):** QA61-2 per-finding positive greps in AC-1; QA61-4/QAX-4 branch-point
  `pytest --collect-only -q` count pinned in the first implementation wave's fate ledger (PLAN W2 / T-61-20);
  ARCH61-3 (the ADR-1 lane is judgment-enforced only) recorded in CLOSURE task T-61-70; ARCHX-3 sibling
  `self_pull.refs` note in §8.

## 1. Problem

The 2026-07-06 full audit found a **healthy skeleton with stale skin**: zero code CRITICAL/HIGH, but 12 of 29
memory atoms drifted (3 STALE, 9 MINOR-DRIFT) because three production PRs (#112 version-0.2.0+PyPI, #113
README/0.2.1, #115 fable-5 agent retier) landed with `ACTIVE.md = release: none` — no SPEC/PLAN/TASKS and **no
CLOSURE memory pass** (G-18, the root cause of G-1/G-5/G-12). Separately, the architecture lane found one dead
port (A-1 `PluginStore` — zero consumers; its own docstring falsely claims "consumers depend on this Protocol,
never on the adapter directly"), one unguarded erosion class (A-2: 11 `cli → infrastructure` import sites with no
import-linter contract), and a batch of LOW cruft (expired schema promise, stale `dist/`, pytest-10 landmine,
legacy CI state file, duplicated CI bootstrap block).

**Read facts (source, 2026-07-07):**

1. **G-1/G-2 verified byte-precisely.** `specs/memory/tech-stack.md:72-74` still claims "the 9 core agents run on
   `claude-opus-4-8` … no model-cost split"; `:97-102` still says fable-5 is "used by no agent … NEVER pin an
   agent to Fable-5"; the `:104-117` table lists 9× opus. Reality: 5 agents carry `model: claude-fable-5` +
   `effort:` frontmatter (`public/agents/{product-engineer,project-auditor}:high, ai-engineer:medium,
   {software-engineer,qa-engineer}:low`); 4 remain opus (`project-manager`, `software-architect`,
   `security-reviewer`, `code-reviewer`). `tech-stack.md:124` still says `frontend-design` is "Not yet
   distributed … No install command exists yet" — contradicting the same atom's `:76` and the shipped
   `dadaia plugin install` (v0.1.60).
2. **A-1 verified.** `core/protocols/plugin_store.py` has zero importers in production or tests; both consumers
   construct `JsonPluginStore()` directly (`cli/commands/plugin.py:26,81`; `infrastructure/public_assets.py:50,
   238,344`); `container.py` has no plugin factory — but carries 30+ `build_*` factories and the wired
   `HarnessProfileStore` precedent the port explicitly mirrors. Wiring is cheap and consistent.
3. **A-2 verified — 11 sites across 9 CLI modules** (grep 2026-07-07; the audit said 8 modules — re-enumerate at
   implementation): `main.py:37`, `lifecycle.py:1361`, `specs.py:21,25`, `lock.py:13`, `plugin.py:26,27`,
   `context.py:39`, `public.py:47`, `bugs.py:26`, `ci.py:113`. `setup.cfg` has no contract with `cli` as source;
   the existing 8 contracts use `forbidden`/`independence` types with capped ignores pinned by
   `tests/contract/test_import_linter_ignore_cap.py` (26 = 9/4/13) — the F10 pattern this release mirrors.
4. **A-3's tracking claim is stale.** The audit defers the aged `PLATFORM.has_fcntl` TODOs to backlog
   `features-import-infrastructure-direct-debt` — but that anchor was **consumed at R6/v0.1.54** and is gone from
   `specs/backlog/candidates.md`. The deferral needs a NEW tracked return (§9 grill correction).
5. **G-12 verified.** `pyproject.toml:3` = `0.2.1`; `.github/workflows/release.yml` auto-tags + publishes when the
   pyproject version has no tag. No memory atom owns PyPI distribution; `quality-assurance.md` enumerates only
   `ci.yml` + `secret-scan.yml`.
6. **G-23 verified.** `specs/_archive/releases/v0.1.41/` contains only `GRILL.md` + `OQ-DECISIONS.md`.
7. **LINT-1 needs no code change.** `lint-memory-atoms.py:252` loads an optional workspace heading-allowlist file
   from `specs/memory/` — PE-writable in the DEFINITION pass; token estimates are frontmatter values.
8. **`constitution_version` = 2.0.0** (`constitution.md:3`); §15 prices this release's amendment at MINOR → 2.1.0.

## 2. Goals

1. **Memory truth restored** — every stale/contradicted claim across the 12 drifted atoms purged; memory
   describes the post-retier, post-plugin-packs, post-PyPI product atomically (constitution §3: a false memory
   claim is a defect of the same severity as failing code).
2. **PyPI distribution owned in memory** — a new `pypi-distribution` atom + a `quality-assurance.md` workflow
   inventory row (G-12); the SDD-version vs package-version split documented, not renumbered (ADR-2).
3. **The ungated-span root cause closed by law** — constitution §1 amended (MINOR, 2.1.0) with an explicit
   **operational-change lane** defining what may land with `release: none` and what never may (the memory-bearing
   test); PRs #112/#113/#115 ratified post-hoc (ADR-1 / G-18).
4. **The plugin seam made honest** — the `PluginStore` port wired through the composition root (A-1, ADR-3), so
   the memory/docstring claim becomes true instead of deleted.
5. **The cli→infrastructure erosion class capped** — a `cli-no-infrastructure` import-linter contract with
   recorded, ratcheted ignores (A-2, ADR-4).
6. **LOW/INFO debt swept honestly** — pytest-10 fixture, legacy CI state file, duplicated CI bootstrap, expired
   `agent_tier` schema property, self-repo doubled AGENTS.md header, workspace/root hygiene, v0.1.41 archive
   residue — each fixed or explicitly deferred/rejected with reason (§6).
7. **Both audits fully dispositioned and archived** with this release referenced (SPEC-DOC-036), naming
   normalized at archive (G-20).

## 3. Functional requirements

### FR1 — Memory truth pass A (DEFINITION phase; drift describing already-shipped reality)

Owner: product-engineer. Executed while `ACTIVE.md` phase = `DEFINITION` (memory gate), BEFORE implementation
waves — implementers ground on true memory. Each edit is a **dated drift-fix** attributed to the release that
shipped the reality (v0.1.60 precedent), never phrased as a v0.1.61 change. Scope (finding → atom):

- **G-1 + G-5:** `tech-stack.md` §Model assignments rewritten to the 5×fable-5(+`effort:`)/4×opus split; the
  "Reserved entry / NEVER pin" block (:97-102) deleted; the per-agent table corrected; `effort:` frontmatter
  documented. `agent-orchestration.md:96,224` model lines corrected to the same split.
- **G-2 + G-3 + G-4:** all "not yet distributed / no install command exists / only 4 verbs" residue purged —
  `tech-stack.md:124` Plugin-inventory rows rewritten install-gated + a `devops` pack row added;
  `product-vision.md:109-111,171-178` Known-limits updated (12 verbs wired since v0.1.56; packs installable since
  v0.1.60).
- **G-6:** `architecture.md:36` cli roster → 23 subcommands incl. `plugin`.
- **G-7:** `dadaia-workflows.md` availability labels: `implementation` + `closure` = PARTIAL (per
  `governed_catalog.py:677,681` ADR-E vocabulary); the 12-verb invocability claim stands.
- **G-8:** `agent-monitoring.md` refreshed to v0.1.52+ panel truth (open_connection wired; detail route deleted;
  Sessions = dashboard-only — align with `panel.md`).
- **G-9:** `server-registry.md:20` verb roster → `list,next,register,release,show,clean,scan` (phantom
  `unregister` dropped).
- **G-10:** `multi-platform-parity.md` plugin rows gain the install-gated story; heading version bumped.
- **G-11:** `cross-platform-portability.md` completed-follow-up cluster (`:84,92,121-122,155-156,165`) rewritten
  as current truth.
- **G-13..G-16:** `panel.md:185` residue deleted; `public-asset-distribution.md:21-25` gains `plugins` (14 types);
  the G-15 one-liner cluster (`sdd-gate-v3.md:32,154`; `specs-doctor.md:32,88`; `workspace-init.md:9-11,30,63`;
  `brand-identity.md:19`) corrected; `harness-pi.md:40-41` auth claim qualified (`ANTHROPIC_API_KEY` deliberately
  allowlisted — `pi_runtime.py:42-43`).
- **G-17 (INFO polish):** `architecture.md:63` line-count + `workspace_guardrail.py` home module;
  `workspace-doctor.md:37-38` INV-5 prose↔table; `lifecycle-foundation.md:437-439` phrasing;
  `workspace-portability.md:19` flags.
- **LINT-1:** token_estimate frontmatter corrected on the 5 drifted atoms; the 3 flagged headings allowlisted via
  the workspace allowlist file under `specs/memory/` (no code change — read fact 7) or retitled.
- **TREE-5:** `specs/AGENTS.md` reviewed against the canonical template; drift merged.
- Catalog regen (`dadaia memory catalog generate`) only if `tldr`/`summary`/`area` change; regenerated `tldr`
  within the length cap. `release_origin` updated on each edited atom.

### FR2 — NEW memory atom: PyPI distribution (G-12; DEFINITION phase, with FR1)

- NEW `specs/memory/product/distribution/pypi-distribution.md` (area `distribution`; owner product-engineer;
  ADR-2). Content: the published package (`dadaia-workspace` 0.2.x, PyPI-live since PR #112/#113), the
  `release.yml` pipeline (version-vs-tag check job → test legs → tag + build + `pypi-publish` OIDC → single
  ubuntu/py3.12 smoke), the wheel content contract (packs ship in-package — v0.1.60 §6 audit verification), and
  the **version-scheme split**: SDD releases `v0.1.x` version the SDD process; the package `0.2.x` versions the
  shipped library (documented, NOT renumbered — ADR-2).
- `quality-assurance.md`: workflow inventory gains the `release.yml` row (+ a C-1 note: the 80% gate scopes
  unit+contract only; integration-covered modules legitimately read 0% — do not slop-fix).
- Catalog + `index.md` regenerated (new atom).

### FR3 — Constitution amendment: operational-change lane + §13 wording (G-18 + G-19)

- **§1 amended (MINOR — ADR-1):** adds the **operational-change lane**. With `release: none`, ONLY: package
  version metadata bumps, README/docs-only changes, CI-infrastructure fixes, dependency bumps — each still
  requiring an explicit operator order, the sha-keyed security APPROVE push gate, and green CI. **Never
  release-less:** any change that alters agent or product behavior or would require a `specs/memory/**` edit to
  stay true (**the memory-bearing test** — e.g. the #115 agent retier). Any ungated span that nonetheless creates
  memory drift obligates the NEXT release to carry a memory-truth pass. Rejected mechanisms: doctor invariant
  (mechanically undecidable) and mandatory micro-releases (rubber-stamp gates) — ADR-1.
- **§13 wording (PATCH, folded into the same bump):** `product/index.md` described as the **generated catalog
  TOC** (`dadaia memory catalog generate`); vision/users/capability-map/limits live in
  `product/philosophy/product-vision.md` (G-19 — current text claims index.md carries them).
- `constitution_version` 2.0.0 → **2.1.0**. Post-hoc ratification of PRs #112/#113/#115 recorded in this SPEC +
  CLOSURE (mitigants held: operator-ordered, sha-matched security handoffs 5/5 valid, CI green). Constitution
  edits are operator-confirmation-gated: operator unavailable → ADR-1 is operator-overridable and the amendment
  ships only through the operator-reviewed PR (the ratification act).

### FR4 — Wire the `PluginStore` port (A-1; ADR-3 = WIRE, not delete)

- NEW `container.build_plugin_store() -> PluginStore` factory (mirrors the `HarnessProfileStore` precedent).
- `cli/commands/plugin.py` consumes the port via the container (drops `json_plugin_store` direct import — the
  `plugin.py:26` cli→infra edge disappears).
- `infrastructure/public_assets.FileSystemPublicAssetManager` takes a `plugin_store: PluginStore` constructor
  parameter (default `JsonPluginStore()` — same-layer default is legal; the seam is now injectable), replacing
  the 3 inline constructions.
- The port docstring's claim ("consumers depend on this Protocol, never on the adapter directly") becomes TRUE.
- **Machine guard — EXECUTED-PATH primary (Ruling 61-D / QA61-1).** <!-- AMEND:QA61-1 --> The executed-path law
  (quality-assurance.md, v0.1.60) applies: static analysis cannot prove the CLI *reaches* the factory at runtime,
  and the byte-lock goldens cannot discriminate a behavior-preserving refactor. Primary acceptance = a
  `CliRunner` **spy test** in NEW `tests/contract/test_plugin_store_port_wired.py`: monkeypatch/spy
  `container.build_plugin_store` and assert BOTH `dadaia plugin list` and the mutating `dadaia plugin install
  <pack>` consume the spy's store at runtime (call recorded; returned store's `read`/`write` invoked). RED-first:
  FAILS on the current tree (`plugin.py:81` constructs `JsonPluginStore()` directly — the spy is never reached).
  The AST/grep check (production `JsonPluginStore(` construction only in `container.py` +
  `infrastructure/json_plugin_store.py` + the `public_assets` default parameter; `build_plugin_store` returns a
  `PluginStore`-satisfying object) is retained as a **secondary lens** in the same module.
- Behavior-preserving: the v0.1.60 plugin goldens + E2E are the byte-lock; zero golden re-baseline expected.

### FR5 — `cli-no-infrastructure` import-linter contract (A-2; ADR-4)

- NEW `setup.cfg` contract `[importlinter:contract:cli-no-infrastructure]` (type `forbidden`, source
  `dadaia_workspace.cli`, forbidden `dadaia_workspace.infrastructure`), with the **post-FR4 recorded edge set**
  as ignores (≤ 10 edges after `plugin.py:26` is removed by FR4; exact set re-enumerated at implementation —
  read fact 3).
- `tests/contract/test_import_linter_ignore_cap.py` extended: the new family's cap pinned alongside 9/4/13, with
  the same bidirectional falsifiability (cap + stale-above-reality ratchet-down).
- `lint-imports --no-cache` result becomes **9 kept / 0 broken**.
- Adjudication (ADR-4, software-architect countersigns at review): none of the recorded edges is true
  composition-root wiring (`container.py` is the sole composition root) — they are accepted, capped, ratcheted
  debt; edge reduction routes to future container-DI work, not this release.

### FR6 — Code/CI/doc hygiene batch (T-1, CI-1, CI-2, D-1, backlog fold)

- **T-1:** `tests/integration/test_telemetry_corrupt_db.py` class-scoped instance-method fixture converted per
  the pytest deprecation doc; the suite's single `PytestRemovedIn10Warning` disappears (full suite: 0 warnings).
- **CI-1:** the legacy `primary_context.json` heredoc block removed from `.github/workflows/ci.yml:314-320` AND
  `release.yml:135-141` (its only production references are the v1→v2 migration deleter).
- **CI-2:** the 39-line e2e-panel bootstrap block (duplicated verbatim `ci.yml:291-329` ↔ `release.yml:112-150`)
  extracted to `.github/scripts/bootstrap-panel-ws.sh`, called from both (kills the hand-synced-copy family).
  NEW contract test `tests/contract/test_ci_workflow_hygiene.py`: (a) zero `primary_context.json` occurrences
  under `.github/workflows/`; (b) both workflows reference the shared bootstrap script; (c) no inline duplicate
  of its body. RED-first on the current tree.
- **D-1:** the expired `agent_tier` property dropped from
  `public/schemas/memory/memory-frontmatter-v1.schema.json` (deprecated v0.1.53, zero carriers among all atoms —
  verified by the audit). ai-engineer via the public-asset flow (stage → install → doctor). A schema contract
  assertion pins `"agent_tier"` absent.
- **Backlog fold — `selfrepo-agents-md-doubled-header`:** sanctioned hand-sync of
  `repos/dadaia-workspace/AGENTS.md` collapsing the doubled workspace-law header to the single canonical short
  header (documented successor to the v0.1.47 T-47-32 exception; the `_is_self_repo` fan-out skip means only a
  hand-sync can fix it). Owner: ai-engineer (AGENTS.md law surface).

### FR7 — Workspace + archive hygiene (G-21, G-22, G-23, D-2)

- **G-21/G-22:** `dadaia doctor --fix` clears `.mypy_cache/` (ROOT) + the stale `tauan-games` lease (LOCK-GC =
  SPEC-DOC-029; transient — verify, may already be clear). The `bug-space-war` root entry is **operator triage**
  (operator-created → `root_exceptions.txt`; else relocate) — deferred to the operator in §6, surfaced at ship.
- **G-23:** the `v0.1.41` residue (`GRILL.md` + `OQ-DECISIONS.md` only) relocated via `git mv` (operator/PM —
  `_archive` is FROZEN for file tools) to `specs/_archive/wip-abandoned/v0.1.41/` with a one-line README naming
  the abandonment (v0.1.40-42 rescue, see v0.1.43). The doctor-coverage-gap INFO (partial archived release dirs)
  is **deferred** → backlog return `specs-doctor-partial-archive-invariant`.
- **D-2:** the stale local `dist/` artifacts (2026-06-07, pre-OpenCode-deletion metadata) deleted at the gates
  wave (operator/PM shell — gitignored, not a repo change; evidence: `dist/` absent or rebuilt-fresh).

### FR8 — Memory truth pass B (CLOSURE phase; claims made true BY this release) + disposition sweep

- `architecture.md`: enforcement section → 9 contracts incl. `cli-no-infrastructure` + its cap; dependency-rules
  section documents the capped cli→infra exception; `container.py` gains `build_plugin_store`; the plugin seam
  described as wired (port consumed via composition root).
- `quality-assurance.md`: CI workflow notes updated (shared bootstrap script; no legacy state file).
- `plugin-packs.md`: seam claim verified — now true as written (edit only if wording implies direct-adapter use).
- Constitution/memory coherence re-checked (`specs doctor` LINT-1 clean; catalog regen if needed).
- **Disposition sweep (ADR-11 vocabulary):** the §6 table executed — both audit files archived to
  `specs/audits/_archive/` with normalized names referencing v0.1.61 (G-20; SPEC-DOC-036);
  `selfrepo-agents-md-doubled-header` → `DELIVERED — v0.1.61`; NEW backlog returns filed
  (`platform-seam-todo-retirement` for A-3, `specs-doctor-partial-archive-invariant` for the G-23 doctor gap);
  0 open bugs at pick → no bug terminal events expected (any bug found mid-release follows bug-always-solved).

## 4. Non-goals

- **No agent model/tier change** — the #115 retier is ratified and documented, not revisited; no `model:` edits.
- **No renumbering** of SDD releases to package versions (ADR-2 documents the split).
- **No cli→infra edge elimination beyond FR4** — the contract caps the class; DI cleanup is future work.
- **No `PLATFORM.has_fcntl` TODO retirement** (A-3 — touches lease/locking code adjacent to the frozen v0.1.50
  no-steal suite; deferred with a tracked return).
- **No new doctor invariants** (the partial-archive check is a tracked return; the G-18 lane is law, not a check).
- **No pack content, no plugin uninstall, no panel/lifecycle/gate behavior change.** The frozen v0.1.50 no-steal
  suite is expected **zero-diff**.
- **No `.github/workflows` behavior change beyond CI-1/CI-2** (same steps, deduplicated + de-crufted).

## 5. Acceptance criteria

- **AC-1 (memory truth — greppable, negative AND positive):** <!-- AMEND:QA61-2 -->
  **Negative greps** — zero hits in `specs/memory/**` for the retired claims: "Not yet distributed", "No install
  command exists", "no install command exists yet", "only 4 workflow verbs" / "Only 4 … verbs", "the 9 core
  agents run on `claude-opus-4-8`", the "NEVER pin an agent to Fable-5" reserved block, "22 subcommands",
  "`unregister`" (server-registry roster). `tech-stack.md` model table = 5 fable-5 (+effort) / 4 opus / 3
  plugin-sonnet rows, matching `public/agents/*` frontmatter byte-truth (re-run after any sibling lands on the
  agent bodies — Ruling 61-A).
  **Positive greps (per-finding, same AC-1 transcript — QA61-2):** G-6 `architecture.md` contains "23
  subcommands" AND names `plugin` in the cli roster; G-7 `dadaia-workflows.md` contains exactly 2 "PARTIAL"
  availability labels (`implementation`, `closure`); G-8 `agent-monitoring.md` states the aggregate-only
  `/api/sessions` + dashboard-only Sessions tab (no detail route); G-10 `multi-platform-parity.md` names
  `dadaia plugin install`; G-11 `cross-platform-portability.md` names the cross legs
  `unit-fast-cross`/`contract-coverage-cross` and carries no "still exist / tracked in backlog" residue for the
  completed follow-ups; G-13 `panel.md` has zero "Mermaid remains loaded" hits; G-14
  `public-asset-distribution.md` lists `plugins` among the asset types (14); G-15 `sdd-gate-v3.md` names
  `features/spec_context/lease.py`; G-16 `harness-pi.md` contains the `ANTHROPIC_API_KEY` allowlist
  qualification; G-17 `workspace-doctor.md` INV-5 prose matches its table (AUTO-FIX). Each captured in the AC-1
  transcript.
- **AC-2 (LINT-1/TREE-5 clean):** `dadaia specs doctor` exit 0 with zero LINT-1 token_estimate/heading warnings
  and zero TREE-5 warning; SPEC-DOC-027/029/031 accepted-debt classes may remain (dispositioned §6).
- **AC-3 (PyPI atom):** `pypi-distribution.md` exists with valid frontmatter, in `catalog.json` + `index.md`;
  documents 0.2.x, `release.yml`, and the version split; `quality-assurance.md` carries the `release.yml` row +
  the C-1 note.
- **AC-4 (constitution):** `constitution_version: 2.1.0`; §1 carries the operational-change lane incl. the
  memory-bearing test; §13 matches the generated-index reality; `specs doctor` SPEC-DOC-028 + the
  no-roster-enumeration check stay green.
- **AC-5 (A-1 wired — EXECUTED-PATH, RED-first — Ruling 61-D):** <!-- AMEND:QA61-1 --> the
  `test_plugin_store_port_wired.py` **spy test** proves at runtime that `dadaia plugin list` and
  `dadaia plugin install` reach `container.build_plugin_store` (CliRunner + composition-root monkeypatch);
  it FAILS pre-fix (direct `JsonPluginStore(` in `cli/commands/plugin.py` bypasses the spy). The AST/grep
  secondary lens passes too. `dadaia plugin install/list/doctor` behavior unchanged: v0.1.60 plugin goldens
  (a)/(b) + `test_plugin_pipeline.py` E2E green with **zero golden re-baseline**.
- **AC-6 (A-2 contract — bidirectionally falsifiable):** `lint-imports --no-cache` = **9 kept / 0 broken**; the
  new family's ignore cap pinned in `test_import_linter_ignore_cap.py`; adding an unrecorded cli→infra import
  breaks the contract (RED probe); lowering the recorded cap below reality fails the stale-cap test.
- **AC-7 (hygiene batch):** full unpiped `pytest` shows **0 warnings** (T-1); `test_ci_workflow_hygiene.py`
  passes post-fix, FAILS pre-fix (CI-1/CI-2); the memory-frontmatter schema carries no `agent_tier` (D-1);
  `repos/dadaia-workspace/AGENTS.md` has exactly ONE workspace-law header block (grep: one occurrence of the
  canonical banner line).
- **AC-8 (workspace/archive hygiene):** workspace doctor shows no ROOT cache issue and no stale `tauan-games`
  lease; `specs/_archive/releases/v0.1.41/` no longer exists (residue relocated with README breadcrumb);
  `bug-space-war` triage recorded (operator decision or explicitly deferred at ship).
- **AC-9 (mutation-sanity — per new test, sabotage → FAIL → revert, captured on the task line):** (a) re-inline
  `JsonPluginStore()` in `cli/commands/plugin.py` (bypass the container) ⇒ the AC-5 **executed-path spy test**
  FAILS (and the secondary AST lens too) <!-- AMEND:QA61-1 -->; (b) add an unignored cli→infra import ⇒
  AC-6 contract breaks; (b′) drop one recorded ignore edge from the cap constant ⇒ stale-cap test FAILS; (c)
  restore the `primary_context.json` heredoc in `ci.yml` ⇒ AC-7 hygiene test FAILS; (d) re-add `agent_tier` to
  the schema ⇒ the D-1 pin FAILS; (e) revert the T-1 fixture ⇒ the 0-warnings gate FAILS.
- **AC-10 (full gates):** `ruff format --check`, `ruff check --no-cache`, `mypy --strict`, full **unpiped**
  `pytest` (real exit, 0 warnings), `lint-imports --no-cache` (9 kept / 0 broken), `dadaia specs doctor` exit 0,
  `dadaia backlog doctor` exit 0, `dadaia public stage → doctor → install --target all → doctor`
  (`[ok] public-privacy`, exit 0 — required by D-1's schema edit + the FR6 hand-sync). Frozen v0.1.50 no-steal
  suite zero-diff. CI watched until every job green (incl. the modified e2e-panel bootstrap on BOTH workflows —
  CI-2's script must prove itself on GHA, not just locally).
- **AC-11 (disposition completeness):** every row of §6 lands in CLOSURE `## Dispositions` with evidence; both
  audit files archived referencing v0.1.61; the two new backlog returns exist; no finding row left blank.

## 6. Disposition table (audit-disposition law — every finding, no silent drops)

<!-- AMEND:ARCH61-2 --> Governance lane (**28** tally rows — the audit's own tally buckets under-counted G-19,
filed as a finding but never tallied; this SPEC restores it) + architecture lane (**12** rows) + backlog fold
(**1** row) = **41 rows**.

| # | Finding | Sev | Disposition | Where |
|---|---|---|---|---|
| 1 | G-1 tech-stack model claims | HIGH | **fixed** | FR1 (T-61-10) |
| 2 | G-2 plugin-inventory contradiction | HIGH | **fixed** | FR1 |
| 3 | G-3 product-vision install stale | HIGH | **fixed** | FR1 |
| 4 | G-4 product-vision 4-verbs stale | HIGH | **fixed** | FR1 |
| 5 | G-18 ungated operational span | HIGH | **fixed** (lane law + post-hoc ratification + this memory pass) | FR3 + ADR-1 |
| 6 | G-5 agent-orchestration model lines | MED | **fixed** | FR1 |
| 7 | G-6 architecture 22→23 subcommands | MED | **fixed** | FR1 |
| 8 | G-7 workflows availability labels | MED | **fixed** | FR1 |
| 9 | G-8 agent-monitoring stale ×3 | MED | **fixed** | FR1 |
| 10 | G-9 server-registry verb roster | MED | **fixed** | FR1 |
| 11 | G-10 multi-platform-parity coverage | MED | **fixed** | FR1 |
| 12 | G-11 cross-platform completed follow-ups | MED | **fixed** | FR1 |
| 13 | G-12 PyPI memory coverage missing | MED | **fixed** | FR2 (new atom + QA row) |
| 14 | G-19 constitution §13 index claim | MED | **fixed** (PATCH wording) | FR3 |
| 15 | G-21 root hygiene (.mypy_cache; bug-space-war) | MED | **fixed** (cache via `doctor --fix`) + **deferred** (bug-space-war → operator triage; human-judgment root entry) | FR7 |
| 16 | G-23 v0.1.41 archive residue | MED | **fixed** (residue relocated + README) | FR7 |
| 17 | G-13 panel.md Mermaid residue | LOW | **fixed** | FR1 |
| 18 | G-14 public-asset-distribution 13→14 types | LOW | **fixed** | FR1 |
| 19 | G-15 stale-claim cluster (sdd-gate/specs-doctor/workspace-init/brand) | LOW | **fixed** | FR1 |
| 20 | G-16 harness-pi auth claim | LOW | **fixed** (qualified) | FR1 |
| 21 | G-22 stale tauan-games lease | LOW | **fixed** (`doctor --fix`; transient) | FR7 |
| 22 | TREE-5 + LINT-1 (specs/AGENTS.md drift; estimates/headings) | LOW | **fixed** | FR1 |
| 23 | G-17 polish cluster (INFO) | INFO | **fixed** (folded) | FR1 |
| 24 | G-20 audit naming convention | INFO | **fixed** (normalized at archive) | FR8 |
| 25 | LOCK-5 BLOCKED_ATTEMPT telemetry | INFO | **rejected** — historical signal, working as designed; no action (auditor concurs) | — |
| 26 | Doctor gap: partial archived release dirs | INFO | **deferred** — small new invariant, out of an already-wide release; tracked return `specs-doctor-partial-archive-invariant` | FR8 return |
| 27 | SPEC-DOC-027 legacy release dir names ×2 | INFO | **rejected** — accepted debt by prior ruling ("preserved until renamed"); renaming archived dirs breaks history links | — |
| 28 | SPEC-DOC-031 ×9 backlog returns flagged | INFO | **rejected** — known false-positive class (ADR-6): the 9 are the deliberately-live returns enumerated in ACTIVE.md | — |
| 29 | A-1 dead `PluginStore` port | MED | **fixed** (WIRED via composition root) | FR4 + ADR-3 |
| 30 | A-2 unguarded cli→infra edges (11 sites) | MED | **fixed** (capped contract) | FR5 + ADR-4 |
| 31 | A-3 aged `PLATFORM.has_fcntl` TODOs | LOW | **deferred** — touches lease/locking adjacent to the frozen no-steal suite; risk ≫ value here. Grill correction: the audit's "already tracked" is FALSE (anchor consumed at R6) → NEW tracked return `platform-seam-todo-retirement` | FR8 return |
| 32 | D-1 expired `agent_tier` schema property | LOW | **fixed** (dropped; zero carriers) | FR6 |
| 33 | D-2 stale local `dist/` | LOW | **fixed** (deleted at gates wave; operator shell; gitignored artifact) | FR7 |
| 34 | D-3 mid-audit cache pollution | LOW | **superseded** — folded into G-21 cleanup + the existing repo-cleanliness law; no distinct action | row 15 |
| 35 | T-1 pytest-10 fixture landmine | LOW | **fixed** | FR6 |
| 36 | CI-1 legacy `primary_context.json` bootstrap write | LOW | **fixed** | FR6 |
| 37 | CI-2 duplicated 39-line bootstrap block | LOW | **fixed** (shared script) | FR6 |
| 38 | C-1 coverage-gate blind spot | INFO | **rejected** — working as designed (gate scopes unit+contract; integration covers the 0% rows); durable note added to `quality-assurance.md` so nobody slop-fixes it | FR2 note |
| 39 | Smoke-matrix range (`^3.12` vs tested 3.12) | INFO | **rejected** — the classifier list (3.12 only) is the honest claim surface; narrowing the range punishes 3.13 users with no breakage evidence; revisit only with a 3.13 CI leg | — |
| 40 | ERA001/noqa inventory (arch lane INFO) <!-- AMEND:ARCH61-1 --> | INFO | **rejected** — clean inventory, all noqa carry rationale, working as designed | — |
| 41 | `selfrepo-agents-md-doubled-header` (backlog fold) | LOW | **fixed** (sanctioned hand-sync) → `DELIVERED — v0.1.61` | FR6 |

Tally <!-- AMEND:ARCH61-1 -->: **fixed 32 · superseded 1 · deferred 2 (each with reason + tracked return/owner)
· rejected 6 (each with reason) = 41 rows** <!-- AMEND:ARCH61-1-reverify: per-row recount fixed 32/rejected 6 -->. (Row 15 counts as fixed with a recorded operator-deferred residual.)

## 7. Risks

- **Memory pass regressing fresh atoms (FR1).** 17/29 atoms are fresh — edits scoped strictly to the cited
  lines/claims; catalog regen only on tldr/summary/area change; `specs doctor` + LINT-1 as the backstop.
- **Constitution amendment overreach (FR3).** The lane could accidentally license behavior changes. Mitigation:
  the memory-bearing test is the hard boundary and #115 is named as the counter-example inside the article;
  operator ratifies via the PR (ADR-1 overridable).
- **A-1 wiring changes plugin behavior (FR4).** Mitigation: constructor-default injection (no call-site behavior
  change); the v0.1.60 goldens + E2E byte-lock; zero-golden-re-baseline is an explicit AC.
- **A-2 cap drift between definition and implementation (FR5).** My grep says 11 sites/9 modules; FR4 removes ≥1.
  Mitigation: the task re-enumerates at implementation truth and pins THAT set (never the SPEC's count).
- **CI-2 script breaks only on GHA (Rich/width/env class).** Mitigation: AC-10 requires watching BOTH workflows'
  e2e-panel legs green on GHA; `release.yml`'s leg fires on the version-bump push — if no version bump occurs
  this release, evidence is the `workflow_dispatch`/next-run watch, recorded at ship.
- **Frozen-suite adjacency.** No lease/gate path is entered (A-3 deferred for exactly this reason). Expect
  zero-diff on the v0.1.50 no-steal suite.
- **Parallel-release collision (QA61-3).** <!-- AMEND:QA61-3 --> v0.1.63 W1 writes the same
  `cli/commands/plugin.py` + `infrastructure/public_assets.py`; v0.1.62/64 rewrite the agent bodies AC-1
  cross-checks against. Governed by Ruling 61-A (fixed order; this release lands FIRST; siblings rebase; the
  AC-1 frontmatter cross-check re-runs after each sibling). Any undeclared overlap = STOP-and-rescope to PM.

## 8. Memory files affected

- **DEFINITION (pass A, FR1+FR2):** `tech-stack.md`, `product-vision.md`, `agent-orchestration.md`,
  `architecture.md`, `dadaia-workflows.md`, `agent-monitoring.md`, `server-registry.md`,
  `multi-platform-parity.md`, `cross-platform-portability.md`, `panel.md`, `public-asset-distribution.md`,
  `sdd-gate-v3.md`, `specs-doctor.md`, `workspace-init.md`, `brand-identity.md`, `harness-pi.md`,
  `workspace-doctor.md`, `lifecycle-foundation.md`, `workspace-portability.md`, NEW `pypi-distribution.md`,
  `quality-assurance.md`, the workspace heading-allowlist file, `specs/AGENTS.md` (TREE-5), catalog + index regen.
- **CLOSURE (pass B, FR8):** `architecture.md` (contract #9 + port wiring + composition-root exception),
  `quality-assurance.md` (CI notes), `plugin-packs.md` (verify/align seam wording).
- `specs/constitution.md` (FR3 — amendment, operator-ratified at PR).
- **Shared-atom merge order (Ruling 61-B / RULING B — ARCHX-2 + QAX-2):** <!-- AMEND:ARCHX-2 --> shared with
  siblings: `quality-assurance.md` (v0.1.61 ×2 passes, v0.1.62, v0.1.64), `tech-stack.md` (v0.1.61, v0.1.64),
  `architecture.md` (v0.1.61, v0.1.62 assess, v0.1.63), `public-asset-distribution.md` (v0.1.61 pass A, v0.1.62,
  v0.1.63), `agent-orchestration.md` (v0.1.61 pass A, v0.1.64), `plugin-packs.md` (v0.1.61 pass B, v0.1.63).
  **PM sequences CLOSURE in release order; the later-closing release REBASES each shared atom on the sibling's
  closed state (never reverts a sibling's correction); every `catalog.json` regen includes all prior
  tldr/summary deltas.**
- **Sibling note (ARCHX-3):** <!-- AMEND:ARCHX-3 --> once v0.1.62 ships, agent handoffs emitted during this
  release's later phases carry `handoff-v1.2` + `self_pull.refs` per the updated instruction surfaces.

## 9. Definition rulings (grill, operator unavailable — OPERATOR-OVERRIDABLE)

- **ADR-1 — G-18 mechanism = constitution §1 operational-change lane (MINOR amendment), not a doctor invariant,
  not micro-releases.** The lane: `release: none` may carry ONLY version-metadata bumps, docs/README, CI-infra
  fixes, dependency bumps — always operator-ordered + sha-keyed security APPROVE + green CI; NEVER anything
  failing the **memory-bearing test** (would a `specs/memory/**` edit be required for memory to stay true? then
  it needs a release — the #115 retier is the named counter-example). An ungated span that still causes drift
  obligates the next release's memory-truth pass. **Rejected:** doctor invariant — "memory-bearing" is
  mechanically undecidable (the doctor cannot judge semantics; a version-diff heuristic would false-block docs
  and false-pass retiers); mandatory micro-releases — rubber-stamp SPEC/PLAN/TASKS for a README comma is gate
  theater that trains gate-bypassing. PRs #112/#113/#115 ratified post-hoc (mitigants recorded). **Override:**
  operator picks the doctor-heuristic or micro-release regime, or narrows/widens the lane list.
- **ADR-2 — G-12: NEW `pypi-distribution.md` atom (distribution area, PE-owned) + QA-atom row; the SDD-vs-package
  version split is DOCUMENTED, not renumbered.** Renumbering SDD releases to 0.2.x would falsify archived history
  and break tag/PR continuity for zero information gain; the split is honest and now stated in one owned place.
  **Override:** align SDD release ids to package versions starting v0.2.2.
- **ADR-3 — A-1: WIRE the port (container `build_plugin_store` + constructor injection), don't delete.** Read
  facts: the container is the declared sole composition root with 30+ `build_*` factories and the wired
  `HarnessProfileStore` precedent this port explicitly mirrors; memory (`plugin-packs.md`, `architecture.md`) and
  the port docstring already sell the seam; wiring cost ≈ one factory + one parameter + one import swap, behavior
  byte-locked by the v0.1.60 goldens. Deleting would demote a correct published architecture to concrete coupling
  and force memory de-selling. **Override:** delete `core/protocols/plugin_store.py` + correct the two atoms.
- **ADR-4 — A-2 contract shape: `forbidden` contract `cli-no-infrastructure` with the post-FR4 edge set as capped
  ignores + cap pinned bidirectionally in `test_import_linter_ignore_cap.py` (the F10 pattern).** Adjudication:
  ZERO of the current edges is legitimate composition-root wiring (that is `container.py`'s monopoly); all are
  accepted pragmatic debt — capped so the class stops growing silently (v0.1.60 added 2 unnoticed), ratcheted
  down opportunistically. `architecture.md` documents the cap at CLOSURE. software-architect countersigns at the
  definition/trio review. **Override:** declare cli→infra a legal uncapped edge in `architecture.md` instead.
- **ADR-5 — Disposition split (§6):** LOW/INFO fixed here only when the fix is cheap AND self-verifying (T-1,
  CI-1/2, D-1, D-2, G-13..G-17, backlog fold); deferred ONLY with a tracked return (`platform-seam-todo-retirement`
  — A-3, frozen-suite adjacency; `specs-doctor-partial-archive-invariant` — G-23 gap) or a named owner
  (bug-space-war → operator); rejected only where acting would be dishonest or destructive (naming/renumbering
  history, false-positive classes, working-as-designed signals). **Override:** operator promotes any deferred row
  into scope.
- **ADR-6 — Memory-pass sequencing: pass A at DEFINITION, pass B at CLOSURE.** Pass A corrects drift describing
  ALREADY-SHIPPED reality (dated drift-fixes, v0.1.60 precedent) so implementation waves ground on true memory;
  pass B lands only claims made true BY this release (contract #9, port wiring). Both phases are gate-legal for
  MEMORY writes. **Override:** single CLOSURE pass.
- **Grill corrections (dossier/audit vs source):** (1) A-3's "tracked in backlog `features-import-…-debt`" is
  stale — that anchor was consumed at R6/v0.1.54; the deferral files a NEW return. (2) A-2's "8 modules" is 9 by
  the 2026-07-07 grep (11 sites); implementation re-enumerates. (3) LINT-1 heading fixes need no code change —
  the workspace allowlist file under `specs/memory/` is the mechanism (`lint-memory-atoms.py:252`).
