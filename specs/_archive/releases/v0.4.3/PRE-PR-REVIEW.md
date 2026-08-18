# Six-axis pre-PR review — v0.4.3, T-043-50

**Reviewer:** code-reviewer
**Date:** 2026-08-18 (UTC)
**Target:** `feature/0.4.3`, tip `6ba60c48`; base `df3b1a93` (`origin/develop..HEAD` equivalent)
**Delta:** 121 commits · 155 files changed · +13,875 / −1,754
**Verdict: APPROVED** — zero CRITICAL, zero HIGH. 1 MEDIUM (a decision to ratify, not a
code defect), 3 LOW (all CLOSURE-authoring accuracy items), 3 INFO (record-only).

---

## 1. Target and method

Every number below was produced by this review, running against the working tree at
`6ba60c48`. No figure is quoted from a prior artifact without independent re-measurement;
where a prior artifact's number is confirmed, that is stated explicitly.

Orientation inputs read: `specs/releases/v0.4.3/{SPEC,PLAN,TASKS}.md`,
`ALPHA-{1..6}-QA.md`, `specs/memory/product/catalog.json`, `specs/releases/ACTIVE.md`.

Cache-guard compliance held throughout: `pytest -p no:cacheprovider`, `ruff --no-cache`,
mypy cache redirected under `.dadaia/tmp/code-reviewer/20260818/`.

---

## 2. Gate and suite numbers (measured)

| Check | Command | Result |
|---|---|---|
| Full suite | `pytest -p no:cacheprovider -m 'not quarantine' -n auto -q` | **2582 passed, 3 skipped, 1 warning, 52.55s, exit 0** |
| CI preflight | `dadaia ci preflight` | **5/5 PASS** (`ruff format --check`, `ruff check`, `mypy --strict`, `lint-imports`, `pytest`) |
| Layering | `lint-imports` | **319 files, 1,439 dependencies, 9 contracts kept, 0 broken** |
| Specs | `dadaia specs doctor` | **0 errors**; 20 `LINT-1` heading warnings + 5 structural warnings |
| Backlog | `dadaia backlog doctor` | **clean**; `## ACTIVE` = **0 entries** |
| Public | `dadaia public doctor` | **183 `[ok]`, 0 drift, 0 missing**; `[ok] public-privacy`, `[ok] entities-derivation` (9↔9), `[ok] model-resolution` |
| Workspace | `dadaia doctor` | **All invariants OK** |
| Privacy self-scan | `pytest tests/integration/test_repo_self_scan.py` | **5 passed** |

Collected per tier (independent re-measure): unit **2172**, integration **190**,
e2e **54**, contract **169**.

The single warning is a pre-existing `DeprecationWarning` (`os.fork()` in a
multi-threaded process) at `tests/unit/test_container.py:142` — outside the delta.

Task-marker governance at HEAD: **zero open `[-]` reservations** (the four `[-]` hits in
`TASKS.md` are the legend at `:16` and prose at `:40,42,43`).

---

## 3. Axis 1 — Architecture conformance

**PASS.**

- All 9 import-linter contracts kept, 0 broken. `features/**` imports neither `cli`,
  `infrastructure` nor `hooks`; `core/**` stays stdlib-pure; feature packages remain
  mutually independent (`features-no-cross-feature` kept).
- **Ignore-edge cap ratchet, net down 16 → 15.** Two edges removed by FR16
  (`doctor_memory -> subprocess_runner`, from both `features-no-infrastructure` and
  `features-no-subprocess` — `setup.cfg:65-69,97-101`), one added by FR27
  (`chokepoints.service -> infrastructure.jsonl_log_rotation`, `setup.cfg:79-84`). Both
  moves carry a rationale comment on the edge **and** a cap adjustment in
  `tests/contract/test_import_linter_ignore_cap.py:84-93`, in the same commit — the
  documented protocol was followed exactly. Per-family breakdown re-pinned at
  `:97-102`.
- The one added edge is a **function-scoped lazy import** inside `_append_ledger_line`
  (`features/chokepoints/service.py:882`), so the module keeps its module-load-time
  "never imports infrastructure" posture. Verified by reading the import block
  (`:20-45` — no infrastructure import at module level).
- No cross-feature reach-in was introduced by the delta.

See Finding L-1 for the literal-vs-net tension with A32.3.

---

## 4. Axis 2 — Design patterns

**PASS.** Every new seam follows the established idiom; no pattern break found.

