# QA Close — Segment S5 (the bug sweep and branch hygiene)

**Release:** v0.4.4 · **Segment:** S5 · **Task:** T-044-42 (QA verdict)
**Author:** qa-engineer · **Date:** 2026-08-24
**Scope:** FR22 (T-044-61), FR23 (T-044-62), the eight Arm-B bug fixes (T-044-33…40),
FR20 branch hygiene (T-044-41), and the four FR23 architect rulings this segment fired.
Commits audited: `170b0e61` `8d94bbe7` `f17bf6cd` `f3b95a4d` `35fe5cc8` `5af53a7c`
`6a563961` `d5f50068` `7d9e8382` `d3346382` `c10d4a49` `d9bb8004` `69cb34c5` `19f9ad9f`
`4ae47780` `46ed4188` `e89b6372`, plus en-route defang commit `f594fafb`. All on
`feature/0.4.4`, none pushed.

**Verdict: APPROVE.**

Every one of the eight sweep bugs is independently confirmed `resolved` with the full
FR23 three-field evidence, and every named pinning test re-runs GREEN by name on this
session, not read off the implementer's report. The FR23 gate itself was re-proven live
against a throwaway tmp specs directory (never the real ledger): a `resolved` append
missing one field is refused, naming exactly that field, and nothing is written; a
well-formed append is accepted on the first try (A23.6 re-proof at close). T-044-41's
branch hygiene is independently re-verified against `origin` right now: heads = `main` +
`develop` only (`feature/0.4.4` is not pushed — arrives at rc-1, per contract), 50
`archive/*` tags on origin, 3 spot-checked tags resolve to real commits, local branches
are exactly the three permitted patterns, local `hotfix/0.4.3` is gone. Full gates are
green: `ruff format --check` (715 files, clean), `ruff check --no-cache` (clean),
`mypy --strict` (273 source files, 0 issues), full suite `2803 passed, 4 skipped
(environment-gated), 0 failed`.

Six bugs remain OPEN, all consistent with what this segment's own record predicted or
outside this segment's scope entirely — none blocks this verdict. §4 records them and
the accumulated intake candidates in full for the PM's intake feed.

---

## 1. Per-bug table — FR23 evidence, pinning-test re-run, bug-surface delta

