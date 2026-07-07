# Closure: Release — v0.1.61 — Audit Remediation & Memory Truth

> **Status:** Aprovado
> **Release ID:** v0.1.61
> **Owner:** product-engineer
> **Closed:** 2026-07-07
> **Branch:** `feature/v0.1.61` · **Base:** post-v0.1.60 `main` (`4a433063` lineage) · **Merged:** `3965df4c` (PR #116, squash of `feature/v0.1.61`, 2026-07-07) · **Closure branch:** `chore/v0.1.61-closure`
> **Ship gates:** qa-engineer **APPROVED** (handoff `2026-07-07T120000Z-qa-engineer-v0161-ship-gate.handoff.json`) · security-reviewer **APPROVED** (push-gate keyed to the pushed ref sha `cdab4806`, handoff `2026-07-07T130000Z-security-reviewer-v0161-push-gate.handoff.json`) · CI **35 checks pass** on PR #116, including **both e2e-panel legs** (the `ci.yml` leg is the on-GHA proof of the new shared bootstrap script; `release.yml`'s leg fires on the next version-bump push — evidence plan recorded, see Drifts).
> **Mandate:** Audit-mandated remediation release for the **2026-07-06 full audit** (audit-disposition law) — first of the fixed four-release queue v0.1.61 → v0.1.62 → v0.1.63 → v0.1.64 (Rulings 61-A/61-B).

## Summary

v0.1.61 dispositions **every finding of the 2026-07-06 full audit** (governance lane G-1..G-23
+ tally extras; architecture lane A-1..A-3, D-1..D-3, T-1, C-1, CI-1..CI-2, smoke-matrix,
noqa-inventory) — 41 rows, no silent drops — and restores **memory truth** after the audit
found 12 of 29 atoms drifted because three production PRs (#112 PyPI/0.2.0, #113 README/0.2.1,
#115 fable-5 agent retier) landed with `release: none` and no closure memory pass.

Four things shipped beyond the memory pass: (1) the **constitution 2.1.0 operational-change
lane** (§1) closing the G-18 root cause by law — with the memory-bearing test as the hard
boundary and PRs #112/#113/#115 ratified post-hoc (see "Ratification record" below); (2) the
**`PluginStore` port wired through the composition root** (`container.build_plugin_store()`,
constructor injection into `FileSystemPublicAssetManager`), guarded by an executed-path
CliRunner spy contract shown RED pre-fix (Ruling 61-D) — the port's "consumers depend on this
Protocol, never on the adapter directly" docstring claim is now true; (3) the
**`cli-no-infrastructure` import-linter contract** capping the cli→infra erosion class at 10
recorded, rationale-commented, bidirectionally-ratcheted ignores (`allow_indirect_imports =
True` because `cli → container → infra` is the legal composition-root direction) —
`lint-imports` is now **9 kept / 0 broken**; and (4) a **hygiene batch** (pytest-10 fixture →
full suite 0 warnings; the duplicated 39-line e2e-panel CI bootstrap extracted to the shared
`.github/scripts/bootstrap-panel-ws.sh` + the legacy `primary_context.json` heredocs deleted,
contract-guarded; the expired `agent_tier` schema property dropped; the self-repo AGENTS.md
doubled header collapsed, consuming backlog `selfrepo-agents-md-doubled-header`).

Memory ran in two passes per ADR-6: **pass A at DEFINITION** (drift describing already-shipped
reality — 19 atoms + NEW `pypi-distribution.md` + `specs/AGENTS.md` + constitution 2.1.0) and
**pass B at this CLOSURE** (claims made true BY this release — `architecture.md`,
`quality-assurance.md`; `plugin-packs.md` verified true as written, no edit).

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-61-01 | W0 definition — SPEC/PLAN/TASKS from the 2026-07-07 code read + mandatory grill (operator unavailable → ADR-1..6 operator-overridable + 3 grill corrections); dual-review REJECT folded (`ARCH61-*`/`QA61-*`/`ARCHX`/`QAX` AMEND markers); PM Rulings 61-A..61-D; 41-row disposition table; `Aprovado` after dual re-verify | `977593cf` (queue definition) |
| T-61-10 | W1 FR1+FR2+FR3 — memory truth pass A (G-1..G-17, LINT-1, TREE-5) + NEW `pypi-distribution.md` atom + QA-atom `release.yml` row + C-1 note + constitution §1 operational-change lane + §13 wording → `constitution_version: 2.1.0` (DEFINITION phase) | `92adaeb6` (phase flip → IMPLEMENTATION: `1239afbe`) |
| T-61-20 | W2 FR4 — `container.build_plugin_store()` + `plugin.py` consumes the port via container + `FileSystemPublicAssetManager` constructor injection + executed-path spy contract (RED-first, Ruling 61-D) + AC-9(a) sabotage; branch-point collect pin 4691 | `bee4fdbe` |
| T-61-30 | W3 FR5 — `cli-no-infrastructure` contract (10 recorded edges, `allow_indirect_imports = True`) + cap 26→36 with per-family pin + AC-9(b)(b′) sabotages; `lint-imports` 9 kept / 0 broken | `8a87c8db` |
| T-61-40 | W4(SE) FR6 — T-1 pytest-10 fixture (suite → 0 warnings) + CI-1 `primary_context.json` heredocs deleted + CI-2 shared `.github/scripts/bootstrap-panel-ws.sh` + `test_ci_workflow_hygiene.py` (RED-first 5/5) + AC-9(c)(e) sabotages | `ef482626` |
| T-61-41 | W4(ai-engineer) FR6 — `agent_tier` dropped from the memory-frontmatter schema (+absence pin, AC-9(d) sabotage, public stage→install→doctor) + self-repo AGENTS.md doubled header collapsed (banner count 2→1, body byte-preserved) | `16c6f01c` |
| T-61-60 | W5 FR7 + AC-10 full gates + ship — doctor --fix (ROOT cache + stale lease), `bug-space-war` explicitly deferred to operator, D-2 `dist/` deleted, G-23 v0.1.41 residue relocated + README; full gate set green; QA ship-gate + security push-gate; push; CI watched green; PR #116; merge `3965df4c` | `cdab4806` |
| T-61-70 | W6 FR8 — this CLOSURE.md + memory pass B + 41-row disposition sweep + 2 backlog returns + `selfrepo-agents-md-doubled-header` → delivered + archive handoff to PM | (this closure) |

## Validations

Each row is a triple: description, command, evidence (SHA / stdout snippet / handoff path).
Gate evidence captured at the ship tree (`cdab4806`) and merged as PR #116 (`3965df4c`).

| Description | Command | Evidence |
|-------------|---------|----------|
| AC-10 full suite green, warning-clean | unpiped `pytest` (real exit) | `4684 passed, 17 skipped, 0 warnings, exit 0` — `cdab4806` (branch-point pin 4691 collected, T-61-20; growth = new contract tests, not churn) |
| AC-10 format + lint clean | `ruff format --check` · `ruff check --no-cache` | both exit 0 — `cdab4806` |
| AC-10 types clean | `mypy --strict dadaia_workspace` | exit 0, 312 files — `cdab4806` |
| AC-6 import contracts | `lint-imports --no-cache` | **9 kept / 0 broken**, exit 0; cap 36 (9/4/13 + cli→infra 10) pinned per-family — T-61-30 |
| AC-5 executed-path port wiring (RED-first) | `pytest tests/contract/test_plugin_store_port_wired.py` | RED pre-fix (2 failed + 2 errors — `container.build_plugin_store` absent; AST lens flags direct construction); GREEN post-fix; AC-9(a) sabotage re-inlined `JsonPluginStore()` ⇒ 2 failed ⇒ reverted ⇒ 4 passed — T-61-20 |
| AC-5 plugin behavior byte-locked | plugin goldens (a)/(b) + projection + pipeline + cli + json_plugin_store suites | 36 passed; `git diff` on `tests/integration/_golden/` empty — **zero golden re-baseline** — T-61-20 |
| AC-6 RED probe + ratchet | temp unrecorded cli→infra import · cap 36→35 | `Contracts: 8 kept, 1 broken` (cli-no-infrastructure BROKEN) ⇒ reverted 9/0 · stale-cap test FAILS ⇒ reverted — T-61-30 |
| AC-7 CI hygiene contract (RED-first) | `pytest tests/contract/test_ci_workflow_hygiene.py` | pre-fix `5 failed`; post-fix `5 passed`; AC-9(c) heredoc restore ⇒ FAIL ⇒ reverted — T-61-40 |
| AC-7 0-warnings gate (T-1) | file run + `-W error::pytest.PytestRemovedIn10Warning` | `11 passed`, 0 warnings (was 1); AC-9(e) fixture revert ⇒ `4 passed, 7 errors` ⇒ re-fixed — T-61-40 |
| AC-7 schema property drop (D-1) | schema contract test + `dadaia public stage → install → doctor` | absence pin green; AC-9(d) re-add ⇒ FAIL ⇒ reverted (37 passed); public doctor exit 0 incl. `[ok] public-privacy` — T-61-41 |
| AC-7 single AGENTS.md banner | canonical-banner grep on `repos/dadaia-workspace/AGENTS.md` | count before=2, after=1; body byte-preserved (diff vs `git show HEAD:AGENTS.md` = 8 header lines only) — T-61-41 |
| AC-1..AC-4 memory truth pass A | negative + positive grep transcript + `dadaia specs doctor` | 0 hits for every retired claim; all QA61-2 positive greps present; doctor exit 0, LINT-1/TREE-5 clean; manual sabotage line captured — T-61-10 |
| AC-8 workspace/archive hygiene | `dadaia doctor --fix` + shell (PM) | ROOT-2 `.mypy_cache` deleted; stale `tauan-games` lease GC'd (zero SPEC-DOC-029); `dist/` absent; v0.1.41 residue → `specs/_archive/wip-abandoned/v0.1.41/` + README — T-61-60 |
| AC-10 SDD + backlog doctors | `dadaia specs doctor` · `dadaia backlog doctor` | both exit 0 — T-61-60 |
| AC-10 self-hosting reconcile | `public stage → doctor → install --target all → doctor` | all exit 0, `[ok] public-privacy` — T-61-60 |
| Frozen v0.1.50 no-steal suite | `git diff` vs main on the lease/gate test files | **zero-diff** — every wave (A-3 deferred precisely to protect this) |
| QA ship gate | `dadaia reports validate <handoff>` | **APPROVED** — handoff `2026-07-07T120000Z-qa-engineer-v0161-ship-gate.handoff.json` (1 INFO finding → Drifts) |
| Security push gate (per push-cycle) | pre-push security-verdict chokepoint | **APPROVED** — keyed to pushed ref sha `cdab4806`, handoff `2026-07-07T130000Z-security-reviewer-v0161-push-gate.handoff.json` |
| CI (PR #116) | GitHub Actions | **35 checks pass, 0 failures** — incl. the `ci.yml` e2e-panel leg exercising `.github/scripts/bootstrap-panel-ws.sh` on GHA (the CI-2 proof surface); merge `3965df4c` |

## Drifts

### setup-cfg-header-comment-count-stale (QA INFO finding)

**Description:** The QA ship-gate's single INFO finding: the `setup.cfg` header comment above
the import-linter contracts still says "Current count = 26" while the actual recorded ignore
cap is 36 (9/4/13 + cli→infra 10). Stale prose only — the machine truth (the contracts, the
cap constant, and `test_import_linter_ignore_cap.py`) is correct and bidirectionally pinned.

**Resolution:** Accepted as an opportunistic future fix (one-line comment edit for the next
release that touches `setup.cfg` — v0.1.63 W1 or later). Not worth a post-ship commit cycle.

**Memory updates:** none (memory documents the machine truth, which is correct; the stale
prose is a source comment, not a memory claim).

### public-memory-agents-md-tolerates-claim-now-false (ai-engineer follow-up)

**Description:** ai-engineer flagged (LOW) during T-61-41: `dadaia_workspace/public/data/memory-AGENTS.md:52`
and `public/scaffold/memory/AGENTS.md:52` still say the memory-frontmatter schema "tolerates"
`agent_tier` — false since D-1 dropped the property (the schema is
`additionalProperties: false`, so a carrier is now a hard validation error, not tolerated).

**Resolution:** These are PUBLIC canonical assets (ai-engineer's surface, outside the
product-engineer write set) — recorded here as a **follow-up for ai-engineer**: reword both
lines via the public-asset flow (`stage → install → doctor`) in the next release that opens
the `public/**` surface (v0.1.62 is first in the queue). Not edited by this closure.

**Memory updates:** `specs/memory/architecture.md` §Structured-memory-source already states
the schema is `additionalProperties: false` with `agent_tier` removed (pass A/B truth); the
stale claim lives only in the two public assets.

### plugin-packs-token-estimate-fix-applied-by-pm

**Description:** During the release the `plugin-packs.md` atom carried a drifted
`token_estimate` (LINT-1 class). PM applied the frontmatter correction (now 700) as part of
the LINT-1 sweep coordination — a mechanical frontmatter fix on an atom whose body this
release did not otherwise change.

**Resolution:** Recorded for attribution honesty: the fix is part of the FR1/LINT-1
disposition (row 22), executed by PM shell rather than the PE pass-A commit. `specs doctor`
LINT-1 is clean at close.

**Memory updates:** `specs/memory/product/distribution/plugin-packs.md` (frontmatter
`token_estimate` only; body untouched — seam wording verified true as written, see Memory updates).

### release-yml-e2e-panel-leg-evidence-deferred

**Description:** AC-10 requires the CI-2 shared bootstrap script proven on GHA on BOTH
workflows. This release carries no package version bump, so `release.yml` (fired by a
version-vs-tag mismatch on `main`) did not run — its e2e-panel leg could not execute on GHA
within this release.

**Resolution:** Per the SPEC §7 risk clause: the `ci.yml` e2e-panel leg (35-check PR #116 run)
is the in-release GHA proof of the shared script; the `release.yml` leg runs the **same script
file** and its GHA evidence lands on the next version-bump push (v0.1.62+ or the next package
release). Recorded as the ship-note evidence plan — whoever pushes the next version bump must
watch that leg green (watch-CI-until-green law).

**Memory updates:** none (the QA atom documents the shared-script truth; the deferred evidence
is a closure fact, not a product claim).

### cli-contract-needed-allow-indirect-imports

**Description:** The SPEC's FR5 sketch (plain `forbidden` contract) was insufficient at
implementation truth: without `allow_indirect_imports = True` the contract flagged ~24
legitimate **indirect** `cli → container → infrastructure` chains — the composition-root
direction that is legal by design. The plan bent from "forbidden, edges as ignores" to
"forbidden with `allow_indirect_imports = True`, direct edges only as ignores".

**Resolution:** Adjudicated in-wave (T-61-30, software-architect countersign per ADR-4): the
contract polices exactly the erosion class the audit named (DIRECT cli→infra imports) while
leaving the legal indirect wiring path unflagged. 10 direct edges recorded with rationale
comments; RED probe + bidirectional cap ratchet prove falsifiability both ways.

**Memory updates:** `specs/memory/architecture.md` (pass B — the contract description and the
composition-root exception paragraph both document `allow_indirect_imports = True` and why).

### g23-relocation-via-plain-mv (untracked sources)

**Description:** The G-23 v0.1.41 residue relocation was planned as `git mv`, but both files
were untracked (`GRILL.md` gitignored; `OQ-DECISIONS.md` never added) — `git mv` is impossible
on untracked sources.

**Resolution:** Relocated via plain `mv` (PM shell — the `_archive` FROZEN class applies to
file tools; the operator/PM chokepoint path is the sanctioned lane); `OQ-DECISIONS.md` + the
README breadcrumb are now tracked under `specs/_archive/wip-abandoned/v0.1.41/`.

**Memory updates:** none.

## Memory updates

Memory describes the product **as it is now**; the change history lives here and in
`_archive/`. Pass A was written at DEFINITION (T-61-10, `92adaeb6`); pass B at this CLOSURE.
**Catalog regen:** pass A required it (NEW atom + tldr/summary changes — already run at W1).
Pass B changes **no catalog-indexed field** (body-only edits on two core atoms; product atom
untouched) — the PM's closure `dadaia memory catalog generate` run is a defensive no-op
re-run, expected zero-delta.

**Pass B (this CLOSURE, phase = CLOSURE, MEMORY gate open):**

- `specs/memory/architecture.md` — **edit (core atom, body only).** Enforcement section →
  **9 import-linter contracts** incl. `cli-no-infrastructure` (directed `forbidden`,
  `allow_indirect_imports = True`, 10 capped/rationale-commented/ratcheted ignores; cap
  **36** = 9/4/13/10, per-family pinned); NEW "Declared exception — cli→infrastructure
  (capped debt)" paragraph in Dependency rules (legal direction = `cli → container → infra`,
  the composition root's monopoly); `container.py` gains the `build_plugin_store()` port
  factory; the plugin seam described as **WIRED** (CLI consumes the `PluginStore` port via
  the composition root; `FileSystemPublicAssetManager` injectable; executed-path contract
  named). `release_origin` v0.1.61 (already set at pass A).
- `specs/memory/quality-assurance.md` — **edit (core atom, body only).** CI notes → the
  shared `.github/scripts/bootstrap-panel-ws.sh` bootstrap (both workflows' e2e-panel legs;
  hygiene contract named), no legacy `primary_context.json` state file; NEW warning-clean
  law (full suite 0 warnings; pytest-10 fixture converted); live-scale bracket re-validated
  at closure per QA61-4 (4,339/v0.1.53 → **4,701/v0.1.61**). `release_origin` v0.1.61
  (already set at pass A).
- `specs/memory/product/distribution/plugin-packs.md` — **no body change: verified.** Its
  ports-and-adapters seam wording ("PluginStore port + JsonPluginStore adapter") does not
  imply direct-adapter use by consumers and is **now true as written** (the port is consumed
  via `container.build_plugin_store` since FR4). Frontmatter `token_estimate` corrected by
  PM during the release (see Drifts).

**Pass A (DEFINITION, T-61-10 `92adaeb6` — recorded here for the closure ledger):**
`tech-stack.md` (G-1/G-2 model split + plugin inventory), `product-vision.md` (G-3/G-4),
`agent-orchestration.md` (G-5), `architecture.md` (G-6/G-17), `dadaia-workflows.md` (G-7),
`agent-monitoring.md` (G-8), `server-registry.md` (G-9), `multi-platform-parity.md` (G-10),
`cross-platform-portability.md` (G-11), `panel.md` (G-13), `public-asset-distribution.md`
(G-14), `sdd-gate-v3.md` + `specs-doctor.md` + `workspace-init.md` + `brand-identity.md`
(G-15), `harness-pi.md` (G-16), `workspace-doctor.md` + `lifecycle-foundation.md` +
`workspace-portability.md` (G-17), NEW `product/distribution/pypi-distribution.md` (G-12,
ADR-2), `quality-assurance.md` (`release.yml` row + C-1 note), the workspace
heading-allowlist file + token_estimate fixes (LINT-1), `specs/AGENTS.md` (TREE-5),
`specs/constitution.md` → 2.1.0 (FR3), catalog + index regenerated.

## Dispositions

Disposition sweep per the audit-disposition law and ADR-11 vocabulary — **the full 41-row
SPEC §6 table, each row with terminal disposition + evidence**. Tally: **fixed 32 ·
superseded 1 · deferred 2 (tracked) · rejected 6 (reasoned) = 41** (row 15 counts as fixed
with a recorded operator-deferred residual). Both audit lane files archive to
`specs/audits/_archive/` with v0.1.61-normalized names (G-20; PM `git mv`, see Archive
decision). Bug ledger: **0 open at pick, 0 filed mid-release → no bug terminal events.**

| # | Finding | Sev | Disposition | Evidence |
|---|---|---|---|---|
| 1 | G-1 tech-stack model claims | HIGH | **fixed** | T-61-10 `92adaeb6` — §Model assignments → 5×fable-5(+effort)/4×opus; AC-1 negative grep 0 hits |
| 2 | G-2 plugin-inventory contradiction | HIGH | **fixed** | T-61-10 `92adaeb6` — install-gated rows + `devops` pack row; AC-1 |
| 3 | G-3 product-vision install stale | HIGH | **fixed** | T-61-10 `92adaeb6` — Known-limits updated; AC-1 positive grep (G-10 class) |
| 4 | G-4 product-vision 4-verbs stale | HIGH | **fixed** | T-61-10 `92adaeb6` — 12-verbs truth; AC-1 negative grep 0 hits |
| 5 | G-18 ungated operational span | HIGH | **fixed** | FR3 constitution §1 operational-change lane, `constitution_version: 2.1.0` (T-61-10 `92adaeb6`) + post-hoc ratification record (this CLOSURE) + the pass-A memory truth |
| 6 | G-5 agent-orchestration model lines | MED | **fixed** | T-61-10 `92adaeb6` — same 5/4 split at both cited lines |
| 7 | G-6 architecture 22→23 subcommands | MED | **fixed** | T-61-10 `92adaeb6` — AC-1 positive grep "23 subcommands" + `plugin` in roster |
| 8 | G-7 workflows availability labels | MED | **fixed** | T-61-10 `92adaeb6` — AC-1 positive grep exactly 2 PARTIAL labels |
| 9 | G-8 agent-monitoring stale ×3 | MED | **fixed** | T-61-10 `92adaeb6` — AC-1 positive grep dashboard-only Sessions truth |
| 10 | G-9 server-registry verb roster | MED | **fixed** | T-61-10 `92adaeb6` — AC-1 negative grep `unregister` 0 hits |
| 11 | G-10 multi-platform-parity coverage | MED | **fixed** | T-61-10 `92adaeb6` — AC-1 positive grep `dadaia plugin install` named |
| 12 | G-11 cross-platform completed follow-ups | MED | **fixed** | T-61-10 `92adaeb6` — AC-1 positive grep cross-leg names, zero residue |
| 13 | G-12 PyPI memory coverage missing | MED | **fixed** | T-61-10 `92adaeb6` — NEW `pypi-distribution.md` (AC-3: frontmatter valid, in catalog + index) + QA-atom `release.yml` row |
| 14 | G-19 constitution §13 index claim | MED | **fixed** | T-61-10 `92adaeb6` — §13 generated-TOC wording (AC-4) |
| 15 | G-21 root hygiene (.mypy_cache; bug-space-war) | MED | **fixed** + **deferred residual** | T-61-60 `cdab4806` — `doctor --fix` deleted `.mypy_cache` (ROOT-2); `bug-space-war` **explicitly deferred to operator triage** at ship (operator-created root entry; human-judgment call: `root_exceptions.txt` or relocate) |
| 16 | G-23 v0.1.41 archive residue | MED | **fixed** | T-61-60 `cdab4806` — residue relocated to `specs/_archive/wip-abandoned/v0.1.41/` + README breadcrumb (plain `mv`, untracked sources — see Drifts) |
| 17 | G-13 panel.md Mermaid residue | LOW | **fixed** | T-61-10 `92adaeb6` — AC-1 positive grep zero "Mermaid remains loaded" |
| 18 | G-14 public-asset-distribution 13→14 types | LOW | **fixed** | T-61-10 `92adaeb6` — AC-1 positive grep `plugins` in the 14-type list |
| 19 | G-15 stale-claim cluster (sdd-gate/specs-doctor/workspace-init/brand) | LOW | **fixed** | T-61-10 `92adaeb6` — AC-1 positive grep `features/spec_context/lease.py` |
| 20 | G-16 harness-pi auth claim | LOW | **fixed** | T-61-10 `92adaeb6` — AC-1 positive grep `ANTHROPIC_API_KEY` allowlist qualification |
| 21 | G-22 stale tauan-games lease | LOW | **fixed** | T-61-60 `cdab4806` — lease GC'd; specs doctor zero SPEC-DOC-029 |
| 22 | TREE-5 + LINT-1 (specs/AGENTS.md drift; estimates/headings) | LOW | **fixed** | T-61-10 `92adaeb6` (+ PM `plugin-packs.md` token_estimate, see Drifts) — AC-2: doctor exit 0, LINT-1/TREE-5 clean |
| 23 | G-17 polish cluster (INFO) | INFO | **fixed** | T-61-10 `92adaeb6` — incl. AC-1 positive grep INV-5 prose==table |
| 24 | G-20 audit naming convention | INFO | **fixed** | This CLOSURE + PM `git mv` → `specs/audits/_archive/2026-07-06-full-audit-{governance,architecture}-lane--dispositioned-v0.1.61.md` |
| 25 | LOCK-5 BLOCKED_ATTEMPT telemetry | INFO | **rejected** | Historical signal, working as designed; no action (auditor concurs) — SPEC §6 row 25 |
| 26 | Doctor gap: partial archived release dirs | INFO | **deferred** | Tracked return `specs/backlog/specs-doctor-partial-archive-invariant.md` filed this closure (anchored at `features/specs/doctor_release.py#ReleaseValidator`) |
| 27 | SPEC-DOC-027 legacy release dir names ×2 | INFO | **rejected** | Accepted debt by prior ruling ("preserved until renamed"); renaming archived dirs breaks history links |
| 28 | SPEC-DOC-031 ×9 backlog returns flagged | INFO | **rejected** | Known false-positive class (ADR-6 of the prior queue): the 9 are the deliberately-live returns enumerated in ACTIVE.md |
| 29 | A-1 dead `PluginStore` port | MED | **fixed** | T-61-20 `bee4fdbe` — WIRED via composition root (ADR-3); executed-path spy RED-first + AC-9(a) sabotage; zero golden re-baseline |
| 30 | A-2 unguarded cli→infra edges | MED | **fixed** | T-61-30 `8a87c8db` — capped contract (ADR-4), 10 edges recorded, 9 kept / 0 broken, AC-9(b)(b′) sabotages |
| 31 | A-3 aged `PLATFORM.has_fcntl` TODOs | LOW | **deferred** | Frozen no-steal suite adjacency (risk ≫ value here). Grill correction stands: the audit's "already tracked" anchor was consumed at R6/v0.1.54 → NEW tracked return `specs/backlog/platform-seam-todo-retirement.md` filed this closure |
| 32 | D-1 expired `agent_tier` schema property | LOW | **fixed** | T-61-41 `16c6f01c` — property dropped (zero carriers), absence pin, AC-9(d) sabotage, public flow `[ok] public-privacy` |
| 33 | D-2 stale local `dist/` | LOW | **fixed** | T-61-60 `cdab4806` evidence — deleted at gates wave (gitignored artifact, PM shell); dir absent |
| 34 | D-3 mid-audit cache pollution | LOW | **superseded** | Folded into row 15's G-21 cleanup + the existing repo-cleanliness law; no distinct action |
| 35 | T-1 pytest-10 fixture landmine | LOW | **fixed** | T-61-40 `ef482626` — `@staticmethod` class-scoped fixture; suite 0 warnings; AC-9(e) sabotage |
| 36 | CI-1 legacy `primary_context.json` bootstrap write | LOW | **fixed** | T-61-40 `ef482626` — heredocs deleted from both workflows; hygiene contract assertion (a) |
| 37 | CI-2 duplicated 39-line bootstrap block | LOW | **fixed** | T-61-40 `ef482626` — extracted to `.github/scripts/bootstrap-panel-ws.sh` (bodies verified verbatim-identical pre-extraction); GHA proof on the PR #116 `ci.yml` e2e-panel leg; `release.yml` leg evidence plan recorded (Drifts) |
| 38 | C-1 coverage-gate blind spot | INFO | **rejected** | Working as designed (gate scopes unit+contract; integration covers the 0% rows); durable do-not-slop-fix note added to `quality-assurance.md` (T-61-10) |
| 39 | Smoke-matrix range (`^3.12` vs tested 3.12) | INFO | **rejected** | The classifier list (3.12 only) is the honest claim surface; narrowing the range punishes 3.13 users with no breakage evidence; revisit only with a 3.13 CI leg |
| 40 | ERA001/noqa inventory (arch lane INFO) | INFO | **rejected** | Clean inventory, all noqa carry rationale, working as designed (row restored per Ruling 61-C) |
| 41 | `selfrepo-agents-md-doubled-header` (backlog fold) | LOW | **fixed** | T-61-41 `16c6f01c` — sanctioned hand-sync, banner 2→1, body byte-preserved → backlog `status: delivered`, `delivered_in: v0.1.61` (this closure) |

**Backlog/bug sweep rows (ADR-11 terminal tokens):**

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/backlog/selfrepo-agents-md-doubled-header.md` | backlog | `delivered` (`delivered_in: v0.1.61`) | T-61-41 `16c6f01c`; flipped this closure; PM `git mv` → `specs/backlog/_archive/` |
| `specs/audits/2026-07-06-full-audit-governance-lane.md` | audit | fully dispositioned — v0.1.61 | 28 governance-lane rows above; PM `git mv` → `specs/audits/_archive/...--dispositioned-v0.1.61.md` |
| `specs/audits/2026-07-06-full-audit-architecture-lane.md` | audit | fully dispositioned — v0.1.61 | 12 architecture-lane rows above (+1 backlog fold); PM `git mv` → `specs/audits/_archive/...--dispositioned-v0.1.61.md` |

## Backlog returns

Two deferred rows filed as tracked returns this closure (`status: candidate`, BL-SCHEMA
intents anchored at top-level Python symbols), routed through PM curation and indexed in
`candidates.md`:

- `backlog/candidates.md` (LOW) ← **`platform-seam-todo-retirement`** — retire the aged
  `PLATFORM.has_fcntl` TODOs (in-body `sys.platform` checks in the lock/telemetry lazy
  adapter factories) by consolidating on `PLATFORM.has_fcntl` / the container's platform
  gate. Deferred from v0.1.61 (A-3) because the surface is adjacent to the **frozen v0.1.50
  no-steal suite** — risk ≫ value inside an audit-remediation release. NEW anchor: the
  audit's cited `features-import-infrastructure-direct-debt` was consumed at R6/v0.1.54.
  Anchored at `features/spec_context/locking.py#_default_workspace_lock` (+
  `_default_context_lock`, `features/telemetry/service.py#_default_refresh_lock`).
- `backlog/candidates.md` (LOW) ← **`specs-doctor-partial-archive-invariant`** — a doctor
  invariant flagging **partial archived release dirs** (an `_archive/releases/<id>/` that
  carries none of SPEC/PLAN/TASKS/CLOSURE — the v0.1.41 GRILL-only residue class the G-23
  audit finding exposed). Deferred from v0.1.61 (small new invariant, out of an already-wide
  release). Anchored at `features/specs/doctor_release.py#ReleaseValidator`.

Also indexed: `selfrepo-agents-md-doubled-header` removed from the surviving-candidates
index (removal-on-release; delivered v0.1.61).

## ADR-1 enforcement honesty (Ruling ARCH61-3)

The constitution 2.1.0 **operational-change lane is judgment-enforced only.** No mechanical
gate — neither a doctor invariant nor a hook — enforces the memory-bearing test ("would a
`specs/memory/**` edit be required for memory to stay true?"), because it is mechanically
undecidable (ADR-1: a version-diff heuristic would false-block docs changes and false-pass
retiers). The enforcement surfaces are: (1) **human PR review** — the operator ratifies each
`release: none` change at the PR boundary (plus the still-mechanical sha-keyed security
APPROVE push gate and green CI); and (2) the **reactive next-release memory-truth pass** —
any ungated span that nonetheless creates memory drift obligates the NEXT release to carry a
memory-truth pass (this release itself is the precedent execution of that obligation).

## Ratification record — PRs #112 / #113 / #115

Post-hoc ratification per FR3/ADR-1, recorded as release truth:

| PR | Change | Lane verdict under constitution 2.1.0 §1 |
|---|---|---|
| #112 | package version 0.2.0 + PyPI publish | **in-lane** (version metadata + CI-infra; operator-ordered, sha-matched security APPROVE, CI green) |
| #113 | README rewrite + 0.2.1 | **in-lane** (docs + version metadata; same mitigants held) |
| #115 | fable-5 agent retier (5 agents `model:`/`effort:`) | **out-of-lane** — fails the memory-bearing test (it changed agent behavior and required `tech-stack.md`/`agent-orchestration.md` edits to stay true); named inside §1 as the counter-example. Ratified post-hoc with mitigants recorded (operator-ordered, security handoffs 5/5 sha-valid, CI green); the memory drift it caused was repaid by this release's pass A (G-1/G-5). |

All three ratified through the operator-reviewed PR #116 (the amendment itself shipped only
via that reviewed merge — the ratification act, per FR3).

## Cross-release closure order (Ruling 61-B)

**This release closes FIRST** in the fixed queue v0.1.61 → v0.1.62 → v0.1.63 → v0.1.64. The
SPEC §8 shared-atom merge-order clause binds the later-closing siblings, not this closure:
each later release **REBASES** every shared memory atom (`quality-assurance.md`,
`tech-stack.md`, `architecture.md`, `public-asset-distribution.md`, `agent-orchestration.md`,
`plugin-packs.md`) on THIS closure's closed state — never reverting a correction landed here
— and every subsequent `catalog.json` regen accumulates all prior tldr/summary deltas. PM
owns the phase schedule; `ACTIVE.md` is a single pointer and the queue never holds
DEFINITION/CLOSURE phases concurrently.

## Archive decision

**MOVE** — `specs/releases/v0.1.61/` moves to `specs/_archive/releases/v0.1.61/` via `git mv`
(PM/operator; PE issues no git mutations and runs no shell). PM then executes, in order:
(1) `git mv` both audit files → `specs/audits/_archive/2026-07-06-full-audit-{governance,architecture}-lane--dispositioned-v0.1.61.md`;
(2) `git mv specs/backlog/selfrepo-agents-md-doubled-header.md → specs/backlog/_archive/`;
(3) `dadaia memory catalog generate` (defensive re-run — pass B changed no catalog-indexed
field, expected zero-delta); (4) `dadaia specs doctor` + `dadaia backlog doctor` (both must
exit 0); (5) the release-dir `git mv`; (6) advance `ACTIVE.md` → `release: v0.1.62`,
`phase: DEFINITION` per the queue schedule. **Order law honored: memory pass B + this
disposition sweep land BEFORE `ACTIVE.md` leaves CLOSURE.**
