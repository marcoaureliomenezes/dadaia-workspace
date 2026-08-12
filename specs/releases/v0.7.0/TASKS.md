# TASKS — Release v0.7.0 — Test stewardship

**Status:** Aprovado
**Release ID:** v0.7.0
**Segment:** `alpha-1`
**Owner:** product-engineer
**Source PLAN:** `specs/releases/v0.7.0/PLAN.md`
**Source SPEC:** `specs/releases/v0.7.0/SPEC.md`
**Grill:** `specs/releases/v0.7.0/GRILL.md`
**Branch:** `feature/v0.7.0` (cut from `develop`; branch contract: `dadaia-gitflow`)

## Task status markers

- `[ ]` OPEN
- `[-]` IN PROGRESS
- `[x]` DONE

## Standing rules for this release

- **The law is edited at source only.** `dadaia_workspace/public/data/DADAIA.md` is the one
  editable copy; the four projections are `0444` and PROTECTED. Every task touching
  `dadaia_workspace/public/` ends with `dadaia public stage` →
  `dadaia public install --target all` → `dadaia public doctor`, **run to completion in that
  task**. v0.6.0's alpha-1 was rejected for exactly this omission. Hand-editing a projection
  is a process violation, never a shortcut.
- **Reference, never restate.** After T-070-01 the doctrine is explained operationally in
  exactly one file. Every removal from a tier-2 surface must be answerable with "it now lives
  at `dadaia-test-stewardship` line N". The A4.1 relocation grep is the proof and it is run
  twice — by the author and independently by QA.
- **Edit, never append.** The 13 conflicts are pre-resolved in GRILL §5. Do not re-derive the
  map, do not add a paragraph where the map says "rewrite in place", and do not leave a
  summarized copy behind when the map says "delete".
- **RED before GREEN, with evidence.** T-070-05 and T-070-07 write their tests first and
  capture the failing output for CLOSURE. A test that never failed proves nothing.
- **Nothing is loosened.** The 80 % coverage gate, `retries: 1`, the pre-push CI preflight
  ladder and the `pre_gate` path-class model are copied through unchanged. This release adds
  rules and makes an existing silence loud.
- **A group of completed tasks = a commit.** Not one commit per file.
- **Economy directive (R4).** Read only the files named in your write set. Do not explore the
  tree, do not re-scan the suite (the scans are in GRILL §2), do not re-open the source
  report. Everything you need to decide has been decided.
- **Parallelism.** Exactly two sanctioned concurrent pairs: `T-070-04 ∥ T-070-05`, and
  `T-070-06 ∥ T-070-07`. Both pairs have disjoint write sets, verified file by file.
  Everything else is sequential. Never two `[-]` outside those two pairs.
- **This release ships by its own rules.** Milestone (a) fires on approval of this trio
  (merge to local `develop` → diff security review of `origin/develop..develop` → push).
  Milestone (b) is T-070-10. Memory is written only in the `CLOSURE` phase (T-070-11).

---

- [x] **T-070-01 — `dadaia-test-stewardship`: the single operational home**

**Owner role:** ai-engineer · **Commit:** `feat(T-070-01): add dadaia-test-stewardship universal skill`

**Preconditions:** none. **First task of the release** — nothing may defer to a skill that
does not exist.

**Write set:** `dadaia_workspace/public/skills/dadaia-test-stewardship/SKILL.md` (**new file,
sole write**). No `public/entities/registry.json` entry — this is a **universal** skill, not
a per-harness derivation (the `dadaia-gitflow` precedent). Projections are produced by the
chain at the end of this task, never hand-written.

**Description:** Author the skill per SPEC FR1: groups **A–H** as an operational protocol
(intent taxonomy; admission filter; size tiers with the tier→timeout table and the LARGE
owner rule; demotion with the S-15 map; deletion criteria a–f plus the tombstone ban and the
separation of powers; flake/quarantine pipeline with the 30 d/30 d/+1-release escalation;
artifact hygiene; health metrics, trigger-based audit, mutation cadence), the **§10 parameter
table** as *declared adjustable defaults*, and **at least three decision tables** an agent can
execute without prose (S-16 deletion criteria; the flaky flow; the
tombstone/SCAFFOLD/quarantine disposition table).

Two things the skill must get exactly right:

