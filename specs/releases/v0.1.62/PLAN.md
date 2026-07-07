# PLAN — v0.1.62 — Injection Contract & Fan-out Containment

**Status:** Aprovado

Seven waves (W0–W6). **FR1/FR2 land FIRST behind the AC-1 back-compat corpus lock** (golden-first: the existing
v1/v1.1 corpus is proven green BEFORE and AFTER the bump). The schema/validator chain (W1) gates the emitter bump
(W2) and the instruction adoption (W3) — sequential on the version token. The fan-out hardening (W4) and the
response-guard e2e (W5a) touch **disjoint files** and may run in parallel with declared write sets; everything else is
sequential. Three sibling releases (v0.1.61/63/64) are in flight — any write-set collision discovered mid-wave is a
STOP-and-rescope to PM, never a silent merge.

## Wave map

- **W0 — definition.** SPEC/PLAN/TASKS from the 2026-07-07 code read; mandatory release-definition grill on the
  picked set (inspection-first — operator unavailable, nine overridable ADRs §9). **Dual-review fold
  (2026-07-07, REJECT):** QA62-1..5 + ARCHX/QAX folded with `<!-- AMEND:… -->` markers; PM Rulings 62-A/62-B/62-E
  in SPEC §0 (fixed order v0.1.61→62→63→64 + honest overlap enumeration; shared-atom closure merge order;
  picked HIGH bug `reports-sidecar-version-detection-misroutes-future-tokens` consumed, AC-4 = its repro
  verbatim). `Aprovado` after re-verify; definition commit. Owner: product-engineer (orchestrated).

