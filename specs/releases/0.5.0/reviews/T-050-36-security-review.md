# T-050-36 — Security review of `feature/0.5.0` (diff-based, range `02eef219..HEAD`)

**Reviewer:** security-reviewer
**Date:** 2026-08-27
**Scan target:** the branch range `02eef219..HEAD` — 158 commits, 320 files,
+21 441 / −10 347 lines. Diff-based (`DADAIA.md` §7: the PR-gate security review is
diff-based only; a full scan lives solely in the audit lane).
**Snapshot reviewed:** `343acc3805b7e15c36cb98a640a389b26870b899`
**Verdict:** `APPROVED-PENDING-REKEY` — see §7.

> **This review does not key a verdict handoff.** The dispatcher will rewrite history
> before the first push (§2), which changes every sha in the range. No
> `specs/releases/0.5.0/verdicts/<sha>.handoff.json` is written here; a re-dispatch keys
> the APPROVED verdict to the final HEAD. HEAD moved three times during this review
> (concurrent implementer landing the histo-redaction fix chain) — every finding below
> was re-verified against the snapshot named above.

---

## 1. Scan summary

| Dimension | Tool / method | Result |
|---|---|---|
| Publication denylist | `dadaia ci push-gate-check` over the full range | **BLOCKED — 11 objects** (all historical; HEAD tree clean — §2) |
| Public-asset privacy | `dadaia public doctor` | `[ok] public-privacy`, `[ok] entities-derivation` |
| Secret patterns | grep over added lines: `(password\|passwd\|secret\|token\|api_key\|apikey\|private_key)\s*[:=]\s*["'][^"']{6,}` | **0 hits** |
| Private keys | grep `BEGIN (RSA\|EC\|OPENSSH) PRIVATE KEY` over the tree | 1 hit, synthetic fixture, pre-existing, outside the range |
| Dependency CVEs | `pip-audit` (workspace venv) | 32 findings, **0 in declared deps**, **0 new deps in the range** (§5) |
| Secret scanner | `gitleaks` / `trufflehog` | **not installed** — not run (§8) |
| OWASP/CWE pass | manual, on the new surfaces named in the task | 3 MEDIUM-cluster areas, no HIGH/CRITICAL |

**Totals:** CRITICAL 0 · HIGH 0 · MEDIUM 8 · LOW 9 · INFO 3.

**Bug-surface axis (FR24 / `dd-bug-registration` §5).** This range **reduces** the bug
surface of the touched features. `atomic_write` collapses eleven hand-kept
tmp-then-replace writers into one primitive with a scan-enforced sole-definition census
(`tests/unit/core/test_atomic_write_census.py`); `JsonlRecordStore` replaces
`jsonl_bug_store` + the v5 event fold + `BugService.archive`'s raw
file rewrite with one refuse-stale seam; `BugRecord` derives its redactable field set
from its own `dataclasses.field(metadata=...)`, retiring the hand-kept mirror that missed
a free-text field twice (T-043-23 → T-044-62); the `.gitignore` inversion retires a
whitelist shape with nine registered bug instances. The residual MEDIUMs below are
**gaps the consolidation did not close**, not new branches it added — with one exception,
F-07, which is a genuinely new insecure default introduced by the FR5 histo writer.

---

## 2. Publication-boundary status (`ci push-gate-check`)

Command run (range-scoped, exactly as the pre-push hook runs it):

```
printf 'refs/heads/feature/0.5.0 %s refs/heads/feature/0.5.0 0000000000000000000000000000000000000000\n' \
  "$(git rev-parse HEAD)" | <ws>/.dadaia/.venv/bin/dadaia ci push-gate-check   # exit 1
```

11 offending objects. Classification — **HEAD blob vs historical** — by comparing each
flagged blob id against `git rev-parse HEAD:<path>`, and by re-scanning the HEAD content
with the gate's own baseline patterns:

| # | Object | Term class | HEAD blob? | HEAD content clean? |
|---|---|---|---|---|
| 1 | `tests/unit/features/backlog/test_document.py:920` (`b2b78307f32b`) | operator denylist `t…n` | no (`a856ff091241`) | **yes** — fixture now uses a fictional term |
| 2 | `tests/unit/test_backlog_models.py:217` (`16a691fe752e`) | operator denylist `t…n` | no (`c1f3df8cacb3`) | **yes** — same fix |
| 3 | `specs/backlog/_archive/backlog_histo.jsonl:48` (`9bb2366e1481`) | operator denylist `t…n` | no (`179fdb3a3918`) | **yes** — re-redacted by the histo-writer fix |
| 4-6 | `specs/bugs/BUGS.jsonl:497` ×2, `:500` (`1a53838dd027`, `067f11a3711f`, `3122160426f5`) | baseline `email-address` | no (`273b21807548`) | **yes** — RFC-2606 reserved domain, gate-excluded |
| 7 | `tests/contract/test_hooks_publication_boundary.py:98` (`b57849bcd506`) | baseline `email-address` | no (`3e506a1a0ae8`) | **yes** — RFC-2606 reserved domain |
| 8 | `tests/contract/test_git_history_reader_log_added_lines.py:34` (`513284b73776`) | baseline `email-address` | no (`07a095ed6089`) | **yes** — RFC-2606 reserved domain |
| 9 | **commit message** of the newest commit, line 4 | operator denylist `t…n` | n/a | n/a |
| 10 | **commit message** `ffe1b00982e8`, line 5 | baseline `email-address` | n/a | n/a |
| 11 | **commit message** `e5fa1fbf2677`, line 3 | baseline `email-address` | n/a | n/a |

