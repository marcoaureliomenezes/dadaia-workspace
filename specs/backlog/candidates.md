# Backlog index — PM-curated

> **Reconciled 2026-08-14 (third pass, post-v0.8.0).** Every claim below re-verified
> against HEAD on 2026-08-14 after the v0.8.0 ship (PR #189, audit-disposition
> release, both audits archived). This pass materializes the seven v0.8.0 CLOSURE
> "Backlog returns" dispositions: the two stale live release directories archived
> (`v0.2.6`/`v0.2.9` → `specs/_archive/releases/`, commit `c71b21c4`), four new
> candidates + one new idea registered below, one Codex-authored entry adopted, and
> one routed note deliberately **not** materialized (see the decisions list at the
> bottom).
>
> **Addendum 2026-08-14 (post-v0.5.2 hotfix).** Entry #18 registered from the
> APPROVED v0.5.2 pre-push security review (LOW follow-up routing); pick-precedence
> notice updated — the outranking bug was resolved by that hotfix.
>
> Per grill ADR #14 the backlog converges to a single `BACKLOG.md` (ACTIVE + LEDGER)
> inside the dd-lifecycle-skills-family release. **Not anticipated here** — this index
> and the per-file entries remain the format of record until that release lands.

## Pick-precedence notice (DADAIA.md §5)

At release-pick time, open bugs and undispositioned audits **outrank** every fresh
backlog entry in this index. Currently outranking: **none** — bug
`context-alive-sweeps-unrelated-worktree-changes` (MEDIUM) was resolved by hotfix
v0.5.2 (2026-08-14, merge `db753b1c`, `resolved` event in `bugs.jsonl`; `dadaia bugs
status`: 0 open), and both 2026-07 audits left this list on 2026-08-14 when v0.8.0
dispositioned all 18 findings and archived both files to `specs/audits/_archive/`
naming it (`…--dispositioned-v0.8.0`).

