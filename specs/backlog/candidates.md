# Backlog index — PM-curated

> **Reconciled 2026-08-14 (second pass, post-grill).** Every claim below re-verified
> against HEAD on 2026-08-14. This pass applies the 2026-08-14 grill refinement report
> (14 operator ADRs): the denylist entry renamed, the suite-remediation entry rewritten
> on a live baseline, three grill-mandated candidates registered, and the twelve
> v0.7.0 CLOSURE "Backlog returns" materialized. Note: the grill report counts the
> CLOSURE returns as 8 (6+2); the CLOSURE text lists **12** (6 candidates + 6 ideas) —
> this index follows the CLOSURE text, the source document.
>
> Per grill ADR #14 the backlog converges to a single `BACKLOG.md` (ACTIVE + LEDGER)
> inside the dd-lifecycle-skills-family release. **Not anticipated here** — this index
> and the per-file entries remain the format of record until that release lands.

## Pick-precedence notice (DADAIA.md §5)

At release-pick time, open bugs and undispositioned audits **outrank** every fresh
backlog entry in this index. Currently outranking:

- **Audit:** `specs/audits/2026-07-15-consumer-dadaia-integration.md` — disposição
  ratificada no grill 2026-08-14 (ADR #1: externals → `deferred`, herdados por
  `consumer-side-validation-round`), **release de disposição pendente** (PE, release 1).
- **Audit:** `specs/audits/2026-07-18-architecture-resilience-review.md` — disposição
  ratificada no grill 2026-08-14 (ADR #2: W6 → `superseded` por
  `thin-wrapper-projected-scripts`, resto `rejected`), **release de disposição
  pendente** (PE, release 1).
- **Open bug:** `context-alive-sweeps-unrelated-worktree-changes` (MEDIUM,
  `bugs.jsonl`) — Arm B on `hotfix/{M.m.p}`, never release material.

Both audits leave this list the moment the PE's audit-disposition release archives
them naming it — ratification alone does not archive.

## Active candidates (12)

