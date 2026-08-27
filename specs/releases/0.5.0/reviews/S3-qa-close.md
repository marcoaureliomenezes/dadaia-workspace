# S3 QA Close — release 0.5.0

**Task:** T-050-27 · **Reviewer:** qa-engineer · **Branch:** `feature/0.5.0` ·
**HEAD reviewed:** `29f506bc` (T-050-26, "first audit under canon v6 (dry run)"), with
`5259f5d8` (specs/AGENTS.md reconciliation) and the S4 close commits (`f4483c6c` et al.)
landing concurrently and out of this task's scope — reviewed here only where they touch
S3's own preconditions.
**Scope:** T-050-23…T-050-26 (incl. 25A), all `[x]` — SPEC A13–A16, A14.7, A13.5/V24,
V16, V33.
**Note on concurrency:** at review time `RELEASE.jsonl` was mid-append by another session
(S4 close, T-050-33). It was read, never written, per this task's instruction.

## Verdict: **APPROVE**

The deciding question — *did the dry run rediscover the loop?* — is answered yes, with
every chain pinned to explicit bug ids exactly as A16.2 requires. The quantitative half
(A14.7/V33) is complete: all eight metrics carry `baseline → measured`, metric 7 is
honestly reported worse, and metric 8's `0` is disclosed as unmeasurable rather than
passed off as a target met. V24's redaction claim was independently re-run and matches
the artifact's own report. `FINDINGS.jsonl` validates 37/37 against the schema. Zero new
`tests/e2e/**` files exist since S2 close.

---

## 1. The deciding question (A16.2/V16) — did the dry run rediscover the loop?

All four chains of SPEC §1.1 are named in `AUDIT.md` §"Pillar 1 → 1.1", each by its
pinned `bugs.jsonl` ids, independently cross-checked here against `specs/bugs/BUGS.jsonl`
and `git show`:

**Chain 1 — gitignore class.** All **nine** pinned ids present (≥ 3 required by the
task): `backlog-candidates-md-tracked-violates-noncanonical-gitignore`,
`grill-and-oq-decisions-records-gitignored-not-version-controlled`,
`specs-bugs-jsonl-store-gitignored`, `backlog-gitignored-governance-vacuous`,
`remote-bugs-gitignore-blocks-new-intake`, `gitignore-alpha-qa-review-untrackable`,
`gitignore-code-review-artifact-untrackable`,
`v0.4.4-reviews-dir-untrackable-gitignore-recurrence`,
`gitignore-verdict-evidence-untrackable-fourth-recurrence` → finding
`20260827-canon-v6-first-audit-F006`.

**Chain 2 — certify probe (fix-induced).**
`codex-live-probe-gate-checks-presence-not-usability` →
`certify-skip-detail-leaks-full-codex-output`, plus the cheap sibling
`certify-cannot-install-installed-provider` (81 s registration→resolution interval,
ledger-only bulk flip) → findings `…-F001` and `…-F002`.

**Chain 3 — frozen clock.**
`no-ratchet-against-frozen-clock-tests-that-age-fixtures-by-the-real-clock` →
`frozen-clock-ratchet-scans-tests-tmp-scratch-dir`, with the later record's declared
`caused_by` shown contradicted by the diff (the named prior is still `open`/unresolved
and cannot have produced the file the diff shows a different commit created) →
finding `…-F003`.

**Chain 4 — bug-event ledger family.**
`bug-event-field-with-unicode-line-separator-silently-drops-the-event` (present,
`resolved`) plus the ESC/CWE-117 escaping symptom, cited by its review artifact since it
carries no bug id → finding `…-F007`. **Provenance correction, verified:** SPEC §1.1
attributes the ESC half to "a v0.4.4 security review." `grep -rn 'ESC|CWE-117'
specs/_archive/releases/v0.4.4/` returns zero hits (re-run here, same result). The
ESC/raw-render symptom first appears at `specs/releases/v0.4.5/SPEC.md:371`, one release
later than SPEC §1.1 states. The audit's correction is accurate and is carried into this
review rather than repeating the SPEC's original (wrong) attribution.

**Verdict on this section:** A16.2 is met. A chain named without its pinned ids would not
count under this task's own instruction — every one of the four chains here is named with
ids, not prose.

---

## 2. The quantitative half — eight forensic metrics (A14.7/V33)

Reproduced from `AUDIT.md` §1.2 (last-100, like-for-like column — the baseline's own
denominator):

