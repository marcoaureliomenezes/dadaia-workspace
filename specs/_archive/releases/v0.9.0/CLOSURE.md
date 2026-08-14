# Closure: Release — v0.9.0 — Push-range denylist scan

**Status:** Aprovado
**Release ID:** v0.9.0
**Owner:** product-engineer
**Closed:** 2026-08-14
**Branch:** `feature/v0.9.0` (cut from `develop` at `1883b85b`; branch contract: `dadaia-gitflow`)
**Source SPEC:** `specs/releases/v0.9.0/SPEC.md` · **Source PLAN:** `specs/releases/v0.9.0/PLAN.md`
**QA close of the flat increment:** `specs/releases/v0.9.0/ALPHA-1-QA.md` (APPROVED, 36/36 acceptance ids)
**Close history:** first closed 2026-08-14 at `946272e4` (since retired from the branch);
**reopened** the same day by the
`code-reviewer` pre-PR verdict (REQUEST-CHANGES); remediated at `3c3c6d4a` and re-closed
against this amended document — see `## Drifts › code-review-round-refused-own-close`.
**Review round evidence:** `.dadaia/handoff/dadaia-workspace/2026-08-14T200852Z-code-reviewer-v0.9.0-prepr.handoff.json`
(REJECTED / REQUEST-CHANGES) · `.dadaia/handoff/dadaia-workspace/2026-08-14T215726Z-software-engineer-v0.9.0-code-review-remediation.handoff.json`
(remediation, APPROVED)

---

## Summary

