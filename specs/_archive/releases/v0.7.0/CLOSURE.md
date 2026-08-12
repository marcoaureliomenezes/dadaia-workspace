# Closure: Release — v0.7.0 — Test stewardship

**Status:** Aprovado
**Release ID:** v0.7.0
**Segment:** `alpha-1` (single segment; shipped from it)
**Owner:** product-engineer
**Closed:** 2026-08-12
**Branch:** `feature/v0.7.0` → `develop` → PR #188 → `main`

## Summary

The workspace now has **one** test lifecycle contract, and it reaches every workspace this
library scaffolds. A test declares its intent and its size at birth, is admitted only if it
adds real detection, is demoted at closure, is pruned by a steward's verdict carrying
`file:line` evidence, and can no longer rot silently in a skip, a quarantine or an
invisible flake. The doctrine is stated once at law level (`DADAIA.md` §6, five points plus
the never-delete scoping sentence and the quarantine carve-out), explained operationally in
exactly one file (the new universal skill `dadaia-test-stewardship`), landed for consumers
in exactly two (scaffold constitution §8 and the new `public/templates/tests-AGENTS.md`),
and referenced everywhere else. The four-way coverage split is gone: all four sites now say
the same thing — the 80 % floor is a CI gate and a by-product metric, never an acceptance
target and never an audit score anchor.

The enforceable subset is mechanical, not aspirational. `pytest-timeout` applies per-tier
ceilings at collection (unit 10 s / contract 30 s / integration 60 s / e2e 120 s) without
ever overriding an explicit marker; `flaky` and `quarantine` moved across all six marker
surfaces in one change, with a collection-time refusal for a `quarantine` mark that carries
no registered bug id; every gating selector — six in `ci.yml`, four in `release.yml`, plus
the pre-push preflight — excludes the quarantine lane; `--durations` and per-job
`timeout-minutes` ceilings make the wall-clock budget a reviewable diff; and the panel E2E
retry stopped being invisible — an unregistered pass-on-retry now fails the job, proven
once on this branch with a deliberately flaky throwaway spec that was removed in the same
task. The dead `--ignore=tests/performance` and its pinning assertion are gone.

Nothing was loosened. The 80 % gate is byte-unchanged, `retries: 1` stays, and the
`pre_gate` path-class model is untouched. What changed is that a silence became loud and
nine scattered, contradicting surfaces became one home. Suite remediation itself is
deliberately **not** in this release: the companion backlog entry
`test-suite-remediation-stewardship` now has its blocking dependency discharged.

## Tasks completed

