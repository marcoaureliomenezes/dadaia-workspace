# T-044-46 — Release Verdict (QA)

**Verdict: APPROVED — "closed by QA".**

The whole v0.4.4 scope — five segments (S1–S5), 57 declared tasks, the six-axis code
review, three security-review rounds, five QA segment closes, two architect rulings and
one six-firing FR23 ledger — is accepted as a candidate for `rc-1`. This verdict alone
does not close the task: `T-044-46`'s done criterion is the APPROVED security handoff
**plus** this recorded release verdict, both present (evidence table below). Flipping
`T-044-46` to `[x]` unblocks `T-044-52` (the `rc-1` PR), not any later closure step.

Re-run at `HEAD = c7cc8d04ff04360a3142099d063c75067e27977a`, working tree clean,
`feature/0.4.4`.

---

## 1. Evidence-chain table

| Artifact | Verdict | Commit / sha |
|---|---|---|
| `reviews/S1-qa-close.md` | APPROVE | segment close on `feature/0.4.4` |
| `reviews/S1-AR2-ruling.md` | dual-path rulings: none found; enforcement 6→6 gross (relocated, not multiplied) | architect ruling, S1 close |
| `reviews/S2-qa-close.md` | APPROVE | segment close on `feature/0.4.4` |
| `reviews/S3-qa-close.md` | APPROVE (A30.2 disclosed FAIL, out-of-scope; A30.3 PASS) | segment close on `feature/0.4.4` |
| `reviews/S3-AR1-ruling.md` | two test-architecture intake items named (INTAKE-AR1-1/2) | architect ruling, S3 close |
| `reviews/S4-qa-close.md` | APPROVE (S4 reduces bug surface net of its own sanctioned additive scope) | segment close on `feature/0.4.4` |
| `reviews/S5-qa-close.md` | APPROVE | segment close on `feature/0.4.4` |
| `reviews/S5-FR23-first-firing-ruling.md` | 6/6 firings SOUND (1–5) / CONFIRMED (6) | architect ruling, S5 close |
| T-044-44 scope-complete gate capture | A21.4/A21.8 PASS, A21.9 disclosed miss, suite 0 failed | `7a8a0175` |
| `reviews/T-044-45-code-review.md` | REQUEST_CHANGES → REQUEST_CHANGES → **APPROVED** (3 passes) | final pass reviewed `3bf5824c` (cited in-doc as `ed5d64cd`, its pre-rewrite hash — see §3 note) |
| `specs/releases/v0.4.4/verdicts/f83cfb724d1c8534605138c6c1d8f45d23b21e70.handoff.json` | **APPROVED**, 3 rounds, 0 CRITICAL/HIGH, 2 MEDIUM (record-only) | commit `1bc9a5ea`, reviewed sha `25632ef5` |
| `.dadaia/handoff/dadaia-workspace/2026-08-24T172302Z-project-manager-v044-intake-report.handoff.json` | 15 intake candidates compiled, nothing materialized to `BACKLOG.md` | PM intake handoff, present |
| This verdict, re-run gates | **APPROVE** | `c7cc8d04` (this session) |

Every listed artifact was read and verified present with the stated verdict string
inside it — this table is not transcribed from the dispatch brief, it is re-derived from
the files on disk.

---

## 2. Top-line release numbers (re-measured this session)

| Metric | Value | Source |
|---|---|---|
| Segments | 5 (S1–S5) | `specs/releases/v0.4.4/reviews/S{1..5}-qa-close.md` |
| Task markers in `TASKS.md` | 57 total — 49 `[x]`, 8 `[-]` | `grep -c` re-run this session |
| Remaining `[-]` tasks | `T-044-46/47/48/49/50/51/52/53` — the closure/ship chain this verdict unblocks | `TASKS.md` |
| Bugs resolved since release start (2026-08-23) | 23 `resolved` events + 1 pick-time `superseded`/`archived` (`context-list-current-branch-stale-for-alive-repo`) | `specs/bugs/bugs.jsonl`, filtered `ts >= 2026-08-23` |
| Bugs open at this verdict | **7**, severities LOW/MEDIUM only — **0 HIGH/CRITICAL** | `dadaia bugs status --all`, re-run this session |
| Concurrent fix landed during this verdict | `gitignore-verdict-evidence-untrackable-fourth-recurrence` (MEDIUM) resolved by `software-engineer` at `c7cc8d04`, disjoint from this task's write set | `git log`, `dadaia bugs status` |
| Production LOC net (`dadaia_workspace/**`) | **−130** (+4528/−4658); −813 excluding S4's sanctioned addition | T-044-44 gate capture (A21.4) |
| AI-surface LOC net (`public/{agents,skills,data,entities}/**`) | **−943** (+3021/−3964); skills 25 → 21 | T-044-44 (A21.8) + code review final tally |
| Full suite (re-run this session, `HEAD=c7cc8d04`) | **2822 passed, 4 skipped, 0 failed**, 94.29s | `pytest -p no:cacheprovider -q`, this session |
| `dadaia ci preflight` (re-run this session) | **PASS** — ruff format/check, mypy --strict, lint-imports, pytest all green | this session |
| `dadaia ci push-gate-check` (re-run this session, real refspec, no pipe) | **exit 0**, denylist scan clean | this session, `refs/heads/feature/0.4.4` new-branch refspec |
| Security review rounds | 3 rounds, final APPROVED, 0 CRITICAL/HIGH | `verdicts/f83cfb72*.handoff.json` |
| Code review passes | 3 passes, final APPROVED, 0 CRITICAL/HIGH open (F-7/8/9/10 LOW, F-11 registered as a bug) | `T-044-45-code-review.md` |
| FR23 net-positive-diff firings | 6, all SOUND (1–5) / CONFIRMED (6) | `S5-FR23-first-firing-ruling.md` |