1. **Intent is declared in the module docstring** — `Intent: <KIND> — <AC id | bug-id |
   task-id>` — **never** as a pytest marker (GRILL P3: the marker namespace already binds
   `contract` to the layer `tests/contract/`; an intent marker of the same name would
   silently re-tier tests and corrupt every `-m` selector in CI). State this reasoning in the
   skill in one sentence so nobody "improves" it later.
2. **The abstract LARGE default (12–15 per module) and this repo's value (30) are separate
   facts.** A consumer re-parameterizes; it does not inherit dadaia-workspace's number.

**Done criterion:**
- File exists with valid frontmatter; **≤ 250 lines** (A1.4).
- All eight groups present as named sections; none reduced to a single sentence (A1.2).
- Parameter table carries all seven D3 values, each labelled adjustable (A1.3).
- **No sentence is copied verbatim from `DADAIA.md` §6** (A1.5) — the law states, the skill
  operates.
- Projection chain run to completion; `dadaia public doctor` → `[ok] public-privacy`, zero
  drift; the skill present in `.claude/skills/`, `.agents/skills/`, `.codex/`, `.kimi-code/`
  (A1.1).

---

- [x] **T-070-02 — `DADAIA.md` §6 increment + projection**

**Owner role:** ai-engineer · **Commit:** `refactor(T-070-02): test-lifecycle law in DADAIA.md §6`

**Preconditions:** T-070-01 `[x]` (the law delegates to the skill).

**Write set:** `dadaia_workspace/public/data/DADAIA.md` (**source only**). The four
projections are regenerated, never edited.

**Description:** Add the five-point test-lifecycle block to §6 (Quality) per SPEC FR2, plus
**exactly two** sentences elsewhere: the never-delete **scoping** sentence (§5's law covers
bugs and backlog **only**; tests are prunable under the criteria) and the **quarantine
carve-out** inside *Push green* (a `quarantine`-marked test is out of the gating selectors by
design, requires a registered bug and expires; a green run with quarantined tests is green;
an **unregistered pass-on-retry is a failure**).

**Measure the always-on token count before the edit and after.** This file is injected on
every turn; growth is paid forever. Cap **+400** (A2.2). Report both numbers regardless of
outcome. If the increment exceeds the cap, **cut law text** — never raise the cap.

**Done criterion:**
- All five points and both sentences present, **exactly once each** (A2.1, reviewer diff
  read).
- **No number and no marker name in the law** — no timeout value, no quarantine cap, no flake
  percentage (A2.4). Those live in the skill and in the repo.
- Token before/after pair captured for CLOSURE; growth ≤ +400.
- Four `0444` byte-identical projections; `dadaia public doctor` green (A2.3);
  `dadaia specs doctor` exits 0.
- A grep for the never-delete law returns exactly one, now-scoped, statement (A2.5).

---

- [x] **T-070-03 — Consumer surface: constitution §8, `tests-AGENTS.md` template, memory template**

**Owner role:** ai-engineer · **Commit:** `feat(T-070-03): consumer test doctrine — constitution §8 + tests/AGENTS.md template`

**Preconditions:** T-070-02 `[x]` (the article points at the law and the skill).

**Write set:** `dadaia_workspace/public/scaffold/constitution.md`;
`dadaia_workspace/public/templates/tests-AGENTS.md` (**new**);
`dadaia_workspace/public/scaffold/memory/quality-assurance.md`. **Not**
`features/spec_context/service.py` — the wiring is T-070-07, which keeps the pair with
T-070-06 disjoint.

**Description:** Three landings, per SPEC FR3.

1. **`## 8. Disciplina de Testes`** — inserted between §7 (*Mapa*) and §9 (*Autoridade de
   Dispatch*); PT-BR to match the file; **≤ 12 lines**. Intent + size at birth; admission
   requires real detection; demotion at closure; pruning is a steward verdict, never the
   implementer's; tombstone/expired-SCAFFOLD are slop; artifacts failure-gated. Points at
   `dadaia-test-stewardship` for the protocol and states that the numbers are
   project-adjustable. **Renumber nothing** — the section set becomes {1..9, 11, 13, 14}.
2. **`public/templates/tests-AGENTS.md`** — the scoped rule file a consumer repo receives.
   Same structure as T-070-04's rewritten `tests/AGENTS.md`, but **parameterized**:
   placeholders for the tier timeouts, the LARGE cap and the wall-clock baseline, and the
   abstract defaults (12–15/module) rather than this repo's 30.
