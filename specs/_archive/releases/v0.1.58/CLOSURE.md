# Closure: Release — v0.1.58 — Harness & Projection Distribution

> **Status:** Aprovado
> **Release ID:** v0.1.58
> **Owner:** product-engineer
> **Closed:** 2026-07-04
> **Branch:** `feature/v0.1.58` · **Base:** v0.1.57 closure · **Merged:** `b0bd8217` (PR #106, squash of `feature/v0.1.58`) · **Closure branch:** `closure/v0.1.58`
> **Ship gates:** qa-engineer **APPROVE** (AC-1..AC-8 traced + spot-run green; golden-first verified by commit order; 9/9 AC-9 evidences specific; slop check clean; AC-12 verified against the tree) · security-reviewer **APPROVED ×4** (zero findings; re-keyed through the CI-fix chain `70d61847 → 60f42904 → c02e74f6 → 1dadfafe`) · CI 35 checks, 0 failures on PR #106 (round 4).

## Summary

v0.1.58 is R10 of the operator-approved 12-release plan — the **second** release of the
R9→R12 continuation mandate — and it makes **harness isolation** mechanical. Harness
isolation had been a first-class *documentation* concept since v0.1.47 (the
`memory/product/harness/` atoms describe "what a claude-only / codex-only / pi-only
workspace installation contains"), but nothing enforced it: `dadaia init` always scaffolded
all four surfaces, harness identity was scattered as bare string literals with no typed
Layer-1/Layer-2 capability model, `public doctor` would false-fail a partial install, and the
consumer-repo `AGENTS.md` fan-out that should keep repo copies fresh was dead by construction
(its trigger — an in-repo `.dadaia/agentic/` marker — contradicts the repo-cleanliness law).

This release lands a **typed core harness registry** (`core/harness_registry.py`) that owns the
L1 entry-harness set `{claude, codex, pi}`, the L2 worker set `{codex, pi}`, capability typing,
and the install-target vocabulary — consumed by 7 formerly-forked roster literals (4 L1 + 3 L2)
under golden-first discipline, with a contract test locking `L2_WORKER_HARNESSES` to
`harness_models.harnesses()` so the identity roster and the model catalog can never silently
diverge. It adds `dadaia init --harness <set>` profiles that scaffold ONLY the chosen harnesses
and persist the selection to `.dadaia/states/harness_profile.json` via a ports-and-adapters
seam (pure `core` model + `parse_harness_set`, an `infrastructure/` JSON adapter mirroring
`json_context_store.py`, an inline init-time write — no new `features→infrastructure` edge). It
makes `public install`-all and `public doctor` **profile-aware** (absent profile ⇒ all-four
back-compat, byte-locked against a captured golden; an out-of-profile runtime physically present
on disk is never silent). And it **redesigns the consumer `AGENTS.md` fan-out** to detect Spec
Context repos via `spec_contexts.json` instead of the forbidden in-repo marker, restore a
divergent consumer root to canonical with a DISTINCT `[updated]` line, and flag stale/missing
consumer copies in `public doctor` instead of `[skip]`ping them — the self-repo skip retained,
the tri-copy untouched.

The workflow-spawn entry-harness auto-default was deliberately **deferred** (Ruling F): PI has no
session env var and Claude is L1-only, so a correct default needs its own design. This CLOSURE
records the distribution machinery into memory (`public-asset-distribution` primary,
`workspace-init`, the three harness atoms, `multi-platform-parity`, `architecture`, a `tech-stack`
pointer), extends the golden-authoring law in `quality-assurance` with the three
environmental-leak classes the three-round CI saga taught, dispositions the two consumed backlog
entries (both anchors survive → CLOSURE archival; bug ledger stays 0 open), and files four backlog
returns (the deferred auto-default, a fan-out slug-containment hardening, the consolidated
golden-platform-normalization layer, and a doc-pass for the self-repo doubled header).

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-58-01 | W0 definition — SPEC/PLAN/TASKS from the 2026-07-04 code read; mandatory release-definition grill on the picked set; ten operator-unavailable rulings (A–J) + three PM binding rulings (K A2-repoint / L A5-lib-owned / M A6-doctor-before-install) recorded; dual definition review (qa REJECT Q1–Q7 + architect REJECT A1–A7) folded → `Aprovado` | `978137ba` · phase-flip `8807ecd6` (squash `b0bd8217`) |
| T-58-10 | W1 FR1 — capture + commit the behaviour goldens BEFORE any refactor: `install_target_resolution_v0158.json` (5 targets), `panel_runtime_validation_v0158.json` (api_workflows/api_agents × claude/codex/pi/bogus), `doctor_all_four_v0158.json` (all-four no-profile report list) — the AC-1 behaviour lock + the FR3 absent-profile back-compat lock | `f6a7ebca` (squash `b0bd8217`) |
| T-58-11 | W1 FR1 — NEW `core/harness_registry.py` (pure core leaf) + consume in the 7 roster-encoding literals (4 L1 + 3 L2 `_LAYER2_HARNESSES` repointed per Ruling K); `model_profiles.py:112` reconciled by the L2⇔`harness_models.harnesses()` contract test; goldens replay byte-identical | `2fcf5009` · marker `f3e49040` (squash `b0bd8217`) |
| T-58-20 | W2 FR2 — `dadaia init --harness <set>` + harness-aware `WorkspaceService.init` + persisted `harness_profile.json` via the A1 ports-and-adapters seam (`HarnessProfile` core model, `HarnessProfileStore` port, `json_harness_profile_store` adapter, inline init-time write); ignore-cap 26 UNCHANGED | `0e247eb4` (squash `b0bd8217`) |
| T-58-30 | W3 FR3 — profile-aware `install`-all (via the adapter) + profile-scoped `doctor` (inline `_compare` block + Q1 codex-parity gate + A3 out-of-profile non-silent); absent-profile byte-equality vs the W1 doctor golden | `e0041a0e` (squash `b0bd8217`) |
| T-58-40 | W4 FR4 — `_consumer_repos_for_root` reimplemented (kept by name) reading `spec_contexts.json` (defensive `json.loads`); fan-out fires with the A5 distinct `[updated]` divergent-restore line; doctor flags `[drift]`/`[missing]`/`[ok]`, never `[skip]`; self-repo skip retained, tri-copy untouched | `1c690135` (squash `b0bd8217`) |
| T-58-50 | W5 FR5 — four per-profile E2Es on `test_public_pipeline.py` (in-process `CliRunner`, staged once, ~6s exec); W3→W5 runtime-loop boundary completed (claude-scope guard); pi-only scripts scaffolded via real `_install_scripts` (FR3-consistent) | `6e16a98b` (squash `b0bd8217`) |
| T-58-60 | W6 gates + ship — full local gates (AC-10); self-hosting reconcile (AC-12 / Ruling M, doctor-before-install, executed + recorded); QA ship gate APPROVE; security push gate; push; three CI-fix rounds; PR #106; merge | gate-evidence `70d61847` · CI-fixes `60f42904` / `c02e74f6` / `1dadfafe` · merge `b0bd8217` |
| T-58-70 | W7 closure — this CLOSURE.md + memory truth + disposition sweep + four backlog returns + candidates R10 row shipped | (this closure) |

## Validations

Each row is a triple: description, command, evidence (SHA / stdout snippet / handoff path).
Gate evidence captured at the W6 tree (`70d61847`); pytest re-verified across the three CI-fix
rounds and on PR #106 (`b0bd8217`).

| Description | Command | Evidence |
|-------------|---------|----------|
| AC-10 full suite green (unpiped, real exit) — 4 runs | `pytest tests/` (no pipe) | `4566 passed, 17 skipped, exit 0` at W5 `6e16a98b`, W6 `70d61847`, and re-verified on the two test-only CI-fix rounds `c02e74f6`/`1dadfafe` and the merged tree `b0bd8217` — QA ship-gate handoff `2026-07-04T124902Z-qa-engineer-v0158-ship-gate` |
| AC-10 format + lint clean | `ruff format --check` · `ruff check --no-cache` | both exit 0 (795 files ruff format) — W6 |
| AC-10 types clean | `mypy --strict dadaia_workspace` | exit 0, 309 files — W6 |
| AC-10 import contracts + ignore-cap unchanged | `lint-imports --no-cache` · `pytest …/test_import_linter_ignore_cap.py` | `8 kept, 0 broken`; ignore-cap `== 26` (9/4/13) **UNCHANGED** — A1 held: `core/harness_registry.py` is a stdlib-only `core` leaf (no new edge) and the persistence seam writes inline (**no** new `features→infrastructure` / `infrastructure→features` edge) — W6 |
| AC-2 typed registry is the single source (7 sites + L2 contract test) | `pytest tests/unit/core/test_harness_registry.py` | 30 passed: `L1_ENTRY_HARNESSES == ("claude","codex","pi")`, `L2_WORKER_HARNESSES == ("codex","pi")`, `is_l2("claude")`/`can_be_workflow_worker("claude")` False; grep proves the tuple/set literals gone from all **7** sites (4 L1 + 3 L2); `frozenset(L2_WORKER_HARNESSES) == frozenset(harness_models.harnesses())` order-independent (reconciles `model_profiles.py:112`) — W1 |
| AC-1 goldens byte-identical post-refactor | `pytest tests/unit/infrastructure/test_install_target_goldens.py` | 4 passed; install/panel/doctor goldens replay **byte-identical** post-registry-refactor (no regeneration; a byte diff is adjudicated INVARIANT) — W1 |
| AC-3/AC-4 `init --harness` scaffolds exactly the chosen set + persists it | `pytest tests/unit/cli/test_init_harness.py tests/unit/features/workspace/test_service_harness_profile.py` | green: `--harness claude` → `.claude/` + hook, no `.codex/`/`.pi/`; `--harness codex,pi` → `.codex/`+`.pi/`, no `.claude/` agents; omitted → all-four (back-compat); `--harness zzz` → exit 2 + width-independent stderr; `harness_profile.json` records the set; idempotent — W2 |
| AC-5 profile-aware install/doctor green (claude/codex/pi-only) | `pytest tests/unit/infrastructure/test_public_assets_profile.py` | 13 green (W3 8 + W5 boundary-1 5): a claude-only tree's report list has **NO `[missing] codex:agents/*.toml (D-CX-1)`** and no `[missing]` `.codex/`/`.pi/`, CLI exit 0; codex-only & pi-only green after the W5 runtime-loop guard; A3 stale-`.codex/`-on-disk emits a non-silent line — W3/W5 |
| AC-5 (Q2/A4) absent-profile back-compat byte-lock | `pytest …::test_absent_profile_doctor_byte_equals_all_four_golden` | PASS — the absent-profile doctor report == `_golden/doctor_all_four_v0158.json` (every pre-v0.1.58 workspace rides on this) — W3 |
| AC-6/AC-7 consumer fan-out fires + doctor flags (registry) | `pytest tests/unit/infrastructure/test_consumer_fanout.py` | 11 passed; RED-first pre-fix `10 failed / 1 passed` (marker-based writes nothing; report list has NO `repos/demo:AGENTS.md` line); post-fix fan-out writes `repos/demo/{AGENTS.md,CLAUDE.md}`, divergent restore emits the DISTINCT `[updated]` line, nested subtree untouched, self-repo skipped, tri-copy not written, doctor `[drift]`/`[missing]`/`[ok]` — W4 |
| AC-8 per-profile E2E (in-process CLI, wall-time budget) | `pytest tests/e2e/features/test_public_pipeline.py::TestPerProfileInit` | 4 passed, ~6.0s test-exec (~7.9s incl. startup, well under the ~30s budget); each asserts the EXACT structure + persisted `harness_profile.json` + a profile-scoped green `public doctor` on BOTH Q7 surfaces (report-list blocker-free AND CLI exit 0) — W5 |
| AC-9 mutation-sanity (9 sabotages → FAIL → revert) | one-line plant per new test | (a)/(a′) L1/L2 site → registry-consumption grep FAIL; (b) init ignores set → claude-only FAIL; (c)/(c′)/(c″) doctor-profile / codex-drift-unconditional / out-of-profile-silence → AC-5 FAIL; (d)/(e) restore in-repo-marker filter → fan-out / `[drift]` FAIL; (f) E2E under init sabotage → claude-only E2E FAIL — all reverted, zero residue — W1..W5 |
| AC-10 SDD doctor | `dadaia specs doctor` | exit 0 — W6 |
| AC-10 backlog doctor | `dadaia backlog doctor` | exit 0 — W6 (no `specs/backlog/**` staged in W1–W5) |
| Frozen v0.1.50 no-steal suite untouched | `git diff <base> -- <frozen lease/gate files>` | **zero-diff** — the release lives in `core/harness_registry.py` (new), `cli/commands/init.py`, `features/workspace/service.py`, `infrastructure/public_assets*.py`, `infrastructure/workspace_guardrail.py`, the 2 panel views, and the 3 L2 sites; it never enters `spec_context`/lease/gate — W6 |
| AC-10 zero `public/**` content change | `git diff <base> -- dadaia_workspace/public/` | **empty** — the release changes projection *package code*, not projected assets; `[ok] public-privacy` reconfirmed on the confirming doctor — W6 |
| AC-12 (Ruling M) self-hosting reconcile — doctor BEFORE install | `public stage` → `public doctor` → (PM record) → `public install --target all` → confirming `public doctor` | stage exit 0 → **pre-install doctor surfaced the FULL consumer write set: 12 targets across 6 repos** (`bothub-provisioner`, `burrinhos-barbe`, `dadaia-bots`, `dd-chain-capture`, `dd-chain-explorer`, `tauan-games` — each `[drift]` AGENTS.md + `[missing]` CLAUDE.md), self-repo absent → PM recorded the surfaced set (all lib-owned root-law files, no nested/operator files) → install restored each divergent root with the DISTINCT `[updated]` line + created the CLAUDE.md bridges, self-repo `[skip]` (self-projection) → confirming doctor **exit 0, 0 drift/missing, `[ok] public-privacy`**. Every consumer overwrite appeared in the pre-install surface — no silent clobber — W6 |
| QA ship gate | `dadaia reports validate <handoff>` | **APPROVE**, zero blockers (AC-1..AC-8 traced + spot-run green; golden-first verified by commit order; all 9 AC-9 evidences specific; slop clean; AC-12 claims verified against the tree) — handoff `2026-07-04T124902Z-qa-engineer-v0158-ship-gate` |
| Security push gate (per push-cycle) ×4 | pre-push security-verdict chokepoint | **APPROVED ×4**, zero findings — original keyed to `70d61847`, then **re-keyed through the CI-fix chain `70d61847 → 60f42904 → c02e74f6 → 1dadfafe`** (each test-only CI fix moved the pushed ref sha; every prior approval was superseded, not reused) |
| CI (PR #106) | GitHub Actions | 35 checks, 0 failures — merge gate `b0bd8217` (green on **round 4**, after the three golden-normalization fixes) |

## Drifts

### v0158-three-round-golden-environmental-leak-saga

**Description:** The W1 behaviour goldens — captured to byte-lock the FR1 registry refactor and the
FR3 absent-profile back-compat (`install_target_resolution_v0158.json`,
`panel_runtime_validation_v0158.json`, `doctor_all_four_v0158.json`) — leaked THREE distinct
classes of host/OS-environmental state, invisible on the local Linux capture but turning CI red
across three successive rounds on the `-cross` (Windows/macOS) matrix:

1. **Host denylist state (round 1, `60f42904`).** The doctor golden captured the
   `_check_public_privacy` output, whose privacy walk starts from cwd and scans up for private
   identifiers. On the CI runner the walk hit a different ambient tree than the local capture, so
   the `public-privacy` ok-marker line differed (bare vs baseline ok-marker) — a **host-state read
   resolved from cwd** leaked into a byte-golden.
2. **Directory-iteration order (round 2, `c02e74f6`).** The doctor golden's `.pi/` projection
   lines were captured in the local filesystem's iteration order (`pi/extensions/…` before
   `pi/SYSTEM.md`); Windows enumerated the same directory in a different order, so the report-list
   **multiset was identical but the SEQUENCE differed** and a byte-compare failed on ordering alone.
3. **OS-phrased exec-probe text (round 3, `1dadfafe`).** The D-CX-9 codex-wrapper drift line embeds
   the OS's process-spawn error phrasing — a wrapper exec renders `exited 127` on POSIX vs
   `[WinError 193]` on Windows — so the golden carried an **OS-specific string**.

**Resolution:** Each was fixed **test-only**, never by regenerating the golden to mask a behaviour
change (fix-the-consumer-never-the-golden). Round 1 canonicalized the host-state-dependent privacy
line; round 2 replaced the byte-sequence compare with a **sorted-multiset** lock on the projection
lines (order-independent, invariant preserved); round 3 canonicalized the OS-phrased exec-probe text
to a stable token. The behaviour invariant — target resolution, panel accept/reject, absent-profile
doctor report content — is byte-identical throughout; only platform-variant rendering was normalized.

**LESSON (security reviewer's meta-observation, recorded verbatim intent):** three per-round patches
to the SAME golden-capture harness is the signal that the harness needs a **CONSOLIDATED
platform-normalization layer** — one shared golden-invariance helper (host-state canonicalization +
sorted-multiset locks + OS-phrase canonicalization) applied at capture, rather than re-discovering
each leak class one CI round at a time. Filed as the backlog return
`golden-platform-normalization-layer`. The durable lesson is also written into
`quality-assurance.md` as three new leak classes extending the golden-authoring law.

**Memory updates:** `specs/memory/quality-assurance.md` — the golden-authoring law gains the three
environmental-leak classes (host-state reads resolved from cwd; directory-iteration order →
sorted-multiset locks; OS-phrased exec-probe text → canonicalize with the invariant preserved).

### w3-w5-runtime-loop-boundary-completion

**Description:** W3 (FR3) scoped only the inline `_compare` block to the profile; the
`runtime_expectations` projection loop (`_CLAUDE_DIRS` → `claude:<dir>/*`) stayed UNCONDITIONAL.
That was correct for W3's claude-only tests (claude ∈ profile → `[ok]`), but a **codex-only /
pi-only** `public doctor` would still emit `[missing] claude:*` from that loop. W3 flagged this as a
boundary rather than expanding its own scope.

**Resolution:** W5 completed the boundary in-spirit of FR3 "doctor scopes runtime expectations":
`public_assets.doctor()` hoists the `profile_harnesses`/`active` resolution above the loop and adds a
one-line guard `if not claude_active and label.startswith("claude:"): continue`. RED-first:
neutralizing the guard made codex-only & pi-only doctor emit ×40 `[missing] claude:*` lines and the
CLI exit 1; restoring → green. **Byte-lock preserved:** claude ∈ all-four ⇒ the loop runs fully on
the absent-profile path, so `test_absent_profile_doctor_byte_equals_all_four_golden` and the W1
doctor golden replay byte-identical.

**Memory updates:** captured in `public-asset-distribution.md` (doctor scopes claude/codex/pi runtime
expectations to the profile).

### w5-scripts-boundary-not-scoped

**Description:** A pi-only / agents-only per-target subset init installs **no** chokepoint scripts
(the existing rule installs `.dadaia/scripts/*` only for `{all, claude, codex}` targets). The scripts
doctor check stays UNCONDITIONAL because chokepoints are harness-independent — scoping them would
contradict FR3.

**Resolution:** Recorded as a deliberate boundary (FR3-consistent), **not** a gate change: instead of
scoping the scripts check, the pi-only E2E and unit fixtures **scaffold the scripts** via the real
production `_install_scripts` (exactly what `dadaia public install` runs). No production install-path
change; the chokepoint scripts remain harness-independent.

**Memory updates:** none (behaviour unchanged; `public-asset-distribution.md` / `workspace-init.md`
already state the chokepoints are harness-independent).

### w4-consumer-detection-json-loads-adjudication

**Description:** FR4 reimplemented `_consumer_repos_for_root` to detect consumer repos from
`spec_contexts.json`. The obvious route was `JsonContextStore.list_all()`, but that store raises
`SchemaVersionError` on a v1/unknown registry and its `_load` carries a "not outside
SpecContextService" caveat, so it could crash the fan-out / doctor on a malformed or old registry.

**Resolution:** The reimplementation reads `spec_contexts.json` via a **direct, defensive
`json.loads`** (never-raises contract) rather than the store — a read-only best-effort detection path
that keeps fan-out and doctor from crashing on a bad registry. Same schema (`repo_slug`), no new
infra→infra dependency. Adjudicated as the more honest choice for a detection seam that must degrade
gracefully.

**Memory updates:** `public-asset-distribution.md` (registry-based consumer detection is a defensive
read of `spec_contexts.json`); `architecture.md` (the guardrail-pair fan-out detects consumers via a
defensive `spec_contexts.json` read).

### selfrepo-agents-md-doubled-header (pre-existing, doc-pass)

**Description:** `repos/dadaia-workspace/AGENTS.md` (the self-repo root) carries a **DOUBLED**
workspace-law header — the v0.1.47 one-time hand-sync note stacked above the canonical short header
(lines 1–7 + 9–12). This is a pre-existing v0.1.47 hand-sync artifact, **not** introduced by this
release. Because FR4 RETAINS the `_is_self_repo` skip, the fan-out never rewrites the self-repo copy,
so the doubled header persists.

**Resolution:** Out of scope for v0.1.58 — the self-repo skip is deliberate (the source tree keeps
its hand-synced copy; `install` `[skip]`s self-projection). Filed as the doc-pass backlog return
`selfrepo-agents-md-doubled-header` for a sanctioned hand-sync. Not gate-relevant.

**Memory updates:** none.

## Memory updates

Memory describes the product **as it is now**; the change history lives here and in `_archive/`.
Written this CLOSURE (phase = CLOSURE, MEMORY gate open). Catalog-regen triggers (`tldr`/`summary`/
`area` changed) are flagged; `catalog.json` + `index.md` are **not** hand-edited (PE has no shell) —
the CLI regen (`dadaia memory catalog generate`) + `lint-memory-atoms` exit-0 is a pending
orchestrator step.

- `specs/memory/product/distribution/public-asset-distribution.md` — **primary edit; `summary`
  changed** (→ catalog regen). The install/doctor chain is now **harness-profile-aware** (reads
  `.dadaia/states/harness_profile.json`; absent ⇒ all-four back-compat; explicit `--target X`
  overrides; an out-of-profile runtime present on disk is `[warn]`/`[drift]`, never silent), the
  codex-parity block gates on `codex in profile`, and the consumer `AGENTS.md` fan-out detects Spec
  Context repos via a defensive `spec_contexts.json` read (alive OR dead, minus the self-repo),
  restores a divergent consumer root with a DISTINCT `[updated]` line, and doctor flags
  `[drift]`/`[missing]`/`[ok]` — never `[skip]`. `tldr` **unchanged** (still accurate at the high
  level, within the length cap). `release_origin` → v0.1.58.
- `specs/memory/product/platform/workspace-init.md` — **edit; `summary` changed** (→ catalog regen).
  `dadaia init --harness <set>` scaffolds only the chosen harnesses and persists the selection to
  `.dadaia/states/harness_profile.json` (ports-and-adapters; absent ⇒ all-four back-compat); CLI
  surface line updated. `release_origin` → v0.1.58.
- `specs/memory/product/harness/harness-claude-code.md` / `harness-codex.md` / `harness-pi.md` —
  **body + `release_origin` only; `tldr`/`summary`/`area` UNCHANGED** (no catalog regen). Each gains a
  one-line note that single-harness isolation is now **enforced mechanically at `init`**
  (`dadaia init --harness <set>` + the persisted profile), not only documented. `release_origin` →
  v0.1.58.
- `specs/memory/product/platform/multi-platform-parity.md` — **body + `release_origin` only;
  `tldr`/`summary`/`area` UNCHANGED** (no catalog regen). The Layer-1 entry-harness set
  `{claude, codex, pi}` is now **typed in `core/harness_registry.py`** (its code embodiment; the
  `tech-stack` §Agent runtimes roster stays the doc single source). `release_origin` → v0.1.58.
- `specs/memory/architecture.md` — **body + `release_origin` only; `tldr`/`summary`/`area` UNCHANGED**
  (no catalog regen). The `core/` inventory gains `harness_registry.py` (typed L1/L2 roster consumed
  by the 4 L1 + 3 L2 sites) + the `HarnessProfile` model; `infrastructure/` gains the
  `json_harness_profile_store` adapter (mirrors `json_context_store.py`); the guardrail-pair fan-out
  description updates (registry-based consumer detection via a defensive `spec_contexts.json` read;
  profile-aware install/doctor). Persistence seam is ports-and-adapters (no new `features→infra` /
  `infra→features` edge; ignore-cap 26 unchanged). Feature count unchanged (23). `release_origin` →
  v0.1.58.
- `specs/memory/tech-stack.md` — **small pointer edit; `tldr`/`summary`/`area` UNCHANGED** (no
  catalog regen). §Agent runtimes stays the roster doc single source; adds a one-line pointer that
  the **executable encoding** of the L1/L2 roster is `core/harness_registry.py`, locked to
  `harness_models.harnesses()` by a contract test. `release_origin` → v0.1.58.
- `specs/memory/quality-assurance.md` — **body + `release_origin` only; `tldr`/`summary`/`area`
  UNCHANGED** (no catalog regen). The golden-authoring law is **extended** with the three
  environmental-leak classes taught by the three-round CI saga: (1) host-state reads resolved from cwd
  (canonicalize the host-dependent line), (2) directory-iteration order (lock the report-list with a
  sorted-multiset, not a byte-sequence), (3) OS-phrased exec-probe text (canonicalize with the
  invariant preserved). `release_origin` → v0.1.58.
- `specs/memory/product/catalog.json` + `index.md` — **no hand-edit** (PE has no shell). Two atoms'
  `summary` changed (`public-asset-distribution`, `workspace-init`), so the CLI catalog regen +
  `lint-memory-atoms` exit-0 is a pending orchestrator step. No atom's `area` changed; no `tldr`
  changed.

## Dispositions

Disposition-sweep ledger. Both consumed backlog anchors SURVIVE this release
(`harness-isolation-profiles`: `harness_models.py#harnesses` survives untouched — the identity fix is
a NEW registry, not an edit to that function; `init` survives, gaining `--harness`.
`consumer-agents-md-fanout-redesign`: `_consumer_repos_for_root` survives, reimplemented, **kept by
name** — Ruling G) → archived **at CLOSURE** by the orchestrator `git mv`. No consumed anchor DIED
this release, so there was **no SHIP-time backlog archival**. No implementation-wave commit (W1–W5)
staged any `specs/backlog/**` (AC-11 verified). Bug ledger: **0 open** at pick, **0 open** after — no
bug consumed, none introduced.

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/backlog/harness-isolation-profiles.md` → `specs/_archive/v0.1.58/consumed-backlog/` | backlog | `DELIVERED — v0.1.58` | this CLOSURE (FR1 typed registry + FR2 `init --harness` profiles + persisted profile + harness-aware scaffold + FR3 profile-aware install/doctor + FR5 per-profile E2E; FR6 auto-default deferred → backlog return); orchestrator `git mv` + `consumed_backlog.json` at CLOSURE |
| `specs/backlog/consumer-agents-md-fanout-redesign.md` → `specs/_archive/v0.1.58/consumed-backlog/` | backlog | `DELIVERED — v0.1.58` | this CLOSURE (FR4 registry-based `_consumer_repos_for_root` + A5 lib-owned restore-with-`[updated]` + Ruling J doctor flagging); orchestrator `git mv` + `consumed_backlog.json` at CLOSURE |

## Backlog returns

Four items discovered/deferred during this release, filed as `specs/backlog/<slug>.md`
(status `candidate`), routed through PM curation:

- `backlog/candidates.md` (MEDIUM) ← **`workflow-spawn-entry-harness-autodefault`** — Ruling F
  deferral. The workflow-spawn entry-harness auto-default (enter codex ⇒ `--harness codex`, enter pi
  ⇒ `--harness pi`, explicit flag wins) is not shipped: PI has no session env var
  (`core/session_env.py` carries only `CLAUDE_CODE_SESSION_ID` + `CODEX_SESSION_ID`), and Claude is
  L1-only so never a valid `--harness`. A correct default needs its own detection design. Anchored at
  `core/session_env.py` + `features/lifecycle` spawn seam.
- `backlog/candidates.md` (LOW, security) ← **`fanout-repo-slug-containment`** — the redesigned
  `_consumer_repos_for_root` joins `repos/<repo_slug>/` from the registry; assert the join resolves
  **inside** `repos/` (or reject a multi-component / traversal slug) so a malformed
  `spec_contexts.json` `repo_slug` cannot escape the repos root. Anchored at
  `infrastructure/workspace_guardrail.py#_consumer_repos_for_root`.
- `backlog/candidates.md` (MEDIUM) ← **`golden-platform-normalization-layer`** — the three-round CI
  saga signal (security reviewer's meta-observation): consolidate the per-test normalization helpers
  into **one shared platform-invariance layer** for golden capture (host-state canonicalization +
  sorted-multiset report-list locks + OS-phrase canonicalization), so a new golden is
  platform-invariant by construction instead of re-discovering each leak class one CI round at a time.
  Anchored at `tests/unit/infrastructure/test_install_target_goldens.py` (`_norm_path_line` +
  siblings) + the v0.1.55 golden-authoring law.
- `backlog/candidates.md` (LOW, doc-pass) ← **`selfrepo-agents-md-doubled-header`** — the v0.1.47
  hand-sync left two stacked workspace-law headers on `repos/dadaia-workspace/AGENTS.md`; because
  `install` `[skip]`s self-projection (the `_is_self_repo` skip is retained), the duplicate needs a
  sanctioned hand-sync. Anchored at `repos/dadaia-workspace/AGENTS.md` + the `_is_self_repo` skip in
  `workspace_guardrail.py`.

## Archive decision

**MOVE** — `specs/releases/v0.1.58/` will be moved to `specs/_archive/releases/v0.1.58/` via
`git mv` (by the orchestrator / devops-engineer; PE issues no git mutations), together with the two
CLOSURE-archived consumed backlog entries → `specs/_archive/v0.1.58/consumed-backlog/` +
`consumed_backlog.json` (`DELIVERED — v0.1.58`). `specs/releases/ACTIVE.md` is then advanced by the
orchestrator to the next release (R11 "Panel UX overhaul") or `release: none` if the operator pauses.
(PE does not edit `ACTIVE.md` at this closure per the dispatch scope.)
