# SPEC — Release v0.11.0 — scan-v2: prior-published-term amnesty and push-gate hardening

**Status:** Aprovado — operator-delegated approval, 2026-08-15 (goal directive)
**Release ID:** v0.11.0
**Owner:** product-engineer
**Opened:** 2026-08-15
**Created:** 2026-08-15
**Branch:** `feature/v0.11.0` (cut from `develop` at `d15bdf4e`; branch contract: `dadaia-gitflow`)
**Consumes:** prior-published-term-amnesty, denylist-scan-skip-note-oversized-mislabel,
registry-derived-foreign-name-set, refusal-path-redaction,
push-ref-sha-validation-git-argv-hardening, git-objects-batch-parse-typed-error-boundary,
git-objects-streamed-batch-reads, self-scan-sentinel-integration-marker,
closure-v14-perf-figure-correction
**Picked set:** nine backlog entries (#19, #20, #22, #23, #25, #26, #27, #28, #29 in
`specs/backlog/candidates.md`). **No bug is picked, because there is no open bug** — at pick
time the bug ledger carries **zero** open bugs: the two v0.9.0-window LOWs
(`specs-resolver-context-tests-flaky-under-xdist-full-suite`,
`mypy-strict-cache-dir-created-without-cache-dir-env-override`) were closed by
`hotfix/0.7.1`, merged at `d15bdf4e` — the very commit this branch was cut from — each
carrying a `resolved` event in `specs/bugs/bugs.jsonl` alongside the `0.7.1` mint.
**No audit is outstanding** — both 2026-07 audits were archived fully dispositioned by
v0.8.0. Pick-time priority (`DADAIA.md` §5) is therefore satisfied with nothing outranking:
backlog P1 leads.
**Grill (mandatory, done):**
`.dadaia/reports/dadaia-workspace/product-engineer/2026-08-15T160500Z-refine-specs.html`
— fifteen refinement problems (P1–P15) resolved; ADRs **D1–D8** are binding and settled and
are **not re-litigated here**.
**Intake provenance:** all eight implementation entries carry an ADR #15 intake approval —
#20, #22, #23, #25, #26, #27, #28, #29 were **APPROVED** at intake report #1
(`.dadaia/reports/dadaia-workspace/project-manager/2026-08-15T132600Z-intake.html`,
operator-delegated adjudication 2026-08-15), and #19 is a **pre-approved intake**
(operator deferral, ratified retroactively at the v0.10.0 approval, SPEC §7/§8). Nothing in
this release's scope was materialized by an agent without an operator decision.

---

## 1. Problem and context

v0.9.0 shipped the push-range denylist scan. It worked — it refused its own author twice,
both times legitimately — and the release closed with an honest list of what it did not
fix. Nine of those residuals are picked here. They are not nine unrelated chores: seven of
them live inside one 190-line adapter and one 170-line pure matcher, and the way they
interact is the whole content of this release.