| Idiom | Where the delta applies it | Evidence |
|---|---|---|
| Fail-open hook code | reap isolated in its own `try/except` so a reap bug can never break the reconciler | `hooks/sdd_post_gate.py:562-576` |
| Deletion-lane guard (`_resolved_within`) | resolve-then-`relative_to` inside `try/except`, never a string-prefix check (CWE-22 class) | `features/tmp_gc/service.py:122-132`; mirrored in `features/chokepoints/service.py:836` and `hooks/sdd_post_gate.py:127` |
| Symlink refusal | symlinked entries excluded as candidates, `os.walk(..., followlinks=False)`, `lstat` for marker mtime | `features/tmp_gc/service.py:142-149,182,190-191,227`; `hooks/sdd_post_gate.py:285,406` |
| Token-matched guard, no shell parsing | bare name or our-own-venv-rooted basename only; `shlex` tokenizing, never a substring match | `hooks/venv_guard.py:150-163` |
| Single-implementation helper | one rotation helper every `.dadaia/logs/*.jsonl` writer funnels through | `infrastructure/jsonl_log_rotation.py`; writers at `hooks/pre_gate.py:120`, `sdd_post_gate.py`, `chokepoints/service.py:884` |
| Thin-wrapper contract | LINT-1 imports the package module; the projected script wraps it | `features/specs/memory_lint.py`; contract asserted by `tests/contract/test_public_scripts_thin_wrapper.py` |

Three design details worth naming as *correct*, because they are easy to get wrong:

1. `jsonl_log_rotation` uses **double-checked locking** — the size is re-checked under
   the lock before `os.replace` (`:120-127`), which is what prevents two near-simultaneous
   crossers from destroying each other's rotated generation.
2. The lock-acquisition timeout branch **appends without rotating** rather than dropping
   the line (`:132-140`), and that branch can never call `os.replace`, so it cannot cause
   the race the lock exists to prevent.
3. `gc_consumed_push_verdicts` **appends the audit-ledger line before unlinking** the
   handoff (`features/chokepoints/service.py:958-965`); a failed append leaves the handoff
   in place. A24.4's ordering is implemented as written.

---

## 5. Axis 3 — Tests

**PASS.**

- **Pyramid shape.** unit 2172 / integration 190 / contract 169 / e2e 54. The e2e tier
  measured **54** — matching the alpha-3 V5 re-measure exactly (independent
  `--collect-only`). Playwright specs: **11 files / 46 specs**. Broad LARGE census =
  54 + 46 = **100**, confirming the alpha-3 figure (was 102, −2 from the stderr-drain
  demotion).
- **Intent/Size discipline.** `tests/scripts/check_test_intent_declared.py` exits **0**;
  it is wired into the gating suite via `tests/integration/scripts/test_check_test_intent_declared.py`
  (as is `check_skill_orphans.py`, whose orphan-tooling wiring was the alpha-3 Verdict 3).
- **Slop audit, sample of 12 new test files** (`test_tmp_gc_service.py`,
  `test_post_gate_reap.py`, `test_push_verdict_gc.py`, `test_jsonl_log_rotation.py`,
  `test_memory_lint.py`, `test_bugs_picked_event.py`, `test_service_picked_fold.py`,
  `test_repo_agents_scaffold_symlink.py`, `test_entities_derivation_behavioral.py`,
  `test_public_scripts_thin_wrapper.py`, `test_service_codex_live_probe.py`,
  `test_jsonl_log_rotation_concurrency.py`): **zero tautologies, zero slop found**. Each
  module docstring declares `Intent: <KIND> — <acceptance ids>` and states what it does
  *not* cover (e.g. `test_jsonl_log_rotation.py` explicitly hands A27.3 to the integration
  tier because it spawns real processes). Fixtures assert behaviour, not implementation
  shape.
- **Deletion discipline.** `tests/unit/scripts/test_lint_memory_atoms.py` (−597 lines) was
  deleted under an explicit retroactive `qa-engineer` verdict (`ALPHA-2-QA.md:108`), and
  its replacement `tests/unit/features/specs/test_memory_lint.py` carries **17** test
  functions against the deleted file's **11** — coverage grew, not shrank. A18.4 held.
- **Mutation baseline.** V11 90.4% is recorded as evidence, not as a gate; `mutmut 3.7.0`
  sits in an **optional** poetry group (`pyproject.toml:94-100`) so a plain
  `poetry install` never pulls it, and it is absent from every push-path selector (A20.3).
  Not re-run by this review — off the push path by design.

