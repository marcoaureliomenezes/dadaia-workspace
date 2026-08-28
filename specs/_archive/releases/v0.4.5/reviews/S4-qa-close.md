# S4 QA close — token-economy program (T-045-25 … T-045-30)

**Author:** qa-engineer, 2026-08-26
**Governs:** TASKS.md T-045-31 ("`S4` close: `qa-engineer` review committed")
**Scope reviewed:** `bdb62406` … `96637803` on `feature/0.4.5` (FR11–FR15)
**Independent verification method:** re-ran `measure_v6_v7_v9.py` myself at HEAD (fresh
V8 real bound-session re-measurement too), opened every coverage-table row's named
surviving home directly, `sha256sum` on all four `DADAIA.md` copies, diffed all 9
personas source-vs-projected minus the model/effort overlay, re-ran `dadaia ci
preflight`/`specs doctor`/`public doctor`/`bugs stats` myself — nothing below is taken
on report alone.

## Verdict

**APPROVE.**

## 1. Coverage-table verification (R-4 — no law dropped)

Opened **all 34 rows** (100%, exceeds the ≥50% floor) across both coverage tables at
their named surviving home: T-045-27's 8 `DADAIA.md` compressions (§1/§3/§5/§6/§7/§8/§10
+ header), the 5-persona NO-LOCKS pointer, 8 description negation-rewrites, 5 skill
description rewrites; T-045-28's 12 relocated blocks (spec-navigator directory
reference, `CLOSURE-CHECKS.md` items 4/5/7, `dd-release-definition`/`dd-bug-registration`
§5/`dd-ai-eng-knowhow` Part 2/`CONTEXT-ENGINEERING.md` §4/`dd-release-implement` gate-
cadence pointers, plus the one internal-duplicate deletion needing no home). Every fact
is present at its claimed home; zero rows reject. `[SCOPE ERROR]`/"Write permissions"/
`write_allowlist` blocks confirmed byte-identical via `git diff` on the touched personas
(A13.3) — no scope boundary weakened.

## 2. V6–V9 — re-measured myself, before/after, target verdict

