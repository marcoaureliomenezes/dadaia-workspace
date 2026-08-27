# FR23 firings — rulings on net-positive Arm-B fixes (0.5.0)

One entry per firing, appended in order. The S1 firing on the segment-wide diff stays in
its own file (`S1-FR23-firing.md`); this file collects the per-fix firings that follow it.

---

## Firing 1 — `8f7b5356` — `bugs-record-store-append-clobbers-concurrent-update-batch`

**Release:** 0.5.0 · **Arm:** B (bug, HIGH, audit F034) · **Author:** software-architect ·
**Date:** 2026-08-27
**Trigger:** the resolving commit is net-positive on production (+69/−18: `core/atomic_write.py`
+49/−4, `infrastructure/jsonl_record_store.py` +20/−14) — a net-positive Arm-B diff routes to
the architect before acceptance (standing order; `DADAIA.md` §7).
**Method:** no shell in this session. Every statement is from `Read`/`Grep` over the tree at
HEAD: `core/atomic_write.py`, `infrastructure/jsonl_record_store.py`,
`core/protocols/record_store.py`, `features/bugs/service.py:184-224`,
`cli/commands/bugs.py:305-329`, `tests/unit/core/test_atomic_write.py:159-221`,
`tests/unit/infrastructure/test_jsonl_record_store.py:101-243`,
`tests/contract/test_core_file_io_purity.py:57-64`, `hooks/_common.py:17-27`, the bug record
(`specs/bugs/BUGS.jsonl:509`) and the two ledger neighbours it cites (`:481`, `:493`), my own
`S1-AR1-ruling.md` §2 (b)(iii), `S1-FR23-firing.md` F4/A1, and the v0.4.5 `S2-AR1-ruling.md`.
The commit's diff was not viewed as a diff; the post-state was read whole and the pre-state is
reconstructed from the S1 firing's verification note ("refuse-stale by re-read bytes ✓
`jsonl_record_store.py:102-104`") and the bug record's `cause` field.

**Verdict: SOUND.** The compare-and-swap belongs in the one primitive; it is the structural fix,
not a puxadinho. Two LOW observations recorded for the next touch of each file; neither is a
blocking amendment.

---

### 0. Problem, constraints, prior art (architect-core-workflow)

**Core problem.** A whole-file rewrite built from a snapshot must never be swapped over content
the writer never saw — and the only place that guarantee can physically hold is the instruction
immediately before `os.replace`, which lives inside `atomic_write`, not in any caller.

**Constraints (from the tree).** `core/atomic_write.py` is bound by v0.4.5 AR-1: stdlib-only,
zero `dadaia_workspace.*` imports (not even a `core` sibling), stateless, temp cleanup on every
failure path for every parameter combination, one entry in `_AUTHORIZED_STEMS`. Forty-plus
call sites across `features/`, `infrastructure/` and migrations call it positionally or with
`preserve_mode`/`newline`/`ensure_parent` only. `hooks/_common.py` no longer imports it at all
(`:17-27` — `core.platform` and `core.session_env` only), so the hooks-latency law is preserved
by absence, not by argument. A2.9: one race semantics — refuse-stale, never last-write-wins;
D15/AS-16: a refusal is a non-zero exit naming "re-read and retry", never a block on a human.
NO-LOCKS doctrine: races are surfaced, never prevented — so a blocking file lock is not an
available design.

**Success criteria.** (1) A concurrent `O_APPEND` line landing at any point after the caller's
snapshot and before the swap is refused, not discarded — proven at the seam that failed
(`test_update_refuses_a_concurrent_append_that_lands_after_the_rereads_own_check`). (2) The
store owns zero re-read logic of its own. (3) Every existing `atomic_write` call site is
byte-compatible. (4) AR-1's four conditions on the primitive still hold.

**Assumptions made explicit.** (a) The residual window — the comparison itself, between
`read_text`/`read_bytes` and `os.replace` — is accepted as irreducible under a rename-based
swap without a file lock; it is microseconds, not "the whole serialization". (b) The ledger is
small enough (≈500 records) that reading the full file twice per update is not a cost that
matters; a digest would trade one `hashlib` import for no measurable gain.

