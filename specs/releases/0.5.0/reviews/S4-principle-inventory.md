# S4 — FR18 principle inventory and FR17 split plan

**Author role:** software-architect · **Task:** T-050-29 (architect half) · **Release:** 0.5.0, S4
**Inputs read:** `specs/releases/0.5.0/SPEC.md` FR17/FR18/FR19 (A17.1–A17.5, A18.1–A18.6),
`TASKS.md` T-050-29, operator ruling D13 (grill handoff 2026-08-26), `setup.cfg`, every
`tests/contract/*` named by the task, `dadaia-test-stewardship/PARAMETERS.md`,
`specs/memory/{ARCHITECTURE,QUALITY,TECHSTACK,AGENTS}.md`, `pyproject.toml` ruff blocks,
`tests/conftest.py` tier table, `.github/workflows/ci.yml` selectors.
**Method:** inspection only (Read/Glob/Grep). Every number below was re-counted from the tree at
task time; no figure is transcribed from a review or the SPEC.

The product-engineer authors the Part-1 text in the CLOSURE window from this file. Each
`P-NN` row is ready to paste: statement, `Measured by:`, home file, ADR slug.

---

## 0. architect-core-workflow trail

**Core problem.** Memory describes an architecture in prose that no check enforces, so the
architecture eroded silently (the bug loop the standing order names). D13 answers it: a
principle is admitted only with an existing mechanical measure, and the first Part 1 is an
inventory of what is already measured — not new rules, not new checks.

**Constraints.** A18.3: zero new product checks (doctor codes, CI jobs, hook exits); the
only permitted new test is the contract-count/`modules =`-on-disk test (A18.1/A18.5, +1).
A18.5: the independence contract must be TRUE before it is promoted. A18.6: one numeric home
per parameter. A18.4: one ADR per principle, and vice versa. D12: any agent writes `proposed`,
only the operator flips to `accepted` (FR20 sitting). Memory is writable by product-engineer
only, in CLOSURE — hence this file is the architect's deliverable, not a memory edit.

**Success criteria.** V13: `grep -c '^\[importlinter:contract' setup.cfg` = 9 = the number of
Part-1 principles promoted from it. V14: every `Measured by:` below runs. V29: `QUALITY.md`
carries no numeric LARGE cap of its own. V32: `modules =` equals the packages on disk with the
cap at 17 and `lint-imports` green.

**Assumptions made explicit.** (1) A "mechanical check" is anything that runs in the gating
`pytest` job or in `dadaia ci preflight`/CI lint steps and fails on violation — a *reported,
not gated* measure (V30) is a measurement, not an enforcement, and is flagged as such below
for an explicit decision. (2) The D13 enumeration is the inventory's **scope**, not a ceiling
on what *may* be measured: rules already measured by a test D13 did not name are listed in §5
as Tier-B candidates for the operator/PE to promote or leave in Part 2 with their check cited.
(3) Final ADR numbers are T-050-30's to assign; slugs here are the stable key, numbers are
provisional in the order the principles appear.

**Prior art surveyed.** import-linter contracts (already in use, 9 sections), the
measure-then-pin-then-ratchet law already used by four tests in this repo
(`test_module_size_ceiling.py`, `test_import_linter_ignore_cap.py`,
`test_core_file_io_purity.py`, `test_test_suite_ratchets.py`), and the Nygard/MADR ADR shape
D12 already fixed. The design space is closed by D12/D13; no external candidate was needed
beyond the checks that exist, which is the point of the ruling.

---

## 1. Pre-promotion facts (re-counted from disk, A18.5)

| Fact | Measured now | Source |
|---|---|---|
| `[importlinter:contract:*]` sections | **9** | `setup.cfg` lines 49, 86, 106, 126, 137, 155, 174, 218, 258 |
| `dadaia_workspace/features/*/__init__.py` packages | **24** | glob |
| Packages in `features-no-cross-feature` `modules =` | **20** | `setup.cfg:177–197` |
| Missing from `modules =` | **4** — `capabilities`, `certification`, `reconcile`, `tmp_gc` | diff |
| Module-level cross-feature edges present | **5** | grep `^from dadaia_workspace.features` across `features/**` |
| …declared as `ignore_imports` today | **2** — `chokepoints.service → spec_context.presence`, `specs.doctor_governance → backlog.document` | `setup.cfg:201,206` |
| …invisible (source package unlisted) | **3** — `reconcile/service.py:12 → features.capabilities`, `:13 → features.migrate.legacy_dadaia_dirs`, `:14 → features.migrate.state_v2` | grep |
| `capabilities`/`certification`/`tmp_gc` sibling imports | **0** — listing them adds no new edge | grep |
| `_RECORDED_IGNORE_EDGE_CAP` at HEAD | **14** (7/3/2/2) — T-050-08 already took the −1 the SPEC's "15 − 1" describes | `test_import_linter_ignore_cap.py:100–109` |
| Target cap after this task | **17** (7/3/**5**/2) | 14 + 3 |
| `setup.cfg` header comment cap | says **16** (4-family "7; 4; 2; 3") — stale twice over | `setup.cfg:24–25` |