v0.9.0 closes the leak channel that produced the same incident in two consecutive releases.
In v0.6.0 a SPEC named a consumer project and in v0.7.0 a QA artifact transcribed a foreign
presence record; both left through a push that nothing mechanical inspected, and both were
caught only by a human security diff review after the fact. The push gate now inspects
**content**, not only refs: for every non-deletion ref a push would publish — branch or tag —
the new objects of the pushed range are scanned against three additive term layers (the
operator-private denylist, the packaged structural baseline, and the foreign `repos/` slugs
minus the pushed repository's own) before any network I/O. A match refuses the push with a
masked, satisfiable diagnostic that names the ref, the blob path and line, the source layer,
and the one action that clears it — edit and rewrite the offending commits *before* the push.
Because the scope is the objects the push would publish, a rewrite of already-published
history is never demanded, and no amnesty list exists anywhere in the product.

The same release closes the *entry* path both incidents actually used. `dadaia doctor`,
`dadaia context list` and `dadaia context show` gained an opt-in `--redact` output mode that
replaces every Spec Context name and repo slug other than the caller's own with a stable
`[REDACTED-CONTEXT-<n>]` placeholder, applied at the render boundary only so default output
stays byte-for-byte unchanged and the `--json` form stays valid JSON with the same key set.
The `qa-engineer` canonical persona now carries the matching doctrine: diagnostic output
transcribed into any authored document is captured with `--redact` or masked by hand, and a
foreign context name is never pasted verbatim. The QA review that closed this increment is
itself the first artifact authored under that doctrine.

The gate proved itself against its own author. Its first real-world run — over this very
release's push range — **refused**, with 7 masked hits: five fixture git-identity email
addresses, one positive-fixture IPv4 literal inside the matcher's own test, and one genuine
baseline false positive on RFC-2606 reserved-TLD synthetic identities. All three causes were
fixed at the root (a baseline v2 carve-out written RED-first, fixture hygiene, positive
fixtures rebuilt by concatenation), and the range was scan-clean at that remediation commit
`42b59cd8`, independently reproduced by QA. Nothing had been published at that point, so the
branch-local history was rewritten to leave no matching literal in any object the push would
carry — the exact remediation the refusal's own message prescribes.

It then refused its author a second time. The six-axis pre-PR review ran the shipped scanner
over the *close tip* and returned **REQUEST-CHANGES**: the three commits that followed
`42b59cd8` — the memory update, and the close itself — had reintroduced 3 hits, two of them
structural (the packaging author email that every release bumps past, and the product's own
synthetic git identity quoted in `architecture.md`, which a closure edits every cycle). The
close was **reopened**. The operator ratified three decisions — whole-blob matching is kept,
with a prior-published-term amnesty refinement routed to the backlog rather than built here;
the packaging author email moves to the GitHub noreply form; the product's own synthetic
`workspace.local` identity gets a specific, narrow baseline carve-out — and the remediation
landed at `3c3c6d4a`: batched git object reads (~16× faster), the carve-outs written
RED-first, a fail-closed adapter path with a 5 MB per-blob cap, a matcher short-circuit, and
the one test that would have caught all of this the first time — a self-scan regression guard
over the repository's own tracked content. That guard immediately earned itself by surfacing
two further real false positives, both fixed at the root. 2192 tests pass, 3 skip at the
remediated tip; import-linter keeps 9/9 contracts, including the purity contracts that force
git object I/O through an injected port rather than a subprocess inside the decision module.

## Tasks completed

Commit note, load-bearing for anyone re-resolving these SHAs: the branch's local-only history
was rewritten mid-release (see `## Drifts › first-real-refusal-was-this-releases-own-range`).
The SHAs below are **post-rewrite branch order**, except T-090-01, whose definition commit is
recorded at its **pre-rewrite** sha `7f3185fc` — it was already published through the
milestone-(a) merge `8680beeb`. Paired SHAs are `reserve / final`: the
`chore(tasks): start <id>` reservation commit, then the commit carrying the work and the
`[-]` → `[x]` flip, per `dadaia-task-manager`.

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-090-01 | [git] Commit the definition content on `feature/v0.9.0` (trio + `ACTIVE.md` → IMPLEMENTATION; the PM's purge-on-pick of the two consumed entries rode this commit) | `7f3185fc` (pre-rewrite) |
| T-090-02 | [git] Milestone (a): merge into `develop`, diff-based security review, push | merge `8680beeb` (pushed, CI green); marker flip `0ebae832` |
| T-090-03 | Git object port and adapter (`GitObjectReader`, `ScannedObject`, `infrastructure/git_objects.py`) | `d1ae1dd2` / `81f527c4` |
| T-090-04 | Pure denylist matcher (`features/chokepoints/denylist_scan.py`, masking inside the matcher) | `205a6687` / `5e572862` |
| T-090-05 | Wire the scan into `push_gate_decision` (scan ref set independent of `review_refs`; policy order) | `f17bcb0b` / `771b91a8` |
| T-090-06 | CLI wiring in `ci.py push_gate_check` + fail-closed boundary + stderr mode line | `97f20d43` / `b7ccb8d1` |
| T-090-07 | `--redact` output mode for `doctor` / `context list` / `context show` (FR8a) | `5f53b79b` / `ccd7672b` |
| T-090-08 | Redaction doctrine in `public/agents/qa-engineer.md` + re-projection (FR8b) | `acd06be8` / `a7b1f883` |
| T-090-09 | E2E planted-term journey + FR7 timing measurement | `d8a4892a` / `c5ae8fc1` |
| — | Remediation of the gate's first live refusal (baseline v2 RFC-2606 carve-out, fixture hygiene, positive-fixture concatenation) — not a TASKS entry; root-cause fix inside T-090-09's window | `42b59cd8` |
| T-090-10 | `qa-engineer` review of the increment (flat alpha-close) — **APPROVED**, 36/36 acceptance ids | `0491613a` (reserve) / `ac805c67` (housekeeping) / `38d2120b` (artifact + flip) |
| T-090-11 | Memory update in CLOSURE phase — five atoms + catalog regeneration | `eeb1195c` / `b6272772` |
| T-090-12 | CLOSURE, dispositions, release archive, version bump | reserve `83398138`; first close attempt `946272e4`, **retired** when the code review reopened it (`## Drifts › code-review-round-refused-own-close`); final `docs(T-090-12): close release v0.9.0` (sha assigned by the dispatcher at commit time) |
| — | Code-review remediation: batched `cat-file --batch` object reads + generator streaming + 5 MB blob cap + typed batch-check errors, three baseline carve-outs (`workspace.local` in two patterns, `Path.home` in one), matcher short-circuit + case-insensitive foreign slugs, unified `ZERO_SHA`, and the self-scan regression guard — not a TASKS entry; root-cause fix inside T-090-12's **reopened** window | `3c3c6d4a` |
| — | Bug registration `mypy-strict-cache-dir-created-without-cache-dir-env-override` (LOW) — ADDITIVE `specs/bugs/` write made during the remediation window; not release scope and not a task | `d869c7dc` |
| T-090-13 | [git] Milestone (b): ship — code review, merge, security review, push, PR `develop` → `main` | the pre-PR code review ran **before** this closure and reopened it (`## Drifts`); the remaining ship steps execute after it. Archives `[ ]` by design — see `## Drifts › ship-task-archives-open` |

## Validations

V1–V12 are the PLAN §5 validation plan, one row each. V13–V14 are added by the reopened close
and carry the post-code-review re-measurement — they are not PLAN rows and are labelled so a
reader does not mistake them for planned validations. Evidence is a test id verified by
`qa-engineer` in `ALPHA-1-QA.md`, a commit sha, a captured stdout figure, or a handoff path.
Where a figure moved between the QA close and the remediated tip `3c3c6d4a`, **both** are
kept and the standing one is named.

| Description | Command | Evidence |
|-------------|---------|----------|
| V1 — Range scope (A1.1–A1.4): term in range refuses; term reachable only from `remote_sha` does not; deletion is never scanned; blobs deduped by object sha | `pytest tests/unit/features/chokepoints/test_push_denylist_scan.py tests/unit/infrastructure/test_git_object_reader.py` | `ALPHA-1-QA.md` §FR1 — 4 named tests re-run PASS (`test_branch_push_with_denylisted_blob_in_range_is_refused`, `test_term_outside_the_range_does_not_refuse`, `test_deletion_ref_is_never_scanned` asserting `source.calls == []`, `test_shared_blob_across_two_refs_is_deduped`); both FR1 range forms additionally covered against real `tmp_path` git repos at the adapter |
| V2 — Tag coverage with the security-verdict carve-out intact (A2.1–A2.4) | `pytest tests/unit/features/chokepoints/test_push_denylist_scan.py` | `ALPHA-1-QA.md` §FR2 — tainted tag refused; clean tag allowed **with no handoff present anywhere** (DP-5 carve-out preserved); branch deletion unchanged; `test_branch_policy_refusal_precedes_the_scan` uses a `_FailingObjectSource` that would raise if policy order ever inverted |
| V3 — Term sources, self-slug exclusion, mode line (A3.1–A3.5) | `pytest tests/unit/features/chokepoints/test_denylist_scan.py tests/contract/test_push_gate_wiring.py` | `ALPHA-1-QA.md` §FR3 — baseline layer alone refuses an IPv4 literal and a home path with zero operator terms; own slug never enters the `slugs` tuple; word-boundary slug matching proven both ways; `exclude_regex` carve-outs honored. Live: `push-gate-check` over the real range printed `[pre-push] denylist scan mode: operator denylist + baseline` on stderr |
| V4 — No amnesty list; FROZEN↔scan invariant mechanical (A4.1–A4.2) | `pytest tests/integration/test_push_gate_denylist.py`; allowlist-constant grep contract test | `ALPHA-1-QA.md` §FR4 — `test_no_allowlist_or_sanctioned_terms_constant_in_matcher_source` PASS, QA independently re-grepped `features/chokepoints/**` with no match; `test_git_mv_into_archive_produces_no_new_blob_and_a_clean_scan` (clean) contrasted with `test_editing_the_same_content_produces_a_new_blob_and_a_refusal` (refused), both on a real git repo |
| V5 — Satisfiable, non-leaking diagnostic (A5.1–A5.4) | `pytest -k test_refusal_message_shape_and_ten_item_cap`; plus the live capture below | `ALPHA-1-QA.md` §FR5 — message carries ref, `path:line`, short blob sha, masked term and source layer; asserts `--amend`/rebase and "already-published history never needs a rewrite"; 12 synthetic hits render 10 + `"2 more"`. **Live shape proof:** the gate's own first run over this branch refused with **7 hits, every term masked** — e.g. `t…m` (email-address) and `1…5` (ipv4-literal) — no term echoed unmasked and no matched line content printed |
| V6 — Fail-closed / fail-open boundary (A6.1–A6.3) | `pytest tests/unit/features/chokepoints tests/integration/test_push_gate_denylist.py tests/contract/test_push_gate_wiring.py` | `ALPHA-1-QA.md` §FR6 — git failure refuses naming the failure and `--no-verify` (unit + real non-repo integration); undecodable blob skipped and counted (`skipped_binary_count == 1`, adapter marks `decodable=False` without raising); `test_push_gate_check_always_wires_a_real_object_source` spy asserts the source was actually called. **Finding QA-1 (LOW)**: no end-to-end test of the skip-count note at the CLI output layer — behavior manually verified correct, gap routed to the backlog |
| V7 — Architectural purity and the < 2 s budget (A7.1–A7.3) | `lint-imports`; `mypy --strict dadaia_workspace/`; scan timing over this release's own range | **Purity:** import-linter **9 contracts kept, 0 broken**, including *features must not import infrastructure directly* and *features must not import subprocess directly*; `mypy --strict` clean over **265 files**; the object source is a required keyword parameter, so an unwired call site is a type error. Re-verified at the remediated tip `3c3c6d4a`: `mypy --strict` PASS, `lint-imports` 9/9. **Timing (first measurement, superseded):** **real 0.760 s** (budget 2 s) over a 62-blob `origin/develop..HEAD` via `printf '<pre-push stdin line>' \| python -m dadaia_workspace.cli.main ci push-gate-check` with `WORKSPACE_ROOT` set — measured at the **intermediate** sha of T-090-09, not at the close tip; capture `.dadaia/tmp/software-engineer/20260814/T-090-09-timing-A7.3.txt`, handoff `2026-08-14T19:09:16Z-software-engineer-T-090-09-push-denylist-journey.handoff.json`. **Timing (current, A7.3 partially missed — see V14):** the code review showed the budget was validated only on the 62-blob happy path, while the FR1 `--not --remotes` fallback shape cost **~48 s** (16.1 s read + 31.6 s match, ~129 MB resident) over 8852 blobs. After batching at `3c3c6d4a` the same synthetic 8852-blob benchmark runs **2.978 s** total (0.415 s read + 2.562 s match) — **~16×** faster, per-blob subprocess spawning eliminated. The real range at the remediated tip (**247 objects / 66 blobs**) runs **~2.7–3.4 s** wall clock: **over** the A7.3 2 s budget, dominated by one ~900 KB `specs/bugs/bugs.jsonl` blob appended twice inside this local range (whole-file blob per append), not by the scan mechanism. Recorded as missed, not rounded down; mitigation routed to `## Backlog returns` |
| V8 — Redaction, all three verbs, table and JSON (A8.1–A8.5) | `pytest tests/unit/cli/test_redact_output.py tests/contract/test_cli_output_stability.py`; `dadaia public doctor` | `ALPHA-1-QA.md` §FR8 — 16/16 unit + 5/5 contract PASS; default output pinned byte-for-byte across doctor/context-list/context-show × table/json; ordinal-by-first-appearance stability and JSON key-set preservation proven; `dadaia public doctor` reports `[ok] public-privacy`; the doctrine line is present in `dadaia_workspace/public/agents/qa-engineer.md` and in every projection. Live `--redact` run masked every foreign context in the real registry with no name unmasked |
| V9 — End-to-end journey (A9.1) | `pytest tests/e2e/test_push_denylist_journey.py` | `test_planted_term_refused_then_clean_push_after_amend` — real `.git/hooks/pre-push` boundary on a throwaway repo: planted synthetic term refused, term removed and commit amended, clean push after a matching security verdict. Green in the full suite |
| V10 — Suite green before each push (A9.2) | `dadaia ci preflight`; `pytest -p no:cacheprovider -q`; `pytest -q -p no:cacheprovider -m "not quarantine" -n auto` | At the QA close: **2185 passed, 3 skipped** — twice, once directly (105.16 s) and once under preflight's exact `-n auto` invocation (75.76 s), matching the implementer's baseline exactly. **At the remediated tip `3c3c6d4a` (the figure that stands): 2192 passed, 3 skipped, 0 failed** (455.41 s), +7 tests from the code-review remediation. `ruff format --check` and `ruff check` clean; `mypy --strict` clean; `lint-imports` **9/9**; `dadaia ci preflight --quick` **PASS** — all four re-run at `3c3c6d4a`, not carried over from the earlier tip. Two transient/tooling defects met during these runs are registered as bugs, not carried as release defects (Findings QA-2 and the mypy cache-dir bug — see `## Backlog returns`) |
| V11 — Test intents declared at birth (A9.3) | grep of each new test module's first 20 lines; `git diff origin/develop..HEAD -- tests/` | All 8 new test modules declare `Intent: CONTRACT — v0.9.0 <A-id list>`; the 3 pre-existing modules touched received fixture repairs only, with **zero** added or removed `def test_` lines; zero `skip`/`xfail`/`quarantine` additions anywhere in the diff — all measured at the QA-close tip. **At the remediated tip** the code-review round added **7 more tests**: a **9th** module, `tests/integration/test_repo_self_scan.py`, declared `Intent: SENTINEL` at birth (a standing guard over the product's own content, not an acceptance-id contract), plus new cases inside the matcher and adapter unit modules this release already owns — so the "zero `def test_` lines added to pre-existing modules" statement above is true of the QA-close tip and **not** of the final tip, by design. The declaration rule holds for all of them, and the diff still carries zero `skip`/`xfail`/`quarantine` additions |
| V12 — Memory stays atomic (SPEC §5) | `dadaia specs doctor`; catalog regeneration via `public/scripts/generate-memory-catalog.py` | Five atoms updated and `catalog.json` regenerated at `b6272772`; no `Changelog`/`History`/`Versions` section added to any atom; every SPEC §5 row satisfied file by file (see `## Memory updates`). One doctor-flagged schema-length violation on the `sdd-gate-v3` `tldr` was trimmed before the commit closed — recorded as a drift, not hidden |
| V13 — **Post-review**: the gate's own pushable range scans clean at the remediated tip, and the result is pinned by a test rather than by prose | `dadaia ci push-gate-check` read-only over the real `origin/develop..HEAD`; `pytest tests/integration/test_repo_self_scan.py` | **0 hits over 247 objects / 66 blobs** at `3c3c6d4a` (3 hits at the reviewed tip `946272e4`). The claim is now enforced by `tests/integration/test_repo_self_scan.py`, which runs the real baseline over `dadaia_workspace/` + `specs/` (excluding both `_archive/` trees) + `pyproject.toml` — ~513 files — and asserts zero hits; it runs with a deterministic **empty** foreign-slug set by design, documented in the module docstring, because resolving `repos/` live would make the suite's verdict depend on which sibling repos happen to be checked out. Its first run found **46** hits, not 0 — reproducing the reviewer's wider-probe finding — and the triage is recorded in `## Drifts › self-scan-guard-surfaced-two-more-baseline-false-positives` |
| V14 — A7.3 `< 2 s` budget re-measured after batching — **residual miss**, disposed rather than rounded | timed `ci push-gate-check` over the real range; synthetic 8852-blob benchmark | Synthetic fallback-shape range: **2.978 s** (was ~48 s). Real range at `3c3c6d4a`: **~2.7–3.4 s**, i.e. **over** the 2 s budget A7.3 states for a typical range. Cause is data, not mechanism — a ~900 KB `specs/bugs/bugs.jsonl` blob published twice in the local range. **A7.3 is therefore recorded as partially missed at close**, with the mitigation routed to `## Backlog returns`; no acceptance id was re-interpreted to make it pass |

## Drifts

### first-real-refusal-was-this-releases-own-range

**Description:** 2026-08-14. The gate this release built refused its author. Its first
real-world run — the scan over v0.9.0's own push range — **BLOCKED with 7 hits**: five
fixture git-identity email addresses (`t…m` / `t…t` style values used to construct
throwaway repos in tests — transcribed here in the gate's **own masked form**, because the
first version of this paragraph transcribed them literally and was itself one of the review
round's refusal hits; see `## Drifts › code-review-round-refused-own-close`), one IPv4
literal living inside a *positive* fixture of the
matcher's own test (a string that must match, by design), and one genuine baseline **false
positive**: RFC-2606 reserved-TLD synthetic identities in `container.py` were matched by the
email pattern, even though a `.invalid` address is synthetic by definition and belongs to the
same carve-out family as the pre-existing `example.com` and RFC-5737 exclusions. Every hit
was reported masked (`t…m`, `1…5`), so the refusal did not leak what it was protecting — FR5
proved live, on the worst possible day for it to be wrong.

**Resolution:** Fixed at the root, in three distinct moves, none of them a suppression:
(i) `privacy_baseline.json` v1 → v2 gains a reserved-TLD email carve-out, written RED-first —
`test_baseline_excludes_rfc2606_reserved_tld_emails` was confirmed failing before the JSON
change and passing after; (ii) test fixtures were hygienized onto `example.com`; (iii) the
positive fixtures that must contain a matchable literal were rebuilt by runtime concatenation
(`"198.18" + ".0.5"`, `"/hom" + "e/alice"`), so the assembled value still exercises the real
compiled baseline regex — QA verified the assertions genuinely produce one hit — while no
tracked file carries a matchable literal. **No amnesty entry was added**, and none exists
(A4.1 re-verified). The branch's local-only history was then rewritten (filter-branch with an
idempotent scrubber) so that no object the push would publish carries a matching literal.
That rewrite is exactly the remediation the refusal's own message prescribes — edit, then
rewrite the offending commits *before* the push — and it was legitimate precisely because
nothing in the rewritten range had been published; already-published history was never
touched, which is the property the range scope exists to guarantee. Cost: the branch SHAs
changed mid-release, which is why `## Tasks completed` carries an explicit pre/post-rewrite
note.

**Correction (2026-08-14, second round).** This drift originally claimed *"post-remediation
the denylist scan over the range is clean"* without qualification. That claim was **true at
`42b59cd8`**, where it was measured and where QA independently reproduced it, and **false at
the tip it was written on**. Three commits later the range carried 3 hits again:
`b6272772` (the T-090-11 memory update) republished `specs/memory/architecture.md`, whose
line 83 quotes the product's own synthetic git commit identity on the `workspace.local` host;
and the close commit `946272e4` both authored this very file — with the fixture emails
transcribed literally, now masked above — and bumped `pyproject.toml`, whose line 5 carries
the packaging author email. Evidence measured at an intermediate sha was presented as
evidence at the tip. The claim now reads with its sha, and the clean result at the *actual*
close tip is a separate row (V13) pinned by a test rather than by prose. The full second-round
chronology is the next drift.

**Memory updates:** `specs/memory/product/sdd/sdd-gate-v3.md` — the baseline layer is
described with its current version and carve-out set, so the atom describes the matcher as it
now is (the version moved again in the second round — see the next drift).

### code-review-round-refused-own-close

**Description:** 2026-08-14, second round. The six-axis pre-PR review (`code-reviewer`, over
`8680beeb..946272e4`, 24 commits / 41 files) returned **REQUEST-CHANGES** — 1 CRITICAL,
2 HIGH, 3 MEDIUM, 6 LOW, 4 INFO. The CRITICAL is the same class as this release's headline
drift, recurring one commit after its remediation: the reviewer ran the **shipped scanner**
read-only over the exact range the pre-push hook computes for the close tip, and it refused
with **3 hits** — `pyproject.toml:5` (the packaging author email), this file at line 103 (the
fixture emails transcribed literally into the drift narrative, now masked), and
`specs/memory/architecture.md:83` (the product's own synthetic git commit identity on the
`workspace.local` host). Two of the three are **structural**, not incidental: law §5 bumps
`pyproject.toml` on every release and hotfix, and `architecture.md` is edited at essentially
every closure — so the refusal would recur every cycle with no sanctioned escape but
`git push --no-verify`, i.e. the feature's first production use would train the bypass it
names as discouraged. A wider probe over the 1498 tracked text files found **50** latent
blockers of the same shape. The two HIGHs were the false clean-scan claim (previous drift)
and the FROZEN↔scan invariant recorded in memory, which reasons only about `git mv` renames
and therefore over-claims for documents authored directly inside `_archive/` — one of which
was a live hit in that very range.

**Resolution:** the close was **reopened** — the archive move was undone, the release
directory is live again under `specs/releases/`, and this document was **rewritten** rather
than patched after the fact (the reviewed close commit `946272e4` is consequently retired from
the branch; it is cited here as the sha the review measured, not as a reachable ancestor).
The operator ratified three decisions before any code moved:

1. **Whole-blob matching is KEPT**, not narrowed to the lines the range adds. The structural
   tension it creates is real and is routed to the backlog as `prior-published-term-amnesty`
   (a term already published in the remote-reachable version of the *same path* should not
   refuse) rather than resolved by widening the ruler under close pressure.
2. **The packaging author email moves to the GitHub `users.noreply.github.com` form** — the
   root fix rather than a carve-out, and already covered by a pre-existing baseline exclude.
   The metadata change rides this release (see `## Version bump decision`).
3. **A specific carve-out for the product's own synthetic `workspace.local` identity** — the
   exact literal only, in both the `internal-hostname` pattern and as an email domain. It is
   the product's own fixture host, not an operator's network; every other `.local` host and
   every other subdomain of it still matches, proven by still-flagged fixtures.

Remediation landed as the single commit `3c3c6d4a`, every behavioral fix written RED-first,
with the MEDIUMs and the actionable LOWs absorbed in the same pass: git object contents are
now read through **one** `cat-file --batch` conversation instead of one subprocess per blob
and streamed as a generator into the matcher; a **5 MB per-blob cap** excludes an oversized
blob *before* its content is ever fetched; the `--batch-check` call was routed through the
module's `_run` wrapper so a timeout or missing git surfaces as the typed `GitObjectReadError`
the port promises instead of an unhandled traceback at the push boundary; the matcher
short-circuits at the first hit line instead of scanning the whole blob and sorting; foreign
slugs now match case-insensitively; the duplicated comment block was deleted and the private
`_ZERO_SHA` replaced by the shared port constant. The self-scan regression test the reviewer
asked for was added and is the subject of the next drift. Post-remediation the release was
re-validated end to end (V10, V13, V14) and the close re-executed against this amended
document.

Two process costs are recorded rather than smoothed over. First, the remediation itself was
refused by its own gate mid-session: the new positive fixtures were first committed as
contiguous literals, a new blob in the pushed range; the fix was then combined into one
commit with `git reset --soft` (local, unpublished, no history rewrite of anything published)
because `rev-list --objects` walks every commit of the range, so an intermediate bad blob
stays a new object of that range until the commits are combined. Second, the reviewer's LOW
on the untask-attributed baseline v2 widening is absorbed by attribution here, not by
rewriting history: `## Tasks completed` now carries explicit non-task rows for `42b59cd8` and
`3c3c6d4a` naming the baseline edits and their rationale.

**Memory updates:** `specs/memory/product/sdd/sdd-gate-v3.md` — the FROZEN↔scan invariant
keeps its verbatim SPEC FR4 quote (A4.3 stays discharged) and gains a following paragraph
stating the residual the quote does not cover: a document **authored** into `_archive/` is an
ordinary new blob and *is* scanned, which is correct behavior and is precisely why
archive-time documents follow the redaction-at-authoring doctrine. The baseline layer is
restated at **version 4** with its current carve-out set.

### self-scan-guard-surfaced-two-more-baseline-false-positives

**Description:** 2026-08-14, second round. The regression test that closes the reviewer's
MEDIUM *"no test asserts that this repository's own pushable tip scans clean"* earned itself
immediately: it surfaced **two further genuine false positives**, both on content that is
edited routinely, both of which would have blocked pushes indefinitely.

1. The same synthetic `workspace.local` identity is matched **independently** by the
   `email-address` pattern, whose regex captures the whole address and is unaffected by the
   hostname pattern's exclude. Carving out `internal-hostname` alone would have re-attributed
   the CRITICAL's hit to another pattern instead of clearing it. Found while implementing
   ratified decision 3, before the test existed.
2. The stdlib `Path.home()` / `pathlib.Path.home()` call form is matched by
   `internal-hostname`'s `.home` TLD alternative — a dotted attribute chain read as a
   hostname. It permanently blocked two live source files
   (`features/telemetry/aggregator/runtimes.py`, `infrastructure/runtime_config.py`). Found
   by the self-scan test on its first run, which is exactly the class of defect the reviewer
   said prose evidence could not hold.

That first run returned **46** hits, not 0 — independently reproducing the reviewer's
"50 latent blockers" probe — in three classes: the 2 live-source false positives above;
hits confined to `specs/_archive/**` and `specs/audits/_archive/**`, formally FROZEN and
exempt from the real push gate by construction; and ~30 pre-existing synthetic fixture
literals under `tests/**` (fake addresses and fixture home paths) that predate this session.

**Resolution:** the two false positives were fixed **at the root**, RED-first, as narrow
anchored literal excludes — `privacy_baseline.json` v2 → v3 (the `workspace.local` pair) →
v4 (the `Path.home` form, case-sensitive). Narrowness is proven, not asserted: still-flagged
fixtures keep other `.local` hosts, other subdomains of the carved-out host, and a real
`.home` internal hostname matching. Neither is an amnesty entry — no sanctioned-terms list
exists (A4.1 still holds). The `tests/**` class was **not** silently suppressed: it is routed
to the `prior-published-term-amnesty` return and excluded from the test's scope with the
rationale written into the module docstring. Final scope of the guard:
`dadaia_workspace/` + `specs/` (both archive trees excluded) + `pyproject.toml`, ~513 files,
with a deterministic **empty** foreign-slug set — resolving `repos/` live would make the
suite's verdict depend on which sibling repos happen to be checked out on the machine running
it (a real collision was observed during development), violating the suite's determinism
filter.

**Memory updates:** `specs/memory/product/sdd/sdd-gate-v3.md` — the baseline carve-out set
now names the RFC-2606 reserved-TLD email domains, the product's own synthetic
`workspace.local` identity in both patterns, and the stdlib `Path.home` call forms, alongside
the pre-existing documentation-IP, `example.*` and noreply exclusions.

### scrubber-duplicate-insertion-at-the-tip

**Description:** 2026-08-14. The idempotent scrubber used in the history rewrite above left
one duplicate-insertion artifact in the tree at the branch tip — a mechanical defect of the
rewrite tooling, not of any authored change.

**Resolution:** Caught by tree-diff verification of the rewritten branch against the expected
tree (the reason that verification step exists) and amended out before anything advanced. The
trade-off accepted here is that a history rewrite is only as safe as its post-condition
check; the check found the one defect it was there to find. No content was lost, and the
suite stayed green across the amend.

**Memory updates:** none — a one-off tooling artifact of a local rewrite is not current
product truth.

### spec-acceptance-id-count-41-vs-36

**Description:** 2026-08-14. The dispatch brief for the QA task stated the SPEC carried **41**
acceptance ids; a direct count of `SPEC.md`'s `A<n>.<m>` markers gives **36** (A1: 5, A2: 4,
A3: 5, A4: 3, A5: 4, A6: 3, A7: 3, A8: 5, A9: 4). The approval-time figure was therefore
wrong, in the direction that matters least but still matters: it would have made a complete
review look incomplete.