`product-engineer` has no shell; where a task's final SHA was not carried in an evidence
artifact, the commit **subject** is the durable identifier. Every commit below is reachable
from the approved ship tip `d0cd990d` and from the `main` squash `d2c7c32b`.

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-070-01 | `dadaia-test-stewardship` universal skill (groups A–H, parameter table, 3 decision tables, ≤250 lines) | `feat(T-070-01): add dadaia-test-stewardship universal skill` |
| T-070-02 | `DADAIA.md` §6 five-point increment + scoping sentence + quarantine carve-out; four `0444` projections | `7611ffea` — `refactor(T-070-02): test-lifecycle law in DADAIA.md §6` |
| T-070-03 | Consumer surface: scaffold constitution §8, `templates/tests-AGENTS.md`, scaffold memory sync | `feat(T-070-03): consumer test doctrine — constitution §8 + tests/AGENTS.md template` |
| T-070-04 | Tier-2 single-home edits C1–C13 (7 files) + coverage-stance reconciliation | `refactor(T-070-04): single-home test doctrine; reconcile coverage stance` |
| T-070-05 | RED then GREEN: tiered timeouts, `flaky`/`quarantine` markers, preflight cleanup, heading allowlist | `test(T-070-05): RED contracts for tier timeouts and quarantine markers` → `feat(T-070-05): pytest-timeout tiers, flaky/quarantine markers, preflight cleanup` |
| T-070-06 | CI: quarantine selectors, `--durations`, ratcheted `timeout-minutes`, loud-flake gate + live demonstration | `ci(T-070-06): quarantine selectors, durations, budget ceilings, flake detection` |
| T-070-07 | RED then GREEN: scaffolder copies `tests/AGENTS.md` at `alive()` | `test(T-070-07): RED cases for tests/AGENTS.md scaffolding` → `feat(T-070-07): copy tests-AGENTS.md template on context alive` (marker close `85191d0c`) |
| T-070-08 | `alpha-1` QA review on the live instance, baselines frozen | `test(T-070-08): alpha-1 QA review committed to the branch` |
| T-070-09 | Six-axis code review + diff-based security verdict; 8 actionable findings remediated | `ee02006e` + `831e6333` |
| T-070-10 | Merge to `develop`, push, PR #188 → `main`, CI green, merge | ship tip `d0cd990d`; reconciliation merge `84888045`; squash `d2c7c32b` |
| T-070-11 | Memory → CLOSURE → archive | this document |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| **RED before GREEN (T-070-05)** — the tier/marker contracts failed for the right reason before the fix | `pytest -p no:cacheprovider -q tests/contract/test_stewardship_mechanics.py` | **6 failed / 1 passed** at the RED commit `test(T-070-05): RED contracts for tier timeouts and quarantine markers`; every failure an `ImportError`/`AttributeError` on the not-yet-built symbol (`_validate_quarantine_markers`, `_KNOWN_MARKERS`, `_TIER_TIMEOUTS`, `Check.command`) — re-confirmed independently in `ALPHA-1-QA.md` §9 |
| **RED before GREEN (T-070-07)** — only the case needing new behavior failed | `pytest -p no:cacheprovider -q tests/unit/features/spec_context/test_tests_agents_scaffold.py` | **1 failed / 2 passed** at the RED commit `test(T-070-07): RED cases for tests/AGENTS.md scaffolding`; the failure is `test_tests_dir_without_agents_receives_the_template_byte_identical`; the two "nothing happens" cases correctly passed already — `ALPHA-1-QA.md` §9 |
| **Full suite green under the new ceilings** | `pytest -p no:cacheprovider -q tests/ -m "not quarantine" -n auto` | **2120 passed, 3 skipped, 0 failed, 277.68 s (4:37)**; 2123 collected in the gating set. Across the release's runs the pass count moved between **2116 and 2120** as tests were added; no tier ceiling was ever raised to make a run green — `ALPHA-1-QA.md` §8 |
| **Quality ladder** | `ruff format --check .` · `ruff check .` · `mypy --strict dadaia_workspace/` · `lint-imports --config setup.cfg --no-cache` | 647 files formatted; all checks passed; no issues in 261 source files; 9 contracts kept / 0 broken — `ALPHA-1-QA.md` §8 |
| **Doctors** | `dadaia doctor` · `dadaia specs doctor` · `dadaia public doctor` | all exit **0**; specs doctor `0 error(s), 6 warning(s)` (pre-existing, unrelated); public doctor `[ok] public-privacy` + `[ok] entities-derivation` — `ALPHA-1-QA.md` §7 |
| **Projection integrity (A2.3)** | `sha256sum` + `stat -c '%a'` over the four `DADAIA.md` copies | four identical hashes (`4084bef6…5ee`), all mode `444`; `dadaia-test-stewardship` present in `.claude/skills/` and the canonical `.agents/skills/` home — `ALPHA-1-QA.md` §1 |
| **Relocation grep (A4.1), run twice** | `grep -rniE 'SENTINEL\|SCAFFOLD\|QUARANTINE\|tombstone\|demotion' public/ tests/AGENTS.md tests/README.md` | every doctrine hit resolves to the skill, the law, `tests/AGENTS.md`, or an explicit reference; author pass + independent QA pass — `ALPHA-1-QA.md` §2 (one INFO: pre-existing homonym noise) |
| **Coverage stance (A7.1/A7.2/A7.3)** | `grep -rn 'cov-fail-under\|80%' public/ tests/ .github/workflows/ci.yml` | exactly four sites, one stance; no line-% score anchor anywhere; `ci.yml:174`'s `--cov-fail-under=80` byte-unchanged — `ALPHA-1-QA.md` §3 |
| **Constitution citations (A3.2)** | extract cited `§N` from `public/agents/**` + `public/skills/**`, intersect with the scaffold's section set | headings `{1..9,11,13,14}`; citations `§6,§7,§9,§11,§13,§14` — empty difference, no renumbering — `ALPHA-1-QA.md` §4 |
| **Consumer landing (A3.4)** | `pytest tests/unit/features/spec_context/test_tests_agents_scaffold.py` | 4 cases pass: `tests/` + no file → byte-identical copy; existing file → untouched; no `tests/` → nothing written, no directory created; symlinked `tests/` → refused (added at review r2) |
| **Loud-flake gate, demonstrated live (A5.5)** | deliberately flaky throwaway Playwright spec pushed on the branch, then removed in the same task | job output `STEP-FAILS: 1 test(s) passed only on retry — unregistered pass-on-retry` / `detection-exit=1`; the throwaway spec was removed in T-070-06, leaving no residue. QA judged the two-line capture credible as a same-shape match to `ci.yml`'s step and recorded evidence thinness as finding **F2 (LOW)** — the step body itself was re-executed independently at code review r2 (missing / empty / malformed / non-numeric report all exit 1) |
| **Two explicit justified timeouts (R5 bar)** | read of the two markers and their inline justifications | `tests/integration/cli/test_context_name_differs_from_repo_slug.py::test_create_refuses_a_name_no_other_verb_can_use` — `timeout(180)`, measured ~20 s solo / >60 s under xdist; `tests/e2e/features/test_handoff_pipeline.py::test_full_handoff_emit_and_validate` — `timeout(300)`, measured 71 s solo. Each cites a measured number, the ceiling exceeded and why, and names `specs/backlog/test-suite-remediation-stewardship.md` as the **structural split** that retires it. Neither raises a default — `ALPHA-1-QA.md` "Explicit-timeout justification review" |
| **`alpha-1` QA verdict** | qa-engineer review from the live instance (not the diff) | **PASS / APPROVE on the first pass** — 9/9 checks with per-check evidence, 0 CRITICAL/HIGH/MEDIUM, three non-blocking findings (F1 INFO grep homonyms, F2 LOW flake-evidence thinness, F3 INFO ratchet re-derivation). `specs/releases/v0.7.0/ALPHA-1-QA.md`; handoff `2026-08-12T214958Z-qa-engineer-T-070-08-alpha1-qa.handoff.json` |
| **Code review (six-axis)** | code-reviewer r1 then r2 on the remediation commits | **APPROVED at r2** (`831e6333`): **8 of 8** actionable r1 findings CLOSED, each verified by execution rather than by reading the commit message; 40 tests run / 40 passed across touched and affected surfaces; 9 files, +102/−14, no drive-by edits. One residual INFO carried here: a structurally valid Playwright report **lacking a `stats` key** still exits 0, because `jq -er '.stats.flaky // 0'`'s `// 0` default defeats the `-e` check it is paired with — a **one-token fix** (drop `// 0`, or add a `has("stats")` precheck), reachable only through future Playwright schema drift, and the `ee02006e` commit message overstates the current behavior. Handoffs `…215825Z-code-reviewer-v070-six-axis` (r1) and `…220718Z-code-reviewer-v070-six-axis-r2` |
| **Security verdict (diff-based, `origin/develop..develop`)** | security-reviewer r1 then r2 | **REJECTED at `7318f26d`** → **APPROVED at `d0cd990d`** (26 commits, 236 objects, 60 new blobs scanned against 18 denylist terms: **0** denylist hits, 0 foreign-slug hits, 0 absolute local paths, 0 scratchpad paths, 0 secrets/keys/tokens/IPs, 0 `shell=True`, 6 tainted SHAs checked → **0 reachable from any ref**). Handoffs `…221221Z-…-ship-push` (REJECTED) and `…221751Z-…-ship-push-r2` (APPROVED). See the drift `privacy-denylist-recurrence` below |
| **Reconciliation merge verdict** | security-reviewer on the content-empty merge | **APPROVED at `84888045`**: proven content-empty *structurally* — the merge tip's tree object is identical to the already-approved tip `d0cd990d`'s tree; scoped scan (`--not origin/main`) transmits exactly **1 new object** and it is the merge commit itself (0 new blobs, 0 new trees); the commit message itself scanned clean. Handoff `…222753Z-…-reconcile-push` |
| **`DADAIA.md` always-on token cost (A2.2)** | token measurement before and after the §6 edit | **3983 → 4204 (Δ +221)** against the **+400** cap — commit `7611ffea`; the file is byte-identical to that "after" state at closure |
| **Ship (T-070-10)** | PR #188 `develop` → `main` | every CI job green including the new flake gate and the new ceilings; `pr-source-guard` green on a `develop` head; **squash-merged as `d2c7c32b`**, after the reconciliation merge described below |