**Conclusion: the HEAD working tree carries zero denylist hits.** All 11 are historical
objects inside the unpushed range — exactly the shape a pre-push rewrite dissolves.

> **F-01 · MEDIUM · CWE-532 (Insertion of Sensitive Information into Log File) ·
> BLOCKING for the push, not for the code.**
> Three of the eleven are **commit messages**, one of them on the newest commit — the
> very commit that removed the real operator term from the test fixtures **names that
> term in its own message**. A rewrite that only rewrites blobs leaves the leak
> published. **Recommendation:** the planned rewrite must `--reword` (not merely
> `--amend` the tree of) every offending commit, and the operator must re-run
> `ci push-gate-check` to exit 0 **before** the first push. This report's verdict is
> conditional on that (§7).

---

## 3. OWASP / CWE findings — new surfaces

### 3.1 `core/atomic_write.py` (CAS) + `infrastructure/jsonl_record_store.py`

> **F-02 · MEDIUM · CWE-59 / CWE-61 (Link Following) · A17.1 symlink doctrine ·
> `dadaia_workspace/infrastructure/jsonl_record_store.py:83`**
> `append()` opens the ledger with `self._path.open("a", ...)`, which **follows a
> symlink** at the ledger path and appends to the link's target. `_read_text()`
> (`:181`, `Path.read_text`) follows on the read side too. The write path is
> inconsistent with itself: `update`/`remove` route through `atomic_write`, whose
> `os.replace(tmp, path)` **replaces the symlink** rather than following it — so the
> same store both writes *through* a planted link (append) and *destroys* it (update).
> The v0.4.5 A17.1 doctrine ("a symlinked destination is refused at every write site,
> with a fixture per site", carried by `dadaia-handoff-emitter` AG.1 by reference) is
> not applied at this new write site. Reachable ledger paths are attacker-influenceable
> in the weak sense only (an actor who can plant the symlink already has repo write) —
> hence MEDIUM, defence-in-depth.
> **Recommendation:** open with `os.open(path, os.O_WRONLY|os.O_APPEND|os.O_CREAT|os.O_NOFOLLOW, 0o600)`
> — the same single-atomic-open shape the v0.4.3 security review already imposed on
> `spec_context/service.py`'s scaffold write — and add the per-site fixture A17.1
> requires.

> **F-03 · LOW · CWE-276 (Incorrect Default Permissions) ·
> `dadaia_workspace/core/atomic_write.py:97,100-104`**
> The temp sibling is created with the process umask default (typically `0644`) and
> `preserve_mode` is opt-in and only copies from an **existing** target. A ledger
> created for the first time through `atomic_write` is therefore world-readable, and a
> `0600` target that is later replaced by a caller passing `preserve_mode=False` is
> silently widened. **Recommendation:** create the temp file with an explicit restrictive
> mode and make `preserve_mode` default `True`, or document the intended mode per
> caller.

> **F-04 · LOW · CWE-367 (TOCTOU) · `dadaia_workspace/core/atomic_write.py:105-113`**
> The `expected_previous` compare-then-swap narrows, but does not eliminate, the race:
> two writers can both observe an equal `current` and both reach `os.replace`, and the
> second silently wins. The docstring's "nothing but the comparison itself sits between
> the read and the swap" is accurate and the residual window is small, but the module
> claims "never last-write-wins, one race semantics: refuse-stale" — which holds
> *statistically*, not *by construction*. Accepted under the NO-LOCKS DOCTRINE.
> **Recommendation:** state the residual explicitly in the docstring (as
> `git_subprocess._commit` already does for its own CWE-367 residual), rather than
> asserting an absolute.

> **F-05 · LOW · CWE-778 / OWASP A09 (Insufficient Logging) ·
> `dadaia_workspace/infrastructure/jsonl_record_store.py:159-174,183-196`**
> `iter_records()` skips a malformed / non-object / unparseable line with a
> `logging.warning` on a module logger that no CLI entry point configures — so a bug
> record silently disappears from `bugs status`, `bugs stats` and the archive
> eligibility scan with **no operator-visible signal**. `append()` is a single
> unsynchronised `write()`; a short write (ENOSPC, signal) leaves a partial line that
> is then silently skipped forever. `specs doctor`'s SPEC-DOC-033 backstops the v5-line
> case but not the truncated-line case.
> **Recommendation:** surface a skipped-line count on stderr from the CLI verbs, the way
> `_print_coherence_warnings` already surfaces coherence gaps.

### 3.2 `infrastructure/git_subprocess.py::log_added_lines`

> **F-06 · LOW · CWE-88 (Argument Injection) ·
> `dadaia_workspace/infrastructure/git_subprocess.py:68,90,444-457`**
> `pathspec` reaches `git log`/`git show` **after `--`**, so a leading `-` cannot be
> parsed as an option — argument injection in the option sense is closed. It is **not**
> wrapped in git's `:(literal)` pathspec-magic escape, unlike every other pathspec in
> this module (`commit_paths` A10.3, `_stage_files_safe`), so a value containing
> `:(exclude)` / `:!` / `*` is reinterpreted as pathspec magic and the walk silently
> under-reports — directly contradicting the port's own contract, "a policy-relevant
> history walk never silently under-reports". Both current call sites pass a hardcoded
> constant (`"specs/bugs/"` at `features/bugs/service.py:260`; a test-only parameter at
> `features/bugs/migrate_v5.py:473`), so this is latent, not live.
> **Recommendation:** wrap as `f":(literal){pathspec}"` at all three call sites, matching
> A10.3.

> **F-07 · LOW · CWE-20 (Improper Input Validation) ·
> `dadaia_workspace/infrastructure/git_subprocess.py:78`**
> `line.startswith("+++")` excludes the diff file header, but also drops a genuine
> **content** line whose own text begins with `++` (rendered `+++…` in the diff). Same
> "never under-reports" contract. JSONL ledger lines start with `{`, so unreachable
> today. **Recommendation:** match the header as `"+++ "` (git always emits the space),
> or parse hunk boundaries.
>
> Byte-mode decoding (`_run_bytes` + `_decode_lines_strict`, `:26-59`) is **correct and
> commendable**: strict UTF-8, split on literal `b"\n"` only, undecodable lines skipped
> rather than replaced with U+FFFD. This closes the cp1252-on-Windows corruption class
> at a second, independent reader.

### 3.3 `features/bugs/service.py` + `cli/commands/bugs.py` — `bugs update --set`

**Can `--set` reach an immutable/core field? No.**
`BugRecord.apply_governance_update` (`core/models/bugs.py:297-315`) is a strict
three-way allowlist over field metadata: immutable-core is refused on any *change*
(`BugRecordImmutableFieldError`), write-once is refused on a differing re-set
(`BugRecordWriteOnceFieldSetError`), and an unknown field raises before `replace()` is
reached. `_parse_set_options` (`cli/commands/bugs.py:279-289`) never reaches an
attribute directly. **This seam holds.**

**Can `--set` inject control chars past the sanitizer? No, for governance fields.**
`BugService.apply_update` (`features/bugs/service.py:193-197`) redacts the **whole**
resulting record through `BugRecord.redact` → `core.redaction.redact_text`, whose
control/format strip runs *first*, before masking (`core/redaction.py:99`). The field set
is schema-derived from `dataclasses.field(metadata=...)`, so a newly added free-text
field is scrubbed the day it exists (A2.6/A2.10). **This seam holds.** Two gaps remain:

> **F-08 · MEDIUM · CWE-20 / OWASP A04 (Insecure Design) ·
> `dadaia_workspace/cli/commands/bugs.py:292-329`**
> `bugs append` validates the payload against `bug-record-v1` before writing
> (`:198`); **`bugs update` performs no schema validation at all** — its own docstring
> states "No content validation is added beyond the seam's own structural refusals".
> The schema constrains `status` to a 5-member enum and `diff_direction` to a 3-member
> enum, and `additionalProperties: false` — none of which `--set` honours. Concretely:
> `bugs update <id> --set status=<arbitrary>` writes an out-of-enum status; the record
> is then neither `open` (so it vanishes from the default `bugs status` view,
> `features/bugs/service.py:269`) nor in `TERMINAL_EVENTS` (so `archive` never touches
> it) — an open defect can be **hidden from the ledger view without ever being
> resolved**. Likewise `--set resolved_commit=<any string>` and `--set audited=<any
> string>` forge audit-trail evidence: the schema declares no `pattern` on either, and
> `BugService.resolved_commit` (`:255-256`) returns a stored value verbatim in
> preference to the git-derived one, so the forged cache wins over real history.
> **Recommendation:** run the same `_load_validator()` over the post-update record before
> the store write — one validator, two verbs — and add a 40-hex `pattern` to
> `resolved_commit`/`registration_commit` in `bug-record-v1.schema.json`.

> **F-09 · MEDIUM · CWE-117 (Improper Output Neutralization for Logs) / privacy ·
> `dadaia_workspace/core/models/bugs.py:240-242,405-407`; `core/models/backlog.py:319-324`**
> `_BUG_RECORD_REDACTABLE_FIELDS` excludes every field marked
> `metadata={"identity": True}` — `id`, `ts`, `reported_by` — and the schema confirms
> `x-redact: false` on exactly those three. **Neither `id` nor `reported_by` carries a
> schema `pattern`** (verified against `bug-record-v1.schema.json`), and both are free
> CLI strings (`--bug-id`, `--reported-by`, `cli/commands/bugs.py:136-138`). So an
> operator-local home path, an IPv4 literal, or a denylisted term passed as
> `--reported-by` is written to the ledger **unmasked**, and control/format characters in
> it are never stripped. FR6's stated invariant — "a leak is masked at the moment of
> writing rather than caught after it is committed" — has a three-field hole.
> `BacklogHistoRecord` reproduces the identical exemption on `id`/`ts`/`by`. Mitigated
> downstream by the push-time denylist scan, which is why this is MEDIUM and not HIGH.
> **Recommendation:** add a `^[a-z][a-z0-9-]*$` pattern to `id` and constrain
> `reported_by` to the known-agent set in the schema; or drop the redaction exemption and
> keep only `ts` exempt.

> **F-10 · LOW · CWE-436 (Interpretation Conflict) ·
> `dadaia_workspace/features/bugs/service.py:193-197`**
> `apply_update` redacts the **whole** record, immutable-core fields included, *after*
> `apply_governance_update` has already run its immutable check. If the operator
> denylist gains a term later, an unrelated governance update silently rewrites an
> immutable-core field's stored value — and `immutable_core_drift` (A2.7,
> `core/models/bugs.py:452`) will then report that legitimate re-redaction as tampering,
> indistinguishable from a hand-edit. **Recommendation:** document the precedence
> (privacy wins over immutability) at both seams, so the A2.7 detector's consumer can
> classify the signal.