See Findings L-3 and L-4.

---

## 6. Axis 4 — Security sweep of `2be00f62..HEAD`

**PASS — no CRITICAL, no HIGH.** This is the range carrying **no** dedicated security
review (the alpha-2 APPROVE r2 covered through `ce47f1ea`): **67 commits, 101 files,
+8,917 / −268**. The formal push verdict remains T-043-53's; these findings feed it.

**Secrets / absolute paths.** Every added line was scanned with the shipped privacy
baseline's 15 patterns. The only path-shaped hits are **synthetic fixture literals**
(`/home/<redacted>/ws/.dadaia/.venv/bin/pytest`, etc. in `tests/unit/hooks/test_venv_guard.py`) —
an anonymized operator placeholder, not a real local path. Email-shaped hits are
`t@example.com` (fixture) and `noreply@anthropic.com` (the law-mandated trailer, carved
out by FR12/A12.2). No credential, token, key, hostname or IP. The repo self-scan sentinel
is green (5 passed).

**Injection surfaces.** Zero `shell=True`, zero `os.system`, zero `eval`/`exec` in the
range. Every new subprocess call passes list-argv with a bounded `timeout=`:
`features/certification/service.py:90-109` (codex live probe, `_CODEX_VERSION_PROBE_TIMEOUT` /
`_CODEX_LIVE_PROBE_TIMEOUT`) and `infrastructure/codex_doctor.py` (`_probe_installed_codex_version`,
`timeout=5.0`, `check=False`, never raises). `dadaia tmp gc` accepts **no path argument at
all** (`cli/commands/tmp.py:40-46` — only `--dry-run`), so there is no user-controlled
deletion target. `reports --workspace` takes an operator path and only *resolves* it
(`cli/commands/reports.py`) — no shell, no deletion.

**Deletion-lane safety (the GC code).** Verified per lane, by reading:

- `features/tmp_gc/service.py` — resolve-then-boundary-check on **every** target before
  acting (`_apply_lane:260-264`); refuses anything resolving outside `.dadaia/`; excludes
  `.venv` and `sessions` from the cache walk (`:186`); never descends into or matches a
  symlinked directory (`:190-191`); dated-scratch age from the directory **name's own
  date**, never mtime (`:162-169`); a marker is only orphaned if there is **no** session
  record at all *and* it is older than the SessionStart-safety floor (`:224-231`).
- `features/chokepoints/service.py:954` — same guard before any unlink; ledger append
  precedes the delete.
- `hooks/sdd_post_gate.py:127,285,406` — same guard, `followlinks=False` walks.

`_remove` (`tmp_gc/service.py:236-247`) checks `is_symlink()` first and unlinks rather
than `rmtree`-ing, so the classic dir→symlink swap is not exploitable; on Linux
`shutil.rmtree.avoids_symlink_attacks` is True.

**FR28 cache guard — empirically exercised by this review** (`venv_guard.evaluate_payload`):

| Command | Verdict |
|---|---|
| `pytest -q tests/` | **BLOCK** (correction carried) |
| `pytest -p no:cacheprovider -q tests/` | ALLOW |
| `ruff check .` | **BLOCK** |
| `ruff check --no-cache .` | ALLOW |
| `mypy --strict dadaia_workspace/` | **BLOCK** |
| `mypy --strict --cache-dir /tmp/x dadaia_workspace/` | ALLOW |
| `ruff --version` / `pytest-watch -q` / `repos/other/.venv/bin/pytest -q` / `git status` | ALLOW (no false block) |

A28.1, A28.2 and A28.3 all hold on the executed path.

**Bug-event redaction.** All 12 `bugs.jsonl` events appended in the range parse cleanly
and contain **zero** absolute paths, IPs or emails. Two of the twelve are themselves
Arm-B fixes *for* redaction escapes (`t043-33-absolute-path-leaked-into-tasks-md`,
`self-scan-baseline-drift-t04343-evidence-prose`), each with a `reported`→`resolved`
pair — the discipline is working, and visibly so.

---

## 7. Axis 5 — Performance (the hook path)

**PASS.** Nothing heavy landed on the PreToolUse path.

- **Reap (FR26)** runs in `sdd_post_gate` — **PostToolUse**, off the blocking path
  entirely — and is gated *behind* the existing 30 s throttle
  (`sdd_post_gate.py:556-560`: `_throttled` returns before any work; the marker is
  stamped immediately so even a slow or erroring pass throttles the next call). It rides
  the same cadence as the pass that already spawns a `git status` child, which is far
  heavier than the reap's bounded record walk.
