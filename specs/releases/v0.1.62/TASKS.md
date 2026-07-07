# TASKS — v0.1.62 — Injection Contract & Fan-out Containment

**Status:** Aprovado

Markers: `[ ]` open · `[-]` in progress · `[x]` done. W1 → W2 → W3 strictly sequential (version-token chain).
**Declared safe parallelism:** T-62-40 (W4) ∥ T-62-50 (W5a) — disjoint write sets
(`infrastructure/workspace_guardrail.py` + its new test vs `tests/e2e/panel/response-guard.spec.ts`), different
owners, at most one `[-]` per owner. Every implementation-wave task: **NO `specs/backlog/**` paths staged**
(dispositioned at CLOSURE — T-62-70). Every version-token grep includes `tests/` AND non-import textual references.
AC-10 mutation-sanity: each sabotage → shown to FAIL → reverted, captured on the task line. Three sibling releases in
flight under the FIXED order **v0.1.61 → v0.1.62 → v0.1.63 → v0.1.64** (Ruling 62-A): declared overlaps are
sequenced (the 12 agent bodies: this release's W3 FIRST, then v0.1.63 W2/W3 frontmatter, then v0.1.64 W3 rename);
any UNdeclared collision = STOP-and-rescope to PM. <!-- AMEND:ARCHX-1 -->

## W0 — definition

- [x] T-62-01 SPEC/PLAN/TASKS authored from the 2026-07-07 **code read** (not a dossier restatement): the schema is
  ALREADY `$id: handoff-v1.1` → the real bump is **v1.2**; the stdlib validator has no `if`/`then` → service-layer
  conditional; `_detect_sidecar_version` misroutes v1.2 → v1.0 compat hard-error (latent bug, FR2); `gates.py` +
  `runtime_files.py` accept-set pins; `ROLE_ATOM_MAP` unreachable from `features/reports` → `core` relocation;
  `_consumer_repos_for_root` joins `repo_slug` verbatim + `shutil.copy2` follows dst symlinks; CI `ln -sfn` proves
  symlinked consumer DIRS are legit; the e2e fixture deterministically seeds ≥1 context (ci.yml:291-326) → the
  graceful-empty branch dies. Mandatory release-definition grill run on the picked set (inspection-first).
  **ADRs recorded (§9, operator unavailable — overridable):** ADR-1 token v1.2; ADR-2 transition + service-layer
  conditional; ADR-3 `self_pull.refs` + existence + role-map coverage; ADR-4 core map relocation w/ re-export;
  ADR-5 L2 refs reuse + honest v1.1 zero-refs fallback; ADR-6 slug-reject AND containment assert; ADR-7 refuse
  dst-file symlinks / allow dir symlinks; ADR-8 chip required, empty branch removed; ADR-9 trusted-input override
  DECLINED (PM retier). **Dual-review fold (2026-07-07, REJECT):** QA62-1..5 + ARCHX/QAX folded with
  `<!-- AMEND:… -->` markers; PM Rulings 62-A/62-B/62-E recorded in SPEC §0 (fixed order + honest overlap
  enumeration replacing the deleted "disjoint by construction" claim; shared-atom closure merge order; HIGH bug
  `reports-sidecar-version-detection-misroutes-future-tokens` CONSUMED — AC-4 = its repro verbatim, terminal
  event at T-62-70). `Aprovado` after re-verify; definition commit. Owner: product-engineer (orchestrated).

## W1 — FR1/FR2 schema bump + validator (golden-first → RED-first)

- [x] T-62-10 **AC-1 back-compat corpus lock FIRST.** Owner: software-engineer. Write set: NEW
  `tests/unit/features/reports/test_handoff_v12_validation.py` (corpus-lock section only). Checklist:
  - Collect every in-tree v1/v1.1 handoff fixture + transcribe the emitter-skill v1.1 example as a fixture; assert
    each passes `ReportsValidationService.validate_file` (hash checks stubbed/absent-path variants as today).
  - **First implementation wave (QAX-4):** pin the branch-point `pytest --collect-only -q` count in this task's
    fate ledger (re-validated at closure). <!-- AMEND:QAX-4 -->
  - Commit BEFORE any schema/service edit. Precondition for T-62-11. Done: green on the pre-bump tree.
  - **Evidence (2026-07-07):** corpus = 5 fixtures (tree carries NO committed `*.handoff.json` — corpus is the
    fixture docs embedded in tests + the emitter skill): `v1-minimal-report` (test_cli_reports.py),
    `v1-no-artifact-path` (test_reports_validation_service.py), `v1.1-contract-full`
    (test_handoff_schema_contract.py), `v1.1-skill-handoff-only` + `v1.1-skill-with-report` (SKILL.md examples
    transcribed; report-mode hash recomputed against a materialized artifact — literal skill hash is
    illustrative). Real `StdlibHandoffValidator` + real public schema; 6 tests (5 parametrized + validate_all
    sweep) GREEN on the pre-bump tree (`6 passed`). **QAX-4 branch-point collect count pin:
    `pytest --collect-only -q` = 4701 tests collected** (at HEAD 52606197, pre-corpus-file; re-validate at
    closure).

- [x] T-62-11 Schema bump + map relocation + conditional validator + detection fix. Owner: software-engineer.
  Preconditions: T-62-10 committed. Write set: `public/schemas/handoff-v1.schema.json`,
  `features/reports/validation.py`, `cli/commands/reports.py`, NEW `core/role_atom_map.py`,
  `features/lifecycle/role_atoms.py` (re-export ONLY), `tests/unit/features/reports/test_handoff_v12_validation.py`.
  Checklist:
  - Schema: `$id`/`title` → v1.2; enum += `"handoff-v1.2"`; optional `self_pull` (`required: ["refs"]`, `minItems: 1`,
    no-traversal item pattern) — **whitelisted keywords only** (stdlib validator must construct unchanged).
  - NEW `core/role_atom_map.py` (pure dict, stdlib-only); `role_atoms.py` imports + re-exports `ROLE_ATOM_MAP`
    (same name — grep proves the three Layer-2 surfaces + tests keep importing from `role_atoms`).
  - `validation.py`: v1.2 ⇒ `self_pull` required (`HandoffValidationError("self_pull", ...)`); refs existence
    (`repos/<context>/<ref>` → `<workspace>/<ref>`, `_within_workspace`-guarded; fail-soft when workspace root is
    None); role-map coverage for mapped agents (import from `core` — NO cross-feature edge).
  - `reports.py#_detect_sidecar_version`: v1.2 = modern; never routes to `_check_v10_compat`.
  - Tests: AC-2 (RED-first staged: enum-reject pre-FR1 → conditional-fire post-FR2) — **the 4-case version
    matrix as ONE named parametrized test `test_schema_version_matrix` (v1 ✓ / v1.1 ✓ / v1.2+self_pull ✓ /
    v1.2−self_pull ✗; QA62-5)** <!-- AMEND:QA62-5 -->, AC-3(a)(b)(c), AC-4 (**RED-first = the picked bug's
    recorded repro VERBATIM: v1.2 sidecar → `dadaia reports validate` → v1.0-compat `findings[]` hard error;
    Ruling 62-E**) <!-- AMEND:QA62-1 -->. AC-1 corpus lock still green (transition proven).
  - **Mutation-sanity NOW:** AC-10(a) drop the conditional ⇒ AC-2 FAILS; AC-10(b) skip existence ⇒ AC-3(a) FAILS;
    AC-10(c) skip coverage ⇒ AC-3(b) FAILS; AC-10(d) revert detection ⇒ AC-4 FAILS — each captured here, reverted.
  - Fate ledger (file-enumerated): existing reports/CLI/stdlib-validator tests SURVIVE (v1.1 accepted); any test
    pinning unknown-token rejection amended-with-rationale; `lint-imports` 8/0, ignore-cap UNCHANGED. Done: gates
    green (ruff, mypy --strict, unpiped pytest).
  - **Evidence (2026-07-07):** AC-2 staged RED: stage-1 (pre-FR1) v1.2−self_pull failed ONLY on enum
    (`'handoff-v1.2' is not one of ['handoff-v1', 'handoff-v1.1']`); stage-2 (post-FR1, pre-FR2) same doc passed
    schema-blind (`validator errors == []`); post-FR2 the `self_pull`-pathed conditional fires.
    `test_schema_version_matrix` = ONE named parametrized 4-case test (v1 ✓ / v1.1 ✓ / v1.2+self_pull ✓ /
    v1.2−self_pull ✗). AC-3(a) indexed `self_pull.refs[1] ref does not exist` + repos/<context> resolution +
    fail-soft (root None) tests; AC-3(b) qa-engineer coverage miss fails / software-engineer unmapped passes;
    AC-3(c) `..`/absolute refs rejected by the schema pattern (`self_pull.refs[0]` pattern error). AC-4 RED
    (bug repro VERBATIM, pre-fix): `dadaia reports validate <v1.2 sidecar>` → exit 1,
    `ERROR: Missing required field 'findings[]'. This sidecar appears to be v1.0 and is incompatible with
    v1.1.`; post-fix same sidecar (no findings[]) exits 0, `1 valid`. `StdlibHandoffValidator` constructs
    UNCHANGED against the v1.2 schema (whitelisted keywords only). Map relocation grep: consumers
    (`fragment_coherence_doctor`, `role_atoms` helpers, `test_role_atoms_injection`,
    `test_fragment_coherence_doctor`) all still import via `role_atoms`; re-export is the SAME object
    (identity-asserted test). **Mutation-sanity AC-10:** (a) drop conditional ⇒
    `test_schema_version_matrix[v1.2-without-self_pull-fails]` FAILED; (b) `if False` existence ⇒
    `test_v12_nonexistent_ref_fails_with_indexed_evidence` FAILED; (c) `mapped = None` coverage ⇒
    `test_v12_mapped_agent_missing_its_atom_fails_coverage` FAILED; (d) detection reverted to v1.1-only ⇒
    `test_v12_sidecar_never_routes_to_v10_compat_cli` FAILED (exit 1, findings[] compat error) — all four
    surgically reverted, file back to 20 passed. **Fate ledger:** NO existing test pinned unknown-token
    rejection (grep `_detect_sidecar_version|findings\[\]` in tests/ = zero hits) — nothing amended;
    reports/CLI/stdlib-validator suites SURVIVE green in the full run; AC-1 corpus lock still green
    post-bump (transition proven). **Rebase note (Ruling 62-A):** the "8 kept" figure in this task text
    predates v0.1.61's merge, which landed a 9th contract (`cli must not import infrastructure`) — actual
    gate result **9 kept / 0 broken**, ignore-cap UNCHANGED (`core/role_atom_map.py` is a stdlib-only core
    leaf; `features→core` edges legal). Gates: `ruff format --check` 0 (816 formatted); `ruff check
    --no-cache` 0; `mypy --strict dadaia_workspace/` 0 (313 files, CI-canonical scope); full unpiped
    `pytest` exit 0 — **4704 passed, 17 skipped** (4701 branch-point + 20 new = 4721 collected).

## W2 — FR3 accept-sets + Layer-2 emitter bump (sequential after W1)

- [ ] T-62-20 Accept-set widening + emitter bump + tree-wide token sweep. Owner: software-engineer. Preconditions:
  T-62-11 done. Write set: `features/lifecycle/gates.py`, `infrastructure/runtime_files.py`,
  `features/lifecycle/service.py`, `features/lifecycle/report_workflow.py`, `features/panel/reports_doctor.py`
  (grep fate), their unit tests. Checklist:
  - `gates.py#_schema_version` + `runtime_files.py:210` → `{v1, v1.1, v1.2}`.
  - `service.py` + `report_workflow.py` emit v1.2 with `self_pull.refs` from the run's `InjectedContext` refs
    (dedup); zero-refs → role-map fallback → **honest v1.1** (ADR-5; the only sanctioned v1.1 emission).
  - `rg 'handoff-v1'` sweep across `dadaia_workspace/` — every hit updated or fate-ledgered;
    `workflow-step-payload-v1.schema.json` explicitly OUT (different family).
  - Tests: AC-5 round-trip (emit → gates → runtime_files → `reports validate` exit 0; zero-refs fallback = v1.1).
  - Fate ledger: gates/runtime_files tests pinning the old set amended-with-rationale; frozen v0.1.50 suite
    zero-diff. Done: gates green.

## W3 — FR4 instruction adoption (ai-engineer, `public/**`, sequential after W2)

- [ ] T-62-30 All-agent emission-instruction adoption. Owner: ai-engineer. Preconditions: T-62-20 done. Write set:
  `public/agents/*.md` (9 core), `public/plugins/{frontend-design,devops}/agents/*.md` (3),
  `public/skills/dadaia-handoff-emitter/SKILL.md`, `public/data/handoff-AGENTS.md`,
  `public/lifecycle_fragments/shared/output-handoff.md`, affected prompt goldens. Checklist:
  - Every surface instructs v1.2 emission + `self_pull.refs` = the atoms actually self-pulled (`specs/`-prefixed,
    context-relative); never list an unread atom. Skill: fields table + BOTH examples gain `self_pull`;
    `schema_version` literals → `"handoff-v1.2"`.
  - AC-6 negative grep: `rg 'handoff-v1\.1' dadaia_workspace/public/` → only fate-ledgered back-compat mentions.
  - **AC-6 positive 16/16 contract (QA62-3):** <!-- AMEND:QA62-3 --> NEW contract test enumerating the 16
    surfaces (12 agent bodies, the emitter skill's two examples, `handoff-AGENTS.md`, `output-handoff.md`),
    asserting each carries the `handoff-v1.2`/`self_pull` instruction — a surface mentioning neither token FAILS.
  - **Sequencing (Ruling 62-A):** these 12-body edits land BEFORE v0.1.63's plugin-agent frontmatter and
    v0.1.64's `tier:` rename on the same files; v0.1.64 re-verifies this AC-6 post-rename. <!-- AMEND:ARCHX-1 -->
  - Prompt goldens embedding `output-handoff.md`: re-baseline as deliberate recorded amendments (diff = exactly the
    fragment edit); FRAG-COH doctor green before/after.
  - Public-privacy law holds (generic content only). Done: AC-6 both halves asserted; gates green.

## W4 — FR5/FR6 fan-out containment + symlink refusal (∥ W5a permitted — disjoint write sets)

- [ ] T-62-40 Slug containment + symlink write-through refusal. Owner: software-engineer. Preconditions: none on
  W1-W3 files (disjoint); may start after T-62-01. Write set: `infrastructure/workspace_guardrail.py`, NEW
  `tests/unit/infrastructure/test_consumer_fanout_containment.py`. Checklist:
  - `_consumer_repos_for_root`: lexical slug validation (single relative non-dot component; reject `/`, `\\`,
    `.`/`..`, absolute incl. Windows drive/UNC via `PurePosixPath` AND `PureWindowsPath` parts); `[reject]` stderr
    line per bad slug (non-silent); fail-open.
  - `_install_guardrail_pair`: write-time containment assert (lexical join parent == `repos_dir`; on failure the same
    `[reject]` line, skip, never write, never raise).
  - Symlink refusal: `dst.is_symlink()` (incl. dangling) ⇒ never written (`[foreign] <path> — left untouched
    (symlink)`); pair follows the FR9 sibling-fate ladder; `_doctor_consumer_pair_lines` classifies symlinked pair
    files `[foreign]` (doctor exit 0). Regular-file provenance ladder byte-identical.
  - Tests: AC-7 hostile-slug matrix (`"../evil"`, `"a/b"`, absolute, `".."` — RED-first: pre-fix `"../evil"` gets the
    pair OUTSIDE `repos/`); AC-8(a) out-of-repo symlink survives byte-identical at target (RED-first: pre-fix
    clobbered), (b) dangling refused, (c) doctor `[foreign]` + exit 0, (d) **symlinked consumer DIR stays `[ok]`**
    (CI `ln -sfn` pattern pin; POSIX skip marker if Windows CI can't symlink — degrade the TEST, never the guard).
  - **Mutation-sanity:** AC-10(e) drop the slug reject ⇒ AC-7 FAILS; AC-10(f) drop `is_symlink()` ⇒ AC-8(a) FAILS —
    captured here, reverted.
  - Fate ledger (REAL paths — QA62-4) <!-- AMEND:QA62-4 -->: v0.1.60 provenance tests SURVIVE byte-identical —
    `tests/unit/infrastructure/test_consumer_fanout_provenance.py`,
    `tests/unit/infrastructure/test_public_assets.py` (consumer classes),
    `tests/unit/features/public/test_workspace_guardrail_pair.py`,
    `tests/integration/test_public_doctor_parity.py` — enumerate + confirm green. Done: gates green.

## W5a — FR7 response-guard chip assertion (∥ W4 permitted — disjoint write set)

- [ ] T-62-50 Require the memory chip in both e2e guards. Owner: qa-engineer. Write set:
  `tests/e2e/panel/response-guard.spec.ts` ONLY. Checklist:
  - Replace BOTH null-guards (L76-83, L128-131): `await page.waitForSelector('.memory-chip', { timeout: 8000 })` →
    click → settle; delete the `if (firstChip)` branches; update the module docblock (chip REQUIRED).
  - **AC-9 sabotage replay:** rename `.memory-chip` in `features/panel/views/index.py` (v0.1.59 AC-9(e)) ⇒ unit DOM
    lock FAILS AND the local playwright run now FAILS (pre-fix: "2 passed") ⇒ revert ⇒ both green. Captured here.
  - Fate ledger: `test_index_dom_contract.py` byte-identical (primary lock SURVIVES); other panel specs untouched.
  Done: local e2e green; GH e2e-panel job re-proves at W5 push.

## W5 — gates + ship

- [ ] T-62-60 Full gates + self-hosting reconcile + ship. Owner: software-engineer (+ PM/operator for shell;
  security-reviewer for the push verdict). Preconditions: T-62-11/20/30/40/50 all `[x]`. Checklist:
  - AC-11: `ruff format --check`; `ruff check --no-cache`; `mypy --strict`; full **unpiped** `pytest`;
    `lint-imports --no-cache` (**8 kept / 0 broken**, ignore-cap UNCHANGED); `dadaia specs doctor` exit 0;
    `dadaia backlog doctor` exit 0; frozen v0.1.50 suite **zero-diff**.
  - Self-hosting reconcile: `dadaia public stage` → `dadaia public install --target all` → `dadaia public doctor`
    (`[ok] public-privacy`, exit 0) — projects the W3 surfaces; never hand-edit projections.
  - QA ship-gate review; security push-gate handoff with `metrics.commit_sha` == pushed sha; push; **watch CI until
    every job green** (incl. e2e-panel with the FR7 assertion); PR; merge — sequenced with the sibling releases
    through PM. *(PE runs no shell — commands surfaced to PM/operator or devops-engineer.)*

## W6 — closure (CLOSURE phase)

- [ ] T-62-70 CLOSURE + memory + dispositions + archive. Owner: product-engineer. Preconditions: T-62-60 merged.
  Checklist:
  - `ACTIVE.md` phase = `CLOSURE`. Write CLOSURE.md (Summary, Tasks + final SHAs, Validations triples
    {description, command, evidence}, Drifts, Memory updates, Dispositions, Backlog returns, Archive decision MOVE).
  - MEMORY (SPEC §8): `agent-comms.md` (primary), `public-asset-distribution.md`, `lifecycle-foundation.md`,
    `quality-assurance.md`, `architecture.md` (assess); regen `catalog.json` where tldr/summary changed
    (`dadaia memory catalog generate`, length cap); `release_origin` → v0.1.62. **ORDER LAW:** memory + catalog regen
    BEFORE `ACTIVE.md` → none.
  - Dispositions sweep: `layer1-selfpull-handoff-audit-line`, `fanout-repo-slug-containment`,
    `response-guard-chip-presence-hardening` → `DELIVERED — v0.1.62`; archive →
    `specs/_archive/v0.1.62/consumed-backlog/` + `consumed_backlog.json` (all anchors survive → CLOSURE archival).
  - **Bug terminal event (Ruling 62-E — never silently absorbed):** <!-- AMEND:QA62-1 --> append
    `dadaia bugs append --bug-id reports-sidecar-version-detection-misroutes-future-tokens --event resolved
    --release v0.1.62` (evidence: the AC-4 test + FR2 commit SHA in the CLOSURE Dispositions row).
  - **Shared-atom merge order (Ruling 62-B):** <!-- AMEND:ARCHX-2 --> this release closes after v0.1.61, before
    v0.1.63/64 — rebase `quality-assurance.md` / `public-asset-distribution.md` / `architecture.md` on
    v0.1.61's closed state (never revert a sibling's correction); catalog regen includes all prior deltas.
  - Backlog returns (through PM curation): `l1-read-proof-hardening` only if the trio review demands it; else none.
  - `dadaia specs doctor` clean; request `git mv specs/releases/v0.1.62 specs/_archive/releases/v0.1.62`
    (devops/operator); `ACTIVE.md` per PM's multi-release sequencing.
