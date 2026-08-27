# Test minimization literature review — cross-checked against this repo's doctrine

**Scope.** Operator question: cleaner architecture, FEWER tests, minimization that keeps
coverage and value, never again an unmarked temporary test, and tests that ossify the
architecture. Part 1 grounds each theme in literature fetched on 2026-08-26 (every claim
carries the URL actually read). Part 2 maps the rules onto `dadaia-test-stewardship`
(`SKILL.md` + `PARAMETERS.md`), `tests/AGENTS.md` and `specs/memory/quality-assurance.md`.
Part 3 is the measurable rule list for 0.5.0. Repo counts were measured on the working tree
(`find`/`grep`), not estimated.

Fetch failures (recorded so nobody cites them as read): Beck's Medium post (403; the same
text was read at testdesiderata.com), Khorikov's blog post on the four pillars (404; the
Manning chapter-4 outline and his "When to mock" post were read instead), the van Deursen
2001 PDF (404; testsmells.org catalog used as the secondary source), Rothermel 2002 / Yoo &
Harman 2012 full texts (403/refused; the ICSM'98 abstract sentence came via search).

---

## Part 1 — What the literature says

### 1.1 Kent Beck, "Test Desiderata" — https://testdesiderata.com/

Twelve properties, each a one-liner. The ones this review turns on:

- **Structure-insensitive** — "tests should not change their result if the structure of the
  code changes". This is the anti-ossification property: a test that breaks when a private
  helper is renamed, a module is split, or a string literal moves is structure-sensitive.
- **Behavioral** — "tests should be sensitive to changes in the behavior of the code under
  test". Behavioral + structure-insensitive together define a test that pins the *contract*
  and frees the *implementation*.
- **Isolated** — "tests should return the same results regardless of the order in which they
  are run". **Deterministic** — "if nothing changes, the test result shouldn't change".
- **Predictive** — "if the tests all pass, then the code under test should be suitable for
  production". **Specific** — "if a test fails, the cause of the failure should be obvious".
- Trade-off stated by Beck: "Making tests more predictive of production behavior makes them
  slower"; composability is his resolution (test dimensions separately, combine the results).

### 1.2 Fowler "TestPyramid" — https://martinfowler.com/bliki/TestPyramid.html

"Tests that run end-to-end through the UI are: brittle, expensive to write, and time
consuming to run." "An enhancement to the system can easily end up breaking lots of such
tests." The inverted shape is the **ice-cream cone**. High-level tests are a "second line of
test defense" to catch gaps below, not the primary validator.

### 1.3 Vocke, "The Practical Test Pyramid" — https://martinfowler.com/articles/practical-test-pyramid.html

Two rules: "Write tests with different granularity" and "The more high-level you get the fewer
tests you should have". Push "your tests as far down the test pyramid as you can". When a
higher-level test catches what a lower one should have, add the lower test. **Delete**
higher-level tests already covered lower unless they add value; keeping them because they
were expensive to write is the "sunk cost fallacy". Do not test private methods — refactor
the logic into its own unit instead.

### 1.4 Software Engineering at Google, ch. 11 — https://abseil.io/resources/swe-book/html/ch11.html

- Sizes: **small** "must run in a single process", no sleep/I/O/blocking; **medium** may use
  threads, processes and `localhost`; **large** may span machines.
- Beyoncé rule: "If you liked it, then you shoulda put a test on it" — test the behaviors you
  want preserved, and only those.
- Brittleness: tests "can actually resist change" when they "over-specify expected outcomes or
  rely on extensive and complicated boilerplate".
- Mix target: ~80 % small / 15 % medium / 5 % large. Flakiness: "as you approach 1 %
  flakiness, the tests begin to lose value"; Google sits at ~0.15 %.

### 1.5 Software Engineering at Google, ch. 12 — https://abseil.io/resources/swe-book/html/ch12.html

- **Unchanging tests**: "after it's written, it never needs to change unless the requirements
  of the system under test change."
- **Brittle test** := "fails in the face of an unrelated change to production code that does
  not introduce any real bugs."
- Test **via public APIs**; test **state, not interactions**; test **behaviors, not methods**
  ("any guarantee that a system makes about how it will respond"); **don't put logic in
  tests** ("something has gone wrong if tests start becoming complex enough that it feels
  like they need their own tests"); **DAMP over DRY**.

### 1.6 Hyrum's Law — https://www.hyrumslaw.com/

"With a sufficient number of users of an API, it does not matter what you promise in the
contract: all observable behaviors of your system will be depended on by somebody." A test
suite is such a user: every test that asserts on an incidental behavior (exact message text,
private constant, call order) converts that incident into a de-facto contract and ossifies it.

### 1.7 Khorikov — https://livebook.manning.com/book/unit-testing/chapter-4/ and https://enterprisecraftsmanship.com/posts/when-to-mock/

Chapter 4 lists the four attributes of a good test: protection against regressions,
resistance to refactoring, fast feedback, maintainability. In "When to mock":
"intra-system communications are implementation details"; "inter-system communications form
the observable behavior of your system as a whole"; "Asserting interactions with stubs always
leads to fragile tests". Khorikov's book-level stance (not verbatim-fetched, stated here as
the reviewer's reading of ch. 4): resistance to refactoring is binary — a test either couples
to implementation details or not — and is the pillar not to trade away; tests that fail on
refactors are false positives and are the deletion candidates.

### 1.8 Feathers, characterization tests — https://michaelfeathers.silvrback.com/characterization-testing

Tests that "document your system's actual behavior, not check for the behavior you wish your
system had"; their purpose is to "build up our knowledge of what the code actually does" before
a refactor or rewrite. They are not specification tests. Consequence for this repo: a
characterization test is a **scaffold by construction** — it earns permanence only when it is
rewritten as a behavior (CONTRACT) assertion, and must be labelled as temporary from birth.

### 1.9 Mutation testing — https://research.google/pubs/state-of-mutation-testing-at-google/ and https://mutmut.readthedocs.io/en/latest/

Google surfaces surviving mutants inside code review; it fights unproductive/equivalent mutants
by skipping "arid lines" via "a heuristic for judging whether a node is arid or not,
conditioned on the programming language", and runs on "about 30 % of all diffs across Google
that have statement coverage calculated". The signal: a *surviving* mutant marks a behavior
nobody asserts; a test that kills no mutant on its own detects nothing. mutmut classifies
killed vs survived, has `mutmut run` / `browse` / `apply`, and a stack-depth filter to cut
incidental coverage; it does not solve equivalent mutants, so the score is a floor with a
human-triaged remainder.

### 1.10 Test-suite minimization — https://ieeexplore.ieee.org/document/738487/ (abstract via search), https://onlinelibrary.wiley.com/doi/10.1002/stvr.430

Rothermel, Harrold, Ostrin, Hong (ICSM '98): "the fault-detection capabilities of test
suites can be severely compromised by test-suite reduction" — coverage-preserving reduction
keeps statement/branch coverage but loses fault detection. Yoo & Harman 2012 survey split the
field into minimization (permanent removal), selection (per-change subset) and prioritization
(ordering). Lesson: reduce on *behavior* and *mutant-kill* evidence, never on coverage alone.

### 1.11 Coverage — https://martinfowler.com/bliki/TestCoverage.html

"Test coverage is a useful tool for finding untested parts of a codebase. Test coverage is of
little use as a numeric statement of how good your tests are." "High coverage numbers are too
easy to reach with low quality testing." Enough testing := rare escapes to production and
rarely "hesitant to change some code for fear it will cause production bugs".

### 1.12 Test smells — van Deursen et al. 2001 via https://testsmells.org/pages/testsmells.html

Eager Test ("a test method invokes several methods of the production object"), Assertion
Roulette (multiple undocumented assertions), Mystery Guest (external resources), **Sensitive
Equality** (asserting on a rendered string / `toString`), General Fixture, Lazy Test,
Conditional Test Logic, Redundant Assertion, Magic Number. Tests that pin private symbols or
exact message strings are the sensitive-equality / structure-sensitive family.

---

## Part 2 — Cross-check against this repo's doctrine

Sources: `dadaia_workspace/public/skills/dadaia-test-stewardship/SKILL.md` (+ `PARAMETERS.md`),
`tests/AGENTS.md`, `specs/memory/quality-assurance.md`, `DADAIA.md` §7.

### Already doctrine (exact clause)

| Literature rule | Where it lives | Clause |
|---|---|---|
| Sizes small/medium/large (Google) | SKILL §C, memory "Layers" | "SMALL = `unit` + `contract`; MEDIUM = `integration`; LARGE = `e2e`" with per-tier timeouts; "A test that needs more time than its tier's timeout is mis-tiered" |
| Push tests down / delete higher-level duplicates (Vocke) | SKILL §C, §D | "Assert at the cheapest tier that detects the failure"; demotion: each LARGE "yields file:line of the equivalent SMALL/MEDIUM coverage … or is kept as the seam's single SENTINEL" |
| One behavior per test, observable effect (Google, Beck) | SKILL §B | "One test per behavior, asserting only on observable effect" |
| Change-detector / tautology ban (Google "brittle", Khorikov) | SKILL §B | "Prohibited: change-detector tests (mirror the implementation); tautologies …; reflex-regenerated snapshots" |
| Temporary tests must be labelled and expire (Feathers) | SKILL §A, DADAIA.md §7 | "An undeclared test is SCAFFOLD — the default is to die, not to stay"; SCAFFOLD "expires at its closure" |
| Flake quarantine bounded (Google 1 %) | SKILL §F, memory "Flake Policy" | quarantine requires bug id, refused at collection; cap 8; 30 d → `disabled`; flake ceiling 1 %, target 0.5 % |
| Mutation score as value judge (Google) | SKILL §H, memory "Test Health" | "a test that kills no mutant and is not a SENTINEL enters the next curation pass"; `mutmut==3.7.0`, `run_mutation_baseline.sh`, 1×/release off push path |
| Coverage is a floor, not a target (Fowler) | memory "CI" | "The 80 % floor … a by-product metric — never an acceptance target, never a reason to write a test" |
| Do not pin private symbols / strings | `tests/AGENTS.md` "No Slop" | "Do not add tests for … private implementation strings unless they protect a documented security or compatibility contract"; "Do not duplicate private constants in tests as the source of truth" |
| Tombstone ban (no tests of history) | SKILL §E | "validates a historical event, not a live behavior … dies at that release's closure" |
| Reduction needs evidence, not coverage alone (Rothermel) | SKILL §E | delete only with `file:line` evidence, as a `qa-engineer` verdict; "Deleting coverage without the map is cheating" |
| LARGE census ratchets down only | memory "Test Health" | "the cap is re-pinned at the census and ratchets only downward" |

### Missing (no clause exists)

1. **Structure-insensitivity as a named, measured property.** The "No Slop" prose forbids
   private-string tests but nothing counts private-symbol imports. Measured now: **21 of 396**
   `test_*.py` files import an underscore-prefixed symbol from `dadaia_workspace` (e.g.
   `hooks._common` ×6, `cli._specs_resolution` ×3, `_CANONICAL_AGENTS_BANNER`, `_MIME_BY_EXT`,
   `_parse_write_allowlist`). No metric, no ceiling.
2. **Sensitive-equality / exact-message assertions.** No rule forbids `assert msg == "…"` on
   diagnostics that are not a documented contract; Hyrum's law makes every such literal a
   frozen contract.
3. **Interaction-vs-state rule** (Google, Khorikov): no clause says "assert state, not mock
   call sequences"; intra-system interaction asserts are not listed as a smell.
4. **No-logic-in-tests / DAMP** (Google ch. 12): absent; no conditional-test-logic smell.
5. **Intent enforcement is e2e-only.** `check_test_intent_declared.py` gates `tests/e2e/**`
   only (memory: "there is no suite-wide mechanical gate"). Measured: only **94/396** test
   files carry a `^Intent:` header. So "temporary test without marker" is *forbidden by
   doctrine* (it is SCAFFOLD, it expires) but **not enforced** outside e2e — an unmarked
   SCAFFOLD in `tests/unit` has never been expired because nothing lists it.
6. **SCAFFOLD carries no expiry reference that a tool can read.** `Intent: SCAFFOLD — <task-id>`
   names a task, but no check joins it to the archived release and fails after closure.
7. **Mutation score has no floor.** `PARAMETERS.md` declares cadence only; no per-package
   number, no "tests killing zero mutants" report consumed by curation.
8. **Per-tier proportion target** (Google 80/15/5): the repo has tier directories (unit 244,
   contract 53, integration 84, e2e 15 files) but no declared shape or ceiling per MEDIUM.
9. **Characterization-test lifetime**: not named; the taxonomy has SCAFFOLD but no rule that
   a test written to "document actual behavior" must be rewritten as CONTRACT or deleted.

### Contradicted / drifted

- `PARAMETERS.md` says LARGE cap **30 (current ~84)**; `tests/AGENTS.md` says **30**;
  memory says census **100** *is* the ceiling. Three numbers for one parameter — a
  Sensitive-Equality smell in the doctrine itself. Fix: one source (`PARAMETERS.md`), the
  other two reference it.
- Memory calls coverage "80 % floor … never an acceptance target" but CI enforces
  `--cov-fail-under=80` on `unit or contract` — a floor that also blocks. Literature agrees a
  floor is fine; the wording "never a reason to write a test" is only true if nobody writes
  padding to clear it. No mechanism detects padding (a test with zero mutant kills that raised
  coverage is exactly that).
- SKILL §B admits a test that "kills a mutant no current test kills" — but mutation runs
  1×/release, so at admission time the criterion is unverifiable. Admission and measurement
  are on different cadences.

---

## Part 3 — Rules 0.5.0 should adopt, measurable

1. **Structure-insensitive floor.** Test files importing a private symbol (`_name`,
   `._module`) from `dadaia_workspace` ≤ **21 → ratchet to 0** across the release; measured by
   a contract test that greps `tests/**` and pins the count (same measure-then-ratchet law as
   C90). Whitelist entries need an inline "documented contract" reason.
2. **No sensitive equality.** Equality asserts on full diagnostic/message strings ≤ current
   measured count and ratchet down; assert on a stable token, exit code or structured field.
   Measured by an AST scan for `assert x == "<literal with spaces>"` outside `tests/contract`.
3. **Every test carries intent + size.** `Intent:` header coverage **94/396 → 396/396**;
   extend `check_test_intent_declared.py` from `tests/e2e/**` to `tests/**` (size stays by
   directory). Metric: files without header = 0, gated in CI.
4. **SCAFFOLD carries an expiry release.** Shape `Intent: SCAFFOLD — <task-id> — expires:
   <M.m.p>`; a check fails when the named release is in `_archive/`. Metric: expired-SCAFFOLD
   count = 0 at every closure.
5. **One behavior, lowest tier; cross-tier duplicates deleted.** Each LARGE/MEDIUM test names
   the behavior id it covers; a behavior appearing at two tiers is a defect unless the higher
   one is the seam's single SENTINEL. Metric: duplicate-behavior pairs = 0; LARGE census ≤
   **15 files / 100 items and only ratchets down**; SENTINEL ≤ 1 per seam.
6. **Mutation score is the value judge, with a floor.** `mutmut` on `core/` ≥ **measured
   baseline** at 0.5.0 start, ratchet up only; every test killing zero mutants and not a
   SENTINEL is listed in the CLOSURE curation table with a disposition (rewrite / delete).
   Metric: zero-kill tests outside SENTINEL = 0 at closure.
7. **Coverage is a floor only.** Keep `--cov-fail-under=80`; a coverage increase in a PR with
   no mutation-kill increase is flagged as padding by the qa-engineer verdict. Metric: the
   verdict carries both numbers.
8. **State, not interactions; no logic in tests.** Mock `assert_called*` on intra-system
   collaborators and `if/for/while` inside test bodies each ≤ measured count, ratchet down.
   Measured by AST scan (Conditional Test Logic, interaction-assert smells).
9. **Pyramid shape declared.** Target SMALL ≥ 75 %, MEDIUM ≤ 20 %, LARGE ≤ 5 % of collected
   items; measured per CI run from `--collect-only` counts; drift > 5 pp fails the closure
   size accounting, not the push.
10. **One number per parameter.** LARGE cap, flake ceiling and quarantine cap live only in
    `PARAMETERS.md`; `tests/AGENTS.md` and memory reference it. Metric: a contract test
    fails if a numeric cap appears in more than one doctrine file.