| # | Metric | Baseline | Measured (last-100) | Target |
|---|---|---|---|---|
| 1 | Per-bug diff attributability | 28 % | 35 % | 100 % post-0.5.0 |
| 2 | FR23 triple coverage | 25 % | 38 % | 100 % post-0.5.0 |
| 3 | Fix-shape ratio | 0.68 | 0.42 | — |
| 4 | Same-surface re-bug rate (3 d / 14 d) | 55 % / 73 % | 69 % / 86 % (64 %/83 % excl. `unknown`) | — |
| 5 | Hand-kept-list touch count | 19 % | 19 % (diffable) / 55 % (all coarse) | — |
| 6 | Test-layer bug share | 21/100 | 32/100 | — |
| 7 | Scanner-vs-prose recurrence | 10/100 | **0/100 under the literal definition, disclosed as inflated by coarse shas rather than by absence of the phenomenon** | 0 |
| 8 | Sweep closures as `resolved` | 9/92 | **0/88 — disclosed as a false zero** | 0 |

All eight rows present, each with `baseline → measured`, satisfying A14.7's structural
requirement ("every one of the eight ... is computed ... and each appears in `AUDIT.md`").

**Metric 7 — worse in substance, exactly as the SPEC anticipated.** A14.7 states this
metric is *expected* to be worse and that saying so, honestly, is itself the acceptance.
The literal `0/100` reads as target-met; the audit discloses that the population able to
be measured this way (records with a diffable `exact` sha) is only 3 of 7 symptom-matching
records, and that this release *grows* the scanned-prose corpus it is supposed to shrink
(four QA closes, three reviews, this `specs/audits/**` folder, the FR3 migration report,
five scoped `AGENTS.md`) while moving no prose out of the scanned tree. This is a real
worsening reported honestly, not a favorable number reported blind. Independently
re-checked: no counter-evidence found that contradicts the audit's own accounting.

**Metric 8 — a false zero, and the question this task poses directly: is A14.7 met when a
metric is honestly reported as unmeasurable?** Independently reproduced:
`grep -c '"evidence"' specs/bugs/BUGS.jsonl` → **0** matches — the v5 free-text `evidence`
field the metric's regex reads (`^Need met|re-affirmation`) does not exist anywhere in the
v6-migrated ledger. `grep -ci 'Need met|re-affirmation' specs/bugs/BUGS.jsonl` → **0** as
well, confirming there is nothing left to match, not that the phenomenon stopped
occurring. **Yes, A14.7 is met.** The acceptance's own text names the failure mode it
exists to prevent — "a metric named in §1 but absent from the artifact is the
fabricated-evidence shape one level up" — and the alternative to fabrication is exactly
what happened here: the metric is computed, appears in `AUDIT.md`, and its `0` is labeled
untrustworthy with the mechanism named (the field the migration deleted), rather than
silently reported as target-met. Silently accepting `0/88, target met` would have been the
fabricated-evidence shape; disclosing the false zero is the honest report A14.7 demands.

**Routed to intake, not blocking S3.** The underlying defect — metric 8 has no valid
input after the v5→v6 migration — is `AUDIT.md` finding `20260827-canon-v6-first-audit-F005`
and is already on the audit's own "Recommended actions" table (#3: restore an input for
metric 8, or retire it and say so; owners `product-engineer` (SPEC) + `software-engineer`
(record model)). This is `PILLAR-BUGS.md`'s metric-8 *definition* that needs fixing, not
this dry run's execution of it — S3's job was to run the protocol honestly, which it did.
This observation is recorded here for `project-manager`'s operator-gated intake report
(`DADAIA.md` §6); this review does not itself create a backlog entry.

---

## 3. V24 — redaction-clean and self-cited evidence

Independently re-run, not merely trusted from `AUDIT.md`:

```
cd repos/dadaia-workspace
HEAD_SHA=$(git rev-parse HEAD)   # 2e7e0bfa (post S3/S4 concurrent commits)
printf 'refs/heads/feature/0.5.0 %s refs/heads/feature/0.5.0 0000...0000\n' "$HEAD_SHA" \
  | dadaia ci push-gate-check
```