**Prior art.** The AR-1 §0 survey (whole-document stores, CAS-by-version in `eventsourcing`,
SQLite) already chose "CAS in spirit, on the snapshot re-read immediately before the rewrite".
What this bug exposed is that "immediately before" was implemented one function call away
from the swap. The two structural candidates for closing that gap: (i) the check as an
optional parameter of the one primitive; (ii) a second primitive (`atomic_compare_and_write`)
or a context manager exposing a pre-swap hook. (ii) duplicates the temp/replace/cleanup idiom
— the exact divergence class the v0.4.5 bug `two-atomic-writers-leak-temp-file-on-injected-
os-replace-failure` (`BUGS.jsonl:481`) documents — or widens the primitive into a protocol
with more surface than any caller needs. (i) is one keyword, one `if`, zero new idiom copies.
(i) wins on Fit, Integration and Risk.

---

### 1. Is the CAS in the primitive the structural fix or a puxadinho?

**Structural — and it corrects a shape my own ruling specified.** `S1-AR1-ruling.md` §2
(b)(iii) said: "`update(id, mutate)` re-reads immediately before `atomic_write` and
refuses-stale by comparing the re-read bytes … to the snapshot". That wording placed the
re-read in the caller, one call before the swap; the S1 firing then verified that shape as ✓
and A1 replicated it into `remove`. The bug's `cause` field names the consequence exactly: the
check "ran in the CALLER … before invoking the separate, unconditional `atomic_write()` call,
leaving a gap for the whole duration `atomic_write` spent serializing content to its temp
sibling". The 507-update loss (`BUGS.jsonl:509` `symptom`) is that gap hit once per record by a
real second session.

The fix does what the standing order asks of a fix:

| Test | Evidence at HEAD |
|---|---|
| Removes a code path rather than adding one | The store's own re-read-and-compare is gone: `update` is snapshot (`:88`) → build lines → `atomic_write(..., expected_previous=before)` (`:117`); `remove` is identical (`:131`, `:152`). Two hand-kept copies of the check → zero; −14 lines in the store. |
| Puts the logic where it is physically correct | `atomic_write.py:103-111` performs the read after `tmp.write_text` (`:97-99`) and after `copymode` (`:100-102`); the only statement between the comparison and `os.replace` (`:112`) is the `raise`. `test_expected_previous_check_is_the_last_read_before_the_swap_not_before_the_temp_write` (`test_atomic_write.py:191-214`) pins the placement by injecting the concurrent write from inside the temp `write_text` itself — the check cannot silently drift earlier without turning that test RED. |
| One seam, one semantics | `ConcurrentModificationError` is the single stale signal; the store translates it once per method to the port's `StaleRecordWriteError` (`:118-119`, `:153-154`), the CLI reports it as exit 1 with the retry remedy (`bugs.py:318-328`). No new branch in the service, no retry loop, no flag, no sleep. |
| No cross-feature reach, no shared state | The primitive gained a stdlib exception class and one keyword; no import, no module-level state. |

The +49 in `core/atomic_write.py` is ≈35 lines of docstring (module `:17-27`, class `:40-48`,
function `:80-89`) plus the 14-line exception class and 9-line check. The executable growth of
the fix is ≈23 lines against ≈14 deleted — the "net-positive" label is mostly prose. That is
the acceptable shape of a net-positive Arm-B diff: a genuine capability the primitive lacked,
recorded once, at the one home.

**Root-cause gate (§0.1 gate 1): PASS.** The fix moves the check to the only place a
compare-then-swap can be adjacent to the swap. A caller-side "re-read again, closer" would have
been the workaround; it was not taken.

### 2. Does the primitive stay stateless, import-light, and byte-compatible?