**Correction to the SPEC/TASKS arithmetic, stated so nobody re-derives it:** the SPEC's
"15 → 17" assumed the FR2 removal and this task landed together. At HEAD the FR2 removal is
already pinned (cap 14, family `cli-no-infrastructure` = 2). The same-commit move for T-050-29
is therefore **14 → 17**, per-family `features-no-cross-feature` **2 → 5**. Also repair the
stale header block at `setup.cfg:24–25` in the same commit (it is comment-pinned "by review
discipline", and it is wrong today).

**What the independence-contract completion must contain** (config + the cap test, same
commit; software-engineer applies — the architect writes no config):

1. `modules =` gains `dadaia_workspace.features.capabilities`, `.certification`, `.reconcile`,
   `.tmp_gc` (alphabetical position).
2. `ignore_imports` gains three edges, each with its own reason line, e.g.
   `reconcile.service → capabilities` ("reconcile refreshes the capabilities payload as its last
   step; composition via container is the FR-sized rewrite routed to intake"),
   `reconcile.service → migrate.legacy_dadaia_dirs` and `→ migrate.state_v2` ("reconcile *is*
   the transactional wrapper over the migrate steps; collapsing it is a feature rewrite, not an
   inventory step").
3. `_RECORDED_IGNORE_EDGE_CAP = 17`, `_RECORDED_PER_FAMILY_CAP["features-no-cross-feature"] = 5`.
4. `setup.cfg:24–25` header: "Current count = 17 (features-no-infrastructure: 7;
   features-no-subprocess: 3; features-no-cross-feature: 5; cli-no-infrastructure: 2)".
5. The new contract-count test (A18.1 + A18.5, **one function**): parse `setup.cfg`, assert the
   section count equals the number of `### P-NN` entries in `ARCHITECTURE.md` whose
   `Measured by:` names `lint-imports`, and assert `modules =` of `features-no-cross-feature`
   equals the on-disk package set (`__init__.py` glob). This is the release's one permitted
   new test for FR18.

Only after `lint-imports --config setup.cfg --no-cache` is green on that state may P-07 be
authored.

---

## 2. The inventory — Part 1 principles, one per existing mechanical check

Statement form is "We …" per D12. `Measured by:` names the exact command; V14 captures its
output once. `Accepted by:` is left for the FR20 sitting. ADR numbers provisional (T-050-30).

### 2.1 `ARCHITECTURE.md` — 17 principles

| Id | Statement ("We …") | Measured by | ADR slug |
|---|---|---|---|
| **P-01** | We keep features on ports: a feature never imports `infrastructure` directly; the container injects the adapter. | `lint-imports --config setup.cfg --no-cache` — contract `features-no-infrastructure` (7 capped ignores, P-10) | `0001-features-depend-on-ports-not-adapters` |
| **P-02** | We never spawn a subprocess from a feature; process execution goes through `ProcessRunner`. | same command — contract `features-no-subprocess` (3 capped ignores) | `0002-features-never-spawn-subprocess` |
| **P-03** | We keep `core` free of OS primitives (`fcntl`, `signal`, `subprocess`, `msvcrt`); `core/platform.py` is the sole platform seam. | same command — contract `core-no-os-primitives` | `0003-core-is-os-primitive-free` |
| **P-04** | We make `core` the bottom ring: it imports no `features`, `infrastructure`, `cli` or `hooks`. | same command — contract `core-no-upper-layers` (zero ignores) | `0004-core-is-the-bottom-ring` |
| **P-05** | We let `infrastructure` depend on `core` only — never on `features`, `cli` or `hooks`. | same command — contract `infrastructure-no-upper-layers` (zero ignores) | `0005-infrastructure-depends-only-on-core` |
| **P-06** | We keep `core.kernel_tunables` a pure-constant leaf that imports no upper layer. | same command — contract `kernel-tunables-is-a-leaf` | `0006-kernel-tunables-is-a-pure-constant-leaf` |
| **P-07** | We keep features mutually independent: they compose through the container, never through sibling imports; a helper two features need lives in each (duplication over coupling). | same command — contract `features-no-cross-feature`, `modules =` equal to the 24 packages on disk, 5 declared edges (A18.5, V32) | `0007-features-are-mutually-independent` |
| **P-08** | We compose the CLI through the container: a verb never imports an infrastructure adapter directly. | same command — contract `cli-no-infrastructure` (2 capped ignores) | `0008-cli-composes-via-the-container` |
| **P-09** | We resolve a Spec Context in exactly one place, `core.specs_resolver.resolve_context`, imported directly only by `cli._specs_resolution`, `container` and `hooks`. | same command — contract `bind-resolution-seam-is-a-single-home` (zero ignores, none ever accepted) | `0009-one-context-resolution-authority` |
| **P-10** | We cap every suppressed layering edge and ratchet the cap only downward; an edge is added with a reason on the edge and the cap moved in the same commit. | `pytest -p no:cacheprovider tests/contract/test_import_linter_ignore_cap.py` (cap 17 = 7/3/5/2 after this task; exact equality, per-family pin, sanctioned-source check) | `0010-suppressed-layering-edges-are-capped` |
| **P-11** | We keep `core` file-I/O pure outside an authorized set of six modules; new file I/O enters `core` only by joining that set on purpose. | `pytest -p no:cacheprovider tests/contract/test_core_file_io_purity.py` (AST walk; authorized stems must exist) | `0011-core-file-io-authorized-set` |
| **P-12** | We never import the composition root from a hook; hooks reach the resolution authority directly because they are one-shot processes on the write hot path. | `pytest -p no:cacheprovider tests/contract/test_hook_import_surface.py` (six hook modules + the executed gate path, `container` absent from `sys.modules`) | `0012-hooks-never-import-the-composition-root` |
| **P-13** | We keep the architecture diagrams derived from live code: every diagrammed class, view module and feature package is introspected, and every live one is diagrammed. | `pytest -p no:cacheprovider tests/contract/test_architecture_diagrams_current.py` | `0013-architecture-diagrams-derive-from-live-code` |
| **P-14** | We keep the release-event fold read-only: `core/release_events.py` contains no write call and no file I/O at all. | `pytest -p no:cacheprovider tests/contract/test_release_events_read_only.py` | `0014-release-event-fold-never-writes` |
| **P-15** | We close the release-record envelope: exactly seven event kinds, `additionalProperties: false`, and no harness `session_id` ever enters a governance record. | `pytest -p no:cacheprovider tests/contract/test_release_event_schema.py` | `0015-release-record-envelope-is-closed` |
| **P-16** | We store no provenance a resolver cannot re-derive: a stored `resolved_commit` equals the value derived from git history, on a live sample of ≥ 20 records. | `pytest -p no:cacheprovider tests/contract/test_resolved_commit_stored_equals_derived.py` (marked `slow`; runs in the `contract-coverage` job and the local preflight — only `unit-fast` excludes `slow`) | `0016-stored-provenance-equals-derived-provenance` |
| **P-17** | We map every core skill and every scoped `AGENTS.md` source to exactly one `DADAIA.md` section, every section to at least one owner, with content hashes re-recorded only by review. | `pytest -p no:cacheprovider tests/contract/test_behavior_map.py` (bijection, hash tuples, citation check, invocation grants) | `0017-behavior-map-bijection` |

### 2.2 `QUALITY.md` — 10 principles

| Id | Statement ("We …") | Measured by | ADR slug |
|---|---|---|---|
| **P-18** | We hold decomposed modules under a line-count ceiling that only decreases: `features/specs/doctor*.py` ≤ 700, `features/panel/views/api*.py` ≤ 450, and `api.py` stays deleted. | `pytest -p no:cacheprovider tests/contract/test_module_size_ceiling.py` | `0018-module-size-ceilings-ratchet-down` |
| **P-19** | We pin cyclomatic complexity and nesting at the measured maxima (`max-complexity = 63`, `max-nested-blocks = 6`) and move them only downward, with the justification in the reducing release's CLOSURE. | `ruff check --no-cache dadaia_workspace/` (`C901`, `PLR1702`, `pyproject.toml:148–156`) — run by `dadaia ci preflight` and the CI lint job | `0019-complexity-ceilings-ratchet-down` |
| **P-20** | We do not grow `specs upgrade`/`specs doctor`: `#upgrade` CC ≤ 26, `#doctor` CC ≤ 30, and `features/migrate/upgrade.py` changes only with a same-commit justification. | `pytest -p no:cacheprovider tests/contract/test_specs_cli_complexity_ratchet.py` (radon; pinned SHA-256 of `upgrade.py`) | `0020-specs-cli-complexity-ratchet` |
| **P-21** | We give every test a size tier with an enforced timeout at collection — unit 10 s, contract 30 s, integration 60 s, e2e 120 s — and an explicit `@pytest.mark.timeout` is never overridden. | `pytest -p no:cacheprovider tests/contract/test_stewardship_mechanics.py -k "timeout"` (executed-path: the marker on the test's own item; `tests/conftest.py:129`) | `0021-every-test-carries-a-tier-timeout` |
| **P-22** | We gate quarantine on a registered bug: a `quarantine` mark without `bug=` refuses collection actionably (serial and xdist), and every gating selector excludes the lane. | `pytest -p no:cacheprovider tests/contract/test_stewardship_mechanics.py -k "quarantine"` | `0022-quarantine-requires-a-registered-bug` |
| **P-23** | We ratchet private-symbol imports in `tests/**` downward only (AST-exact; ceiling 60 statements / 54 files; per-statement `# allow-private-import: <reason>` is the only exception). | `pytest -p no:cacheprovider tests/contract/test_test_suite_ratchets.py -k v26` | `0023-tests-pin-no-private-symbols` |
| **P-24** | We declare intent at birth: the count of `tests/**/test_*.py` whose module docstring carries `Intent: <KIND> — <ref>` ratchets upward only (floor 108). | `pytest -p no:cacheprovider tests/contract/test_test_suite_ratchets.py -k v27` | `0024-test-intent-declared-at-birth` |
| **P-25** | We expire SCAFFOLD: every `Intent: SCAFFOLD` names `expires: <M.m.p>`, and one naming an archived release is red until renewed by a `qa-engineer` verdict. | `pytest -p no:cacheprovider tests/contract/test_test_suite_ratchets.py -k v28` | `0025-scaffold-tests-expire` |
| **P-26** | We keep one number per parameter: `dadaia-test-stewardship/PARAMETERS.md` is the LARGE cap's only literal home (30); every other doctrine file references it and carries no number of its own. | `pytest -p no:cacheprovider tests/contract/test_test_suite_ratchets.py -k v29` (competing-home ceiling 1 → **0** once `QUALITY.md`'s 100 is deleted; re-pin `_V29_COMPETING_HOME_CEILING = 0` in the same commit — that is a ratchet-down re-pin, not a new check) | `0026-one-number-per-parameter` |
| **P-27** | We measure the pyramid every run: SMALL/MEDIUM/LARGE shares from one `--collect-only`, judged against 75/20/5 (±5 pp) — **reported, not gated**; a drift is a closure finding. | `pytest -p no:cacheprovider -s tests/contract/test_test_suite_ratchets.py -k v30` (prints the shares; the detector is proven on a mutation fixture) | `0027-pyramid-shape-is-measured-every-run` |

**Decision the operator must take on P-27 (flagged, not assumed).** V30 runs and produces
the number mechanically, but by design it never fails on the real repository. Under the
strict reading of D13 ("a principle without a measure is not admitted") it qualifies — it is
measured. Under the stricter reading the standing order implies (a rule that cannot go red
is decoration), it is a Part-2 tunable. Recommendation: **admit it with the words "reported,
not gated" in the statement itself**, so the principle says exactly what its measure does;
promoting it silently as if it gated would be the fabricated-detection this release outlaws.

### 2.3 `TECHSTACK.md` — 1 principle

| Id | Statement ("We …") | Measured by | ADR slug |
|---|---|---|---|
| **P-28** | We keep the pytest marker set closed and single-sourced: `pyproject.toml`'s `markers` equals `tests/conftest.py`'s `_KNOWN_MARKERS` (eight: unit, contract, integration, e2e, slow, tmp, flaky, quarantine), and `flaky`/`quarantine` are always among them. | `pytest -p no:cacheprovider tests/contract/test_stewardship_mechanics.py -k marker_set` | `0028-marker-set-is-closed-and-single-sourced` |

**Totals (Tier A, the D13 inventory): ARCHITECTURE 17 · QUALITY 10 · TECHSTACK 1 · = 28.**
Import-linter contracts promoted: 9 of 9 (V13 = 9).

### 2.4 Refused for Part 1 — measurably false or unmeasured at birth

| Candidate the SPEC/FR18 text names | Why it is NOT a principle | Where it goes |
|---|---|---|
| "The LARGE-test census ceiling" (30) | **False at birth.** `PARAMETERS.md:10` itself says "30 (current ~84 — remediation target)"; measured today 42 functions under `tests/e2e/**`, 15 `e2e`-marked. Nothing mechanical compares the census to 30. Promoting a target the tree does not meet is exactly A18.5's refusal applied to QA. The principle that *is* true and measured is P-26 (one home). | Part 2 of `QUALITY.md`: "LARGE cap: see `PARAMETERS.md`" — no number, no ceiling claim. Remediation stays where PARAMETERS.md puts it. |
| "Demotion at closure" (stewardship lifecycle) | No check runs it; it is a CLOSURE-step discipline. | Part 2 (protocol pointer to `dadaia-test-stewardship`). |
| "Intent + size at birth" as a *gate* | Only V27's floor is mechanical (P-24). The e2e-only `check_test_intent_declared.py` gate is a Tier-B measured rule (§5), not part of this enumeration. | P-24 carries the measured half; the rest is Part 2. |
| Quarantine cap 8 / 30-day escalation / flake < 0.5 % | Numbers live in `PARAMETERS.md`; no check measures them (V29 scans only the LARGE cap). | Part 2, by reference to `PARAMETERS.md`. |

---

## 3. V14 execution list (one run each, output captured by software-engineer)

```
lint-imports --config setup.cfg --no-cache                                   # P-01..P-09
ruff check --no-cache dadaia_workspace/                                      # P-19
pytest -p no:cacheprovider tests/contract/test_import_linter_ignore_cap.py   # P-10
pytest -p no:cacheprovider tests/contract/test_core_file_io_purity.py        # P-11
pytest -p no:cacheprovider tests/contract/test_hook_import_surface.py        # P-12
pytest -p no:cacheprovider tests/contract/test_architecture_diagrams_current.py   # P-13
pytest -p no:cacheprovider tests/contract/test_release_events_read_only.py   # P-14
pytest -p no:cacheprovider tests/contract/test_release_event_schema.py       # P-15
pytest -p no:cacheprovider tests/contract/test_resolved_commit_stored_equals_derived.py  # P-16
pytest -p no:cacheprovider tests/contract/test_behavior_map.py               # P-17
pytest -p no:cacheprovider tests/contract/test_module_size_ceiling.py        # P-18
pytest -p no:cacheprovider tests/contract/test_specs_cli_complexity_ratchet.py   # P-20
pytest -p no:cacheprovider tests/contract/test_stewardship_mechanics.py      # P-21, P-22, P-28
pytest -p no:cacheprovider -s tests/contract/test_test_suite_ratchets.py     # P-23..P-27
```

Run order matters for P-07 and P-10: execute the `setup.cfg` + cap edits of §1 first, then
`lint-imports`, then the cap test — P-07 is authored only on a green result.

---

## 4. FR17 split plan — coverage table skeleton per file

Legend: **P1** = goes to Part 1 (measured, row above) · **P2** = Part 2 Implementation ·
**U-n** = prose rule with NO mechanical measure (→ Part 2 or delete; PE fills the last
column) · **B** = measured by a check outside the D13 enumeration (§5; Part 2 with its
check cited unless promoted at the sitting) · **STALE** = contradicts the tree today.

### 4.1 `ARCHITECTURE.md`

| Current section (line) | Content | Disposition | Notes for PE |
|---|---|---|---|
| Overview (24–58) | three-ring diagram, ring responsibilities | P2 | keep the mermaid; it is the Part-2 map |
| Overview | "New feature code depends on ports" | P1 → P-01 | |
| Overview | "accepted-ignore-edge cap ratchets only downward … same commit" | P1 → P-10 | |
| Overview | "`container.py` is the only general composition root" | **U-1** | partially implied by P-08/P-07; no check asserts a single root |
| Overview | "function-scoped lazy import keeps load-time posture" | **U-2** | idiom, not a rule; Part 2 or delete |
| Overview | "ships no agent-execution runtime" | **U-3** | product statement; Part 2 |
| Context and SDD (62–70) | spec_context ownership, hook composition | P2 | |
| Context and SDD | "There is no lease or locking module" | **U-4** | no test asserts absence; Part 2 (Concurrency) |
| The resolution seam (72–89) | single authority, three importers | P1 → P-09 | |
| The resolution seam | "no hook imports `container`" | P1 → P-12 | |
| The resolution seam (90–94) | exit codes / git identity fallback | **U-5** | implementation notes; Part 2 |
| Git chokepoints (96–101) | scripts list | P2 | |
| chokepoints purity (103–110) | "imports no `infrastructure` module and spawns no subprocess" | **STALE** | `setup.cfg:84` declares `chokepoints.service → infrastructure.jsonl_log_rotation` (lazy). Rewrite as "no module-load-time edge; one function-scoped edge, capped under P-10" |
| GitObjectReader (112–121), redaction (123–131) | port contracts | P2 | |
| Handoffs, Panel (133–146) | | P2 | |
| Public assets (148–168) | projection chain; "generated files never edited in place"; "underived core surface is forbidden" | P2 + **B-1** (`test_agentic_entities_derivation.py`, `dadaia public doctor`) | |
| Specs and memory (170–190) | lint one-sourced, catalog derived, frontmatter closed | P2 + **B-2** (`test_public_scripts_thin_wrapper.py`), **B-3** (`test_memory_catalog_render_contract.py`, frontmatter schema) | |
| Specs and memory | SpecsDoctor coordinator + drift-guard | P1 → P-13 (pointer) + P2 | |
| Other feature domains (192–206) | "ACTIVE/LEDGER grammar has exactly one owner" | **U-6** | verify against `test_backlog_status_vocabulary_contract.py`; if it does not assert single-parser, U |
| Other feature domains | "event-sourced bug state" | **STALE** | D11/FR2: one record per bug, mutable governance fields — rewrite |
| Concurrency (208–216) | no-lock rule | **U-7** | law lives in `DADAIA.md` §3; Part 2 pointer, no restatement |
| Runtime State (218–257) | table mirrors `_DADAIA_ALLOWED_SUBDIRS`; repo hygiene | P2 + **B-4** (`dadaia doctor` ROOT-4; `test_source_repo_hygiene.py`) | |
| Core file-I/O authorized set (259–266) | six-module set | P1 → P-11 | |
| Core file-I/O (268–285) | atomic_write rationale; "one writer, proven by scan" | P2 + **B-5** (`tests/unit/core/test_atomic_write_census.py`) | |
| Agent Surface (287–295) | roles, SDD ownership | P2 | |
| Agent Surface (297–313) | persona 120–220-line target; five above it | **U-8** | text itself admits it is unmet → cannot be Part 1; Part 2 "target" |
| Agent Surface (314–317) | "`rules-skills-map.json` … one contract test" | **STALE** | retired by T-050-19 → `behavior-map.json`, P-17 |
| Agent Surface (319–323) | "law reaches each harness exactly once" | **U-9** | verify against install tests; else Part 2 |
| Architecture Diagrams — doctor (329–413) | | P1 → P-13 + P2 | |
| Architecture Diagrams — package map (415–482) | "26 packages", nodes `ai_surface`, `lifecycle`, `workflows`, "ignore-cap 26 = 9/4/13", `lifecycle-no-workflows` contract | **STALE** | 24 packages on disk; three nodes are retired packages; that contract was deleted in v0.3.0. The drift guard checks packages **forward only** (live ⊆ diagram), so stale nodes pass — regenerate the diagram now; a reverse check is an intake candidate, not this release (A18.3) |
| Architecture Diagrams — panel (484–563) | | P1 → P-13 + P2 | |
| Dependencies (565–568) | wikilinks | P2 | |

### 4.2 `QUALITY.md`

| Current section (line) | Content | Disposition | Notes for PE |
|---|---|---|---|
| Purpose (33–37) | hermetic; never a paid binary without opt-in | **U-10** | conftest autouse backstop exists but no contract asserts the rule; Part 2 |
| Layers table (41–47) | tiers | P2 | |
| Layers (49–63) | four-token intent taxonomy; undeclared = SCAFFOLD | P1 → P-24 (floor) + P2 (taxonomy prose points to `tests/AGENTS.md`) | |
| Layers (65–75) | "enforced over `tests/e2e/**` and nowhere else" | **B-6** (`check_test_intent_declared.py`) + **STALE-ish** | V27 now measures suite-wide; rewrite: e2e gate + suite-wide floor (P-24) |
| Layers (77–87) | conftest backstops; "broad LARGE census is **100**" | **DELETE the 100** (A18.6) | V29 ceiling re-pins to 0 |
| Layers (89–99) | derived-inventory rule (goldens policy-only, one roster, one oracle) | **U-11** | embodied by tests, no check of the rule; Part 2 |
| Layers (101–107) | scan-vacuity two-line convention | **U-12** | census lives in a helper docstring; Part 2 |
| Root Cause, Always (109–120) | "`resolved` event refused unless…" | **U-13** + **STALE** | FR2 retired the event stream; rewrite to the record model; discipline, not measure |
| Redaction At Authoring (122–145) | by-hand masking; `--redact` | **U-14** | push-gate denylist is **B-7** (`test_push_gate_wiring.py`); the authoring rule is discipline |
| Satisfiable Diagnostics (147–174) | healable checks; compensating events | **U-15** + **STALE** | "event-sourced store" language vs D11; Part 2 principle-as-prose |
| Browser Validation (176–183) | | **U-16** | Part 2 |
| Flake Policy (185–193) | quarantine bug-gated; marker set pinned | P1 → P-22, P-28 | |
| Flake Policy (195–202) | cap 8, 30 d, rerun 3, flake < 0.5 % | **U-17** | numbers → reference `PARAMETERS.md`, no restatement |
| Flake Policy (204–209) | pass-on-retry CI step | **B-8** (`test_ci_workflow_hygiene.py` — verify it covers the step) | |
| Test Health (213–216) | three metrics; audit trigger | **U-18** | Part 2 |
| Test Health (218–233) | tier timeouts table; two justified exceptions | P1 → P-21 + P2 | |
| Test Health (235–243) | "census is **100** … is the ceiling" | **DELETE** (A18.6) | replace with "LARGE cap: `PARAMETERS.md`"; see §2.4 |
| Test Health (245–248) | wall-clock baselines, `timeout-minutes` | **U-19** | CI ceilings exist in `ci.yml` but no test pins them; Part 2 |
| Test Health (250–255) | mutmut pinned, off push path | **B-9** (contract test named in the text — locate; if absent, U) | |
| Test Health (257–260) | exact-pin rule for tools | **U-20** | Part 2 |
| CI (267–272) | job list | P2 | |
| CI (274–282) | quarantine excluded from every selector; `--durations`; 80 % floor | P1 → P-22 (preflight arm) + **B-10** (`ci.yml` selectors — pinned by a test? verify) | |
| CI (284–303) | pr-source-guard; security-verdict gate | **B-11** (`test_ci_v2_gitflow_pr_gate.py`, `test_pr_verdict_check_gate.py`) | |
| CI (305–308) | preflight/CI parity | **B-12** (`test_ci_preflight_ci_gating_parity.py`) | strong Tier-B promotion candidate |
| CI (310–314) | bug-surface delta in every verdict | **U-21** | persona allowlist test does not measure verdict content; Part 2 |
| CI (316–320) | consumer-side approval | **B-13** (`test_consumer_validation_recipe.py`) | |
| Complexity And Size (324–334) | ruff ceilings ratchet down | P1 → P-19 | |
| Complexity And Size (336–342) | CLOSURE `## Size accounting` mandatory | **U-22** | no doctor rule; Part 2 |
| Anti-Slop (346–349) | cache flags; forbidden artifacts | **B-14** (venv guard; `test_source_repo_hygiene.py`) | |

### 4.3 `TECHSTACK.md`

| Current section (line) | Content | Disposition | Notes for PE |
|---|---|---|---|
| Snapshot (16) | version lives in `pyproject.toml` only | **B-15** (`test_release_semver_canon.py` — verify scope) else U | |
| Snapshot (17–19) | deps, harness roster (`L1_ENTRY_HARNESSES`), model policy | P2 (+ **B-16** harness roster single-source if `test_harness_env_contract.py` pins it) | |
| Snapshot (20) | closed marker set of eight | P1 → P-28 | |
| Snapshot (20) | coverage ≥ 80 % CI gate; `-p no:cacheprovider`; venv guard | P2 + **B-14** | |
| Snapshot (21) | prohibitions; "features reach infrastructure via ports" | P2 pointer → P-01 (no restatement) | |
| Canonical Commands (23–36) | | P2 | |
| Packaging Notes (38–47) | | P2 | |

### 4.4 Counts for the coverage table

| File | Part-1 principles (Tier A) | Sections with content staying in Part 2 | Unmeasured prose rules (U) | Stale claims to correct |
|---|---|---|---|---|
| `ARCHITECTURE.md` | **17** | all current sections survive as Part 2 | **9** (U-1…U-9) | 4 (chokepoints edge; event-sourced bugs; rules-skills-map; package map 26/retired nodes + dead contract) |
| `QUALITY.md` | **10** | all except the two census sentences (deleted) | **13** (U-10…U-22) | 3 (e2e-only enforcement; `resolved` event; event-sourced store) |
| `TECHSTACK.md` | **1** | all | **0** | 0 |
| **Total** | **28** | | **22** | 7 |

Every U-row is a rule with no measure: by A17.3 it moves to Part 2 as description or is
deleted, and the coverage table records the move. None may appear under `## Part 1`.

---

## 5. Tier B — measured rules D13 did not enumerate (operator/PE decision at the sitting)

Each has an existing check today; promoting one costs one more ADR at the FR20 sitting and
nothing else. Not promoting one leaves it in Part 2 **with its check cited**, which already
satisfies "no unmeasured law in Part 1".

| B-id | Rule | Existing check | Recommend |
|---|---|---|---|
| B-1 | Underived core surface is forbidden (entity registry first) | `tests/contract/test_agentic_entities_derivation.py` | promote — it is a foundational law of the AI surface |
| B-2 | A projected script is a thin wrapper over a package module | `tests/contract/test_public_scripts_thin_wrapper.py` | promote |
| B-5 | One atomic-write primitive, proven by derived census | `tests/unit/core/test_atomic_write_census.py` | promote (note: unit tier) |
| B-12 | Local preflight and CI gate the same check set | `tests/contract/test_ci_preflight_ci_gating_parity.py` | promote — it closes the "local green, CI red" loop the root-cause law forbids |
| B-17 | Hooks validate only at the publication boundary (D9) | `tests/contract/test_hooks_publication_boundary.py` — the SPEC's own ADR 0007 example | promote; FR19 already drafted its ADR |
| B-18 | Session-identity stores have one owner | `tests/contract/test_session_store_ownership.py` | leave Part 2, cite the check |
| B-19 | No test ages a fixture with the real clock against a frozen one | `tests/contract/test_frozen_clock_aging_ratchet.py` | leave Part 2, cite the check |
| B-20 | SDD writers never mutate task markers | `tests/contract/test_sdd_writers_never_mutate_task_markers.py` | leave Part 2, cite the check |
| B-1…B-16 others | see §4 rows | as cited | Part 2 with the check cited |

If the operator promotes B-1, B-2, B-5, B-12 and B-17, the totals become ARCHITECTURE 20 ·
QUALITY 12 · TECHSTACK 1 = 33. The contract-count test (§1 item 5) counts only
`lint-imports`-measured principles against `setup.cfg`, so Tier-B promotion never moves V13.

---

## 6. Findings (architect format)

### [HIGH] The independence contract cannot see three of five cross-feature edges
Location: `setup.cfg:177–197`; `dadaia_workspace/features/reconcile/service.py:12–14`
Issue: four packages are unlisted, so three real sibling imports are invisible to the only
check that measures feature independence.
Why it matters: a principle promoted on this state would be false at birth (A18.5) and the
next `reconcile`-style edge would land silently.
Trade-off if fixed: +3 declared ignores and cap 14 → 17 (a visible, capped debt) versus a
rewrite of `reconcile` (intake). Visibility now, collapse later.
Recommendation: apply §1 items 1–5 in one commit; author P-07 only on a green `lint-imports`.

### [HIGH] The LARGE census ceiling is not true and is not measured
Location: `dadaia-test-stewardship/PARAMETERS.md:10`; `specs/memory/QUALITY.md:85–87, 237–240`
Issue: two values (30 / 100), and the one canonical value (30) is above nothing — 42 e2e
functions exist and no check compares them to 30.
Why it matters: promoting it would place a Sensitive-Equality smell into Part 1.
Trade-off if fixed: the principle admitted is P-26 (one home), not a cap; the cap stays a
remediation target in Part 2. No check written.
Recommendation: delete both `QUALITY.md` numbers; re-pin `_V29_COMPETING_HOME_CEILING` to 0.

### [MEDIUM] The package-map diagram carries three retired packages and a dead contract name
Location: `specs/memory/ARCHITECTURE.md:415–482`
Issue: "26 packages", nodes `ai_surface`/`lifecycle`/`workflows`, "ignore-cap 26 = 9/4/13",
`lifecycle-no-workflows`. The drift guard checks packages forward only, so this passes.
Why it matters: P-13 would claim "diagrams derive from live code" over a diagram that is
visibly stale — the guard's own blind spot.
Trade-off if fixed: regenerating the diagram is a Part-2 edit at CLOSURE (zero code). Adding
the reverse check is a new test — out of A18.3's letter for this FR; route to intake.
Recommendation: regenerate the diagram in the FR17 rewrite; state P-13's scope honestly
("forward for packages, both directions for classes and view modules"); intake the reverse
check.

### [MEDIUM] `setup.cfg` header comment and the ignore-cap test disagree with each other
Location: `setup.cfg:24–25` (says 16, four families "7; 4; 2; 3") vs
`tests/contract/test_import_linter_ignore_cap.py:100–109` (14 = 7/3/2/2)
Issue: the comment-pinned number "kept in sync by review discipline" is stale twice over.
Why it matters: P-10's own text says the two stay in sync; a reader trusts the wrong one.
Trade-off if fixed: one comment line, same commit as §1.
Recommendation: rewrite the header to 17 (7/3/5/2) in the T-050-29 commit.

### [LOW] Two memory claims contradict the tree
Location: `ARCHITECTURE.md:103–104` (chokepoints "imports no `infrastructure` module") vs
`setup.cfg:84`; `ARCHITECTURE.md:314–317` (`rules-skills-map.json`) vs `behavior-map.json`.
Recommendation: correct in the FR17 rewrite; both are Part-2 prose.

---

## 7. Bug-surface axis (FR24)

Direction of this task on the touched features: **reduced**. Production LOC 0 (documentary
plus config). The independence check gains visibility over 3 hidden edges (2 → 5 visible),
`modules =` coverage 20/24 → 24/24 with a test that keeps it there (V32), one competing
numeric home deleted (V29 1 → 0), four stale memory claims corrected. Bug-history evidence:
the frozen-clock chain and the citation-enforcer pair both came from guards nobody had
described in memory — naming each guard beside the rule it measures is what makes the guard
reviewable before it drifts. No new check, no new branch, no new code path.

**Root-cause gate:** PASS — the visible defect (a principle about to be promoted over a
check that could not see its violations) is fixed at the contract, not by wording.
**Architecture-fidelity gate:** PASS with the §6 corrections applied — the SPEC's "15 → 17"
is arithmetic drift already absorbed at HEAD (14 → 17); the LARGE-cap promotion is refused as
misrepresenting a target as a measured principle.
