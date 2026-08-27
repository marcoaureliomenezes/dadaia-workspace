# S4 QA Close — release 0.5.0

**Task:** T-050-33 · **Reviewer:** qa-engineer · **Branch:** `feature/0.5.0` ·
**HEAD reviewed:** `8f912b24` · **Reviewed at:** 2026-08-27T16:09Z
**Scope:** T-050-28 … T-050-32 (SPEC A17–A21, A18.3, V13/V14/V15/V27/V32).
**Preconditions note:** TASKS.md's precondition line reads "T-050-28 … 32 all `[x]`". At
review time T-050-28, T-050-29, T-050-30, T-050-32 are `[x]`; **T-050-31 (the operator
ADR-acceptance sitting) is `[ ]`, unstarted** — this is the expected, pre-announced state
(D12/D-13: only the operator flips an ADR to `accepted`, no agent may perform the step,
and no S4 acceptance depends on it having happened yet). Recorded, not treated as a
blocking precondition failure.

## Verdict: **APPROVE-CONDITIONAL on T-050-31**

Every property this task exists to check (§1–§4 below) holds on the committed tree at
`8f912b24`, verified independently (not merely re-read from the software-engineer/
software-architect artifacts). The one open item is entirely outside this task's or any
agent's control: **T-050-31, the operator's ADR-acceptance sitting, has not happened.**
All 28 ADRs remain `Status: proposed`; zero carries `accepted`, written by an agent or
otherwise. This is not a defect — FR20/D12 forbid any agent from performing that step —
but it is the one condition this verdict is contingent on: Part 1 as written today
documents 28 *candidate* principles, not 28 *ratified* ones, and the constitution's own
"How to read a reference" block (T-050-32) already states this plainly
(`(ADR 00NN proposed)` on every reference). Nothing in S4's own scope is blocked by it.

---

## 1. Property (1) — every Part-1 principle names an executed measure (V14) — **PASS**

Re-verified independently, not merely trusted from `T-050-29-v14.md`:

- **V13** re-run: `grep -c '^\[importlinter:contract' setup.cfg` → **9** (matches P-01..P-09).
- **V32** re-run: `lint-imports --config setup.cfg --no-cache` → `Contracts: 9 kept, 0
  broken.` `modules =` under `[importlinter:contract:features-no-cross-feature]` lists
  all **24** `dadaia_workspace/features/*/` packages (verified by direct read of
  `setup.cfg`), `_RECORDED_IGNORE_EDGE_CAP = 17` (`tests/contract/
  test_import_linter_ignore_cap.py:110`), 5 declared cross-feature ignores with reason
  lines each (checked all 3 new ones name their rationale, not just their pair).
- **3 of the 28 `Measured by:` commands re-run from scratch, chosen at random**, exit
  code and output compared against `T-050-29-v14.md`'s table — **all 3 match exactly**:

  | P-id | Command | Result (this session) | V14 claim |
  |---|---|---|---|
  | P-17 | `pytest -p no:cacheprovider tests/contract/test_behavior_map.py` | `30 passed in 0.60s` | `30 passed` — match |
  | P-10 | `pytest -p no:cacheprovider tests/contract/test_import_linter_ignore_cap.py` | `2 passed in 0.19s` | `2 passed` — match |
  | P-19 | `ruff check --no-cache dadaia_workspace/` | `All checks passed!` | `All checks passed!` — match |

- Spot-checked 6 additional Part-1 entries (`ARCHITECTURE.md` P-01, P-07, P-13;
  `QUALITY.md` P-18, P-24, P-26; `TECHSTACK.md` P-28) directly in the memory files: every
  one carries a `Measured by:` line naming an exact, existing command (not a paraphrase)
  and an `ADR: 00NN (proposed)` line.

**V14 is a one-time capture, stated as such — not misrepresented as a standing gate.**
`T-050-29-v14.md`'s own header says every command "was executed exactly once" and the
inventory file (`S4-principle-inventory.md` §3) frames it as a run-order list, not a CI
job. Nothing in this release wires the 28 `Measured by:` commands into a new CI step —
each already runs as part of the pre-existing `pytest`/`lint-imports`/`ruff` jobs it
promotes, which is exactly what A18.2/V14 requires and no more. A `Measured by:` line
that drifts from its command later is a pillar-3 finding at the next audit, never a
commit-time gate — this artifact says so explicitly rather than implying otherwise.

## 2. Property (2) — zero new *product* checks by FR18 (A18.3) — **PASS**

`tests/contract/test_test_suite_ratchets.py`'s own module docstring states the A18.3
boundary in its own words (read directly, not paraphrased from a review):

> "**The A18.3 boundary, stated once so nobody re-litigates it.** These five properties
> are *test-suite ratchets* — they measure the suite itself, run inside the existing
> `pytest` job, and add zero new CLI surface, zero new doctor code and zero new hook
> exit. A18.3's 'zero new checks' governs *product* checks; it does not reach a contract
> test that fails when the suite it measures regresses."

