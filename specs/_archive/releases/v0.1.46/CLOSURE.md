# Closure: Release — v0.1.46 — SDD Governance v2

> **Status:** Aprovado
> **Release ID:** v0.1.46
> **Owner:** product-engineer
> **Closed:** 2026-07-01

## Summary

v0.1.46 closes the half-shipped v0.1.14/15 mandate: SDD bug telemetry is now
**event-sourced JSONL** and — critically — its **enforcing rule shipped in the same
release**, so the drift that regrew for five releases cannot silently regrow again.
Bugs live as append-only JSONL event streams at
`specs/bugs/<YYYYMMDDTHH>Z-<n>.jsonl`, written and folded through the new
`dadaia bugs append|status|stats` CLI over a core `BugStore` Protocol. The one-time
migration **ran on this workspace**: 99 legacy `specs/bugs/*.md` were converted into 18
coherent JSONL event streams, every source `.md` was moved to `specs/bugs/_archive/`
in-process, and `specs/bugs/` now holds **zero loose `.md`**. The
`bug-registration-guardrail` rule and the root `AGENTS.md` "Bug Registration" section
were rewritten for the JSONL contract as the R-1 hard pair — no surviving prescription
to author a Markdown bug record.

Around the JSONL core, the release established the **governance taxonomy** the audit
demanded: a FROZEN `_archive` gate class (with the R-2 ordering fix so `_archive/` is
classified before the ADDITIVE `specs/bugs|backlog|audits/` prefixes), an
audit-disposition law in `release-governance.md`, and doctor invariants SPEC-DOC-033
(JSONL schema + rotation + terminal-coherence) and SPEC-DOC-034/035/036
(taxonomy + disposition). Product memory was swept clean of the stale
"OpenCode-as-live" long-tail (~14 atoms, OpenCode was removed in v0.1.24) and the
catalog regenerated.

Shipped via PR #82 (merge `f2fd4e22`), all 35 CI checks green; qa alpha + security
APPROVED, code-review findings resolved and re-verified. One planned descope was
taken: the audit-disposition + backlog-status-normalize + HTML-cluster data sweep (the
non-migration portion of T-46-21) slipped to v0.1.47 under the R-4 valve — the
mechanism ships here, the SPEC-DOC-035 undisposed-audit warnings are now live to
enforce the follow-up.

## Tasks completed

All 13 tasks `[x]`. T-46-21 is `[x]` with the R-4 descope valve taken (76-bug archival
shipped; audit/status/HTML data sweep slipped to v0.1.47 — see Drifts).

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-46-01 | Bug-event JSON schema (+ rejection-case tests) | PR #82 `f2fd4e22` |
| T-46-02 | `BugEvent` model + append-only JSONL store + `redact()` | PR #82 `f2fd4e22` |
| T-46-03 | `dadaia bugs append\|status\|stats` CLI group | PR #82 `f2fd4e22` |
| T-46-04 | Doctor SPEC-DOC-033 (schema + rotation + coherence) | PR #82 `f2fd4e22` |
| T-46-05 | One-time `*.md`→JSONL migration (in-process archive move) | PR #82 `f2fd4e22` |
| T-46-06 | Guardrail rule + AGENTS.md rewrite for JSONL (R-1 pair) | PR #82 `f2fd4e22` |
| T-46-11 | Create `_archive` dirs (workspace + scaffolder + onboarding) | PR #82 `f2fd4e22` |
| T-46-12 | Gate: `_archive` subdirs FROZEN (R-2 ordering fix) | PR #82 `f2fd4e22` |
| T-46-13 | Doctor: taxonomy + disposition invariants (SPEC-DOC-034/035/036) | PR #82 `f2fd4e22` |
| T-46-14 | Audit-disposition law text (release-governance.md) | PR #82 `f2fd4e22` |
| T-46-21 | Disposition data sweep — **PARTIAL (R-4 valve)**: 76-bug archival shipped; audit/status/HTML sweep → v0.1.47 | PR #82 `f2fd4e22` |
| T-46-22 | OpenCode product-memory sweep (~14 atoms) + catalog regen | PR #82 `f2fd4e22` |
| T-46-23 | Minor doctor debt (token_estimate, audit-dir rename, heading allowlist) | PR #82 `f2fd4e22` |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Full test suite green | `pytest` | `4306 passed` |
| Strict type check clean | `mypy --strict` | clean (0 errors) |
| Lint + format clean | `ruff format --check && ruff check` | clean |
| Bug feature layering (features→infrastructure contract) | `lint-imports` | contract clean |
| SDD invariants (incl. SPEC-DOC-033/034/035/036) | `dadaia specs doctor` | 0 errors; 15 warnings (see Drifts — all grandfathered or the slipped-sweep enforcers) |
| Projection consistency + privacy | `dadaia public doctor` | exit 0, `[ok] public-privacy` |
| Migration ran on this workspace | `dadaia specs upgrade` | 99 `.md` → 18 JSONL streams; all `.md` git-mv'd to `specs/bugs/_archive/`; 0 loose `.md` |
| CI on merge | GitHub Actions PR #82 | all 35 checks green |
| Trio review | qa alpha + security-reviewer + code-reviewer | qa APPROVE, security APPROVE, code-review findings resolved + re-verified |
| Windows unit-fast | GitHub Actions (windows) | fixed (separator-agnostic test assertion) |