### 3.4 `core/redaction.py` — the one masking primitive

> **F-11 · MEDIUM · CWE-176 (Improper Handling of Unicode Encoding) / CWE-179 ·
> `dadaia_workspace/core/redaction.py:75,99-106`**
> `_UNSAFE_FORMAT_CHARS_RE` strips C0/C1/DEL (minus TAB/LF/CR) plus U+2028/U+2029. It
> does **not** strip the Unicode **Cf (format)** category: zero-width space/non-joiner/
> joiner (U+200B-U+200D), the bidi marks and overrides (U+200E-U+200F, U+202A-U+202E,
> U+2066-U+2069), the invisible-operator block (U+2060-U+2064) or U+FEFF. The module's
> own stated rationale is that characters are *deleted rather than escaped* precisely so
> "a denylisted term an attacker interrupts with one of these bytes must re-join into a
> contiguous substring the masking pass can still catch" — a term split with U+200B does
> **not** re-join, so the write-time mask misses it. The push-time scan
> (`denylist_scan.operator_terms_match`) uses the same plain case-insensitive substring
> semantics (A6.3, deliberately), so **both layers of the privacy control miss the same
> input**. Bidi overrides additionally enable Trojan-Source-style misrendering (CWE-451)
> of a bug title in the panel and in any HTML report.
> **Recommendation:** extend the stripped class to `unicodedata.category(ch) == "Cf"`
> plus U+200B, in `redact_text` — one edit, both consumers inherit it.