3. **`scaffold/memory/quality-assurance.md`** — doctrine sync: the layer→size mapping plus
   pointers to the skill and to constitution §8. **A pointer, not a copy** (C10). Refresh
   `last_updated`.

**Done criterion:**
- §8 present; section-number set is {1..9, 11, 13, 14}; no existing section renumbered (A3.1).
- Every `constitution §N` citation in `public/agents/**` + `public/skills/**` still resolves
  (A3.2 — extract, intersect, expect empty difference).
- `templates/tests-AGENTS.md` contains **zero** dadaia-workspace-specific literals — no
  `dadaia_workspace`, no `2:38`, no `30`-as-the-cap (A3.3); `dadaia public doctor` reports
  `[ok] public-privacy`.
- Scaffold memory carries the mapping + both pointers and no copy of the protocol (A3.5).
- Projection chain run to completion; `dadaia public doctor` green.

---

- [x] **T-070-04 — Tier-2 single-home edits (C1–C13)**

**Owner role:** ai-engineer · **Commit:** `refactor(T-070-04): single-home test doctrine; reconcile coverage stance`

**Preconditions:** T-070-03 `[x]`. **May hold a concurrent `[-]` with T-070-05** (disjoint
write sets: text vs code).

**Write set:** `tests/AGENTS.md`; `tests/README.md`;
`dadaia_workspace/public/agents/{qa-engineer,software-engineer}.md`;
`dadaia_workspace/public/skills/{dadaia-release-closure,drift-detection,project-orchestration}/SKILL.md`;
`dadaia_workspace/public/scaffold/constitution.md` (**line 44 only** — the coverage sentence;
T-070-03 owns §8 and is `[x]` before this starts). No package file, no YAML.

**Description:** Execute the conflict map (SPEC FR4 table + FR7). Per file:

- **`tests/AGENTS.md`** — rewrite "Good Test Standard" as the **intent taxonomy + admission
  filter + deletion criteria**; extend the existing tombstone bullet in place to S-17's full
  form (removed feature returns 404, module became a stub, directory/repo removed, old
  migration gone); add the **tier table** with the timeout values, the LARGE-owner rule and
  the declared-but-WARN LARGE cap (30); document the two new markers. This file becomes the
  repo's single owner of C1, C3 and C5.
- **`tests/README.md`** — **collapse to `## Commands` + one pointer line**. Delete the Layers
  and No-Slop-Policy sections outright; every string removed must exist in `tests/AGENTS.md`.
- **`qa-engineer.md`** — steward duties **verdict-only**: issues delete/demote/quarantine
  verdicts with S-16 `file:line` evidence, never executes the pruning commit. Narrow
  `write_allowlist` from `tests/**` to `tests/e2e/**` + `specs/releases/**/ALPHA-*-QA.md` +
  reports + handoff (P8 — the alpha-N review must remain writable). Align `:169`'s coverage
  sentence to the single stance.
- **`software-engineer.md`** — one note: **executes** qa-engineer curation verdicts, quoting
  the verdict's evidence in the commit message; never prunes on its own initiative. Point the
  slop-test discipline at `tests/AGENTS.md` instead of restating admission rules. Its `:176`
  coverage sentence is the **canonical** phrasing the other three align to.
- **`dadaia-release-closure/SKILL.md`** — new **demotion + disposition** block (the S-15 map:
  deleted LARGE → the cheaper test replacing it, `file:line`; the quarantine/SCAFFOLD expiry
  sweep; where each lands in `CLOSURE.md`). Amend `:184`: the closer does not *write* tests,
  it **records dispositions**.
- **`drift-detection/SKILL.md`** — rewrite **Dimension E** off line coverage onto detection
  quality (intent declared, demotion performed, flake within ceiling, quarantine within cap
  and not expired, LARGE owned). Line coverage may appear only as "the CI floor holds".
- **`project-orchestration/SKILL.md`** — **citation only**; no doctrine text.
- **`scaffold/constitution.md:44`** — the 80 % floor restated as a **CI gate** and an
  explicit by-product metric, pointing at §8.

**This is the largest task and it is splittable at execution time** (R4): it may close in two
commits over two dispatches without a spec amendment, provided the A4.1 grep is clean at the
end. Progress is legible because the Done criterion is stated per file.

Re-project at the end (same chain as T-070-02).