- **W1 — FR1/FR2 schema bump + validator (software-engineer, golden-first then RED-first).**
  1. **AC-1 corpus lock FIRST.** Add the back-compat test proving every in-tree v1/v1.1 handoff fixture (+ the
     emitter-skill example, transcribed as a fixture) passes `ReportsValidationService`. Commit BEFORE any schema edit.
  2. **Schema edit** (`public/schemas/handoff-v1.schema.json`): `$id`/`title` → v1.2; enum gains `"handoff-v1.2"`;
     optional `self_pull` object (`required: ["refs"]`, `minItems: 1`, no-traversal item pattern) — whitelisted
     keywords ONLY (the stdlib validator must load it unchanged; a keyword slip raises `HandoffSchemaError` at
     construction — that is the guard, not a new test).
  3. **Map relocation (ADR-4).** NEW `core/role_atom_map.py` (pure dict `ROLE_ATOM_MAP`, stdlib-only);
     `features/lifecycle/role_atoms.py` imports + re-exports SAME NAME (three Layer-2 surfaces + existing tests keep
     their import path — zero churn; grep proves no other importer breaks).
  4. **Service-layer conditional (FR2).** `validation.py#validate_file`: v1.2 ⇒ `self_pull` required; refs
     existence-checked (`repos/<context>/<ref>` then `<workspace>/<ref>`, `_within_workspace`-guarded, fail-soft when
     `_workspace_root is None`); role-map coverage for mapped agents (import from `core`).
  5. **Detection fix.** `reports.py#_detect_sidecar_version` — v1.2 (token or `$id`) is modern; never routes to
     `_check_v10_compat`.
  - Tests: AC-1 (green pre+post); AC-2 conditional (RED-first: pre-fix the v1.2-no-self_pull doc only trips the enum;
    post-FR1 the enum passes and post-FR2 the conditional fires) — **the 4-case version matrix is ONE named
    parametrized test (`test_schema_version_matrix`, QA62-5)** <!-- AMEND:QA62-5 -->; AC-3
    existence/coverage/pattern; AC-4 detection (**RED-first = the picked bug's repro verbatim — Ruling 62-E**)
    <!-- AMEND:QA62-1 -->. Mutation-sanity AC-10(a)(b)(c)(d) NOW. **First implementation wave: pin the
    branch-point `pytest --collect-only -q` count in this ledger (QAX-4).** Fate ledger: existing
    `tests/unit/features/reports/*`, `tests/unit/cli/*reports*`, `tests/unit/infrastructure/test_stdlib_handoff_validator*`
    fixtures SURVIVE (v1.1 still accepted); any test asserting the OLD enum rejection of unknown tokens is amended
    with rationale. NO `specs/backlog/**`.

- **W2 — FR3 accept-sets + Layer-2 emitter bump (software-engineer, sequential after W1).**
  1. Widen `gates.py#_schema_version` + `runtime_files.py:210` to `{v1, v1.1, v1.2}`.
  2. Bump `features/lifecycle/service.py` + `report_workflow.py` emissions to v1.2, `self_pull.refs` from the run's
     `InjectedContext` refs (dedup, `specs/`-prefixed as recorded); zero-refs → role-map fallback → honest v1.1
     (ADR-5 — the only sanctioned v1.1 emission).
  3. Grep sweep `rg 'handoff-v1'` across `dadaia_workspace/` — update or ledger every hit (`reports_doctor.py`,
     docstrings, `workflow-step-payload-v1.schema.json` is a DIFFERENT schema family: DO NOT touch).
  - Tests: AC-5 round-trip (emit → gates accept → runtime_files accept → validate exit 0; zero-refs fallback emits
    v1.1). Fate ledger: gates/runtime_files tests pinning the old set amended-with-rationale; frozen v0.1.50 suite
    untouched. NO `specs/backlog/**`.

- **W3 — FR4 instruction adoption (ai-engineer, `public/**`, sequential after W2).**
  1. Update the 12 agent bodies + `dadaia-handoff-emitter/SKILL.md` (fields table + BOTH examples) +
     `public/data/handoff-AGENTS.md` + `lifecycle_fragments/shared/output-handoff.md`: emit v1.2; record only
     actually-read atoms in `self_pull.refs` (`specs/`-prefixed, context-relative); never fabricate.
  2. `rg 'handoff-v1\.1' dadaia_workspace/public/` → only fate-ledgered back-compat mentions remain (AC-6
     negative half).
  3. **Positive 16/16 adoption contract (QA62-3):** <!-- AMEND:QA62-3 --> a contract test enumerating the 16
     surfaces (12 agent bodies, the emitter skill's two examples, `handoff-AGENTS.md`, `output-handoff.md`) and
     asserting each carries the v1.2/`self_pull` instruction — file-enumerated, never a manual sweep.
  4. Prompt-assembly goldens embedding `output-handoff.md`: re-baseline as deliberate recorded amendments (captured
     diff = exactly the fragment edit); FRAG-COH doctor green before/after.
  - **Sequencing (Ruling 62-A):** this wave's 12-body prose edits land BEFORE v0.1.63's plugin-agent
    `skills:` frontmatter edits and v0.1.64's `tier:` rename on the same files; the later siblings rebase and
    v0.1.64 re-verifies this wave's AC-6 grep post-rename. <!-- AMEND:ARCHX-1 -->
  - Tests: AC-6 both halves. NO `specs/backlog/**`.

- **W4 — FR5/FR6 fan-out containment + symlink refusal (software-engineer; disjoint from W1–W3 files; may run
  parallel to W5a — declared disjoint write sets).**
  1. **Lexical slug validation** in `_consumer_repos_for_root`: single relative non-dot component (reject `/`, `\\`,
     `.`/`..`, absolute incl. Windows drive/UNC — check `PurePosixPath` AND `PureWindowsPath` parts); `[reject]`
     stderr line per bad slug (non-silent, A3); fail-open, never raises. Protects install AND doctor.
  2. **Write-time containment assert** in `_install_guardrail_pair` (belt-and-braces: lexical join parent ==
     `repos_dir`; on failure, same `[reject]` line, skip, never write).
  3. **Symlink refusal (FR6):** `dst.is_symlink()` (incl. dangling) ⇒ never write through (`[foreign] ... (symlink)`);
     pair semantics follow the v0.1.60 FR9 ladder; `_doctor_consumer_pair_lines` classifies symlinked pair files
     `[foreign]` (doctor exit 0). Regular-file provenance ladder byte-identical.
  - Tests: NEW `tests/unit/infrastructure/test_consumer_fanout_containment.py` — AC-7 hostile-slug matrix (RED-first:
    pre-fix `"../evil"` receives the pair outside `repos/`); AC-8(a)(b)(c) symlink refusal (RED-first: pre-fix
    `copy2` clobbers the link target) + **AC-8(d) symlinked-dir stays green** (the CI `ln -sfn` pattern pin —
    POSIX-only via a platform skip marker if needed; 3-OS CI law). Mutation-sanity AC-10(e)(f). Fate ledger
    (REAL paths — QA62-4) <!-- AMEND:QA62-4 -->: the v0.1.60 provenance tests
    (`tests/unit/infrastructure/test_consumer_fanout_provenance.py`,
    `tests/unit/infrastructure/test_public_assets.py` consumer classes,
    `tests/unit/features/public/test_workspace_guardrail_pair.py`,
    `tests/integration/test_public_doctor_parity.py`) SURVIVE byte-identical (regular-file paths untouched);
    enumerate + confirm. NO `specs/backlog/**`.

- **W5a — FR7 response-guard chip assertion (qa-engineer; disjoint file, may run parallel to W4).**
  1. Replace BOTH null-guards in `response-guard.spec.ts` (L76-83, L128-131) with required presence:
     `await page.waitForSelector('.memory-chip', { timeout: 8000 })` → click → settle. Remove the `if (firstChip)`
     branches; update the module docblock (the tour now REQUIRES the chip).
  2. **Sabotage replay (AC-9):** rename `.memory-chip` in `features/panel/views/index.py` → run the unit DOM lock
     (FAILS, as v0.1.59) AND the local playwright suite (now FAILS — pre-fix it passed "2 passed") → revert →
     both green. Local run via the panel bootstrap; the e2e-panel CI job re-proves on GH.
  - Fate ledger: `test_index_dom_contract.py` byte-identical (SURVIVES — primary lock); the other panel specs
    untouched. NO `specs/backlog/**`.

- **W5 — gates + ship.** Full local gates (AC-11): unpiped `pytest` + `ruff format --check` + `ruff check --no-cache`
  + `mypy --strict` + `lint-imports --no-cache` (**8 kept / 0 broken**, ignore-cap UNCHANGED) + `dadaia specs doctor`
  + `dadaia backlog doctor`. Self-hosting reconcile: `dadaia public stage` → `dadaia public install --target all` →
  `dadaia public doctor` (`[ok] public-privacy`, exit 0) — the W3 instruction surfaces project here. Frozen v0.1.50
  no-steal suite **zero-diff**. QA ship-gate; security push-gate keyed to the pushed sha (`metrics.commit_sha`); push;
  **watch CI until every job green** (incl. e2e-panel — the FR7 guards now assert the chip); PR; merge. Coordinate the
  merge order with the sibling releases through PM. *(PE runs no shell — surfaces commands to PM/operator or requests
  devops-engineer.)*

- **W6 — closure (CLOSURE phase).** `ACTIVE.md` phase = `CLOSURE`; CLOSURE.md (Summary, Tasks + SHAs, Validations
  triples, Drifts, Memory updates, Dispositions, Backlog returns, Archive). MEMORY (§SPEC 8): `agent-comms.md`
  (primary — v1.2 contract + self_pull + transition posture), `public-asset-distribution.md` (containment + symlink
  posture), `lifecycle-foundation.md` (emitters v1.2 + core map relocation), `quality-assurance.md` (response-guard
  real assertion), `architecture.md` (assess — core leaf). Regen `catalog.json` where tldr/summary changed
  (`dadaia memory catalog generate`; length cap); `release_origin` → v0.1.62. **ORDER LAW:** memory edits + catalog
  regen BEFORE `ACTIVE.md` → none. **Dispositions:** archive the 3 consumed backlog items
  (`DELIVERED — v0.1.62`) → `specs/_archive/v0.1.62/consumed-backlog/` + `consumed_backlog.json`. **Backlog
  returns (route through PM):** `l1-read-proof-hardening` (per-atom read-proof beyond self-report — only if the trio
  review asks for it; else none). **Bug terminal event (Ruling 62-E):** <!-- AMEND:QA62-1 --> append
  `dadaia bugs append --bug-id reports-sidecar-version-detection-misroutes-future-tokens --event resolved
  --release v0.1.62`. **Shared-atom merge order (Ruling 62-B):** closes after v0.1.61, before v0.1.63/64;
  rebase `quality-assurance.md`/`public-asset-distribution.md`/`architecture.md` on v0.1.61's closed state
  (never revert its corrections); catalog regen includes prior deltas. `dadaia specs doctor` clean; request
  `git mv specs/releases/v0.1.62 → specs/_archive/releases/` (devops/operator); `ACTIVE.md` per PM's
  multi-release sequencing.

## Write sets (disjoint per wave; shared files force sequential order)

| Wave | Files |
|---|---|
| W1 | `public/schemas/handoff-v1.schema.json`; `features/reports/validation.py`; `cli/commands/reports.py` (`_detect_sidecar_version`); NEW `core/role_atom_map.py`; `features/lifecycle/role_atoms.py` (re-export only); NEW `tests/unit/features/reports/test_handoff_v12_validation.py` (+ AC-1 corpus lock in the same module or a sibling) |
| W2 | `features/lifecycle/gates.py`; `infrastructure/runtime_files.py`; `features/lifecycle/service.py`; `features/lifecycle/report_workflow.py`; `features/panel/reports_doctor.py` (grep fate); their unit tests |
| W3 | `public/agents/*.md` (9); `public/plugins/{frontend-design,devops}/agents/*.md` (3); `public/skills/dadaia-handoff-emitter/SKILL.md`; `public/data/handoff-AGENTS.md`; `public/lifecycle_fragments/shared/output-handoff.md`; affected prompt goldens (recorded amendments) |
| W4 | `infrastructure/workspace_guardrail.py`; NEW `tests/unit/infrastructure/test_consumer_fanout_containment.py` |
| W5a | `tests/e2e/panel/response-guard.spec.ts` |
| W5 | (gates + `public stage/install/doctor`; no `specs/**` change) |
| W6 | `specs/releases/v0.1.62/CLOSURE.md` + `specs/memory/**` + `specs/_archive/v0.1.62/consumed-backlog/` + `ACTIVE.md` |

**Sequencing:** W1 → W2 → W3 strictly sequential (version-token chain). **W4 ∥ W5a permitted** (disjoint write sets,
declared here per the one-`[-]` exemption rule); both after W1 merges cleanly (no file overlap — the parallelism is
owner-level, one `[-]` per owner). `role_atoms.py` is touched in W1 ONLY (re-export); no other wave touches
`features/lifecycle` map code.

## Test strategy

- **Golden-first (AC-1).** The v1/v1.1 back-compat corpus lock is committed BEFORE the schema edit and must be green
  before AND after — the transition posture is proven, never asserted. Fix-the-consumer-never-the-golden.
- **RED-first for every new behavior (FR2/FR4-half/FR5/FR6/FR7).** Each new check's test is shown to FAIL (or the
  pre-fix hole shown to pass wrongly) against the pre-fix tree: v1.2-no-self_pull accepted; v1.2 misrouted to v1.0
  compat; `"../evil"` written outside `repos/`; symlink written through; sabotaged chip → e2e "2 passed".
- **Mutation-sanity AC-10 (a–f)** — one-line sabotage ⇒ named test FAILS ⇒ revert; captured on each task line.
- **Platform seam.** Slug validation checks BOTH `PurePosixPath`/`PureWindowsPath` parts; symlink tests carry a
  POSIX skip marker where Windows CI cannot create symlinks unprivileged (3-OS CI law — degrade the TEST, never the
  guard). No `os.symlink` in production code — only `is_symlink()` checks.
- **Schema-keyword guard is constructive.** `StdlibHandoffValidator` raises at construction on any non-whitelisted
  keyword — the existing construction tests re-load the edited schema; a keyword slip cannot land silently.
- **Fate ledger per wave (AC-12), file-enumerated**; version-token greps include `tests/` + docstrings + fragment
  prose + skill examples. `workflow-step-payload-v1.schema.json` is explicitly OUT (different schema family).
- **Frozen suite:** v0.1.50 no-steal lease/gate suite untouched — zero-diff confirmation in W5.
- **E2E:** the panel e2e runs locally for the AC-9 sabotage replay and re-proves on the GH e2e-panel job (CI seeds the
  context deterministically — ci.yml:291-326).

## Rollback

Single feature branch `feature/v0.1.62`. W1 is additive-conditional (revert = restore enum + drop the service check;
v1.1 corpus unaffected by construction — AC-1). W2 revert restores the v1.1 emissions (accept-sets are supersets —
safe to leave). W3 is instruction prose (revert + re-project). W4/W5a are pure hardening/tests (revert restores the
permissive behavior). No data migration; on-disk handoffs are never rewritten. The only irreversible-ish step is
`public install` on the live instance (re-run stage/install/doctor to reconcile). CLOSURE dispositions are recoverable
by reverting the closure commit.