| AR-1 (v0.4.5) condition | HEAD |
|---|---|
| Stdlib-only, zero package imports | `:32-36` — `contextlib`, `os`, `shutil`, `uuid`, `pathlib`. `ConcurrentModificationError(Exception)` imports nothing. ✓ |
| Stateless | No module-level mutable state; `replaced` is a local. ✓ |
| Temp cleanup on every failure path, every parameter combination | The `finally` at `:114-117` covers the new `raise` at `:111` — the refused swap unlinks the temp sibling; `test_expected_previous_mismatch_refuses_the_swap_and_leaves_the_live_content` asserts `_no_tmp_sibling_left` (`test_atomic_write.py:188`, `:214`). ✓ |
| One `_AUTHORIZED_STEMS` entry | `test_core_file_io_purity.py:64` — unchanged. ✓ |
| Hooks-latency law | Moot at HEAD (`hooks/_common.py` does not import the primitive) and preserved anyway: the added read path executes only when `expected_previous is not None`. ✓ |

**Byte-compatibility.** `expected_previous` is keyword-only with default `None` (`:56-63`);
the check is skipped entirely on `None` (`:103`). Every other call site in the grep — 43
production calls in `features/`, `infrastructure/` and migrations — passes no such keyword, so
their executed path is unchanged instruction-for-instruction. ✓

**Architecture-fidelity gate (§0.1 gate 2): PASS.** The module docstring (`:11-15`) restates
AR-1's conditions accurately and the layering claim ("pure `core` leaf — stdlib only") is
true at HEAD. The port docstring (`record_store.py:63-83`) says "re-reads the file
immediately before the rewrite" — now literally true.

### 3. Is the append path still race-benign, and does it need no CAS?

**Yes, and no.** `JsonlRecordStore.append` (`:79-84`) opens with `"a"` and writes one
newline-terminated line under a single `open` — `O_APPEND` positions each write at the live
end of file, so two concurrent appenders never overwrite each other and an appender never
discards anything. A CAS on append would be wrong by construction: append has no snapshot and
rewrites nothing; there is no stale state to refuse. The only loss an append can suffer is the
residual window in §0(a): an append landing between the primitive's comparison and its
`os.replace` is still swapped away. That window is the comparison instruction, not a
serialization; closing it would require a kernel lock (`fcntl`/`msvcrt` — platform-branched,
the Windows-compat bug class in memory) and would contradict the NO-LOCKS posture. Accepted as
the irreducible residual of a rename-based swap, and the primitive's docstring says so
honestly (`:24`: "nothing but the comparison itself sits between the read and the swap").

One theoretical non-atomicity noted, not actioned: a record line longer than the text
buffer could be flushed as more than one `write(2)` and interleave with a second appender.
Records are ≈1-2 KB against an 8 KB buffer; the redaction seam bounds free text. Not a finding.

### 4. Bug-surface direction with the ledger evidence (FR24 / `dd-bug-registration` §5)

**Touched feature:** `features/bugs` writer seam; **touched primitive:** `core/atomic_write`.

**Lineage read from the ledger and the rulings.**

| Step | What landed | What followed |
|---|---|---|
| v0.4.5 T-045-12 | 11 hand-kept atomic writers → 1 primitive (`BUGS.jsonl:481`, superseded by the consolidation) | no temp-leak recurrence; the primitive is the one home every later writer uses |
| 0.5.0 T-050-07/08 | `JsonlRecordStore` born; `update` refuse-stale implemented as a **caller-side** re-read before a separate `atomic_write` (AR-1 (b)(iii) wording; S1 firing verified ✓) | the gap the check could not see |
| S1 firing A1 | `remove` added with "the SAME read-snapshot / filter / re-read-compare / atomic_write shape" — the gap copied a second time | — |
| 2026-08-26 `BUGS.jsonl:493` | `mutation-baseline-wiring-test-flakes-under-concurrent-additive-writes` (LOW, tests): a second live session writing `specs/bugs`/`specs/backlog` during a suite run — proof that concurrent ADDITIVE writers on this ledger are the **normal** operating condition, not a hypothetical | fixed net-neutral in the test (assertion scoped), production untouched — correct class separation |
| 2026-08-27 `BUGS.jsonl:509` | 507 audited-field updates silently lost to one concurrent append (HIGH) | `8f7b5356`: check moved into the primitive; both caller copies deleted |

