# AUDIT — 20260827-canon-v6-first-audit

**Auditor:** `project-auditor` · **Release:** 0.5.0, segment `S3` · **Task:** T-050-26 (FR16)
**Protocol:** `dd-audit-project` (T-050-24, `dab69d29`) — three pillars, run together (A14.1).
**Nature:** dry run. This audit **opens no remediation release** and creates **no backlog
entry**: every finding is compiled for the PM's operator-gated intake report (A16.5,
`DADAIA.md` §6).

---

## Scope — the window

`dd-diagnose`'s `LINEAGE.md` ("The window, stated once") is the computation, cited not
restated (A14.2). Applied here:

| Step | Result |
|---|---|
| Scan the live release's `RELEASE.jsonl` for an `audited` milestone | none — 6 records: `phase` ×3, `defined` ×1, `note` ×2 |
| Scan every archived release's fold (`specs/releases/_archive/releases_histo.jsonl`) | none — 167 records over 97 releases: `shipped` ×41, `defined` ×12, `note` ×114, **`audited` ×0** |
| `specs/releases/_ideas/**` | never scanned (D10/AS-7) — a Draft carries no `RELEASE.jsonl` |
| **Window** | **no `audited` milestone exists anywhere, so the window is the whole history** — `[e61e5fc7 (root, 2026-04-26), HEAD]` |

**This is the first audit this workspace has ever run.** Stating that explicitly is part of
the finding set: the audit lane has been nominally present and never executed, so every
number below is a first measurement, not a delta.

**Audited:** the whole `specs/bugs/BUGS.jsonl` ledger (**506 records** at read time; the 507th
is the record this audit itself registered), this release's **121 commits**
(`38916605~1..HEAD`), the full `dadaia specs doctor` surface, `releases_histo.jsonl`'s 97
releases, the 28 `specs/ADRs/` Confirmation lines, the memory trio's Part 1 and
`specs/constitution.md`.

**Excluded, by rule or by honesty:**

- `specs/releases/_ideas/**` — D10/AS-7.
- The heavier dead-code tools (`vulture`, `ts-prune`, `knip`, `depcheck`, `pydeps`) —
  each needs a pinned install this release's A14.5 zero-dependency posture forbids the
  audit to add. Recorded as **not-run**, never as clean (F033).
- Concurrent in-flight work by other sessions (`features/specs/doctor_*`, `container.py`,
  `cli/commands/specs.py`, `tests/**`, `specs/memory/**`). Where a measurement touches it,
  the reading is timestamped and flagged.

---

## V16 / V24 / V33 — the three validations this artifact carries

| Validation | Statement | Result |
|---|---|---|
| **V16** | The FR16 folder exists; pillar 1 names the four §1.1 chains with evidence; every finding `open` / `release: null` | **PASS** — all four chains named **by their pinned ids** (below); `FINDINGS.jsonl` = 33 records, every one `disposition: "open"`, `release: null`, `reason: null`, each validated line-by-line against `finding-record-v1.schema.json` (0 errors) |
| **V24** | The folder is redaction-clean under the push detector; every `evidence` value is the reproducible command **plus** a redacted one-line result, never a path alone | **PASS** — see *Redaction and the push-gate scan* below. No `.dadaia/tmp/**` path appears as a citation anywhere in `FINDINGS.jsonl`; that lane GCs at 3 days and a path-only citation decays into an unverifiable claim |
| **V33** | All **eight** forensic metrics present with `baseline → measured` | **PASS** — the eight-metric table below. Metric 7 was expected to worsen and is reported honestly; metric 8's measured 0 is reported as a **false zero**, not as target-met |

---

## Pillar 1 — bug history

### 1.1 The four pinned chains, named by the ids §1.1 pins (A16.2)

All four were rediscovered from `BUGS.jsonl` + `git show` alone, with no human pointing
at them. **Every pinned id was found in the ledger** — 15 of 15 lookups resolved.

#### Chain 1 — the gitignore class · **nine ids, all nine present** (≥ 3 required)

`backlog-candidates-md-tracked-violates-noncanonical-gitignore` ·
`grill-and-oq-decisions-records-gitignored-not-version-controlled` ·
`specs-bugs-jsonl-store-gitignored` · `backlog-gitignored-governance-vacuous` ·
`remote-bugs-gitignore-blocks-new-intake` · `gitignore-alpha-qa-review-untrackable` ·
`gitignore-code-review-artifact-untrackable` ·
`v0.4.4-reviews-dir-untrackable-gitignore-recurrence` ·
`gitignore-verdict-evidence-untrackable-fourth-recurrence`