## Drifts

### privacy-denylist-recurrence

**Description.** The pre-push security review **REJECTED** the ship tip `7318f26d`: a
privacy-denylist term — a private consumer project name on the operator's curated 18-term
protect-list — had re-entered the repository through `specs/releases/v0.7.0/ALPHA-1-QA.md`,
transcribed verbatim from `dadaia doctor` output while QA validated on the live instance.
The term itself is withheld from this record by design. This is a **recurrence**: the same
term class, the same file class (`ALPHA-1-QA.md`), the same source (quoted doctor output),
one release after the identical block on v0.6.0. It had spread to 6 of the 24 commit trees
in the range, so a tip-only edit could not remediate — a push transmits every reachable
object. `check_public_privacy()` returned `ok` throughout, correctly: it scans only
`dadaia_workspace/public/**` and cannot see `specs/`. Nothing mechanical stood between the
term and a public push except the manual review. Severity was MEDIUM rather than HIGH
because the term is already published at the base in two archived backlog files.

**Resolution.** The evidence line was rewritten to carry the same evidentiary meaning
generically ("an unrelated Spec Context Project"), and the range was **rebuilt by history
rewrite from the QA commit forward**, exactly as in v0.6.0. The re-review at `d0cd990d`
scanned all 60 new blobs and all 26 commit trees: **0 denylist hits**, and the 6 tainted
SHAs are **unreachable from any ref**. v0.6.0 fixed the symptom and left the cause as an
open operator decision; two identical incidents in consecutive releases is the evidence
that the workspace's own root-cause doctrine is owed a structural fix. That fix is
registered as `specs/backlog/whole-tree-denylist-push-scan.md` — extend the denylist scan
beyond `public/**` to the whole tree at the push gate — and it **stays `candidate`
pending the operator's decision**, with the security reviewer's tag-carve-out design note
attached to it through the ship and reconcile handoffs (a scan implemented only on the
develop delta leaves the tag-push path, which bypasses branch policy and the verdict
entirely, unscanned; the two must be designed together). A second, cheaper mitigation is
recorded as a backlog return below: QA evidence transcription should redact foreign Spec
Context names at authoring time — both incidents entered exactly that way.

