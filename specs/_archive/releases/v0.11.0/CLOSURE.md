# Closure: Release — v0.11.0 — scan-v2: prior-published-term amnesty and push-gate hardening

**Status:** Aprovado
**Release ID:** v0.11.0
**Owner:** product-engineer
**Closed:** 2026-08-15
**Branch:** `feature/v0.11.0` (cut from `develop` at `d15bdf4e`; branch contract: `dadaia-gitflow`)
**Source SPEC:** `specs/releases/v0.11.0/SPEC.md` · **Source PLAN:** `specs/releases/v0.11.0/PLAN.md`
**QA close of the flat increment:** `ALPHA-1-QA.md` (APPROVED, 55/55 acceptance ids A1.1–A10.5)
**Close reopened:** 2026-08-15 — the pre-PR `code-reviewer` pass returned **APPROVE** with three
MEDIUM findings; the archive commit was reset, the findings were remediated on the branch, and
this document was amended before ship. See `## Drifts › reopened-close-for-review-remediation`.
**Picked set:** nine backlog entries — #19 #20 #22 #23 #25 #26 #27 #28 #29. **No bug and no
audit was picked**, because at pick time the ledger carried zero open bugs (both v0.9.0-window
LOWs closed by `hotfix/0.7.1`, merged at `d15bdf4e`, the very commit this branch was cut from)
and both 2026-07 audits were archived fully dispositioned by v0.8.0.

---

## Summary

v0.11.0 makes the push-range denylist scan usable for a second year. The v0.9.0 gate worked —
it refused its own author twice, both times legitimately — but it matched whole blobs, so any
edit to a long-lived file that already carried a matching line produced a new blob and a
refusal, even though the matched value was already published in the remote-reachable version
of that same path. That refusal demanded a rewrite of content the operator had already
published, which is exactly what the range scope exists to avoid, and the only escape was the
`--no-verify` bypass the gate itself names as discouraged. A security control whose first year
of production use trains its own bypass is a failed control. The release closes that without
acquiring an amnesty list and without narrowing the whole-blob ruler the operator ratified: a
candidate hit is suppressed if and only if the exact matched value already occurs in the prior
published text of the **same path**. The same value in a new path still refuses. A new value in
an edited path still refuses — the predicate keys on the matched value, never on the pattern,
which is the whole difference between an amnesty and a smuggling path, and it is the property
the QA review was asked to attack directly. The 29 latent one-time blockers under `tests/**`
are cleared, and they stopped being a review figure: the self-scan sentinel now covers
`tests/**` behind a shrink-only baseline that fails if a new literal appears **and** fails if a
baseline row is cleaned without deleting its row, so the count can only go down.

Around that core, the same pass closed every honesty and robustness residual on the same
surface. The 5 MB per-blob cap stopped being a blind spot reported as a lie: an oversized blob
now has its first 5 MB scanned and can refuse the push, is read through a bounded stream that
is closed early so the remainder is genuinely never fetched, and is reported as what it is —
this file, this size, first 5 MB scanned, remainder not scanned, verify by hand — while
genuinely undecodable blobs keep their own count and their own wording. The foreign-name term
layer is derived from the context registry rather than from directory listings, so a registered
context whose repository directory is gone keeps protecting its name at exactly the moment that
name becomes more sensitive; both of the pushing repository's own identities are subtracted,
because a context's name and its repo slug are separate fields. Every operator-facing string
the gate emits that names a blob path now masks that path's private-name-bearing segments —
the refusal and the oversized note alike — through a shared primitive that the `--redact`
operator surface also consumes, and a path matching nothing renders byte-identically to before,
so diagnostics stay satisfiable. Pre-push shas are shape-validated before they can reach a git
argv, closing a measured class where an option-shaped value produced a successful empty range
and silently no-opped the scan. The batch parser fails typed and a desynchronised stream aborts
instead of inventing objects that the skip counters would then report as fact. And the whole
conversation runs in fixed-size chunks, so the resident set is a constant instead of growing
with the range.

The release also corrects its own record. The archived v0.9.0 closure reported a
fallback-range benchmark measured on a synthetic corpus roughly two orders of magnitude
smaller than real content. That document is FROZEN and was not edited, reopened or annotated;
the correction is forward, in memory, on figures measured against the shipped code. The
honest outcome is not the one the entry predicted: the real numbers came out **better**, not
worse — 0.42 s/MB against the ~1.3 s/MB intermediate reading, at a 285.5 MiB peak — because
the chunked reader landed in the same release that measured it. Matching is ~98% of the
fallback cost and is deliberately left unoptimised, with the reason written down. Ten
acceptance criteria families, 55 ids, all verified independently by QA against the shipped
code rather than the implementer's report; **2,253** tests green at the alpha-1 QA run and
**2,261** after the pre-PR review remediation; zero new e2e tests.

The close then reopened once. The pre-PR six-axis `code-reviewer` pass over the release delta
returned **APPROVE** — zero CRITICAL, zero HIGH — with three MEDIUM findings that were fixed on
the branch rather than deferred, because two of them sat on the exact surface this release
exists to make trustworthy: the amnesty predicate compared the matched value against prior text
by raw substring containment while every detection layer matches anchored, so a *different*
already-published value could suppress a new one that was merely a substring of it; and the
scan's three term sources were each consumed twice, so a one-shot iterator would have handed the
scan an empty term set. Neither was reachable in the shipped wiring or leaked a byte sequence the
same path had not published, and both are now closed at the root: suppression re-runs each
layer's own anchored matcher against the prior text and requires **value equality**, and the term
sources are materialised once before either consumer touches them. The third MEDIUM was an
evidence claim in this document that its own delta did not substantiate; it is corrected below,
and the two assertions it claimed now exist.

## Tasks completed