Registered 2026-06-24 → 2026-08-24, **61 days, nine instances**. Seven of the nine
resolving commits touch `.gitignore` — the hand-kept allowlist metric 5 counts. Exactly
**one** carries `resolution_granularity: exact` (`232c1405`, 3 files); the other eight are
release squashes, so eight ninths of the class cannot be diffed as a fix. The class was
never named: no record carries a `caused_by` chain longer than one hop, and the last
instance names itself *fourth recurrence* in its own slug. → **F006**

#### Chain 2 — the certify probe · fix-induced, proven from the diff

`codex-live-probe-gate-checks-presence-not-usability` → `certify-skip-detail-leaks-full-codex-output`

`git show e74e9911 --numstat -- dadaia_workspace/features/certification/service.py` →
**55 insertions / 10 deletions**, adding `_codex_environment_unavailable_reason()`, which
returns the raw captured `codex exec` blob straight into the skip message. Bug B was
registered **37 minutes and 0 seconds after that fix commit** (`e74e9911` at 19:23:59Z → B's
`ts` 20:00:59Z) on the same `component: features/certification`. B's fix `7681d4f3`
(**+38 / −21**, same file) deletes that function and replaces it with `_codex_probe_outcome`,
capped at 200 chars and redacted. **B's record declares no lineage at all** —
`caused_by: null`, `lineage_source: null` — so the link that the diff makes obvious exists
today only as prose. → **F001**

The cheap sibling signature holds too: `certify-cannot-install-installed-provider`,
registered 18:41:56Z, whose resolving commit `2ffc7d57` is dated **18:43:17Z — 81 seconds
later** — and whose subject is `chore(bugs): reconcile the validator's ledger upstream`, a
bulk ledger flip that touches no code. Arithmetic, not judgement. → **F002**

#### Chain 3 — the frozen clock · the fix grew the feature, and the growth was the next bug

`no-ratchet-against-frozen-clock-tests-that-age-fixtures-by-the-real-clock` → `frozen-clock-ratchet-scans-tests-tmp-scratch-dir`

`git show a7e727aa --numstat` → **294 insertions / 0 deletions** creating
`tests/contract/test_frozen_clock_aging_ratchet.py` — the SPEC's "+294 LOC" confirmed to the
line. `git show 0d9d49bb --numstat` → **32 / 2** in that *same* file: the guard's own bug.
Two hops, both diffable.

**And the later record's declared lineage is contradicted by the diff.**
`frozen-clock-ratchet-scans-tests-tmp-scratch-dir` carries
`caused_by: "windows-xdist-workers-crash-on-unit-fast-tier"` with
`lineage_source: "text-reference"`. That named prior is **still `status: open` with
`resolved_commit: null`** — it has no fix diff at all, so it cannot have introduced the file
this bug repairs. `a7e727aa` did. This is exactly the shape `PILLAR-BUGS.md` calls a finding.
→ **F003**

#### Chain 4 — the bug-event ledger family · one seam, two symptoms, one fix

`bug-event-field-with-unicode-line-separator-silently-drops-the-event` (present, MEDIUM,
resolved at `2b9b30c1`, `resolution_granularity: exact`) **plus the ESC/CWE-117 escaping
finding, named by its review artifact** since it carries no bug id:

> **`specs/_archive/releases/v0.4.4/reviews/T-044-45-code-review.md:246` — finding `F-11`,
> axis *Security*, MEDIUM**, and carried forward verbatim in all five v0.4.4
> `security-reviewer` verdict handoffs under
> `specs/_archive/releases/v0.4.4/verdicts/` as *"F-11 stays registered (MEDIUM, open) as
> the only reachable ledger corruption, forgery structurally unreachable"*.