**Memory updates:** none. This is a process and push-gate concern; it changes no statement
of current product truth in `specs/memory/**`.

### reconciliation-merge-is-a-standing-gitflow-mechanic

**Description.** PR #188 could not merge on a fully green build: GitHub's **strict
up-to-date** branch-protection rule on `main` requires the PR head to contain the target's
tip, and `main` had advanced past `develop`'s merge base. The fix was to merge `main` back
into `develop` before merging the PR. That merge resurrected loose copies of files a
previous release had archived (a `specs/backlog/` entry and a `specs/releases/v0.6.0/`
tree), because the old merge base predates that archive move — the conflict had to be
resolved in **develop's** favour, keeping the archived copies as the single source of truth
and dropping the resurrected loose ones.

**Resolution.** The reconciliation merge landed as a **content-empty** commit `84888045`
(tree identical to the approved tip `d0cd990d`), was security-reviewed as its own push, and
unblocked the squash-merge `d2c7c32b`. This is **not** a one-off: it is a **new standing
gitflow mechanic discovered by this release** — *every squash-merge to `main` leaves
`develop` behind, so every subsequent PR requires a reconciliation merge of `main` into
`develop` first, and every such merge must drop the loose copies its old merge base
resurrects in favour of `develop`'s archives.* Recommended as a one-line addition to the
`dadaia-gitflow` skill; routed as a backlog return below, since `public/**` is
`ai-engineer`'s surface and this closure authors no skill text.