| # | Entry | Status | PM priority | State at HEAD (2026-08-14) |
|---|---|---|---|---|
| 1 | `push-range-denylist-scan` | candidate | **P1** | Renamed from `whole-tree-denylist-push-scan` (grill ADRs #3/#3b/#4/#5 — scope, no-amnesty invariant, tag coverage, absorbed redaction FR all settled). Grill requirement for the SPEC: **done** (2026-08-14 report). Release 2 in the grill sequence. |
| 2 | `test-suite-remediation-stewardship` | candidate | **P1** | **Rewritten 2026-08-14** (grill ADR #6) on a live baseline: 55 e2e-tier pytest / 41 Playwright / 96 broad vs cap 30; dead dossier ref removed. Excluded from the current release round; strong candidate for its own follow-up release (release 4 in the grill sequence). |
| 3 | `20260814-dd-lifecycle-skills-family` | candidate | **P2** | Intents fixed to canonical anchors; grill E-1…E-7 decisions folded in (ADRs #7–#13) plus the BACKLOG.md consolidation (ADR #14). Release 3 in the grill sequence; implementer `ai-engineer`. |
| 4 | `retire-dead-hotfix-surface` | candidate | **P2** | Unchanged this pass. Dead surface confirmed still in tree at last verification (`cli/commands/specs.py:26,346`, SPEC-DOC-022/023 checks, hotfix templates). Small, riskless removal. |
| 5 | `consumer-side-validation-round` | candidate | P2 | New (grill ADR #1). Inherits consumer-audit externals #3/#6 as acceptance criteria; the 2026-07-15 audit archives citing it. |
| 6 | `thin-wrapper-projected-scripts` | candidate | P2 | New (grill ADR #2, W6 extraction). Inversion evidence at HEAD: `doctor_memory.py:38-40,357` shells out to the projected script. |
| 7 | `bug-picked-ledger-event` | candidate | P2 | New (grill ADR #10/E-4). `BugEventKind` closed 6-kind enum (`core/models/bugs.py:30-40`), no `[-]` analogue; architect + software-engineer surface, kept out of the AI-surface release. |
| 8 | `mutation-testing-tool-selection-and-wiring` | candidate | P3 | v0.7.0 CLOSURE return. No tool wired at HEAD; cadence 1×/release off the push path. |
| 9 | `intent-docstring-mechanical-enforcement` | candidate | P3 (blocked) | v0.7.0 CLOSURE return. Blocked on #2 — enforcing before remediation is an unsatisfiable diagnostic. |
| 10 | `gitflow-reconciliation-merge-mechanic` | candidate | P3 | v0.7.0 CLOSURE return. No "reconciliation" mention in the gitflow skill at HEAD; `ai-engineer` surface. |
| 11 | `memory-path-class-dotfiles` | candidate | P3 | v0.7.0 CLOSURE return. Gate classifies all of `specs/memory/` MEMORY by prefix (`gate_policy.py:56,218-219`); dotfile question undecided. |
| 12 | `redact-foreign-context-names-at-qa-authoring` | candidate | — (absorbed) | v0.7.0 CLOSURE return. **Absorvido como FR na release push-range-denylist-scan (grill ADR #5) — não pickável isoladamente.** |

Priority rationale: #1 is a recurring privacy-leak class whose entire contract the
grill just settled — the root-cause doctrine owes the structural fix; #2 is real,
large, and now truthfully measured, but the operator excluded it from the current
round (ADR #6); #3 is the operator's strategic priority with recurring token payoff
(release 3); #4 remains small/riskless; #5–#7 are grill-mandated feeders of releases
1–2 and the NO-LOCKS gap; #8–#11 are materialized CLOSURE debt with no incident
driver; #12 is not independently pickable. The §5 precedence notice above outranks
this whole table, and final priority is the operator's at pick time.

## Ideas (4)

| Entry | Note |
|---|---|
| `tests-agents-md-placeholder-doctor-warning` | v0.7.0 CLOSURE return; check still missing at HEAD (only MEM-PLACEHOLDER-1 exists). |
| `stewardship-relocation-grep-homonym-note` | v0.7.0 CLOSURE return; note still absent from the stewardship skill. |
| `tag-push-carve-out-reachability` | v0.7.0 CLOSURE return; **absorbed** into `push-range-denylist-scan` (grill ADR #4). Not pickable in isolation. |
| `repo-agents-md-symlink-hardening` | v0.7.0 CLOSURE return; `public_assets.py` still has no symlink refusal. |

## Terminal at materialization (never-delete law — recorded, not pickable)

| Entry | Status | Evidence |
|---|---|---|
| `loud-flake-stats-key-residual` | delivered | Fixed at HEAD before materialization: `ci.yml:361-374` hard-errors on missing/malformed `stats` (commit `15cb12c4`, T-070-09). |
| `frozen-wall-clock-baselines-in-repo-text` | delivered | Baselines embedded in `quality-assurance.md:147-151`; CI `timeout-minutes` set against them. |
| `dispose-published-denylist-term` | rejected | Void by construction under the range-scoped scan (grill ADR #3b: FROZEN `_archive/` + `git mv` ⇒ no new blob). |

## Rejected entries (retained per never-delete law)

Both archived 2026-08-14 by `git mv`, terminal `rejected_reason` in frontmatter:

| Entry | Reason | Location |
|---|---|---|
| `20260714-panel-games-pong-codex-v026` | Panel Games surface removed in v0.3.0; PI harness support removed — nothing left to validate | `_archive/` |
| `20260714-snake-wall-wrap-v025-pi-validation` | Same removal — nothing left to validate | `_archive/` |

## History — 2026-07-10 consolidation (fully delivered)

All 5 entries of the previous index shipped and live in `_archive/` with terminal
pointers in frontmatter. None of them is pickable work.

| Entry | Delivered in |
|---|---|
| `20260710-lock-lease-session-identity-kernel` (NO-LOCKS doctrine) | v0.1.76 |
| `20260709-central-bind-resolution-seam` | v0.1.77 |
| `20260710-lifecycle-pipeline-correctness-and-diagnosability` | v0.1.78 |
| `20260708-panel-tab-reorg-agentic-layers` | v0.1.79 |
| `20260710-deprecation-strips-and-doctor-cleanup` | v0.1.81 (date gate operator-waived 2026-07-11) |

The NO-LOCKS DOCTRINE ratified in that cycle is now workspace law (DADAIA.md §3); its
full decision record stays in the archived kernel entry.

Known open inconsistency (unchanged): the SPEC-DOC-022/023 governance checks still
police a `## Hotfixes pendentes` intake section in this file that the v0.6.0 law
revoked — this index intentionally does not carry that section; entry #4 is the queued
removal of those checks.

## Archive

`_archive/` holds consumed/superseded/rejected entries; each carries its terminal
pointer in frontmatter.