The dispatch brief's approximate "13 bugs closed / 7 open" figure undercounts closures:
the actual count re-derived from `bugs.jsonl` this session is **23 resolved + 1
superseded/archived**, with the open count of **7** matching exactly (after the
concurrent gitignore fix landed mid-verdict).

---

## 3. Disclosed non-conformances riding to intake (none blocking)

| Item | Disposition |
|---|---|
| **A21.9** — always-on prefix token/negation budget (≤3.5k tokens, ≤60 negations) NOT MET; measured 8.2k–11.8k tokens, 123–162 negations | Honestly disclosed in T-044-44's gate capture. Not a regression — every measured component moved net-negative from baseline; the residual gap is the already-disclosed S3 finding (A30.2/A29.1: `ctx_inject`'s catalog-digest prefix size + 4/9 personas still >220 lines). Carried to PM intake theme C (AI-surface token economy, 6 candidates). |
| **A30.3-adjacent catalog trimming/paging** | S3 close names this as carried, unexecuted; PM intake theme C. |
| **S-3 — branch-protection configuration** | The relocated CI verdict gate is a required check on **neither** `develop` nor `main` PR edge. Sanctioned for `rc-1` only by SPEC A4.4 (a job added on a branch does not run on its own PR); both the code review and the security handoff (round 2/3) re-confirm it stands, and PM intake theme B (item B1, HIGH, time-boxed) names it an **operator-only** action item due before the `rc-2` PR edge — not backlog material. |
| **Root-whitelist / doctor debris** (`.dadaia/references/` at the workspace root) — the doctor check family flagging any unlisted root-level directory (`ROOT-4` in `specs/memory/architecture.md`'s runtime-state table) | T-044-44's gate capture discloses `dadaia doctor` alone fails on this pre-existing, unrelated operator research clone outside `repos/dadaia-workspace`, untouched by any v0.4.4 commit. `ci preflight`, `specs doctor` (0 errors), `backlog doctor` and `public doctor` are all green independently. Record-only — not this release's defect, not blocking. |
| **INTAKE-AR1-1/2** (S3-AR1 ruling) — split the test-inventory assertion out of two byte-golden tests into a derived roster oracle; one shared oracle for three coupled-inventory tests | Named, unexecuted, carried through S5 close; PM intake theme A (structural consolidation). |
| **F-7/F-8/F-9/F-10** (code review, LOW) | Cosmetic naming/wording residuals and CLI-startup-noise measurement, non-blocking, open. |
| **F-11** (code review, MEDIUM) | Registered as a bug (`bug-event-field-with-unicode-line-separator-silently-drops-the-event`) — pre-existing defect surfaced by this review's 10-payload probe, not a defect of this diff. Currently open (MEDIUM, not HIGH/CRITICAL). |
| **Atomic-writer consolidation** (8 near-identical primitives → 1) | PM intake theme A, item A1 (HIGH) — structurally subsumes open bug `two-atomic-writers-leak-temp-file-on-injected-os-replace-failure` (LOW). |
| **B2 — doctor-lane slug-ownership uniqueness** (S5-FR23 Firing 5) | The two write-seam enforcement (F-1 + its Firing-6 mirror fix) never heals a pre-existing corrupt registry imported verbatim by the v2→v3 migration. PM intake theme B, item B2 (MEDIUM) — explicit follow-up decision, not this release's scope. |

Full text of all 15 intake candidates: the PM intake handoff (§1 table, row 3).

---

## 4. Bug-surface statement for the whole release

**The release reduces the bug surface.** Evidence, not "tests green":

- **Ledger arithmetic.** 23 bugs `resolved` + 1 `superseded`/`archived` since release
  start, against **7** open at this verdict, all LOW/MEDIUM, **zero HIGH/CRITICAL**. The
  release found and closed defects faster than it accumulated open ones, and the residual
  open set carries no severity above MEDIUM.
- **Per-feature tally (T-044-45 final code review, 11 touched features).** **REDUCED on
  10**, **sanctioned-INCREASED on 1** (`S4`, the additive scope R-2 explicitly sanctions
  in SPEC, tracked and bounded, not an unaccounted growth). No feature moved from
  REDUCED to INCREASED across the three review passes without a named, ratified reason.
- **FR23 firing discipline.** All 6 net-positive-diff firings this release triggered were
  ruled SOUND or CONFIRMED by `software-architect` — every place the diff grew, the
  growth was traced to a missing enforcement at the seam that owns it (Firings 1, 4, 5),
  a governed test-coverage addition with a defect deleted at its root (Firing 2), an
  earned third exception category on four named conditions (Firing 3), or an exact,
  drift-free repeat of a prior firing's prescription (Firing 6) — never a bolt-on branch,
  flag or second code path. This is the standing order's own test, applied six times,
  passing six times.
- **The F-1 → F-12/Firing-5/Firing-6 arc, specifically.** The `add_repo` fix (`7a56b5c7`)
  closed one seam while its own docstring overclaimed completeness (F-12). The architect's
  own mirror-gap check on the first fix (Firing 5) found the second seam (`create`) still
  open — a real hole, found by challenging a fix for completeness, not assumed closed.
  The fix (`3bf5824c`) closes it with **zero new exception shapes**: one predicate
  (`_foreign_slug_owner`), consulted at exactly the two store-write sites that can
  introduce a slug (a full census of all six `SpecContextService` write call sites is in
  the code review's final section), the same exception type, the same message shape. This
  is the standing order's prescribed shape exactly — structural cause found and closed at
  the owning seam, not a symptom patch stacked on the first fix.
- **Root-cause discipline, not accretion.** Net production LOC is **negative** (−130,
  −813 excluding S4's sanctioned addition) and net AI-surface LOC is **negative** (−943,
  skills 25→21) for a release that closed 24 bugs and hardened a CI gate class (S-1: the
  verdict-check bypass shapes) — the release did not buy its bug closures with added
  complexity; it shrank the surface while closing defects on it.
- **No repetition signal.** Reading the bug history per the standing order: no bug_id in
  this release's ledger recurs against the same file/symptom pair from a prior release's
  resolution — the one class with textbook recurrence (`v0.4.4-reviews-dir-untrackable`
  → `gitignore-verdict-evidence-untrackable-fourth-recurrence`, both about the same
  `.gitignore` catch-all shape) was this session explicitly diagnosed as a repeated
  symptom patch (three prior per-artifact whitelist lines) and closed **structurally**
  this session (`c7cc8d04`, inverting the rule for the whole release tree instead of a
  fifth per-artifact line) — exactly the standing order's prescribed remedy for a
  repetition signal.

**Conclusion: net bug-surface reduction, evidenced, not asserted.**

---

## 5. Security / privacy leakage note (explicit, per contract)

- **Public-asset privacy:** no consumer-specific names, private paths, IPs or hostnames
  found in any of the read artifacts (this document self-scans clean — see §6).
- **Secrets/tokens:** security handoff `f83cfb72*` reports `secrets_detected: 0`,
  `cve_findings: 0`, `new_dependencies: 0` across the full reviewed range (133 commits,
  165 files, +15058/−5466).
- **Auth/access control:** the F-1/F-12/Firing-5/Firing-6 arc is exactly an
  auth/access-control class (cross-context ownership of a shared repo-slug namespace) —
  closed at both write seams this release, verified above.
- **History rewrite integrity:** two privacy rewrites occurred this release (redacting
  historical blobs/messages only); the security handoff verifies both rewrites moved
  nothing but the redactions (identical range measurement pre/post-rewrite,
  `refs/original` empty, prior heads unreachable). This is why an earlier review artifact
  (`T-044-45-code-review.md`) cites a pre-rewrite hash (`ed5d64cd`) for a commit whose
  current hash is `3bf5824c` — same content, rewritten identity, disclosed and verified,
  not a discrepancy in the review's findings.
- **Generated files / consumer-specific data:** none introduced by this release's
  reviewed range per the security handoff's standard diff sweep.
- **No suspected leakage found requiring escalation to `security-reviewer`** beyond what
  the three completed security rounds already covered and closed.

---

## 6. Self-scan

`pytest tests/integration/test_repo_self_scan.py -q` re-run with this file staged: no
home-absolute path, no email literal, no IP, no hostname — every path repo-relative.