| Metric | Baseline (T-045-25) | After S4 (my re-run, HEAD) | Target | Verdict | Reason (AS-3/A11.4/A13.4) |
|---|---:|---:|---|---|---|
| V6 tokens (Claude Code) | 21527.4 | **20502.0** | ≤3.5k | **MISSED** | Persona bodies (15334.9, 75%) dominate; T-045-27's own scope excludes line-ceiling relocation (that's T-045-28); DADAIA.md alone (2559w/3403.5t) already exceeds the target pre-personas |
| V7 negations (Claude Code) | 299 | **257** | ≤60 | **MISSED, improved** | 226 of 257 (88%) are persona negations, many protected hard-stop sentences; DADAIA.md's own count halved (58→28); T-045-28's pointer idiom "referenced, not restated" added +3 back, honestly flagged in its own coverage table |
| V8 bound-session prefix | 1505.6 | **877.8** (T-045-26, unchanged since — FR12 is the only lever, untouched after) | ≤0.7k | **MISSED, −41.7%** | tech-stack digest floor ~564 tokens is out of FR12's lever (A30.3 pins it); catalog's own remaining floor ≈314 tokens (every entry keeps slug/title/path, A12.3); routed to CLOSURE/PE ratification |
| V9 personas >220 lines | 5 | **5** (my re-run: ai-engineer 252, product-engineer 279, qa-engineer 269, software-architect 250, software-engineer 245) | 0 | **PARTIAL** | Fleet net negative (source 2170→2077, −93; my recount matches T-045-28's 2095-projected claim exactly) — AS-1 bounds the trim to already-existing siblings, never "all under 220"; each residual named with its specific non-relocatable reason in T-045-28's table |

My V6/V7/V9 re-run (`.dadaia/tmp/qa-engineer/20260826/S4-close-v6v7v9-raw.md`) matches
T-045-28-after.md's own after-capture exactly (20502.0/257/2095-projected). My V8 re-run
(fresh real bound session, `.dadaia/tmp/qa-engineer/20260826/v8-stdout.txt`) reproduced
7393 chars/660 words/877.8 tokens exactly, matching T-045-26's after-capture. All four
misses/partial are honest, each with a recorded reason — no target was silently
redefined.

## 3. Acceptance evidence (A11.1–A15.3)

| Id | Evidence | Verified |
|---|---|---|
| A11.1–A11.4 | T-045-25-baseline.md (method+baseline), T-045-27-coverage-table.md, T-045-27-after.md ("Target: MISSED" section, both V6/V7) | Re-measured myself, §2 |
| A12.1–A12.4 | T-045-26-v8-after.md; `git diff --stat -- hooks/ctx_inject.py` empty across `bdb62406..HEAD`; `test_persisted_catalog_tldr_curation_shrinks_ctx_inject_digest` + `test_memory_catalog_render_contract.py` (AM-1 twin parity) | Re-ran — 33/33 catalog tests green; diff confirmed empty myself |
| A13.1–A13.4 | T-045-28-coverage-table.md, T-045-28-after.md (per-persona table + reasons) | Re-measured myself, §2; `[SCOPE ERROR]`/write-allowlist diff-confirmed unchanged |
| A14.1 | `ai-engineer.md:218` cites `DADAIA.md` §8 (was §5); `dadaia public doctor` clean (no `[drift]`/`[missing]`) | Read directly; ran doctor myself |
| A14.2 | `tests/contract/test_rules_skills_map.py -k citation` | Ran myself — 3 passed |
| A14.3 | `af7bd369`+`a4754a28`; full `dadaia ci preflight` green | Ran myself — pytest 2868 passed, 4 skipped (platform-gated) |
| A15.1 | `dadaia-test-stewardship/SKILL.md:32` "REGRESSION/BUG are not tokens" | Read directly |
| A15.2 | `grep -rn -E 'Intent: *(REGRESSION\|BUG)\b' tests/` → zero hits, exit 1 | Ran myself |
| A15.3 | Not yet written — correctly deferred to release `CLOSURE.md` (S4 close ≠ release close), same posture as S2's A2.7 | Confirmed CLOSURE.md does not exist yet |

## 4. FR23 Firing 3 — amendments applied

`5c4f30c9` net +59 (ruled SOUND-WITH-AMENDMENT). Both applied in `d85dfc19` **before**
`[x]`: AM-1 (twin `generate-memory-catalog.py` now imports the shared
`curate_catalog_for_persistence()`, F-84 contract extended to pin both **written**
`catalog.json` texts — RED-then-GREEN per the commit message) and AM-2 (27-line prose cut
to essentials, net for the whole task down to +16 from the ruling's measured +59). I
independently ran the extended F-84 + catalog suite — 33 passed.

## 5. Gates at HEAD (`96637803`)

```
dadaia ci preflight            -> PASS (ruff format/check, mypy --strict, lint-imports, pytest — 2868 passed, 4 skipped)
dadaia specs doctor --json     -> errors 0, warnings 4 (same 4 pre-existing legacy items S1/S2/S3 already recorded)
dadaia public doctor           -> [ok] public-privacy, [ok] entities-derivation, no [drift]/[missing]
dadaia bugs stats              -> total 493, status:open 2 (see §7 — was 1 at dispatch time)
sha256(DADAIA.md source)       -> c51a5c21… identical across public/data/, root, .codex/, .kimi-code/
9 personas source-vs-projected -> byte-identical, minus the model:/effort: overlay lines
```

One transient full-suite failure was hit during my own preflight run
(`test_staging_step_copies_scoped_subset_without_touching_repo_git_tree`) — re-ran in
isolation (green) and re-ran the full suite (green): a genuine pass+fail-on-same-code
flake, root-caused to the test's `git status --porcelain` before/after window racing a
concurrent live session's legitimate ADDITIVE write (`specs/backlog|bugs/probe-*.md`),
which NO-LOCKS DOCTRINE explicitly permits. Registered per §F of the stewardship skill:
`mutation-baseline-wiring-test-flakes-under-concurrent-additive-writes` (LOW, `reported`
only — quarantine/fix is a separate verdict, out of this close's write set).

## 6. Definition drifts (recorded, not blocking)

- SPEC FR13 / TASKS.md T-045-28 both name "four" over-ceiling personas; the measured
  baseline (and my own re-run) finds **five** — `software-engineer` (245) was omitted
  from both. T-045-28 correctly included it per the dispatching agent's instruction and
  recorded the drift in its own coverage table; SPEC's wording still needs the operator/PM
  reconciliation at release CLOSURE.
- T-045-29: TASKS.md names `ai-engineer` as sole owner; F-7/F-8/F-10 are production
  Python outside `public/**` (ai-engineer's scope forbids writing production code), so
  `software-engineer` correctly swept them in `a4754a28` after `ai-engineer`'s citation
  fix in `af7bd369` — two agents, two commits, one task id, both zero-behaviour-change.

## 7. Intake candidates (not bugs, routed for the PM's intake — list only, not fixed here)

1. Tech-stack digest floor (~564 tokens, `_digest_tech_stack`) is the next V8 lever, out
   of FR12's scope (A30.3-pinned) — a future FR would need to touch `ctx_inject` itself.
2. `_TLDR_INJECTED_CATEGORIES = frozenset({"core"})` (today: drop-all, no atom carries
   `category: core`) is a mechanism with a proposed default — PE ratification pending,
   or explicit disposition of the ~178-token V8 residual gap as an honest miss.
3. `dadaia-step0-memory-bootstrap`'s "tldr/summary" wording should read "summary" (the
   persisted file no longer carries `tldr` under the live default).
4. T-045-28's "referenced, not restated" pointer idiom trips the V7 negation regex (+3);
   reword positively (e.g. "canonical home:") in a future pass, without reopening scope.
5. T-045-30's own scan: **no test enforces the Intent-token taxonomy** — a lightweight
   contract test grepping `tests/` for `Intent: *(REGRESSION|BUG)\b` would catch
   regrowth of this drift class; not implemented (out of T-045-30's dispatched scope).
6. My own flake finding (§5) — a fix/quarantine decision for
   `mutation-baseline-wiring-test-flakes-under-concurrent-additive-writes`.

## 8. Bug-surface axis (operator's standing order)

**AI-surface always-on budget class.** History: v0.4.4 landed the diet program's first
pass (~8.4k→~8.2k-11.8k, still over) and left `always-on-token-diet`/
`memory-catalog-digest-trimming`/`persona-line-ceiling-trim` as backlog. S4 continues the
same structural direction (measure once, cut in contribution order FR12→FR11→FR13,
D-6) rather than a fresh symptom patch: V6 −4.8% (21527→20502), V7 −14.0% (299→257), V8
−41.7% (1505.6→877.8), V9 fleet lines −4.3% (2170→2077 source). None of the three
targets close this segment — an **honest** structural constraint (persona-body mass and
the tech-stack floor are the dominant remaining contributors, both named), not a
recurrence of a previously-"fixed" symptom. **No duplicated-law instance survives
uncollapsed**: the 5×-repeated NO-LOCKS restatement is now one pointer (T-045-27), 12
persona-internal/cross-persona duplicate blocks are now pointers to their single
canonical home (T-045-28) — exactly the "collapse duplicated law → pointer" shape the
standing order asks for, verified at every named home in §1.

**Stale-citation class** (recurring: `t044-04-renumber-stale-DADAIAmd-section-citations`,
`dadaia-task-manager-stale-workspace-protocol-citation`, now `ai-engineer`'s F-3 §5→§8):
FR14 closes this instance at source with the same enforcer (`test_rules_skills_map.py`)
that caught the prior two — not a new mechanism per recurrence, the existing citation
check is reused each time; the class itself (DADAIA.md renumbering silently staling a
persona's own citation) has no structural close yet in this release — worth naming for
the PM's intake as a candidate for a numbered-anchor or automated-citation-update lever,
not fixed here.

**Net this close:** 1 new LOW bug registered (test-isolation flake, §5), 0 new HIGH/
CRITICAL, workspace-wide open count 1→2 (the pre-existing `windows-xdist-…` LOW plus
mine) — both LOW, neither blocks APPROVE.

## 9. Security/privacy leakage note

None. Every S4 diff stays inside `dadaia_workspace/{public,features}/**` and `tests/**`.
`dadaia public doctor` reports `[ok] public-privacy` after every re-projection in this
segment. No secrets, tokens, credentials, consumer-specific data, or home-absolute paths
in any S4 commit or in this document. No new third-party dependency. `dadaia bugs stats`
confirms no bug reopened and no unregistered pass-on-retry (the one flake is registered,
not silently rerun).

## 10. What S4 left unevidenced

Nothing in S4's acceptance/evidence map is unevidenced. A15.3's CLOSURE statement is
correctly deferred to the release-wide `CLOSURE.md` (not yet written), same posture as
S2's A2.7. FR12's PE-ratification of the default tier frozenset is likewise correctly
deferred, per T-045-26's own text.