**A provenance correction the dry run is obliged to report.** SPEC §1.1 attributes the ESC
half to "a v0.4.4 security review". It is not there:
`grep -rn 'ESC|CWE-117' specs/_archive/releases/v0.4.4/` returns **zero hits**. The v0.4.4
artifact `F-11` covers the **U+2028 splitlines** symptom only; the **ESC/CWE-117 raw-render**
symptom first appears one release later, at `specs/releases/v0.4.5/SPEC.md:371` ("Separately,
ESC survives the round-trip and `bugs status` renders titles raw"), and is verified by the
v0.4.5 security verdicts. Both symptoms then close in one fix, `2b9b30c1` (T-045-20) — the
family claim stands; only its citation was wrong. → **F007**

### 1.2 The eight forensic metrics — `baseline → measured` (A14.7 / V33)

Reported on **two denominators**, because the baselines were measured over *the last 100
reported bugs* and the audit window is *the whole ledger*. The **last-100 column is the
like-for-like comparison**; the whole-ledger column is what the window actually contains.

| # | Metric | Baseline | **Measured — last 100 (like-for-like)** | Measured — whole ledger | Target |
|---|---|---|---|---|---|
| 1 | Per-bug diff attributability (`resolution_granularity == exact`) | 26/92 = **28 %** | **31/88 = 35 %** | 57/483 = 12 % | 100 % on post-0.5.0 resolutions — **actually 7/9 = 78 %** (F009) |
| 2 | FR23 triple coverage (`evidence_loop`+`evidence_seam`+`evidence_diff`) | 23/92 = **25 %** | **33/88 = 38 %** | 33/483 = 7 % | 100 % post-0.5.0 |
| 3 | Fix-shape ratio `net-negative / (net-neutral + net-positive)` | 21/31 = **0.68** | **8/19 = 0.42** | 8/19 = 0.42 (`diff_direction` present on only 27/506) | — |
| 4 | Same-surface re-bug rate at 3 d / 14 d | **55 % / 73 %** | **69 % / 86 %** (excluding the `unknown` sentinel: 53/83 = 64 % / 69/83 = 83 %) | 419/506 = 83 % / 470/506 = 93 % | — |
| 5 | Hand-kept-list touch count | 16/83 = **19 %** | **5/27 = 19 %** on diffable (`exact`) shas; 49/89 = 55 % counting coarse shas | 6/53 = 11 % on `exact` shas | — |
| 6 | Test-layer bug share (`surface == tests` or `component` under `tests/`) | **21/100** | **32/100** | 43/506 = 8 % | — |
| 7 | Scanner-vs-prose recurrence | **10/100**, target **0** | **0/100** under the literal definition — but see the honesty note | 0/506 literal; 10/506 symptom-matching | **0** |
| 8 | Sweep closures recorded as `resolved` | 9/92, target **0** | **0/88 — a false zero** | 0/483 — same false zero | **0** |

**Metric 4 is worse, and it is not a like-for-like worsening.** FR2 deliberately *closed*
the `surface` enum (86 distinct free-text strings → 30 values) and the migration mapped
**266 of 506** records to the `unknown` sentinel. Both changes coarsen the grouping upward,
which mechanically inflates any "same-surface predecessor" count. The comparable reading is
the excluding-`unknown` figure (64 % / 83 %). It is still above baseline; the release does
not claim to have shrunk this. → **F011**

**Metric 7 — the honest report the acceptance asks for.** Under the literal definition
(symptom matches `self-scan|denylist|privacy` **and** the fix touches only `specs/**/*.md`
or `tests/`) the measured value is **0/100**, which looks like the target met and is not.
The symptom-matching **population** is 7/100 (10/506 whole ledger), of which only **3** carry
a diffable `exact` sha; the other four are release squashes that touch hundreds of files, so
they fail the "touches only prose or tests" clause for a reason that has nothing to do with
the fix's real shape. Two of the three diffable ones
(`privacy-baseline-noreply-local-part-not-carved-out`,
`reconciliation-merge-body-scan-unamendable-main-squash`) fix
`infrastructure/data/privacy_baseline.json` — a hand-kept list — plus tests. **This release
grew the scanned prose corpus exactly as predicted** (four QA closes, three reviews, this
`specs/audits/**` folder, the FR3 migration report, five scoped `AGENTS.md`), and moved no
prose out of the scanned tree. The metric's *measurement* is currently blocked by coarse
shas rather than by the absence of the phenomenon. Saying so is the acceptance.

**Metric 8 is unmeasurable at HEAD, and that is a finding, not a pass.** The regex
`^Need met|re-affirmation` reads the v5 free-text `evidence` field. The v5→v6 migration
**did not carry that field forward**: scanning every field of every record for
`Need met|re-affirmation` returns **0 matches across 507 records**, and the field census
shows `cause` present on **10/507** and the FR23 triple on **33/507**. The release built the
instrument and deleted the thing it measures. → **F005**

### 1.3 The three cheap measures, and the per-record checks

| Check | Result |
|---|---|
| Registration→resolution interval | `certify-cannot-install-installed-provider`: **81 s**, closed by a ledger-only bulk reconciliation (F002) |
| **Core-field mutation** | **Clean.** Diffing every `BUGS.jsonl` blob against its predecessor across the 14 commits that touch the file: **0** immutable-core field changes on any existing `id` (F012 — a positive result, recorded because the rule is otherwise unenforced at write time) |
| **Cache disagreement (A8.2)** | **1 stored-vs-derived disagreement** across 506 records — *and the disagreement detector is itself compromised*: see below |
| Resolved with no `cause` | **473/483** resolved records carry `cause: null` |
| Resolved with no regression seam | **474/507** carry no `evidence_seam` |
| `net-positive` never routed to `software-architect` | **7 of 8** net-positive records carry a release-squash sha, so the routing evidence is structurally unverifiable (F008) |

**The finding underneath the finding (F004).** The FR3 resolver walks
`git log --all --no-merges --reverse --date-order -- specs/bugs/`
(`dadaia_workspace/infrastructure/git_subprocess.py:419`) with **no `--full-history`**. Under
a pathspec, git's default history simplification prunes commits it considers TREESAME
through a parent:

```
git log --all --no-merges --format=%H -- specs/bugs/ | wc -l                  -> 324
git log --all --full-history --no-merges --format=%H -- specs/bugs/ | wc -l   -> 362
```

**38 ledger-touching commits are invisible to the derivation**, and `a7e727aa` — the exact,
per-bug, +294-line fix for a chain §1.1 itself pins — is one of them. The resolver therefore
records `resolved_commit: 68658783` / `release-squash` (the 0.4.4 ship) for that bug when an
`exact` commit exists, is reachable from HEAD, and is seven hours older. This caps metric 1
at a ceiling that has nothing to do with commit discipline. → **F004**

### 1.4 The derived-cache write (A14.6)

Pillar 1 is the single writer. **507 records rewritten, one atomic rewrite per record**,
each through the FR2/AS-16 seam — `dadaia bugs update <id> --set audited=… [--set
registration_commit=… --set registration_granularity=… --set resolved_commit=… --set
resolution_granularity=…]`. No file-tool write touched `BUGS.jsonl`; no immutable-core field
was passed to the seam.

- `audited: "20260827-canon-v6-first-audit"` written on **507/507** records (previously
  `null` on all 507).
- **11 records** had a `null` provenance field the resolver can derive — every record
  registered after T-050-10's migration ran, plus this audit's own registration. Filled.
- **1 record** disagreed with the derivation (`test-git-history-reader-fixture-email-not-on-selfscan-baseline`:
  stored `resolution_granularity: exact`, derived `ledger-only`; the resolving commit
  `e5fa1fbf` stages only `BUGS.jsonl`, so `ledger-only` is correct). Corrected, and recorded.

**A seam discrepancy worth naming.** The task brief specified `--set audited=true`; the
schema defines `audited` as *"the audit window id that reviewed this resolution"*
(`type: ["string","null"]`) and `PILLAR-BUGS.md` specifies `--set audited=<audit-slug>`. The
skill and the schema agree, so the **audit slug** was written. The seam accepts either — it
validates structure, not semantics — so a `true` would have been silently accepted and would
have destroyed the field's only purpose, which is naming *which* window reviewed the record.
No bug was registered for this: the seam is behaving as specified (D15/AS-16).

---

## Pillar 2 — spec compliance

### 2.1 FR8 commit-shape conformance, **per shape** (A16.3), over this release's own 121 commits

Range `38916605~1..HEAD`. Shapes are `dd-gitflow-default` §3a's; this pillar reads that table.

| Shape | Population | Conformant | Verdict |
|---|---|---|---|
| **1 — bug registration** (`chore(bugs): report <id>`, `BUGS.jsonl` alone) | 8 | **5** | Three use non-canonical subjects (`register` / `close` / `fix(bugs): correct`) → **F014**, MEDIUM |
| **2 — backlog entry / ADR proposal** | 28 | **28** | **100 %.** Every `docs(adr): propose NNNN-<slug>` stages exactly one new ADR file. The one clean shape in the release |
| **3 — bug fix, one commit, no second** | 4 | **2** | `92868f1a` carries no `(resolves <id>)`; `cf51666c` stages code + the ledger line with **no regression test** → **F013**, HIGH — this is precisely the rule FR8 exists to prove |
| **5 — release definition** | 31 touch SPEC/PLAN/TASKS; **1** is the definition commit `38916605` | **1/1** | Purge-on-pick executed **in the same commit**: `-302` lines from `BACKLOG.md`, six entries moved to `CONSUMED · 0.5.0`, `SPEC.md:15` carries `**Consumes:**` → **F025**, conformant. The other 30 are task-marker flips, not definitions |
| **(isolation breach)** | 3 | — | `b8e65f42` (+26 paths), `588e4722` (+16), `3e7a92a4` (+3) stage `BUGS.jsonl` bundled → **F015** |
| **(unclassified)** | **47** | n/a | The ordinary task-implementation commit matches **no** shape → **F016** |

**The structural observation.** The five shapes classify 74 of 121 commits. The largest
single class in any release — the task commit — is outside the table, so "FR8 conformance"
can never speak about 39 % of what a release actually does. That is a canon gap, reported,
not fixed.

### 2.2 Canon-v6 pattern compliance — `dadaia specs doctor`

`dadaia specs doctor --json` → **exit 1, 2 errors, 492 warnings, 494 issues.** A15.3's
acceptance is **0 errors**. `--recipe` renders all 494 as ordered, copy-pasteable steps.
*(Note: this command raised `AttributeError: 'ClosureAuditValidator' object has no attribute
'check_archive_closures'` on the first attempt, during T-050-25A's in-flight refactor. Per
the concurrency protocol it was retried, not patched, and succeeded. Not registered as a bug
— it is another session's uncommitted intermediate state, not a shipped contract violation.)*

| Code | Sev | Count | Finding |
|---|---|---|---|
| `LINT-1` | **error** | 1 | `ARCHITECTURE.md` + `QUALITY.md` frontmatter → **F017** / **F031** |
| `SPEC-DOC-024` | **error** | 1 | phase `CLOSURE` with 21 unfinished markers → **F017** |
| `SPEC-DOC-033` | warn | **482** | resolved records missing `cause`/`caused_by`/`resolved_release`/`solution` → **F018** |
| `SPEC-DOC-004` | warn | 3 | SPEC/PLAN/TASKS `Em revisão` at phase `CLOSURE` |
| `SPEC-DOC-027` | warn | 2 | two legacy archive dir names |
| `SPEC-DOC-035` | warn | 1 | **false positive** on the scoped law file `specs/backlog/AGENTS.md` → **F022** |
| `SPEC-DOC-036` | warn | 1 | 21 archived audits predate the `FINDINGS.jsonl` canon → **F023** |
| `SPECS-VERSION` | warn | 1 | `specs_pattern_version` still **5** → **F021** |
| `TREE-5` | warn | 1 | `specs/AGENTS.md` superseded template → **F024** |
| `TREE-8` | warn | 1 | `specs/_archive` outside the canon root → **F020** |

**482 of 494 issues are one code.** `SPEC-DOC-033` is **97.7 %** of everything the doctor
says about this workspace, and it fires on records the historical ledger structurally cannot
complete. The governance surface the release built is, today, drowned in its own noise.
→ **F018**

### 2.3 `RELEASE.jsonl` milestone completeness

Folding `specs/releases/_archive/releases_histo.jsonl` — 167 records, 97 releases:

| Milestone | Present | With a `sha` |
|---|---|---|
| `defined` | **12 / 97** | 12 |
| `implemented` (final-rc QA close) | **0 / 97** | — |
| `shipped` | **41 / 97** | 41 |
| `audited` | **0 / 97** | — |

**36 releases carry `shipped` with no `defined`.** **56 carry no milestone at all.** No
release in the entire recorded history carries the middle milestone. Every `sha` that does
exist is populated — the shape is right where it is used; the chain simply has gaps almost
everywhere. → **F019**

The live release is mid-flight and consistent with its phase: `defined` at `38916605`,
phase `CLOSURE` (S4 memory window, AS-12). Not a finding.

---

## Pillar 3 — memory and constitution drift

### 3.1 Every Part-1 principle run through its own named check — **28 / 28 executed, 28 / 28 pass**

**Part 1 is authored** (T-050-28/29, concurrent) — 17 principles in `ARCHITECTURE.md`,
10 in `QUALITY.md`, 1 in `TECHSTACK.md` — **but it is uncommitted working-tree text.**
Per the task's instruction the 28 measures were executed as they stand, from the
`Measured by:` lines and the matching `specs/ADRs/00NN-*.md` `## Confirmation` lines.

| Principles | Measure | Result |
|---|---|---|
| P-01 … P-09 (ADR 0001–0009) | `lint-imports --config setup.cfg --no-cache` | **PASS** — `Contracts: 9 kept, 0 broken` |
| P-10 (0010), P-07's second half | `pytest tests/contract/test_import_linter_ignore_cap.py` | **PASS** — 2 passed |
| P-11 (0011) | `test_core_file_io_purity.py` | **PASS** — 1 passed |
| P-12 (0012) | `test_hook_import_surface.py` | **PASS** — 7 passed |
| P-13 (0013) | `test_architecture_diagrams_current.py` | **PASS** — 1 passed |
| P-14 (0014) | `test_release_events_read_only.py` | **PASS** — 1 passed |
| P-15 (0015) | `test_release_event_schema.py` | **PASS** — 1 passed |
| P-16 (0016) | `test_resolved_commit_stored_equals_derived.py` | **PASS — 21 passed, and the pass is tautological** (below) |
| P-17 (0017) | `test_behavior_map.py` | **PASS** — 30 passed |
| P-18 (0018) | `test_module_size_ceiling.py` | **PASS** — 2 passed |
| P-19 (0019) | `ruff check --no-cache dadaia_workspace/` | **PASS** — `All checks passed!` |
| P-20 (0020) | `test_specs_cli_complexity_ratchet.py` | **PASS** — 2 passed |
| P-21 (0021) | `test_stewardship_mechanics.py -k timeout` | **PASS** — 8 passed |
| P-22 (0022) | `… -k quarantine` | **PASS** — 4 passed |
| P-23…P-27 (0023–0027) | `test_test_suite_ratchets.py -k v26…v30` | **PASS** — 1 each; V30 printed `collected 2961: small 89.9% · medium 8.5% · large 1.6% — findings: none` |
| P-28 (0028) | `… -k marker_set` | **PASS** — 1 passed |

Every check **runs**. Not one is a "check does not run" row. → **F032**

### 3.2 The two gaps this makes visible

**Zero principles are ADR-accepted.** `grep -c 'Accepted by:'` across the memory trio → **0**
in all three files. `grep -h '^Status:' specs/ADRs/0*.md | sort | uniq -c` → **28
`Status: proposed`**. Under FR17/A18.4 and D12 (only the operator flips `proposed` →
`accepted`), **the entire Part-1 inventory is unratified**, which means the ADR gate the
principles are supposed to sit behind is not yet closed. → **F028**

**The ADR-pairing check has no input in this window.** `PILLAR-MEMORY` §2 matches every
committed Part-1 hunk to an `accepted` ADR in the same commit. `git status --short
specs/memory/` → ` M` on all three files; the window contains **no committed Part-1 hunk**.
Recorded, per A16.4 and the task's instruction, as **a gap to re-run at the final `rc`
(T-050-34) — never as a pass.** → **F029**

**ADR-0016's Confirmation is tautological.** `test_resolved_commit_stored_equals_derived.py`
clears `resolved_commit` and re-derives it through **the same `GitHistoryReader` walk** that
wrote the stored value. It proves the cache agrees with the resolver; it cannot notice that
the resolver disagrees with git (F004). A principle whose measure re-asks the question it is
supposed to check is measured, but not measured *against anything*. → **F030**

### 3.3 `constitution.md` violations — **2 CRITICAL**

`PILLAR-MEMORY` §5: a violated absolute law is CRITICAL by definition.

1. **§16 "Rules Map to Skills" mandates a file that does not exist.** It names
   `public/entities/rules-skills-map.json` (schema `rules-skills-map-v1`) as *"exactly one
   controlled source"* and declares *"a deterministic test … gates every deploy: no deploy
   without a valid map."* `find . -name rules-skills-map.json` → **nothing**;
   `ls dadaia_workspace/public/entities/` → `behavior-map.json`, `registry.json`. T-050-19
   retired the map; the constitution still gates every deploy on it. → **F026**, CRITICAL
2. **§13 "Memory Canon" enumerates three atoms by paths that no longer exist.** It names
   `specs/memory/architecture.md`, `tech-stack.md` and `quality-assurance.md`; all three
   `ls` as *No such file or directory* after FR1's rename to `ARCHITECTURE.md`,
   `TECHSTACK.md`, `QUALITY.md`. The one document nothing in this workspace may contradict
   is contradicted by the release that is renaming its own memory. → **F027**, CRITICAL

Both are consistent with `SPECS-VERSION` still reading **5** (F020): the constitution was
never migrated with the tree.

### 3.4 Product atoms, tech stack, and dead code

- **Memory frontmatter.** `ARCHITECTURE.md` and `QUALITY.md` fail `yaml.safe_load` at
  *line 5, column 22* — an unquoted `tldr` scalar containing `": "`. `TECHSTACK.md` parses
  clean (8 keys). The lint reports this as *"No valid YAML frontmatter found (expected `---`
  delimited block)"* although the block is present, swallowing the `yaml.YAMLError` that
  names the exact position — registered as its own record,
  `memory-lint-blames-missing-delimiter-for-a-yaml-parse-error` (LOW), in an isolated
  FR8 shape-1 commit. → **F031**
- **Product catalog.** `specs/memory/product/` carries `index.md`, `catalog.json` and eight
  area folders (`agents`, `distribution`, `harness`, `panel`, `philosophy`, `platform`,
  `sdd`, …) — the folder shape the canon requires. No atom-vs-code contradiction was found
  in the sampled walk.
- **Dead code — partial, and said so.** `ruff check --no-cache dadaia_workspace/ --select
  F401,F811,F841` → `All checks passed!`. `vulture` / `ts-prune` / `knip` / `depcheck` /
  `pydeps` were **not run**: each needs a pinned install, and A14.5 pins this FR at zero new
  dependencies. Recorded as **not-run**, never as clean. → **F033**

---

## Findings summary

**33 findings**, every one `disposition: "open"`, `release: null`, `reason: null`
(A16.5), each line validated against
`dadaia_workspace/public/schemas/audits/finding-record-v1.schema.json`.

| Severity | Count | Ids |
|---|---|---|
| **CRITICAL** | **2** | F026 (constitution §16 gates every deploy on a deleted file), F027 (constitution §13 names three non-existent memory atoms) |
| **HIGH** | **9** | F001, F003, F004, F005 · F013, F017, F019 · F028, F029 |
| **MEDIUM** | **16** | F002, F006, F007, F008, F009, F010, F011 · F014, F015, F016, F018, F020, F021, F022 · F030, F031 |
| **LOW** | **6** | F012 · F023, F024, F025 · F032, F033 |

By pillar: **bugs 12 · specs 13 · memory 8.**

**No backlog entry was created by this audit** (A16.5). The findings are compiled for
`project-manager`'s operator-gated intake report, which decides what enters `## ACTIVE`.

### The two CRITICAL findings, stated plainly for the operator

Per this persona's escalation rule, a CRITICAL finding needs acknowledgement before the
audit is treated as consumed. Both are the same shape: **`specs/constitution.md` was never
migrated alongside the canon-v6 rename it governs.** §16 gates every deploy on a JSON file
T-050-19 deleted, and §13 lists the memory trio under its pre-FR1 lowercase names. Neither
is a code defect; both are the document of last resort describing a workspace that no longer
exists. `product-engineer` owns the correction.

---

## Recommended actions — by severity, each naming its owner

The auditor recommends; it never dispatches. Remediation dispatch is `project-manager`'s.

| # | Action | Owner |
|---|---|---|
| 1 | Migrate `constitution.md` §13 and §16 to the v6 canon (uppercase memory atoms; `behavior-map.json` in place of the retired map) and bump `specs_pattern_version` to 6 — F026, F027, F021 | `product-engineer` |
| 2 | Add `--full-history` to the FR3 history walk at `git_subprocess.py:419` and re-derive the whole ledger; 38 commits and at least one pinned chain's exact fix are currently invisible — F004 | `software-engineer` |
| 3 | Restore an input for metric 8, or retire the metric and say so — the field its regex reads no longer exists on any record — F005 | `product-engineer` (SPEC) + `software-engineer` (record model) |
| 4 | Re-key ADR-0016's Confirmation onto an independent oracle (raw `git log --full-history`), so the check can fail — F030 | `software-architect` |
| 5 | Fix the two invalid memory frontmatter blocks and the lint diagnostic that misnames the cause — F031 and the registered record | `product-engineer` (frontmatter) + `software-engineer` (diagnostic) |
| 6 | Close the two doctor errors before `S3` closes: A15.3 demands 0 — F017 | `software-engineer` + `product-engineer` |
| 7 | Declare `caused_by` on the certify and frozen-clock records, and correct the one contradicted by its diff — F001, F003 | `software-engineer` (via `dadaia bugs update`) |
| 8 | Triage `SPEC-DOC-033`'s 482 warnings: scope the check to post-0.5.0 records, or accept the historical residue explicitly — F018 | `product-engineer` |
| 9 | Decide whether FR8 gains a sixth shape for the task commit, or states that it deliberately does not cover it — F016 | `software-architect` |
| 10 | Exempt `AGENTS.md` from `SPEC-DOC-035` — F022 | `software-engineer` |
| 11 | Backfill or explicitly waive the `implemented` milestone for the archived corpus (0/97 today) — F019 | `product-engineer` |
| 12 | Re-run **pillar 3** at the final `rc` against the committed, ADR-accepted Part 1, appending new findings with new ids — A16.4, T-050-34 | `project-auditor`, dispatched by `project-manager` |

**Score floor.** Not applicable: FR14's canon retired the six-dimension 1–10 scorecard and
absorbed it into pillar 3 (`dd-audit-project`, FR14 bug-surface note). This audit reports
findings and dispositions, not dimension scores.

---

## Redaction and the push-gate scan (V24 / A13.5)

Every `evidence` value in `FINDINGS.jsonl` is **the reproducible command plus a redacted
one-line result**. No home-absolute path, e-mail, IP, hostname or consumer-repo slug appears
anywhere in this folder; tool output that carries runner-absolute paths (`lint-imports`,
`pytest`, the ratchets, `specs doctor`) was reduced **by hand** to its one-line conclusion,
never pasted. No `.dadaia/tmp/**` path is cited as evidence anywhere — that lane GCs at three
days, and a path-only citation decays into exactly the unverifiable claim this release exists
to end.

The folder was then scanned with the same detector a push uses. The result is recorded in
*Scan result* below.

---

## Evidence sources

Read directly by this session; no sub-agent was dispatched (the three pillars are this
persona's own protocol, and a leaf dispatch would have added a hop without adding evidence):

- `specs/bugs/BUGS.jsonl` — 506 records at read time; `dadaia bugs update` for the writes
- `specs/releases/0.5.0/{SPEC,TASKS}.md`, `RELEASE.jsonl`, `reviews/S4-principle-inventory.md`,
  `reviews/bug-history-forensic-100.md`
- `specs/releases/_archive/releases_histo.jsonl` — 167 records / 97 releases
- `specs/_archive/releases/v0.4.4/reviews/T-044-45-code-review.md` and the five
  `verdicts/*.handoff.json` — the chain-4 provenance
- `specs/releases/v0.4.5/{SPEC,TASKS}.md`, `reviews/`, `verdicts/`
- `specs/ADRs/0001…0028` — the 28 `## Confirmation` lines
- `specs/memory/{ARCHITECTURE,QUALITY,TECHSTACK}.md`, `specs/memory/product/`, `specs/constitution.md`
- `setup.cfg`, `dadaia_workspace/infrastructure/git_subprocess.py`,
  `dadaia_workspace/core/bug_provenance.py`, `dadaia_workspace/features/specs/memory_lint.py`,
  `tests/contract/**`
- `git log` / `git show` over `[e61e5fc7, HEAD]`; `dadaia specs doctor --json` / `--recipe`;
  `lint-imports`; `ruff`; the 18 named `pytest` node sets; `dadaia ci push-gate-check`
