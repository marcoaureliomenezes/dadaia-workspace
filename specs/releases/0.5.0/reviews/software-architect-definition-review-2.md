# software-architect — definition review 2 of release 0.5.0 (post-fold)

**Reviewed:** SPEC §9 fold (commit `b1d424b8`) and every section it points to — AS-1/4/13/14/15,
D-A, §1.1, §1.5, §7, §8, FR1, FR2, FR3 (A3.7/A3.10), FR4, FR8, FR11, FR13, FR14, FR15, §6 V19–V24;
TASKS T-050-04/06A/07/10/11/21A/42; PLAN §2 — against the live tree (`core/atomic_write.py`,
`core/specs_version.py`, `core/protocols/`, `infrastructure/jsonl_bug_store.py`,
`.github/scripts/pr-verdict-check.sh`, `specs/bugs/bugs.jsonl`, `specs/releases/v0.4.5/TASKS.md`),
rulings D1–D15 and the standing order. **Mode:** REVIEW, second pass.

## 1. SA-1 … SA-14

| id | Status | Evidence / what remains |
|---|---|---|
| SA-1 | **CLOSED** + one NEW-CONCERN | The seam is fixed upstream: T-045-20 is `[x]`, `bugs.jsonl:1006` carries `resolved` (2026-08-26T13:41Z), the reader splits on `"\n"` only (`jsonl_bug_store.py:89`). Precondition shape (AS-14/V23) is the right ownership. **NEW-CONCERN:** the T-045-20 fix *strips* U+2028/U+2029/U+0085 at the write seam (`core/models/bugs.py:248`, `_UNSAFE_FORMAT_CHARS_RE`) — so V23/A3.7 "a record carrying U+2028 round-trips **byte-identically**" is unsatisfiable by construction and goes RED against the very fix it verifies. Reword: "a field containing U+2028 is stripped at write, the file parses, `skipped: 0`". Also §1.1 row 4 still says "still open on this tree" — false since 13:41Z. |
| SA-2 | **PARTIAL** | Applied in FR2, A2.2/A2.7/A2.9, FR14 core-field measure, FR11 §3 row — correct shape. Missing: FR2 prose says the race loser's write is "*lost*, never a corrupt file", while A2.9 says the writer "*refuses* a stale rewrite". Those are two designs (lost-update vs compare-and-swap on the re-read snapshot). Keep A2.9's (refuse + caller retries), delete the "lost" sentence. |
| SA-3 | **PARTIAL** | AS-1(ii), FR8 shape 3, A8.2, FR14 single writer, §8.1 all consistent. One stale sentence survives: §7 traceability row "Open reconciliation … **the follow-up ledger commit is the cache**" contradicts AS-1. Delete it. |
| SA-4 | **CLOSED** + one NEW-CONCERN | 28 consumers enumerated (FR4, T-050-21A), fold at `core/release_events.py` called by hook/container/doctor, contract step in `S2` after T-050-21, 26+4 test census. **NEW-CONCERN:** T-050-21A adds `public/data/DADAIA.md` to its write set "by exception"; A11.1 is proven by *a grep asserting exactly one task carries that file* — the exception makes A11.1 RED by its own definition. Fix structurally: T-050-20 (FR11, already before T-050-21) removes the `ACTIVE.md` citation itself; T-050-21A does not touch `DADAIA.md`. |
| SA-5 | **CLOSED** | A2.5 generic `JsonlRecordStore` + record protocol, A3.10 pure derivation over `GitHistoryReader`, A13.4 "no module knows two shapes", PLAN §2, T-050-04 as confirmation. Name one more deletion: `core/protocols/bug_store.py` (the event-store protocol) retires with `jsonl_bug_store.py`. |
| SA-6 | **CLOSED** | AS-13, §7 disambiguation paragraph, T-050-42. |
| SA-7 | **CLOSED** | §1.1 row 1: one class, nine ids, three patched; ledger confirms 9 `gitignore` `reported` events. |
| SA-8 | **CLOSED** | Zero-hit grep for `commit_granularity` as a field across SPEC/PLAN/TASKS; D-A withdraws it explicitly. |
| SA-9 | **CLOSED** | FR2 vocabulary has no `picked`; FR8 shape 5 "the pick is the commit". |
| SA-10 | **CLOSED** | FR4: seven kinds, envelope `{ts, event, agent, data}`, `session_id` dropped. |
| SA-11 | **rejected — accepted on the merits** | see §2 |
| SA-12 | **CLOSED** | A2.5 legacy reader, A4.4 parser fates, FR15 extended scope (`AUDIT_DIR_NAME_RE`, `RELEASE_ARTIFACTS`, `gate_policy.py` comment), V19. |
| SA-13 | **CLOSED** | FR14 pillar 1 interval measure; §1.1 certify row carries the 1-second sibling. |
| SA-14 | **CLOSED** | FR4 `implemented` = QA-close sha; T-050-42 appends it before the merge. |

## 2. SA-11 — the `--recipe` rejection, judged

The product-engineer's argument holds. My S4 cut conflated "no new surface" with "no new
flag"; the anti-slop criterion that actually binds is D15 (no blocker, no mutating precondition
to learn what to do) plus single-source. Making an agent run `specs upgrade` — a **mutating**
verb — to read the steps it must perform by hand is the worse shape, and `doctor` is already
the read-only reporter. **Accepted**, with one advisory condition on A1.3 so the flag cannot
become a second knowledge store: `--recipe` must be a *rendering of the same finding objects*
`specs doctor --json` emits (recipe text attached per finding), never a separate step table
that can drift from the findings. Not a REWORK item.

