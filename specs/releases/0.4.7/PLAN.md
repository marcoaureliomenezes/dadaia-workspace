# PLAN — Release: 0.4.7

**Status:** Approved
**Release ID:** 0.4.7
**Owner:** dd-software-engineer

---

## Assumptions (stated, not decided here)

- **D8 default — `release: published`.** `release.yml` triggers on the `release` event
  release-please emits when the release PR merges and the tag is cut. The alternative
  (`push: tags: v*`) is not planned for; a PM reversal changes exactly one `on:` block in
  T-047-88 and its two contract assertions.
- **D9 default — rename at promote.** The release directory keeps its floor id while the
  candidate runs; if release-please mints a different number, the directory is renamed once at
  promote and the minted version recorded in the `_RELEASE.json` log. Under the version finding
  below this rename is expected to be a no-op for 0.4.7.

## The version release-please would mint (verified against the action, 2026-09-21)

`v0.4.6..HEAD` carries 1,689 commits, 140 of them `feat:`, **zero** with a `!` breaking marker.
release-please's pre-1.0 rules: `bump-minor-pre-major` (default `false`) governs BREAKING
(→ major unless set); `bump-patch-for-minor-pre-major` (default `false`) governs `feat`. With
both at their defaults a `feat` on a `0.x` version bumps the **minor** — the first release PR
would propose **0.5.0**, not 0.4.7.

The operator wants 0.4.7. The config must therefore set, at the root of
`release-please-config.json`:

```
"bump-minor-pre-major": true,
"bump-patch-for-minor-pre-major": true
```

— `feat` bumps patch, BREAKING bumps minor, `fix`/the rest bump patch, for as long as the
project stays below 1.0. With that, the first release PR proposes **0.4.7** from the 0.4.6
floor, and D9's rename is a no-op. This is the plan's recommendation; changing it is a PM call,
not an implementation call.