## Drifts

### t-46-21-descope-valve-r4

**Description:** The 76-bug archival portion of T-46-21 shipped intrinsically with AC-2:
`dadaia specs upgrade` ran the in-process migration, moving all 99 `.md` (including the
76 Closed) to `specs/bugs/_archive/` and emitting 18 JSONL streams; `specs/bugs/` has 0
loose `.md`. The **audit-disposition + backlog-status-normalize + HTML-report-cluster
dedupe** portion was too large to land cleanly in this cycle and was slipped to v0.1.47
under the pre-declared R-4 descope valve.

**Resolution:** The enforcing mechanism (SPEC-DOC-035 undisposed-audit + SPEC-DOC-036
disposition invariants, the FROZEN `_archive` gate class, the audit-disposition law) all
shipped in v0.1.46. The now-live SPEC-DOC-035/036 warnings are exactly the signal that
drives the v0.1.47 sweep. Of specs doctor's 15 warnings: these disposition/taxonomy
warnings plus grandfathered TREE-5 (template drift), SPEC-DOC-027 (legacy names),
SPEC-DOC-029 (stale sample lease), and SPEC-DOC-031 (referenced-EPIC status) — none are
regressions introduced by this release.

**Memory updates:** none — the slipped sweep touches `specs/audits/**` and
`specs/backlog/*.md` statuses, not memory atoms.

### migration-move-shutil-not-git-mv

**Description:** The migration moved the 99 source `.md` files with `shutil.move`, not a
literal `git mv` subprocess call.

**Resolution:** Intentional and correct — the features layer must not shell out
(features-no-subprocess law). Git detects the rename at commit time, so the archive move
is recorded as a rename in history. Precedent: `features/migrate/tree_v2.py`.

**Memory updates:** none.

### features-to-infrastructure-base-debt

**Description:** Pre-existing features→infrastructure layering debt (4 import chains,
tracked by backlog `features-import-infrastructure-direct-debt`) remains in the tree.

**Resolution:** Not touched this release — out of scope. The new bug feature was built
clean against this contract (BugEvent in `core/models/bugs.py` behind a core `BugStore`
Protocol; store in `infrastructure/jsonl_bug_store.py`), and code-review verified the new
code adds no new violations. The 4 legacy chains stay on the backlog for a dedicated
remediation.

**Memory updates:** none — `architecture.md` already reflects the two-layer model.

## Memory updates

Memory writes for this release were performed in the implementation phase under T-46-22
and T-46-23 (PE, DEFINITION/CLOSURE gate window). No further memory change is needed at
closure beyond noting them here — `architecture.md` already reflects the two-layer model
and required no change.