**Repetition check.** Same seam, same symptom class, twice in shape (`update`, then `remove`)
and once in production loss. The prior "fix" was not a fix — it was the initial design, and
the design's re-read was one call too early. The structural cause is now named in the ledger
(`root_cause: compare-then-swap TOCTOU gap between the caller's own re-read check and the
physically separate, later atomic_write() call`) and the fix collapses the two caller copies
into one check at the primitive. There is no puxadinho to undo.

**Direction: REDUCED.** Refuse-stale implementations on the ledger 2 → 0 in the store, 1 in
the primitive that every rewrite of any file may now reuse; the TOCTOU class is closed for the
whole serialization window on every present and future `expected_previous` caller, not for
the bugs ledger alone. The residual comparison-instruction window is documented, not hidden.

### 5. Observations (LOW — record, do not block)

#### [LOW] The comparison is text-mode for `str` snapshots; the ruling said bytes
Location: `dadaia_workspace/core/atomic_write.py:104-109`; `dadaia_workspace/infrastructure/jsonl_record_store.py:178-181`, `:117`, `:152`
Issue: The store snapshots with `read_text(encoding="utf-8")` and the primitive re-reads the same way, so both sides undergo universal-newline translation and compare consistently — the CAS is correct. But AR-1 (b)(iii) said "re-read **bytes** (or their digest)": two byte-different files that differ only in CR/LF compare equal in text mode. No writer in this tree produces such a difference, so this is a fidelity note, not a live hazard. Separately, the function docstring (`:83-84`) says the kinds of `expected_previous` and `content` "must match", while the code keys the read mode on `expected_previous` alone (`:104`) and would accept a `bytes` snapshot with `str` content — the docstring is stricter than the code.
Why it matters: a rule stated as "bytes" and implemented as "text" is the kind of drift the next reader inherits as truth.
Trade-off if fixed: the store snapshots `read_bytes()`, decodes for parsing, and passes the bytes as `expected_previous` — ≈3 lines, zero new imports; or the ruling's wording is relaxed to "content as read". Either is fine; the first is byte-exact and matches the docstring's intent once the "kinds must match" sentence is corrected to describe what the code does.
Recommendation: take the bytes snapshot in the store and align the docstring the next time either file is touched; not a 0.5.0 amendment.

#### [LOW] The bug record's `component` names a module that no longer exists
Location: `specs/bugs/BUGS.jsonl:509` — `component: "features/bugs/service.py + infrastructure/jsonl_bug_store.py (append vs update seam)"`
Issue: `jsonl_bug_store.py` was deleted at T-050-08; the seam is `infrastructure/jsonl_record_store.py`. `component` is an immutable core field under A2.2, so this stays as registered.
Recommendation: none on the record; FR14 pillar 1's provenance audit will read the resolving commit's touched paths (`core/atomic_write.py`, `infrastructure/jsonl_record_store.py`) as the authoritative component — which is why derived provenance, not the free-text field, is the audit's truth.

### 6. Gate record

| Gate | Verdict |
|---|---|
| Root-cause gate | **PASS** — check relocated to the only physically adjacent position; two caller copies deleted; no retry/sleep/flag/lock added |
| Architecture-fidelity gate | **PASS** — primitive still stdlib-only, stateless, single-entry in the I/O ratchet; port and adapter docstrings describe the executed path |
| Bug-surface axis (FR24) | **REDUCED** — evidence in §4 |

### 7. Disposition

**SOUND.** `8f7b5356` is accepted as the resolving commit; the `resolved` record at
`BUGS.jsonl:509` stands. No amendment gates S3/S4 on this firing. Two LOW notes above are
"fix when touching the file". No production code, tests, specs, or TASKS touched by this
session.