Every task reached `[x]` with its acceptance ids satisfied. **`product-engineer` has no
shell**, so per-task commit SHAs below are transcribed only where an artifact already records
them (TASKS.md evidence, the QA review, the security handoff); the remainder are named by
their exact commit subject and resolve on `feature/v0.11.0` — the dispatcher fills them at
commit time rather than the closer guessing. No history was rewritten in this release.

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-110-01 | [git] Definition content committed on `feature/v0.11.0` (trio + nine backlog pick flips + `candidates.md`) | `11aad989` (phase flip one commit later — see `## Drifts`) |
| T-110-02 | [git] Milestone (a): merge into `develop`, diff-based security review, push | merge `89a703b8`; APPROVED handoff `2026-08-15T173153Z-security-reviewer-v0.11.0-definition-push`; pushed, gate exit 0 |
| T-110-03 | FR7 — pre-push sha validation and git argv hardening (#25) | `5368d59a` — `fix(T-110-03): validate pre-push shas and close the git argv interpolation sites` |
| T-110-04 | FR8 — typed parse boundary, desync aborts instead of fabricating (#26) | `14aea760` — `fix(T-110-04): surface batch-stream desync as GitObjectReadError instead of fabricating` |
| T-110-05 | FR9 — chunked batch conversation, constant resident bound (#27) | `d47f39c6` — `perf(T-110-05): chunk the cat-file --batch conversation to a constant resident bound`; capture `.dadaia/tmp/software-engineer/20260815/t-110-05-peak-bound-measurement.txt` |
| T-110-06 | FR4 — oversized blobs partially scanned and honestly reported (#20) | `848f106a` — `fix(T-110-06): scan the first 5 MB of an oversized blob and stop calling it binary` |
| T-110-07 | FR6(a) — masking primitive extracted into `core/redaction.py` | `7b102e0c` — `refactor(T-110-07): extract the redaction primitive into core for shared use` |
| T-110-08 | FR6(b) — path-segment masking in both gate renderers (#23) | `6d719c38` — `fix(T-110-08): mask private-name-bearing path segments in every gate refusal and note` |
| T-110-09 | FR2 — prior-side same-path lookup inside the chunk loop (#19a) | `12361384` — `feat(T-110-09): resolve each scanned path's published prior blob in the same conversation` |
| T-110-10 | FR1 — the amnesty suppression predicate (#19b) | `b7440be1` — `feat(T-110-10): suppress a hit whose matched value the same path already published` |
| T-110-11 | FR1 — integration proof over real ranges with a real remote (#19c) | `e3acf775` — `test(T-110-11): pin the amnesty over real git ranges` |
| T-110-12 | FR3 — sentinel covers `tests/**` behind a shrink-only baseline + the marker (#19d, #29) | `a075ff57` — `test(T-110-12): extend the self-scan sentinel to tests/ with a shrink-only baseline`; baseline **29 rows** (14 home-abs-path, 9 email-address, 5 ipv4-literal, 1 secret-token) |
| T-110-13 | FR5 — registry-derived foreign-name set, after the enumeration (#22) | `4c1b02b4` — `fix(T-110-13): derive the foreign-name layer from the registry so a DEAD context still protects its name`; enumeration capture `…/t-110-13-enumeration-capture.txt` |
| T-110-14 | Real-content performance measurement (#28 evidence) | `e4492735` — `chore(T-110-14): measure the shipped scan on real content, ordinary and fallback ranges` |
| T-110-15 | `qa-engineer` review of the increment (alpha-1 close) — **APPROVED**, 55/55 ids | reserve `9ceceaa2`, done `15cc494f`; artifact `ALPHA-1-QA.md` + handoff `2026-08-15T185812Z-qa-engineer-v0.11.0-alpha1` |
| T-110-16 | Memory update in the CLOSURE phase — four atoms + catalog + index ripple | `3195d84b` — `docs(T-110-16): memory — amnesty semantics, registry-derived layer, real-content perf` |
| T-110-17 | CLOSURE, dispositions, archive, version bump | this file; final sha assigned by the dispatcher at commit time |
| T-110-18 | [git] Milestone (b): ship — code review, merge, security review, push, PR `develop` → `main`, CI green | **Pending ship.** Archives `[ ]` **by design** — the ship task cannot flip its own marker after T-110-17 moves the directory into FROZEN `specs/_archive/`. Fourth occurrence of the same flat-release canon gap (v0.8.0, v0.9.0, v0.10.0, here); completion evidence lives in the milestone-(b) merge commit, the two reviewer handoffs, the PR and CI. Not re-raised as a new intake candidate |

**No task id was created for the review round.** The three review-remediation commits —
`9648030a` (M1 anchored-value suppression + the matcher-level oversized pinning test),
`697548aa` (M2 single materialisation of the three term sources), `517a62bd` (LOW4 `local_sha`
shape check, LOW5 non-blob prior objects discarded, and the adapter-level oversized pinning
test) — ride **between T-110-16 and T-110-17**, in the window T-110-18's own review step
opened. They are review remediation on tasks already `[x]`, not new scope: no acceptance id
moved, no picked entry changed, and the write set stays inside T-110-03/T-110-06/T-110-09's.
Inventing T-110-19 for them would have misfiled a review round as fresh work.

## Validations

V1–V14 are PLAN §9's validation plan, one row each. Every figure was independently re-run by
`qa-engineer` at T-110-15 against the shipped code, not taken from the implementer's report.
V15–V16 are not from PLAN §9: they record the pre-PR review round that reopened this close.

**Suite figure, stated once so the two runs are never confused.** The **alpha-1 QA run** at
T-110-15 measured `2253 passed, 3 skipped` — that figure is the QA run's and is labelled as such
everywhere it appears below. The **post-remediation** full gate, after the three review-fix
commits added 9 tests, measures `2261 passed, 3 skipped`. The 3 skips are the same
environment-gated three in both runs.

| Description | Command | Evidence |
|-------------|---------|----------|
| V1 — Full local gate (A10.5) | `dadaia ci preflight` | All 5 checks PASS: ruff format, ruff check, `mypy --strict`, `lint-imports`, pytest. **Alpha-1 QA run** (T-110-15): `2253 passed, 3 skipped, 1 warning in 92.78s` under `-m 'not quarantine' -n auto`; the 3 skips are environment-gated (two Windows-only, one needing a non-loopback IPv4) and unrelated to this release. **Post-remediation re-run:** `2261 passed, 3 skipped` — see V16 |
| V2 — Ring purity (A1.5, A5.3, A10.3) | `lint-imports --config setup.cfg --no-cache` | Green, folded into V1. No new `ignore_imports` entry; `tests/contract/test_import_linter_ignore_cap.py` unmodified and passing inside the alpha-1 QA run's 2253 — and inside the post-remediation 2261, with the ignore cap still unmoved (`code-reviewer`: 9 contracts kept, 0 broken, no new `ignore_imports`). `features/chokepoints/**` imports no `infrastructure` and no `cli`; `core/redaction.py` is stdlib-only with zero I/O (QA direct read) |
| V3 — Matcher + decision suites (A1.1–A1.4, A4.4–A4.5, A6.1–A6.3, A7.1–A7.3) | `pytest tests/unit/features/chokepoints -p no:cacheprovider` | **87 passed.** Includes the three amnesty semantic cases and the deliberate smuggling-path attack (`test_amnesty_does_not_apply_to_a_new_value_in_an_edited_path`), the oversized note on `decision.warn` for allow **and** refuse, and the masking pair (masked segment / byte-identical when nothing matches) |
| V4 — Adapter suite (A2.1–A2.6, A4.2, A8.1–A8.2, A9.2–A9.3) | `pytest tests/unit/infrastructure/test_git_object_reader.py -p no:cacheprovider` | **26 passed.** Carries A4.2's byte-count assertion (`len(text.encode()) == scanned_bytes`, proving the over-cap remainder is never read), the three fail-closed absence cases, the typed-desync abort, and the invocation-count contract (two prior-side calls per **chunk**, not per blob) |
| V5 — Real-git ranges (A1.6, A2.3, A5.1, A10.2) | `pytest tests/integration/test_push_gate_denylist.py -p no:cacheprovider` | **12 passed.** Editing a `tests/**` file carrying a pre-existing fixture literal no longer refuses; the same value in a new path still refuses; a forced git failure on the prior-side lookup refuses naming the failure and `--no-verify`; the `git mv`-into-archive FROZEN↔scan test passes **unmodified** (QA verified by diff-hunk inspection, not by trusting the claim) |
| V6 — Repository sentinel (A3.1–A3.4) | `pytest tests/integration/test_repo_self_scan.py -p no:cacheprovider` | **2 passed.** `_SCAN_SCOPE = ("dadaia_workspace", "specs", "tests")`; both directions of the shrink-only baseline assert (no hit outside it, every row still hits); the `specs/_archive/**` and `specs/audits/_archive/**` exclusions and the deterministic empty foreign-slug set are unchanged |
| V7 — Sentinel marker reachability (A3.5) | `pytest tests/integration/test_repo_self_scan.py -m integration --collect-only -q` | **2 collected.** `pytestmark` now carries `[integration, slow]`, matching the six sibling modules; the SENTINEL is reachable under `-m integration`, `-m slow` and `-m "not quarantine"` alike |
| V8 — No amnesty list in the product (A3.6, A10.1, A10.4) | `grep -rn "AMNESTY\|SANCTIONED\|ALLOWLIST" dadaia_workspace/features/chokepoints/ dadaia_workspace/infrastructure/git_objects.py` | **Empty — 0 hits.** A4.1's contract test is confirmed **unmodified** by direct diff inspection (its function body falls entirely outside every changed hunk). The FR3 baseline lives only in the test module; the production matcher's source contains no reference to it |
| V9 — Redaction regression (A6.4) | `pytest tests/unit/cli/test_redact_output.py -p no:cacheprovider` | **15 passed with unmodified assertions** — the stated proof that the `core/redaction.py` extraction was mechanical. `cli/redact.py#ContextRedactor` confirmed a thin consumer by direct read |
| V10 — FR5 enumeration (A5.5) | one-off run of the widened term set over the pushable range and the tracked tree | `.dadaia/tmp/software-engineer/20260815/t-110-13-enumeration-capture.txt`. Widened set **11 terms**. Pushable range `origin/develop..develop`: **0 objects, 0 hits**. Tracked tree (990 files): **6 hits**, each individually dispositioned — one product-owned generic asset-filename literal, two archived backlog entries, two bug-ledger files, one `dadaia doctor` golden fixture — all pre-existing, none touched by this release, all amnestied by FR1 by construction for any future edit. The capture is redacted at authoring: real names never printed, only `foreign-name-NN` ordinals and lengths |
| V11 — Ordinary-range timing, before vs after (A9.5) | timed scan over the release delta at the base commit and at the tip, four repeated pairs | `.dadaia/tmp/software-engineer/20260815/t-110-14-ordinary-range-capture.txt`. 70 blob objects: old mean **~36.7 ms**, new mean **~48.3 ms** — **~+11.6 ms absolute**, exactly FR2's budgeted design cost of two extra batched subprocess calls per chunk (one chunk at this size), both sub-100 ms and dominated by process-spawn noise. **No algorithmic regression**; A9.5 satisfied |
| V12 — Fallback-range real-content measurement (A9.1, A9.4) | timed run over the `--not --remotes` shape on the shipped code | `.dadaia/tmp/software-engineer/20260815/t-110-14-fallback-range-capture.txt`. **9,095 blobs** (9,051 decodable, 44 skipped-binary) / **130.29 MB**; read **1.261 s** + match **53.871 s** = **0.423 s/MB**; **peak RSS 285.5 MiB**. Peak-bound proof separately captured at T-110-05: 600 → 6,000 blobs (10×) grows peak RSS only ~22% (16,000 → 19,456 KiB) |
| V13 — Specs health | `dadaia specs doctor` | **Owed to the dispatcher at the T-110-17 commit** — `product-engineer` has no shell. QA's T-110-15 run reported 4 ERRORs, all from one cause (the non-canonical `**Status:**` annotation on the release trio, SPEC-DOC-004 ×3 + the derived SPEC-DOC-024); that cause is **fixed in this closure** — see `## Drifts › non-canonical-status-token-in-the-release-trio`. **Discharged at V15, no longer owed:** the pre-PR review ran `dadaia specs doctor` over the delta and reports **0 errors, 16 warnings**, confirming the four ERRORs fixed. The 16 warnings are the pre-existing `token_estimate` drift class (V15 INFO), not this release's. Re-run once more before the re-archive, since this amendment changed the document |
| V14 — Gate self-proof (FR10, R5) | the release's own `develop` push passes the modified gate with **no** `--no-verify` | **Due at T-110-18 (milestone b), not a gap here.** The definition push already cleared the pre-modification gate at T-110-02 (exit 0). This document, the memory diff and every capture path cited are authored under the standing privacy rule and will be scanned as new blobs by the very gate this release modifies |
| V15 — Pre-PR six-axis code review of the release delta (T-110-18 step 1) | `code-reviewer` dispatch over `89a703b8..ff922566` | **APPROVE** — **0 CRITICAL, 0 HIGH, 3 MEDIUM, 3 LOW, 3 INFO** across all six axes. 37 files changed (+3,457 / −283), 7 production files, 58 tests added, 3 disclosed supersessions, 0 new test modules, 0 new e2e; 142 targeted tests pass; `lint-imports` 9 contracts kept / 0 broken; `dadaia specs doctor` **0 errors, 16 warnings** — which independently discharges **V13** (the four SPEC-DOC-004/024 ERRORs QA saw are confirmed fixed). Handoff `.dadaia/handoff/dadaia-workspace/2026-08-15T192401Z-code-reviewer-v0.11.0-prepr.handoff.json`. The three MEDIUMs are M1 (substring amnesty over-grant), M2 (double-consumed term sources), M3 (this document's unsubstantiated oversized-amnesty evidence claim); the three LOWs are the `local_sha` shape gap, the tree-object prior read, and a CHANGELOG identifier error |
| V16 — Review remediation on the branch, before ship | `software-engineer` dispatch on the V15 findings, then the full local gate | **4 findings fixed + 1 evidence-pinned**, 6 files changed, 9 tests added, across `9648030a`, `697548aa`, `517a62bd`. Post-remediation full gate: **`2261 passed, 3 skipped`** — **+8 net** against the alpha-1 QA run while the remediation handoff reports **9 tests added**. That one-test difference is **not reconciled by any artifact in hand** and is stated rather than smoothed: the measured run governs the figure, and the discrepancy is owed a one-line explanation at the ship commit (see `## Test dispositions`). M1 and M2 fixed at the root, LOW4 and LOW5 fixed, M3 pinned by two new tests (see the amended drift below). Handoff `.dadaia/handoff/dadaia-workspace/2026-08-15T193500Z-software-engineer-v0.11.0-prepr-remediation.handoff.json` |

## Drifts

### definition-commit-and-phase-flip-split

**Description:** T-110-01's done criterion was one commit carrying the trio, the nine backlog
pick flips, `candidates.md` **and** the `ACTIVE.md` phase flip `DEFINITION` → `IMPLEMENTATION`.
The content landed at `11aad989`; the phase flip landed one commit later as a `chore(tasks)`
follow-up. The task is correctly `[x]` — every artifact exists and the phase is right — but the
atomicity the task asked for was not achieved on the first attempt.

**Resolution:** Recorded rather than smoothed. The cost is real but bounded: for the span of
one commit the repository claimed a phase that no longer matched the work, which matters
because the gate reads that field to decide whether `specs/memory/**` is writable. Nothing
raced it — this release ran as a single dispatched sequence — so the exposure was theoretical.
The lesson is that a task whose write set spans "content plus the pointer that governs the
content" is easy to split under staging pressure; the pointer should be staged first, not last.

**Memory updates:** none — an intra-release sequencing artifact is not current product truth.

### reservation-slip-self-caught-at-t-110-08

**Description:** The implementer began T-110-08's work before landing its
`chore(tasks): start` reservation commit, and caught the slip itself during the task rather
than having it surfaced by a reviewer.

**Resolution:** Self-corrected in the same task, and disclosed rather than quietly repaired.
The reservation commit exists so a *parallel* session can learn who took a task; this release
ran as one dispatched sequence with no second session, so the slip cost nothing observable.
It is recorded because "no one was watching" is precisely the condition under which marker
discipline decays, and `dadaia-task-manager`'s markers are discipline, not a hook check —
nothing would have blocked it.

**Memory updates:** none.

### oversized-never-amnestied-scope-boundary

**Description:** FR1 and FR4 meet on one object class: a blob over the 5 MB cap whose scanned
prefix produces a hit. Neither the SPEC nor the PLAN states whether the amnesty may suppress
such a hit. The prior side has its own cap — an over-cap prior blob maps to *absence* per
FR2's fail-closed table — so the two rules could have been read as composing into an amnesty
granted from a prior blob that was itself only partially read.

**Resolution:** Resolved in the conservative direction: an oversized blob is **never amnestied**.
An amnesty is only ever granted from prior content the adapter actually read in full, so a prior
blob that is over the cap, undecodable or absent yields no prior content and every hit on it
refuses. This keeps FR2's three-way table literally true and keeps the fail-open (partial
coverage of the new side) from ever compounding into a fail-open on the suppression side.

**Evidence, corrected.** The first version of this section claimed the boundary was "pinned by
test" and "stated in memory as product truth". The pre-PR review (V15, MEDIUM **M3**) checked
both legs and found neither substantiated by the delta, and the finding was right on both counts.
What was true then: the behaviour holds **by construction** — the adapter yields an oversized
object from its own bounded-stream path, which never sets `prior_text`, so the field defaults to
absent and no hit on an oversized object can be suppressed. What is true now, after V16:

- **Pinned by test — two, one per layer.** Matcher level:
  `tests/unit/features/chokepoints/test_denylist_scan.py::test_oversized_object_carrying_prior_text_still_hits_when_value_not_amnestied`
  (the `_oversized_obj` helper gained a `prior_text` parameter so the composition is expressible
  at all). Adapter level:
  `tests/unit/infrastructure/test_git_object_reader.py::test_new_objects_oversized_current_object_never_carries_prior_text_even_with_resolvable_base`,
  which proves the guarantee holds even when a resolvable base **and** an under-cap prior version
  of the same path both exist — the exact configuration under which a composed amnesty would
  otherwise have been granted. Landed at `9648030a` and `517a62bd`.
- **What memory actually says**, stated without overclaiming: `sdd-gate-v3.md`'s fail-closed
  table carries the **prior-side** row — "the path is absent at the base, or its prior blob is
  over the cap or undecodable ⇒ no prior content, so every hit on it refuses" — and a separate
  row for the **current-object** oversized case that governs scanning only: "scan its first 5 MB
  and report it as an oversized note; the remainder is never fetched". The atom does **not**
  carry a sentence saying an oversized *current* object is never amnestied. The earlier claim
  that it was "stated in memory as product truth" was false and is withdrawn. Whether the atom
  should gain that sentence is a memory decision for the re-close pass, listed under
  `## Intake candidates`, not asserted here.

The lesson is the release's own theme turned on its author: this drift was written from what the
implementation obviously did, and "obviously true" was transcribed as "pinned and recorded"
without opening either file. That is precisely the failure class entry #28 was picked for, and it
was caught by a reviewer rather than self-caught.

**Memory updates:** `specs/memory/product/sdd/sdd-gate-v3.md` — the fail-closed table's
prior-side rows and the "no prior content ⇒ every hit refuses" sentence. The current-object
oversized row was rewritten by this release for FR4 (scanning, not amnesty); no memory sentence
was added for the amnesty boundary itself, and none is claimed.

### expected-one-task-test-breakage-t-110-10-to-11

**Description:** Landing T-110-10 (the suppression predicate) broke a v0.9.0 integration test
that asserted the **opposite** behaviour — `test_editing_the_same_content_produces_a_new_blob_and_a_refusal`
— and the branch stayed red for exactly the span between T-110-10 and T-110-11, which is the
task that rewrites that test.

**Resolution:** Correct by construction and disclosed at the time, not discovered at review.
The broken assertion *is* the blocking problem this release exists to fix: a v0.9.0 test
asserting that an edit refuses is a v0.9.0 assumption, not a v0.9.0 contract. The rewrite in
T-110-11 asserts the superseding behaviour, names the superseded test in its own docstring and
cites the SPEC section that authorises the change. QA independently verified all three rewrites
by diff and confirmed nothing was weakened, deleted or skipped to reach green. The process note
worth keeping: a task pair whose first half is knowingly red needs both halves in the same
review window, which PLAN §3's ordering already ensured.

**Memory updates:** none — the shipped behaviour is recorded in the amnesty section; the
transient red is not product truth.

### empty-pushable-range-at-the-fr5-enumeration

**Description:** T-110-13's step 1 was to run the widened term set over **the pushable range**
and disposition every hit before the wider layer landed (acceptance A5.5). At capture time
`origin/develop..develop` was **empty** — 0 objects, local and remote both at `89a703b8` — so
the pushable-range half of the enumeration could only ever return zero hits and proved nothing.

**Resolution:** The tree half was executed instead of declaring the criterion vacuously
satisfied: 990 tracked files scanned against the 11-term widened set, 6 hits, each
individually dispositioned with a stated reason. Every one is a pre-existing file untouched by
this release, verified by `git log --name-only` over the release range, so none can appear as a
*new* object of any range this release pushes — and each is amnestied by FR1 by construction on
any future edit, which is the literal case the grill predicted. One deserves naming: the active
bug ledger republishes its whole blob on every append, so its hit **will** enter a future push
range the next time a bug event is written, and FR1 is exactly what keeps that from refusing.
The capture also corrects the SPEC's "two wider-set hits" to the measured one-hit-per-object
figure for this commit — the scanner returns at most one hit per object, so the two figures
count different things.

**Memory updates:** none directly; the registry-derived layer and the amnesty that covers these
hits are both recorded in `sdd-gate-v3.md`.

### empty-ordinary-range-at-the-perf-measurement

**Description:** A9.5 asks for the ordinary `origin/develop..develop` range timed at the
release base and at the tip. That range was empty for the same reason as the drift above —
nothing had been merged from this release yet — so the literal command measures nothing.

**Resolution:** A substitute range was used and named: `d15bdf4e..HEAD`, this release's own
delta (26 commits, 70 blob objects, 266 total objects), which is precisely what
`origin/develop..develop` **will** contain once milestone (b) merges. Four repeated old/new
pairs on the real repository, not a synthetic corpus — the shape of measurement error this
release exists partly to correct. Recorded because the substitution is a judgement call: the
criterion's intent (does the shipped code regress on the range operators actually push?) is
served, its literal text is not, and rounding that into a pass is how the v0.9.0 V14 figure got
into an archived document in the first place.

**Memory updates:** `specs/memory/product/sdd/sdd-gate-v3.md` — the ordinary-range figure is
recorded as ~48 ms for a 70-blob push, with the ~12 ms prior-side cost named.

### the-28-correction-came-out-directionally-positive

**Description:** Entry #28 was picked on the premise that the archived v0.9.0 V14 figure
**understated** the real cost — 2.978 s reported against a real range believed to cost ~147 s
at ~1.3 s/MB. The measurement on the shipped code returned 55.1 s total at **0.423 s/MB** for a
similar-sized corpus: still far above the archived synthetic figure, but roughly **3× better**
than the intermediate reading the entry itself carried, with read time alone improving ~3.4×.

**Resolution:** The correction is written as measured, in both directions, rather than only in
the direction the entry predicted. Two figures are named as superseded in memory: the archived
2.978 s synthetic benchmark and the ~1.3 s/MB intermediate reading. The improvement is
attributable and stated — FR9's chunked batch conversation landed in the same release that
measured it, so "the correction is smaller than expected" and "this release made it smaller"
are the same fact, and a closure that quoted only the pessimistic figure would have been
precisely the evidence-fidelity failure entry #28 was raised about. `specs/_archive/**` was not
edited, reopened or annotated: the correction is forward, in the atom, citing the entry.

**Memory updates:** `specs/memory/product/sdd/sdd-gate-v3.md` — the measured-cost paragraph,
with both superseded figures named.

### match-throughput-optimisation-rejected

**Description:** A9.4 required a recorded decision on match-throughput optimisation — adopt it
with before/after real-content numbers, or reject it with a reason. The measurement makes the
case for it look strong in isolation: matching is 53.9 s of the 55.1 s fallback total, ~98%.

**Resolution:** **REJECTED for this release**, with the reason recorded in the capture and
repeated here so it survives the capture's lifetime. Three grounds. (a) The fallback shape is
the rare one — it fires only when the remote sha is zero or unresolvable, i.e. a genuinely new
ref or a fresh clone, and never again on the same repository once a remote-tracking ref exists;
the ordinary shape that dominates real operator experience is ~48 ms and is untouched by match
throughput at that scale. (b) A genuine fix — collapsing the baseline patterns into one
alternation, or adopting a compiled/vectorised engine — is separate, non-trivial work with its
own correctness surface across every existing baseline-pattern test, and no picked entry in
this release authorises a matcher-engine change. (c) 55 s for a one-time 130 MB full-history
scan is inside operator tolerance. Rejecting with a written reason, rather than silently not
doing it, is the point: the next reader gets the measurement and the argument, not just the
absence.

**Memory updates:** `specs/memory/product/sdd/sdd-gate-v3.md` — matching named as the dominant
term and deliberately unoptimised, with the reason.

### non-canonical-status-token-in-the-release-trio

**Description:** QA finding **QA-1 (MEDIUM)**, raised at T-110-15 and non-blocking for that
task. `SPEC.md`, `PLAN.md` and `TASKS.md` each carried
`**Status:** Aprovado — operator-delegated approval, 2026-08-15 (goal directive)` instead of
the bare canonical token. `dadaia specs doctor` reported 4 ERRORs from that single cause
(SPEC-DOC-004 ×3 plus the derived SPEC-DOC-024). `DADAIA.md` §5 states the three status tokens
are kept "as they are"; every prior release used the bare token. The deviation originates in
T-110-01's authored prose — `product-engineer`'s own surface, not any implementer's.

**Resolution:** Fixed in this closure, before any memory write: all three files now carry
`**Status:** Aprovado` on its own line, with the provenance moved to an adjacent
`**Approval provenance:** operator-delegated, 2026-08-15 (goal directive)` line, so the fact is
kept and the machine-readable token is exact. Worth stating plainly: the finding is against the
closer's own authoring, it was surfaced by the reviewer rather than self-caught, and the
temptation it created — to treat a status line as prose because the annotation was true and
useful — is exactly what a machine-checked token exists to refuse. The canonical tokens are a
contract, and a true annotation appended to a contract still breaks it.

**Memory updates:** none — a status-token deviation in one release's documents is not product
truth. `specs-doctor`'s SPEC-DOC-004 behaviour is already recorded and needed no change; it
worked exactly as designed.

### reopened-close-for-review-remediation

**Description:** This release closed once and was reopened. The archive commit `ff922566` had
already moved `specs/releases/v0.11.0/` into FROZEN `specs/_archive/` when T-110-18's first step
— the pre-PR six-axis `code-reviewer` pass — returned **APPROVE with three MEDIUM findings**
(V15). Two of them were behavioural and landed on the surface this release exists to make
trustworthy; the third was an evidence claim in this very document. The archive commit was
**reset**, the release directory returned to `specs/releases/`, the findings were remediated on
`feature/v0.11.0`, and this document was amended. Same manoeuvre as v0.9.0, which set the
precedent, and for the same reason: a document that has entered `_archive/` cannot be corrected
in place, so a finding against a closure is either fixed by reopening the close or it ships
wrong.

**Resolution:** Reopened rather than deferred, and the split is deliberate. Findings that make a
shipped claim false, or that put a new conditional-allow edge on a security gate, are fixed
**before** ship; findings that ask for scope the release did not pick go to intake. Under that
rule five of the six actionable findings were fixed here:

- **M1 — amnesty over-grant by substring containment (the one that mattered).** Detection is
  anchored on all three layers (baseline regexes carry lookarounds, slugs compile to
  `\bslug\b`), but suppression tested raw `matched_value.lower() in prior_lower`, so the two
  sides used different notions of "a value". The reviewer reproduced it read-only on the shipped
  matcher: a *different* already-published home-path value suppressed a new standalone value that
  was merely its substring, and a slug glued inside a longer word — never detectable there —
  suppressed a new standalone occurrence of that slug. Fixed at the root by making the predicate
  **layer-aware and value-equal**: `_pattern_suppressed` re-runs that pattern's own regex over
  the prior text and compares matched values case-insensitively, `_slug_suppressed` re-runs the
  `\bslug\b` pattern (where a boolean match *is* value equality), and `_term_suppressed` keeps
  substring semantics because FR3(1) defines an operator term's "occurs" as substring on the
  detection side too — so both sides still agree, layer by layer. Never substring for a pattern
  or a slug again. `9648030a`. This is not cosmetic: the over-grant sat inside R1, the smuggling
  surface `security-reviewer` is pre-committed to attack at milestone (b), and shipping it would
  have made this closure's own summary sentence — "the predicate keys on the matched value" —
  true only of the characters, not of the value.
- **M2 — latent fail-open from double-consumed term sources.** `_run_denylist_scan` built
  `_PathMasker(terms, patterns, slugs)` — which materialises all three — *before* its own
  `list(...)` calls, so a one-shot iterator would have reached the scan **empty**, i.e. a silent
  allow on a gate whose FR10.3 invariant is "every new edge lands on refusal". Unreachable in
  shipped wiring (the container returns tuples, the CLI passes a list) and a regression against
  the base commit, where each source was touched exactly once. Fixed by materialising all three
  first and constructing the masker from those lists. `697548aa`.
- **LOW4 — `local_sha` shape check.** The adapter's docstring claimed a second, independent
  argv-defence layer "regardless of what already validated the caller's input", but only
  `remote_sha` was shape-checked; `local_sha` reached the `git rev-list` argv unchecked, and the
  trailing `--` sits after the revisions, so an option-shaped value would still parse as an
  option. `_SHA_SHAPE_RE` is now applied to `local_sha` too, so the code matches its own claim
  rather than the claim being softened. `517a62bd`.
- **LOW5 — non-blob prior objects discarded.** Prior-side resolution parsed `%(objecttype)` and
  threw it away, so a path that was a **directory** at the base had its tree object fetched and
  decode-attempted as prior text; tree bytes carry filenames verbatim, so any tree that happened
  to decode would have fed the amnesty. Now `obj_type != "blob" → continue`, which also makes the
  "prior **blob**" wording in the port's contract exact. `517a62bd`.
- **M3 — this document's own evidence claim** — corrected in the amended drift above, and made
  true by two pinning tests rather than by softening the sentence.

Not fixed here, by the same rule: **LOW6**, the `[0.8.0]` `CHANGELOG.md` entry naming
`skipped_oversized`/`skipped_binary` — identifiers that exist only in the backlog entry's
*proposal*, never in the code, which ships `ScanOutcome.skipped_binary_count` plus structured
`oversized_notes`. That entry is **owed at the ship commit** (`CHANGELOG.md` is outside
`_archive/` and is written at the same commit as the version bump); it is called out in
`## Version bump decision` so it cannot be missed. The three INFOs are recorded observations, not
defects, and are not re-raised.

**Cost of the reopen, stated plainly.** Three commits ride between T-110-16 and T-110-17 with no
task id of their own, T-110-16's and T-110-17's markers returned to `[ ]` with the reset archive
commit, and the alpha-1 QA figure and the shipped figure now differ — every one of which is a
traceability seam a reader could mistake for sloppiness. Each is disclosed at the place it shows.
The alternative — ship the archive as it stood and carry three MEDIUMs, two of them on the
security gate, into `main` — was never the cheaper option.

**Memory updates:** none required by the reopen itself. Two consequences are worth stating
because they cut in opposite directions. **First, M1's fix moved the code onto a property memory
already asserted**: `sdd-gate-v3.md` states that "a value the same path already published never
refuses again" and that the predicate "keys on the matched value itself and never on the pattern
id or the term layer" — before the fix that was true of characters and not of values; it is now
true as written, so the atom needed no correction and would have needed one had the finding been
deferred. Its `iff the exact matched value occurs … in that prior text` sentence remains a true
necessary condition and the code is now strictly stricter for the pattern and slug layers; a
one-line refinement to say so is listed under `## Intake candidates`, not smuggled in here.
**Second, `quality-assurance.md`'s test census now trails the tree**: the atom reads ~2,253
collected against a shipped 2,261. It was accurate when written and is off by 8 only because of
the remediation; the correction is owed at the re-close memory pass and is listed rather than
performed, since this amendment writes no memory.

## Memory updates

All memory writes landed in the CLOSURE phase (`ACTIVE.md` set to `phase: CLOSURE` before the
first write) and **before** this file, holding the finalization order memory → CLOSURE →
archive. Every SPEC §5 row is discharged below, file by file, including the rows that resolved
to "no change". No atom gained a `Changelog`, `History`, `Histórico` or `Versions` section, and
none narrates a past version.

- `specs/memory/product/sdd/sdd-gate-v3.md` — one pass over the push-range scan section
  covering both bound entries. New `#### Prior-published-term amnesty` subsection states the
  suppression rule and its three consequences (same-path prior-published value never refuses; a
  new path still refuses; a new value in an edited path still refuses, because the predicate
  keys on the matched value and never on the pattern id or layer), the no-amnesty boundary in
  the `--not --remotes` fallback shape, and the fact that the matcher acquires no parameter and
  no new input source. The reader paragraph now states the chunk-bounded conversation (500
  shas) as the resident-set bound. Term layer 3 is rewritten from directory-derived to
  **registry-derived** — `{registry names} ∪ {registry repo_slugs} ∪ {repos/ dir names}` minus
  **both** own identities — with the DEAD-context rationale and the degrade-to-directories
  behaviour on a missing or malformed registry. The fail-closed table gains the prior-side
  failure row, the no-prior-content row and the typed-desync row, and its oversized row is
  rewritten from "skipped, content never fetched at all" to "first 5 MB scanned, remainder never
  fetched", followed by a paragraph on the two separately-counted, separately-worded skip
  classes. The refusal section gains the class-level masking rule (every operator-facing string
  naming a blob path masks its offending segments, through the shared `core/redaction.py`
  primitive, with non-matching output byte-identical). The branch-policy paragraph gains
  pre-push sha shape validation, the `--` end-of-options marker and the prefix check. A new
  measured-cost paragraph carries the real figures — fallback 9,095 blobs / 130.29 MB, read
  1.261 s + match 53.871 s = 0.423 s/MB at 285.5 MiB peak; ordinary ~48 ms for 70 blobs with
  ~12 ms of prior-side cost — and names the archived 2.978 s synthetic benchmark **and** the
  ~1.3 s/MB intermediate reading as superseded, plus the rejected match-throughput
  optimisation. Both surviving invariants are stated explicitly and unchanged: no
  sanctioned-terms or amnesty list anywhere, and the FROZEN↔rename blockquote verbatim.
  Frontmatter `tldr`/`summary` updated; `token_estimate` 1320 → 1600; `last_updated`
  2026-08-15.
- `specs/memory/architecture.md` — the "Context and SDD" subsystem gains two paragraphs. The
  `GitObjectReader` port's contract is widened: each object carries its own new content **and**
  the prior published text of the same path at the range's base, with absence as a distinct
  value that is never an empty string, so the decision layer cannot confuse "nothing published"
  with "nothing matched"; widening the port rather than giving the matcher a second input source
  is what keeps the decision function pure. The protocol module stays data-only and zero-I/O
  while the adapter owns every subprocess, chunks its conversation to a constant bound, and
  converts every parse failure into its own typed error. The second paragraph places
  `core/redaction.py` as the single stdlib-pure masking primitive with two consumers on
  opposite sides of the tree — `cli/redact.py`'s `--redact` surface and the gate's render
  boundary in `features/chokepoints/` — and states *why* it lives in `core`: `features` may
  import `core` and may never import `cli`, so shared placement is the only one that lets both
  render boundaries mask identically. `token_estimate` 1300 → 1430; `last_updated` 2026-08-15.
  `tldr`/`summary` unchanged — still accurate.
- `specs/memory/quality-assurance.md` — "Redaction At Authoring" records that by-hand masking is
  no longer the only branch: the gate's own render boundary masks the private-name-bearing
  segments of every blob path it prints, through the same primitive the `--redact` verbs use,
  while the by-hand rule still governs everything an agent transcribes into an authored
  document. "Satisfiable Diagnostics" records the amnesty's effect on clearability: a value the
  same path already published never refuses again, so editing a long-lived file is never a
  demand to rewrite already-published content and the discouraged bypass is never the only
  escape. The test-census sentence is corrected to the figures this release measured — ~2,253
  collected, 56 LARGE e2e-tier — and its duplicated wall-clock figure is dropped in favour of
  the single home in "Test Health", whose declared ratchet baselines are untouched. `token_estimate`
  1900 → 1980; `last_updated` 2026-08-15. **Note:** the census correction sits in a section
  SPEC §5 did not name. It is a correction of a *false* number this release measured, not a new
  fact — the atom said 55 LARGE and ~2,123 collected while the shipped tree carries 56 and
  2,253 — and it is recorded here rather than made silently. **Now trails by 8:** the review
  remediation took the suite to 2,261, so the atom's census sentence is owed a figure refresh at
  the re-close memory pass (the LARGE count is unaffected at 56). Recorded, not performed — this
  amendment writes no memory.
- `specs/memory/product/catalog.json` — the `sdd-gate-v3` entry's `tldr`, `summary` and
  `token_estimate` updated to match the atom's new frontmatter, per SPEC §5's condition. No slug
  was added, removed or re-ranked. **Owed to the dispatcher:** re-run
  `dadaia_workspace/public/scripts/generate-memory-catalog.py` to confirm a zero content diff
  and refresh `generated_at` — `product-engineer` has no shell, and a fabricated generation
  timestamp is worse than a stale one.
- `specs/memory/product/index.md` — **changed, where SPEC §5 predicted no change.** The catalog
  table renders each atom's `tldr`, so the changed one-liner propagates into the TOC row for
  `sdd-gate-v3`. A generated-consistency ripple, not a feature-catalog change: no feature was
  added, removed or re-ranked, and the vision, users, capability-map and limits sections are
  untouched. Same ripple v0.10.0 recorded; noted rather than left as an unexplained diff.
- `specs/memory/tech-stack.md` — **no change:** no dependency, command or language version
  moved. The one new module is stdlib-only.

## Dispositions

This release picked **nine backlog entries and no bug and no audit**. The bug ledger carried
**zero** open bugs at pick time — the two v0.9.0-window LOWs were closed by `hotfix/0.7.1`,
merged at `d15bdf4e`, the commit this branch was cut from — and both 2026-07 audits were
archived fully dispositioned by v0.8.0. The sweep is therefore complete with nine rows and no
bug row; nothing was silently dropped.

Purge-on-pick was executed in its **provenance form** at T-110-01, as SPEC §7 ratified: the nine
entry files were flipped to `status: picked` with a pick-provenance section rather than deleted,
because nine simultaneous deletions would have destroyed the index rows the #31 single-source
`BACKLOG.md` consolidation is being written against. Each file now carries its terminal token
and a `## Delivery (v0.11.0 closure)` section, and `specs/backlog/candidates.md` carries the
`## Ledger` block in the `dd-backlog-definition` §2 LEDGER line form. Nothing was deleted.

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/backlog/prior-published-term-amnesty.md` (#19) | backlog | `DELIVERED — v0.11.0` | FR1+FR2+FR3; A1.1–A1.6, A2.1–A2.6, A3.1–A3.6 verified (`ALPHA-1-QA.md`); V3/V4/V5/V6 |
| `specs/backlog/denylist-scan-skip-note-oversized-mislabel.md` (#20) | backlog | `DELIVERED — v0.11.0` | FR4; A4.1–A4.6 verified; V3/V4. Closes the v0.9.0 QA-1 return by test, not by manual check |
| `specs/backlog/registry-derived-foreign-name-set.md` (#22) | backlog | `DELIVERED — v0.11.0` | FR5; A5.1–A5.6 verified; V3/V5 + the V10 enumeration with all 6 hits dispositioned |
| `specs/backlog/refusal-path-redaction.md` (#23) | backlog | `DELIVERED — v0.11.0` | FR6 resolution A; A6.1–A6.6 verified; V3/V9 with `test_redact_output.py` assertions unmodified |
| `specs/backlog/push-ref-sha-validation-git-argv-hardening.md` (#25) | backlog | `DELIVERED — v0.11.0` | FR7; A7.1–A7.5 verified; V3/V4 |
| `specs/backlog/git-objects-batch-parse-typed-error-boundary.md` (#26) | backlog | `DELIVERED — v0.11.0` | FR8; A8.1–A8.4 verified; V3/V4 |
| `specs/backlog/git-objects-streamed-batch-reads.md` (#27) | backlog | `DELIVERED — v0.11.0` | FR9; A9.1–A9.3 verified; V4 + the T-110-05 peak-bound capture |
| `specs/backlog/closure-v14-perf-figure-correction.md` (#28) | backlog | `DELIVERED — v0.11.0` | Closure obligation; A9.4/A9.5 evidence in V11/V12, forward correction landed in `sdd-gate-v3.md`, match-throughput decision recorded as REJECTED with reason |
| `specs/backlog/self-scan-sentinel-integration-marker.md` (#29) | backlog | `DELIVERED — v0.11.0` | FR3(A3.5); V6/V7 — SENTINEL collected under `-m integration` |

Explicit non-flips, so a later reader does not read them as an incomplete sweep:

- `specs/backlog/baseline-carve-out-review-cadence.md` (#24) — **stays a candidate.** The D6
  `internal-hostname` structural fix was evaluated and **declined** for this release (SPEC §4.3):
  no picked intent binds `privacy_baseline.json`, and the 29-blocker census carries zero
  `internal-hostname` hits, so it does not fall inside any picked write set naturally. No
  baseline version bump happened; the baseline stays at version 4. #24 now owns that question
  alone.
- `specs/backlog/commit-message-scanning-residual.md` (#21) — untouched (SPEC §4.5). After
  v0.11.0 it is still the **only** unscanned channel on the push path: commit and tag-annotation
  bodies remain outside the scan.
- `specs/backlog/test-suite-remediation-stewardship.md` (#2) — untouched (SPEC §4.6). This
  release added **zero** e2e tests, so the LARGE census did not grow; it stays 56 against a
  declared cap of 30, and that overshoot stays owned here.
- `specs/backlog/bugs-jsonl-whole-blob-per-append.md` (idea) — untouched (SPEC §4.4). Named
  again by the V10 enumeration as the reason a bug-ledger line re-enters every future push
  range; FR1 now amnesties it, which removes the pain without removing the cost driver.
- `specs/backlog/python-env-interpreter-probe-hardening.md` (#9),
  `specs/backlog/commit-paths-index-scope-hardening.md` (#18) — untouched: same Arm-B hardening
  lane, different surface.
- **No bug status was flipped and no `dadaia bugs append` event was emitted by this release's
  scope.** Zero bugs were open at pick time and none was registered during implementation.

**Sweep-adjacent fidelity fix (not a disposition).** `candidates.md`'s "Pick-precedence notice"
still claimed two LOW bugs were outranking every backlog entry. They were closed by
`hotfix/0.7.1` at `d15bdf4e` and the ledger carries zero open bugs — the v0.11.0 SPEC §1 already
recorded the true state at pick time, so the notice was contradicting a document it sits beside.
Corrected in the same sweep, with the correction marked as such in the file. A precedence notice
that lies in the *conservative* direction is still a lie: it would have made the next pick
believe it was blocked behind work that no longer exists.

## Test dispositions

No demotion, no quarantine expiry and no SCAFFOLD expiry occurred. The full suite ran
**2253 passed, 3 skipped** at the alpha-1 QA run and **2261 passed, 3 skipped** after the review
remediation (V16); the e2e census is **56 collected, unchanged** in both — this release added
zero e2e tests, exactly as TASKS' standing rule required. Every added test declares its intent
and size at birth inside one of the seven pre-existing modules; `git diff --name-status` over
the release range shows **no added test module**, and the remediation added none either.

**Added-test count, reconciled.** The implementation added **58** tests (`code-reviewer` census
over `89a703b8..ff922566`); the review remediation added **9** more across `9648030a`,
`697548aa` and `517a62bd` — including the two M3 pinning tests named in the amended
`oversized-never-amnestied-scope-boundary` drift — for **67 added in the release**. The **3**
supersession rewrites are **unchanged at 3**: the remediation superseded nothing, and no test was
deleted, skipped, weakened or renamed away to accommodate a fix. One arithmetic seam is left
open rather than papered over: 2253 + 9 = 2262 against a measured 2261, an **8-test net gain for
9 added tests**. No artifact in hand explains the missing one — the reviewer's 58 and the
remediation's 9 are both self-reported counts, the 2261 is a measured run, and the closer has no
shell to reconcile them. It is flagged here for the dispatcher to resolve at the ship commit
rather than asserted away; a figure that does not add up is exactly what this release's #28
correction was about.

| Kind | Deleted/expired test | Replacement / disposition | Evidence |
|------|----------------------|----------------------------|----------|
| demotion | none | none — no LARGE test was replaced, removed or demoted; the LARGE census is unchanged at 56 | `ALPHA-1-QA.md` "Test stewardship checklist"; `pytest tests/e2e --collect-only -q` → 56 |
| quarantine expiry | none | none — no quarantine marker added, expired or restored | full-suite count 2253/3/0 (alpha-1 QA run), 2261/3/0 (post-remediation) |
| SCAFFOLD expiry | none | none — every touched module carries an updated `Intent: CONTRACT — v0.9.0 <ids>; v0.11.0 <ids>` line at birth | QA direct grep of every changed test file |
| supersession rewrite (1/3) | `test_editing_the_same_content_produces_a_new_blob_and_a_refusal` (`tests/integration/test_push_gate_denylist.py`) | → `test_editing_a_path_that_already_published_the_value_no_longer_refuses` — the v0.9.0 test asserted the edit **refuses**; the v0.11.0 test asserts it is **allowed**. The superseded assumption is the release's own blocking problem | QA diff verification; docstring names the superseded test and cites SPEC §4.2 |
| supersession rewrite (2/3) | `test_new_objects_marks_oversized_blob_undecodable_and_never_fetches_its_content` (`tests/unit/infrastructure/test_git_object_reader.py`) | → `test_new_objects_scans_the_first_cap_bytes_of_an_oversized_text_blob` — `decodable is False` / `text == ""` becomes `decodable is True` / `oversized is True` / decoded prefix, **plus** a new byte-count assertion (A4.2) the old test did not have | QA diff verification; FR4's honesty fix |
| supersession rewrite (3/3) | `test_this_repos_own_tracked_tree_scans_clean` (`tests/integration/test_repo_self_scan.py`) | → split into `test_no_hit_outside_the_shrink_only_baseline` + `test_every_baseline_row_still_produces_a_hit` — one assertion cannot express both directions of a shrink-only baseline | QA diff verification (A3.3/A3.4) |

**Nothing was pruned, skipped or disabled to reach green.** All three rewrites are disclosed in
their own docstrings, cite the SPEC entry or ADR authorising the behaviour change, and replace
each removed assertion with one proving the new, SPEC-mandated behaviour — the shape a
superseded assumption is supposed to take. No `qa-engineer` deletion verdict was required
because nothing was deleted. QA re-ran the suite itself and its count matches the implementer's,
which is what makes that claim checkable rather than asserted.

## Intake candidates

Residuals discovered during this release, **listed** for the PM's operator-facing intake report
(ADR #15). This closure creates **no** backlog entry and flips no backlog status outside the
nine picked entries of its own sweep.

### To be adjudicated

No prior operator ruling covers these; the PM's next intake report presents each for approval,
rejection or discard.

- **LOW — the `home-abs-path` baseline pattern covers one operating system's home layout.**
  Raised by `security-reviewer` at the milestone-(a) definition-push review
  (`2026-08-15T173153Z`). The packaged structural baseline's absolute-home-path pattern matches
  the Linux `/home/<user>` shape only; the macOS `/Users/<user>` shape, the Windows
  `C:\Users\<user>` shape and the root-account `/root` shape fall outside **every** structural
  pattern in the baseline. On those platforms the layer that is supposed to catch an operator's
  local path in a pushed blob simply does not fire, and the product declares cross-platform
  support for all three. Not fixed here: no picked entry binds `privacy_baseline.json`, and a
  baseline version bump was explicitly out of scope (SPEC §4.3, D6 declined). Adjacent to #24
  (`baseline-carve-out-review-cadence`), which owns the *carve-out* half of the same file — the
  PM should decide whether this merges into #24 or stands as its own coverage entry, since it is
  a **missing pattern**, not a carve-out review.
- **Match-throughput optimisation for the fallback range shape.** Measured at T-110-14 and
  **rejected for this release** with the three-point reason recorded above and in the capture.
  It remains a real, measured cost — 53.9 s of a 55.1 s fallback scan, ~98% — and the shape that
  pays it is exactly the one a fresh clone or a bare CI checkout hits. Listed so the rejection is
  a decision with a paper trail rather than an omission: if the operator ever wants it, the entry
  should carry the correctness-parity requirement across every existing baseline-pattern test as
  its first acceptance criterion.
- **Memory-wording refinements owed by the review round (two, both small, neither performed
  here).** (a) `sdd-gate-v3.md` states the suppression rule as "iff the exact matched value
  occurs, case-insensitively, in that prior text"; after M1's fix the predicate is stricter than
  that for the pattern and slug layers — it requires the value to occur **as a value that layer's
  own anchored matcher finds** — while operator terms keep substring semantics on both sides. The
  sentence is still true as a necessary condition, so nothing in the atom is false; the
  refinement makes it exact. (b) The atom carries no sentence stating that an oversized *current*
  object is never amnestied — the boundary is now test-pinned twice but memory-silent, and
  whether it belongs in the atom is a memory decision. Both are listed because a memory edit is
  not a thing a closure amendment does on its own initiative.
- **The pre-PR code review runs *after* the archive step, so a finding against the closure can
  only be answered by resetting the archive commit.** T-110-17 archives; T-110-18's first step
  reviews. Second occurrence of the resulting reopen (v0.9.0 was the first), and the cost is
  paid in reset commits and lost task markers each time. The candidate is a TASKS-template
  ordering change — six-axis review of the delta **before** the `git mv`, with only the ship
  steps after it — which no picked entry in this release authorised and which the closer cannot
  make from inside the release it would govern.
- **INFO — `token_estimate` frontmatter drift across the memory atoms.** Raised by
  `code-reviewer` at V15 as **pre-existing**: `dadaia specs doctor` warns on all three atoms this
  release touched, and the class spans ~12 atoms workspace-wide; the drift existed at the base
  commit and this release moved the declared values in the right direction without creating or
  closing it. Listed as a standing memory-hygiene item for `product-engineer`, not as v0.11.0
  rework. It is the bulk of V15's 16 doctor warnings.

Two smaller observations are recorded **inside their drift sections rather than listed here**,
because neither is actionable work: the `specs/backlog/_archive/` prefix question raised by the
V10 enumeration (whether that archive root should join the sentinel's excluded prefixes —
narrower than FR5's scope and answered by FR1 in practice), and the flat-release ship-task
marker gap, which already has a standing idea entry and whose fourth occurrence is noted in
`## Tasks completed` rather than duplicated.

### Pre-approved intake

**None.** No operator-ratified deferral was taken during this release: every scope decision was
settled at approval (D1–D8, SPEC §8) and every named non-goal points at an entry that already
exists in the backlog.

## Version bump decision

**Decision: bump `pyproject.toml` `0.7.1` → `0.8.0` (minor) and add the `[0.8.0]`
`CHANGELOG.md` entry in the same commit.** Recorded here as **owed**; the dispatcher executes
both, since `product-engineer` has no shell. This is ADR D5, ratified with the SPEC.

1. **Behavioural change for every consumer, backward-compatible.** The push gate ships inside
   the wheel and every consumer workspace installs it; a wheel built from this tree refuses and
   allows differently than the previous one — an already-published value in the same path stops
   refusing, an oversized text blob starts refusing, a DEAD context's name starts protecting.
   Added and corrected behaviour with nothing removed and nothing broken is a minor under the
   package's `0.x` scheme.
2. **Not a patch, because this is not a hotfix.** Law §5 binds PATCH-with-CHANGELOG to a hotfix
   merge; `0.7.1` was exactly that. This is a feature release closing at milestone (b), and
   minting another PATCH would misfile nine consumed backlog entries as a fix.
3. **The two version axes stay distinct.** `v0.11.0` is the SDD release identity; `0.8.0` is the
   package version (ADR-2). Neither is renumbered to chase the other; the precedent chain is
   v0.9.0→0.6.0, v0.10.0→0.7.0.

The `[0.8.0]` entry should name the amnesty and its path-bound semantics (a consumer whose push
stops refusing needs to know why), the oversized-blob honesty fix, the registry-derived name
layer, the path masking, and the three hardening fixes. The pre-existing CHANGELOG version-axis
incoherence is tracked as a live backlog entry and is **not** re-raised here: write the entry in
the file's current shape.

**One correction is owed in that same entry — `code-reviewer` LOW6 (V15).** The drafted `[0.8.0]`
text describes the oversized fix as shipping "split counters (`skipped_oversized` vs
`skipped_binary`)". **Neither identifier exists in the shipped code**: those names come from the
backlog entry's proposal, and the implementation carries `ScanOutcome.skipped_binary_count` plus
a structured `oversized_notes` tuple of records bearing path, total size and scanned bytes — the
better shape, chosen at grill P13. Reword to *"a separate binary skip count plus structured
oversized notes carrying path, total size and scanned bytes"* before the bump commit. A
consumer-facing document naming an API surface that does not exist is the same defect class this
release was picked to fix, one file over. `CHANGELOG.md` sits outside `_archive/` and is written
at the bump commit, so this is a ship-time edit, not a reopen.

## Archive decision

**MOVE** — `specs/releases/v0.11.0/` moves to `specs/_archive/releases/v0.11.0/` via `git mv`,
executed by the dispatcher, in the same commit that carries this file. `ACTIVE.md` is set to
`release: none` / `phase: none`: no release follows immediately, and the next pick is the PM's.
At that pick the queue is bugs-and-audits-first by law — **zero** open bugs, zero
undispositioned audits — so fresh backlog leads, with this closure's two intake candidates due
for adjudication before they can be picked.

Two properties of the move are worth stating because this release is the one that made them
matter. First, `git mv` creates no new blob, so every file moving into `_archive/` is invisible
to the push scan by the FROZEN↔rename invariant this release left untouched and re-verified.
Second, **this document is not covered by that invariant**: it is authored into the archive
directory, so it is an ordinary new blob and the gate reads it like any other. It was written
under the redaction-at-authoring doctrine — every path cited is workspace-relative, and no
foreign Spec Context name, repo slug, hostname, IP address, email or absolute local path was
transcribed into it, including from the capture files it quotes. A closure that leaked a
literal would refuse its own push, which is the most direct self-proof this release could ask
for.

After the move, nothing under `specs/_archive/` is edited again — including T-110-18's `[ ]`
marker, which archives open by design.

**Second attempt, and the reason there is one.** The first archive commit `ff922566` was reset
after the pre-PR review (see `## Drifts › reopened-close-for-review-remediation`), so this `git
mv` is executed again, on this amended document, at the re-close commit. The invariant above is
what forced the reopen rather than an in-place fix: once this file is under `_archive/` it is
FROZEN, and a MEDIUM finding against its own text has no legal repair path except reopening the
close. That is the correct trade — an archive that cannot be quietly rewritten is worth more than
the cost of one reset. It also names the ordering that produced it: T-110-17 archives and
T-110-18 reviews, so the six-axis pass reads a closure that is **already FROZEN**, and any
finding against the closure text can only be answered by resetting the archive commit. Fourth
release on this shape, second reopen (v0.9.0 was the first). The fix is not this document's to
make — moving the pre-PR review ahead of the archive step is a TASKS-template change — but the
recurrence is recorded here so the next definition can order it correctly.