**Done criterion:**
- **A4.1 relocation grep clean** for `SENTINEL`, `SCAFFOLD`, `QUARANTINE`, `tombstone`,
  `demotion` across `public/`, `tests/AGENTS.md`, `tests/README.md`: every hit resolves to
  the skill, the `DADAIA.md` §6 statement, `tests/AGENTS.md`, or a reference to one of them.
  Any other hit is a stop condition.
- `tests/README.md` = `## Commands` + pointer + nothing else; every deleted string exists in
  `tests/AGENTS.md` (A4.2).
- `qa-engineer.md` frontmatter has no `tests/**` wildcard and agrees with its body;
  **no other agent's allowlist widens** (A4.3, diff-read).
- `dadaia-release-closure/SKILL.md:184` no longer forbids recording test dispositions; the
  new block names the exact CLOSURE sections (A4.4).
- `drift-detection` Dimension E contains **no** line-coverage percentage in any score anchor
  (A4.5).
- Coverage grep returns exactly four sites, all one stance; no fifth stance (A7.1, A7.2).
  `ci.yml`'s `--cov-fail-under=80` is **byte-unchanged** (A7.3).
- `dadaia public doctor` + `dadaia specs doctor` both exit 0 (A4.6).

---

- [-] **T-070-05 — Markers, tiered timeouts, preflight (TDD: RED before GREEN)**

**Owner role:** software-engineer · **Commits:** `test(T-070-05): RED contracts for tier timeouts and quarantine markers` then `feat(T-070-05): pytest-timeout tiers, flaky/quarantine markers, preflight cleanup`

**Preconditions:** T-070-01 `[x]` (the values are the skill's declared defaults).
**May hold a concurrent `[-]` with T-070-04.**

**Write set:** `pyproject.toml`; `tests/conftest.py`;
`dadaia_workspace/features/ci_preflight/service.py`;
`tests/unit/features/ci_preflight/test_service.py` (**named explicitly — it pins the dead
flag at `:28,34` and reddens the suite if left behind**); new/extended `tests/unit/**` and
`tests/contract/**` for the contracts below; `specs/memory/.heading-allowlist`.
**Not** `.github/workflows/ci.yml` (T-070-06), **not** any `public/**` file (T-070-04).

**Description:** Two commits, RED first — the RED commit is not optional.

**RED.** Write the contracts of PLAN §4: tier→timeout mapping for all four layers; explicit
`@pytest.mark.timeout` never overridden; `quarantine` without a bug id errors at collection
with an actionable message; the marker-set pin (`pyproject.toml` ≡ `conftest.py` known
markers); every gating selector excludes `quarantine`; the dead `--ignore=tests/performance`
is gone (the existing pin **is** the RED). **Capture the failing output** for CLOSURE.

**GREEN.**
1. Add the `pytest-timeout` dev dependency.
2. Extend `tests/conftest.py`'s `pytest_collection_modifyitems` (`:118-141`, the
   `_PATH_MARKERS` table) to apply `pytest.mark.timeout(N)` by layer — unit **10 s** /
   contract **30 s** / integration **60 s** / e2e **120 s** — **only when the test declares
   no explicit `timeout` marker**. A test that needs more time is **mis-tiered**; fix the
   tier, never the default.
3. Add `flaky` and `quarantine` to `pyproject.toml` `markers` and enforce the bug-id rule in
   `conftest.py`.
4. `features/ci_preflight/service.py:257` — drop `--ignore=tests/performance`, add the
   `quarantine` exclusion to the gating invocation.
5. Append `Flake Policy`, `Test Health`, `Root Cause, Always` and `Satisfiable Diagnostics`
   to `specs/memory/.heading-allowlist` (the last two are already live and un-allowlisted).

**M1 warning:** this task owns **five** of the six marker surfaces. The sixth (`ci.yml`) is
T-070-06 and follows immediately. A marker that exists in five surfaces and not the sixth
produces a **green** suite that selects the wrong tests — the worst failure mode in this
release.

**Done criterion:**
- All PLAN §4 contracts pass; RED evidence captured (A5.1, A5.2, A5.3, A5.6).
- `--ignore=tests/performance` appears nowhere in `dadaia_workspace/` or `tests/`.
- Full suite green **under the new timeouts**: `pytest -p no:cacheprovider -q`. Any test that
  trips a tier ceiling is re-tiered or given an explicit justified marker — **never** a
  raised default (R5).
