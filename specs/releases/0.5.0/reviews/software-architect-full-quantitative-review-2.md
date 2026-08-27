# software-architect — verification pass on fold 3 (review 2)

**Reviewed at:** commit `fccd652a` — SPEC §9.3 (22 rows) and every FR/AS/A/V/T it cites, read
against the live tree. **Mode:** REVIEW, verification of `software-architect-full-quantitative-review.md`
§9 Q1–Q10 and §11. Every claim the fold makes about the tree was re-checked by inspection, not
transcribed: `cli/commands/specs.py` lines 26/28 (`release`/`segment` groups) and 367/397 (each
group carries **only** `open`, so deleting the two verbs deletes the groups whole);
`cli/commands/bugs.py` registers exactly `append`/`status`/`stats` (119/281/310);
`features/*/__init__.py` globs **24**, `setup.cfg:178–197` lists **20**, the four missing are
`capabilities`, `certification`, `reconcile`, `tmp_gc` — the fold's corrections of my 25/5 figures
are right.

## 0. architect-core-workflow (carried)

Core problem, constraints, success criteria and prior art are unchanged from review 1 §0. The one
assumption re-examined here: "the fold's numbers describe the tree" — verified above.

## 1. Q1–Q10 dispositions

| Q | Status | Evidence / what is missing |
|---|---|---|
| Q1 one `BUGS.jsonl` seam | **CLOSED** | FR2 one-seam paragraph, A2.13 fixture exercises all three writer roles; AS-16 fixes the seam and gates only the door; T-050-08 write set conditional on (i)/(ii); leaf offset verified real (T-050-21A, `_write_active` 390/428) |
| Q2 FR23 triple | **CLOSED** | write-once category, A2.11, FR3 6d/A3.11 carry + count, FR14 metric 2 baseline 23/92 |
| Q3 no `specs upgrade` automation | **CLOSED** | §1.6 row, FR1 paragraph, A1.4 zero-diff on `upgrade.py`, `--recipe` in its own function, V35 `#upgrade ≤ 26 / #doctor ≤ 30`, §4.9 intake |
| Q4 derivation in `core/` | **CLOSED** | `core/bug_provenance.py` stdlib-only, `migrate_v5.py` adapter+table+runner deletable, contract test "no permanent consumer imports `migrate_v5`", CONTRACT/SCAFFOLD split (QA-Q10) |
| Q5 `surface` enum | **CLOSED** (applied-modified, better than asked) | one source with A18.5; 24 packages + 6 layer arms + `unknown`. Note: the 6 non-feature arms (`core`…`public-assets`) are a small hand list (+1 constant) — acceptable, name it in A2.12 |
| Q6 eight metrics | **CLOSED** | FR14 table with definition/command/baseline/carrier, A14.7, V33 "fewer than eight is incomplete", metric 7 declared worse on purpose |
| Q7 public-assets exposure | **CLOSED** (split) | FR10A deletion-only in `tests/`, A10A.3 bounds it out of `infrastructure/`; AS-17 defers 3 engines by bug id with intake target; exposure quantified (10 cycles) — quantified, not capped: see §3 |
| Q8 independence contract | **CLOSED** | A18.5/V32 24/24, 3 reconcile edges declared with reason, cap 15 → 17 in the same commit, principle only after |
| Q9 test economy | **PARTIAL** | V25–V35 land. Missing: the roll-up does not close — see §2 "tests total" |
| Q10 textual closure | **CLOSED** | `release_events.py` read-only + file-tool append seam named (FR4), A13.4 store-only-where-writer, A13.6, A8.3 verb corrected, V9 three refusals, V34 ceiling +500, `_OPTIONAL_STR_FIELDS` deleted (A2.10) |

## 2. The operator's axes — before → after, as now specified

| Axis | Before → after | Where |
|---|---|---|
| Cross-feature module edges | 5 → **5** (visible to the check 2 → 5; declared ignores 2 → 5; cap 15 → 17; collapse routed to intake) | A18.5, V32 |
| Two-writers-of-one-truth | 14 → **12**; the two fold-2 regressions closed: `BUGS.jsonl` 3 writers → **1 seam**, `RELEASE.jsonl` 1 writer class append-only, stated | FR2, FR4, AS-16 |
| Hand-kept truth constants | 264 → **≈258** (−13/+7 named) **− N** rosters (FR10A, measured at task) + 2 declared `memory_lint` headings | FR1/2/5/10A/15/17 |
| Doctor check codes | 47 → **≤ 45**, post-release **list** recorded in V19 | FR1, FR15 |
| CLI leaf commands | 71 → **71** under AS-16(i) (+`update` +`archive` −`release open` −`segment open`) / **69** under (ii) | AS-16, T-050-08/21A |
| Hook hard-exit scripts | 2 → **1**; human-blocking hooks at commit 2 → **0**; pre-push refuses exactly 3 | FR9, A22.6, V9 |
| Side-effect call sites | 358 → **≈360**; FR3 +4 stated, `core/release_events.py` +0 proven; no release-wide total is pinned (V19 counts LOC, not sites) — unchanged ±1 %, acceptable | FR3, FR4 |
| Test functions | 1 859 → gate **≤ 1 859** (A22.9). As written the per-FR `Tests:` lines sum **+56 / −32 = +24**, and T-050-18A's +5 (TASKS) appears in no FR line (FR22 reads +0/−0) → **+29** on paper; the only route to ≤ 0 is T-050-21A's **unquantified −N** (26+4 `ACTIVE.md`/`CLOSURE.md` census) plus the closure demotion map | V25, A22.9, T-050-18A, T-050-21A |
| Private-symbol imports | 24 → **0** target, ratchet down only, residue routed | V26 |
| Undeclared-intent test files | 302 → **0** target or per-segment ratchet carrying its number | V27 |
| Always-on tokens | 21 511 → **≤ 22 011** | V34 |
| Loop metrics measured | 2/8 → **8/8** | A14.7, V33 |