- **Rotation at write time (FR27)** adds, per PreToolUse latency append: one
  `mkdir(exist_ok=True)` (already present before the change), one `stat`, one append. The
  lock is taken **only** when the file is at or over the 1 MB cap
  (`jsonl_log_rotation.py:172-177`) — the overwhelming majority of calls are entirely
  lock-free. Cost is unchanged from the pre-FR27 writer.
- **Cache-guard token scan (FR28)** is a `shlex` tokenization plus set membership on the
  first token — O(len(command)), no filesystem access, no subprocess.

Bounded-worst-case note recorded as INFO-3 below.

---

## 8. Axis 6 — Dead code

**PASS.**

- Mechanical scan of **93 symbols added by the delta** (functions and classes, parsed
  from the diff) against the whole tree (`dadaia_workspace`, `tests`,
  `specs/releases/v0.4.3`, `.dadaia`): **0 with zero references**. The delta introduced no
  orphans.
- `gc_consumed_push_verdicts` — the known intentional unwired function. **Disposition
  verified to exist**, and it is thorough: `ALPHA-5-QA.md:182-247` (§6.1) carries a full
  written verdict with the routing decision; `TASKS.md:1375,1906`; the implementer's own
  handoff (`…T-043-39-verdict-gc.handoff.json`) raises it as a finding with a
  `decisions_required` entry; the alpha-5 close handoff repeats it; and the alpha-6
  consumer round records it as **"Not exercised"** rather than silently passing it. Per
  the mandate, verified rather than flagged as dead code — but see Finding M-1 for the
  budget consequence.
- No commented-out block over 10 lines, no unreferenced import introduced by the delta
  (`ruff check` F401 clean across the tree).
- Retired-with-its-subject: the FR16 `subprocess` fallback edges were deleted from
  `setup.cfg` in the same change that removed the shell-out, and the module docstring's
  "architectural exception it HOLDS" note went with it (A16.4).

---

## 9. A32.1–A32.4 — explicit verification

| Id | Requirement | Status | Evidence |
|---|---|---|---|
| **A32.1** | `ci preflight`, `doctor`, `specs doctor`, `backlog doctor`, `public doctor` green; `specs doctor` **0 errors** | **PASS** | preflight 5/5; `dadaia doctor` "All invariants OK"; `specs doctor` **0 errors** (20 `LINT-1` + 5 structural warnings, all warning-class); `backlog doctor` clean; `public doctor` 183 `[ok]` / 0 drift |
| **A32.2** | `public doctor` reports `[ok] public-privacy`, `[ok] entities-derivation`, `[ok] model-resolution` | **PASS** | all three present and `[ok]`; entities-derivation reports 9 Personas ↔ 9 core sub-agents |
| **A32.3** | `features/**` imports no `cli`/`infrastructure`/`hooks`; `core/**` stdlib-pure; `lint-imports` green with **no new accepted edge** | **PASS with a documented exception** | 9/9 contracts kept, 0 broken. One edge **added** (FR27) and two **removed** (FR16); the cap ratcheted **net down 16 → 15**. Literal "no new accepted edge" is not met; net posture improved. See Finding L-1 |
| **A32.4** | No harness projection changes except where an FR requires it, proven by byte-diff | **PASS** | 26 `public/**` files changed, **each mapping to a named FR** (agents ×9 → FR5 + the skill-orphan Arm-B rider; `data/DADAIA.md` → FR4; `schemas/bugs/*` → FR14; 4 scripts → FR2/FR5/FR16; 11 skills → FR1/2/3/6/7/22/23/25/21). Agent diffs are **additive-only, 24 lines total**, and the two shell-less agents correctly received **no** `dadaia-cli` grant. `lint-dadaia-cli-reachability.py --self-test` passes in both directions; `lint-skill-collisions.py` reports no undeclared overlap among 14 stage skills. A22.8's 81-file sha256 byte-diff (2 intended lines) independently re-verified in `ALPHA-4-QA.md:43`. Projections: 0 drift, 0 missing |

Adjacent, verified while in the tree: **A32.5's headline holds** — `## ACTIVE` = 0 entries.
**A13.4 is pending by design** (the `.heading-allowlist` write is MEMORY-class, held for
the `rc-1` window at T-043-51 per D-6) — see the note in §11.

---

## 10. Findings