**Standing operator decision, pending (v0.8.0 CLOSURE return #3):** is `deferred`
terminal for bug `panel-telemetry-sqlite-corrupts-under-concurrent-access`, or does
it return to the queue? Undecided; will keep surfacing at every pick. The related
dangling-pointer repair is entry #12 below and proceeds either way.

## Active candidates (18)

| # | Entry | Status | PM priority | State at HEAD (2026-08-14) |
|---|---|---|---|---|
| 1 | `push-range-denylist-scan` | candidate | **P1** | Renamed from `whole-tree-denylist-push-scan` (grill ADRs #3/#3b/#4/#5 — scope, no-amnesty invariant, tag coverage, absorbed redaction FR all settled). Grill requirement for the SPEC: **done** (2026-08-14 report). Release 2 in the grill sequence. |
| 2 | `test-suite-remediation-stewardship` | candidate | **P1** | **Rewritten 2026-08-14** (grill ADR #6) on a live baseline: 55 e2e-tier pytest / 41 Playwright / 96 broad vs cap 30; dead dossier ref removed. Excluded from the current release round; strong candidate for its own follow-up release (release 4 in the grill sequence). |
| 3 | `20260814-dd-lifecycle-skills-family` | candidate | **P2** | Intents fixed to canonical anchors; grill E-1…E-7 decisions folded in (ADRs #7–#13) plus the BACKLOG.md consolidation (ADR #14). Release 3 in the grill sequence; implementer `ai-engineer`. |
| 4 | `retire-dead-hotfix-surface` | candidate | **P2** | Unchanged this pass. Dead surface confirmed still in tree at last verification (`cli/commands/specs.py:26,346`, SPEC-DOC-022/023 checks, hotfix templates). Small, riskless removal. |
| 5 | `consumer-side-validation-round` | candidate | P2 | New (grill ADR #1). Inherits consumer-audit externals #3/#6 as acceptance criteria; the 2026-07-15 audit archived 2026-08-14 citing it (`…--dispositioned-v0.8.0`). |
| 6 | `thin-wrapper-projected-scripts` | candidate | P2 | New (grill ADR #2, W6 extraction). Inversion evidence at HEAD: `doctor_memory.py:38-40,357` shells out to the projected script. The 2026-07-18 audit archived 2026-08-14 citing it. |
| 7 | `bug-picked-ledger-event` | candidate | P2 | New (grill ADR #10/E-4). `BugEventKind` closed 6-kind enum (`core/models/bugs.py:30-40`), no `[-]` analogue; architect + software-engineer surface, kept out of the AI-surface release. |
| 8 | `codex-persona-law-context-dehydration` | candidate | P2 | **Adopted 2026-08-14** — authored by parallel Codex session, sanitized and verified at adoption (`a1b68aad`): 9 TOMLs 8,208–22,836 B / 124,557 B total confirmed; false "12 TOML personas" at `harness-codex.md:55` confirmed; registry↔projection wrapper drift (`pre_gate.sh` vs `codex-pre-gate`) confirmed; privacy clean. Codex-only scope; implementer `ai-engineer`. |
| 9 | `python-env-interpreter-probe-hardening` | candidate | P2 | **New 2026-08-14** — materializes the two LOWs of the APPROVED v0.5.1 hotfix security review (handoff `2026-08-14T151941Z-…-full-range`): CWE-426 `os.path.isabs` filter on interpreter candidates (incl. `pyvenv.cfg` value) + `timeout=`/stdin isolation on the `_interpreter_version` probe. Third materialization of a routing asserted twice without a file. Arm-B-lane hardening; `software-engineer`. |
| 10 | `spec-doc-031-citation-classes` | candidate | P3 | **New 2026-08-14** (v0.8.0 CLOSURE return). The check WARNs on inheritance and non-goal citations in archived SPEC/CLOSURE — the 3 predicted v0.8.0 WARNs (V9) are the concrete false-positive case. Proposes citation-consumption vs citation-reference distinction. |
| 11 | `changelog-version-axis-reconciliation` | candidate | P3 | **New 2026-08-14** (v0.8.0 CLOSURE return; promoted from ideas destination by operator mandate). Dated `[0.5.1]` atop three stacked `[Unreleased] — spec release vX` + `[0.5.0] — Unreleased` (CHANGELOG lines 7/30/107/177/236). Owners `software-engineer` + `product-engineer`; ADR-2 never-renumber untouched. |
| 12 | `panel-runtime-reliability-dangling-ledger-pointer` | candidate | P3 | **New 2026-08-14** (v0.8.0 CLOSURE return). `bugs.jsonl:202` defers `panel-telemetry-sqlite…` to a slug consumed by v0.1.52 — terminal deferral target. Fix = appended clarifying event, never a rewrite. Partially gated on the standing operator decision above. |
| 13 | `mutation-testing-tool-selection-and-wiring` | candidate | P3 | v0.7.0 CLOSURE return. No tool wired at HEAD; cadence 1×/release off the push path. |
| 14 | `intent-docstring-mechanical-enforcement` | candidate | P3 (blocked) | v0.7.0 CLOSURE return. Blocked on #2 — enforcing before remediation is an unsatisfiable diagnostic. |
| 15 | `gitflow-reconciliation-merge-mechanic` | candidate | P3 | v0.7.0 CLOSURE return. No "reconciliation" mention in the gitflow skill at HEAD; `ai-engineer` surface. |
| 16 | `memory-path-class-dotfiles` | candidate | P3 | v0.7.0 CLOSURE return. Gate classifies all of `specs/memory/` MEMORY by prefix (`gate_policy.py:56,218-219`); dotfile question undecided. |
| 17 | `redact-foreign-context-names-at-qa-authoring` | candidate | — (absorbed) | v0.7.0 CLOSURE return. **Absorvido como FR na release push-range-denylist-scan (grill ADR #5) — não pickável isoladamente.** |
| 18 | `commit-paths-index-scope-hardening` | candidate | P2 | **New 2026-08-14** (post-v0.5.2 hotfix push) — materializes the single LOW of the APPROVED v0.5.2 security review (handoff `2026-08-14T172631Z-…-scaffold-commit-scope`): `commit_paths` discards its `git add -- <paths>` exit status and commits the WHOLE index (`git commit -m` with no pathspec), so a gitignored scaffold path or operator pre-staged content can land in the scaffold-titled commit — CWE-754 (+CWE-668), OWASP A08, same consent class as the v0.5.2-fixed bug narrowed to index-staged content. Fix: checked `git add` + path-scoped `git commit -m <msg> -- <paths>` + `:(literal)`/`--pathspec-from-file` defence. Residual of the v0.5.2 fix, orbits `git_subprocess`; Arm-B hardening lane with #9; `software-engineer`. |

Priority rationale: #1 is a recurring privacy-leak class whose entire contract the
grill just settled — the root-cause doctrine owes the structural fix; #2 is real,
large, and now truthfully measured, but the operator excluded it from the current
round (ADR #6); #3 is the operator's strategic priority with recurring token payoff
(release 3); #4 remains small/riskless; #5–#7 are grill-mandated feeders of releases
1–2 and the NO-LOCKS gap; #8 is the adopted Codex fidelity boundary (large but
self-contained, pairs naturally with the #3 AI-surface release); #9 and #18 carry
the only open security-review residuals in the index and should ride the next
hotfix/patch window (#18 additionally orbits the surface the v0.5.2 hotfix just
touched, so the context is warm); #10–#12 are v0.8.0 CLOSURE debt with concrete
evidence but no incident driver; #13–#16 are materialized v0.7.0 CLOSURE debt; #17
is not independently pickable. The §5 precedence notice above outranks this whole
table, and final priority is the operator's at pick time.

## Ideas (5)

| Entry | Note |
|---|---|
| `flat-release-ship-task-evidence` | **New 2026-08-14** (v0.8.0 CLOSURE return). Closure freezes the directory before the ship marker can flip (T-080-07 archived `[ ]`); template needs ship evidence outside the archived dir. |
| `tests-agents-md-placeholder-doctor-warning` | v0.7.0 CLOSURE return; check still missing at HEAD (only MEM-PLACEHOLDER-1 exists). |
| `stewardship-relocation-grep-homonym-note` | v0.7.0 CLOSURE return; note still absent from the stewardship skill. |
| `tag-push-carve-out-reachability` | v0.7.0 CLOSURE return; **absorbed** into `push-range-denylist-scan` (grill ADR #4). Not pickable in isolation. |
| `repo-agents-md-symlink-hardening` | v0.7.0 CLOSURE return; `public_assets.py` still has no symlink refusal. |

## Terminal at materialization (never-delete law — recorded, not pickable)

All three archived to `_archive/` by `git mv` per SPEC-DOC-035.

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

## PM disposition decisions — 2026-08-14 (v0.8.0 CLOSURE returns)

Recorded here so the routing trail closes in writing:

1. **`specs/releases/v0.2.6/` + `v0.2.9/` → ARCHIVED** (`c71b21c4`). Both were dead
   husks: CLOSURE `Aprovado`, closed 2026-07-14/2026-07-19, pre-v0.3.0, every
   sibling (v0.2.5/v0.2.7/v0.2.8) already archived. Live `specs/releases/` again
   holds only `README.md`, `.gitkeep`, `ACTIVE.md`.
2. **Resilience-audit title miscount ("21-bug" vs 25-row dataset) → NO ENTRY.** The
   v0.8.0 CLOSURE already records it as a reader note with the correct count (the
   SPEC's "25-row" statement), the file is FROZEN in `_archive/` and may never be
   edited, and no future work exists to track — an unactionable entry would be
   index noise. Traceability lives in that CLOSURE (§"Backlog returns", last item)
   and in this decision record.
3. **CLOSURE return #3 (panel-telemetry deferred-state ruling) → NOT MATERIALIZABLE
   BY PM.** It is an operator decision, not backlog work; carried in the standing
   notice above until ruled.

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