This is the correct scope reading: A18.3 governs checks that can fail a **consumer's**
tree or block a **human** (doctor codes, CI jobs, hook exits); a `tests/contract/` file
measuring the test suite's own shape is neither. The one genuinely new **product**-facing
test this segment's FR18 work adds is the contract-count / `modules =`-on-disk assertion
inside `tests/contract/test_import_linter_ignore_cap.py` (A18.1 + A18.5) — itself an
**extension of an existing contract test**, not a new doctor code, CLI leaf or hook exit;
confirmed by reading the file: no new pytest module, no new `dadaia` CLI command, no new
hook registered anywhere in this segment's diff (`git log --stat b076b0f2..HEAD` shows
only `tests/contract/*.py`, `specs/ADRs/*.md`, `specs/memory/*.md`,
`specs/constitution.md` and `specs/releases/0.5.0/**` — zero `hooks/`, zero `cli/`, zero
new `doctor*.py` files touched).

## 3. Terminal ADR decisions (FR20/A20.1) — **RECORDED, not yet satisfied (T-050-31)**

```
$ git log --oneline | grep -c 'docs(adr): propose'
28
$ ls specs/ADRs/ | grep -cE '^[0-9]{4}-'
28
$ grep -h "^Status:" specs/ADRs/00*.md | sort -u
Status: proposed
```