> **F-12 · LOW · privacy coverage · `dadaia_workspace/core/redaction.py:49-51`**
> `redact_text` masks IPv4 and POSIX/Windows home-path usernames only. **IPv6 literals
> and internal hostnames are not masked at write time**, although the packaged baseline
> scan refuses both at the push boundary (`ipv6-literal`, `internal-hostname` in
> `privacy_baseline.json`). Write-time and push-time coverage therefore diverge — a
> record written with an IPv6 address reaches the ledger, then blocks the push.
> **Recommendation:** thread the packaged baseline patterns into `redact_text` the same
> way `denylist_terms` is threaded, so the two boundaries enforce one set.

### 3.5 `features/backlog/document.py` — the FR5 histo writer

The redaction seam itself is **correct at HEAD**: `backlog_exit` redacts through
`BacklogHistoRecord.redact(denylist_terms)` **before** `histo_store.append`
(`document.py:675-676`), and the committed `backlog_histo.jsonl` re-scans clean (§2 row 3).

> **F-13 · MEDIUM · CWE-1188 (Insecure Default Initialization) / CWE-665 ·
> `dadaia_workspace/features/backlog/document.py:645`**
> `denylist_terms: Sequence[tuple[str, str]] = ()` — the redaction argument **defaults to
> "no redaction"**, and `backlog_exit` currently has **zero production call sites**
> (`grep -rn "backlog_exit(" dadaia_workspace/` returns only the definition). The first
> real caller that omits the keyword silently reintroduces the exact bug this release
> just fixed (`backlog-histo-writer-skips-write-time-denylist-redaction`), with no
> error, no warning and no test failure. A docstring currently carries what the
> signature should carry. `BugService.__init__` (`features/bugs/service.py:124`) has the
> same shape, mitigated only by its single call site passing it.
> **Recommendation:** make `denylist_terms` a **required** keyword-only parameter on both
> — the type checker then enforces at every future call site what the docstring only
> requests. This is a strictly-simplifying change: it deletes a default, adds no branch.