- `mypy --strict`, `ruff format --check`, `ruff check`,
  `lint-imports --config setup.cfg --no-cache` all clean (A5.8).
- `dadaia specs doctor` exits 0 with the new headings allowlisted (A5.7).

---

- [ ] **T-070-06 — CI: selectors, durations, ceilings, loud flake**

**Owner role:** software-engineer · **Commit:** `ci(T-070-06): quarantine selectors, durations, budget ceilings, flake detection`

**Preconditions:** T-070-05 `[x]` — a `-m` selector cannot reference a marker that does not
exist. **May hold a concurrent `[-]` with T-070-07.**

**Write set:** `.github/workflows/ci.yml`; `tests/e2e/panel/playwright.config.ts`; a
flake-detection script under `dadaia_workspace/public/scripts/` **only if** the step needs
more than inline shell (if added, it is a public asset and its task ends with the projection
chain). No Python package file, no `public/` text file.

**Description:**
1. **Quarantine exclusion in every gating selector** (`ci.yml:144,174,201,227,251,275`).
2. **`--durations=25`** on the unit job and the unit+contract coverage job (integration/e2e
   already carry `--durations=30`).
3. **Budget ratchet (P6):** set each pytest job's `timeout-minutes` to ≈1.5× the frozen
   baseline — preflight quick **2:38**, preflight full **~5:30**, panel E2E **1:10**. The
   ceiling becomes a reviewable diff; raising one later requires a justification in CLOSURE.
4. **Loud flake (P7):** add a JSON reporter to the Playwright CI run, written **outside the
   repo**, alongside `list`; add a step that fails the job on a `passed`-after-`retry > 0`
   result **unless** the test is registered (quarantined with a bug id). `retries: 1` stays —
   what changes is that the retry stops being invisible. **A missing JSON report is a hard
   error, never a pass** (R9).
5. **Demonstrate it once (A5.5):** commit a deliberately flaky throwaway spec, show the job
   **fail** on the unregistered pass-on-retry, capture the output for CLOSURE, and **remove
   the spec in this same task**. A gate nobody ever fired is a claim.

**Done criterion:**
- Every gating selector excludes `quarantine`; a quarantined sample runs under
  `-m quarantine` and does not run in the gating jobs (A5.4).
- `--durations` on the unit and coverage jobs; `timeout-minutes` set per the ratchet.
- Unregistered pass-on-retry **fails** the panel E2E job — demonstrated, output captured,
  throwaway spec removed in the same task (A5.5).
- The JSON report path is outside the repo tree; no new repo-local artifact
  (`DADAIA.md` §4).
- `--cov-fail-under=80` **byte-unchanged** (A7.3); every CI job green on the branch path.

---

- [ ] **T-070-07 — Scaffolder wiring: consumer repos receive `tests/AGENTS.md` (TDD)**

**Owner role:** software-engineer · **Commits:** `test(T-070-07): RED cases for tests/AGENTS.md scaffolding` then `feat(T-070-07): copy tests-AGENTS.md template on context alive`

**Preconditions:** T-070-03 `[x]` (the template must exist). **May hold a concurrent `[-]`
with T-070-06.**

**Write set:** `dadaia_workspace/features/spec_context/service.py`;
`tests/unit/features/spec_context/**` (new/extended). No template file, no YAML.

**Description:** At the existing `templates/repo-AGENTS.md` seam (`:387-390`), copy
`public/templates/tests-AGENTS.md` to `<repo>/tests/AGENTS.md` **only when `<repo>/tests/`
already exists and `<repo>/tests/AGENTS.md` does not** (GRILL P2). **Never create a `tests/`
directory** — a repo without one is not a repo this doctrine can scaffold into, and inventing
the directory would plant a stray folder in every non-Python consumer.

RED first, three cases (PLAN §4): `tests/` exists + no `AGENTS.md` → created from template;
`tests/AGENTS.md` exists → **byte-identical** afterwards; no `tests/` → **no directory
created, no file written**. The third case is the one that catches a naive
`mkdir(parents=True)`.

**Done criterion:**
- All three cases pass; RED evidence captured (A3.4).
- The generated file matches the template byte-for-byte (no rendering step is introduced —
  this is a copy, like `repo-AGENTS.md`).
- `mypy --strict` clean; `lint-imports` contracts kept, 0 broken; full suite green.

---

- [ ] **T-070-08 — QA `alpha-1`: validate the contract on the live instance**