Result: **exit 1, 8 objects carrying a denylisted term, 0 of them under
`specs/audits/`** (`grep -c 'specs/audits/'` over the tool's own output → 0). This
matches `AUDIT.md`'s V24 claim exactly — same count (8), same zero-inside-the-folder
result, same finding id (`…-F037`) recording the 8 as pre-existing and out of S3's scope
(`specs/backlog/_archive/backlog_histo.jsonl`, two `BUGS.jsonl` lines, two test fixtures,
two commit messages — all `email-address` baseline / operator-denylist hits that predate
this segment).

**`evidence` field shape.** Sampled all 37 `FINDINGS.jsonl` records programmatically: no
`evidence` value contains a home-absolute path (`/home/`, `/the-operator`); every value contains
a command-shaped token (`git `, `grep`, `pytest`, `ruff`, `->`/`→`, or a `file:line`
anchor) followed by a result, matching A13.5's "reproducible command plus a redacted
one-line result." No `.dadaia/tmp/**` path is cited as the sole evidence in any record.

---

## 4. `FINDINGS.jsonl` schema validation

All 37 lines validated against
`dadaia_workspace/public/schemas/audits/finding-record-v1.schema.json` with
`jsonschema.validate` — **0 errors**. Every record: `disposition: "open"`,
`release: null`, `reason: null` (A16.5) — confirmed programmatically across all 37, not
sampled. `A16.6` (the `audited` milestone appended to `RELEASE.jsonl`) confirmed: exactly
one `audited` record, `sha: 5c0448dcc1feeec204e24b4b4583618017f6c52b`,
`audit: 20260827-canon-v6-first-audit`.

---

## 5. Zero new `tests/e2e/**` files since S2 close

```
git diff --name-status 72d7c882 HEAD -- 'tests/e2e/**'
```

Zero output, zero matches for `e2e` in the full `git diff --name-status` between S2's
close commit and this review's HEAD. **No exceptions to name.**

---

## 6. The two HIGH bugs the audit surfaced — audit outcomes, not S3 defects

Both are classified here as findings the dry run correctly surfaced about the tooling it
ran on, not defects introduced by this segment's own work:

- **`bugs-record-store-append-clobbers-concurrent-update-batch`** (HIGH, `open` in
  `specs/bugs/BUGS.jsonl`) — the FR2/AS-16 record-store seam lost a 507-record governance
  write batch to a concurrent `bugs append`, silently on both sides. Registered in an
  isolated shape-1 commit (`7e5b1725`); mirrored as finding `…-F034`.
- **The `--full-history` walk gap**, finding `20260827-canon-v6-first-audit-F004`
  (HIGH, `open`, no separate bug id registered as of this review — the finding names the
  defect directly by `file:line`: `dadaia_workspace/infrastructure/git_subprocess.py:419`
  lacks `--full-history`, pruning 38 ledger-touching commits from the FR3 derivation,
  including the exact per-bug fix for the pinned frozen-clock chain).

Per this task's instruction, both are recorded here as audit outcomes surfaced by a
correctly-functioning dry run (exactly what FR16 exists for — "the canon fails *here*
rather than at a consumer"), being fixed concurrently by `software-engineer`, and are not
treated as S3 acceptance blockers.

---

## 7. Security / privacy leakage note (FR24)

- No home-absolute paths, hostnames, IPs, secrets, or tokens found in `AUDIT.md`,
  `FINDINGS.jsonl`, or this review — spot-checked and programmatically scanned.
- The push-gate scan (§3) independently confirms the audit folder itself carries zero
  denylisted hits; the 8 hits found elsewhere on the branch are pre-existing
  (`…-F037`), already recorded, and not introduced by S3's own commits.
- No new dependency, no auth/access-control surface, and no generated file is touched by
  this segment — it is a data-producing dry run (0 production LOC per FR16's own
  bug-surface note), consistent with what was independently observed.
- **Bug-surface axis (FR24):** this segment adds no production code and no AI-surface
  beyond the audit artifact itself; it does not increase the bug surface of any shipped
  feature. It *does* surface two real, pre-existing HIGH bugs in tooling this workspace
  already ships (the record-store lost-update seam and the history-walk pruning) —
  exactly the intended effect of running the canon for the first time, per FR16's
  bug-history evidence ("a green internal gate that diverges from real consumer behavior
  is itself a bug").

---

## Evidence paths

- `specs/audits/20260827-canon-v6-first-audit/AUDIT.md`
- `specs/audits/20260827-canon-v6-first-audit/FINDINGS.jsonl`
- `specs/bugs/BUGS.jsonl`
- `specs/releases/0.5.0/RELEASE.jsonl`
- `specs/releases/0.5.0/TASKS.md` (T-050-23…T-050-26 markers)
- `dadaia_workspace/public/schemas/audits/finding-record-v1.schema.json`