> **F-14 · MEDIUM · CWE-367 (TOCTOU) / CWE-662 (Improper Synchronization) ·
> `dadaia_workspace/features/backlog/document.py:571-575` and `:615,629`**
> Both writers of `BACKLOG.md` — the operator's single-source demand queue — use a plain
> `read_text` → `write_text` pair: **non-atomic** (a crash or ENOSPC mid-write truncates
> the file) and with **no compare-and-swap**, so a concurrent writer's subsection is
> silently clobbered under the NO-LOCKS DOCTRINE. This is precisely the lost-update class
> `expected_previous` was introduced for in the JSONL ledgers this same release
> (`bugs-record-store-append-clobbers-concurrent-update-batch`), left unapplied on the
> governance document whose retention law is absolute (`DADAIA.md` §6: "Every item is
> retained"). The `test_atomic_write_census` contract does not catch it — it forbids a
> second *definition* of the tmp-then-replace idiom, not a plain `write_text`.
> **Recommendation:** route both through
> `atomic_write(target, new_text, expected_previous=text)` and surface
> `ConcurrentModificationError` to the caller. Also strictly simplifying — it removes
> two bespoke write paths.

> **F-15 · LOW · CWE-460 (Improper Cleanup on Thrown Exception) ·
> `dadaia_workspace/features/backlog/document.py:674-677`**
> `backlog_exit`'s docstring calls the removal + append an "atomic pair"; it is a
> sequence with no transaction. If `histo_store.append` raises after
> `remove_active_subsection` has already rewritten `BACKLOG.md`, the item leaves ACTIVE
> **with no histo record** — a retention-law violation with no trace.
> **Recommendation:** append the histo record first (it is idempotent by slug key), then
> remove the subsection; or catch and restore.

### 3.6 `.github/scripts/pr-verdict-check.sh` — the required PR gate

Verified correct and worth recording: `set -euo pipefail`; fail-closed canon derivation
with no fallback glob (`:115-137`); `RELEASE_ID` pinned to the **anchored**
canon-derived ERE `^v?[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z][0-9A-Za-z.]*)?$` before it
reaches a path, so no traversal shape survives (`:149-155`, verified by printing the
pattern); the handoff-sourced `metrics.commit_sha` pinned to 40-hex **before** it reaches
any git argv (`:203-206`) — closing the "HEAD collapses both checks into tautologies"
class; the `git diff` exit status checked explicitly rather than through a heredoc
(`:227-230`) — closing a real fail-open. The workflow wiring is sound too:
`permissions: contents: read`, action pinned by sha, `ref: …head.sha` (never the
synthetic merge ref), `fetch-depth: 0`, `pull_request` (not `pull_request_target`).

> **F-16 · MEDIUM · CWE-1220 (Insufficient Granularity of Access Control) ·
> `.github/scripts/pr-verdict-check.sh:169-174`; `dadaia_workspace/core/specs_version.py:55-65`**
> The canon docstring and the script header both assert that `specs/releases/_ideas/` is
> "never a root here **BY CONSTRUCTION** — it is not one of the two templates" (AS-15 /
> A6.3: "a freely-writable directory is never a trust root of a required check"). **The
> assertion does not hold.** `RELEASE_ID` is never set by `ci.yml`, so `RELEASE_GLOB`
> is always the literal `*`, and template 1 expands to
> `specs/releases/*/verdicts/*.handoff.json` — which pathname expansion matches against
> `specs/releases/_ideas/verdicts/…`. Verified empirically in an isolated scratch tree
> reproducing the exact expansion the script performs:
> ```
> CANDIDATE: specs/releases/0.5.0/verdicts/b.handoff.json
> CANDIDATE: specs/releases/_ideas/verdicts/a.handoff.json     <-- MUTATING root, accepted
> CANDIDATE: specs/releases/_archive/0.4.5/verdicts/c.handoff.json
> ```
> The `_ideas` protection is real only for the two-segment
> `_ideas/<release-id>/verdicts/` shape, not for a `verdicts/` directory placed directly
> under `_ideas/`. **Recommendation:** anchor the candidate discovery on
> `is_release_semver()` (reject any expanded segment that is not a canon release id)
> rather than relying on the glob shape, and add a fixture asserting an `_ideas`-rooted
> candidate is refused.

> **F-17 · MEDIUM · CWE-183 (Permissive List of Allowed Inputs) ·
> `.github/scripts/pr-verdict-check.sh:233-237`**
> The coverage exemption uses a bash `case` pattern whose `*` **crosses `/`**:
> `specs/releases/*/verdicts/*`. Any path with a `/verdicts/` segment anywhere under
> `specs/releases/` is therefore excused from the "nothing unreviewed landed since the
> review" proof — including source-shaped files. Verified:
> ```
> EXCUSED : specs/releases/_ideas/0.6.0/verdicts/x.json
> EXCUSED : specs/releases/0.5.0/reviews/verdicts/evil.py     <-- not evidence, still excused
> OFFENDER: specs/releases/0.5.0/SPEC.md
> ```
> The script's own comment acknowledges the `*`-crosses-`/` behaviour, but treats it only
> as the (correct) reason the archive shape already matches — never as the widening it
> also is. The second alternative, `specs/_archive/releases/*/verdicts/*`, is the
> **retired pre-v6 layout** and is now dead. **Recommendation:** replace with an anchored
> two-arm test (`specs/releases/<id>/verdicts/<file>` and
> `specs/releases/_archive/<id>/verdicts/<file>`, each with `<id>` matched against the
> canon), and drop the dead legacy arm.

> **F-18 · LOW · CWE-20 · `.github/scripts/pr-verdict-check.sh:83,213,219,227`**
> `PR_HEAD_SHA` is checked for presence (`:?`) but **never for shape**, while the
> handoff-sourced `sha` is pinned to 40-hex at `:203`. The T-044-46 S-1 comment explains
> at length why a symbolic value collapses the ancestor and diff checks into tautologies
> — the identical reasoning applies to the gate's own env input. Today it is supplied by
> `github.event.pull_request.head.sha` and is trustworthy; the asymmetry is the finding.
> **Recommendation:** apply the same `^[0-9a-fA-F]{40}$` check to `PR_HEAD_SHA` and exit
> non-zero on mismatch.

> **F-19 · MEDIUM · CWE-345 (Insufficient Verification of Data Authenticity) · design ·
> `.github/scripts/pr-verdict-check.sh:182-190`**
> The gate's entire trust basis is a **committed JSON file the PR author controls**. Any
> actor who can push to the feature branch can author
> `specs/releases/<id>/verdicts/<ancestor-sha>.handoff.json` with
> `agent: "security-reviewer"`, `verdict: "APPROVED"` and an ancestor sha, and the only
> path differing from the PR head is the verdict file itself — which the `case`
> exemption excuses (F-17) — so the gate passes. There is no signature, no provenance
> check, and no CODEOWNERS restriction on `specs/releases/**/verdicts/**`. The gate
> therefore reliably detects a **forgotten** review and provides no resistance to a
> **forged** one. That may well be the intended trust model, but the SPEC states the
> opposite property (AS-15/A6.3, "a freely-writable directory is never a trust root of a
> required check") for `_ideas/` specifically while leaving every other verdict root
> equally writable.
> **Recommendation (operator decision — §6):** either (a) document the trust model
> honestly as omission-detection, or (b) add a CODEOWNERS rule requiring a second
> approver for `specs/releases/**/verdicts/**`, or (c) have the gate verify a signed
> commit / a trusted-author check on the verdict file's own commit.

### 3.7 Hooks — did anything security-relevant leave the boundary?

**No.** Verified against the diff of
`dadaia_workspace/public/scripts/pre-commit-presence-gate.sh` and
`pre-push-ci-gate.sh`:

| Control | Before | After | Security impact |
|---|---|---|---|
| Range-scoped denylist scan | pre-push | **pre-push (unchanged)** | none — the privacy publication boundary is intact |
| Branch-name validation / `develop`+`main` push refusal | pre-push | **pre-push (unchanged)** | none |
| Fail-closed runner resolution | pre-push + pre-commit | **pre-push only** | none — pre-commit never enforced a privacy control |
| `backlog doctor` BLOCK | pre-commit | **deleted** (CI `backlog-doctor` job runs the unscoped sweep) | none — governance schema, not security |
| `ci preflight --quick` | pre-push | **deleted** (always-on rule; CI still gates) | none — quality, not security |

The pre-commit hook moving to `set -uo pipefail` + `|| true` + unconditional `exit 0`
**aligns the implementation with `DADAIA.md` §3** ("pre-commit warns and always allows")
and removes the `--no-verify` pressure that a commit-blocking gate created. This is a
**net reduction** in the bug surface of the chokepoint feature. Recorded as an INFO
observation only: `DADAIA.md` §7 still reads "Every `feature/{M.m.p}` push runs the local
CI preflight … before the branch contract even considers it", which now describes an
always-on agent rule rather than a hook guarantee — worth a wording pass at closure
(governance, `code-reviewer`/`product-engineer` lane, not a security finding).

### 3.8 `.gitignore` inversion — what became tracked

The inversion replaces a catch-all deny + per-extension whitelist (nine registered bug
instances) with per-area opt-in. Newly tracked-by-default areas: `specs/audits/**`,
`specs/ADRs/**`, `specs/bugs/_archive/**`, `specs/backlog/_archive/**`,
`specs/releases/_archive/**`, `specs/_archive/**`. Every file the range actually added
under these areas is a canonical governance artifact (`FINDINGS.jsonl`, `AUDIT.md`, 28
ADRs, three `*_histo.jsonl`) — **no secret-shaped file became tracked in this range**
(grep for secret-shaped assignments over added lines: 0 hits; `BEGIN … PRIVATE KEY`: 0
hits in the range).

> **F-20 · MEDIUM · CWE-538 (Insertion of Sensitive Information into Externally-Accessible File) ·
> `.gitignore:100-170`**
> The inversion's own comment claims "Only the narrow scratch/private-notes class the
> original catch-all ever actually hid (`local-notes.md`, `tmp/` working dirs) still gets
> denied, **per area**." The scratch denies were **not** carried to the newly opened
> areas. Verified with `git check-ignore`:
> ```
> TRACKED*: specs/audits/x/local-notes.md      TRACKED*: specs/audits/x/tmp/a.txt
> TRACKED*: specs/ADRs/local-notes.md          TRACKED*: specs/bugs/_archive/tmp/a.log
> TRACKED*: specs/backlog/_archive/local-notes.md
> TRACKED*: specs/_archive/x/tmp/a.txt         <-- `local-notes.md` was carried here, `tmp/` was not
> IGNORED : specs/releases/0.5.0/local-notes.md   IGNORED : specs/releases/0.5.0/tmp/a.txt
> ```
> Only `specs/releases/**` carries both denies. An agent writing scratch material into
> `specs/audits/<ts>/tmp/` — a shape `DADAIA.md` §5 makes natural — now has it staged by
> default. Root-level `.env`/`*.pem`/`*.key`/`credentials/` denies (`.gitignore:34-93`)
> still apply and are the reason this is MEDIUM rather than HIGH; a `secrets.env` under
> `specs/releases/0.5.0/` is nonetheless **tracked** (`*.env` is not denied — only `.env`
> and `.env.*`).
> **Recommendation:** add `local-notes.md` and `tmp/` denies to every newly opened area
> (one line each), and add a secret-shaped deny inside `specs/` (`*.env`, `*.pem`,
> `*.key`, `id_rsa*`) now that the whole tree is tracked-by-default.

### 3.9 `public/**` privacy and committed `specs/**` content

`dadaia public doctor` → `[ok] public-privacy` (operator-denylist mode, not the
degraded baseline-only mode). No consumer name, hostname, IP or operator path in the
`public/` payload.

> **F-21 · LOW · CWE-200 (Exposure of Sensitive Information) ·
> `specs/bugs/BUGS.jsonl:168,172,401`**
> Two records name a **private consumer game-project slug** in their `symptom` text, and
> one names the operator's **GitHub handle** (inside a `<handle>/dadaia-workspace` repo
> reference, so not an email and correctly not flagged by the `email-address` pattern).
> Neither token is in the operator denylist, so no boundary refuses them. This content is
> **migrated, not authored** by this range — both strings are present in the retired
> `specs/bugs/bugs.jsonl` at the range base (`git show 02eef219:specs/bugs/bugs.jsonl |
> grep -c` → 2 and 1 respectively) and are therefore already published. Recorded for the
> operator's denylist decision, not as a regression.

> **F-22 · LOW · CWE-200 · `specs/releases/0.5.0/reviews/S3-qa-close.md:144`**
> A review artifact added by this range spells the operator's local username as a literal
> in prose describing a path check. The baseline `home-abs-path` pattern does not fire
> (the token is not followed by a path segment), so no boundary refuses it.
> **Recommendation:** genericize to `<user>` at closure.

### 3.10 Panel (adjacent to a diff-touched line)

> **F-23 · LOW · CWE-79 (Stored XSS) · PRE-EXISTING, not introduced by this range ·
> `dadaia_workspace/features/panel/views/_md_render.py:167-169`**
> `_render_wikilink` interpolates the wikilink body into both the `href` attribute and
> the anchor text with **no HTML escaping**:
> `return f'<a href="{href}">{text}</a>'`. The inline pattern is `\[\[[^\]]+\]\]`, so any
> character except `]` reaches the sink — `"` included, which breaks out of the attribute
> without needing `]`. The module escapes everywhere else (`HTMLRenderer(escape=True)`,
> `mistune.util.escape` for mermaid fences) and its own header cites OWASP A03, which
> makes this the one unescaped sink. Mitigated by the panel's loopback bind, Host
> allowlist and sha256-pinned CSP `script-src` (which blocks an injected inline handler),
> and by memory atoms being operator-authored. The range modified the **adjacent** line
> (the `href` computation, for the v6 canon filename map), so the fix is one `escape()`
> call away while the file is already open.
> **Recommendation:** `escape(text)` in both interpolations.

---

## 4. Secrets detected

**None.** Scans run:

| Scan | Scope | Result |
|---|---|---|
| `(password\|passwd\|secret\|token\|api_key\|apikey\|private_key)\s*[:=]\s*["'][^"']{6,}` | added lines of the range | 0 hits |
| `BEGIN (RSA\|EC\|OPENSSH) PRIVATE KEY` | whole tree | 1 hit — `tests/unit/test_spec_context_service.py:277`, a synthetic `MIIE...` placeholder in a pre-existing fixture, **outside the range**; value `[REDACTED]`, no action |
| `secret-token` baseline pattern | committed tree | 4 hits, all in pre-existing test fixtures asserting the scanner's own behaviour, outside the range |
| operator denylist (18 terms) | committed `specs/**` JSONL/MD added by the range | 0 hits at HEAD (§2) |

No live credential appears anywhere in this range. **No escalation threshold was tripped.**

---

## 5. CVE findings

`pip-audit` over the workspace tool venv: **32 findings across 5 packages** — `pillow`
12.2.0 (17), `pip` 24.0 (7), `poetry` 1.8.3 (2), `dulwich` 0.21.7 (2), `msgpack` 1.1.2 (1).

**None affects a declared dependency of this project, and this range adds no dependency.**
The `pyproject.toml` diff changes only comments and a `max-complexity` rationale; the
`[tool.poetry.dependencies]` block is untouched. `pillow`/`msgpack`/`dulwich`/`poetry`/
`pip` are ambient tool-environment packages (the `pip`/`poetry`/`dulwich` trio is already
documented as R9-DEFERRED at `pyproject.toml:63-80` with required safe floors), and
a private consumer utility package (`<consumer-pkg>` 0.1.0) in the venv is operator-installed;
`grep` confirms it is referenced by **no** dadaia-workspace source, `pyproject.toml` or
`setup.cfg`.

**INFO:** two packages skipped as "not found on PyPI" — `dadaia-workspace` itself and the
same `<consumer-pkg>`. A locally-installed distribution whose name does not exist on PyPI is
the dependency-confusion shape; neither is resolved from an index by this project's
install path, so no action is required here, but the operator should keep the private
name off any public index resolution order.

**INFO:** `pillow` 12.2.0 with 17 open findings (fix 12.3.0) is the largest ambient
cluster. Outside this repo's lockfile control, same disposition as R9 — routed to the
operator, not to this PR.

---

## 6. Open items — operator decision required

| # | Item | Why it needs the operator |
|---|---|---|
| O-1 | **F-19** — the verdict gate's trust model | Choosing between "document as omission-detection", CODEOWNERS on `specs/releases/**/verdicts/**`, or signature verification is a governance decision, not a code fix. |
| O-2 | **F-21** — a private consumer project slug and the operator's GitHub handle in the committed bug ledger | Whether to add them to the operator denylist (which would then require re-redacting already-published history) is the operator's call. |
| O-3 | **F-01** — the history rewrite must reword three commit **messages**, not just blobs | The rewrite is the dispatcher's; the verdict in §7 is conditional on `ci push-gate-check` exiting 0 afterwards. |
| O-4 | **F-20** — whether `specs/**` should carry a secret-shaped deny now that it is tracked-by-default | A policy choice about what may ever live under `specs/`. |

---

## 7. Verdict

### `APPROVED-PENDING-REKEY`

**No blocking security or privacy finding stands against the HEAD tree.** Specifically,
none of the mandatory `REQUEST_CHANGES` triggers fires:

| Mandatory trigger | Status |
|---|---|
| Public-asset privacy violation | **clear** — `dadaia public doctor` → `[ok] public-privacy` |
| Secrets / tokens | **clear** — 0 hits over added lines and the tree |
| PII leakage | **clear at HEAD** — all 11 gate hits are historical (§2); F-21/F-22 are LOW and pre-existing/cosmetic |
| Auth / access-control gap | **no new one** — the `--set` seam's allowlist holds; F-16/F-17/F-19 are gaps in a *stated invariant* of an existing gate, not a new access path |
| Unsafe dependency addition | **clear** — zero dependencies added |
| Generated-file leakage | **clear** — the `.gitignore` inversion tracks only canonical governance artifacts in this range (F-20 is a forward-looking gap) |
| Deploy leakage | **clear** — CI workflow YAML unchanged; `permissions: contents: read`, sha-pinned actions, `pull_request` not `pull_request_target` |
| Consumer-specific data exposure | **pre-existing only** — F-21, already published at the range base |

**Conditions attached to the rekeyed APPROVE:**

1. **C-1 (blocking the push, not the code).** The planned history rewrite must clear all
   11 objects **including the three commit messages** (F-01), proven by
   `dadaia ci push-gate-check` exiting **0** on the rewritten range.
2. **C-2.** F-13 (`denylist_terms` default) and F-14 (non-atomic `BACKLOG.md` writes)
   should land before the `develop` PR — both are strictly-simplifying changes (delete a
   default; route two bespoke writers through the release's own primitive) that close
   recurrence paths for bugs this very release fixed. Not blocking; strongly recommended.
3. **C-3.** F-08, F-09, F-11, F-16, F-17, F-20 are routed to PM intake as backlog
   candidates if not taken in an `rc`.

**Bug-surface verdict (FR24).** **Reduced.** The consolidation removed writer count, race
surface and hand-kept mirrors; the residual MEDIUMs are pre-existing gaps the
consolidation newly made visible, with the single exception of F-13, whose fix is a
deletion.

---

## 8. Method and limitations

- **Diff-based**, per `DADAIA.md` §7. The whole-tree posture (`specs/_archive/**`,
  pre-existing test fixtures) is explicitly **out of scope** and belongs to the audit
  lane; where a whole-tree observation is recorded above it is labelled pre-existing.
- **`gitleaks` and `trufflehog` are not installed** on this host — the secret pass used
  the persona's grep patterns plus the packaged `privacy_baseline.json` `secret-token`
  pattern. A `gitleaks` run before the first push would be a cheap additional layer.
- **No exploit code was run.** F-16/F-17 were verified by reproducing bash's pathname-
  expansion and `case`-pattern semantics in an isolated scratch directory containing only
  empty files, never against this repository or its gate.
- **Raw values are redacted throughout** — denylist terms appear only in the gate's own
  masked `t…n` form, and no matched secret, email, path or private name is reproduced.
- **HEAD moved three times during the review** (concurrent implementer). Every finding was
  re-verified against `343acc3805b7e15c36cb98a640a389b26870b899`; the worktree was dirty
  with that implementer's in-flight changes, which are **not** part of this review.