**Memory updates:** none in this release. `sdd-bug-backlog-governance` already carries the
four-branch contract and defers the operational detail to `dadaia-gitflow`; the mechanic is
recorded here and lands in memory when the skill edit ships.

### memory-class-write-during-implementation

**Description.** `specs/memory/.heading-allowlist` was written **twice outside the
`DEFINITION`/`CLOSURE` phases** by `software-engineer` — once under T-070-05 (SPEC-sanctioned
by FR5.6, which explicitly assigned the file to that task's write set) and once under
T-070-09 as a review-driven fix — while `ACTIVE.md` read `phase: IMPLEMENTATION`. The
code reviewer flagged it as a governance observation (r2 finding 6) and asked that it be
recorded here. The gate did not stop either write: the MEMORY path class matches
`specs/memory/**/*.md` and legacy memory paths, and a **dotfile** under `specs/memory/`
falls outside that classifier.

**Resolution.** Recorded as a known deviation, not retro-fixed. Two questions are handed to
the operator: (i) whether the MEMORY classifier should cover dotfiles under
`specs/memory/`, and (ii) whether a SPEC may assign a memory-class path to a non-CLOSURE
task at all — this release's SPEC did, deliberately, because the allowlist must be in force
before the new headings land. Both are backlog returns below. The file's content is correct
and verified: exactly the four headings A5.7 requires, with `dadaia specs doctor` at 0
errors.

**Memory updates:** none — the deviation concerns the gate's path classifier, not a
statement about the product's current behavior.

### qa-marker-fold

**Description.** T-070-08 folded its `[ ]` → `[-]` → `[x]` marker transitions into a single
commit alongside the review file, rather than the ordinary two-commit reserve/complete
discipline of `dadaia-task-manager`, under the operator's explicit economy directive for
that task. The QA review records the fold itself for audit-trail continuity.

**Resolution.** Accepted deviation, recorded in both `ALPHA-1-QA.md` ("Marker note") and
here. No task ran concurrently with T-070-08, so the observable-reservation property the
two-commit discipline protects was not needed.

**Memory updates:** none.

### qa-review-file-history-rewritten

**Description.** `specs/releases/v0.7.0/ALPHA-1-QA.md` as it stands on `develop` and `main`
is **not** byte-identical to the file the QA author originally committed: one evidence line
was redacted and the commit range was rebuilt from that commit forward, so the original
bytes exist in no reachable ref. The same happened to v0.6.0's QA review, for the same
reason.

**Resolution.** Recorded so a future reader is not confused by a review file whose history
does not start where the task did. The redaction removed a private project name and changed
no verdict, no check, no evidence value and no finding. The archived review under
`specs/_archive/releases/v0.7.0/` is the canonical copy.

**Memory updates:** none.

## Memory updates

Written in the `CLOSURE` phase, describing the product **as it is now** — no changelog
narrative, no "we used to…", every number cross-checked against what is actually in force
(`pyproject.toml`, `tests/conftest.py`, `ci.yml`, `release.yml`, `tests/AGENTS.md`).

- `specs/memory/quality-assurance.md` — **primary.** `Layers` gains the layer→size-tier
  column (SMALL = unit + contract, MEDIUM = integration, LARGE = e2e) and the intent-taxonomy
  **mapping** (CONTRACT / SENTINEL / SCAFFOLD / QUARANTINE declared in the module docstring,
  never as a marker, with the reason), pointing at `tests/AGENTS.md` for the prose and at
  `dadaia-test-stewardship` for the protocol; the stale "~2,100 collected" is replaced by the
  measured **2,123 collected / 55 LARGE e2e-tier** with the 2,120-passed 4:37 run; new h2
  **`Flake Policy`** (both markers, the bug-id collection refusal and its stderr pre-print,
  the pinned closed marker set, the cap of 8, the 30 d → `disabled` / 30 clean days →
  restored / `disabled` + 1 release → deleted ladder, the rerun bound of 3, the < 0.5 % target
  against the 1 % ceiling, and the push-green carve-out with the fail-closed loud-flake step);
  new h2 **`Test Health`** (the three metrics, the trigger-based audit thresholds, the tier
  timeout table, the two justified explicit ceilings, the e2e owner rule, the LARGE cap of 30
  as a WARN, the frozen wall-clock baselines, the mutation cadence); `CI` gains the quarantine
  exclusion across all ten gating selectors plus the preflight, `--durations`, the per-job
  `timeout-minutes` ceilings, and the single coverage stance. Frontmatter `tldr`/`summary`/
  `tags`/`token_estimate` refreshed.
- `specs/memory/tech-stack.md` — the Quality bullet now names the real pytest plugin set:
  `pytest-cov`, `pytest-xdist` (`-n auto`, previously omitted although already in use),
  `pytest-randomly` (same omission) and the newly added `pytest-timeout` with per-tier
  defaults; the marker set is stated as **eight** (adds `flaky`, `quarantine`); coverage
  described as a gate, never an acceptance target. `last_updated` and `token_estimate`
  refreshed.
- `specs/memory/product/distribution/public-asset-distribution.md` — the universal-skill
  roster names `dadaia-test-stewardship` alongside `dadaia-gitflow`; a new paragraph states
  that repo templates land at `alive()` (not at install): `repo-AGENTS.md` at the repo root
  and `tests-AGENTS.md` at `<repo>/tests/AGENTS.md` **only** when `tests/` is a real
  directory (symlink refused) and no file exists — never creating the directory, never
  overwriting an operator file, shipping parameterized with `<ANGLE-BRACKET>` placeholders.
  `summary` and `token_estimate` refreshed.
- `specs/memory/architecture.md` — **no change, deliberately.** The atom carries no
  `spec_context` `alive()` scaffold-file inventory for the new copy to join: its two
  test-adjacent sentences are the import-linter/AST contract statement (unchanged by this
  release) and the repo-hygiene forbidden-artifact list (unchanged). The one `alive` mention
  is about injected git identity for tool-initiated commits. The scaffold copy set is
  functional distribution truth and is recorded in `public-asset-distribution.md` instead,
  which already owns the template roster. FR6 anticipated this as "expected minor — state
  explicitly either way"; the explicit statement is: **unchanged, and why**.
- `specs/memory/product/{index.md,catalog.json}` — **not hand-edited.** One atom's `summary`
  moved (`public-asset-distribution`), so the catalog must be **regenerated** with
  `dadaia memory catalog generate` (requested below). `quality-assurance.md` and
  `tech-stack.md` are `category: core` and carry no catalog entry.

## Dispositions

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/backlog/test-stewardship-standardization.md` | backlog | `DELIVERED — v0.7.0` | this CLOSURE + the intent→FR map below; edited in place with the mapping recorded in its frontmatter |

The picked entry was consumed **in full — all three of its intents**:

| Intent (subject `ref`) | Consumed by | Evidence |
|---|---|---|
| `quality-assurance.md#Layers` — the doctrine itself (taxonomy, tiers, admission, deletion, tombstone ban, demotion-at-closure, flake pipeline, health metrics), with the 13 mapped conflicts resolved by **editing**, never appending | **FR1** (the skill) + **FR2** (the law) + **FR4** (the C1–C13 single-home edits) + **FR7** (the coverage reconciliation) | A4.1 relocation grep clean, run twice; A7.1/A7.2 four sites one stance; A2.1 each law point exactly once |
| `public-asset-distribution` — the new universal skill, the `tests/AGENTS.md` public template, the scaffold constitution article, the `DADAIA.md` §6 increment with the never-delete scoping sentence | **FR1** + **FR2** + **FR3** | A1.1–A1.5 (skill projected, ≤250 lines, no verbatim law copy); A3.1–A3.5 (§8 present, no renumbering, zero workspace literals in the template); A2.2 tokens 3983→4204 |
| `quality-assurance.md#CI` — the mechanical wiring (pytest-timeout tiers, the two markers across the closed set, Playwright flaky-status recording, `--durations` + budget ratchet, retire the dead `--ignore`, refresh the stale memory facts) | **FR5** + **FR6** | A5.1–A5.8 all green; A6.1–A6.4 in this CLOSURE's memory-updates section |

**Not dispositioned by this release, by design:**

- `specs/backlog/test-suite-remediation-stewardship.md` — stays **`candidate`**, and is now
  **unblocked**: it was blocked on the doctrine existing, and the doctrine ships here. It is
  the companion that applies the contract to this repo's own suite (the tombstones, the
  tautology/change-detector families, LARGE ownership, the permanently-skipped journey spec,
  the duplicated panel readiness helpers, the artifact residue), turns the LARGE cap from a
  WARN into a failure once the count can satisfy it, and structurally splits the two tests
  currently carrying justified 180 s / 300 s ceilings. This release's CI now *measures* the
  LARGE count, the flake rate and the durations, so its targets are visible from day one.