## 3. New concern introduced by the fold — FR1 boundary 2 / AS-15

Location: SPEC FR1 boundary 2, T-050-06A (b); `core/specs_version.py:38`
(`RELEASE_SEMVER_RE = ^v\d+…`, documented as "the ONE release-id canon every public entry
point validates against"); consumers `features/specs/scaffolder.py`, `features/specs/doctor_release.py`,
`features/spec_artifacts/new_artifacts.py`, identity contract `tests/contract/test_release_semver_canon.py`;
ledger `lifecycle-accepts-noncanonical-release-id` (lines 769–770, component = this module).
Issue: (a) canon v6 moves live/archived ids to **bare** semver, so the canon constant the
gate is told to derive from must itself flip from `^v…` to bare — that flip and its four
consumers, its identity test and the bug-lifecycle `resolved_release` validator are in **no**
FR text and **not** in T-050-06A's write set (only `core/specs_version.py` + `tests/contract/**`).
This is the FR4-class omission (consumer set understated) on the exact seam whose third
firing AS-15 names. (b) `pr-verdict-check.sh` is bash; "derive from `core/specs_version.py`"
names no mechanism (a `python -c` import in CI, or a JSON export the gate reads). Unnamed,
an implementer will copy the regex into the script — the hard-coded shape again.
Recommendation: FR1 states the bare-semver flip of `RELEASE_SEMVER_RE` with its enumerated
consumers (same discipline as FR4's 28), adds them to T-050-06A's write set or a T-050-06B,
and names the derivation mechanism (recommended: `python -m dadaia_workspace.core.specs_version --gate-json`
style export is *new CLI surface*; prefer a one-line `python -c` import in the script,
tested by V20). Trade-off: one paragraph, ~4 write-set lines; zero code shape change.

## 4. Gates

- **Root-cause gate: PASS.** The U+2028 seam is closed at its cause (reader + write-time strip,
  one seam, ledger 984→1006 with RED/GREEN evidence); the verdict-gate fix derives from the
  canon instead of patching a glob (third firing named, AS-15); FR9 deletes the two registered
  hook causes (ledger 159/170 → 186/187); no puxadinho found in the folded text — AS-1(ii),
  no `picked`, no shape 3b, seven kinds, generic store.
- **Architecture-fidelity gate: FAIL (narrow).** Layers, abstractions and placement are now
  right (PLAN §2: `core` stdlib-pure fold, protocol-injected git, no new accepted edge). The
  one misrepresentation is §3 above: the canon the CI gate derives from is described as
  already bare-semver-capable while the live constant, its identity test and four consumers
  mandate `v` — an understated consumer set on a boundary this release explicitly owns.

## 5. Verdict — REWORK (targeted, textual; no re-scoping)

1. FR1/T-050-06A: enumerate the `RELEASE_SEMVER_RE` bare-semver flip's consumers and name the
   bash→canon derivation mechanism (§3).
2. V23/A3.7/T-050-10: replace "round-trips byte-identically" with the strip semantics the
   T-045-20 fix actually has; fix §1.1 row 4 "still open on this tree".
3. A11.1 vs T-050-21A: move the `DADAIA.md` `ACTIVE.md`-citation edit into T-050-20; drop the
   Tier-1 exception.
4. FR2 vs A2.9: one race semantics (refuse-stale + retry); delete the "loser's write is lost"
   sentence.
5. Housekeeping: delete §7's "follow-up ledger commit is the cache" row text; name
   `core/protocols/bug_store.py` in the A2.5 deletion list; V4's absolute "490/490" → "every
   record at branch cut" (the ledger already reads 503 `reported` / 473 `resolved` events).

Items 2–5 are sentences; item 1 is one paragraph plus write-set lines. With them applied the
trio is ready for `Em revisão`; without item 1 the ship PR can fail its required check a
third time, and without item 2 FR3 is blocked by a validation that cannot pass.

## 6. Bug-surface statement (ledger evidence)

**Reduces**, on every touched feature but two rulings-mandated additions. Evidence:
hooks — the two registered causes (`precommit-backlog-doctor-blocks-unrelated-commits`,
`backlog-doctor-blocks-consumed-item-refactor-commit`) are deleted, none added (FR9, V9/V10
negative LOC). Bugs feature — the event fold that produced
`bugs-append-accepts-second-terminal-event` (826/834) is deleted; the U+2028 family (984/1006)
is closed upstream and the record model removes its amplification only, stated honestly now.
CI gate — `verdict-gate-cannot-resolve-evidence-after-release-archive` (996/997) moves from
glob-patch to canon-derivation (conditional on item 1). Specs doctor — prose regexes retire
(FR15). AI surface — the stale-citation class (`dadaia-task-manager-stale-workspace-protocol-citation`,
957/1001) gets a contract test (FR10). Governance paths — nine `gitignore` instances, one
class, inverted at the source (FR1). **Increases**: release state (FR4 schema + fold, D3/D7)
and audits (FR13 folder + schema, D5) — both operator rulings, both with a single reader and
a single writer seam; always-on tokens (FR11), measured by V12 rather than assumed.
