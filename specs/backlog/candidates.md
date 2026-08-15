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
> **Addendum 2026-08-14 (v0.9.0 pick — purge-on-pick executed).** Release v0.9.0
> approved by the operator (SPEC/PLAN/TASKS `Aprovado`, branch `feature/v0.9.0`).
> Per the operator-ratified purge-on-pick doctrine (grill ADR #14; provenance:
> `specs/releases/v0.9.0/SPEC.md` §7), the two consumed live entry files were
> removed by the PM — `push-range-denylist-scan.md` (#1, picked as the release
> scope) and `redact-foreign-context-names-at-qa-authoring.md` (#17, absorbed as
> FR8) — riding the T-090-01 definition commit. Their ledger rows below are
> **retained forever** per the never-delete law (the law covers the record; the
> purge removes only the live file). The absorbed idea
> `tag-push-carve-out-reachability` (FR2) has its ledger row flipped; SPEC §7
> delegates no file removal for it ("terminal at closure"), so its file stays.
>
> **Addendum 2026-08-14 (fourth pass, post-v0.9.0 ship).** v0.9.0 shipped (PR #190
> squash `3200bba1`, reconciliation `d5b189db`). This pass materializes the v0.9.0
> CLOSURE "Backlog returns" (rows #1/#17 flipped `DELIVERED — v0.9.0` per the
> archived CLOSURE's Dispositions) **and** the reviewer-routed residuals of the two
> ship security reviews and the round-2 code review: entries #19–#29 (11 new
> candidates) plus one new idea, deduplicated across the three sources — the
> oversized-skip MEDIUM (reported twice) and the batch-parse ValueError LOW
> (reported twice) are ONE entry each citing both handoffs; the 29-latent-blocker
> sizing merged into #19; QA-1 merged into #20. Dedupe/disposition record at the
> bottom.
>
> **Addendum 2026-08-15 (v0.10.0 pick — purge-on-pick executed; first ADR #15
> intake compiled).** Release v0.10.0 approved by the operator 2026-08-15
> (SPEC/PLAN/TASKS `Aprovado`, branch `feature/v0.10.0`). Purge-on-pick (ADR #14;
> provenance: `specs/releases/v0.10.0/SPEC.md` §7): the picked entry file
> `20260814-dd-lifecycle-skills-family.md` (#3) removed by the PM, riding the
> T-100-01 definition commit; ledger row retained. Candidate #8
> (`codex-persona-law-context-dehydration`) explicitly **NOT absorbed** (SPEC
> §4.2/§6-D) — stays live, with a baseline-invalidation note (v0.10.0 edits three
> personas rendered into the Codex TOMLs; PM re-measures the 124,557 B baseline
> after ship). The 12 post-v0.9.0 entries received the operator's
> retroactive-adjudication ruling (SPEC §7/§8): the **8 technical residuals**
> (#20 #22 #23 #25 #26 #27 #28 #29) are compiled into the **first ADR #15 intake
> report** for operator decision (approve/reject/discard); the **4 operator
> deferrals** (#19, #21, #24, idea `bugs-jsonl-whole-blob-per-append`) are
> **pre-approved intake** and are not re-adjudicated.
>
> **Addendum 2026-08-15 (fifth pass — both ADR #15 intake reports adjudicated,
> operator-delegated).** The operator delegated the adjudication of intake reports #1
> (`2026-08-15T132600Z-intake.html`) and #2 (`2026-08-15T152234Z-intake.html`) to the
> dispatcher this session; verdicts follow the PM recommendations. Trace recorded on
> every touched entry: "operator-delegated adjudication, 2026-08-15 (goal directive),
> verdicts per PM recommendation". **Report #1:** all eight v0.9.0 technical residuals
> (#20 #22 #23 #25 #26 #27 #28 #29) **APPROVED** — live pickable candidates. **Report
> #2:** 2-1/2-3/2-4/2-5 APPROVED as new entries #32-#35; 2-2 APPROVED AS MERGE into
> #30; 2-7 APPROVED AS MERGE into #8; 2-6 and 2-8 DISCARDED (terminal rows in the
> intake-adjudication ledger section below). **Pre-approved queue executed:** P-1/P-2
> materialized as #30/#31, P-3/P-4 as #36/#37, P-5 as the re-measured #8 baseline
> (126,155 B, nine TOMLs). Index now 34 live candidates + 3 terminal rows.
>
> **Addendum 2026-08-15 (v0.11.0 pick — nine entries picked, files retained).** Release
> `v0.11.0` "scan-v2" approved by the operator 2026-08-15 (SPEC/PLAN/TASKS `Aprovado`,
> branch `feature/v0.11.0`). Picked set: **#19 #20 #22 #23 #25 #26 #27 #28 #29** — the whole
> post-v0.9.0 push-gate residual cluster in one release. Provenance:
> `specs/releases/v0.11.0/SPEC.md` §7; grill report
> `.dadaia/reports/dadaia-workspace/product-engineer/2026-08-15T160500Z-refine-specs.html`.
> **Purge-on-pick is executed in its provenance form, not its deletion form**: each entry
> file is flipped to `status: picked` with a `## Pick provenance (v0.11.0)` section, and
> **no file is removed**, because nine simultaneous deletions would destroy the index rows
> the #31 single-source `BACKLOG.md` consolidation is being written against. Terminal
> `DELIVERED — v0.11.0` rows land at closure via the `dd-release-closure` disposition sweep.
> **Executed 2026-08-15:** all nine flipped terminal at that closure; see `## Ledger`.
> #28 is picked as a **CLOSURE-phase obligation**, not an implementation FR. Four sibling
> entries were evaluated and explicitly **not** picked, each recorded as a named non-goal in
> the SPEC: **#24** (D6's `internal-hostname` structural fix — evaluated, declined: no picked
> intent binds `privacy_baseline.json` and the 29-blocker census carries zero
> `internal-hostname` hits), **#21**, **#2**, and the idea
> `bugs-jsonl-whole-blob-per-append`. No bug and no audit outranked at pick time.
>
> Per grill ADR #14 the backlog converges to a single `BACKLOG.md` (ACTIVE + LEDGER).
> That doctrine now ships in v0.10.0 (law + schema); the **physical consolidation
> follows the ship as delegated PM work** (v0.10.0 SPEC §4.4/D5). Not anticipated
> here — this index and the per-file entries remain the format of record until then.

## Pick-precedence notice (DADAIA.md §5)

At release-pick time, open bugs and undispositioned audits **outrank** every fresh
backlog entry in this index. **Currently outranking: nothing.** The two LOW bugs this
notice named until 2026-08-15 —
`specs-resolver-context-tests-flaky-under-xdist-full-suite` (QA-2) and
`mypy-strict-cache-dir-created-without-cache-dir-env-override` — were **closed by
`hotfix/0.7.1`, merged at `d15bdf4e`**, each carrying a `resolved` event in
`specs/bugs/bugs.jsonl` alongside the `0.7.1` mint; the ledger carries **zero** open
bugs. Both 2026-07 audits remain archived and dispositioned (v0.8.0); no audit
outranks. *(Corrected at the v0.11.0 closure sweep — the notice had gone stale against
the hotfix that cleared it, and the v0.11.0 SPEC §1 already recorded the true state at
pick time. Flagged as a sweep-adjacent fidelity fix, not a disposition.)*

**Standing operator decision, pending (v0.8.0 CLOSURE return #3):** is `deferred`
terminal for bug `panel-telemetry-sqlite-corrupts-under-concurrent-access`, or does
it return to the queue? Undecided; will keep surfacing at every pick. The related
dangling-pointer repair is entry #12 below and proceeds either way.

## Active candidates (25 live + 12 terminal ledger rows)

Numbering is stable (ledger rows are never renumbered — cross-references like
"#9 and #18" and "blocked on #2" depend on it). Rows #1, #3 and #17 are terminal from
earlier releases. Rows **#19 #20 #22 #23 #25 #26 #27 #28 #29** went terminal
**`DELIVERED — v0.11.0`** at that release's closure on 2026-08-15 (disposition sweep,
`dd-release-closure`); their one-line ledger entries are in `## Ledger` below and their
entry files are retained forever per the never-delete law.

| # | Entry | Status | PM priority | State at HEAD (2026-08-14) |
|---|---|---|---|---|
| 1 | `push-range-denylist-scan` | **DELIVERED — v0.9.0** | — (terminal) | **Flipped 2026-08-14 at ship.** The entire v0.9.0 release scope; FR1–FR7 + FR9 delivered, QA-verified 36/36 acceptance ids (`ALPHA-1-QA.md`); CLOSURE Dispositions row 1. Ledger row retained per never-delete law. |
| 2 | `test-suite-remediation-stewardship` | candidate | **P1** | **Rewritten 2026-08-14** (grill ADR #6) on a live baseline: 55 e2e-tier pytest / 41 Playwright / 96 broad vs cap 30; dead dossier ref removed. v0.9.0 added +1 e2e (LARGE census 56 vs cap 30 — CLOSURE Test dispositions row notes the overshoot is owned here). Excluded from the current release round; strong candidate for its own follow-up release (release 4 in the grill sequence). |
| 3 | `20260814-dd-lifecycle-skills-family` | **picked — v0.10.0** | — (terminal) | **Purged from live backlog 2026-08-15** (purge-on-pick, ADR #14; rides T-100-01). Picked as the v0.10.0 release scope — the `dd-` lifecycle-skills family, law dehydration, ADR #14 doctrine (partial: law + schema; physical consolidation delegated to PM post-ship) and ADR #15/FR16 operator-gated intake. Provenance: `specs/releases/v0.10.0/SPEC.md` §7. Flips to `DELIVERED — v0.10.0` at closure. Ledger row retained per never-delete law. |
| 4 | `retire-dead-hotfix-surface` | candidate | **P2** | Unchanged this pass. Dead surface confirmed still in tree at last verification (`cli/commands/specs.py:26,346`, SPEC-DOC-022/023 checks, hotfix templates). Small, riskless removal. v0.10.0 SPEC §7 records it untouched (operator ruling D4). |
| 5 | `consumer-side-validation-round` | candidate | P2 | New (grill ADR #1). Inherits consumer-audit externals #3/#6 as acceptance criteria; the 2026-07-15 audit archived 2026-08-14 citing it (`…--dispositioned-v0.8.0`). |
| 6 | `thin-wrapper-projected-scripts` | candidate | P2 | New (grill ADR #2, W6 extraction). Inversion evidence at HEAD: `doctor_memory.py:38-40,357` shells out to the projected script. The 2026-07-18 audit archived 2026-08-14 citing it. |
| 7 | `bug-picked-ledger-event` | candidate | P2 | New (grill ADR #10/E-4). `BugEventKind` closed 6-kind enum (`core/models/bugs.py:30-40`), no `[-]` analogue; architect + software-engineer surface, kept out of the AI-surface release. v0.10.0 references it by name from `dd-bug-fix` (A8.3) without picking it. |
| 8 | `codex-persona-law-context-dehydration` | candidate | P2 | **Adopted 2026-08-14** — authored by parallel Codex session, sanitized and verified at adoption (`a1b68aad`): 9 TOMLs 8,208–22,836 B / 124,557 B total confirmed; false "12 TOML personas" at `harness-codex.md:55` confirmed; registry↔projection wrapper drift (`pre_gate.sh` vs `codex-pre-gate`) confirmed; privacy clean. Codex-only scope; implementer `ai-engineer`. **v0.10.0 note (2026-08-15):** explicitly NOT absorbed (SPEC §4.2/§6-D) — stays candidate; v0.10.0 edits three personas rendered into the Codex TOMLs, so the 124,557 B baseline is **invalidated at that ship**; PM re-measures and rewrites the baseline then (note appended to the entry file). **2026-08-15 (delegated adjudication):** P-5 executed — baseline re-measured post-v0.10.0 ship (nine TOMLs, **126,155 B** total, was 124,557 B; entry figures rewritten); intake report #2 item 2-7 (stale `public/rules/*.md` taxonomy row at `ai-harness-codex/SKILL.md:99`) **APPROVED AS MERGE** into this entry — operator-delegated adjudication, 2026-08-15 (goal directive), verdicts per PM recommendation. |
| 9 | `python-env-interpreter-probe-hardening` | candidate | P2 | **New 2026-08-14** — materializes the two LOWs of the APPROVED v0.5.1 hotfix security review (handoff `2026-08-14T151941Z-…-full-range`): CWE-426 `os.path.isabs` filter on interpreter candidates (incl. `pyvenv.cfg` value) + `timeout=`/stdin isolation on the `_interpreter_version` probe. Third materialization of a routing asserted twice without a file. Arm-B-lane hardening; `software-engineer`. v0.9.0 SPEC §4 non-goal 5 records it untouched by that release. |
| 10 | `spec-doc-031-citation-classes` | candidate | P3 | **New 2026-08-14** (v0.8.0 CLOSURE return). The check WARNs on inheritance and non-goal citations in archived SPEC/CLOSURE — the 3 predicted v0.8.0 WARNs (V9) are the concrete false-positive case. Proposes citation-consumption vs citation-reference distinction. |
| 11 | `changelog-version-axis-reconciliation` | candidate | P3 | **New 2026-08-14** (v0.8.0 CLOSURE return; promoted from ideas destination by operator mandate). Dated `[0.5.1]` atop three stacked `[Unreleased] — spec release vX` + `[0.5.0] — Unreleased` (CHANGELOG lines 7/30/107/177/236). Owners `software-engineer` + `product-engineer`; ADR-2 never-renumber untouched. v0.9.0's `[0.6.0]` entry was written in the file's current shape per its CLOSURE, not as a reconciliation. v0.10.0 SPEC §7 records it untouched. |
| 12 | `panel-runtime-reliability-dangling-ledger-pointer` | candidate | P3 | **New 2026-08-14** (v0.8.0 CLOSURE return). `bugs.jsonl:202` defers `panel-telemetry-sqlite…` to a slug consumed by v0.1.52 — terminal deferral target. Fix = appended clarifying event, never a rewrite. Partially gated on the standing operator decision above. |
| 13 | `mutation-testing-tool-selection-and-wiring` | candidate | P3 | v0.7.0 CLOSURE return. No tool wired at HEAD; cadence 1×/release off the push path. |
| 14 | `intent-docstring-mechanical-enforcement` | candidate | P3 (blocked) | v0.7.0 CLOSURE return. Blocked on #2 — enforcing before remediation is an unsatisfiable diagnostic. |
| 15 | `gitflow-reconciliation-merge-mechanic` | candidate | P3 | v0.7.0 CLOSURE return. No "reconciliation" mention in the gitflow skill at HEAD; `ai-engineer` surface. The v0.9.0 ship executed the mechanic live (`d5b189db`, tree-identical two-parent merge verified by the reconciliation security review) — evidence for the skill text when picked. |
| 16 | `memory-path-class-dotfiles` | candidate | P3 | v0.7.0 CLOSURE return. Gate classifies all of `specs/memory/` MEMORY by prefix (`gate_policy.py:56,218-219`); dotfile question undecided. |
| 17 | `redact-foreign-context-names-at-qa-authoring` | **DELIVERED — v0.9.0** | — (terminal) | **Flipped 2026-08-14 at ship.** Absorbed as v0.9.0 FR8 (grill ADR #5); `--redact` on all three verbs + the qa-engineer doctrine, A8.1–A8.5 verified (CLOSURE V8, Dispositions row 2). Ledger row retained per never-delete law. |
| 18 | `commit-paths-index-scope-hardening` | candidate | P2 | **New 2026-08-14** (post-v0.5.2 hotfix push) — materializes the single LOW of the APPROVED v0.5.2 security review (handoff `2026-08-14T172631Z-…-scaffold-commit-scope`): `commit_paths` discards its `git add -- <paths>` exit status and commits the WHOLE index (`git commit -m` with no pathspec), so a gitignored scaffold path or operator pre-staged content can land in the scaffold-titled commit — CWE-754 (+CWE-668), OWASP A08, same consent class as the v0.5.2-fixed bug narrowed to index-staged content. Fix: checked `git add` + path-scoped `git commit -m <msg> -- <paths>` + `:(literal)`/`--pathspec-from-file` defence. Residual of the v0.5.2 fix, orbits `git_subprocess`; Arm-B hardening lane with #9; `software-engineer`. v0.9.0 SPEC §4 non-goal 4 records it untouched by that release. |
| 19 | `prior-published-term-amnesty` | **DELIVERED — v0.11.0** | — (terminal) | **New 2026-08-14** (v0.9.0 CLOSURE return, operator-ratified at the code-review round: whole-blob matching KEPT, refinement routed here). A term already published in the remote-reachable version of the SAME path must not refuse. Sized by the round-2 code review at **29 latent blockers under `tests/**`** (that LOW merged here); the sentinel's `tests/**` exclusion names this entry as rationale. Until picked, every long-lived file carrying a matching line is a one-time push blocker whose only escape is `--no-verify`. **ADR #15 retroactive ruling: pre-approved intake (operator deferral).** |
| 20 | `denylist-scan-skip-note-oversized-mislabel` | **DELIVERED — v0.11.0** | — (terminal) | **New 2026-08-14** — merges the SAME defect from both ship reviewers (**MEDIUM in each**: security `2026-08-14T224700Z` CWE-778; code-review round-2 `2026-08-14T222609Z`) + the CLOSURE's QA-1 return (skip-note e2e coverage). The 5 MB fail-open is reported as "binary … not text-decodable" — untrue for oversized TEXT, degrading the disclosed R3 mitigation exactly where it matters. Split counters + honest wording + `decision.warn` tests. Hotfix-eligible per both reviewers; the most operator-visible residual of v0.9.0. **ADR #15: APPROVED at intake (report #1) — operator-delegated adjudication, 2026-08-15 (goal directive), verdicts per PM recommendation. Live pickable.** |
| 21 | `commit-message-scanning-residual` | candidate | P2 | **New 2026-08-14** (v0.9.0 CLOSURE return; SPEC §4.2 operator-ratified non-goal, "defer to backlog at closure" — this is that materialization). Sharpened by the reconciliation review: the final ship range published **0 scannable blob bytes and a 59,263-char squash commit message** the gate structurally cannot see — under squash-merge the residual is the whole release narrative in one object. Scope includes the squash-merge shape + annotated tag bodies per the reviewer. **ADR #15 retroactive ruling: pre-approved intake (operator deferral).** |
| 22 | `registry-derived-foreign-name-set` | **DELIVERED — v0.11.0** | — (terminal) | **New 2026-08-14** — materializes the ship security review LOW (FR3 term source 3): the foreign-name layer enumerates `repos/` directory names only, so a DEAD/relocated registry context contributes no term — protection silently shrinks exactly when a name gets more sensitive. Demonstrated: wider registry set (11 vs 6 terms) yields 2 hits the gate misses (historical content, not a leak). Sequenced with #19 (the layer grows strictly larger; enumerate latent blockers first). **ADR #15: APPROVED at intake (report #1) — operator-delegated adjudication, 2026-08-15 (goal directive), verdicts per PM recommendation. Live pickable.** |
| 23 | `refusal-path-redaction` | **DELIVERED — v0.11.0** | — (terminal) | **New 2026-08-14** (v0.9.0 CLOSURE return, LOW; re-confirmed by the ship security review as the open CWE-532 residual at `service.py:351`). The refusal masks the term but prints the blob path verbatim; `--redact` does not cover the refusal renderer. Two named resolutions (renderer redaction, or doctrine hand-mask incl. path) — pick one at grill time. Interim rule per the reviewer: transcribed refusals are hand-masked including the path. **ADR #15: APPROVED at intake (report #1) — operator-delegated adjudication, 2026-08-15 (goal directive), verdicts per PM recommendation. Live pickable.** |
| 24 | `baseline-carve-out-review-cadence` | candidate | P3 | **New 2026-08-14** (v0.9.0 CLOSURE return). `privacy_baseline.json` went v1→v4 in one release, all three carve-outs reactive; no defined re-examination moment. Absorbs the round-2 INFO on the unbounded `internal-hostname` dotted-chain false-positive class (structural fix over a fourth literal) and the ship review's RFC-2606-breadth and fail-closed-deadline notes. Constraint inherited: baseline patterns stay single-line. **ADR #15 retroactive ruling: pre-approved intake (operator deferral).** |
| 25 | `push-ref-sha-validation-git-argv-hardening` | **DELIVERED — v0.11.0** | — (terminal) | **New 2026-08-14** — materializes the ship security review LOW (CWE-88/CWE-20): pre-push shas reach `git` argv unvalidated, no `--` separator; an option-shaped `local_sha` (`--glob=…`/`--branches=…`) yields a SUCCESSFUL EMPTY rev-list, silently no-opping the scan for that ref instead of failing closed. Fix: sha shape check as malformed-line refusal + `--` + prefix-check. Arm-B hardening lane with #9/#18/#26. **ADR #15: APPROVED at intake (report #1) — operator-delegated adjudication, 2026-08-15 (goal directive), verdicts per PM recommendation. Live pickable.** |
| 26 | `git-objects-batch-parse-typed-error-boundary` | **DELIVERED — v0.11.0** | — (terminal) | **New 2026-08-14** — merges the SAME defect from both ship reviewers (LOW in each: CWE-755): `out.index`/`int(size_str)` in `_read_blobs` raise raw ValueError past the `GitObjectReadError` contract (fail-closed but a traceback, not the FR6 refusal), and the desync branch continues into garbage instead of aborting typed. Plus the truncated-stream unit test both reviewers asked for. Rides with #25/#27. **ADR #15: APPROVED at intake (report #1) — operator-delegated adjudication, 2026-08-15 (goal directive), verdicts per PM recommendation. Live pickable.** |
| 27 | `git-objects-streamed-batch-reads` | **DELIVERED — v0.11.0** | — (terminal) | **New 2026-08-14** — materializes the ship security review LOW (CWE-400): `capture_output=True` materializes the whole `cat-file --batch` output in one buffer before the first object yields; measured fallback-shape bound in this repo **11,478 blobs / ~277 MB**. Fail-closed (MemoryError refuses); fix = Popen streaming or fixed-size sha chunks (smaller change, deterministic cap). **ADR #15: APPROVED at intake (report #1) — operator-delegated adjudication, 2026-08-15 (goal directive), verdicts per PM recommendation. Live pickable.** |
| 28 | `closure-v14-perf-figure-correction` | **DELIVERED — v0.11.0** | — (terminal, closure obligation) | **New 2026-08-14** — materializes the round-2 code-review MEDIUM (evidence fidelity) via the reviewer's own routing: CLOSURE.md is FROZEN, no third reopen — correct forward in memory. V14's 2.978 s "same benchmark" was synthetic (~2 MB vs 133 MB real); real fallback range ≈ **147 s** (read 4.29 s + match 142.9 s, ~1.3 s/MB regex throughput; the read-path ~3.7× win is real and reproduced). Record the real figure in the `sdd-gate-v3` atom; optional match-throughput decision. **ADR #15: APPROVED at intake (report #1) — operator-delegated adjudication, 2026-08-15 (goal directive), verdicts per PM recommendation. Live pickable.** |
| 29 | `self-scan-sentinel-integration-marker` | **DELIVERED — v0.11.0** | — (terminal) | **New 2026-08-14** — round-2 code-review LOW: `test_repo_self_scan.py:85` carries only `pytest.mark.slow`, not the `[integration, slow]` pair of its siblings; today's `-m "not quarantine"` selector runs it, but any future `-m integration` adoption silently drops the SENTINEL. One-line fix; rides the first window touching the surface. **ADR #15: APPROVED at intake (report #1) — operator-delegated adjudication, 2026-08-15 (goal directive), verdicts per PM recommendation. Live pickable.** |
| 30 | `backlog-tooling-reconciliation` | candidate | **P2** | **New 2026-08-15** — pre-approved intake P-1 (D-A ratification at v0.10.0 approval, SPEC §4.5/§4.10): reconcile the per-entry-file tooling (five `features/backlog/*` modules, `backlog new`/`backlog doctor`, SPEC-DOC-031, scaffold README, consumer recipe) with the single-source `BACKLOG.md` schema v0.10.0 shipped as doctrine. **Folds in intake report #2 item 2-2 (APPROVED AS MERGE)**: the `**Consumes:**` checklist item has no consumer — `removal_lifecycle.py`'s former caller was the deleted workflow engine. `software-engineer` surface, own release round. Trace: operator-delegated adjudication, 2026-08-15 (goal directive), verdicts per PM recommendation. |
| 31 | `backlog-md-physical-consolidation` | candidate | **P2** | **New 2026-08-15** — pre-approved intake P-2 (D-A ratification at v0.10.0 approval, SPEC §4.4/D5): fold the per-entry files + this candidates.md into single-source `BACKLOG.md` (ACTIVE + LEDGER), never-delete preserved end to end. PM curation surface; **sequences with/after #30** — consolidating before the tooling ships would break `backlog new`/`doctor`/SPEC-DOC-031 (SPEC R6). Trace: operator-delegated adjudication, 2026-08-15 (goal directive), verdicts per PM recommendation. |
| 32 | `dd-skills-applyto-glob-collisions` | candidate | P3 | **New 2026-08-15** — intake report #2 item 2-1 APPROVED (code-review pre-PR `2026-08-15T145731Z`, LOW, un-absorbed): the seven `dd-*` skills' `applyTo` globs collide pairwise (two skills claim `specs/backlog/**`) — the one-skill-per-stage boundary is absent from the activation surface; partition the globs + mechanical collision check. `ai-engineer` lane, rides the next AI-surface window with #33. Trace: operator-delegated adjudication, 2026-08-15 (goal directive), verdicts per PM recommendation. |
| 33 | `dd-release-definition-orchestration-pointer-loop` | candidate | P3 | **New 2026-08-15** — intake report #2 item 2-3 APPROVED (code-review pre-PR `2026-08-15T145731Z`, LOW; surfaced by PM verification — a review residual is never dropped silently): `dd-release-definition:103` and the `project-orchestration` release-definition playbook point at each other with no content at either end. One-line fix; rides with #32. Trace: operator-delegated adjudication, 2026-08-15 (goal directive), verdicts per PM recommendation. |
| 34 | `bug-event-redaction-always-on-reinforcement` | candidate | P3 | **New 2026-08-15** — intake report #2 item 2-4 APPROVED (security ship review `2026-08-15T151005Z`, LOW): the dehydration left the bug-event redaction rule on-demand only (`dd-bug-registration` §3); add ONE always-on reinforcement line in law §6. Distinct from #23 (refusal renderer path — different surface; dedupe record in the report). Trace: operator-delegated adjudication, 2026-08-15 (goal directive), verdicts per PM recommendation. |
| 35 | `dd-audit-project-pinned-tool-installs` | candidate | P3 | **New 2026-08-15** — intake report #2 item 2-5 APPROVED (security ship review `2026-08-15T151005Z`, INFO, pre-existing rename-carried): the audit skill instructs unpinned `pip install`/`npx` for third-party scanners; version-pin (or hash-pin) every invocation. `ai-engineer` lane, small hardening. Trace: operator-delegated adjudication, 2026-08-15 (goal directive), verdicts per PM recommendation. |
| 36 | `dadaia-cli-skill-agent-grant` | candidate | P3 | **New 2026-08-15** — pre-approved intake P-3 (v0.10.0 SPEC §4.7, finding F-1): `dadaia-cli`'s description claims "all agents may use it" while NO agent's frontmatter `skills:` list grants it — reachable only by the top-level session; make grant and description agree. `ai-engineer` surface. Trace: operator-delegated adjudication, 2026-08-15 (goal directive), verdicts per PM recommendation. |
| 37 | `codex-skill-ref-phantom-memory-ctx-prefix` | candidate | P3 | **New 2026-08-15** — pre-approved intake P-4 (v0.10.0 SPEC §4.8): `_CODEX_SKILL_REF_PREFIXES` names `memory-ctx`, which exists only under `public/runtime/codex/`, not `public/skills/` — a phantom prefix in the persona skill-ref filter; remove/re-point it + inventory-bound test. `software-engineer`, rides any `codex_assets.py` window. Trace: operator-delegated adjudication, 2026-08-15 (goal directive), verdicts per PM recommendation. |

Priority rationale: #1 and #17 delivered by v0.9.0; #3 picked as v0.10.0 (all three
terminal ledger rows). **#19 is P1 by the CLOSURE's own reading and the reviewers'
sizing** — 29 latent one-time push blockers, same failure mode as the round-1
CRITICAL, and the item both #22 and #24 sequence behind; #2 stays P1 for its own
release round (operator-excluded from the current one). #20 is the operator-visible
MEDIUM pair (both ship reviewers, hotfix-eligible) and pairs naturally with
#26/#25/#27 in the Arm-B chokepoints/git_objects hardening lane that #9/#18 already
form — a single hotfix/patch window could clear all five. #21 is P2 because after
v0.9.0 it is the ONLY unscanned channel on the push path and its evidence (59 KB
unscanned vs 0 B scanned) is the sharpest in the index; #22 is P2 as a real coverage
hole in the shipped privacy control, explicitly sequenced behind #19. #23/#24 are P3
privacy-control refinements with named resolutions; #25–#27 are P3 hardening of a
control whose failure modes are all fail-closed today; #28/#29 are P3
record-fidelity and marker hygiene. The 8 technical residuals among #19–#29 were
adjudicated **APPROVED** on 2026-08-15 (operator-delegated, report #1) and were
**picked into `v0.11.0` the same day, together with the pre-approved #19** — the whole
push-gate residual cluster clears in one release rather than trickling through five hotfix
windows, which is what the shared surface (`features/chokepoints/**`,
`infrastructure/git_objects.py`) makes cheapest. **#24 stays P3 and unpicked** and now owns
the `internal-hostname` structural-fix question alone (v0.11.0 SPEC §4.3 records the D6
evaluation and its negative outcome). **#21 stays P2** and is, after v0.11.0, still the only
unscanned channel on the push path. #30-#37 are the 2026-08-15 intake round: #30/#31 are the
P2 backlog tooling/consolidation pair (#31 sequenced after #30); #32-#37 are P3. The §5
precedence notice above (two open LOW bugs, Arm-B hotfix lane) outranks this whole table, and
final priority is the operator's at pick time.

## Ledger

One line per closed item, in the `dd-backlog-definition` §2 LEDGER form
`<slug> · <disposition> · <release-or-reason> · <date>`. Rows are never deleted and never
renumbered; the entry files stay in the tree carrying the same terminal token in their
frontmatter. This section is the forward-compatible shape of the single-source
`BACKLOG.md` LEDGER (#31), written here until that consolidation runs.

```
push-range-denylist-scan · DELIVERED · v0.9.0 · 2026-08-14
redact-foreign-context-names-at-qa-authoring · DELIVERED · v0.9.0 · 2026-08-14
tag-push-carve-out-reachability · DELIVERED · v0.9.0 · 2026-08-14
20260814-dd-lifecycle-skills-family · DELIVERED · v0.10.0 · 2026-08-15
prior-published-term-amnesty · DELIVERED · v0.11.0 · 2026-08-15
denylist-scan-skip-note-oversized-mislabel · DELIVERED · v0.11.0 · 2026-08-15
registry-derived-foreign-name-set · DELIVERED · v0.11.0 · 2026-08-15
refusal-path-redaction · DELIVERED · v0.11.0 · 2026-08-15
push-ref-sha-validation-git-argv-hardening · DELIVERED · v0.11.0 · 2026-08-15
git-objects-batch-parse-typed-error-boundary · DELIVERED · v0.11.0 · 2026-08-15
git-objects-streamed-batch-reads · DELIVERED · v0.11.0 · 2026-08-15
closure-v14-perf-figure-correction · DELIVERED · v0.11.0 · 2026-08-15
self-scan-sentinel-integration-marker · DELIVERED · v0.11.0 · 2026-08-15
loud-flake-stats-key-residual · DELIVERED · fixed before materialization · 2026-08-14
frozen-wall-clock-baselines-in-repo-text · DELIVERED · baselines embedded in memory · 2026-08-14
dispose-published-denylist-term · REJECTED · void by construction under the range-scoped scan · 2026-08-14
20260714-panel-games-pong-codex-v026 · REJECTED · surface removed in v0.3.0, nothing to validate · 2026-08-14
20260714-snake-wall-wrap-v025-pi-validation · REJECTED · same removal, nothing to validate · 2026-08-14
intake-2-6-consumer-validation-recipe-glob · REJECTED · operator discard at intake (delegated) · 2026-08-15
intake-2-8-spec-drafting-zero-hit-grep-lesson · REJECTED · operator discard at intake (delegated) · 2026-08-15
```

The nine `v0.11.0` rows above are the disposition sweep of that release's closure
(`specs/_archive/releases/v0.11.0/CLOSURE.md` §Dispositions). **No bug and no audit** was
picked into or superseded by v0.11.0, so the sweep has no bug row: the ledger carried zero
open bugs at pick time and both 2026-07 audits were already archived fully dispositioned by
v0.8.0.

## Ideas (5 live + 1 absorbed ledger row)

| Entry | Note |
|---|---|
| `flat-release-ship-task-evidence` | **New 2026-08-14** (v0.8.0 CLOSURE return). Closure freezes the directory before the ship marker can flip (T-080-07 archived `[ ]`); template needs ship evidence outside the archived dir. **v0.9.0 adds a second occurrence** (T-090-13 archives `[ ]` by design; CLOSURE §"Drifts › ship-task-archives-open" routes it here rather than opening a duplicate). |
| `tests-agents-md-placeholder-doctor-warning` | v0.7.0 CLOSURE return; check still missing at HEAD (only MEM-PLACEHOLDER-1 exists). |
| `stewardship-relocation-grep-homonym-note` | v0.7.0 CLOSURE return; note still absent from the stewardship skill. |
| `tag-push-carve-out-reachability` | **absorbed — v0.9.0 FR2** (grill ADR #4: tag pushes stay review-exempt but become scan-covered, closing the `service.py:344` bypass). Ledger row flipped 2026-08-14 at pick; **DELIVERED at closure** (CLOSURE Dispositions row 3; entry file flipped `status: delivered` and archived at `03ddd0b2`). |
| `repo-agents-md-symlink-hardening` | v0.7.0 CLOSURE return; `public_assets.py` still has no symlink refusal. |
| `bugs-jsonl-whole-blob-per-append` | **New 2026-08-14** (v0.9.0 CLOSURE return, ideas lane). Every `dadaia bugs append` republishes the whole ~900 KB `bugs.jsonl` as a new blob: dominated v0.9.0's real-range scan (the A7.3 2 s budget miss, V14) and is why long-published lines resurface as new range content (the #22 wider-set hits). Shape genuinely open (shard vs segments vs accept-with-amnesty) — grill before binding intents; `software-architect` input needed. **ADR #15 retroactive ruling: pre-approved intake (operator deferral).** |

## Terminal at materialization (never-delete law — recorded, not pickable)

All three archived to `_archive/` by `git mv` per SPEC-DOC-035.

| Entry | Status | Evidence |
|---|---|---|
| `loud-flake-stats-key-residual` | delivered | Fixed at HEAD before materialization: `ci.yml:361-374` hard-errors on missing/malformed `stats` (commit `15cb12c4`, T-070-09). |
| `frozen-wall-clock-baselines-in-repo-text` | delivered | Baselines embedded in `quality-assurance.md:147-151`; CI `timeout-minutes` set against them. |
| `dispose-published-denylist-term` | rejected | Void by construction under the range-scoped scan (grill ADR #3b: FROZEN `_archive/` + `git mv` ⇒ no new blob). v0.9.0 SPEC §7 records it untouched — FR4 documents why. |

## Terminal at intake adjudication — 2026-08-15 (ADR #15 report #2; never-delete law)

Discarded at the operator-gated intake before any entry file existed — the ledger row
below is the entire record (never-delete covers the record; there is no live file).
Trace: operator-delegated adjudication, 2026-08-15 (goal directive), verdicts per PM
recommendation.

| Item | Disposition | Reason |
|---|---|---|
| 2-6 `CONSUMER_VALIDATION_RECIPE.md` inside the ratified `public/data/*.md` glob | REJECTED — operator discard at intake (delegated) | Awareness served by intake report #2 itself; the D-C-ratified glob stands as ratified. |
| 2-8 SPEC-drafting zero-hit-grep scoping lesson | REJECTED — operator discard at intake (delegated) | Traceability lives in the archived v0.10.0 CLOSURE (Drifts section carries the corrected criteria form). |

## Rejected entries (retained per never-delete law)

Both archived 2026-08-14 by `git mv`, terminal `rejected_reason` in frontmatter:

| Entry | Reason | Location |
|---|---|---|
| `20260714-panel-games-pong-codex-v026` | Panel Games surface removed in v0.3.0; PI harness support removed — nothing left to validate | `_archive/` |
| `20260714-snake-wall-wrap-v025-pi-validation` | Same removal — nothing left to validate | `_archive/` |

## PM disposition decisions — 2026-08-14 (v0.9.0 returns + reviewer residuals, fourth pass)

Recorded here so the routing trail closes in writing:

1. **Dedupe: one entry per defect, all sources cited.** The oversized-skip mislabel
   (security MEDIUM CWE-778 + code-review MEDIUM) → #20 only; the batch-parse
   ValueError (security LOW CWE-755 + code-review LOW) → #26 only; the
   29-latent-blocker sizing (code-review LOW) → merged into #19, not a separate
   entry; QA-1 (CLOSURE return) → merged into #20 because the counter split
   rewrites the exact note QA-1 wants covered; the squash-message evidence
   (reconciliation INFOs) → merged into #21; the dotted-chain treadmill INFO →
   #24 (cadence half) with the structural-fix timing noted in #19.
2. **CLOSURE accepted-without-action list → NOT materialized, by design.** The
   seven items the v0.9.0 CLOSURE explicitly accepted (attribution debt, short-term
   masking, `json_value` keys, line-vs-whole-text traversal, ReDoS residual bounded
   by the cap, the wiring-spy naming sub-note) stay accepted; the two that were
   routed rather than accepted (#23, single-line-pattern constraint) live in #23
   and #24. Nothing from the REQUEST-CHANGES round is dropped silently.
3. **Git commit-identity de-personalisation → OPERATOR DECISION, not backlog
   work.** Both security handoffs raise it as INFO with an explicit
   "operator's call, no code change" (`git config user.email` →
   `users.noreply.github.com` form; no history rewrite). Carried as a standing
   notice here until ruled — same precedent as the panel-telemetry ruling (v0.8.0
   pass, decision 3). Not materializable by PM.
4. **`flat-release-ship-task-evidence` second occurrence → appended to the existing
   idea**, per the CLOSURE's own routing ("adds a second occurrence to it rather
   than a duplicate return"); no new entry.
5. **Anchor-uniqueness rebind.** `backlog doctor` (BL-CONFLICT) requires each
   canonical anchor to be bound by at most one live entry; the initial
   registration shared `sdd-gate-v3`/`push_gate_decision`/`_read_blobs`/
   `GitSubprocessObjectReader` across entries and was rebound to unique anchors in
   commit `3e45ccce` — memory-atom updates that lost their intent binding are
   recorded in each entry's body ("Memory note") instead.

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