- `specs/backlog/whole-tree-denylist-push-scan.md` — stays **`candidate`**, **operator
  decision pending**. Its urgency is no longer theoretical: see the drift
  `privacy-denylist-recurrence` (second identical incident in consecutive releases, both
  caught only by manual review). The security reviewer's **tag-carve-out design note** is
  attached through the ship and reconcile handoffs and must be designed together with the
  scan: `push_gate_decision` filters tag refs out before any policy runs, so a scan that
  covers only the develop delta leaves the tag path — which publishes every commit reachable
  from the tag — unscanned.
- `specs/backlog/retire-dead-hotfix-surface.md` — stays **`candidate`**. The dead
  `release_hotfix.md.j2` / `closure_hotfix.md.j2` templates and the `dadaia specs hotfix open`
  verb are still present and still never invoked; v0.7.0 touched none of them.

## Test dispositions

| Kind | Deleted/expired test | Replacement / disposition | Evidence |
|------|----------------------|----------------------------|----------|
| demotion | none | No LARGE test was deleted or demoted in this release: v0.7.0 ships governance and enforcement, not suite remediation (SPEC §4). The 55-strong LARGE set is unchanged and its reduction is the companion entry's job | SPEC §4 out-of-scope; `ALPHA-1-QA.md` §9 baselines |
| SCAFFOLD expiry | the deliberately flaky throwaway Playwright spec (T-070-06) | **deleted in the same task** that created it, exactly as an admission-filter SCAFFOLD must die at its task's closure | T-070-06 Done criterion; the demonstration output is preserved in the Validations table above, the spec is not in the tree |
| SCAFFOLD expiry | the pid-named probe file written under `tests/tmp/` by the quarantine-refusal contract test | self-expiring: created and `unlink(missing_ok=True)`-ed inside the test's own `finally` | code review r2 finding 2, verified by execution |
| quarantine expiry | none | No test in the tree carries `quarantine`. That is correct rather than incomplete: a permanently parked sample would itself violate the 30-day escalation rule. The mechanism is proven by the contract tests and by the live flake demonstration | `ALPHA-1-QA.md` §5 |
| deferred split | `test_create_refuses_a_name_no_other_verb_can_use` (180 s) and `test_full_handoff_emit_and_validate` (300 s) | **kept**, each with a measured, justified explicit ceiling; structural split queued in `test-suite-remediation-stewardship` | `ALPHA-1-QA.md` "Explicit-timeout justification review" |