> Convention: **actionable** findings carry a severity, an owning lane and a fix
> recommendation, and return to that lane before the archive move. **Record-only**
> observations terminate in this report and CLOSURE — they never enter intake (FR6/R4).

### M-1 · MEDIUM · lane: `project-manager` → operator · FR24 is not live-wired, and its only routing creates an intake candidate the release budget forbids

`gc_consumed_push_verdicts` (`features/chokepoints/service.py:887`) has **no production
caller** — verified independently: the only references outside its own module are its test
suite and release documents. FR24's SPEC preamble states, present-tense, *"After a
successful push, the pre-push chokepoint deletes the APPROVED `security-reviewer` verdict
handoff(s)…"*, which is **not true of the live system**. A24.1–A24.4 nonetheless pass at
the function-contract level, and the technical reasoning is correct (the pre-push hook runs
before git transfers anything, so "the push succeeded" is unknowable from inside it).

The issue is not the code — it is the **budget**. `qa-engineer` dispositioned this as
routing (2) *CLOSURE honesty* **+** (3) *operator/PM intake for the wiring work*
(`ALPHA-5-QA.md:225-247`). Routing (3) is by definition an actionable intake candidate,
which collides head-on with **A32.5: "Residual budget: zero actionable intake candidates."**
The release cannot both defer the wiring to intake and claim a zero residual budget without
an explicit ruling.

**Fix recommendation:** do **not** rush the wiring into `rc-1` — the qa reasoning against
that is sound (choosing between a `reference-transaction` hook and a `git push`-wrapping
CLI verb is a real design decision). Instead: (a) obtain an **operator-ratified deferral**,
which `DADAIA.md` §5 already classes as *already-approved intake* and therefore reconciles
with A32.5; (b) require T-043-51/T-043-52 to record FR24 with the qualification qa
specified — implemented and tested contract, **no live caller**, a push today never invokes
it — so the `sdd-gate-v3.md` memory write (A24.4) never encodes a false present-tense claim.

### L-1 · LOW · lane: `product-engineer` (CLOSURE) · A32.3's "no new accepted edge" is met net, not literally

FR27 added one accepted ignore edge (`features.chokepoints.service ->
infrastructure.jsonl_log_rotation`, `setup.cfg:79-84`) while FR16 removed two
(`setup.cfg:65-69,97-101`). The cap ratcheted **16 → 14 → 15** — net **down**. Every step
followed the documented protocol (rationale on the edge, cap bumped in the same commit,
per-family breakdown re-pinned). The added edge is a function-scoped lazy import, so the
module's module-load-time posture is intact.

This is a **good** outcome, but A32.3's literal wording is "no new accepted edge", and one
was added. Silence in CLOSURE would leave the record implicitly claiming zero additions.

**Fix recommendation:** CLOSURE states A32.3 is satisfied **net** and names the arithmetic
— one edge added by FR27, two removed by FR16, cap 16 → 15 — so the ratchet's direction is
the record rather than an unqualified "no new edge".

### L-2 · LOW · lane: `product-engineer` (CLOSURE memory, A19.3) · FR19's enforcement is narrower than its headline

`tests/scripts/check_test_intent_declared.py:6` scopes the check to `tests/e2e/**`,
excluding `__init__.py`, `rendezvous.py` and `conftest.py`. FR19's title is "A new test
without a declared intent is **refused**" — suite-wide in tone. A19.1–A19.3 all hold as
written (green at HEAD, fires on an undeclared e2e file, shape documented in
`tests/AGENTS.md`), and the limitation is **honestly disclosed in the script's own
docstring**: *"the wider suite carries no such mechanical gate yet."* So this is not a
delivery gap — it is a memory-accuracy risk.

**Fix recommendation:** the `quality-assurance.md` write at T-043-51 states the
**e2e-only scope explicitly**, so product memory never claims suite-wide mechanical
enforcement. This is exactly the claim-vs-reality class the release exists to close; it
would be ironic to introduce a fresh instance of it in the same closure.

### L-3 · LOW · lane: `product-engineer` (CLOSURE memory, A18.6) · the LARGE census cap of 30 is now met by nothing

Independently measured: **100 broad LARGE** (54 pytest e2e + 46 Playwright) against a
declared cap of **30**. Of 102 offenders, **100 were dispositioned KEEP** with
justification and a declared owner. A18.2 explicitly permits that disposition, so this
**PASSES** — the curation was executed as specified, and the −2 demotion is real.