**Resolution:** QA enumerated and evidenced all 36 ids one by one in `ALPHA-1-QA.md` and
recorded the discrepancy in the artifact rather than reconciling it silently. The authored
SPEC is the authority; no acceptance id is missing, and none was invented to reach 41. No
edit was made to the `Aprovado` SPEC to chase a briefing number.

**Memory updates:** none — a briefing arithmetic error is not product truth.

### sdd-gate-v3-tldr-exceeded-schema-length

**Description:** 2026-08-14. The T-090-11 memory update first wrote an `sdd-gate-v3` frontmatter
`tldr` longer than the memory-atom schema's length limit — the atom gained a whole new
subsystem (the push-range scan) and the one-line summary tried to carry all of it.

**Resolution:** `dadaia specs doctor` flagged it and the dispatcher trimmed the line to the
current value ("No-lock SDD enforcement: path/mode gates, advisory presence, and a
develop-only, denylist-scanned, security-gated push boundary."), a mechanical doctor-driven
fix inside the same memory commit; `catalog.json` carries the trimmed value. The depth that
did not fit the `tldr` lives in the atom body's `### Push-Range Denylist Scan` section, which
is where depth belongs. Recorded because the doctor caught an authoring defect of mine, not a
tooling defect.

**Memory updates:** `specs/memory/product/sdd/sdd-gate-v3.md` (frontmatter `tldr`) and
`specs/memory/product/catalog.json` (regenerated from it), both at `b6272772`.

### ship-task-archives-open

**Description:** 2026-08-14. T-090-13 (ship) has T-090-12 as a precondition, and T-090-12
archives the release directory into FROZEN `specs/_archive/`. As in v0.8.0, the ship task's
`[ ]` marker can therefore never be flipped to `[x]` — the task that closes the release is
structurally unable to record its own completion in the flat release shape.

**Resolution:** T-090-13 archives as `[ ]` and **must not** be edited afterwards, per the
v0.8.0 precedent: the gate blocks it, and editing archived content would be a worse lie than
leaving the marker open. Its completion evidence lives where it actually is — the milestone
(b) merge commit, the `code-reviewer` and `security-reviewer` handoffs for the shipped delta,
the PR `develop` → `main`, and CI. The canon gap is already tracked as the live backlog entry
`flat-release-ship-task-evidence` (opened from v0.8.0's closure); this release adds a second
occurrence to it rather than a duplicate return.

**Memory updates:** none — a task-template shape issue, not current product truth.

## Memory updates

All memory writes landed in the CLOSURE phase (`ACTIVE.md` `phase: CLOSURE` before the first
write), **before** this file — the finalization order memory → CLOSURE → archive, held in
both rounds. The first round was T-090-11, commit `b6272772`: five atoms plus the regenerated
catalog. The **second round** — the reopened close (`## Drifts ›
code-review-round-refused-own-close`) — rewrote one of them, `sdd-gate-v3.md`, again in the
same phase and again before this file; that edit touches the atom **body only**, so the
frontmatter `tldr`/`summary` are unchanged and `catalog.json` needs no regeneration (its
`token_estimate` for the atom is now a slight undercount — an estimate field, deliberately
not chased with a second generated-file edit inside a reopened close).

- `specs/memory/product/sdd/sdd-gate-v3.md` — `## Git Chokepoints` now states the push
  boundary as it is: branch policy, then the range-scoped denylist scan, then the security
  verdict; tags review-exempt but scan-covered; branch deletions neither scanned nor
  verdict-checked. A new `### Push-Range Denylist Scan` section carries the range computation
  from the pre-push `remote_sha` (both forms), blob-only reading with sha dedupe, the three
  additive term layers with the baseline at **version 4** and its current carve-out set
  (RFC-2606 reserved-TLD email domains; the product's own synthetic `workspace.local` identity
  in both the hostname and the email pattern; the stdlib `Path.home` call forms; alongside the
  pre-existing documentation-IP, `example.*` and noreply exclusions), the never-a-no-op posture
  and the stderr mode line, the fail-closed/fail-open table, the masked and satisfiable refusal
  contract, and the **FROZEN↔scan invariant quoted verbatim from SPEC FR4** (A4.3 discharged)
  — now followed by the nuance the quote does not carry: renames reuse the blob, but a document
  *authored* into `_archive/` is an ordinary new blob and **is** scanned. Frontmatter
  `tldr`/`summary` updated in the first round (see the drift on the trim); the second round
  edited the body only.
- `specs/memory/quality-assurance.md` — new `## Redaction At Authoring` section records the
  posture as product truth: the three verbs that accept `--redact`, the stable
  `[REDACTED-CONTEXT-<n>]` placeholder ordinal by first appearance, opt-in and render-boundary
  only, the doctrine binding the `qa-engineer` persona, and the scan named as the mechanical
  backstop on the exit path. `## Satisfiable Diagnostics` gains the refusal's healing action
  and the reason a rewrite of published history is never demanded.
- `specs/memory/product/platform/workspace-doctor.md` — new `## Redacted Output` section:
  `dadaia doctor --redact` masks every foreign Spec Context name and repo slug in the reported
  issues; frontmatter summary updated.
- `specs/memory/product/platform/context-management.md` — new `## Redacted Output` section:
  `context list` and `context show` accept `--redact` in table and `--json`, the caller's own
  context stays visible, redaction applies at the render boundary only, and the redacted JSON
  keeps the same key set; frontmatter summary updated.
- `specs/memory/architecture.md` — the chokepoint paragraph names the new seam: the pre-push
  script's stages now include the range-scoped denylist scan, and `features/chokepoints/`
  purity is stated with `GitObjectReader` (adapter
  `infrastructure/git_objects.GitSubprocessObjectReader`, built at the composition root)
  alongside the existing `ProcessAncestry`, with the required-parameter property that makes an
  unwired call site a type error. The seam was judged structural — SPEC §5 left this
  conditional and the condition is met.
- `specs/memory/product/catalog.json` — regenerated: the `sdd-gate-v3`, `quality-assurance`,
  `workspace-doctor` and `context-management` `tldr`/`summary` values moved, and the `privacy`
  tag was added where it now applies. No slug added, removed or re-ranked.
- `specs/memory/product/index.md` — no change: no feature was added, removed or re-ranked;
  this release deepened four existing features rather than creating one.
- `specs/memory/tech-stack.md` — no change: the scan is stdlib plus the `git` binary already
  in the stack; no dependency, command or Python version moved.

No atom gained a `Changelog`, `History`, `Histórico` or `Versions` section, and none narrates
a past version. This release's history lives in this file and in the archived directory.

## Dispositions

This release picked **no bug and no audit**: `dadaia bugs status` reported **0 open** at pick
time, and both outstanding audits were fully dispositioned and archived by v0.8.0. The sweep
below is therefore complete with three rows — the picked backlog entry, the entry absorbed
into it, and the absorbed idea.

**Purge-on-pick was performed by the PM before T-090-01** (operator-ratified doctrine, grill
ADR #14): the two consumed live entry files were removed and the removal rode the T-090-01
definition commit, with the provenance record in `SPEC.md` §7 and the ledger rows retained
forever in `specs/backlog/candidates.md` per the never-delete law. The pending state that
§7 recorded at authoring time is therefore resolved: the purge happened.

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/backlog/push-range-denylist-scan.md` (#1, P1) | backlog | `DELIVERED — v0.9.0` | The entire release scope. FR1–FR7 + FR9 delivered and QA-verified across 36/36 acceptance ids (`ALPHA-1-QA.md`); live file purged at `7f3185fc` (pre-rewrite T-090-01 definition commit), ledger row 1 of `specs/backlog/candidates.md` retained and now terminal; provenance `SPEC.md` §7 |
| `specs/backlog/redact-foreign-context-names-at-qa-authoring.md` (#17) | backlog | `DELIVERED — v0.9.0` | Absorbed as FR8 (grill ADR #5). `--redact` on all three verbs + the doctrine line, A8.1–A8.5 all verified (V8); live file purged at the same definition commit, ledger row 17 retained and now terminal; provenance `SPEC.md` §7 |
| `specs/backlog/tag-push-carve-out-reachability.md` (idea) | backlog | `DELIVERED — v0.9.0` | Absorbed as FR2 (grill ADR #4). Tag pushes keep the security-verdict carve-out and are now scan-covered, closing the `service.py:344` bypass; A2.1–A2.4 verified (V2). Its ledger row in `candidates.md` was flipped at pick; the entry file was flipped to `status: delivered` / `delivered_in: v0.9.0` and archived to `specs/backlog/_archive/` by `project-manager` at closure time (commit `03ddd0b2`, before this CLOSURE was committed) — no open item remains |

Explicit non-flips, so a later reader does not read them as an incomplete sweep:

- `specs/backlog/commit-paths-index-scope-hardening.md` (#18) and
  `specs/backlog/python-env-interpreter-probe-hardening.md` (#9) — stay `candidate`. SPEC §4
  non-goals 4 and 5: same Arm-B hardening lane, no ADR absorbed them, untouched here.
- `specs/backlog/_archive/dispose-published-denylist-term.md` — already terminal `rejected` as
  void by construction; FR4 records *why* (the FROZEN↔scan invariant), and nothing about it
  changed.
- No bug status was flipped and no `dadaia bugs append` event was emitted **by the release
  scope**. The one bug touched during the window was *registered*, not resolved — see
  `## Backlog returns`.

## Test dispositions

No demotion, no quarantine expiry and no SCAFFOLD expiry occurred in this release. Every test
added declares its intent at birth (V11): 8 modules `CONTRACT`, plus the code-review round's
`tests/integration/test_repo_self_scan.py` as `SENTINEL` and 6 further cases inside modules
this release already owns. Nothing was deleted, skipped or disabled to reach green — the diff
carries zero `skip`/`xfail`/`quarantine` additions at either tip. The release added exactly
**one** LARGE-tier e2e test, which names its owner per the LARGE rules; the remediation added
none.

| Kind | Deleted/expired test | Replacement / disposition | Evidence |
|------|----------------------|----------------------------|----------|
| demotion | none | none — no LARGE test was replaced or removed | `ALPHA-1-QA.md` §"Test stewardship checklist" |
| quarantine expiry | none | none — no quarantine marker added or expired | `git diff origin/develop..HEAD -- tests/` (zero marker additions) |
| SCAFFOLD expiry | none | none — all 9 new modules declared their intent at birth: 8 × `Intent: CONTRACT — v0.9.0 <A-ids>`, 1 × `Intent: SENTINEL` (`test_repo_self_scan.py`) | V11; per-module grep confirmed by QA for the first 8, module docstring for the 9th |
| LARGE census | — | +1 e2e (`test_planted_term_refused_then_clean_push_after_amend`), owner named in-file; census now **56** collected `-m e2e` against the `tests/AGENTS.md` cap of 30 | `pytest --collect-only -q -m e2e`. The overshoot is **pre-existing** and already owned by the live backlog entry `test-suite-remediation-stewardship` (P1); this release's +1 does not silently grow past its declared handling and is not a new return |

## Backlog returns

`specs/backlog/**` belongs to `project-manager` (`DADAIA.md` §5); this release authors nothing
there. The items below are **routed in writing** for the PM to materialize or reject. Nothing
here is picked and no status anywhere is flipped by this closure.

- `backlog/candidates.md` ← **Commit-message scanning — the residual channel.** SPEC §4.2, and
  operator-ratified at approval as *defer to backlog at closure*. `rev-list --objects` lists
  commits without a path and this release scans **blobs only**, so a commit message naming a
  private project still leaves through a push unseen. This is the one known hole left in the
  channel this release closed, and it is recorded here deliberately rather than left implicit.
- `backlog/candidates.md` ← **QA-1: no end-to-end coverage of the binary-skip-count note**
  (LOW, non-blocking). The pure matcher's `skipped_binary_count` and the adapter's
  `decodable=False` marking are each unit-tested, but nothing asserts the note actually
  reaches the operator through `push_gate_decision` → `Decision.warn` → CLI stderr. The wiring
  was manually verified correct live (`_annotate_skip` at `service.py:329`, echoed on both the
  allow and refuse paths); the gap is coverage of an already-correct path. Suggested fix: one
  unit test asserting `decision.warn` carries the skip count on an allow case and a refuse
  case.
- `backlog/candidates.md` ← **Baseline pattern versioning and a carve-out review cadence.** The
  RFC-2606 gap was found by the baseline refusing legitimate synthetic content on its first
  real run, i.e. by accident of timing rather than by review. `privacy_baseline.json` is now at
  version 2 with no defined moment at which its patterns and `exclude_regex` carve-outs are
  re-examined against the reserved/synthetic-value RFCs. Candidate: a periodic review lane, or
  a doctor check that flags baseline patterns lacking a documented carve-out rationale.
  Included at my judgement — the drift above is one instance of a class, not a one-off.
- `backlog/candidates.md` ← **`prior-published-term-amnesty` — the structural tension of
  whole-blob matching.** Operator-ratified at the code-review round: whole-blob matching is
  **kept**, and the refinement is that a term already present in the **remote-reachable
  version of the same path** should not refuse — the blob is new, but the term is not, so
  refusing it demands a rewrite of content the operator already published, which is exactly
  what the range scope exists to avoid. This is the single item that would clear the ~30
  pre-existing `tests/**` fixture literals and the archive-tree hits without any amnesty list
  and without narrowing to diff-scoped matching. P1 in my reading: without it, every
  long-lived file that already contains a matching line is a latent one-time blocker.
- `backlog/candidates.md` ← **`refusal-path-redaction` (LOW, from the review).** The push-gate
  refusal masks the term and never echoes the matched line, but prints the offending **blob
  path** verbatim — and a path can itself carry a private name. Meanwhile FR8a's `--redact`
  covers `doctor`, `context list` and `context show` only, while the new QA doctrine tells
  agents to transcribe diagnostics into authored documents. Two acceptable resolutions:
  extend the redaction surface to the refusal renderer, or state in the doctrine that gate
  refusals must be hand-masked, path included. Today only the by-hand branch exists.
- `backlog/ideas.md` ← **`bugs.jsonl` republishes its whole file as a new blob on every
  append.** Surfaced by the perf re-measurement (V14): one ~900 KB blob appended twice inside
  a local range dominates the scan cost and is the reason the A7.3 2 s budget is missed on a
  247-object range. Included at my judgement — it is a real cost driver named in evidence, and
  leaving it only inside a validation row would bury it.

**Reviewer findings absorbed nowhere else, accepted without action** (so nothing from the
REQUEST-CHANGES round silently disappears; the CRITICAL, both HIGHs, all three MEDIUMs and
four of the six LOWs were fixed at `3c3c6d4a` or in this document):

- LOW — *baseline widened in a commit with no task id and a subject not matching its diff*:
  accepted as attribution debt, resolved forward by the non-task rows now in
  `## Tasks completed`; no history rewrite for a commit-message defect.
- LOW — *refusal prints the blob path unredacted*: routed to backlog above, not fixed here.
- INFO — *`_mask` discloses short terms* (a 1–2 character operator term is effectively
  published in the refusal): accepted. Operator terms have no minimum length; a fixed-width
  mask or minimum-length guard is a sensible future refinement, not a close blocker.
- INFO — *`ContextRedactor.json_value` leaves dict KEYS unredacted*: accepted, documented as
  intentional (A8.4 key-set preservation), and verified to leak nothing today because both
  redacted payloads have static key sets.
- INFO — *the push scan matches line-by-line while the public-privacy doctor matches whole
  text*: accepted. All six baseline patterns are single-line, so behaviour is identical today;
  the residual is a constraint — baseline patterns must stay single-line — recorded here
  rather than enforced.
- INFO — *ReDoS probe*: no exponential backtracking in the baseline; the residual quadratic
  cost on a pathological single line is now bounded by the 5 MB per-blob cap added at
  `3c3c6d4a`.
- INFO — *architectural positives* (ring purity, port/adapter placement, required-parameter
  injection, policy order, masking confined to the matcher): no action, recorded as confirmed
  by an independent reviewer. Its one sub-note — `test_push_gate_check_always_wires_a_real_
  object_source` asserts *a* source is called via a spy rather than the concrete adapter type,
  so the name over-claims slightly — is accepted as-is; the contract it actually pins (the
  source is reached) is the one that matters.

**Registered during the release, not a return** (already in the ledger, listed so the record
is complete). Both are Arm B material for a `hotfix/{M.m.p}`, not release material, and
neither is carried as a release defect:

- `specs-resolver-context-tests-flaky-under-xdist-full-suite` (QA-2, LOW) — 13 pre-existing
  context/session-resolution tests failed once under preflight's full-suite `-n auto` load and
  did not reproduce on an isolated re-run or a full-suite re-run. Same flake class as the
  already-resolved `panel-*-flaky-under-xdist-load` bugs, different site; outside this
  release's scope (`features/chokepoints/**`), whose own runs are green and reproducible.
- `mypy-strict-cache-dir-created-without-cache-dir-env-override` (LOW, workspace tooling) —
  registered at `d869c7dc` during the code-review remediation window. The documented local
  invocation `mypy --strict dadaia_workspace/` materializes `.mypy_cache/` in the repo working
  tree despite `incremental = false`, contradicting the `[tool.mypy]` comment that asserts it
  cannot and violating the repos-stay-clean rule (`DADAIA.md` §4); CI already redirects the
  cache correctly, the local path does not. Session workaround was an explicit
  `MYPY_CACHE_DIR` outside the tree; the fix (pin `cache_dir` outside the repo, or document
  the env var) belongs to a hotfix, not here.

## Version bump decision

**Decision: bump `pyproject.toml` `0.5.2` → `0.6.0` (minor) and add a `CHANGELOG.md` entry
under `[0.6.0]`.** Recorded here as **owed**; the dispatcher executes both, since
`product-engineer` has no shell. This inverts v0.8.0's no-bump ruling for the honest reason
that the two releases are not alike:

1. **This release ships bytes.** v0.8.0 was a record release with zero production code; v0.9.0
   adds a new port and adapter, a new pure matcher, a new policy step in the push decision,
   new CLI wiring, a `--redact` flag on three verbs, and a baseline data version bump (v1 → v4
   after the code-review round). A wheel built from this tree behaves differently from one
   built from `0.5.2`.
2. **Minor, not patch: new capability, backward-compatible surface.** Two new user-visible
   capabilities (the push-range denylist scan and the `--redact` output mode) with no removal
   and no breaking change — default output is pinned byte-for-byte unchanged by contract test
   (A8.2). Under the package's `0.x` scheme that is a minor.
3. **Not a patch, because this is not a hotfix.** Law §5 binds PATCH-with-CHANGELOG to a
   hotfix merge; this is a feature release closing at milestone (b), and minting a PATCH would
   misfile a capability as a fix.
4. **The two version axes stay distinct.** `v0.9.0` is the SDD release identity; `0.6.0` is the
   package version. ADR-2 (`specs/memory/product/distribution/pypi-distribution.md`) documents
   the split and neither axis is renumbered to chase the other — the coincidence of digits
   here is not a merge of the axes.

**Unchanged by the code-review round — with one addition to record.** The remediation added
no capability and removed none, so the decision stands at `0.6.0` exactly as reasoned above.
What rides along is a **packaging metadata change**: `pyproject.toml`'s `authors` entry moves
to the GitHub `users.noreply.github.com` form (ratified decision 2 of the review round). It is
metadata, not surface — it changes no import, no CLI verb and no behavior — so it neither
raises the bump nor justifies a separate one; it simply ships in the same commit that carries
the version, and the `[0.6.0]` entry should say so rather than let a published author address
change silently.

The `CHANGELOG.md` `[0.6.0]` entry should name both capabilities, the baseline carve-outs
(now v4), and the author-metadata change. The pre-existing CHANGELOG version-axis incoherence flagged at v0.8.0's closure is
already tracked as the live backlog entry `changelog-version-axis-reconciliation` and is not
re-returned here; this entry should be written in the file's current shape, not used as an
occasion to reconcile it.

## Archive decision

**MOVE** — `specs/releases/v0.9.0/` moves to `specs/_archive/releases/v0.9.0/` via `git mv`,
executed by the dispatcher. `ACTIVE.md` is set in the same commit to `release: none` /
`phase: none`: no release follows immediately, and the next pick is the PM's — with 0 open
bugs and no undispositioned audit, the queue at the next pick is backlog-first for the first
time in three releases.

This is the **second** archive move attempted for this directory: the retired close commit
`946272e4` archived it, the code-review round reopened the release, the archive move was
undone and the directory is live under `specs/releases/` again for the amendment — and this
close moves it once more. Recorded because a reader comparing git history against the FROZEN
rule deserves the true sequence: `_archive/` was never *edited in place*. Reopening a close
takes the release **out** of the archive first and puts it back after; that is the only
sanctioned shape.

The archived directory carries T-090-13 as `[ ]` by design (see `## Drifts`); after this move,
nothing under `specs/_archive/` is edited again — which is also the invariant this release's
own scan depends on (FR4). One nuance that invariant does **not** grant, learned the hard way
this round and now recorded in memory: this CLOSURE is a **new blob** whichever directory it
lands in, so it is scanned like any other authored document. The archive protects renames, not
authoring — which is why every literal in this file is masked.
