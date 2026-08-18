# Closure: Release — v0.4.3 — claims-made-true / backlog-zero

> **Status:** Aprovado
> **Release ID:** v0.4.3
> **Owner:** product-engineer
> **Closed:** 2026-08-18
> **Branch:** `feature/0.4.3` (cut from `develop` at `84e369a0`; base of the measured delta: `df3b1a93`)
> **Finalization order (satisfied):** review (T-043-50, `6ba60c48`) → memory (T-043-51, `cd24e0fd`) → CLOSURE (this document) → sweep → archive.

## Summary

v0.4.3 took the operator's standing order — *"fila inteira em 1 release"*, with residual
backlogs minimised to zero — and shipped the **entire** `## ACTIVE` queue of 25 records in
one segmented release: six `alpha-N` increments plus a shipping candidate, 32 FRs, 53
tasks. Twenty-four slugs are consumed and receive their terminal `LEDGER` line in this
sweep; the twenty-fifth was rejected by ruling R4 and already carries its line from the
definition commit. `## ACTIVE` is **empty** and stays empty.

Read as a set, the queue was one act: *make the thing that is already claimed actually
true*. The suite doctrine now applies to this repo's own suite (LARGE census measured and
curated, an intent declaration mechanically enforced over the e2e tier, a pinned mutation
tool with a real baseline). The push gate now reads the commit objects it publishes, not
just blobs, with the header/body boundary and the path-less amnesty semantics pinned by
fixture. The privacy baseline stopped growing literal by literal: carve-outs need a
rationale, the dotted-chain class has a structural rule, and the law-mandated co-author
trailer no longer refuses its own push. The Codex projection proves law-load-once for both
a parent session and a delegated agent, certifies against the **installed** Codex, and its
personas lost 10,624 bytes of restated law. Artifact lifetime became event-driven —
ack-on-consume for handoffs, a push-consumed verdict collector wired into the ship flow,
a closure sweep, a reconciler that reaps what it already walks, write-time log rotation, a
venv guard that refuses to let a cache be born, and `dadaia tmp gc` as the single
calendar-based backstop. Complexity and size became measured, ratcheted governance, and
this document carries the first mandatory `## Size accounting` table. Finally, the whole
assembled surface — GC included — was validated on a throwaway **real** consumer
workspace, and the published CHANGELOG lineage was backfilled from git history with no
invention.

Ten Arm-B rider bugs were registered and closed inside the release window, every one with
a complete `reported`→`resolved` pair; the bug ledger reports **0 open**. The pre-PR
six-axis review returned **APPROVED** with zero CRITICAL and zero HIGH; its single MEDIUM
(FR24 had no live caller) was **resolved in-release** rather than deferred, so the residual
budget holds: **this release leaves zero actionable intake candidates.**

## Tasks completed

Segment-close shas marked ⁽ˢ⁾ are the next segment's own declared range base (`ALPHA-N-QA.md`
§1), which is that close commit; where TASKS evidence records no sha, the committed artifact
is named instead.

| Task ID | Description | Final commit |
|---|---|---|
| T-043-01 | Definition commit (SPEC/PLAN/TASKS/GRILL + purge-on-pick) | `c4175ff1` |
| T-043-02 | Milestone (a): merge, security review, push | merge `cab4e6c1` (rider `07c78366`, amendments `df3b1a93`) |
| T-043-03 | FR1 — pin every prescribed third-party install | `8fa6fcca` |
| T-043-04 | FR2 — resolve the two duplicate `dd-` activation claims | `584304ee` |
| T-043-05 | FR3 — break the release-definition pointer loop | `f42f69b2` |
| T-043-06 | FR4 — one always-on sentence for the redaction rule | `2cbd74a2` |
| T-043-07 | FR5 — reconcile `dadaia-cli`'s grant with its description | `03d9b8b9` |
| T-043-08 | FR6 — record the reconciliation-merge mechanic | `8556c8e2` |
| T-043-09 | FR7 — note the stewardship homonyms | `3a562a93` |
| T-043-10 | FR8 — `AGENTS-PLACEHOLDER-1` on an installed `tests/AGENTS.md` | `91c5d831` |
| T-043-11 | `alpha-1` projection cycle (V9) | `e9b3434a` (re-projected `b7ad9123`) |
| T-043-12 | `alpha-1` close — qa review | `600361f2`⁽ˢ⁾ (`ALPHA-1-QA.md`) |
| T-043-13 | FR9 — interpreter-probe hardening | `69214f14` |
| T-043-14 | FR10 — `commit_paths` index-scope hardening | `24a349f5` |
| T-043-15 | FR11 — the push scan reads commit objects | `5479b827` |
| T-043-16 | FR12 — baseline rationale, structural rule, trailer carve-out | `d4658ae5` (+ remediation `f1a1ef93`…`ce47f1ea`) |
| T-043-17 | FR13 — MEMORY path class decided; V3 enumerated | `9dac383d` |
| T-043-18 | FR14 — the non-terminal `picked` bug event | `b001acdd` (+ `6fb8674d`) |
| T-043-19 | FR15 — clarify the dangling deferral pointer | `b85302ac` |
| T-043-20 | FR16 — one logic, one source for projected scripts | `b12791cd` (package) + `2c0b9959` (`public/`) |
| T-043-21 | FR17 — refuse a symlinked repo-`AGENTS.md` destination | `bb2a5959` |
| T-043-22 | Arm-B rider — segment router errors instead of going silent | `29d0f9d0` |
| T-043-23 | `alpha-2` close — qa + security review | `2be00f62`⁽ˢ⁾ (`ALPHA-2-QA.md`) |
| T-043-24 | FR18a — LARGE census baseline (V4) + offender list | `3450b0b3` |
| T-043-25 | FR18b — execute the curation under qa verdicts | `24d0ba26`…`068d0462` (9 commits) |
| T-043-26 | FR18c — re-measure (V5) + demotion map draft | `2446a7e4` |
| T-043-27 | FR19 — mechanical intent-declaration check | `01e3afbb` |
| T-043-28 | FR20 — select, pin and wire the mutation tool (V11) | `49d50353` |
| T-043-29 | FR21a — measure the maxima, pin the ceilings (V6) | `cbfea661` |
| T-043-30 | FR21b — `## Size accounting` required in CLOSURE | `9df50d35` |
| T-043-31 | `alpha-3` close — qa review | `5c7b7616`⁽ˢ⁾ (`ALPHA-3-QA.md`) |
| T-043-32 | FR22a — scope the six intents, re-measure the baseline (V7) | `4428593f` |
| T-043-33 | FR22b — compact the personas, load the law once | `da73d84e` |
| T-043-34 | FR22c — truthful trust boundary, live certification | `a9aa1215` (rider `8c50e1ca`) |
| T-043-35 | FR22d — behavioral `ENT-DERIVE-1`, skill-ref inventory | `2a96e2ac` |
| T-043-36 | FR22e — reconcile the Codex docs, prove isolation (V8) | `02c129fe` |
| T-043-37 | `alpha-4` close — qa review + certification | `e2e13216`⁽ˢ⁾ (`ALPHA-4-QA.md`) |
| T-043-38 | FR23 — ack-on-consume for coordination handoffs | `47255c21` |
| T-043-39 | FR24 — consumed push verdict dies with the push | `b3335d97` |
| T-043-40 | FR25 — release closure sweeps its own artifacts | `7c7edae6` |
| T-043-41 | FR26 — the reconciler reaps what it walks (V10) | `ef2f824e` |
| T-043-42 | FR27 — writers rotate their own logs | `ee712147` |
| T-043-43 | FR28 — the cache must not be born | `86701967` |
| T-043-44 | FR29 — `dadaia tmp gc`, the orphan backstop | `ebc3b292` |
| T-043-45 | `alpha-5` close — qa review | `429e8258`⁽ˢ⁾ (`ALPHA-5-QA.md`) |
| T-043-46 | FR30a — consumer round on a throwaway real workspace | `41f427d1` (bug register `8ca8ac41`) |
| T-043-47 | FR30b — the budgeted remediation cycle (spent) | `e2eb28f8` |
| T-043-48 | FR31 — backfill the published CHANGELOG lineage | `e323ed9f` |
| T-043-49 | `alpha-6` close — qa review | `ALPHA-6-QA.md` (reviewed at `47dee4bd`; artifact sha not recorded in TASKS) |
| T-043-50 | Six-axis pre-PR review on a thawed tree | `PRE-PR-REVIEW.md`, APPROVED at `6ba60c48` |
| — | **M-1 remediation rider** — FR24 wired into the ship flow (`dadaia ci gc-push-verdicts`) | `7e6fd30d` |
| — | **Arm-B rider** — redact the PRE-PR-REVIEW secrets-prose literal | `19ddc962` |
| T-043-51 | Memory window: one authoring pass per atom | `cd24e0fd` |
| T-043-52 | CLOSURE, disposition sweep, artifact sweep, archive | this commit |
| T-043-53 | Ship: version bump, merge, security review, push, PR | **OPEN by design** — ship follows archive (D8/FR5) |