**The blocking problem (P1 of the backlog, entry #19).** The scan matches **whole blobs**.
The operator ratified that ruler and routed the tension it creates to the backlog rather
than narrowing to diff-scoped matching. The tension: any edit to a long-lived file that
already contains a matching line produces a **new blob**, so the scan refuses — even though
the matched value was already published in the remote-reachable version of that same path.
The refusal is unsatisfiable in the way the product forbids: it demands a rewrite of content
the operator already published, which is exactly what the range scope exists to avoid
(`quality-assurance.md` §"Satisfiable Diagnostics"). Sized by the v0.9.0 round-2 code
review: **29 latent one-time blockers under `tests/**`** at the shipped v4 baseline
(14 `home-abs-path`, 9 `email-address`, 5 `ipv4-literal`, 1 `secret-token`) across 450
tracked test files. Until this ships, editing any of those files refuses the push and the
only escape is `--no-verify` — the bypass the gate itself names as discouraged. A security
control whose first year of production use trains its own bypass is a failed control.

**The honesty problem (entry #20).** The 5 MB per-blob cap is a disclosed, sound fail-open
(v0.9.0 SPEC R3). But every `decodable=False` object is counted into one
`skipped_binary_count` and rendered as *"N binary blob(s) skipped by the denylist scan (not
text-decodable)"* (`service.py:328-337`). A 6 MB plain-text file — a log capture, a SQL
dump, vendored data — is neither binary nor undecodable. It is published unscanned while the
one message the operator sees says a binary blob was skipped, from which the operator
correctly concludes there was nothing to check. CWE-778, reported independently as MEDIUM by
both v0.9.0 ship reviewers.

**The coverage problem (entry #22).** The foreign-name term layer enumerates
`<workspace>/repos/` directory names only (`ci.py:226-241`); the registry
`.dadaia/states/spec_contexts.json` is never read. A Spec Context that is registered but
whose repo directory is absent — a DEAD or relocated context — contributes no term. The
protection silently **shrinks** at exactly the lifecycle moment the name becomes more
sensitive, not less.

**The residual-leak problem (entry #23).** The refusal masks the matched term and never
echoes the matched line, but prints the offending blob path verbatim
(`service.py:351`) — and a path can itself carry the private name the gate is protecting.
CWE-532, found at the code review, re-confirmed at the ship security review, accepted then,
open now.

**The robustness problems (entries #25, #26, #27).** Three LOWs on the same surface, all
fail-closed today and all cheap: pre-push shas reach `git` argv unvalidated with no `--`
end-of-options marker, and one measured input class (`--glob=`/`--branches=`-shaped
`local_sha`) produces a **successful empty** rev-list, silently no-opping the scan for that
ref instead of failing closed (CWE-88/CWE-20); two parse paths in `_read_blobs` raise raw
`ValueError` past the module's own typed-error contract, and the desync branch *continues*
into garbage instead of aborting (CWE-755); and the whole `cat-file --batch` output is
materialised in one buffer before the first object yields — a measured ceiling of
**11,478 blobs / ~277 MB** on the fallback range shape (CWE-400).

**The hygiene problem (entry #29).** The self-scan SENTINEL carries only
`pytest.mark.slow`, not the `[integration, slow]` pair its six sibling modules use. Today's
`-m "not quarantine"` selector runs it; any future `-m integration` adoption would silently
drop the one test that pins "this repository's own pushable tip scans clean".

**The record problem (entry #28).** The archived v0.9.0 CLOSURE reports the fallback-range
benchmark at 2.978 s. Two independent measurements contradict it: the real 8,861-blob /
133 MB range costs ~147 s (read 4.29 s + match 142.9 s, ≈1.3 s/MB). `CLOSURE.md` is FROZEN
under `specs/_archive/` and is never edited — the sanctioned shape is a forward correction
in memory.

**What the grill added that the entries did not carry.** The nine entries were written
independently and their interactions were not. Four matter enough to shape the release:
the amnesty predicate must key on the **matched value**, not the pattern, or it becomes a
smuggling path (P1); the amnesty **doubles** the adapter's resident set, so #27 is a
precondition and not a sibling (P3, ADR D8); #23's second intent as literally written would
require a `features → cli` import that the ring purity forbids (P4, ADR D1-a); and #20's
new skip note names a path verbatim, re-opening #23's exact CWE class in a second channel
(P5). All four are resolved below.

---

## 2. Objective

The push-range denylist scan stops refusing what it already published, without acquiring an
amnesty list, without narrowing its ruler, and without loosening a single fail-closed edge.
In the same pass, its three known fail-closed-but-ugly failure modes become typed and
bounded, its one fail-open becomes honest and partially covered, its term layer stops
forgetting dead contexts, and the one place it speaks while protecting a name stops printing
that name.

This is a **production-code release**, implemented by `software-engineer`
(`DADAIA.md` §2). It touches `features/chokepoints/**`, `infrastructure/git_objects.py`,
`core/protocols/git_object_reader.py`, a new `core/redaction.py`, `cli/redact.py`,
`cli/commands/ci.py`, `container.py` and `tests/**`. It authors **no** AI-surface file, no
skill, no persona, no law text, and no CLI verb.

---

## 3. Scope

**Standing scope rule for every zero-hit acceptance criterion in this SPEC (P12, the 2-8
lesson).** Every grep-based criterion is evaluated over the working tree **excluding**
`specs/_archive/**`, `specs/bugs/**`, `specs/backlog/_archive/**`, `CHANGELOG.md` and
`specs/releases/v0.11.0/**` (this release's own documents, which must quote the strings they
forbid). A criterion that does not restate the exclusion set inherits it from here.

**Standing privacy rule.** Everything this release authors is pushed through the very gate it
modifies. Synthetic literals only in every test, spec and code comment: no foreign context
name, repo slug, hostname, IP, email or absolute local path.

---

### FR1 — Prior-published-term amnesty: the matcher suppresses only what the same path already published

`features/chokepoints/denylist_scan.py` gains one suppression rule, expressed **once** and
applied uniformly to all three term layers:

> A candidate hit is suppressed **iff the exact matched string occurs, case-insensitively,
> in the prior published text of the SAME path.** Otherwise it is a hit.

The predicate keys on the **matched value** (`match.group(0)` for a baseline pattern, the
literal for an operator term or a foreign name), never on the pattern id or the layer
(grill P1). A file whose prior version carried one email address therefore does **not**
amnesty a different email address introduced by the edit.

Three consequences are normative and individually testable:

1. **Same-path prior-published value never refuses.** Editing a file that already carried
   the matched value at the published base produces no hit for that value.
2. **The same value in a NEW path still refuses.** The amnesty is bound to the path, not to
   the value; a value moved or copied into a path that did not publish it is a new
   publication.
3. **A NEW value in an edited path still refuses.** Prior content grants nothing beyond the
   values it actually contains.

The prior text reaches the matcher on the `ScannedObject` itself (FR2) — `scan_objects`
gains **no new parameter**, so `features/chokepoints/**` acquires no new input source and
stays a pure function of the objects and the term sources it already receives.

**No list is introduced anywhere.** The amnesty derives from published git state. FR4 of
v0.9.0 and its A4.1 contract test survive unchanged (FR10).

**Acceptance**

- A1.1 A blob whose prior version at the resolvable base contains the matched value produces
  no hit for that value (unit, real-git integration).
- A1.2 The same value appearing in a path with no prior content produces a hit.
- A1.3 A value **absent** from the prior version of an edited path produces a hit, even
  though another value of the same baseline pattern id was present there.
- A1.4 The suppression is case-insensitive on both sides, matching the matcher's existing
  case-insensitivity on every layer.
- A1.5 `scan_objects`'s signature is unchanged apart from consuming the new `ScannedObject`
  field; `features/chokepoints/**` imports no `infrastructure` and no `cli` module
  (`lint-imports --config setup.cfg --no-cache` green).
- A1.6 Editing a `tests/**` file that carries a pre-existing fixture literal no longer
  refuses the push — proven over a real range with a real remote in the integration tier.

### FR2 — The port resolves the same path at the published base, in the same batched conversation

`core/protocols/git_object_reader.ScannedObject` gains one field carrying the prior
published text of the same path (absent ⇒ no prior content). The subprocess adapter
`infrastructure/git_objects.GitSubprocessObjectReader` resolves it.

**Base resolution (ADR D7).** The prior side is defined **only** in the resolvable-base range
shape — `remote_sha` non-zero and resolvable locally, the shape `git rev-list --objects
<local> --not <remote>` already uses. In the `--not --remotes` fallback shape there is no
single published base, so **no object carries prior content and no hit is ever suppressed**;
behaviour there is byte-identical to v0.9.0. This is a deliberate conservative boundary, not
an oversight (grill P2), and is recorded as a non-goal in §4.

**Mechanism.** For each distinct path in the range, the prior blob is resolved as
`<base>:<path>` through the **same batched conversation shape** the content read already
uses — one `cat-file --batch-check` to learn existence and size, one `cat-file --batch` to
read — executed **inside the FR9 chunk loop**, so the peak resident set stays bounded by
`chunk_size × cap × 2` rather than growing with the range (ADR D8). No per-object subprocess
is introduced on this path.

**Fail-closed boundary (grill P14) — three outcomes, all landing on refusal:**

| Situation | Verdict |
|---|---|
| `git` fails resolving the prior side (non-zero exit, timeout, missing `git`) | **refuse**, naming the git failure, exactly as FR6 of v0.9.0 already does |
| The path does not exist at the base (a genuinely new file) | not a failure — **no prior content**, so every hit refuses |
| The prior blob exists but is over the cap or is not valid UTF-8 | **no prior content**, so every hit refuses |

There is no path on which an amnesty is granted from a base the adapter could not read.

**Acceptance**

- A2.1 In the resolvable-base shape, each scanned object carries the prior text of its own
  path, or an explicit absence.
- A2.2 In the fallback shape every object carries an explicit absence and the decision is
  byte-identical to v0.9.0 for the same inputs.
- A2.3 A forced `git` failure on the prior-side lookup refuses, naming the failure; the
  refusal names `git push --no-verify` as the single traceable bypass.
- A2.4 A path absent at the base, an over-cap prior blob, and an undecodable prior blob each
  yield "no prior content" and their hits refuse (three unit cases).
- A2.5 The number of `git` subprocess invocations per chunk is a constant independent of the
  number of blobs in that chunk (contract test counting invocations).
- A2.6 `core/protocols/git_object_reader.py` remains zero-I/O; the new field is data only.

### FR3 — The self-scan sentinel covers `tests/**` behind a shrink-only baseline, and carries the integration marker

`tests/integration/test_repo_self_scan.py` extends its scan scope to `tests/**` (ADR D3),
with an explicit baseline of the pre-existing fixture literals. Two properties make that
baseline honest:

1. **No hit outside the baseline.** A newly introduced matching literal anywhere under the
   scanned scope fails the SENTINEL.
2. **Shrink-only.** Every baseline row must still produce a hit. A row whose file has been
   cleaned fails the test until the row is deleted — so the count can only go down, and the
   29-blocker figure becomes test-pinned rather than review-pinned.

**This baseline is not the forbidden amnesty list (grill P7).** It is a test assertion
baseline: it lives in the test module, the production matcher and adapter never read it, and
the A4.1 source scan of `denylist_scan.py` is unchanged and still green (FR10). The
distinction is stated in the test module's own docstring so a future reader does not have to
reconstruct it.

The module's `pytestmark` gains `pytest.mark.integration` alongside `slow`, matching its six
sibling modules (entry #29).

**Acceptance**

- A3.1 `_SCAN_SCOPE` includes `tests`; the `specs/_archive/**` and `specs/audits/_archive/**`
  exclusions and the deterministic empty foreign-slug set are unchanged.
- A3.2 The baseline is a literal, enumerated structure of `(path, pattern id)` rows; its size
  is recorded in `CLOSURE.md` as the measured figure.
- A3.3 A planted synthetic matching literal in a file not on the baseline fails the test.
- A3.4 A baseline row that no longer produces a hit fails the test with a message naming the
  row to delete.
- A3.5 `pytestmark` carries both `integration` and `slow`; the sentinel is collected under
  `-m integration`, `-m slow` and `-m "not quarantine"`.
- A3.6 The production matcher's source contains no reference to the baseline
  (A4.1 grep unchanged and green).

### FR4 — Oversized blobs are partially scanned and honestly reported

The 5 MB cap stops being a total blind spot (ADR D2).

**Reading.** An oversized blob is read through a **separate, bounded** per-object stream
(`git cat-file blob <sha>`) from which at most the cap's worth of bytes is read before the
stream is closed; git then stops producing, so the remainder is genuinely **never fetched**
and v0.9.0's R3 property holds as stated (ADR D2-a). Two rules make this safe:

- the deliberate early close makes a non-zero exit / `EPIPE` **expected on this call only**
  and it must not be converted into `GitObjectReadError`;
- the per-object read exists **only** on the oversized path. The under-cap population keeps
  the single batched conversation, so v0.9.0's per-blob-spawn remediation is not undone.

**Reporting.** The two skip classes become distinguishable everywhere (grill P13):
`skipped_binary_count` keeps its meaning and counts genuinely undecodable blobs only;
oversized blobs are carried as structured notes bearing path, total size and scanned bytes.
`service._annotate_skip` renders them as what they are — the file, its size, that only its
first 5 MB was scanned, that the remainder was **NOT** scanned, and that it needs
verification by hand — while genuinely binary blobs keep today's wording. Both are emitted on
the allow path and on the refuse path, as today. The path in that note is masked per FR6.

**QA-1 closure.** The operator-facing channel is pinned by tests rather than by a manual
check: `decision.warn` carries the note on an allow case and on a refuse case.

**Acceptance**

- A4.1 An oversized **text** blob produces a hit when its first 5 MB carries a matching value
  (the fail-open is now partial coverage, not zero coverage).
- A4.2 An oversized blob's bytes beyond the cap are never read: the reader's byte count for
  that object is ≤ the cap (contract test over a synthetic over-cap blob).
- A4.3 A genuinely undecodable blob is still skipped and counted, with today's wording.
- A4.4 The oversized note names the path (masked per FR6), the total size and the fact that
  the remainder was not scanned; the two counts are separately readable by every consumer.
- A4.5 `decision.warn` carries the note on an allow decision and on a refuse decision (QA-1
  closed), asserted by unit tests.
- A4.6 An oversized blob whose 5 MB prefix is not valid UTF-8 falls back to the binary count
  and is reported with the binary wording.

### FR5 — The foreign-name layer is registry-derived: a DEAD context keeps protecting its name

`cli/commands/ci.py#_foreign_repo_slugs` derives its set as:

```
{registry context names} ∪ {registry repo_slugs} ∪ {repos/ directory names}
    − {own context name, own repo slug}
```

DEAD and relocated contexts therefore contribute their terms. **Both** self-identities are
subtracted, because a context's `name` and its `repo_slug` are separate fields
(`core/models/spec_context.py`) and may differ — subtracting only the slug would re-open the
A3.2 regression through the new door (grill P8).

The registry is read through a **new container seam** mirroring `load_denylist_terms` /
`load_denylist_baseline_patterns` (`container.py:209-225`), so the CLI still imports no
`infrastructure` module.

**Sequencing (ADR D4).** This layer becomes strictly larger, so it lands **after** FR1 and
only after a one-off enumeration of the wider set's latent blockers has been run and
dispositioned. The two wider-set hits the v0.9.0 reviewer demonstrated live in
`specs/bugs/bugs.jsonl`, are pre-existing, and are same-path prior-published — with FR1 in
place they are amnestied by construction (grill P9).

**Acceptance**

- A5.1 A DEAD registry context's name and its repo_slug both refuse a push that introduces
  them in new content (unit + integration over a real registry fixture).
- A5.2 A fixture whose context `name` differs from its `repo_slug` never contributes either
  of its own identities when it is the pushing repo.
- A5.3 The registry read goes through the container seam; `lint-imports` is green and no new
  `ignore_imports` entry is added (the cap in
  `tests/contract/test_import_linter_ignore_cap.py` is unchanged).
- A5.4 A registry that is missing, empty or malformed yields the directory-derived set and
  never crashes the push hook.
- A5.5 The pre-landing enumeration was executed, its hit list recorded, and each hit
  dispositioned (amnestied by FR1, or explicitly accepted with a reason) — evidence in
  `CLOSURE.md`.
- A5.6 The self-scan sentinel's deterministic empty foreign-slug set is unchanged (A3.1).

### FR6 — Every operator-facing gate string that names a blob path masks its private-name-bearing segments

Resolution **A** of entry #23 (ADR D1): the redaction machinery is extended to the gate's
render boundary rather than the doctrine being patched to say "mask it by hand".

**Placement (ADR D1-a).** The masking primitive — word-boundary alternation, longest-first
ordering, stable first-appearance placeholder ordinals — is extracted into a new
stdlib-pure `core/redaction.py`. `cli/redact.py#ContextRedactor` becomes a thin consumer with
**byte-identical** behaviour, and the gate renderers in `features/chokepoints/service.py`
consume the same primitive. This is what makes the extension possible at all:
`features/chokepoints/**` imports `core` only and may never import `cli`
(`architecture.md`), so the intent as literally written was unimplementable (grill P4).

**Scope.** The rule is stated over a class, not a call site: **every operator-facing string
the gate emits that names a blob path masks that path's offending segments.** Today that is
two renderers — the denylist refusal (`_compose_denylist_refusal`) and the skip note
(`_annotate_skip`, which begins naming paths under FR4, grill P5). A future third channel
inherits the rule instead of re-opening the finding.

**Satisfiability is preserved.** Only segments that match a term source are masked; the rest
of the path, the line number and the short blob sha are untouched, so the operator can still
locate the offending file. Where nothing matches, output is **byte-identical** to today.

The `--redact` flag surface of the three FR8a verbs (`doctor`, `context list`,
`context show`) is untouched by this release.

**Acceptance**

- A6.1 A refusal whose blob path carries a synthetic private-name segment renders that
  segment masked; the line number and short sha are unchanged and the file remains locatable.
- A6.2 A refusal whose path matches nothing is byte-identical to the pre-release rendering
  (regression fixture).
- A6.3 The FR4 oversized note masks its path by the same rule (grill P5) — asserted
  separately from A6.1.
- A6.4 `cli/redact.py`'s existing behaviour is unchanged: `tests/unit/cli/test_redact_output.py`
  passes without modification to its assertions.
- A6.5 `core/redaction.py` is stdlib-only and performs no I/O; `core`'s file-I/O
  authorized-set contract test is unaffected.
- A6.6 The unmasked private segment appears in no field of any emitted string (the same
  property A5.2 of v0.9.0 pins for the term).

### FR7 — Pre-push shas are validated, and no sha can be parsed as a git option

`features/chokepoints/service.py#parse_push_stdin` validates both shas against
`^[0-9a-fA-F]{40}$|^[0-9a-fA-F]{64}$`, plus the all-zero deletion sentinel. A violation is
counted as a **malformed line**, reusing the fail-closed path that already exists — no new
message and no new branch.

`infrastructure/git_objects.py` closes the two remaining argv interpolation sites:
`_rev_list_candidates` appends `--` after the revision arguments, and
`_is_resolvable_commit` prefix-checks the sha before interpolating it into
`git cat-file -e {sha}^{commit}`.

**Acceptance**

- A7.1 The measured silent-no-op class — an option-shaped `local_sha` such as
  `--glob=refs/nonexistent` or `--branches=zzz` — refuses as a malformed line instead of
  producing a successful empty rev-list (unit, both shapes).
- A7.2 The all-zero deletion sentinel still parses and still passes with no verdict.
- A7.3 A 64-character (SHA-256) sha parses; a 39- or 41-character hex string does not.
- A7.4 `_rev_list_candidates`'s argv carries `--` after the revisions;
  `_is_resolvable_commit` rejects non-sha input before interpolation.
- A7.5 Gate behaviour on well-formed pushes is unchanged — the existing contract and
  integration suites pass untouched.

### FR8 — The batch parser fails typed, and a desynchronised stream aborts instead of fabricating

In `infrastructure/git_objects.py#_read_blobs`, the two paths that raise raw `ValueError`
past the module's typed contract — `out.index(b"\n", pos)` with no newline remaining, and
`int(size_str)` on a non-numeric header field — are wrapped and re-raised as
`GitObjectReadError` naming the desynchronisation and the object.

The existing desync branch changes behaviour: instead of yielding a fabricated
`decodable=False` object and **continuing** — after which `pos` points into content bytes and
every subsequent header parse is garbage, producing a stream of fabricated objects silently
counted as binary skips — it raises the typed error. A gate that has lost sync with git's
stream aborts; it does not invent.

**Acceptance**

- A8.1 A truncated batch stream and a non-numeric size field each surface as
  `GitObjectReadError` through the real adapter; no raw `ValueError` escapes the module.
- A8.2 A desynchronised stream aborts typed; no fabricated undecodable object is ever
  yielded, so no fabricated object can reach the skip counts.
- A8.3 The failure class produces the FR6-shaped refusal at the decision layer — it names
  the failure and names `git push --no-verify` — never a Python traceback.
- A8.4 The port contract in `core/protocols/git_object_reader.py` is honoured by
  construction again, pinned by the adapter-level test both v0.9.0 reviewers asked for.

### FR9 — The batch conversation's resident set is bounded by a constant

`infrastructure/git_objects.py` stops materialising a whole range's content in one buffer.
The shas to fetch are processed in **fixed-size chunks**, each chunk reusing the existing
batched conversation, so the peak resident set is `chunk_size × cap` for the content read and
`chunk_size × cap × 2` once FR2's prior side rides the same loop (ADR D8).

The single-conversation win is preserved: no per-blob subprocess returns (FR4's oversized
path is the one, rare, explicitly-scoped exception). The `_TIMEOUT_S` timeout semantics and
the typed-error conversion are unchanged, per chunk.

**Acceptance**

- A9.1 Peak resident bytes for the batch conversation are bounded by a constant, pinned by a
  test or a documented measurement over a multi-thousand-blob synthetic range.
- A9.2 The number of subprocess invocations grows with the number of **chunks**, not with the
  number of blobs; an under-cap range spawns no per-object read (contract test).
- A9.3 Timeout and typed-error semantics are unchanged: the existing
  `tests/unit/infrastructure/test_git_object_reader.py` cases pass without weakening.
- A9.4 A real-content fallback-range measurement is captured on the shipped code — blob
  count, bytes, read seconds, match seconds, s/MB and peak RSS — as the evidence for the
  closure memory correction (§5, entry #28), together with the recorded decision on
  match-throughput optimisation (adopt with before/after real-content numbers, or reject
  with a reason).
- A9.5 Timing on the ordinary `origin/develop..develop` range does not regress against the
  pre-release measurement of the same range.

### FR10 — The invariants this release must not break

Stated as an FR because four of them are exactly what a careless implementation of FR1–FR9
would cost.

1. **No sanctioned-terms / amnesty list anywhere.** The v0.9.0 A4.1 contract test — a source
   scan of `denylist_scan.py` for any `ALLOWLIST|SANCTIONED|AMNESTY|EXEMPT` assignment —
   stays green, unmodified. The amnesty derives from published git state; the FR3 baseline is
   a test assertion, never a scan input.
2. **The FROZEN↔scan invariant.** `specs/_archive/` is entered only by `git mv`, a rename
   reuses the blob, so an archived file never appears as a new object of a future range. The
   invariant is untouched and its existing integration proof stays green.
3. **Fail-closed everywhere.** Every new edge added by this release lands on refusal
   (FR2's three-way table, FR7's malformed-line reuse, FR8's typed abort). No new allow path
   is created.
4. **Ring purity.** `features/chokepoints/**` imports no `infrastructure` and spawns no
   subprocess; `cli/**` imports no `infrastructure`; `core/**` stays stdlib-pure and inside
   its file-I/O authorized set. All I/O reaches the decision logic through injected ports.
5. **Range scope.** The scan still reads only the objects the push would newly publish.
   Whole-tree scanning stays in the audit lane.

**Acceptance**

- A10.1 A4.1's contract test is unmodified and green.
- A10.2 The `git mv`-into-archive integration test is unmodified and green.
- A10.3 `lint-imports --config setup.cfg --no-cache` is green with no new `ignore_imports`
  entry; the ignore cap test is unmodified.
- A10.4 `grep -rn "AMNESTY\|SANCTIONED\|ALLOWLIST" dadaia_workspace/features/chokepoints/
  dadaia_workspace/infrastructure/git_objects.py` returns no assignment (exclusion set per
  §3 preamble).
- A10.5 `dadaia ci preflight` is green — ruff format, ruff check, mypy `--strict`,
  `lint-imports`, and the full pytest gate.

---

## 4. Out of scope (non-goals)

1. **Amnesty in the `--not --remotes` fallback range shape (ADR D7).** No amnesty is granted
   where no single published base exists; behaviour there is byte-identical to v0.9.0.
   Widening it is a deliberate future decision, not a defect of this release.
2. **Diff-scoped matching.** Whole-blob matching is the operator-ratified ruler
   (v0.9.0 code review, decision 1) and is not narrowed here. FR1 resolves the tension
   without touching the ruler.
3. **`internal-hostname` false-positive class / baseline v5 (D6, grill P11).** The structural
   fix (require hostname-ish context, or exclude chains whose preceding label is a
   capitalised identifier) is **evaluated and declined for this release**: no picked entry
   binds `infrastructure/data/privacy_baseline.json`, and the 29-blocker census contains zero
   `internal-hostname` hits, so it does not fall inside a picked intent's write set
   naturally. It stays with `baseline-carve-out-review-cadence` (#24, not picked). No
   baseline version bump happens here.
4. **`bugs-jsonl-whole-blob-per-append` (idea, not picked).** The append-cost driver that
   makes `specs/bugs/bugs.jsonl` republish itself whole on every append — and therefore
   dominates ordinary-range scan cost — is untouched. Its shape is genuinely open and needs
   `software-architect` input.
5. **`commit-message-scanning-residual` (#21, not picked).** Commit and tag-annotation bodies
   remain unscanned. It is the only unscanned channel on the push path and it is not this
   release's scope.
6. **`test-suite-remediation-stewardship` (#2, not picked).** The LARGE census (56 against a
   cap of 30) is not addressed. This release adds **zero** new e2e tests, so the census does
   not grow.
7. **No new CLI verb, no new doctor validator, no new hook, no new script.** The registry
   read is a container seam behind an existing verb.
8. **No AI-surface change.** No skill, persona, rule or law text is authored or edited. The
   quality-assurance doctrine's by-hand masking branch remains stated; FR6 simply stops it
   being the only branch (entry #23's third acceptance bullet).
9. **No change under `specs/_archive/**` (FROZEN).** Entry #28 is a forward correction in
   memory; the archived v0.9.0 CLOSURE is not edited, not reopened, and not annotated.
10. **No memory write in the DEFINITION phase.** The `sdd-gate-v3` atom is currently accurate
    for the shipped product (grill P10); this release changes the product rather than
    correcting an error, so every memory edit waits for CLOSURE (§5).

---

## 5. Memory files affected at closure

| File | Change | When |
|---|---|---|
| `specs/memory/product/sdd/sdd-gate-v3.md` | §"Push-Range Denylist Scan": the amnesty semantics as product truth (a value already published in the remote-reachable version of the same path never refuses; a new path or a new value still refuses; no amnesty in the fallback shape), the **surviving** invariants stated explicitly (no sanctioned-terms list anywhere; FROZEN↔rename unchanged), the term-layer description moved from directory-derived to **registry-derived**, the oversized-blob row rewritten from "skipped" to "first 5 MB scanned, remainder never fetched", the new fail-closed rows (prior-side git failure refuses; no-prior-content refuses), the chunk-bounded conversation, and the **#28 forward performance correction** (real-content fallback figures with the read/match split and s/MB, explicitly superseding the archived V14 synthetic figure) | **CLOSURE** |
| `specs/memory/architecture.md` | §"Context and SDD": the `GitObjectReader` port's widened contract (prior-side same-path resolution) and the new stdlib-pure `core/redaction.py` as the shared masking primitive consumed by both `cli/redact.py` and the gate renderers | **CLOSURE** |
| `specs/memory/quality-assurance.md` | §"Redaction At Authoring": the by-hand masking branch stops being the only branch — the gate's own render boundary now masks path segments; §"Satisfiable Diagnostics": the refusal's clearability statement gains the amnesty (an already-published value in the same path never demands a rewrite) | **CLOSURE** |
| `specs/memory/product/catalog.json` | regenerated **only** if a touched atom's `tldr`/`summary` frontmatter changed (`public/scripts/generate-memory-catalog.py`) | **CLOSURE** |
| `specs/memory/tech-stack.md` | no change — no dependency added or removed | — |
| `specs/memory/product/index.md` | no change — no product feature added or removed | — |

### Closure obligations (not implementation FRs)

- **#28 `closure-v14-perf-figure-correction` is a CLOSURE-phase memory forward-correction,
  not a code FR.** Its acceptance is satisfied in `CLOSURE.md` and in the `sdd-gate-v3` atom:
  the real-content measurement captured under A9.4 is recorded as product truth, explicitly
  superseding the archived V14 synthetic figure and citing the entry; the decision on
  match-throughput optimisation is recorded (adopted with before/after real-content numbers,
  or rejected with a reason); and `specs/_archive/**` is untouched. Entry #19's own memory
  note binds the same atom section — the PE lands **both** in one CLOSURE pass.
- **Disposition sweep.** All nine picked entries reach a terminal disposition at closure per
  `dd-release-closure`; the `## Dispositions` table records each with its evidence pointer.
- **Intake candidates.** Residuals discovered during implementation are **listed** in
  `CLOSURE.md` for the PM's operator-facing intake report. The closer creates no backlog
  entry (ADR #15).

---

## 6. Dependencies and risks

| # | Item | Status / mitigation |
|---|---|---|
| D-1 | `product-engineer` has no shell | every git, measurement and CLI step is an explicit TASKS entry owned by the dispatcher or `software-engineer` |
| D-2 | ADR D8 — FR9 is a **precondition** of FR2, not a sibling | encoded as the precondition chain T-110-05 → T-110-09 and as PLAN §3's execution order |
| D-3 | ADR D4 — FR5 lands after FR1, with the enumeration first | T-110-13's preconditions name T-110-11; A5.5 makes the enumeration an acceptance criterion |
| D-4 | FR6 must land with FR4 (grill P5) | A6.3 pins the skip-note masking; T-110-08 follows T-110-06 |
| D-5 | The release modifies the gate that gates its own push | standing privacy rule (§3); the FR3 sentinel is the mechanical backstop, and it now covers `tests/**` where this release adds fixtures |
| R1 | **The amnesty becomes a smuggling path.** A predicate keyed on the pattern rather than the matched value would amnesty a brand-new value of a previously-seen shape | FR1's single normative sentence + A1.3, the case the security review is asked to attack |
| R2 | **Memory blow-up.** FR2 doubles the resident set on top of an already unbounded buffer | FR9 lands first (D-2); A9.1 bounds the peak by a constant; A9.2 pins the invocation shape |
| R3 | **R3 weakened silently.** "Scan the first 5 MB" implemented inside the batch would convert *never fetched* into *never retained* | ADR D2-a's bounded per-object stream + A4.2's byte-count assertion |
| R4 | **The release regresses the leak axis while reporting a fix.** FR4's note names a path that FR6 has not yet masked | A6.3; the two are ordered and co-delivered |
| R5 | **The FR3 baseline reads as the forbidden list** | FR10.1 + A3.6 + the distinction stated in the test module's docstring; A4.1's contract test unmodified |
| R6 | **The widened FR5 layer converts historical content into fresh blockers** | D4 ordering + A5.5's enumeration + FR1 amnestying same-path prior-published values |
| R7 | **A fail-closed edge is softened while adding an amnesty** | FR2's three-way table; FR10.3; every new edge lands on refusal and is individually tested |
| R8 | **The own-identity subtraction misses the context name** and the gate refuses every push of this repository | A5.2's differing-name/slug fixture |
| R9 | **Test-budget creep** on a surface already owning seven modules | extend the existing modules; zero new e2e; at most one new unit module (grill P15); every test declares intent + size at birth |
| R10 | **The early-closed stream's expected non-zero exit is treated as a git failure**, turning every oversized blob into a refusal | FR4's explicit rule + A4.1/A4.2 exercising the path end to end |
| R11 | **Perf regression on the ordinary range** from chunking or the prior-side lookup | A9.5 measures the ordinary range before and after; A9.4 captures the fallback shape |

---

## 7. Traceability and provenance

| Entry (candidates.md #) | Provenance | Disposition in this release |
|---|---|---|
| `prior-published-term-amnesty` (#19) | v0.9.0 CLOSURE "Backlog returns", operator-ratified at the code-review round; sized by code-review round-2 handoff `2026-08-14T222609Z`; **pre-approved intake** (operator deferral, ratified at the v0.10.0 approval, §7/§8) | **picked — v0.11.0** · FR1, FR2, FR3 · terminal `DELIVERED — v0.11.0` at closure |
| `denylist-scan-skip-note-oversized-mislabel` (#20) | security ship handoff `2026-08-14T224700Z` (MEDIUM, CWE-778) + code-review round-2 (MEDIUM) + v0.9.0 CLOSURE QA-1; **APPROVED** at intake report #1 | **picked — v0.11.0** · FR4 (+FR6 for its note) |
| `registry-derived-foreign-name-set` (#22) | security ship handoff `2026-08-14T224700Z` (LOW, FR3 term source 3); **APPROVED** at intake report #1 | **picked — v0.11.0** · FR5, sequenced per D4 |
| `refusal-path-redaction` (#23) | v0.9.0 CLOSURE (LOW) + security ship handoff (CWE-532 residual); **APPROVED** at intake report #1 | **picked — v0.11.0** · FR6, **resolution A** (D1/D1-a) |
| `push-ref-sha-validation-git-argv-hardening` (#25) | security ship handoff (LOW, CWE-88/CWE-20); **APPROVED** at intake report #1 | **picked — v0.11.0** · FR7 |
| `git-objects-batch-parse-typed-error-boundary` (#26) | code-review round-2 (LOW) + security ship handoff (LOW, CWE-755); **APPROVED** at intake report #1 | **picked — v0.11.0** · FR8 |
| `git-objects-streamed-batch-reads` (#27) | security ship handoff (LOW, CWE-400); **APPROVED** at intake report #1 | **picked — v0.11.0** · FR9, promoted to a **precondition** by D8 |
| `self-scan-sentinel-integration-marker` (#29) | code-review round-2 (LOW); **APPROVED** at intake report #1 | **picked — v0.11.0** · FR3 (A3.5), folded into the sentinel task |
| `closure-v14-perf-figure-correction` (#28) | code-review round-2 (MEDIUM, evidence fidelity), routed by the reviewer as a forward correction; **APPROVED** at intake report #1 | **picked — v0.11.0** · **closure obligation** (§5), evidenced by A9.4 |
| `baseline-carve-out-review-cadence` (#24) | v0.9.0 CLOSURE + round-2 INFO | **not picked** — D6 evaluated and declined (§4.3); the `internal-hostname` structural fix stays here |
| `bugs-jsonl-whole-blob-per-append` (idea) | v0.9.0 CLOSURE | **not picked** (§4.4) — named as the cost driver behind the FR5 enumeration's two historical hits |
| `commit-message-scanning-residual` (#21) | v0.9.0 CLOSURE + reconciliation review | **not picked** (§4.5) |
| `test-suite-remediation-stewardship` (#2) | ADR #6 | **not picked** (§4.6); this release adds zero e2e tests |
| `python-env-interpreter-probe-hardening` (#9), `commit-paths-index-scope-hardening` (#18) | v0.5.1 / v0.5.2 security reviews | **not picked** — same Arm-B hardening lane, different surface (`git_subprocess.py`, interpreter probe); untouched here |
| The two v0.9.0-window LOW bugs | v0.9.0 CLOSURE "Registered during the release" | **already closed** — resolved by `hotfix/0.7.1`, merged at `d15bdf4e` (`resolved` events in `specs/bugs/bugs.jsonl` + the `0.7.1` mint). Nothing to pick: the ledger has zero open bugs |

**Purge-on-pick (ADR #14).** `specs/backlog/**` is `project-manager` surface. This section is
the provenance record the doctrine requires. In this pick the entry files are **flipped to
`status: picked` with a pick-provenance section rather than removed**, because nine entries
are picked at once and the PM's single-source `BACKLOG.md` consolidation (#31) has not yet
run — removing nine live files before that consolidation would destroy the index rows the
consolidation is being written against. Each entry's terminal `DELIVERED — v0.11.0`
disposition and its LEDGER row land at closure (`dd-release-closure` disposition sweep).
`specs/backlog/candidates.md` records the pick in the same commit.

**Version axis (ADR D5, ADR-2 split unchanged).** The SDD release id is `v0.11.0`; the
package version is minted **0.8.0** at ship (`pyproject.toml`, currently `0.7.1`), following
the precedent v0.9.0→0.6.0 and v0.10.0→0.7.0. `CHANGELOG.md` gains the `[0.8.0]` entry in the
same commit as the bump.

---

## 8. Approval

**Approved by the operator on 2026-08-15** (operator-delegated approval, goal directive),
**as written** — no scope change. SPEC, PLAN and TASKS all carry `**Status:** Aprovado`;
milestone (a) of the `dadaia-gitflow` contract may fire once the definition commit
(T-110-01) lands.

Ratified with the approval:

- **D1–D6 as given** (grill report, "ADRs recorded in this session"): #23 resolution A;
  #20's first-5-MB partial scan; the sentinel's `tests/**` extension with a shrinking
  baseline; amnesty-before-registry-set ordering with the enumeration first; release id
  `v0.11.0` / package `0.8.0`; and the D6 conditional, whose condition this SPEC records as
  **not met** (§4.3).
- **D1-a, D2-a, D7 and D8** — the four refinements the grill added. D1-a and D2-a are
  mechanism corrections that keep D1 and D2 intact. **D7** (no amnesty in the fallback range
  shape) and **D8** (#27 sequenced before #19) were taken by `product-engineer` in the
  conservative direction because they were not answerable by inspection and no pre-ruling
  covered them; both are **flagged** and either may be overridden by the operator without
  invalidating any other part of this release.
- **The pick-provenance form of purge-on-pick** (§7): nine entries flip to `status: picked`
  rather than being deleted, pending the #31 consolidation.