All 28 ADRs exist, one isolated `docs(adr): propose NNNN-<slug>` commit each (confirmed:
28 matching commit-message lines, 28 files, exact 1:1). **Every single one reads
`Status: proposed`** — the grep above returns exactly one distinct value across all 28
files. Zero carries `accepted`, so **A20.1's "every inventory ADR has a terminal operator
decision" is not yet met** — this is T-050-31's own job, `[ ]` (unstarted) in TASKS.md,
and no agent may perform it (FR20's own text: "No agent may perform this step").
`tests/contract/test_adr_canon.py` (46 tests, all green) independently proves the
operator-only-acceptance law is enforced (a mutation fixture asserting `Status: accepted`
with no `Accepted by: operator` line is refused) — the mechanism that will gate T-050-31
itself is already correct and tested; only the operator's own action is outstanding.

## 4. Zero new `tests/e2e/**` files (S4 exception check) — **PASS, zero exceptions**

```
$ git diff --diff-filter=A --name-only 7de7c48c..HEAD -- tests/e2e/
(empty)
```

No file was added under `tests/e2e/**` between the S1 QA close commit (`7de7c48c`) and
this review's HEAD (`8f912b24`). No exception to name.

---

## 5. The two inherited debts, as numbers (fold 3, `qa-engineer` amendments 5/8)

### 5.1 `Intent:` coverage (V27)

```
$ grep -rlE "^\s*Intent:" tests --include=test_*.py | wc -l
114
$ find tests -name "test_*.py" | wc -l
408
```

**114/408 declared, 294 undeclared (72.1 %)** — baseline (T-050-18A) was **94/396
declared, 302 undeclared (76 %)**. Delta this release: **+20 declared**, **+12 files
total** (net suite growth stayed inside V25's `after ≤ before` gate on *function* count,
which is a separate measure from file count), **−8 undeclared**. The ratchet direction
V27 requires (UP ONLY on the declared count) is satisfied — declared count moved from 94
to 114, never down — and `check_test_intent_declared.py` continues to gate only
`tests/e2e/**`, so the 294 still-undeclared files sit outside any mechanism that could
ever expire them, exactly as A18.3 leaves it this segment (correcting the gate's scope
is a new check, routed to intake per SPEC V27/QA-Q12, not attempted here).

### 5.2 e2e marker-vs-directory drift (V30)

Measured now, with the methodology stated because the number moves depending on what is
counted:

```
$ grep -rc "^def test_" tests/e2e --include=test_*.py | awk -F: '{s+=$2} END{print s}'
30   # top-level functions
$ grep -rc "^\s\+def test_" tests/e2e --include=test_*.py | awk -F: '{s+=$2} END{print s}'
10   # class-method functions (test_public_pipeline.py's 4 classes)
# => 40 functions total under tests/e2e/**  (baseline was 42 — 2 fewer at this fold)

$ pytest -p no:cacheprovider -m e2e --collect-only -q tests | grep "::" | sed 's/\[.*\]$//' | sort -u | wc -l
40   # distinct FUNCTION NAMES selected by -m e2e (parametrize instances de-duplicated)
```

**Functions under `tests/e2e/**`: 40. Distinct functions selected by `-m e2e`: 40. The
directory-vs-marker drift is effectively CLOSED today (40 = 40), not the 42-vs-15 /
2.8× under-report the SPEC's baseline text describes.** Root cause, traced and confirmed
by reading `tests/conftest.py:118–182`: `pytest_collection_modifyitems` **auto-applies
the `e2e` marker to every collected item whose path starts with `tests/e2e/`**,
independent of whether the file carries an explicit `@pytest.mark.e2e` /
`pytestmark = pytest.mark.e2e` decoration — a pre-existing mechanism (comment cites
T-070-05, landed well before this release). Only **13 of the 40 functions** (across 5 of
14 files) carry an *explicit* `e2e` decoration in source; the SPEC's baseline "15" is in
that same neighborhood, counting the same thing. But because the directory-based
auto-marker already runs on every collection, the **effective** `-m e2e` selector was
never actually under-reporting — it has tracked the directory set all along. The SPEC's
"any `-m e2e` selector under-reports the LARGE tier by 2.8×" framing is corrected here:
that framing was true only of a hypothetical selector that trusted explicit decoration
alone, never of the real one this repository runs.

**Side finding, distinct from the above (not gated, not fixed here — A18.3):**
`tests/e2e/features/test_bound_context_visible_to_cli.py` carries its own
`pytestmark = [pytest.mark.integration]` (a T-69-10-era file, pre-dating the directory
migration) *and* the auto-applied `e2e` marker, so it is currently selected by **both**
`-m integration` and `-m e2e` — a real double-count in any per-tier census (confirmed:
`-m integration --collect-only` on that file also returns 1). One file, one function;
flagged for the same intake routed for the `Intent:` gate-scope extension, not corrected
in this segment.

---

## 6. Bug-surface axis (FR24)

Direction of S4 on the touched surface: **reduced**. Zero new product checks (§2), zero
new `tests/e2e/**` (§4), one existing contract test extended rather than a new one added
(§2), 4 previously-invisible cross-feature edges made visible and capped (V32, inherited
from T-050-29's own evidence, re-verified independently in §1), 261→207 lines of
duplicated law removed from `constitution.md` (V15, T-050-32). No new branch, no new
side effect, no cross-feature reach-in was introduced by this review itself (this task's
own write set is exactly the two files declared in TASKS.md). `dadaia bugs status`: 7
open bugs at review time — none newly introduced by S4's scope; none touch
`ARCHITECTURE.md`/`QUALITY.md`/`TECHSTACK.md`/`specs/ADRs/**`/`constitution.md`.

## 7. Security/privacy leakage note

No credentials, tokens, hostnames, IPs, or consumer-specific slugs were introduced,
observed, or transcribed in this review. All commands were run against the local
workspace tree only; no network calls, no diagnostic output containing a foreign Spec
Context name was pasted verbatim into this file. This report's own write set
(`specs/releases/0.5.0/reviews/S4-qa-close.md`, `specs/releases/0.5.0/RELEASE.jsonl`) is
staged and committed alone, excluding the concurrently-edited
`specs/audits/**`/`specs/bugs/BUGS.jsonl` files another session owns. Not escalated to
`security-reviewer`; no suspected leakage found.

## 8. Memory window closure (AS-12)

The window opened at T-050-28 (`phase: CLOSURE`, ts `2026-08-27T15:32:16Z`) closes with
this task's own `phase: IMPLEMENTATION` record, appended immediately after this file —
same commit, per TASKS.md's write set. `RELEASE.jsonl` was re-read immediately before
the append (a concurrent `project-auditor` session had appended an `audited` record in
the interim); the append below is additive (`>>`), never a rewrite.

## Evidence commands (this review)

```bash
grep -c '^\[importlinter:contract' setup.cfg
.dadaia/.venv/bin/lint-imports --config setup.cfg --no-cache
PYTHONDONTWRITEBYTECODE=1 .dadaia/.venv/bin/pytest -p no:cacheprovider tests/contract/test_behavior_map.py -q
PYTHONDONTWRITEBYTECODE=1 .dadaia/.venv/bin/pytest -p no:cacheprovider tests/contract/test_import_linter_ignore_cap.py -q
.dadaia/.venv/bin/ruff check --no-cache dadaia_workspace/
grep -n "_RECORDED_IGNORE_EDGE_CAP" tests/contract/test_import_linter_ignore_cap.py
git log --oneline | grep -c 'docs(adr): propose'
grep -h "^Status:" specs/ADRs/00*.md | sort -u
PYTHONDONTWRITEBYTECODE=1 .dadaia/.venv/bin/pytest -p no:cacheprovider tests/contract/test_adr_canon.py -q
git diff --diff-filter=A --name-only 7de7c48c..HEAD -- tests/e2e/
grep -rlE "^\s*Intent:" tests --include=test_*.py | wc -l
find tests -name "test_*.py" | wc -l
grep -rc "^def test_" tests/e2e --include=test_*.py | awk -F: '{s+=$2} END{print s}'
grep -rc "^\s\+def test_" tests/e2e --include=test_*.py | awk -F: '{s+=$2} END{print s}'
PYTHONDONTWRITEBYTECODE=1 .dadaia/.venv/bin/pytest -p no:cacheprovider -m e2e --collect-only -q tests
grep -n "pytest_collection_modifyitems\|_PATH_MARKERS" tests/conftest.py
PYTHONDONTWRITEBYTECODE=1 .dadaia/.venv/bin/python -c "from pathlib import Path; from dadaia_workspace.features.specs.doctor_common import resolve_active_release; print(resolve_active_release(Path('specs')))"
dadaia bugs status
```