## Backlog returns

Routed through `project-manager`, which curates `specs/backlog/**`:

- `backlog/candidates.md` ← **Mutation-testing tool selection and wiring.** The cadence
  (1×/release, off the push path) is declared in the skill and in memory; choosing between
  mutmut / cosmic-ray / another and wiring it is its own task (SPEC §4 non-goal).
- `backlog/candidates.md` ← **Mechanical enforcement of the intent docstring (P9).** 384
  existing files are non-compliant, so a check today would be unsatisfiable — a defect in the
  check under the Satisfiable Diagnostics law. Enforceable once the companion remediation
  lands.
- `backlog/candidates.md` ← **The `stats`-key residual in the loud-flake gate.** A
  structurally valid Playwright report lacking `stats` still exits 0 because `// 0` defeats
  `jq -e`; one-token fix (drop `// 0`) or a `has("stats")` precheck, plus correcting the
  `ee02006e` commit-message claim. Reachable only through future Playwright schema drift.
- `backlog/candidates.md` ← **`dadaia-gitflow`: record the reconciliation-merge mechanic.**
  One line stating that every squash-merge to `main` requires a subsequent reconciliation
  merge of `main` into `develop`, and that such a merge resolves resurrected loose copies in
  favour of `develop`'s archives. `public/**` is `ai-engineer`'s surface.