**Corollary the PM must rule on before T-047-87 (see Risks, D10):** release-please reads the
*current* version from `.release-please-manifest.json` and expects `pyproject.toml` to agree —
both must carry the **last published** version, `0.4.6`. This repository's `pyproject.toml`
carries `0.4.7` because `SPEC-DOC-045` requires pyproject to equal the live release id. That
rule dies in T-047-90; the pyproject reset to `0.4.6` lands in the same commit as its death, so
no task ever leaves the tree with a doctor error. T-047-87 therefore writes the manifest at
`0.4.6` and its contract asserts *manifest == last published PyPI version*; the strict
`manifest == pyproject` equality (ADR 0021's `measured_by`) is asserted from T-047-90 on.

## Design (codebase-design vocabulary)

Candidate 10 is a **deletion candidate**. It buys one behaviour — a bot maintains the version,
the CHANGELOG and the tag from the commit log — and pays for it by deleting four scripts, two
subcommands, one schema field, one doctor rule family, one doctor rule and the hand-written
CHANGELOG discipline. Every task's diff should be net-negative in the repository except
T-047-87, which is the one addition.

- **Seam: the release PR.** Today the seam between "this is done" and "this is published" is a
  pyproject edit compared against tags inside the publishing workflow — an implicit seam with no
  reviewable artifact. After this candidate the seam is a pull request on `main` whose body is
  the generated changelog: reviewable, revertable, one place. `release.yml` stops deciding
  *whether* to release and only executes a decision already made upstream (`check` dies,
  `publish` stops creating the tag).
- **Deletion test on `_release_rc.py`/`_release_fold.py`/`_release_fold_plan.py`/`_release_archive.py`
  (404 of the 1,381 skill-script lines).** Delete them and the complexity does *not* reappear at
  any caller: "what was candidate 9's trio" is answered by `git show <CLOSURE sha>:specs/releases/0.4.7/…`,
  which is the same answer `rc-9/` gives, without a copy. `fold` exists solely to repair a wrong
  `archive`; with no `archive` there is nothing to repair. This is the textbook pass-through
  cluster — it earns nothing and it is deleted, not wrapped.
- **Replace, don't layer (the standing order).** Nothing in this candidate adds a flag or a
  branch to keep the old path alive beside the new one. `rc-archive`, `fold` and `archive` do
  not gain a `--legacy`; they cease to exist. The only additive surface is
  `release.py phase CLOSURE --pr <n>`, justified below.
- **ADR 0018 — no verb enters.** `dadaia help tree` is byte-identical after this candidate:
  release-please is a GitHub Action, the config files are data, and `release.py` is a skill
  script, not the CLI. `--pr` is one optional argument on an *existing* subcommand that records
  the merged release PR number where `archive --pr <n>` used to record it — the verb count goes
  6 → 4, the flag moves from a dying verb to a living one. That is a migration, not growth.
- **Read-only tolerance, then death.** `specs/releases/0.4.7/rc-1..rc-9` and
  `specs/releases/_archive/**` stay on disk forever (history is never rewritten). The
  `RELEASE-TREE-ARCHIVE-*` rules are *validators*, so deleting them cannot make an existing
  directory illegal — it makes it unvalidated. `_archive/` and `rc-N/` stay canon members of the
  specs tree, excluded from the release-directory walk by the existing name rule. `doctor` and
  `release.py check` are therefore green on the live instance at every commit of this candidate,
  which is the plan's hardest constraint.
- **The CHANGELOG freezes, it is not migrated.** Everything at and below `## [0.4.7]` is
  hand-written history and is never rewritten; release-please prepends above it from the first
  release PR on. T-047-92's "Candidate 10" section is the last hand-written text in the file.

## Order of work

Fixed by the SPEC: 87 → 88 → 89 → 90 → 91 → 92. Each task leaves `dadaia ci preflight` green,
`dadaia doctor --specs-dir repos/dadaia-workspace/specs` at exit 0 on the live instance, and the
instance re-projectable.

1. **T-047-87 (FR1)** — the addition: the release-please workflow, config and manifest. Nothing
   reads them yet, so this task is safe to land first and is the only place the new mechanism is
   described.
2. **T-047-88 (FR1)** — `release.yml` re-pointed at `release: published`; `check` and the tag
   step die. 88 follows 87 because the tag it stops creating is the tag 87's action starts
   creating.
3. **T-047-89 (FR2)** — the four scripts, the two subcommands and the schema's `rc` field die.
   89 follows 88 because `archive` is what `release.yml`'s old publish path paired with.
4. **T-047-90 (FR2)** — the doctor half: `RELEASE-TREE-ARCHIVE-*` and `SPEC-DOC-045` die,
   `phase CLOSURE --pr` arrives, `pyproject.toml` returns to the 0.4.6 floor. 90 follows 89
   because a rule may only die after its last writer does.
5. **T-047-91 (FR3)** — law, skills, recipe, the root map, and the five ADRs → `superseded` in
   the same commit as the last citation deletion. 91 follows 89/90 because the law may only stop
   naming a verb after the verb is gone.
6. **T-047-92 (FR3)** — closure: CHANGELOG, `_RELEASE.json`, re-projection, derived docs.

## Verification — what each task proves, and what it cannot

`release-please.yml` runs on pushes to `main`; this branch is `feature/0.4.7`. **The mechanism
cannot be exercised before the merge.** Each task therefore proves what is provable statically
and the plan names the residue explicitly.

- **T-047-87/88 — proved locally:** `tests/contract/test_ci_workflow_hygiene.py` parses both
  workflow YAMLs (the workflow exists; the action is pinned to a 40-hex sha with a version
  comment; `release.yml`'s `on:` is the `release: published` event; no job compares pyproject to
  tags; no step runs `git tag`; `approve`/`publish`/`smoke-test`/`publish-skills-repo` survive
  with their `needs:` graph intact), and `tests/contract/test_release_semver_canon.py` parses
  `release-please-config.json` + `.release-please-manifest.json` (valid JSON, the two pre-1.0
  bump flags set as above, `include-component-in-tag: false`, `release-type: python` inside the
  config's `packages["."]` — **not** as an action input: with `config-file`/`manifest-file` set,
  passing `release-type` switches the action out of manifest mode).
- **UNVERIFIED until the first release PR:** that release-please parses this commit history
  without error, that it proposes 0.4.7 rather than 0.4.6/0.5.0, that its CHANGELOG sections
  render as configured, that the `release: published` event actually fires `release.yml`, and
  that `publish` still finds its build artifact under the new trigger. These are one operator
  observation on the first PR after merge to `main`; no test in this repository can assert them.
  T-047-92 records that residue in the `_RELEASE.json` log so the next session inherits it.
- **T-047-89/90 — proved locally, fully:** `tests/contract/test_release_state_schema.py` (the
  schema closes without `rc`/`implemented.rc`), `tests/contract/test_release_tree_canon.py`
  (the `RELEASE-TREE-ARCHIVE-*` cases deleted, the survivors unchanged),
  `tests/contract/test_public_scripts_thin_wrapper.py` + V36 re-pinned down,
  `release.py check --specs specs` exit 0 on this repository's real tree (rc-1..rc-9 and
  `_archive/` present and tolerated), `dadaia doctor` exit 0, `dadaia help tree` unchanged.
- **T-047-91 — proved locally:** `grep -rnE "rc-archive|release\.py fold|release\.py archive|rc-N"`
  over `dadaia_workspace/public/` and `specs/memory/` returns nothing; every `fix:` line names a
  living verb (`tests/contract/test_every_block_carries_a_fix.py`); `ADR-SUPERSEDED-CITATION`
  green with the five records at `status: superseded`.