- `specs/memory/product/*.md` (T-46-22) — OpenCode-as-live purged from the ~14 atoms the
  audit listed (`workspace-init`, `product-vision`, `public-asset-distribution`,
  `harness-primitives`, `cross-platform-portability`, `workspace-portability`,
  `agent-sdd-alignment`, `agent-comms`, `agent-orchestration`, et al.); live Layer-1
  harness set now reads `{claude, codex, pi}`.
- `specs/memory/product/index.md` + `catalog.json` (T-46-22) — regenerated via
  `dadaia memory catalog generate`; OpenCode purge is complete (grep of live atoms
  returns zero OpenCode-as-live hits).
- `specs/memory/product/lifecycle-foundation.md` (T-46-23) — `token_estimate` drift
  (LINT-1) corrected.
- `specs/memory/quality-assurance.md` (T-46-23) — heading-allowlist / doctor-debt items
  reconciled.
- `specs/memory/architecture.md` — no change: already reflects the two-layer
  (Layer-1 / Layer-2) model; the bug feature layering is consistent with it.
- `specs/memory/tech-stack.md` — no change: release introduced no new dependency (JSONL
  via stdlib; no third-party addition).

## Dispositions

The release's picked set is the backbone EPIC plus the scoping audit. The 76 Closed bugs
were archived by AC-2's in-process migration move (source `.md` under
`specs/bugs/_archive/`, JSONL streams carry their terminal event — no JSONL event
appended by the archival, per the AC-1 `archived`-is-non-terminal decision). The EPIC
status-line normalization and the ~14 audit dispositions are the R-4-slipped portion and
are dispositioned in v0.1.47 (mechanism enforced by the now-live SPEC-DOC-035/036).

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/backlog/sdd-governance-v2-agents-lifecycle.md` (FEAT-GOV-V2-01) | backlog (EPIC) | `DELIVERED — v0.1.46` (status-line normalization slipped to v0.1.47 sweep) | this CLOSURE + PR #82 `f2fd4e22` |
| `specs/audits/20260701T135346Z-6145b869/` (scoping audit) | audit | disposition + `git mv` to `_archive/` slipped to v0.1.47 (R-4) | SPEC-DOC-035 warning is the live enforcer |
| `specs/bugs/**` (76 Closed `.md`) | bug | archived (source `.md` → `specs/bugs/_archive/`, JSONL terminal event retained) | migration run; `specs/bugs/` 0 loose `.md` |

> **Note (never-delete law upheld).** No bug/backlog/audit file was deleted — all were
> moved to `_archive/` or carry a terminal status. The remaining
> non-terminal-status flips (EPIC status line, audit disposition pointers) are the
> explicitly-slipped v0.1.47 data sweep, not silent drops.

## Backlog returns

- `backlog/candidates.md` ← **v0.1.47 audit-disposition data sweep** (the R-4-slipped
  portion of T-46-21: disposition the ~14 undisposed audits, normalize off-canon backlog
  statuses SPEC-DOC-031/032, dedupe the HTML-report bug cluster into one JSONL stream).
- `backlog/ideas.md` ← **`pytest-suite-leaves-mypy-cache-in-repo-root`** — bug filed by
  qa dogfooding during this release (repo-hygiene: test suite must redirect the mypy
  cache outside the repo tree per the workspace cleanliness law).
- The pre-existing `features-import-infrastructure-direct-debt` backlog item (4 legacy
  layering chains) remains open — not touched this release.

Follow-up notes for v0.1.47 planning: the code-review "redaction was only `notes`"
finding is **FIXED** in this release (`redact()` masks **all** free-text fields, not just
`notes`); the security MEDIUM raised during review is now closed.

## Archive decision

**MOVE** — release directory will be moved to `specs/_archive/releases/v0.1.46/` via
`git mv` (operator performs the move). ACTIVE.md will be updated to point at the next
release or `release: none` after the move.