## Validations

| Description | Command | Evidence |
|---|---|---|
| Full suite at the final rc-1 tip | `pytest -p no:cacheprovider -m 'not quarantine' -n auto` | **2590 passed, 3 skipped, 0 failed** at `7e6fd30d` (M-1 rider handoff `2026-08-18T021309Z`); 2582/3/0 at review tip `6ba60c48` (`PRE-PR-REVIEW.md` §2) |
| CI preflight (5 checks) | `dadaia ci preflight` | **5/5 PASS** (`ruff format --check`, `ruff check`, `mypy --strict`, `lint-imports`, `pytest`) — `PRE-PR-REVIEW.md` §2; re-confirmed at `7e6fd30d` |
| Layer contracts | `lint-imports` | **319 files, 1,439 dependencies, 9 contracts kept, 0 broken** — `PRE-PR-REVIEW.md` §2/§3 |
| Spec health (pre-memory-window) | `dadaia specs doctor` | **0 errors**, 20 `LINT-1` + 5 structural warnings at `6ba60c48` — `PRE-PR-REVIEW.md` §2 |
| Spec health (post-memory-window, A13.4) | `dadaia specs doctor` | **0 memory errors, 0 `LINT-1` heading warnings** at `cd24e0fd`; sole error `SPEC-DOC-024`, the rc-1 phase-ladder transient that clears at this archive (T-043-51 evidence) |
| Backlog health + headline acceptance (A32.5) | `dadaia backlog doctor` | **clean**; `## ACTIVE` = **0 entries** — `PRE-PR-REVIEW.md` §2 |
| Projection surface (A32.2) | `dadaia public doctor` | **183 `[ok]`, 0 drift, 0 missing**; `[ok] public-privacy`, `[ok] entities-derivation` (9 personas ↔ 9 sub-agents), `[ok] model-resolution` — `PRE-PR-REVIEW.md` §2 |
| Workspace invariants | `dadaia doctor` | **All invariants OK** — `PRE-PR-REVIEW.md` §2 |
| Privacy self-scan sentinel | `pytest tests/integration/test_repo_self_scan.py` | **5 passed** at `6ba60c48` and again at `7e6fd30d` |
| Certification incl. live Codex probe | `dadaia certify --json` | `"ok": true`, **12/12 PASS**, `codex-live-probe — codex-cli 0.147.0: live exec probe observed 'DADAIA-LIVE-PROBE-OK'` — `ALPHA-4-QA.md` |
| Push chokepoint dry-run over the publishable squash shape | `dadaia ci push-gate-check` (read-only, synthetic squash of `df3b1a93..ce47f1ea`) | tree `a50e5b14`, **114 objects, zero denylist blocks**; the only refusal is the structurally inherent "no verdict covers a just-synthesised commit" — `ALPHA-2-QA.md` Appendix C |
| Bug ledger | `dadaia bugs status` | **0 open bug(s)** — `ALPHA-6-QA.md` §4, re-confirmed at `7e6fd30d` |
| Mandatory grill on the picked set (`dd-release-definition` §3) | `dadaia-grill-me` | 26 dossiers, 25 divergences (D1–D25), 9 decisions → R1–R9; report set `.dadaia/reports/dadaia-workspace/product-engineer/2026-08-17T143000Z-v0.4.3-grill*.html`, handoff `.dadaia/handoff/dadaia-workspace/2026-08-17T143200Z-product-engineer-v0.4.3-grill.handoff.json`, index `GRILL.md` |
| Milestone (a) security verdict on the pushed definition delta | diff-based `security-reviewer` review of `origin/develop..develop` | APPROVED handoff `.dadaia/handoff/dadaia-workspace/2026-08-17T145516Z-security-reviewer-v0.4.3-definition-push-rereview.handoff.json`; gate exit 0 |
| `alpha-2` gate/baseline security verdict (FR11, FR12) | diff-based `security-reviewer` review of `600361f2..ce47f1ea` | APPROVED handoff `.dadaia/handoff/dadaia-workspace/2026-08-17T182834Z-security-reviewer-v0.4.3-alpha-2-delta-r2.handoff.json` (`metrics.commit_sha ce47f1ea`) |
| V3 — the standing `LINT-1` heading warnings, enumerated | `dadaia specs doctor` capture | **20 headings across 12 atoms** (the "12" of the entry text was the *atom* count) — `.dadaia/tmp/software-engineer/20260817/v0.4.3-T-043-17-fr13-v3-lint1-heading-capture.md` |
| V4/V5 — LARGE census before and after the curation | `pytest -m e2e --collect-only` + Playwright enumeration | **102 → 100** broad LARGE (pytest e2e 56 → **54**, Playwright 46 unchanged) — `.dadaia/tmp/qa-engineer/20260817/v0.4.3-T-043-24-v4-large-census.md`, `…-T-043-26-v5-census-remeasure.md` |
| V6 — complexity maxima, measured then pinned in one task | `ruff check --no-cache --select C901,PLR1702 --preview --config lint.mccabe.max-complexity=1 --config lint.pylint.max-nested-blocks=1 .` | max complexity **63** (`features/panel/handler.py:330 make_handler_class`), max nesting **6** (`features/telemetry/reader/allowlist.py:116`) — `.dadaia/tmp/software-engineer/20260817/v0.4.3-T-043-29-v6-complexity-maxima.md` |
| V7/V8 — Codex persona bytes and projection isolation | production `install(target="codex")` into an isolated scratch root; sha256 inventory of 81 projected files before/after | **127,594 B → 116,970 B (−10,624 B, −8.3 %)**, all nine TOMLs shrank; exactly **2** of 81 files differ, both the same canonical `ai-harness-codex` skill body (A22.8) — `.dadaia/tmp/ai-engineer/20260817/v0.4.3-T-043-32-v7-codex-byte-baseline.md`, `…-T-043-36-v8-projection-isolation.md` |
| V9 — `alpha-1` projection cycle | `dadaia public stage && dadaia public install --target all && dadaia public doctor` | 183 `[ok]` / 0 `[error]` / 0 `[warn]` / 0 `[drift]`, independently re-verified at `b7ad9123` — `ALPHA-1-QA.md` §0, `.dadaia/tmp/ai-engineer/20260817/public-doctor-out.txt` |
| V10 — reconciler reap, real production execution | installed PostToolUse hook (self-hosting workspace) | `{"event": "RECONCILER_REAP", "sessions_reaped": 1, "presence_reaped": 0, "markers_reaped": 10, "empty_context_dirs_removed": 2, "lifecycle_runs_reaped": 67}` at `2026-08-17T22:48:39Z`; live session untouched — `.dadaia/tmp/software-engineer/20260817/v0.4.3-T-043-41-v10-reconciler-reap.md` |
| V11 — first mutation baseline (evidence, never a gate) | `tests/scripts/run_mutation_baseline.sh` (`mutmut==3.7.0`, off the push path) | **73 mutants, 66 killed, 7 survived, 0 no-tests, 90.4 %, ~9 s** — `.dadaia/tmp/software-engineer/20260817/v0.4.3-T-043-28-v11-mutation-baseline.md` |
| FR29 backstop, dry-run on the real workspace | `dadaia tmp gc --dry-run` | **10 items, all cache-lane**; zero dated-scratch and zero orphan-marker items (the 3-day floor protects this release's own captures) — `ALPHA-5-QA.md` §5 |
| Consumer round on a throwaway REAL workspace (R7) | `dadaia init --workspace <tmp> --harness all`, then supported interfaces only | A30.1–A30.4, A30.6 PASS; 4 environment limits recorded; 5 of 7 GC touchpoints exercised — `.dadaia/tmp/qa-engineer/20260818/v0.4.3-T-043-46-consumer-round.md`, `ALPHA-6-QA.md` |
| Six-axis pre-PR review on a thawed tree (A32.1–A32.4) | `code-reviewer`, delta `df3b1a93..6ba60c48` (121 commits, 155 files, +13,875 / −1,754) | **APPROVED**, 0 CRITICAL / 0 HIGH / 1 MEDIUM / 3 LOW / 3 INFO — `PRE-PR-REVIEW.md`, handoff `.dadaia/handoff/dadaia-workspace/2026-08-18T014638Z-code-reviewer-T-043-50-six-axis.handoff.json` |
| M-1 remediation — FR24 given a live caller | `dadaia ci gc-push-verdicts --sha <landed-tip> [--dry-run]` | 3 files, +311/−3, 8 new unit tests; suite 2590/3/0, preflight 5/5, new-command complexity ~8 vs the 63 ceiling — commit `7e6fd30d`, handoff `.dadaia/handoff/dadaia-workspace/2026-08-18T021309Z-software-engineer-review-m1-fr24-wiring.handoff.json` |
| V12 — size accounting | `git diff --numstat df3b1a93..HEAD` (dispatcher-measured) | see `## Size accounting` below |
| V13 — `SPEC-DOC-031` count **after** the archive move | `dadaia specs doctor` | **pending — owned by T-043-53**, by design: the count is captured after this closure's own `git mv`, never before (`dd-release-closure`, standing note) |

## Size accounting

**Mandatory** (FR21b/A21.4). Measured by the dispatcher over `df3b1a93..HEAD` — the full
release delta, base being the amended milestone-(a) tip. Never estimated.

| Metric | Value |
|---|---|
| Production LOC added | `3641` |
| Production LOC deleted | `767` |
| Production LOC net | `+2874` |
| Test LOC added | `6582` |
| Test LOC deleted | `831` |
| Test LOC net | `+5751` |

**Three largest additions by file:**

| File | LOC added |
|---|---|
| `dadaia_workspace/features/specs/memory_lint.py` | `545` |
| `dadaia_workspace/hooks/sdd_post_gate.py` | `386` |
| `dadaia_workspace/features/tmp_gc/service.py` | `313` |

**Three largest deletions by file:**

| File | LOC deleted |
|---|---|
| `dadaia_workspace/public/scripts/lint-memory-atoms.py` | `583` |
| `dadaia_workspace/features/specs/doctor_memory.py` | `84` |
| `dadaia_workspace/hooks/sdd_post_gate.py` | `18` |

The two largest movements are the same movement: FR16 moved the memory lint **into** the
package (`memory_lint.py` +545, `doctor_memory.py` −84) and thinned the projected script to
a wrapper (−583). Net, the release added capability (GC, the commit-object scan, the CLI
backstop) while deleting a duplicated implementation — the test tier grew ~2× the
production tier, which is the intended ratio for a release whose FRs are mostly contracts.

| Ceiling | Before | After | Justification (only if decreased) |
|---|---|---|---|
| `C90` (`max-complexity`) | `63` | `63` | n/a — unchanged, pinned at the measured maximum |
| `PLR1702` (`max-nested-blocks`) | `6` | `6` | n/a — unchanged, pinned at the measured maximum |

**Nesting-violation count:** `0` — `ruff check` is clean for both `C901` and `PLR1702` at the
pinned ceilings (A21.2, green at HEAD by construction).

**Honest note on "before".** No ceiling existed before this release: `C90` was absent from
`pyproject.toml`'s `select` and no `PL` rule gave a nesting bound. FR21/T-043-29 measured
the real maxima with a permissive ceiling and pinned the ceiling **at** those maxima in the
same task (R8, measure-then-pin, never aspirational), so *before* and *after* are the same
number by construction. Every function added by this release sits far under both: the
highest new-function complexity measured anywhere in the delta is ~14
(`sdd_post_gate._reap_markers`); the M-1 rider's new CLI command is ~8.

**Ratchet law:** ceilings ratchet only downward; a decrease is justified in CLOSURE.

**Layer-contract arithmetic (L-1, recorded rather than left implicit).** A32.3's literal
wording — "`lint-imports` green with **no new** accepted edge" — is satisfied **net, not
literally**. FR16 removed **two** accepted ignore edges
(`doctor_memory -> subprocess_runner`, from both `features-no-infrastructure` and
`features-no-subprocess`, `setup.cfg:65-69,97-101`); FR27 added **one**
(`chokepoints.service -> infrastructure.jsonl_log_rotation`, `setup.cfg:79-84`, a
function-scoped lazy import that keeps the module's module-load-time posture intact). The
cap therefore moved **16 → 14 → 15**, a **net-down** ratchet, with a rationale comment on
each edge and the cap adjusted in the same commit
(`tests/contract/test_import_linter_ignore_cap.py:84-93`). Nine of nine contracts kept, zero
broken. A32.3 is recorded as satisfied **net**, with the arithmetic above as the record.

## Drifts

### fr24-shipped-without-a-live-caller

**Description:** FR24's SPEC preamble is present-tense — *"After a successful push, the
pre-push chokepoint deletes the APPROVED verdict handoff(s)…"* — but the pre-push hook runs
**before** git transfers any object, so "the push succeeded" is categorically unknowable
from inside it. T-043-39 therefore shipped `gc_consumed_push_verdicts` as a correct, fully
tested **pure action function** with no production caller, documenting the two legitimate
observation points (a `reference-transaction` hook, or a `git push`-wrapping caller) as out
of its write set. `ALPHA-5-QA.md` §6.1 named the gap rather than absorbing it; the six-axis
review escalated it as **M-1**, because its only proposed routing (operator/PM intake for
the wiring) collided head-on with A32.5's zero-residual budget.

**Resolution:** wired **in-release**, not deferred. The rc-1 rider `7e6fd30d` added
`dadaia ci gc-push-verdicts --sha <landed-tip> [--dry-run]` — observation point (b) named in
the function's own docstring — which the ship flow runs immediately after a confirmed
`develop` push; 8 new unit tests, `LEDGER_RELPATH` promoted to the module's public surface
so the CLI renders the ledger basename from one source, suite 2590/3/0. The trade-off taken:
the CLI verb (an explicit, auditable, idempotent call the ship flow makes) over a
`reference-transaction` git hook (implicit, harder to reason about, and a fifth chokepoint).
M-1 is closed; **no intake candidate results.**

**Memory updates:** `specs/memory/product/sdd/sdd-gate-v3.md` — the observation point,
the verb, the ledger's append-before-delete ordering and the idempotent/best-effort posture
are recorded as product truth (no present-tense claim the tree does not support).

### a32-3-literal-vs-net

**Description:** A32.3 asks for "no new accepted edge"; FR27 needed one and FR16 removed two.

**Resolution:** recorded as satisfied **net**, with the full arithmetic in `## Size
accounting` above (16 → 14 → 15, rationale per edge, cap adjusted in the same commit).
Silence would have left the record implicitly claiming zero additions.

**Memory updates:** none — `specs/memory/architecture.md` states layer rules, not the
per-edge ignore ledger, which lives in `setup.cfg` and its contract test.

### fr13-warning-count-was-an-atom-count

**Description:** FR13 folded in "the 12 standing `LINT-1` heading warnings". V3's measurement
showed **12 atoms** carrying **20 distinct headings** — the SPEC's number counted the wrong
unit.

**Resolution:** V3 enumerated all 20 with a per-heading disposition (18 allowlist, 2
atom-fix) and the six-axis review independently re-measured 20. T-043-51 landed all 20 (as 19
unique allowlist lines plus 2 corrected forms and the new governance heading, 22 entries
total). A13.4 holds: `specs doctor` reports **0** `LINT-1` warnings.

**Memory updates:** `specs/memory/.heading-allowlist` (22 entries) and two atoms whose
headings were corrected rather than allowlisted.

### fr17-write-set-label-named-the-wrong-seam

**Description:** TASKS labelled FR17's write set `infrastructure/public_assets.py`; the only
package site that writes the repo-`AGENTS.md` template is
`features/spec_context/service.py:400`.

**Resolution:** the implementer followed the SPEC's prose ("the repo-`AGENTS.md` destination
write") over the stale label and disclosed the correction in the commit message;
`ALPHA-2-QA.md` traced and ratified it. The security round then replaced the two-tier
check-then-copy with a single atomic `os.open(O_CREAT|O_EXCL|O_NOFOLLOW)`, which is stronger
than the four mirrored refusal sites originally specified.

**Memory updates:** `specs/memory/product/distribution/public-asset-distribution.md` — the
atom's pre-existing "destination-file symlink refusal" claim now covers this seam and is true.

### alpha-2-security-round-history-vs-publication-shape

**Description:** the `alpha-2` security review refused the **granular** `feature/0.4.3`
range (2, later 3, objects carrying pre-fix literals in already-authored commits), and the
recommended remediation was a history rewrite. QA r2 upheld it as a HIGH blocker.

**Resolution:** retracted at r3 on reproduced evidence, not on say-so: this workspace ships
`feature/{M.m.p}` → `develop` by **squash publication** (precedent `6e1f9c63`), so the
granular range is never published. QA independently re-derived the synthetic squash
(tree `a50e5b14`, 114 objects) and re-ran the real chokepoint over it: **zero** denylist
blocks. Secondary correction: the pre-push chokepoint does not even apply at an `alpha-N`
close. No history was rewritten; the content-level fixes stand.

**Memory updates:** none — the publication shape is `dadaia-gitflow`'s contract (FR6's own
reconciliation-merge statement lives there), not memory.

### fr20-first-baseline-scope-narrowed-to-the-validated-sub-slice

**Description:** the mutation verdict's first-baseline scope (`core/` + `tests/unit/core/`)
included two flat `tests/unit/core/` files that are cross-layer architecture tests which
mutmut's `mutants/` sandbox — mirroring only `source_paths` — cannot run. A second wiring
finding: the runner's nested venv chained onto the host's default `python3` (3.10) instead
of the pinned 3.12.

**Resolution:** the interpreter bug was fixed at the cause (resolve the workspace venv's own
`pyvenv.cfg` `executable =` line); the scope was narrowed to the verdict's own
already-validated `core/models/` sub-slice under the dispatch's bounded-run clause. A20.1–A20.4
hold at the delivered scope: a named, exactly pinned tool runs to completion off the push
path, and V11 is captured as **evidence, never a gate**. Widening the slice is a run-time
choice for a future baseline, not a fix surface — recorded under `## Record-only
observations`, not intake.

**Memory updates:** `specs/memory/quality-assurance.md` — the tool, its exact pin and the
runnable invocation, so the declared cadence is backed by a command.

### alpha-1-projection-drift-after-the-cycle

**Description:** `ed94f5b0` ran `ruff format` on the two new lint scripts **after**
T-043-11's projection cycle, leaving 2 `[drift]` lines and breaking the segment's own
"V9 all `[ok]`" exit criterion.

**Resolution:** one more projection cycle (`b7ad9123`) and an independent re-capture by QA:
183 `[ok]` / 0 / 0 / 0, both scripts byte-verified against source and both `--self-test`
runs green. Not a product bug — `public doctor` emitting a validation it is designed to emit
— but a real process gap: an edit to a projected source must be followed by its cycle in the
same commit.

**Memory updates:** none — the projection chain is already stated in `DADAIA.md` §7.

### spec-doc-024-transient-during-rc-1

**Description:** after the memory window, `specs doctor` reports a single error,
`SPEC-DOC-024`, raised by the rc-1 phase ladder itself: the release is in `CLOSURE` phase
while its own closure tasks are still completing.

**Resolution:** structural and self-clearing — it disappears with this closure's `git mv`
and `ACTIVE.md` reset. It was recorded, not suppressed, and never masked as "0 errors".
The consumer round independently proved the same check fires correctly and folds to 0/0
in a fresh consumer context (A30.2).

**Memory updates:** none.

## Memory updates

Written in the CLOSURE phase at T-043-51 (`cd24e0fd`), one authoring pass per atom (D9/D21),
exactly the set SPEC §5 declared:

- `specs/memory/tech-stack.md` — PE-2: the false "currently `0.5.0`" parenthetical dropped
  rather than restated with a number that re-stales every release (the one-axis rule makes
  the literal redundant); the third-party pinning doctrine recorded (A1.3).
- `specs/memory/quality-assurance.md` — census sentence re-pinned at the **measured 100**
  and the two justified-timeout citations re-aimed off the consumed slug (A18.6, L-3); the
  intent declaration's shape **and its `tests/e2e/**`-only mechanical scope** stated
  explicitly (A19.3, L-2); the mutation tool `mutmut==3.7.0` with its runnable invocation
  (A20.2); the new **Complexity And Size** governance section (A21.6).
- `specs/memory/.heading-allowlist` — 22 entries: all 20 V3 headings as 19 unique lines,
  the new governance heading, and 2 corrected forms (A13.3 → A13.4).
- `specs/memory/product/sdd/sdd-gate-v3.md` — one pass carrying four FRs: the blob-only
  non-goal retired and coverage stated as blob **+ commit object**, with the header/body
  boundary and the path-less (never-amnestied, fail-closed) semantics as product truth
  (A11.5–A11.7); the baseline cadence, version and single-line constraint (FR12); the
  MEMORY path-class decision (FR13); the venv-guard cache rule (FR28); the push-verdict GC
  audit record and its live observation point (A24.4, FR24 + M-1).
- `specs/memory/product/sdd/sdd-bug-backlog-governance.md` — the non-terminal `picked`
  reservation event and its coherence rules (FR14).
- `specs/memory/product/sdd/specs-doctor.md` — the `tests/AGENTS.md` placeholder check
  (FR8); the baseline-rationale check (FR12); the segment-router ERROR from the Arm-B rider.
- `specs/memory/product/agents/agent-comms.md` — ack-on-consume retention, coordination vs
  artifact-bearing handoffs (FR23).
- `specs/memory/product/agents/agent-monitoring.md` — release-closure GC of run records,
  reconciler reaping, write-time log rotation (FR25, FR26, FR27).
- `specs/memory/product/agents/agentic-entities.md` — the decided `dadaia-cli` reachability
  on the derivation surface (FR5); the skill-collision check (FR2).
- `specs/memory/product/harness/harness-codex.md` — law-load-once for parent **and**
  delegated sessions, live certification, `ENT-DERIVE-1` behavioral fidelity, and the
  version-qualified trust boundary replacing the stale headless-asymmetry framing (FR22).
- `specs/memory/product/distribution/public-asset-distribution.md` — the thin-wrapper
  contract (FR16); the repo-`AGENTS.md` symlink refusal made true (FR17).
- `specs/memory/product/distribution/pypi-distribution.md` — the CHANGELOG lineage
  statement (FR31).
- `specs/memory/product/platform/consumer-agent-support.md` — the round's result and the
  honestly-recorded environment limits (FR30).
- `specs/memory/product/index.md` + `specs/memory/product/catalog.json` — regenerated; six
  overlong `tldr` values compressed to the 160-character cap in the same window.
- `specs/memory/architecture.md` — **no change**: neither FR16's package/wrapper seam nor
  FR14's schema altered a layer contract, and the new modules
  (`features/tmp_gc`, `infrastructure/jsonl_log_rotation`, `features/specs/memory_lint`) sit
  inside existing layers under the existing rules. The `features -> infrastructure`
  ignore-edge arithmetic is `setup.cfg`'s ledger, not memory's.

## Dispositions

**Backlog — 24 consumed slugs.** Each row adds a `## LEDGER` line to
`specs/backlog/BACKLOG.md` in this same commit; the `## ACTIVE` subsections were already
removed at definition by purge-on-pick (SPEC §7 is their provenance record), so `## ACTIVE`
stays **empty**. The twenty-fifth record, `bugs-jsonl-whole-blob-per-append`, is **REJECTED**
by ruling R4 and its line was written in the definition commit — it is not consumed and not
re-dispositioned here.

| Record | Kind | Terminal disposition | Evidence |
|---|---|---|---|
| `specs/backlog/BACKLOG.md` (`test-suite-remediation-stewardship`) | backlog | `DELIVERED · v0.4.3` | FR18 · `## Test dispositions`, `ALPHA-3-QA.md` |
| `specs/backlog/BACKLOG.md` (`consumer-side-validation-round`) | backlog | `DELIVERED · v0.4.3` | FR30 · `ALPHA-6-QA.md` §2, §6 |
| `specs/backlog/BACKLOG.md` (`thin-wrapper-projected-scripts`) | backlog | `DELIVERED · v0.4.3` | FR16 · `b12791cd`, `2c0b9959` |
| `specs/backlog/BACKLOG.md` (`bug-picked-ledger-event`) | backlog | `DELIVERED · v0.4.3` | FR14 · `b001acdd` |
| `specs/backlog/BACKLOG.md` (`codex-persona-law-context-dehydration`) | backlog | `DELIVERED · v0.4.3` | FR22 · `ALPHA-4-QA.md` (A22.1–A22.8) |
| `specs/backlog/BACKLOG.md` (`python-env-interpreter-probe-hardening`) | backlog | `DELIVERED · v0.4.3` | FR9 · `69214f14` |
| `specs/backlog/BACKLOG.md` (`panel-runtime-reliability-dangling-ledger-pointer`) | backlog | `DELIVERED · v0.4.3` | FR15 · `b85302ac` |
| `specs/backlog/BACKLOG.md` (`mutation-testing-tool-selection-and-wiring`) | backlog | `DELIVERED · v0.4.3` | FR20 · V11, `49d50353` |
| `specs/backlog/BACKLOG.md` (`intent-docstring-mechanical-enforcement`) | backlog | `DELIVERED · v0.4.3` | FR19 · `01e3afbb` |
| `specs/backlog/BACKLOG.md` (`gitflow-reconciliation-merge-mechanic`) | backlog | `DELIVERED · v0.4.3` | FR6 · `8556c8e2` |
| `specs/backlog/BACKLOG.md` (`memory-path-class-dotfiles`) | backlog | `DELIVERED · v0.4.3` | FR13 · `9dac383d`, V3, A13.4 |
| `specs/backlog/BACKLOG.md` (`commit-paths-index-scope-hardening`) | backlog | `DELIVERED · v0.4.3` | FR10 · `24a349f5` |
| `specs/backlog/BACKLOG.md` (`commit-message-scanning-residual`) | backlog | `DELIVERED · v0.4.3` | FR11 · `5479b827` |
| `specs/backlog/BACKLOG.md` (`baseline-carve-out-review-cadence`) | backlog | `DELIVERED · v0.4.3` | FR12 · `d4658ae5`…`ce47f1ea` (absorbs the co-author-trailer gap and CR-6) |
| `specs/backlog/BACKLOG.md` (`dd-skills-applyto-glob-collisions`) | backlog | `DELIVERED · v0.4.3` | FR2 (R2 scope) · `584304ee` |
| `specs/backlog/BACKLOG.md` (`dd-release-definition-orchestration-pointer-loop`) | backlog | `DELIVERED · v0.4.3` | FR3 · `f42f69b2` |
| `specs/backlog/BACKLOG.md` (`bug-event-redaction-always-on-reinforcement`) | backlog | `DELIVERED · v0.4.3` | FR4 (R3) · `2cbd74a2` |
| `specs/backlog/BACKLOG.md` (`dd-audit-project-pinned-tool-installs`) | backlog | `DELIVERED · v0.4.3` | FR1 · `8fa6fcca` |
| `specs/backlog/BACKLOG.md` (`dadaia-cli-skill-agent-grant`) | backlog | `DELIVERED · v0.4.3` | FR5 · `03d9b8b9` |
| `specs/backlog/BACKLOG.md` (`codex-skill-ref-phantom-memory-ctx-prefix`) | backlog | `SUPERSEDED · v0.4.3` | merged into `codex-persona-law-context-dehydration` at pick; shipped inside FR22/A22.6 · `2a96e2ac` |
| `specs/backlog/BACKLOG.md` (`dadaia-artifact-event-driven-gc`) | backlog | `DELIVERED · v0.4.3` | FR23–FR29 · `ALPHA-5-QA.md`; FR24's live caller by the M-1 rider `7e6fd30d` |
| `specs/backlog/BACKLOG.md` (`repo-agents-md-symlink-hardening`) | backlog | `DELIVERED · v0.4.3` | FR17 · `bb2a5959` |
| `specs/backlog/BACKLOG.md` (`stewardship-relocation-grep-homonym-note`) | backlog | `DELIVERED · v0.4.3` | FR7 · `3a562a93` |
| `specs/backlog/BACKLOG.md` (`tests-agents-md-placeholder-doctor-warning`) | backlog | `DELIVERED · v0.4.3` | FR8 · `91c5d831` |

**Bugs — 10 Arm-B riders, all `Closed`.** No bug was **picked** into this release: at pick
time the ledger was empty (see `## PE-1` below). Every row below is a bug found *while*
running the release and fixed on the spot under `DADAIA.md` §1 Arm B — never backlog demand,
never release scope. Each carries a complete `reported`→`resolved` pair in
`specs/bugs/bugs.jsonl`; `dadaia bugs status` reports **0 open**.

| Record | Kind | Terminal disposition | Evidence (`reported` → `resolved`, UTC) |
|---|---|---|---|
| `specs/bugs/bugs.jsonl` (`specs-doctor-segment-router-silent-skip`, MEDIUM) | bug | `Closed` | 2026-08-17T14:14:50Z → T17:02:00Z · T-043-22, `29d0f9d0` (AB.1–AB.5) |
| `specs/bugs/bugs.jsonl` (`privacy-baseline-noreply-local-part-not-carved-out`) | bug | `Closed` | 2026-08-17T14:33:25Z → T14:48:54Z · definition-window rider `07c78366` (SPEC §6 D-10); satisfies A12.2, verified not re-implemented by T-043-16 |
| `specs/bugs/bugs.jsonl` (`install-target-doctor-goldens-stale-after-v043-skill-additions`, MEDIUM) | bug | `Closed` | 2026-08-17T15:28:50Z → T15:34:48Z · `alpha-1` rider `1830f8b0` (two golden JSON files, scope verified by `ALPHA-1-QA.md` §3) |
| `specs/bugs/bugs.jsonl` (`skill-orphans-unwired-agent-frontmatter`) | bug | `Closed` | 2026-08-17T18:52:41Z → T19:13:15Z · registered `704a67cb`, fixed `10775510` (3 orphaned skills wired; the wiring test's exemption shrank to empty) |
| `specs/bugs/bugs.jsonl` (`repo-self-scan-hits-alpha2-qa-historical-literal`) | bug | `Closed` | 2026-08-17T19:01:19Z → T19:06:39Z · registered `e23a28e5`, fixed `03bc12d3` (reviewer-quoted literals masked in the committed artifact) |
| `specs/bugs/bugs.jsonl` (`ruff-0-16-2-markdown-python-fence-format-drift`) | bug | `Closed` | 2026-08-17T20:09:20Z → T20:24:17Z · `5b517854` (5 archived Markdown files reformatted by the correctly pinned `ruff==0.16.2`) |
| `specs/bugs/bugs.jsonl` (`t043-33-absolute-path-leaked-into-tasks-md`) | bug | `Closed` | 2026-08-17T21:20:52Z → T21:22:18Z · `8c50e1ca` (a live transcript quoted an absolute workspace path; masked, self-scan RED → GREEN) |
| `specs/bugs/bugs.jsonl` (`self-scan-baseline-drift-t04343-evidence-prose`) | bug | `Closed` | 2026-08-18T00:21:24Z → T00:23:49Z · register `e6563504`, fix `5ff19df2` |
| `specs/bugs/bugs.jsonl` (`ancestor-walk-workspace-root-silent-mistarget`, HIGH) | bug | `Closed` | 2026-08-18T00:51:59Z → T01:12:05Z · found live by the consumer round (`8ca8ac41`), root-caused and fixed inside the segment's budget (`e2eb28f8`, A30.5), 6 RED-then-GREEN tests re-run by `ALPHA-6-QA.md` §3 |
| `specs/bugs/bugs.jsonl` (`self-scan-baseline-drift-pre-pr-review-secrets-prose`) | bug | `Closed` | 2026-08-18T01:59:32Z → T02:01:12Z · `19ddc962` (the review's own secrets-prose example redacted) |

**One clarifying append, not a rider.** FR15 appended a single `archived` event to
`panel-telemetry-sqlite-corrupts-under-concurrent-access` (`specs/bugs/bugs.jsonl:897`,
2026-08-17T16:36:44Z) recording that its 2026-07-01 deferral target was already consumed by
v0.1.52 at deferral time, and naming the corrected disposition with an **existing** token
(R6 — no new token was created). The 2026-07-01 line is byte-unchanged (A15.1–A15.3).

**No audit was in the pick** — both 2026-07 audits are archived and fully dispositioned, and
none was outstanding at pick time or at closure.

## PE-1 — the pick-time precedence record

SPEC §7 claims pick-time precedence (`DADAIA.md` §5: open bugs and undispositioned audits
outrank fresh backlog) was satisfied with **nothing outranking**. That claim is measured,
not asserted:

- `memory-token-estimate-normalizer-dead-code` — `reported` 2026-08-16T19:23:46Z,
  `resolved` 2026-08-17T13:34:22Z (`specs/bugs/bugs.jsonl:889`, commit `7971eefb`): the dead
  normalizer deleted, 38 lines removed / 0 added, full gate green.
- `memory-catalog-regenerator-orphaned-factory` — `reported` 2026-08-17T13:35:00Z,
  `resolved` 2026-08-17T13:38:43Z (`specs/bugs/bugs.jsonl:891`, commit `9a09b551`): the
  orphan factory surfaced while closing the first, closed the same way, 22 lines removed,
  cascade boundary stated.

Both were closed by Arm B **on `develop`**, before the definition commit `c4175ff1` — so the
queue was never picked over an open bug. Recorded for completeness and measured in the same
window: a third bug, `push-gate-refuses-its-own-privacy-baseline-fixtures`, also closed that
morning (`resolved` 2026-08-17T12:59:12Z), likewise pre-pick. **V1** (`dadaia bugs status`,
captured at T-043-02) confirmed the zero-open state at the pick, with the expectation
recorded in advance that the `alpha-2` rider — registered *after* the pick — would appear as
open. Both 2026-07 audits remained archived and fully dispositioned.

## R9 — the operator's open decision (OD-A), restated not decided

**Question.** Should the git commit identity used in this workspace be de-personalised
going forward?

**Status.** Open, and **the operator's alone**. R9 ruled at this release's definition that
the question stays with the operator and is *restated* in CLOSURE rather than decided by any
agent. Both v0.12.0 security reviews dispositioned the existing identity as **pre-existing
published metadata** (1,063 of 1,203 commits at the time) — not a leak, and therefore not a
defect any release is obliged to fix. It is a policy call about future commits.

**Why it is not intake.** An operator-owned policy question is not a backlog residual and
never becomes one (`DADAIA.md` §5: only the operator creates demand). It is carried here so
it stays visible, and it will be restated by the next release that touches the identity
surface until the operator rules. Adjacent and already true: FR11's commit-object scan
deliberately leaves `author`/`committer` **headers** out of scope (A11.6) — they carry the
standing identity on every commit and a header hit could never be amnestied, so scanning
them would make the gate self-refuse permanently. Whatever the operator rules, the gate's
boundary is already the right one.

## Test dispositions

Recorded from the segment's demotion map draft
(`.dadaia/tmp/qa-engineer/20260817/v0.4.3-T-043-26-demotion-map-draft.md`, A18.5). Census
**102 → 100** broad LARGE (pytest e2e 56 → 54; Playwright 46 unchanged): **2 demotions, 0
deletions, 100 keeps** (1 already compliant, 99 backfilled), plus **1 tooling WIRE verdict**
(not a test). Every disposition is a `qa-engineer` verdict with evidence, executed by
`software-engineer` — the steward never edited.

| Kind | Deleted/expired test | Replacement / disposition | Evidence |
|---|---|---|---|
| demotion | `tests/e2e/features/test_panel.py::test_drain_stderr_nonblocking_returns_empty_on_quiet_live_process` | moved verbatim to `tests/integration/features/test_panel_stderr_drain.py` (integration/MEDIUM); implementation-coupled per stewardship §E(c); regression coverage for bug `panel-e2e-readiness-flaky-under-xdist-load` preserved; helper shared via `tests/helpers/subprocess_diag.py` | `cb1986ce` |
| demotion | `tests/e2e/features/test_panel.py::test_drain_stderr_nonblocking_returns_buffered_content` | same move, same file, same commit | `cb1986ce` |
| deletion | — | **none.** No test in the 102-test census met a stewardship §E deletion criterion at the evidence bar the segment's collection-only pass supports | `ALPHA-3-QA.md` (A18.4) |
| retroactive deletion verdict | `tests/unit/scripts/test_lint_memory_atoms.py` (−597 lines, deleted by FR16's move) | **RATIFIED** — all 11 deleted functions mapped 1:1 to surviving counterparts in `tests/unit/features/specs/test_memory_lint.py`, which carries **17** functions against the deleted file's 11; coverage grew | `ALPHA-2-QA.md` "Retroactive test-stewardship verdict"; re-verified `PRE-PR-REVIEW.md` §5 |
| keep + plan-ref backfill | `tests/e2e/panel/spec-context-operation-journey.spec.ts` (registry-absent `test.skip`) | KEEP — legitimate environment guard; skip reason now carries `(AC-4 / E2E-SCP-OP-01, evidence: the e2e-panel CI run)` | `193ca6c4` |
| keep + dangling-pointer re-aim | `tests/e2e/features/test_handoff_pipeline.py::test_full_handoff_emit_and_validate` | KEEP — `timeout(300)` justified (71 s solo vs a 120 s tier default under xdist); docstring pointer re-aimed off the now-consumed `test-suite-remediation-stewardship` slug to `v0.4.3 FR18/T-043-25` | `193ca6c4` |
| keep + Intent/Owner backfill | pytest e2e tier — 12 files / 49 tests | KEEP, `Intent: CONTRACT` + `Owner: software-engineer`, each citing its own AC/bug/task id; docstring-only, zero behaviour change | `e5a205c1` |
| keep + Intent/Owner backfill | `tests/e2e/features/test_panel.py` (4 remaining tests, post-demotion) | KEEP, cites T-5.1..T-5.5 (panel AC-1/2/3/9/10, NFR-2/4) | `cb1986ce` |
| keep + Intent/Owner backfill | Playwright LARGE tier — 10 files / 39 tests | KEEP, header-comment `Intent`/`Owner`, each citing its own FR/E2E id; two files with no prior historical id cite this curation's own mandate (`v0.4.3 A18.2`) rather than fabricating one | `db7f7403` |
| already compliant | `tests/e2e/test_push_denylist_journey.py::test_planted_term_refused_then_clean_push_after_amend` | no action — pre-existing `Intent: CONTRACT — v0.9.0 A9.1, A5.1–A5.3` + owner | `ALPHA-3-QA.md` |
| tooling WIRE verdict (not a test) | `tests/scripts/check_skill_orphans.py` (unwired) | WIRED into the gating suite via a real-repo case in `tests/integration/scripts/test_check_skill_orphans.py`; the 3 known orphans were bug-tracked, then **fixed** by the rider `10775510`, shrinking the exemption to empty | `af51815b` (wiring), `704a67cb` (bug), `10775510` (rider) |
| new mechanical gate | — | `tests/scripts/check_test_intent_declared.py` — an undeclared **`tests/e2e/**`** test now fails the gating suite; green at HEAD the moment it landed (A19.1) | `01e3afbb`; scope recorded in memory per L-2 |
| quarantine / SCAFFOLD expiry | — | **none this release.** No quarantine expired and no SCAFFOLD aged out; the census-freeze rule (D12) held — **zero** new `tests/e2e/**` tests were added in any segment, verified per segment by empty `git diff --stat … -- tests/e2e/` | `ALPHA-1-QA.md` §5, `ALPHA-2-QA.md` |

Suite trajectory across the release: 2312 → 2407 → 2425 → 2436 → 2471 → 2512 → 2576 → 2582 →
**2590** passed, 3 platform-gated skips throughout (2 Windows-only, 1 no-non-loopback-IPv4),
0 failed at every segment close.

## Record-only observations

INFO-grade, awareness-only, or already-resolved-at-HEAD. Never-silent is held — each was
recorded in its reviewer's own artifact or handoff — but none carries an actionable fix
surface, so each **terminates here** and never enters the PM's intake report (FR6/R4).

| Source (reviewer/handoff) | Observation | Why record-only |
|---|---|---|
| `code-reviewer` `PRE-PR-REVIEW.md` INFO-1 | `.import_linter_cache/` is born inside the repo tree; the directory pre-dates this delta, is gitignored (`.gitignore:31`), and `lint-imports` is outside FR28's declared token set (`pytest`/`ruff`/`mypy`) | Not a delta defect and not an FR28 miss — noted for whoever next revisits the cache-guard token set |
| `code-reviewer` `PRE-PR-REVIEW.md` INFO-2 | In `features/tmp_gc/service.py`, a target that passes the lane guard but whose `_remove` returns `False` lands in neither `acted` nor `refused`, so an I/O-failed deletion is silent in the CLI report | The documented, deliberate fail-open posture, matching every other GC lane; named so a future observability pass knows the gap is a choice |
| `code-reviewer` `PRE-PR-REVIEW.md` INFO-3 | Bounded worst-case lock wait on the PreToolUse path: 50 attempts × 2 ms ≈ 100 ms, reachable only when `hook-latency.jsonl` is at the 1 MB cap **and** contended | The common path never takes the lock; the tail is bounded and then fails open — recorded for completeness, not action |
| `qa-engineer` `ALPHA-6-QA.md` §6 (A30.4, verbatim) | Environment limit 1 — the system default `python3` (3.10.12) does not satisfy `>=3.12,<4.0`; `python3.12` was selected explicitly to build the round's runner venv | A documented `Requires-Python` constraint working as intended; no verdict impact |
| `qa-engineer` `ALPHA-6-QA.md` §6 (A30.4, verbatim) | Environment limit 2 — FR24's push-verdict GC could not be exercised end-to-end in a non-pushable throwaway workspace (no live caller at round time) | Recorded **not exercised**, never reported as passed; the underlying gap is now closed by the M-1 rider `7e6fd30d`, so nothing survives to route |
| `qa-engineer` `ALPHA-6-QA.md` §6 (A30.4, verbatim) | Environment limit 3 — FR25's release-closure sweep was out of the round's scope: the scripted `valproj` journey opened a release segment for the marker-discipline demo but never drove it to closure | A scoping choice made to spend budget on the GC surface; FR25 is exercised by **this** closure instead (A25.2) |
| `qa-engineer` `ALPHA-6-QA.md` §6 (A30.4, verbatim) | Environment limit 4 — `dadaia reports validate` had no `--workspace` override at discovery time | **Historical**: registered as F-1 and remediated inside the segment's own budget (`e2eb28f8`); the override now exists |
| `qa-engineer` `ALPHA-6-QA.md` §6 (A30.6, verbatim) | GC coverage **5 of 7** touchpoints live-exercised (ack-on-consume FR23, reconciler reap FR26, log rotation FR27, cache guard FR28, `dadaia tmp gc` dry-run + destructive FR29); **2 not exercisable** — push-verdict GC (no live caller at round time) and the release-closure sweep (out of round scope) | Both exclusions were pre-warned by `ALPHA-5-QA.md` §6.3 and recorded with their reasons; neither was reported as passed |
| `code-reviewer` M-1 → `software-engineer` handoff `2026-08-18T021309Z` | **FR24 wiring history:** the function landed at T-043-39 (`b3335d97`) with no production caller by design (the pre-push hook cannot know a push succeeded); it was wired at rc-1 under M-1 via `dadaia ci gc-push-verdicts` (`7e6fd30d`), which the ship flow runs after a confirmed `develop` push | Already-resolved-at-HEAD; recorded so the history is legible and so memory carries no false present-tense claim |
| `software-engineer` T-043-35 evidence | Two inert allowlist/exception entries are **documented, not removed**: `_CODEX_SKILL_REF_RUNTIME_ASSET_EXCEPTIONS` names `memory-ctx` (a real Codex-only runtime adapter at `public/runtime/codex/memory-ctx/SKILL.md`, not a phantom), and `B903` sits in `ignore` (a preview rule newly activated by `preview = true`, 4 hits, all in `tests/**`) | Both are deliberate, commented at their site, and derived-from-inventory by test; neither is dead configuration nor a fix surface |
| `software-engineer` T-043-28 evidence | The first mutation baseline runs the verdict's validated `core/models/` sub-slice; two flat `tests/unit/core/` files are cross-layer architecture tests mutmut's `mutants/` sandbox cannot run | A20.1–A20.4 hold at the delivered scope; V11 is evidence, never a gate. Widening the slice is a run-time choice for a future baseline, not a defect |
| `product-engineer` T-043-51 | `SPEC-DOC-024` is the sole `specs doctor` error after the memory window — the rc-1 phase-ladder transient (the release sits in `CLOSURE` while its closure tasks complete) | Structural and self-clearing at this closure's archive move; recorded rather than suppressed, and independently proven to fire and fold correctly in a fresh consumer context (A30.2) |
| `qa-engineer` `ALPHA-1-QA.md` §2/§6 | A metrics slip in a commit message and handoff ("7 new tests" vs 6 new `test_*` functions plus 2 helpers) | A counting slip, not a coverage gap |
| `qa-engineer` `ALPHA-2-QA.md` | One integration fixture (`test_commit_paths_ignores_operator_pre_staged_unrelated_content`) carries an acceptance-id section comment but no explicit `Intent:`/`Size:` pair | Unambiguous by directory placement and its acceptance anchor; below the SCAFFOLD bar, and outside FR19's declared `tests/e2e/**` scope |

## Intake candidates

**None. This section is intentionally empty (A32.5).**

**No actionable residual leaves this release.** Every actionable finding raised by any
review in any segment was fixed inside the segment that raised it or, for the one that
reached rc-1, inside rc-1:

- **M-1** (MEDIUM, FR24 not live-wired) — the only finding whose proposed routing would have
  created an intake candidate. It was **resolved in-release** by the ship-flow wiring rider
  `7e6fd30d`, so no operator-ratified deferral is needed and none is claimed.
- **L-1, L-2, L-3** (LOW, all `product-engineer` CLOSURE-accuracy items) — discharged in the
  T-043-51/T-043-52 authoring pass: L-1 as the layer-contract arithmetic in
  `## Size accounting`, L-2 as the explicit `tests/e2e/**`-only scope in
  `quality-assurance.md`, L-3 as the census re-pinned at the measured 100.
- **INFO-1/2/3** and every awareness-only observation — recorded above under
  `## Record-only observations`, where the FR6 calibration terminates them.
- Every defect found in the tooling itself was registered as a bug and fixed on the spot
  (10 Arm-B riders, all `Closed`) — never converted into backlog demand.

`## ACTIVE` in `specs/backlog/BACKLOG.md` is **empty** and stays empty. New demand enters as
it always has: only the operator creates it, and `project-manager` curates it.

## Artifact GC sweep

**Mandatory** (FR25/A25.1); executed here as A25.2 — the first real run of the step this
release itself added. Run after the `## Validations`/`## Dispositions` evidence pointers
above were final, before the archive move. Keep/delete rule: `dd-release-closure`'s
"Artifact GC sweep" section — referenced, not restated. Nothing referenced by a surviving
row above appears in the deleted column (A25.3).

**Lane guard (AG.1, stated verbatim):** resolve the target, refuse any resolved target
outside `.dadaia/`, never follow a symlinked directory.

| Artifact class | Kept (still referenced) | Deleted/archived | Evidence |
|---|---|---|---|
| `.dadaia/handoff/dadaia-workspace/*.handoff.json` (this release) | `8` | `43` | delete list below; this CLOSURE's `## Validations` rows are the keep set |
| `.dadaia/reports/dadaia-workspace/**` (this release) | `5` | `0` | the 4 grill parts + the operator's GC evidence report, all cited by `GRILL.md` §1/§5 and by `## Validations` |
| `.dadaia/tmp/<agent>/**` (this release's captures) | `27` | `24` (20 files + 4 directories) | V3–V11 captures, the verdict/offender/demotion artifacts and the consumer-round artifact are kept; raw logs, scratch renders, superseded review copies and the throwaway workspace are deleted |
| `.dadaia/tmp/**` cache directories (FR29 lane) | `0` | `7` | swept by `dadaia tmp gc` — the release's own `*cache*` lane, unconditional on age |
| lifecycle run records (this release) | `0` | `0` | this release created **none** (the workflow engine is retired). FR26 already reaped 67 zombies as its own V10 evidence; the 54 survivors are pre-existing `blocked` records deliberately excluded from reaping and outside this release's scope |

**Kept handoffs (8)** — each is referenced by a surviving evidence pointer above, or is a
verdict record the ship still needs:

```
.dadaia/handoff/dadaia-workspace/2026-08-17T143200Z-product-engineer-v0.4.3-grill.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T143407Z-security-reviewer-v0.4.3-definition-push.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T145516Z-security-reviewer-v0.4.3-definition-push-rereview.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T173112Z-security-reviewer-v0.4.3-alpha-2-delta.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T182834Z-security-reviewer-v0.4.3-alpha-2-delta-r2.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T222426Z-software-engineer-T-043-39-verdict-gc.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-18T014638Z-code-reviewer-T-043-50-six-axis.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-18T021309Z-software-engineer-review-m1-fr24-wiring.handoff.json
```

**Deleted handoffs (43)** — consumed coordination handoffs of this release whose content is
superseded by a committed artifact (TASKS evidence blocks, `ALPHA-N-QA.md`, `PRE-PR-REVIEW.md`,
this CLOSURE). Every one carries `"artifact": {"type": ...}` with **no** `artifact.path`, so
none is artifact-bearing and none is exempt. Citations of these files by name in committed
artifacts are audit provenance, not live-file dependencies.

```
.dadaia/handoff/dadaia-workspace/2026-08-17T145009Z-software-engineer-privacy-baseline-noreply-local-part.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T151000Z-product-engineer-v043-security-amendments.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T151525Z-ai-engineer-v0.4.3-alpha-1-WS-D.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T153010Z-software-engineer-T-043-10.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T154000Z-product-engineer-v0.4.3-definition.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T154422Z-qa-engineer-T-043-12-alpha-1-review.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T154703Z-ai-engineer-T-043-11-reprojection-fix.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T161500Z-product-engineer-v0.4.3-definition-amended.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T161500Z-software-architect-v0.4.3-fr13-fr14.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T172039Z-ai-engineer-T-043-20-public-thin-wrapper.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T172854Z-qa-engineer-T-043-23-alpha-2-close.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T181522Z-software-engineer-t-043-23-rework.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T181912Z-ai-engineer-reproject-staged-drifted-assets.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T182359Z-qa-engineer-v0.4.3-alpha-2-close-r2.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T183001Z-qa-engineer-v0.4.3-alpha-2-close-r3.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T184211Z-qa-engineer-T-043-24-large-census.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T190357Z-software-engineer-T-043-25-suite-curation.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T191342Z-ai-engineer-skill-orphans-unwired-agent-frontmatter.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T191558Z-qa-engineer-T-043-26-census-remeasure.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T192556Z-software-engineer-T-043-27-intent-check.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T193424Z-qa-engineer-T-043-28-mutation-tool-verdict.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T195940Z-software-engineer-T-043-28-mutation-wiring.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T201251Z-software-engineer-T-043-29-complexity-ratchet.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T201957Z-ai-engineer-T-043-30-size-accounting.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T202700Z-software-engineer-ruff-0-16-2-archive-format-fix.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T203500Z-qa-engineer-T-043-31-alpha-3-close.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T204137Z-ai-engineer-T-043-32-codex-scoping.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T210049Z-ai-engineer-T-043-33-persona-compaction.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T212800Z-software-engineer-T-043-34-codex-trust-boundary.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T214251Z-software-engineer-T-043-35-ent-derive-behavioral.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T140000Z-ai-engineer-T-043-36-codex-docs-reconcile.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T220344Z-qa-engineer-T-043-37-alpha-4-close.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T221017Z-ai-engineer-T-043-38-ack-on-consume.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T223028Z-ai-engineer-T-043-40-closure-sweep.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T225755Z-software-engineer-T-043-41-reconciler-reap.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-17T232931Z-software-engineer-T-043-42-log-rotation.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-18T000321Z-software-engineer-T-043-43-cache-guard.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-18T002900Z-software-engineer-T-043-44-tmp-gc.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-18T004052Z-qa-engineer-T-043-45-alpha-5-close.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-18T005635Z-qa-engineer-T-043-46-consumer-round.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-18T011308Z-software-engineer-T-043-47-remediation.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-18T012508Z-software-engineer-T-043-48-changelog-backfill.handoff.json
.dadaia/handoff/dadaia-workspace/2026-08-18T013315Z-qa-engineer-T-043-49-alpha-6-close.handoff.json
```

**Deleted tmp artifacts (20 files + 4 directories)** — raw logs superseded by the numbers
recorded above, scratch renders, working copies of production files, and the throwaway
consumer workspace (declared disposable by R7 and never committed; its verdict survives in
`ALPHA-6-QA.md` and in the kept round artifact):

```
.dadaia/tmp/qa-engineer/20260817/v0.4.3-alpha-2-qa-review.md
.dadaia/tmp/qa-engineer/20260817/v0.4.3-alpha-2-qa-review-r2.md
.dadaia/tmp/qa-engineer/20260817/v0.4.3-alpha-2-qa-review-r3.md
.dadaia/tmp/software-engineer/20260817/full-pytest-run.log
.dadaia/tmp/software-engineer/20260817/full-pytest-run-modulo-preexisting.log
.dadaia/tmp/software-engineer/20260817/v0.4.3-T-043-28-mutation-run.log
.dadaia/tmp/software-engineer/20260817/v6-raw-c901.txt
.dadaia/tmp/software-engineer/20260817/v6-raw-fullrepo.txt
.dadaia/tmp/software-engineer/20260817/v6-concise-fullrepo.txt
.dadaia/tmp/software-engineer/20260817/T-043-29-gate-ruff-format.log
.dadaia/tmp/software-engineer/20260817/T-043-29-gate-ruff-check.log
.dadaia/tmp/software-engineer/20260817/T-043-29-gate-mypy.log
.dadaia/tmp/software-engineer/20260817/T-043-29-gate-pytest.log
.dadaia/tmp/software-engineer/20260817/venv_guard.py.new
.dadaia/tmp/software-engineer/20260817/venv_guard.py.orig
.dadaia/tmp/software-engineer/20260817/v10-before.txt
.dadaia/tmp/code-reviewer/20260818/pytest-full.txt
.dadaia/tmp/code-reviewer/20260818/specs-doctor.txt
.dadaia/tmp/code-reviewer/20260818/added-lines.txt
.dadaia/tmp/code-reviewer/20260818/v0.4.3-T-043-50-six-axis-review.md
.dadaia/tmp/code-reviewer/20260818/base/                        (directory)
.dadaia/tmp/ai-engineer/20260817/scratch-v7/                    (directory)
.dadaia/tmp/ai-engineer/20260817/scratch-v8/                    (directory)
.dadaia/tmp/qa-engineer/20260818/consumer-round/throwaway-ws/   (directory)
```

**Cache directories (7, FR29 lane)** — swept by `dadaia tmp gc`, which resolves and
boundary-checks every target itself:

```
.dadaia/tmp/mypy-check/
.dadaia/tmp/ai-engineer/20260817/mypy-cache/
.dadaia/tmp/software-engineer/20260817/mypy-cache/
.dadaia/tmp/software-engineer/20260817/mypy_cache/
.dadaia/tmp/software-engineer/20260818/mypy-cache/
.dadaia/tmp/software-engineer/20260818/mypy-cache-t04344/
.dadaia/tmp/software-engineer/20260818/mypy-cache-t04344-full/
```

**Out of scope, untouched:** every artifact of another release (including the v0.4.2
ship/reconciliation handoffs, one of which — `2026-08-17T132720Z-security-reviewer-v0.4.2-main-reconciliation`
— is SPEC §7 provenance for the folded trailer gap), the operator's own `claude`-lane
reports, the pre-pick backlog and bug-fix handoffs of 2026-08-17 morning, and everything
outside `.dadaia/`.

## Archive decision

**MOVE.**

```bash
git mv specs/releases/v0.4.3 specs/_archive/releases/v0.4.3
```

`specs/releases/ACTIVE.md` is set to `release: none` in the same commit — no release follows
immediately; the next one is defined when the operator creates demand. `SPEC-DOC-024` clears
with this move. Per the standing note in `dd-release-closure`, the archive move will add one
`SPEC-DOC-031` WARN per non-terminal `ACTIVE` slug named by the just-archived SPEC/CLOSURE —
here **zero**, because all 25 picked slugs are terminal (24 dispositioned in this sweep, 1
rejected at definition) and `## ACTIVE` is empty. **V13** captures the post-archive
`SPEC-DOC-031` count at T-043-53, never before.