**Owner role:** qa-engineer · **Commit:** `test(T-070-08): alpha-1 QA review committed to the branch`

**Preconditions:** T-070-01..07 all `[x]`.

**Write set:** `specs/releases/v0.7.0/ALPHA-1-QA.md` (the review, committed to the branch per
the segment protocol) + `.dadaia/handoff/dadaia-workspace/`. **No source file, no `public/`
file.** A finding is reported, never fixed here.

**Description:** Validate from the **live instance**, not from the diff:

1. Projection integrity: four `DADAIA.md` copies byte-identical and `0444`;
   `dadaia-test-stewardship` present in all four projection roots.
2. **Re-run the A4.1 relocation grep independently.** A dedup pass audited only by its own
   author is not audited. Every hit must resolve to the skill, the law, `tests/AGENTS.md`, or
   a reference.
3. **Re-run the coverage grep (A7.1/A7.2)**: exactly four sites, one stance, no line-%
   score anchor anywhere.
4. **Re-run the citation check (A3.2)**: every `constitution §N` cited in `public/` resolves.
5. Mechanical: tiered timeouts active; a bug-less `quarantine` refused at collection; a
   quarantined sample excluded from every gating selector; the flake-gate demonstration
   output present and credible; `--durations` and `timeout-minutes` in place;
   `--ignore=tests/performance` gone.
6. Consumer landing: the three scaffolder cases; a read of the generated `tests/AGENTS.md`
   for placeholder correctness and for **zero** dadaia-workspace literals (A3.3).
7. Doctors: `dadaia doctor`, `dadaia specs doctor`, `dadaia public doctor` all exit **0**.
8. Full quality ladder: `pytest -p no:cacheprovider -q`, `ruff format --check`, `ruff check`,
   `mypy --strict`, `lint-imports --config setup.cfg --no-cache`.
9. **Capture the frozen baselines** for CLOSURE and for FR6: collected test count, LARGE
   (e2e) count, preflight quick/full wall-clock, panel E2E wall-clock, `DADAIA.md` tokens.

**Done criterion:** SPEC §7 items 1–6 verified with evidence per item; baselines captured;
the `alpha-1` review committed to the branch. Any missed target is reported as a **finding
with its evidence**, never rounded into a pass. A REJECTED verdict returns the offending task
to `[-]` and is preserved verbatim in the review file as the historical record.

---

- [ ] **T-070-09 — Review + diff-based security verdict**

**Owner role:** code-reviewer + security-reviewer (verdicts); software-engineer applies any
required fix · **Commit:** fixes only, each returning its task to `[-]`

**Preconditions:** T-070-08 `[x]` with a PASS verdict.

**Write set:** `.dadaia/handoff/dadaia-workspace/` (verdict handoffs). No source file except
a fix a reviewer requires.

**Description:** Six-axis code review. The security review is **diff-based on
`origin/develop..develop`** — the v0.6.0 rule applied to itself. Surfaces that matter here:

- **The flake-detection step** parses a report produced by CI. Is the parse robust to a
  missing/empty/partial file, and does it fail **closed**? A gate that passes when its input
  is absent is not a gate.
- **`head`-style untrusted input:** confirm no fork-influenceable value reaches a shell
  string unquoted in the new CI step.
- **The scaffolder copy** writes into a consumer repo. Confirm it cannot overwrite an
  existing operator file and cannot create a directory (the three cases).
- **The meta-risk:** every new refusal (bug-less quarantine, timeout kill, flake gate) must
  be **clearable by an action the product accepts** — the "Satisfiable Diagnostics" law. A
  refusal with no legal remedy is a defect in the check.

**Done criterion:** code-review **APPROVE**; `security-reviewer` **APPROVED** handoff whose
verdict covers the `origin/develop..develop` delta about to be pushed. Any
`REQUEST_CHANGES`/`REJECTED` returns the named task to `[-]`.

---

- [ ] **T-070-10 — Milestone (b): merge to `develop`, push, PR to `main`, CI green**

**Owner role:** software-engineer · **Commit:** merge commit + any CI fix

**Preconditions:** T-070-09 `[x]` with both verdicts APPROVE.

**Write set:** git refs only (`develop` merge + push; PR). No spec file, no source file except
a fix CI demands (each returning its task to `[-]`).

**Description:** Execute the ship milestone per `dadaia-gitflow`:

1. Merge `feature/v0.7.0` → **local `develop`**.
2. Diff-based security review of `origin/develop..develop` (T-070-09's verdict must cover the
   merged delta; if the merge changed it, the verdict is re-issued).
3. **Push `develop`** — through the v0.6.0 chokepoint, unmodified.
4. Open PR `develop` → `main`. Watch CI until **every** job is green; read the failing log,
   fix the cause, push again, keep watching. The new flake gate and the new ceilings are part
   of "every job" — if a ceiling is too tight, that is a **finding**, fixed by re-tiering or
   by an explicitly justified ceiling change recorded in CLOSURE, never by silently raising it.
5. Merge the PR.

**Done criterion:** `develop` pushed and accepted by the installed gate; every CI job green on
`develop` and on the PR; `pr-source-guard` green on a `develop` head; PR merged.

---

- [ ] **T-070-11 — Memory → CLOSURE → archive (in that order)**

**Owner role:** product-engineer · **Commit:** `docs(T-070-11): v0.7.0 closure, memory atoms, dispositions`

**Preconditions:** T-070-01..10 all `[x]`. **`ACTIVE.md` phase set to `CLOSURE` before any
memory write** — the memory path class is phase-gated.

**Write set:** `specs/memory/quality-assurance.md`; `specs/memory/tech-stack.md`;
`specs/memory/product/distribution/public-asset-distribution.md`;
`specs/memory/architecture.md`; `specs/memory/product/{index.md,catalog.json}` **only if** an
atom's frontmatter `tldr`/`summary` moved (**regenerated**, never hand-edited);
`specs/releases/v0.7.0/CLOSURE.md`; `specs/releases/ACTIVE.md`;
`specs/backlog/test-stewardship-standardization.md` (terminal disposition); `CHANGELOG.md`.

**Description:** The order is the law: **memory update → CLOSURE → archive.**

**Memory** describes the product *as it is now*, with no changelog and no "we used to have no
timeouts":
- `quality-assurance.md` — new h2 **`Flake Policy`** (markers, caps, 30 d/30 d/+1-release
  escalation, registered-bug requirement, push-green carve-out); new h2 **`Test Health`**
  (the three metrics, trigger-based audit, mutation cadence, frozen wall-clock baselines);
  `Layers` gains the layer→size mapping and the intent **mapping only** (the taxonomy prose
  stays in `tests/AGENTS.md`); `CI` gains tiered timeouts, quarantine exclusion, durations and
  ceilings; the stale ~2,100 test count replaced by T-070-08's measured figure.
- `tech-stack.md` — `pytest-timeout` added; `pytest-xdist`/`pytest-randomly` documented (they
  are already in use); marker list gains `flaky` and `quarantine`.
- `public-asset-distribution.md` — universal-skill roster gains `dadaia-test-stewardship`;
  template roster gains `tests-AGENTS.md`.
- `architecture.md` — the `spec_context` `alive()` scaffold inventory gains the conditional
  `tests/AGENTS.md` copy. **State explicitly either way**, including "no change" with its
  reason.

**CLOSURE** carries: the `## Validations` evidence triples; the `## Dispositions` table
flipping `specs/backlog/test-stewardship-standardization.md` to **`DELIVERED — v0.7.0`** with
each of its **three** intents mapped to the FR that consumed it; an explicit statement that
`specs/backlog/test-suite-remediation-stewardship.md` stays `candidate` and is now
**unblocked**; the `DADAIA.md` token before/after pair; the RED-before-GREEN evidence for
T-070-05 and T-070-07; the flake-gate demonstration output; the frozen baselines; and the
backlog returns — **mutation-testing tool choice**, **intent-docstring mechanical
enforcement** (P9), and the dead `release_hotfix.md.j2` / `closure_hotfix.md.j2` templates if
still present.

**Archive** last: `ACTIVE.md` phase → `ARCHIVED`, then request
`git mv specs/releases/v0.7.0 specs/_archive/releases/v0.7.0` from software-engineer
(product-engineer has no shell), then repoint `ACTIVE.md`.

**Done criterion:** memory states current truth with no changelog section and every number
cross-checked against what is actually in force (A6.2, verified by QA, not by the author);
`dadaia specs doctor` exits 0; CLOSURE complete with the `## Dispositions` table and every
evidence item above; `ACTIVE.md` repointed; the `git mv` requested with the exact command.