**On the tests axis (the one PARTIAL).** The SPEC's own arithmetic promises a gate it cannot show it
meets: FR lines say +29, the gate says ≤ 0, and the balancing deletion is a letter. A22.9 already
carries the honest resolution protocol (demotion map or explicit operator-accepted overshoot with the
number), so this is an accounting contradiction, not an architecture one. Two textual fixes at
promotion: (a) FR22's `Tests:` line reads `+5 / −0 (T-050-18A)`; (b) T-050-21A states a **floor**
for −N from the 26+4 census (the files exist today; a `grep -l ACTIVE.md tests` count is inspection,
not prediction), so the roll-up sums to a number the operator can compare with 1 859.

## 3. AS-16 and AS-17 judged

**AS-16.** Option (i) `dadaia bugs update <id> --set <field>=<value>` is consistent with D8 and D15.
D8 forbids the *lineage check* becoming CLI validation; D15 forbids new *blocking* surface. A
governance writer validates nothing, blocks nobody, exits 0 (A8.3), and refuses only core fields at
the seam (A2.2a) — a refusal that exists under (ii) too. The "CLI only at the publication boundary"
reading does not bite either: the ledger already has a CLI door (`bugs append`); `update` is the
second half of the same door, not a new one, and the leaf count is neutral at 71 because two verbs
that write a file this release deletes are removed. Option (ii) is the puxadinho shape: a second,
undocumented invocation path (`python -m …`) that every skill must spell correctly with no `--help`
and no output-stability fixture — exactly the hidden coupling the standing order refuses. It also
weakens A2.13: a fixture proving "all three writers use the seam" is strongest when the writers have
one executable entry. **Recommendation: (i).** The operator decides; the seam is identical either way.

**AS-17 honesty.** Honest. The three engines are named by bug id, sized against the tree
(`infrastructure/public_assets.py` 1 048 LOC, `#doctor` CC 40), given one intake target bound by
A10A.4, and the exposure is quantified (10 projection cycles, 1 rename, 1 add, 5 scoped
`AGENTS.md`). What the fold did **not** do is cap that exposure: no per-cycle check or S1–S4 count of
bugs registered with `surface: public-assets`. The `surface` enum makes that count free at FR16
(metric 4 grouped on `public-assets`) — ask T-050-34 to report it. Deferral stated out loud, target
named, cost measured: that is the honest form.

## 4. Gates

- **Root-cause gate: PASS.** No symptom patch entered the fold; the one growth on the chain-1
  surface (`specs upgrade`) was cut (Q3).
- **Architecture-fidelity gate: PASS.** The three misrepresentations (three writers, derivation in a
  deletable module, caller-less findings store) and the false-at-birth principle are closed with
  mechanisms verified against the tree, not prose.
- **Bug-surface axis (FR24, `dd-bug-registration` §5):** on the touched features the definition
  **reduces** the surface — `BUGS.jsonl` 3 writers → 1, two-writers 14 → 12, prose regexes 22 → ≈9,
  hook blocks −2, doctor codes −2, leaves ±0, one roster engine of public-assets deleted; on
  spec-context it is **unchanged and says so**. Nothing in the fold adds a branch, flag or second
  path to an existing feature.

## 5. Verdict

**APPROVE-DEFINITION** — ready for the operator's `Aprovado`, with one textual amendment carried
into the promotion commit (§2 tests axis: FR22 `+5`, T-050-21A floor for −N). It changes no
architecture, no ruling, and no task; without it the operator approves a test gate whose paper sum
is +29 against a promise of ≤ 0, which A22.9 then resolves at closure — honest, but a number the
operator should see before signing rather than after.

## 6. "Fica mais limpa ou mais suja?"

Cleaner, and now measurably where it was only asserted at fold 2. Ledger: writers of `BUGS.jsonl`
3 → 1 on the executed path, two-writers-of-one-truth 14 → 12, FR23 evidence 25 % → target 100 %,
loop metrics 2/8 → 8/8. Structure: doctor codes 47 → ≤ 45 with the list pinned, regexes over prose
22 → ≈9, hook hard exits 2 → 1, human-blocking hooks 2 → 0, CLI leaves 71 → 71, hand-kept constants
264 → ≈258 − N rosters, `ignore_imports` 15 → 14 → 17 but with 24/24 packages under the contract
(3 edges made visible, not created), `specs upgrade` CC 26 → ≤ 26, ruff ceiling 63 → 61. Test suite:
1 859 → ≤ 1 859 gated, 24 → 0 private imports, 302 → 0 undeclared, one LARGE number. Still not
smaller: cross-feature edges 5 → 5, side-effect sites ≈358 → ≈360, always-on tokens +≤500,
production LOC +≈1 %, spec-context 0 of 10 bugs' engines touched, public-assets 1 of 4. Net: the
release cleans ≈40 % of the bug-producing surface, measures 100 % of it, and — this is what changed
at fold 3 — no longer dirties the one artifact it exists to make trustworthy.