But the doctrine now carries a cap that **3.3× nothing meets**, sanctioned entirely by
per-test exceptions. That is the same *aspirational-number* failure mode **R8 forbade for
complexity** ("measure first, then pin; never aspirational") — applied there, not applied
here.

**Fix recommendation:** A18.6's census-sentence rewrite should resolve this one way or the
other: either re-pin the cap at the measured reality under the same ratchet-down doctrine
R8 uses, or state plainly that 30 is a target with 100 recorded exceptions. Leaving a bare
"cap: 30" in memory next to a census of 100 is a number that will mislead the next reader.

### INFO-1 · record-only · `.import_linter_cache/` is born inside the repo tree

`repos/dadaia-workspace/.import_linter_cache/` exists (directory dated **before** this
delta) and is gitignored at `.gitignore:31`. `DADAIA.md` §4's "repos stay clean" list does
not enumerate it, and FR28's guard is token-matched on `pytest`/`ruff`/`mypy` only —
`lint-imports` is out of its declared scope, so this is **not** a delta defect and not an
FR28 miss. Noted for whoever next revisits the cache-guard token set.

### INFO-2 · record-only · a delete that fails I/O is invisible in `tmp gc` output

`features/tmp_gc/service.py:260-270`: a target that passes the lane guard but whose
`_remove` returns `False` lands in **neither** `acted` nor `refused`, so an I/O-failed
deletion is silent in the CLI report. This is the documented, deliberate fail-open posture
(`:253-257`) and matches the segment's other GC lanes. Named only so a future observability
pass knows the gap is by choice, not oversight.

### INFO-3 · record-only · bounded worst-case lock wait on the PreToolUse path

`infrastructure/jsonl_log_rotation.py:69-71`: `_LOCK_MAX_ATTEMPTS(50) × _LOCK_RETRY_SECONDS(0.002)`
≈ **100 ms** worst case, reachable only when `hook-latency.jsonl` is at the 1 MB cap *and*
contended. The common path never takes the lock (`:172-177`), so the axis-5 "O(small) on
every Bash call" requirement holds; the tail is bounded and then fails open. Recorded for
completeness, not for action.

---

## 11. Summary

| Severity | Count | Ids |
|---|---|---|
| CRITICAL | 0 | — |
| HIGH | 0 | — |
| MEDIUM | 1 | M-1 |
| LOW | 3 | L-1, L-2, L-3 |
| INFO (record-only) | 3 | INFO-1, INFO-2, INFO-3 |

**Actionable (return to lane before the archive move):** M-1 (`project-manager` → operator
ruling), L-1, L-2, L-3 (all `product-engineer`, and all discharged inside the CLOSURE
authoring pass at T-043-51/T-043-52 — none requires a code change).

**Record-only (terminate here and in CLOSURE, never enter intake):** INFO-1, INFO-2, INFO-3.

**Pending-by-design, not a finding:** A13.4's zero-`LINT-1` requirement. 20 heading
warnings stand at HEAD; the `.heading-allowlist` write is MEMORY-class and correctly held
for the `rc-1` window (D-6). The V3 capture
(`v0.4.3-T-043-17-fr13-v3-lint1-heading-capture.md`) already made the count correction
itself — "12" was the *atom* count, **20** is the *heading* count — and enumerates all 20
with per-heading dispositions (18 allowlist, 2 atom-fix). This review re-measured **20**
independently and confirms the enumeration is complete and current. T-043-51 must land all
20, not 12.

**Fidelity check on FR16, performed as a control:** the base-`df3b1a93` standalone lint
script and the post-move package implementation both report **20** warnings on the same
tree — the relocation preserved behaviour exactly, which is the strongest available
evidence for A16.1.

---

## 12. Recommendation

**APPROVE.**

Zero CRITICAL and zero HIGH findings across all six axes. The suite is green (2582
passed), the preflight is 5/5, all nine layer contracts hold with the ignore-edge cap
ratcheted net down, all four doctors are clean with `specs doctor` at 0 errors, the
projection surface has zero drift, and A32.1–A32.4 are verified with measured evidence.

The one MEDIUM is a **decision to ratify, not a defect to fix**: FR24's live wiring is
correctly deferred on sound engineering grounds, but the deferral needs the operator's
ratification to sit inside A32.5's zero-residual budget rather than outside it. The three
LOWs are CLOSURE-authoring accuracy items — each one guards against writing a claim into
product memory that the tree does not support, which is precisely the failure class this
release was chartered to eliminate.