| Task | Bug (severity) | `resolved` FR23 fields | Pinning test re-run (this session) | Bug-surface delta |
|---|---|---|---|---|
| T-044-33 | `backlog-doctor-silent-on-duplicate-top-level-sections` (MEDIUM) | loop/seam/diff all present, `net-positive` | `test_document.py::test_duplicate_top_level_active_heading_yields_document_error_and_parses_both_bodies` — PASS | **REDUCED** — architect Firing 1, verdict SOUND: silent-drop/first-wins path (a duplicated `## ACTIVE`/`## LEDGER` passed `backlog doctor` clean) closed at the one owning parser seam; no puxadinho, doctor.py untouched. |
| T-044-34 | `backlog-doctor-rejects-deferred-status-documented-by-skill` (LOW) | loop/seam/diff all present, `net-negative` | `test_backlog_status_vocabulary_contract.py::test_skill_active_status_enumeration_excludes_terminal_disposition_tokens` — PASS | **REDUCED** — one contradictory statement deleted from the skill (doctor's own BL-STALE check was already correct); 1-line net-negative fix, no architect firing required. |
| T-044-35 | `atomic-writer-drift-guard-is-brittle-and-covers-only-two-of-eight-writers` (LOW) | loop/seam/diff all present, `net-positive` | full `test_migration_symlink_hardening.py` — PASS (32 battery items + siblings) | **REDUCED** — architect Firing 2, verdict SOUND: a brittle 2-of-8 text-equality comparator (4 documented failure modes) deleted at root, replaced by a 32-item behavioural battery over all 8 writers; the battery's first run surfaced a real production gap, routed to a new bug rather than asserted away (see §4). Coverage-growth exception earned on all stewardship counts. |
| T-044-36 | `crlf-fixture-makes-a-windows-assertion-pass-for-the-wrong-reason` (LOW) | loop/seam/diff all present, `net-neutral` | `test_migration_symlink_hardening.py::test_repair_preserves_file_mode_and_newlines` — PASS (part of the full-file run above) | **REDUCED** — one un-pinned fixture write (`newline=` unspecified) fixed so the assertion can only fail for the reason it names; 1-line net-neutral change, no architect firing required. |
| T-044-37 | `migration-normalises-crlf-atoms-to-lf-contradicting-its-byte-preserve-wording` (LOW) | loop/seam/diff all present, `net-neutral` | `test_frontmatter_keys.py::test_migration_normalises_a_crlf_atom_to_lf_on_disk` — PASS | **REDUCED** — docstring-only fix (0 executable lines changed); a documentation/behavior mismatch that could mislead a future contributor into "fixing" already-correct behavior is closed. |
| T-044-38 | `no-ratchet-against-frozen-clock-tests-that-age-fixtures-by-the-real-clock` (LOW) | loop/seam/diff all present, `net-positive` (+294/-0) | full `test_frozen_clock_aging_ratchet.py` — PASS | **REDUCED** — architect Firing 3, verdict SOUND (a third, distinct exception category: mechanism growth, earned on 4 stated conditions). Guards the class of latent frozen-clock time bombs (the v0.4.3 midnight-UTC incident) at authoring time; the underlying defect was already root-cause-fixed in v0.4.3 — this is the guard, not a re-fix. Zero live violations at HEAD across 10 known aging sites. |
| T-044-39 | `read-only-atom-honouring-is-advisory-and-root-bypasses-it` (LOW) | loop/seam/diff all present, `net-neutral` (+4/-5) | `test_retired_frontmatter_keys.py::test_read_only_atom_needing_no_change_stays_silent` + `test_read_only_atom_needing_change_is_skipped_with_note`; same pair in `test_agent_tier_frontmatter.py` — 4/4 PASS | **REDUCED** — a false "read-only — skipped" note that a clean read-only atom never earned is gone (pure reorder past the no-change determination); no new branch, no second permission probe. **Process note:** unlike every sibling task this segment, the TASKS.md entry for T-044-39 carries no inline `**Resolution:**` narrative block — only the `[x]` flip. The full evidence lives in the commit body and the `bugs.jsonl` `resolved` event (both verified present and complete above), so this is a documentation-consistency gap, not a missing-evidence gap; flagged non-blocking below. |
| T-044-40 | `symlinked-specs-root-is-followed-by-migration-and-repair` (LOW) | loop/seam/diff all present, `net-positive` (+22/-2) | `test_specs_resolver.py::test_resolve_specs_dir_refuses_a_symlinked_explicit_root` + `test_cli_specs_symlinked_root_refused.py` (both entry points) — 3/3 PASS | **REDUCED** — architect Firing 4, verdict SOUND: closes the last unguarded rung of the CWE-59 blind-`.resolve()` class this ledger has tracked since v0.1.11 (symlinked-venv escape), at the one owning resolver seam, with uniform refusal (no per-verb special case). One residual named and routed to intake (`specs init`'s separate explicit-path lane), not a defect of this diff. |

**Architect firings this segment: 4 of 4 SOUND**, per `S5-FR23-first-firing-ruling.md`
(reviewer: `software-architect`, all four independently re-read this session): Firing 1
(T-044-33), Firing 2 (T-044-35), Firing 3 (T-044-38), Firing 4 (T-044-40). No REJECT, no
puxadinho detected in any of the four. The other four bugs (T-044-34/36/37/39) carried
net-negative or net-neutral diffs and correctly never triggered the gate.

**T-044-61 (FR22 method) and T-044-62 (FR23 gate) — enabling infrastructure, not bugs.**
Both `[x]`, both independently re-verified functional this session: the FR23 gate is
live and correctly wired (§2); `dd-bug-fix`'s method shape (phases ending in a checkable
"Done when") is what every one of the eight `resolved` events above was produced
against — every one carries all three required fields on the first attempt recorded in
the ledger, consistent with A22.1–A22.5/A23.1–A23.6 holding in practice, not merely on
paper.

---

## 2. FR23 gate — live re-proof (A23.6), against a throwaway tmp specs dir

Never run against the live ledger. Fresh empty directory, precondition `reported` event
appended first (required before `resolved`):

```
$ dadaia bugs append --specs-dir <tmp-dir> --bug-id fr23-live-verify-probe \
    --event resolved --reported-by qa-engineer --release v0.4.4 \
    --evidence-loop "…" --evidence-seam "…"
    # --evidence-diff intentionally omitted
[error] resolved requires three checkable evidence fields (FR23 resolution law);
missing: --evidence-diff (the diff direction on the touched feature: prefix
'net-negative:'/'net-positive:'/'net-neutral:', lines/branches/flags added vs removed)
exit=1
```

Ledger line count after the refused attempt: unchanged (1 line — only the precondition
`reported` event; nothing written for the refused `resolved`).

```
$ dadaia bugs append --specs-dir <tmp-dir> --bug-id fr23-live-verify-probe \
    --event resolved --reported-by qa-engineer --release v0.4.4 \
    --evidence-loop "…" --evidence-seam "…" \
    --evidence-diff "net-neutral: throwaway probe file, +0/-0, no production feature touched"
[ok] appended resolved for fr23-live-verify-probe -> <tmp-dir>/bugs/bugs.jsonl
exit=0
```

Accepted on the **first try** once well-formed. Both checks pass: refusal names the
exact missing field and writes nothing; a complete event is satisfiable at HEAD with no
bypass flag. Tmp dir deleted after the probe; the real `specs/bugs/bugs.jsonl` was never
touched by this verification. **A23.6 re-proof: PASS.**

---

## 3. T-044-41 / FR20 — branch hygiene, independently re-verified

| Check | Command | Result |
|---|---|---|
| A20.2 — `origin` carries only `main`, `develop`, `feature/0.4.4`, archive tags | `git fetch --all --prune`; `git ls-remote --heads origin` | Two heads: `develop`, `main`. `feature/0.4.4` is intentionally not yet pushed — it arrives at rc-1, per the branch contract; consistent, not a gap. |
| A20.2 (tag count) | `git ls-remote --tags origin \| grep -c 'archive/'` | **50** |
| A20.1 — reachability, spot-checked | `git rev-parse archive/feature/0.4.2`, `archive/chore/v0.1.75-closure`, `archive/feature/pi-fourth-harness-v1` | All three resolve to real commit shas (lightweight tags), matching `refs/tags/<name>^{commit}` exactly. |
| A20.3 — no local branch outside the three permitted patterns | `git branch -a` | `develop`, `feature/0.4.4`, `main` only (plus `remotes/origin/*` mirrors of the same three). `hotfix/0.4.3` (local) confirmed **absent** — `git rev-parse --verify hotfix/0.4.3` fails as expected. |
| V10 evidence files | `.dadaia/tmp/claude/20260824/` | `T-044-41-V10-before.txt` and `T-044-41-V10-after.txt` both present. BEFORE lists 49 non-main/develop origin branches (7 `chore/*`, the 8 named-scope `feature/*` slop branches, plus a broader population this session's own task description under-names: `dependabot/*` ×5, additional `feature/v0.1.*`/`v0.2.*`/`v0.3.0`/`v0.4.0`, `fix/*` ×2, `hardening/*`, `hotfix/*` ×2, `release/*` ×3, `work/*`). AFTER shows origin carrying `main`+`develop` only and 50 archive tags. |

**Honest observation on V10 (not blocking).** T-044-41's own TASKS.md description names
15 branches by exact slug (`chore/*` ×7 + 8 `feature/*`), but the actual before/after
evidence shows the sweep also archived-and-deleted ~34 additional pre-existing slop
branches on `origin` that predate this segment (dependabot branches, older `feature/v0.1.x`
and `release/*` branches, etc.) — necessary to satisfy A20.2's own invariant ("origin
carries main/develop/feature/0.4.4/archive tags only"), which is a strictly broader
claim than the named-branch list. Every deleted branch is tag-reachable (A20.1, spot-checked
above) and no evidence of an improper deletion was found; recorded here because the
task's own prose under-described its true blast radius, and a future reader diffing the
task description against V10 should not read that as a discrepancy in the execution.

**A20.1–A20.4: PASS**, independently re-verified, not read off the implementer's report.

---

## 4. Honest findings — open bugs and intake candidates (PM intake feed, full record)

### 4.1 Open bugs at close (`dadaia bugs status --all`, re-run this session)

| Bug | Severity | In S5 scope? | Note |
|---|---|---|---|
| `two-atomic-writers-leak-temp-file-on-injected-os-replace-failure` | LOW | Discovered BY T-044-35 (S5), left OPEN by design | Registered and pinned as CURRENT (leaking) behaviour by the T-044-35 battery, not silently asserted away (architect Firing 2 check (b), verdict: this is characterization done correctly and is anti-hiding by construction — the pinning test is self-destructing in the fix direction). Production fix is explicitly out of T-044-35's tests-only write set. Consolidation is the intake candidate below (§4.2), not this bug's own fix — the architect ruling recommends the structural fix subsumes this bug rather than a two-call-site patch. |
| `dadaia-task-manager-stale-workspace-protocol-citation` | LOW | Foreign — reported by `qa-engineer`, unrelated to any S5 task's write set | `dadaia-task-manager/SKILL.md` cites `DADAIA.md` §1 for SDD-gate path-class content that actually lives at §3 — a stale cross-reference, not a behavioral defect. |
| `sdd-gate-blocks-fresh-repo-root-agents-md` | MEDIUM | Foreign — reported by `ai-engineer`, outside S5's write set | The SDD gate LAW-classifies `repos/<slug>/AGENTS.md` for any repo, blocking the legitimate first write of a fresh repo-scoped `AGENTS.md`. |
| `repo-agents-md-law-gate-contradicts-template` | MEDIUM | Foreign — reported by the operator session, outside S5's write set | Related but distinct symptom of the same gate surface as the bug above: the gate blocks a consumer repo's root `AGENTS.md` as projected law while the scaffolded template tells the operator to edit it directly. Likely shares a root cause with `sdd-gate-blocks-fresh-repo-root-agents-md` — worth the same architecture-review pass, but this QA close does not adjudicate that; both are recorded here for the PM's intake to route together. |
| `certify-skip-detail-leaks-full-codex-output` | LOW | Foreign, pre-existing (registered 2026-08-23, before S5 opened) | `certify --json`'s SKIP/FAIL detail embeds the entire captured upstream `codex exec` output (workdir, session id) on the not-logged-in branch. |
| `codex-probe-unit-fixture-carries-real-session-uuid` | LOW | Foreign, pre-existing (registered 2026-08-23, before S5 opened) | A captured-stderr test fixture retains a real captured codex session UUID instead of a synthetic one. |

None of the six blocks this verdict: the two S5-adjacent ones (`two-atomic-writers…` and
the consolidation candidate it implies) are deliberately left open under an architect
ruling, not an oversight; the four foreign ones are outside every S5 task's declared
write set and were open before this segment started or were registered by a different
session mid-release.

`self-scan-baseline-drift-t04427-test-fixture-email` (and its three siblings
`self-scan-baseline-drift-pre-pr-review-secrets-prose`,
`…-s4-qa-close-review-prose`, `…-t04343-evidence-prose`) are already **resolved** — not
open. Re-confirmed via `dadaia bugs status --all` (§ above); this segment's own artifact
was proven clean against the same self-scan sentinel before commit (§5).

### 4.2 Intake candidates accumulated this segment (PM intake feed — never materialized as backlog by this close)

1. **`atomic-write-primitive-consolidation`** (HIGH duplication-surface, MEDIUM effort) —
   Firing 2's own §Check(c): collapse the package's 8 near-identical atomic-writer
   primitives (7 modules) into one shared, parameterized primitive (preserve-mode
   on/off, LF-bytes/binary, temp-cleanup-on-any-failure always). Structurally closes
   `two-atomic-writers-leak-temp-file-on-injected-os-replace-failure` instead of a
   two-call-site patch, and shrinks the T-044-35 battery from 8 seams to 1 (net test
   deletion). Two named constraints for the SPEC to adjudicate: the
   features-no-cross-feature-import rule and the core/ I/O ratchet point at
   `infrastructure/` as home; the hooks-never-import-container latency law may require
   `hooks/_common` to keep one sanctioned import-light duplicate — if so, the SPEC must
   say that explicitly.

2. **`scan-test-vacuity-guard`** (LOW severity, LOW effort, class-wide) — Firing 3's
   §Check(b): none of this repo's ~15 tree-walking source-scan tests (including the new
   frozen-clock ratchet itself) asserts its enumerated population is non-empty before
   scanning; a future file-move that mis-roots a walker would pass **vacuously green
   forever** — exactly the false-confidence class the same ruling calls out as bug
   surface in its own right. Fix is a 2-line per-test convention (non-empty + one known
   sentinel file), explicitly **not** a shared harness (a harness was evaluated and
   rejected — the walker duplication has never produced a registered bug, unlike the
   atomic-writer duplication above).

3. **`specs-init-symlinked-target-refusal`** (LOW severity, LOW effort) — Firing 4's
   §Check(a): `dadaia specs init`'s explicit `--specs-dir` branch resolves a symlinked
   target directly, bypassing the resolver seam T-044-40 just hardened (by design — init
   creates rather than resolves). Same CWE-59 class, smaller blast radius (a fresh
   scaffold misplaced, not an existing tree rewritten); closes the last silently-followed
   explicit-path lane.

4. **`INTAKE-AR1-1`** (carried from S3, still unexecuted, re-confirmed present this
   session) — split the test-inventory assertion out of the two byte-golden tests
   (`test_install_target_goldens.py`, `test_public_assets_profile.py`) into a derived
   roster oracle scanned from `dadaia_workspace/public/**`, keeping a policy-only byte
   golden. Zero production-code change.

5. **`INTAKE-AR1-2`** (carried from S3, still unexecuted, re-confirmed present this
   session) — one shared oracle for the three coupled-inventory tests
   (`test_public_pipeline.py`'s `EXPECTED_SKILLS`, `test_public_assets.py`'s path
   assertions, `check_skill_orphans.py`'s roster) to eliminate the cross-write-scope
   drift seam that produced two v0.4.4 bugs.

6. **A30.3-adjacent — catalog trimming/paging at the memory layer** (carried from S3,
   re-confirmed still open) — the bound-session injection prefix currently runs ~4.0×
   over its ≤0.7k-token target purely because `catalog.json` now carries 28 feature
   entries; `ctx_inject.py`'s own digest logic is unchanged and correctly out of scope
   for whichever task eventually owns catalog curation.

7. **A29.1-adjacent — persona line-count ceiling** (carried from S3, re-confirmed still
   open) — 4 of 9 personas (`ai-engineer`, `product-engineer`, `qa-engineer`,
   `software-architect`) still exceed the 220-line target, each justified inline per
   A29.3 ("a fact with no other home stays"); candidate for a follow-up trim pass if the
   operator wants one.

### 4.3 T-044-39 documentation-consistency gap (non-blocking, noted for the record)

Every other sweep task's TASKS.md entry carries an inline `**Resolution:**` narrative
paragraph restating the fix, root cause and evidence pointers. T-044-39's entry does not
— only the `[ ]`→`[x]` marker flip, with the narrative living solely in the commit
message and the `bugs.jsonl` `resolved` event (both independently confirmed complete in
§1). This is a self-consistency gap in this segment's own documentation habit, not a
missing-evidence defect — flagged so a future reader of `TASKS.md` alone (without
`git log`) is not misled into thinking the task is thinner than it is.

---

## 5. Self-scan proof — this artifact is clean before commit

```
$ pytest -p no:cacheprovider -q tests/integration/test_repo_self_scan.py
```

Run at the end of this session, against the working tree including this file — result
recorded in §6 below. No home-absolute path and no email literal appears anywhere in
this document; every filesystem reference in §2–§3 is either a relative repo path or an
explicitly bracketed placeholder (`<tmp-dir>`), matching this release's own established
redaction convention (`f594fafb`, the S4 close's own fix for the identical class).

---

## 6. Full-gate evidence (independently re-run this session)

| Gate | Command | Result |
|---|---|---|
| Format | `ruff format --check .` | `715 files already formatted` |
| Lint | `ruff check --no-cache .` | `All checks passed!` |
| Types | `mypy --strict --cache-dir <out-of-repo> dadaia_workspace` | `Success: no issues found in 273 source files` |
| Full suite | `pytest -p no:cacheprovider -q -n auto` | `2803 passed, 4 skipped, 1 warning` — the 4 skips are all environment-gated (Windows-only assertions, a codex-entitlement live probe, a non-loopback LAN check), matching every prior segment's own recorded skip count; 0 failed |
| Self-scan | `pytest -p no:cacheprovider -q tests/integration/test_repo_self_scan.py` | see §5 — run last, against the committed artifact |

---

## Bug-surface statement (per the standing order — permanent architecture review,
oriented by bug history)

Every one of the eight sweep bugs closes **REDUCED**, independently re-confirmed against
this session's own re-run evidence, not merely re-read from the implementer's claims —
see §1's per-bug column and the four architect rulings it cites (all SOUND, zero REJECT,
zero puxadinho detected across all four independent reviews). Three bugs
(T-044-34/36/37) closed as pure deletions or docstring-only fixes with **zero** new
lines of behavior; T-044-39 is a net-neutral reorder; T-044-33/40 are net-positive in
lines but net-**negative** in behaviors — a silent-acceptance/silent-follow path deleted
in each case, no flag, no second code path, no cross-feature reach-in. T-044-35/38 are
the segment's two legitimate test-growth exceptions, each earned against explicit,
written criteria (coverage-of-existing-contract for T-044-35; four-condition
mechanism-growth for T-044-38) rather than asserted by convenience — and both are
governed by `dadaia-test-stewardship`, not the production-code prefer-deletion doctrine,
which the architect ruling explicitly distinguishes. The one genuine new production gap
this segment surfaced (`two-atomic-writers-leak-temp-file-on-injected-os-replace-failure`)
was **found by** the fix (T-044-35's battery), registered rather than hidden, and pinned
as a self-destructing-on-fix regression test — the opposite of a symptom patch. No
repetition of any prior symptom on any of these eight surfaces was found in the bug
history read for this close. FR22/FR23 themselves (T-044-61/62) operationalize the
standing order as a method and a mechanical gate respectively, and both are proven live
in this document (§2), not merely asserted in the SPEC.
