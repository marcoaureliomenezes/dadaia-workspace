# Closure: Release — v0.1.55 — Architecture Decomposition

> **Status:** Aprovado
> **Release ID:** v0.1.55
> **Owner:** product-engineer
> **Closed:** 2026-07-03
> **Branch:** `feature/v0.1.55` · **Base:** `26c5089b` (v0.1.54 closure) · **Merged:** `a1fc29f4` (PR #99, squash of `feature/v0.1.55`) · **Closure branch:** `chore/v0.1.55-closure`
> **Ship gates:** qa-engineer **APPROVE** (11/11) · security-reviewer **APPROVED** ×3 (r1 `c36ae08e` / r2 `98678030` / r3 `604e2e4c` — two Windows golden-normalization fix rounds after the first CI run) · CI 38 checks, 0 failures.

## Summary

v0.1.55 is R7 of the operator's R6→R8 continuation mandate — the release that lands the two
structural decompositions the now-CI-enforced import contracts (R6/v0.1.54) were built to
protect, plus the reports feature-shape merge, two open-bug fixes carried forward from R6,
and the first committed UML assets. The `features/specs/doctor.py` god module (2,830 lines,
one `SpecsDoctor` class with 54 methods spanning five validator responsibilities) becomes a
**224-line coordinator** that owns `check()`/`fix()` ORDER and delegates LOGIC to six
single-responsibility sibling validators over two shared leaf modules — behavior proven
byte-identical by a deterministic golden that freezes the clock and normalizes every path.
The 1,279-line `features/panel/views/api.py` monolith is split into **eight per-domain view
modules** (each ≤ 429 lines) and **deleted** outright — no facade, no barrel — with
`container.build_panel_views` wired via explicit named imports and every route response
proven byte-identical by a 24-route golden. The `reports_next`/`reports_retention`/
`reports_validation` triplet merges into one `features/reports/` package, dropping the
feature count from 25 to 23. Throughout, the import-linter ignore-cap holds at **26 (9 infra
/ 4 subprocess / 13 cross-feature)**: every moved edge repoints 1:1, and a
`doctor_types.PidProbe` leaf alias keeps the coordinator off any `spec_context` edge so
cross-feature stays 13, not 14.

The two open bugs carried forward from R6 are fixed with regression tests. `bugs-append-
ignores-persisted-bind` is closed by a **harness-native bind channel**: `dadaia context bind`
now persists a session record keyed by the harness-native session id, and the CLI specs-dir
resolver consults it — guarded to live records only, so a stale or inherited id never
resolves to a foreign context and a codex `dadaia bugs append` (a non-descendant of the
bind) resolves its bound context deterministically instead of erroring. `backlog-new-stub-
readme-lag-intents-schema` is closed at the root by an **idea-status BL-SCHEMA gate**: an
unbound `status: idea` brainstorm is exempt from the typed-`intents[]` requirement (mandatory
at `candidate` and beyond), the `backlog new` stub ships clean out of the box even without a
`catalog.json`, and the public scaffold README documents idea-stage freedom, the subject
kinds, and the non-Python-repo anchor note. `features/workspace_clean` gains a STANDS-ALONE
scope docstring. Finally, three canonical fenced-mermaid diagrams of the post-split shape
land under `specs/assets/architecture/`, guarded by an **introspection drift-guard** that
imports the live modules and fails on any diagram/code name divergence.

This CLOSURE records the decomposition truth into memory (`architecture`, `specs-doctor`,
`panel`, `agent-comms`), the golden-authoring law and module-size ratchet into
`quality-assurance`, the harness-native bind channel into `context-management`, and the
idea-status gate into `sdd-bug-backlog-governance`; it dispositions the one consumed backlog
entry and the two picked bugs (bug ledger 0 open).

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-55-01 | W0 definition (SPEC/PLAN/TASKS from the 2026-07-03 inspection dossier; mandatory release-definition grill on the picked set; dual definition review software-architect REJECT + qa-engineer REJECT → R-1..R-8 + A7/A9 folded → `Aprovado`) | definition commit on `feature/v0.1.55` |
| T-55-10 | W1 FR1 — `SpecsDoctor` decomposition: 224-line coordinator (owns ORDER) + six sibling validators + `doctor_types`/`doctor_common` leaves; deterministic golden byte-identical; `setup.cfg` 4-edge repoint; cap 26 = 9/4/13; module-size ratchet | golden `1213dafb` · split `8511d0ab` |
| T-55-20 | W2 FR3 — `reports_*` triplet → `features/reports/` (history-preserving `git mv`); full production + test repoint; `setup.cfg` −3/+1 + edge #7 target; cap unchanged | relocation `8f918dcf` |
| T-55-30 | W3 FR2 — `panel/views/api.py` → eight per-domain modules, `api.py` deleted (no facade); 24-route golden byte-identical; 14 test importers repointed; zero ignore-edge change | golden `e72c49ef` · split `5cde83b4` |
| T-55-40 | W4 FR4 + FR5 + FR6 — harness-native bind channel (staleness-guarded) + idea-status BL-SCHEMA gate + stub/README + `workspace_clean` docstring; four-case FR4 regression + FR5 E2E | FR4 RED `4f964b1c` · FR4 fix `e95f145f` · FR5 RED `98077727` · FR5+FR6 fix `e71edb06` |
| T-55-50 | W5 FR7 — three fenced-mermaid `.md` diagrams under `specs/assets/architecture/` + introspection drift-guard; `.gitignore` `.md`-only opt-in | assets + drift-guard `docs(T-55-50)` |
| T-55-60 | W6 gates + ship — full local gates; consumed-backlog archival at SHIP; QA ship gate APPROVE 11/11; security push gate r1/r2/r3; CI 38/0 after two Windows fix rounds; PR #99; merge | archival `869e0897` · merge `a1fc29f4` |
| T-55-70 | W7 closure — this CLOSURE.md + memory truth updates + bug dispositions + disposition sweep + candidates R7 row shipped | (this closure) + `61def9d2` (QA-LOW stale-comment sweep) |

## Validations

Each row is a triple: description, command, evidence (SHA / stdout snippet / handoff path).

| Description | Command | Evidence |
|-------------|---------|----------|
| AC-6 full suite green (unpiped, real exit) | `pytest tests/` (no pipe) | `4354 passed, 17 skipped, exit 0` — QA ship-gate handoff `2026-07-03T215930Z` |
| AC-2 FR1 doctor issue-code golden byte-identical | `pytest tests/…/test_doctor_golden.py` | 22 issues (8 errors / 14 warnings), six families interleaved, clock frozen 2026-07-15, paths `<SPECS>`-normalized; GREEN pre- and post-split — W1 `1213dafb`/`8511d0ab` |
| AC-2 FR2 route-response golden byte-identical | `pytest tests/…/test_api_golden.py` | 24 routes across 8 domains, `<TS>`/`<VER>`/`<WS>`-normalized; regenerated against the restored monolith, then reproduced byte-identically from the per-domain modules — W3 `e72c49ef`/`5cde83b4` |
| AC-3 import contracts + ignore-cap | `lint-imports --no-cache` · `pytest …/test_import_linter_ignore_cap.py` | `8 kept, 0 broken` (zero "No matches for ignored import"); cap `== 26` + per-family `9/4/13`; coordinator holds no `spec_context` edge (PidProbe leaf) — QA ship gate |
| AC-1 delegation-only + module-size ratchet | `pytest …/test_module_size_ceiling.py` | coordinator 224 lines / **zero `_check_*` bodies**; `doctor_*.py` ≤ 516; `api_*.py` ≤ 429; `api.py`-stays-deleted guard — W1/W3 |
| AC-4 FR4 regression (four cases, disjoint `ancestry_pids`) | `pytest …/test_specs_resolver…` | RED tail `2 failed, 5 passed` pre-fix → GREEN `7 passed`; non-descendant resolves via the harness-id channel; concurrent two-marker never cross-attributes; descendant still resolves; **stale/inherited id falls through to `BadParameter`** — W4 `e95f145f` |
| AC-4 FR5 E2E clean-idea stub + README | `dadaia backlog new <slug>` → `dadaia backlog doctor` | fresh scaffold **without `catalog.json`** → exit 0, zero BL-SCHEMA; projected README documents idea-freedom + `intents[]`@candidate+ + five subject kinds + `dadaia backlog subjects` — W4 `e71edb06` |
| AC-7 mutation-sanity ×6 (sabotage → FAIL → revert) | one-line plant per new test | (a) FR1 golden FAILED on a mutated `doctor_coherence` description; (b) FR2 golden FAILED on a mutated `api_academy` body; (c) ceiling FAILED on a 719-line stub; (d) FR4 regression FAILED on the sabotaged fix line; (e) `backlog doctor` BL-SCHEMA FIRED on `idea→candidate`; (f) introspection drift-guard FAILED on a diagram-only class rename — all reverted, zero residue — QA gate |
| AC-5 UML assets + introspection drift-guard | `pytest …/test_architecture_diagrams_current.py` | three fenced-```mermaid `.md` under `specs/assets/architecture/` (doctor + panel classDiagrams; 23-feature package graph); 4 bidirectional name-liveness tests GREEN — W5 |
| AC-6 format + lint + types clean | `ruff format --check` · `ruff check --no-cache` · `mypy --strict dadaia_workspace` | all exit 0 (768 files ruff; 302 files mypy) — QA ship gate |
| AC-6 SDD + backlog + projection doctors | `dadaia specs doctor` · `dadaia backlog doctor` · `dadaia public doctor` | specs doctor exit 0; **backlog doctor exit 0 / zero BL-SCHEMA** (post-SHIP archival); `[ok] public-privacy`, exit 0 — W6 |
| Frozen no-touch suite honored | `git diff <base> -- <frozen files>` + QA adjudication | **4/4 zero-diff**, incl. `tests/unit/features/spec_context/test_doctor_lock_gc.py` (different subsystem — `spec_context.doctor.DoctorService`, not `specs.doctor`) — QA ship gate |
| QA ship gate | `dadaia reports validate <handoff>` | **APPROVE** 11/11 — handoff `2026-07-03T215930Z-qa-engineer-v0155-ship-gate` (validated exit 0) |
| Security push gate (per push-cycle) | pre-push security-verdict chokepoint | **APPROVED** ×3 — keyed to `c36ae08e` (r1), `98678030` (r2), `604e2e4c` (r3); r2/r3 are the two Windows golden-normalization fix rounds |
| CI (PR #99) | GitHub Actions | 38 checks, 0 failures — after two Windows golden fix rounds; merge gate `a1fc29f4` |

## Drifts

### windows-golden-normalization-two-ci-rounds

**Description:** The FR1 doctor golden and the FR2 route-response golden were captured on
Linux, where absolute paths render with `/`. On the first CI run both were green on Linux
but **red on the Windows `-cross` matrix**: Windows renders paths with `\`, so the
byte-goldens diverged. Two categories of leak survived the initial `<SPECS>`/`<WS>`
payload-field normalization: (1) path tails embedded in **free-text issue messages**, and
(2) relative paths nested inside **serialized JSON values** (double-backslash-escaped on
Windows). A naive `\d`-style regex normalization is ambiguous — `\d` matches a digit but
also collides with a literal `\dir` Windows path segment — so the replacement had to be
**anchored at the message level** on the `<SPECS>`/`<WS>` token boundary rather than by a
free regex.

**Resolution:** Two Windows golden-normalization fix rounds after the first push (`c36ae08e`):
round 1 (`98678030`) anchored the free-text path-tail normalization; round 2 (`604e2e4c`)
added the two-backslash rule for JSON-nested relative paths. CI went 38/0 green after round
2. Recorded as a **new-golden authoring law**: a golden captured on one platform MUST
normalize platform-variant path rendering at three levels — payload-level for structured
fields; anchored canonicalization for free text; the two-backslash rule for JSON-nested
paths — and be proven byte-stable on the `-cross` jobs before it is trusted. No
behavior change; the production output was always correct — only the golden's capture-time
normalization was platform-naive.

**Memory updates:** `specs/memory/quality-assurance.md` — the golden-authoring law added,
with v0.1.55's two CI rounds as the precedent.

### six-implementation-deviations-adjudicated-sound-at-qa-gate

**Description:** Six places where the literal SPEC/TASKS wording could not be satisfied
verbatim; the implementer chose the semantically-correct alternative and recorded each. All
six were adjudicated **sound (6/6)** at the QA ship gate.

**Resolution:**
- **(W2) reports test-file collision renames.** Merging `tests/unit/features/reports_{next,
  retention,validation}/` into `tests/unit/features/reports/` collided two `test_service.py`
  files; disambiguated to `test_next_service.py` / `test_retention_service.py`
  (`test_resolve_artifact_path.py` kept).
- **(W2) contract README asymmetry-map row collapse.** `tests/contract/README.md` had three
  `reports_*` rows driving `test_lifecycle_asymmetry_map.py`; collapsed to one live `reports`
  row.
- **(W3) api golden `<WS>` normalization.** The route-response golden needed the fixture
  `workspace_root` normalized to `<WS>` for determinism across pytest invocations (a
  normalization beyond the literal AC-2 wording; adjudicated sound — and the precursor to the
  Windows lesson above).
- **(W5) canonical drift-guard filename.** The operator prompt named the guard
  `test_architecture_assets_drift.py`; the SPEC FR7 canonical name
  `test_architecture_diagrams_current.py` was used so the W6 gate + reviewers resolve it.
- **(W5) `.gitignore` `.md`-only opt-in.** The repo `/specs/*` privacy backstop ignored the
  new top-level `specs/assets/` subtree; a minimal privacy-preserving opt-in was added
  mirroring the audits pattern (`!/specs/assets/`, `!/specs/assets/*/`, `/specs/assets/*/*`,
  `!/specs/assets/*/*.md` — `.md` only; no `.svg`/`.mmd`/binary ever tracked). The backstop
  working as designed (no bug registered); unique to this source repo's `.gitignore` (no
  consumer-scaffold template to sync).
- **(W1) two extra external-surface repoints.** Two consumer repoints beyond the enumerated
  W1 write set were required to keep the moved-symbol (`Severity`/`read_active_md`) surface
  green; adjudicated sound.

**Memory updates:** none — all six are test/tooling/source artifacts, not memory atoms. (The
diagram drift-guard + the `.md`-only gitignore opt-in are recorded functionally in
`architecture.md` "Visual evidence" as the committed-assets mechanism.)

### mid-branch-dead-anchor-expected-under-r4-law

**Description:** Between W3 (which deletes `api.py`, killing the
`api.py#render_api_agents_canonical` anchor — the function lives on in `api_agents.py`) and
the SHIP archival, the live consumed backlog entry `architecture-uml-decomposition` (status
`candidate`) referenced its own now-dead anchor, so `dadaia backlog doctor` was **RED with
exactly one BL-SCHEMA error** on the feature branch (from the W3 tip `f8aa799b` through
W4/W5).

**Resolution:** This is the **expected R4/R5 dead-anchor process law**, not a defect: because
the release kills its own consuming entry's anchor, no implementation-wave commit stages any
`specs/backlog/**`, and the entry is archived in **one atomic SHIP commit** (`869e0897`) —
moved to `specs/_archive/v0.1.55/consumed-backlog/` with `consumed_backlog.json` — after all
anchor-killing waves and before the single push. `dadaia backlog doctor` is clean (exit 0) in
the pushed/CI state; the invariant "no W1-W5 commit staged `specs/backlog`" was verified at
archival, and the reports-merge/api-delete anchor-stranding risk on OTHER live entries was
verified clean.

**Memory updates:** none — process/branch-state fact, not a product-state change.

### qa-low-stale-comments-swept-in-closure

**Description:** The QA ship gate raised one LOW advisory: two stale prose comments in
`tests/e2e/panel/test_panel.py` (l.204, l.215) still referenced `views/api.py`, deleted in
W3.

**Resolution:** Swept in the closure commit `61def9d2` (the two comments repointed to the
per-domain `api_*` modules). Not a behavior change — a collateral-comment class caught before
archive, consistent with the closure-time stale-narrative retirement of prior releases.

**Memory updates:** `specs/memory/product/panel/panel.md` — the route diagram + view-modules
list repointed from `views/api.py` to the eight per-domain `api_*` modules (the memory-side
twin of the source-comment sweep).

### two-open-bugs-dispositioned-resolved-v0155

**Description:** Both bugs picked into this release from the R6 open-bug debt —
`bugs-append-ignores-persisted-bind` (MEDIUM, codex) and
`backlog-new-stub-readme-lag-intents-schema` (MEDIUM, claude-layer1) — are FIXED (FR4 and FR5
respectively) with regression tests, per the bug-always-solved law (open bugs outrank plain
backlog at pick).

**Resolution:** Terminal `resolved --release v0.1.55` events appended to the JSONL bug store
at closure (ADDITIVE, no lease). Neither bug was superseded; each carries its own fix + AC-4
regression + AC-7 sabotage. The bug ledger is at **0 open** after these dispositions (the
same closure commit `61def9d2` also swept the QA-LOW stale comments above).

**Memory updates:** none — bug telemetry lives in `specs/bugs/`, not in memory atoms. The
fixes' current-state truth lands in `context-management.md` (FR4 harness-native channel) and
`sdd-bug-backlog-governance.md` (FR5 idea-status gate).

## Memory updates

Memory describes the product **as it is now**; the change history lives here and in
`_archive/`. Written this CLOSURE (phase = CLOSURE, MEMORY gate open):

- `specs/memory/architecture.md` — features **25 → 23** (reports triplet → one `reports`
  package); the `SpecsDoctor` **224-line coordinator** (owns ORDER) + six sibling validators
  + the `doctor_types`/`doctor_common` leaves; the eight per-domain panel `api_*` view modules
  (`api.py` **deleted**, named-import wiring); the `features/specs/doctor` contracts row
  updated to the coordinator; **ignore-cap unchanged 26 = 9/4/13** with the repointed doctor +
  reports edges (post-split enumeration) and the coordinator's PidProbe-leaf
  zero-`spec_context`-edge note; the **module-size anti-erosion ratchet** (doctor 700 / api
  450); `core/session_env.py` + the harness-native specs_dir resolution channel; **Visual
  evidence** → the three committed `specs/assets/architecture/*.md` fenced-mermaid diagrams +
  the REGENERATE-AT-STRUCTURAL-CLOSURE law + the introspection drift-guard. `release_origin` →
  v0.1.55.
- `specs/memory/quality-assurance.md` — the **golden-authoring law** (payload-level +
  anchored free-text + two-backslash rule; two Windows CI rounds as precedent) + the
  **module-size anti-erosion ratchet**. `release_origin` → v0.1.55.
- `specs/memory/product/platform/context-management.md` — the **harness-native bind channel**:
  `bind` persists a session record keyed by the harness-native session id; `_session_context`
  resolves via it when `DADAIA_SESSION_ID` is absent, staleness-guarded to live records only; a
  stale/inherited id never resolves to a foreign bound context. `release_origin` → v0.1.55.
- `specs/memory/product/sdd/sdd-bug-backlog-governance.md` — the **idea-status BL-SCHEMA gate**
  (typed `intents[]` optional at `idea`, mandatory at `candidate`+; not blanket; the clean
  `backlog new` stub + the documented public README). `release_origin` → v0.1.55.
- `specs/memory/product/sdd/specs-doctor.md` — the coordinator + six-validator + two-leaf
  module structure; SPEC-DOC-008 LOGIC now in `doctor_memory`; the 700-line doctor ratchet.
  `release_origin` → v0.1.55.
- `specs/memory/product/agents/agent-comms.md` — the merged `features/reports/` package (the
  validation service now at `features/reports/validation.py`; the `build_reports_*_service`
  factory names unchanged); coverage path corrected. `release_origin` → v0.1.55.
- `specs/memory/product/panel/panel.md` — the route diagram + view-modules list repointed to
  the eight per-domain `api_*` modules (`api.py` deleted). `release_origin` → v0.1.55.
- `specs/memory/tech-stack.md` — **no change**: no dependency added; mermaid rendered natively
  (no mermaid-cli/Node); confirmed at CLOSURE.
- `specs/memory/product/catalog.json` + `index.md` — **no hand-edit**: no atom's `tldr`,
  `summary`, or `area` changed (only body content + `last_updated`/`release_origin`
  frontmatter, which the catalog does not carry). Authoritative regeneration
  (`dadaia memory catalog generate`) + `lint-memory-atoms` exit-0 confirmation is a pending
  orchestrator shell step (PE has no shell tool).

## Dispositions

Disposition-sweep ledger. The consumed backlog entry was archived at SHIP (durable copy +
ledger in the atomic archival commit `869e0897`), per the R4/R5 dead-anchor process law — the
release deletes its own consuming entry's anchor (`api.py#render_api_agents_canonical`), so no
implementation-wave commit staged any `specs/backlog/**`.

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/_archive/v0.1.55/consumed-backlog/architecture-uml-decomposition.md` | backlog | `DELIVERED — v0.1.55` | archival `869e0897`; `consumed_backlog.json` |
| `bugs-append-ignores-persisted-bind` (`specs/bugs/*.jsonl`) | bug | `Closed` (`resolved --release v0.1.55`) | closure `resolved` event; FR4 fix `e95f145f` + AC-4 |
| `backlog-new-stub-readme-lag-intents-schema` (`specs/bugs/*.jsonl`) | bug | `Closed` (`resolved --release v0.1.55`) | closure `resolved` event; FR5 fix `e71edb06` + AC-4 |

Bug ledger: **0 open** after these two dispositions. Neither bug was superseded.

## Backlog returns

None to `ideas.md`/`candidates.md`. The single consumed entry `architecture-uml-decomposition`
shipped in full (all seven intents — doctor split, api split, reports merge, workspace_clean
docstring, UML assets). The R8–R12 conversion sequence continues unchanged in
`specs/backlog/candidates.md` (R7 row now marked **SHIPPED — v0.1.55**).

## Archive decision

**MOVE** — `specs/releases/v0.1.55/` will be moved to `specs/_archive/releases/v0.1.55/` via
`git mv` (by the orchestrator / devops-engineer; PE issues no git mutations).
`specs/releases/ACTIVE.md` will then be advanced to the next release per the operator's R6→R8
mandate (R8 = lifecycle verb governance) or `release: none` if the operator pauses.