- `backlog/candidates.md` ← **Redact foreign Spec Context names at QA authoring time.** Both
  privacy incidents entered through verbatim `dadaia doctor` output transcribed into an
  `ALPHA-1-QA.md`; a doctrine line (or a doctor `--redact` output mode) closes the entry path
  at the source, complementing the whole-tree scan.
- `backlog/candidates.md` ← **MEMORY path class vs dotfiles / SPEC-assigned memory writes.**
  Decide whether `specs/memory/.heading-allowlist` (and dotfiles under `specs/memory/`
  generally) belongs to the MEMORY class, and whether a SPEC may legitimately assign a
  memory-class path to a non-CLOSURE task. See the drift above.
- `backlog/ideas.md` ← **A `doctor`/lint warning for an installed `tests/AGENTS.md` that
  still contains `<[A-Z_]+>` placeholders** (code review r1 finding 8, half-implemented: the
  fill-me banner shipped, the check did not).
- `backlog/ideas.md` ← **Note the relocation-grep homonym collision in the skill** so a future
  auditor does not chase pre-existing, unrelated uses of "scaffold"/"sentinel"/"quarantine"
  (QA finding F1).
- `backlog/ideas.md` ← **Embed the frozen wall-clock baselines in repository text** so the
  1.5× `timeout-minutes` ratchet can be re-derived from the repo alone at audit time (QA
  finding F3).
- `backlog/ideas.md` ← **Tag-push carve-out** (carried forward from v0.6.0, restated by both
  security reviews): require a pushed tag to point at a commit already reachable from remote
  `develop`/`main`, designed together with the whole-tree denylist scan.
- `backlog/ideas.md` ← **Destination-file symlink hardening for the adjacent
  `repo-AGENTS.md` copy**, matching `workspace_guardrail.py`'s four refusal sites. The new
  `tests/AGENTS.md` seam was hardened at review r2; its neighbour still follows the older
  shape.
- `backlog/ideas.md` ← **Dispose of the already-published denylist term** in the two archived
  backlog files that carry it (now reachable from both `main` and `develop`) — an operator
  decision carried forward from v0.6.0.

## Archive decision

**MOVE** — `specs/releases/v0.7.0/` moves to `specs/_archive/releases/v0.7.0/` via `git mv`
(requested from the coordinator; `product-engineer` has no shell). `ACTIVE.md` phase is set
to `ARCHIVED` here and is then repointed to `release: none` / `phase: none` with the
`segment:` line dropped, since no release follows immediately.