- **T-047-92 — proved locally:** V32/V33/V34/V35/V36 all green at their new (lower) pins,
  `public stage` → `public install` → `public doctor` exit 0, `dadaia doctor` exit 0.

## Ratchets — down only

| Ratchet | Now | After |
|---|---|---|
| V32 governance ids | 682 | re-pin to the measured value (four scripts' comments die) |
| V33 orphan families | 35 | re-pin to measured; no family is added |
| V34 trio bytes | SPEC ≤ 24 KB / TASKS ≤ 12 KB | unchanged (measured before each commit) |
| V35 skill Markdown | 18 dirs / 2877 lines | re-pin DOWN (rc/fold/archive prose deleted); never raised |
| V36 skill scripts | 36 files / 4191 lines | ≤ 32 files / ≤ 3787 lines, then to measured |
| module ceiling | 699 / 700 | down (`release_tree.py`, `doctor_release.py` shrink) |
| import-linter | 13 contracts | unchanged — no new module, no new edge |

## Risks

**Bug history (standing rule).** The families touching this surface are `release-verbs`
(`rc-archive-discovery-state-rejected-by-doctor` — a verb's own legitimate intermediate state
refused by the doctor; `archived-release-state-invalid-and-unparseable-doctor-silent` — the
archive validated by nobody) and `release-workflow` (`release-workflow-coverage-file-in-checkout`).
The recurring shape is **a rule and a writer disagreeing about the same directory**: every fix so
far added a phase-scoped exception to `release_tree.py` so the rule would tolerate what the verb
had just done. This candidate ends the family the only way that does not add a tenth exception —
it deletes the writers and then the rules, so there is nothing left to disagree. If any task in
this candidate finds itself *adding* a branch to `release_tree.py` or `doctor_release.py`, the
task is wrong: stop and report.

- **D10 (open, PM) — the version floor.** `pyproject.toml` must drop 0.4.7 → 0.4.6 for
  release-please to mint 0.4.7. That reset is coupled to `SPEC-DOC-045`'s death and both land in
  T-047-90. If the PM prefers pyproject to stay at 0.4.7, release-please will mint 0.4.8 and the
  release id must follow — decide before T-047-87 writes the manifest.
- **The trigger is the one unprovable link.** `release: published` is emitted by release-please
  through the `GITHUB_TOKEN`; a workflow triggered by the default token does not, by GitHub's
  rule, trigger further workflows — the `release` event from an Action using `secrets.GITHUB_TOKEN`
  will **not** start `release.yml`. T-047-87 must therefore either take a PAT
  (`token: ${{ secrets.RELEASE_PLEASE_TOKEN }}`, an operator act) or T-047-88 must fall back to
  D8's alternative (`push: tags: v*` — same hazard) or to `workflow_dispatch`. **This is the
  single largest risk in the candidate and the implementer must resolve it with the PM at
  T-047-87, not at T-047-88.** Fail-closed, like `SKILLS_REPO_TOKEN`: a missing secret is one
  `::error::` and a non-zero exit, never a silent skip.
- **Deleting a doctor rule cannot be tested by "doctor is still 0".** A deleted validator is
  invisible in a green run. T-047-90's tests must assert the *absence* of the code from the
  issue vocabulary on a tree that previously produced it — i.e. the deleted rule's fixture is
  rewritten to assert no issue, not deleted outright, so the death is recorded as behaviour.
- **The 15 ADR citations are load-bearing prose, not references.** Nine of them sit inside the
  four dying scripts and vanish with them; six sit in `RC-FLOW.md`, `scaffold/releases/AGENTS.md`
  and `_release_store.py`/`_release_tree.py`/`_release_check.py`. `ADR-SUPERSEDED-CITATION` errors
  on *any* citation of a superseded record, so the flip and the last deletion are one commit
  (T-047-91) or the tree is red in between. Stage them together or not at all.
- **`specs/releases/AGENTS.md` and `public/scaffold/releases/AGENTS.md` are the same bytes.**
  T-047-91 edits the scaffold source and re-projects; hand-editing the instance copy to match is
  the forbidden move that hides drift.
- **V35 must fall, not rise.** T-047-91 deletes prose from four SKILL.md/companion files; the
  re-pin is measured after the deletion. If any edit would raise it, the task stops and reports.
- **The candidate cannot be closed by `archive`.** Promote is the operator merging the release
  PR. T-047-92 leaves `_RELEASE.json` at `CLOSURE` with the release PR number recorded through
  `phase CLOSURE --pr <n>`; the `ARCHIVED` phase and the histo line are the PM's at promote,
  under the new rules, with no script to run.
