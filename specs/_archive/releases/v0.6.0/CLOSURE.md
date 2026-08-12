# Closure: Release — v0.6.0 — Gitflow standardization

> **Status:** Aprovado
> **Release ID:** v0.6.0
> **Segment:** `alpha-1`
> **Owner:** product-engineer
> **Closed:** 2026-08-12
> **Shipped range:** `db1702a6..5763a8e1` on `develop`; PR #185 squash-merged to `main` as
> `380b331a`

## Summary

The workspace now has one git contract. Four branch patterns exist and no fifth — `main`,
`develop`, `feature/{M.m.p}`, `hotfix/{M.m.p}` with PATCH ≥ 1 — `develop` is the only
pushable branch, feature and hotfix branches are local-only, and `main` advances only
through a pull request from `develop`. Where each lifecycle stage commits, when the feature
branch merges, what gets reviewed before a push, and which two files a hotfix bumps are
stated once at law level in `DADAIA.md` §5/§6 and explained operationally in exactly one
place: the new universal skill `dadaia-gitflow`. Every other skill and agent that used to
restate a branch rule now references it.

The contract is not advice. Three mechanisms enforce it: the pre-push chokepoint refuses
any pushed ref other than `refs/heads/develop` and validates branch names against the four
patterns; the security verdict is keyed to the `origin/develop..develop` delta being pushed
rather than a bare per-ref sha match; and `pr-source-guard` is now a required check on
`main`, so a pull request from any head but `develop` is mechanically unmergeable. All
three were exercised for real on this instance — a `main` push and a `feature/*` push were
refused by the installed hook, and the guard was demonstrated red on a non-`develop` head
before it was promoted to required.

Two contradictions were retired in the same pass. The hotfix *release* ceremony — a PATCH≥1
release directory with its own SPEC and CLOSURE templates — is revoked: a bug fix is Arm B
in full, run on `hotfix/{M.m.p}`, and the record of what shipped is the bug ledger's
`resolved` event plus the `CHANGELOG.md` entry written with the version bump at merge. The
push-gate security review admits exactly one scan target, the develop diff; a full-tree scan
survives only in the audit lane. Alongside them, every stale citation living on the same
lines was fixed: the four dangling `release-governance` references, the constitution
§11/§13 gap, the scaffold release-directory regex that rejected `v0.6.0` itself, and the
false claim about the `public/scripts/` inventory.

The release shipped by its own rules from the first commit, which was the point: the
definition trio merged to `develop` at milestone (a) and the ship merge at milestone (b),
each followed by a diff-based security review and a push of `develop` — the first push that
passed through the very chokepoint this release installed.

## Tasks completed

History note, binding for this table: the branch history was **rewritten before the ship
push** to scrub a privacy-denylist term that had entered eight commit trees through QA
evidence (see drift `privacy-tainted-history-rewrite`). The authoring SHAs recorded during
implementation are therefore unreachable from any ref and are **not** cited here. Tasks are
cited by commit subject; the shipped range `db1702a6..5763a8e1` (21 commits) and the squash
merge `380b331a` are the durable anchors.

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-060-01 | `dadaia-gitflow`: the single home of the git contract (89 lines, cap 150) | `feat(T-060-01): add dadaia-gitflow universal skill` |
| T-060-02 | `DADAIA.md` §5/§6 rewrite + projection chain | `refactor(T-060-02): four-branch law in DADAIA.md §5/§6` |
| T-060-03 | Tier-2 dedup + hygiene across 4 skills, 7 agents, 4 hygiene sites | `refactor(T-060-03): defer git contract to dadaia-gitflow; fix stale citations` |
| T-060-04 | Chokepoint enforcement, RED before GREEN | `test(T-060-04): RED contract tests for develop-only push policy` then `feat(T-060-04): develop-only push, branch-name validation, develop-diff verdict` |
| T-060-03/04 | QA rework (e2e contract retarget + projection re-sync) | `fix(T-060-04): QA rework — e2e gate tests updated to the new contract; projection re-synced` |
| T-060-05 | CI `pr-source-guard`; retire `feature/**` + `hotfix/v*` push triggers and the unreachable `hotfix-branch-name` job | `ci(T-060-05): pr-source-guard; retire feature/hotfix push triggers` |
| T-060-06 | QA `alpha-1` review committed to the branch (REJECTED, then re-review APPROVED) | `test(T-060-06): alpha-1 QA review committed to the branch` |
| T-060-07 | Six-axis code review + diff-based security verdict (both r2 APPROVED) | review fixes folded into the T-060-04 rework commit; verdicts in `.dadaia/handoff/` |
| T-060-08 | Milestone (b): merge → `develop`, push, PR #185 → `main`, CI green, merge | merge + squash `380b331a` |
| T-060-09 | `pr-source-guard` promoted to a required check on `main` | no commit — GitHub branch rule, recorded below |
| T-060-10 | Memory update → CLOSURE → archive | `docs(T-060-10): v0.6.0 closure, memory atoms, dispositions` |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| **RED before GREEN (A4.4)** — the branch-policy contract tests failed for the real reason before any implementation existed | `pytest -p no:cacheprovider -q tests/unit/features/chokepoints/ tests/contract/` | **18 failed, 2 passed** pre-fix, recorded in the RED commit `test(T-060-04): RED contract tests for develop-only push policy` (authoring sha `075a27f7`, unreachable after the pre-push history rewrite — cite by subject) |
| **Live refusal 1 — `main` (A4.1, SPEC §7.3)** — real `git push`, installed hook, preflight PASS ×5 first | `git push origin main` | `[pre-push] BLOCKED: 'main' is never pushed directly — it advances only via a PR from 'develop' (gitflow law, DADAIA.md §5). Fix: merge your work into 'develop', push 'develop', then open the PR develop → main.` `exit=1` — captured in `ALPHA-1-QA.md` item 2 |
| **Live refusal 2 — `feature/*`** — real `git push`, installed hook, preflight PASS ×5 first | `git push origin feature/v0.6.0` | `[pre-push] BLOCKED: 'feature/v0.6.0' is a feature branch — feature branches are local-only and are never pushed (gitflow law, DADAIA.md §5). Only 'develop' is pushable. Fix: merge the branch into local 'develop', obtain the diff-based security APPROVE, then push 'develop'.` `exit=1` |
| **Refusal 3 — name outside the four patterns** (dry run, no push executed) | `printf 'refs/heads/bugfix/whatever …' \| dadaia ci push-gate-check` | `BLOCKED: ref 'refs/heads/bugfix/whatever' is outside the four permitted branch patterns — main, develop, feature/vM.m.p, hotfix/vM.m.p` `exit=1` |
| **Refusal 4 — `develop` with no covering verdict** (the false-pass risk, R4) | `printf 'refs/heads/develop …' \| dadaia ci push-gate-check` | `BLOCKED: no security-reviewer APPROVE covers the origin/develop..develop delta being pushed` + the on-disk APPROVE ledger + the corrective dispatch instruction; `exit=1` |
| **Allow path — the first push through the new gate (A4.1, §7.7)** | `git push origin develop` | `db1702a6..5763a8e1` accepted: CI preflight green, branch policy passed, APPROVED security handoff `metrics.commit_sha = 5763a8e177115d045e4aea39ad438b59ac931668` covering `db1702a6..5763a8e1` |
| **Ship — PR to `main`, every job green, merged (A5.5)** | PR #185 `develop` → `main` | all checks green; squash-merged as `380b331a`; local `main` fast-forwarded to `origin/main` after the merge |
| **`pr-source-guard` red run (A5.1)** | scratch PR to `main` from a non-`develop` head | run **31634650017** — `pr-source-guard` **FAILED** and the PR was **unmergeable**; the demo head ref has since been deleted |
| **`pr-source-guard` green run (A5.2)** | PR #185 (`develop` head) | `pr-source-guard` green among PR #185's all-green checks |
| **Required check, strictly after the first merge (A5.4 / R2)** | GitHub branch protection on `main` | `pr-source-guard` added to `main`'s required checks **after** PR #185 merged; the list now carries **17** entries including the guard. Flipping it earlier would have blocked every PR, this release's own included |
| **Four projections byte-identical and `0444` (A1.3)** | `sha256sum` ×5 + `stat -c '%a %n'` ×4 | all five copies `ee6623fb5546e1e58f3a744e9ea1eae23bdf7b4a1c5c8e4331454ab97a69a1e2`; all four projections `444` — `ALPHA-1-QA.md` item 1 |
| **Projection chain clean (A6.5)** | `dadaia public doctor` | `exit=0`, zero `[drift]` lines, `[ok] public-privacy` — QA re-review evidence 2 |
| **SDD doctor (A6.5)** | `dadaia specs doctor` | `exit=0` — 0 errors, 6 pre-existing warnings unrelated to this release |
| **Workspace doctor** | `dadaia doctor` | `All invariants OK — workspace is healthy.` `exit=0` (QA re-review evidence 3) |
| **Full suite green (A4.4)** | `pytest -q -p no:cacheprovider tests/` | after rework: 18/18 on the three previously-failing files, then full-suite green on the ship head; pre-rework state (5 failed, 2101 passed) is preserved verbatim in `ALPHA-1-QA.md` item 5 as the finding it was |
| **Static ladder (A4.3)** | `ruff format --check --no-cache`, `ruff check --no-cache`, `mypy --strict`, `lint-imports --config setup.cfg --no-cache` | 645 files formatted; all checks passed; `Success: no issues found in 261 source files`; `Contracts: 9 kept, 0 broken` |
| **A2.3 relocation grep, run twice (author + QA, §7.2)** | `grep -rnE "feature/v?\{?[0-9M]\|hotfix/v?\{?[0-9M]\|only pushable" dadaia_workspace/public/` | every hit resolves to `dadaia-gitflow/SKILL.md`, `DADAIA.md` §5/§6, or a reference to the skill — `ALPHA-1-QA.md` item 6 (independent re-run) |
| **`DADAIA.md` token budget (A1.4)** | character/token measurement before and after the §5/§6 rewrite | **before 14,375 chars ≈ 3,594 tokens → after 15,932 chars ≈ 3,983 tokens, delta +389** against a +400 cap; source file is 233 lines. See the deviation below on how this pair was recovered |
| **Hotfix ceremony gone (§7.4, A3.2)** | read of `public/agents/product-engineer.md` | `:395-404` — "Hotfix release lifecycle — REVOKED (operator ruling D4, 2026-08-12)"; no `release_hotfix`, no `closure_hotfix`, no `specs hotfix open` prescription, no hotfix SPEC, no `specs/releases/<id>/` for a hotfix |
| **One push-gate scan target (A3.3)** | read of `public/agents/security-reviewer.md` | one admitted target, the `origin/develop..develop` diff; `full` appears only in the audit-lane sentence |
| **PR base corrected (A3.4)** | read of `public/agents/code-reviewer.md` | "The PR you gate is `develop` → `main` only — there is no `feature/*` → `main` path." |
| **Constitution citations resolve (A6.2)** | cited §N extracted from `public/agents/**` ∩ scaffold sections | resolution (a) applied uniformly: `## 11. Checkpoints de Revisão` and `## 13. Propriedade da Memória` added; §6/§7/§9/§11/§13 all resolve |
| **Scaffold hygiene (A6.3, A6.4)** | read of `scaffold/releases/README.md`, `ai-engineer.md` vs `ls public/scripts/` | README states `^v\d+\.\d+\.\d+$` and the v2 `ACTIVE.md` block; `ai-engineer.md:353` inventories exactly the 5 files (3 shell + 2 Python) present on disk |
| **No dangling `release-governance` citation (A6.1)** | `grep -rn "release-governance" dadaia_workspace/` | 0 citation hits; `install_helpers.py:222` remains as a **retired-filename migration sweep list**, not a citation |
| **Publishing untouched (A4.5, A7.2)** | `git rev-parse` on `release.yml` at both ends of the range | blob `6fb17ce27f76be1b5aced301ebd5f2d0516186bb` identical at `origin/develop:` and `develop:`; tag carve-out intact; `RELEASE_SEMVER_RE` unchanged; CI preflight ladder copied through verbatim |
| **QA `alpha-1` arc (§7 items 1–6)** | `specs/releases/v0.6.0/ALPHA-1-QA.md` | **REJECTED** (1 HIGH: 5 stale e2e tests; 1 MEDIUM: `public doctor` drift on `security-reviewer.md`; 1 LOW: unrelated stale presence) → rework at the QA-named head → **APPROVED (QA only)** with fresh commands; the REJECTED review is preserved verbatim as the historical record |
| **Six-axis code review (T-060-07)** | `.dadaia/handoff/dadaia-workspace/2026-08-12T180628Z-code-reviewer-v060-six-axis-r2.handoff.json` | **APPROVED** r2 — all four MEDIUMs closed on the executed path (fail-closed stdin, remote-ref/refspec policy, hotfix PATCH≥1 in the validator, honest dead-surface wording); 46/46 chokepoint + e2e push-gate tests green under the reviewer's own run; 0 CRITICAL/HIGH/MEDIUM, 1 LOW bookkeeping residue |
| **Diff-based security verdict (T-060-07/08)** | `.dadaia/handoff/dadaia-workspace/2026-08-12T182602Z-security-reviewer-develop-v060-ship-push-r2.handoff.json` | **APPROVED** r2 for `5763a8e1` over `db1702a6..5763a8e1`: 193 new objects / 50 new blobs scanned, **0** denylist hits, **0** absolute local paths, 0 secrets/keys/tokens/IPs, 0 GHA interpolation in added `run:` blocks, `public-privacy` ok, 0 dependency files touched. One LOW residual: the pre-existing tag-push carve-out |
| **Milestone (a), before implementation (D3, §7.7)** | definition-trio merge + review + push | `.dadaia/handoff/dadaia-workspace/2026-08-12T161307Z-security-reviewer-develop-v060-definition-push-r2.handoff.json` — APPROVED, `develop` pushed with the trio `Aprovado` before Lane A started |

## Drifts

### alpha-1-qa-rejected-then-reworked

**Description:** QA `alpha-1` returned **REJECTED**. Two real defects, both coverage gaps
rather than design flaws. (i) Five pre-existing e2e tests were broken by this release's own
behavior change: three in `tests/e2e/test_push_gate_check.py` pushed `refs/heads/main` and
asserted the pre-v0.6.0 security-verdict-only refusal, which the new develop-only policy now
refuses *first* with a different and more specific message; two in
`tests/e2e/features/test_public_pipeline.py` asserted an exact `EXPECTED_SKILLS` roster that
never gained `dadaia-gitflow`. (ii) `dadaia public doctor` reported
`[drift] stage:agents/security-reviewer.md` — the source edit had landed but the projection
chain was never re-run to completion after it, so the installed copy carried pre-T-060-03
wording (content substantively intact; a stale-projection defect, not a regression).

Root cause of both: T-060-04's write set was scoped to `tests/contract/**` +
`tests/unit/features/chokepoints/**`, explicitly excluding `tests/e2e/**`, and no task's
Done criterion verified that the *existing* e2e suite still passed — only that the *new*
tests did. The PLAN's own rule "every text task ends in a projection step" was stated and
then not executed to completion.

**Resolution:** T-060-03 and T-060-04 returned to `[-]` per T-060-06's own Done criterion.
The three push-gate tests were retargeted at `refs/heads/develop` — the only ref that still
reaches the security-verdict stage — preserving each test's original design intent
(sha-vs-HEAD keying, no-APPROVE refusal, matching-APPROVE pass) rather than deleting it. The
skill-roster fixture gained `dadaia-gitflow`. The projection chain was re-run to completion.
A third site of a pre-existing flake class surfaced during the rework rerun and was handled
on the bug track, not folded into this release: bug
`panel-command-readiness-flaky-under-xdist-load`, root-caused to a fixed 10 s readiness bound
under 22-worker xdist load, `reported` → `resolved`. QA re-review: **APPROVED (QA only)**,
18/18 green on the three files, `public doctor` exit 0 with zero drift.

**Memory updates:** none — the corrected e2e contract is the same contract the memory atoms
describe. The lesson (a behavior change owns the tests that assert the old behavior, wherever
they live) is a process observation, not product truth.

### gate-review-found-four-mediums-in-its-own-gate

**Description:** The six-axis review's first round found four MEDIUM defects in the
enforcement code this release was shipping — exactly the meta-risk the PLAN named ("this
release is enforced by the thing it is changing"). (1) The parser skipped malformed stdin
lines, so an unparseable ref line **failed open** on a *policy* gate. (2) The refspec
`develop:main` was accepted with a valid APPROVE on disk — the remote side was never
policed, so the develop-only rule had a bypass. (3) The branch-name validator accepted
`hotfix/v1.0.0`, contradicting the PATCH ≥ 1 law it was supposed to carry over from the
retired CI job. (4) `product-engineer.md` asserted the nonexistence of surfaces that are
in fact still shipped as dead code.

**Resolution:** All four fixed and independently re-probed by the reviewer against the
shipped code rather than trusted from the commit message. Malformed stdin now refuses the
whole push while empty stdin keeps the distinct "nothing to gate" allow, and the refusal
names `git push --no-verify` as the one traceable bypass — so the gate stays satisfiable.
The remote side is policed: only `refs/heads/develop → refs/heads/develop` passes. The
hotfix pattern is `^hotfix/v\d+\.\d+\.[1-9]\d*$`. The agent file now describes the dead
surface honestly and points at the queued removal. Four new tests, RED first, each asserting
message *content* per A4.2. Verdict r2: APPROVED, 0 CRITICAL/HIGH/MEDIUM.

**Memory updates:** `specs/memory/product/sdd/sdd-gate-v3.md` — the Git Chokepoints section
states the fail-closed parse, the remote-ref policy and the PATCH ≥ 1 pattern as current
truth.

### privacy-tainted-history-rewrite

**Description:** The first ship-milestone security review was **REJECTED**: a
privacy-denylist term (withheld here by the redaction law, as it was withheld from the
handoff) had entered the QA evidence file and, through it, eight commit trees on the
feature branch. This repository is public; a push transmits every object reachable from the
pushed ref, so the term would have been published even though it appeared in no final file
content.

**Resolution:** The term was scrubbed at five sites in `ALPHA-1-QA.md` and the branch
history was **rewritten** before any push, so no tainted object was ever transmitted. The
re-review verified remediation by its own methods rather than on report: all 193 objects and
50 blobs the push would send were decoded and matched against the full denylist and against
absolute local paths — zero hits, down from one term-bearing blob and two path lines; an
independent per-commit full-tree scan across all 21 commits found zero commits introducing a
term-bearing file, down from eight; and all eight previously-tainted SHAs are contained by
**no** ref and therefore unreachable. The delta versus the rejected tip is one file and five
lines; totals unchanged at 32 files / +1,193 / −164, confirming an in-place replacement with
no loss of evidentiary value.

**Consequence for this CLOSURE:** the authoring SHAs recorded during implementation no
longer exist. The Tasks table cites commit subjects; `db1702a6`, `5763a8e1` and `380b331a`
are the durable anchors.

**Memory updates:** none. Two operator decisions remain open and are carried, not closed,
by this release: dispose of the denylist term already published in two archived backlog
files, and extend the privacy-denylist scan beyond `dadaia_workspace/public/**` to the whole
tree of this public repository. Three consecutive pushes now show that only manual review
catches specs-path leaks.

### pr-source-guard-demo-deferred-to-ship

**Description:** T-060-05 required demonstrating `pr-source-guard` red once and green once
and recording the run URLs. The job fires only on a real `pull_request` event targeting
`main`, and at T-060-05 no such PR existed — the first legitimate one is the ship milestone
itself. QA recorded this as an accepted deviation rather than rounding it into a pass.

**Resolution:** The demonstration moved to the T-060-08/09 window and was completed there:
the red run is **31634650017** (FAILED, PR unmergeable, demo head since deleted) and the
green run is PR #185's own `pr-source-guard` check. The guard was promoted to required only
after that first merge, per R2.

**Memory updates:** `specs/memory/quality-assurance.md` — CI section states the required
check and the `main`/`develop`-only push triggers as current truth.

### task-reservation-commit-folds

**Description:** T-060-03, T-060-06 and T-060-10 did not carry the isolated
`chore(tasks): start <task-id>` reservation commit that `dadaia-task-manager` prescribes;
the marker flip was folded into the task's own work commit. For T-060-10 the cause is
structural: `product-engineer` has no shell, so the closing commit is made by the
coordinator and the `[ ] → [x]` flip rides it.

**Resolution:** Each fold is documented in the body of the commit that carried it. The
`[ ] → [-] → [x]` trace is intact in `TASKS.md` and in the QA record; what was lost is the
separate observability point a parallel session would have used, and no parallel session was
running on this branch. Recorded rather than reconstructed — rewriting history to
manufacture a reservation commit would be worse than the deviation.

**Memory updates:** none.

## Known deviations

1. **`DADAIA.md` token pair not surfaced in the implementing agent's return message.**
   A1.4 requires the before/after numbers in CLOSURE. The implementing agent's final message
   was truncated and did not carry them; they were **recovered from the task's handoff on
   disk** (`.dadaia/handoff/dadaia-workspace/2026-08-12T170000Z-ai-engineer-T-060-01-02.handoff.json`):
   before 14,375 chars ≈ 3,594 tokens, after 15,932 chars ≈ 3,983 tokens, **delta +389**
   against the +400 cap. Corroborated by the current source file — 233 lines,
   `dadaia_workspace/public/data/DADAIA.md`, whose sha256
   `ee6623fb…a69a1e2` matches all four projections. The measurement was performed; only its
   reporting channel failed. A1.4 is met, with the recovery path recorded rather than
   glossed.
2. **Reservation-commit folds** on T-060-03 and T-060-06 — see the drift above.
3. **`pr-source-guard` demo timing** — see the drift above; the acceptance itself (A5.1/A5.2)
   is met, only its position in the task order moved.
4. **Tag-push carve-out remains unreviewed** (LOW, pre-existing, deliberately preserved).
   `push_gate_decision` filters tag refs out before any policy runs, so a tag push bypasses
   both the branch policy and the APPROVE requirement — and publishes every commit reachable
   from it. Untouched here because `release.yml`'s OIDC trusted publishing depends on it, and
   `release.yml` is provably byte-identical across the shipped range. Recorded because this
   release narrows every *other* publication channel to `develop`, which raises this one's
   relative weight.
5. **Breaking change for consumer workspaces.** After upgrading, a consumer repo with no
   `develop` branch, or with `release/*`-style branch names, gets hard push refusals. No
   migration verb was written (explicit non-goal). Carried into `CHANGELOG.md`.
6. **Two stale releases remain unarchived.** `v0.2.6` and `v0.2.9` are still under
   `specs/releases/` pending the operator's word — their CLOSURE documents carry conditions,
   so archiving them is an operator decision, not a bookkeeping sweep. This release does not
   touch them.

## Memory updates

- `specs/memory/product/sdd/sdd-bug-backlog-governance.md` — **primary.** New
  `## Branches And Stage Placement` and `## Merge Cadence` sections state the four patterns
  with `develop` as the only pushable branch, `main` as PR-only, stage placement (backlog,
  research and bug registration on `develop` with a commit per registration; definition and
  implementation on `feature/{M.m.p}`), the two merge milestones with their mandatory
  post-merge sequence, and the finalization order memory → CLOSURE → archive. The
  bug-hotfix doctrine now carries the PATCH-mint law (pyproject bump + CHANGELOG entry in
  the merge commit, no ceremony, no release directory). The push sentence is re-keyed from
  "each exact pushed commit SHA" to the `origin/develop..develop` delta. Frontmatter
  `tldr`/`summary`/`tags`/`token_estimate`/`last_updated` updated.
- `specs/memory/product/sdd/sdd-gate-v3.md` — the `## Git Chokepoints` section now states
  the develop-only ref policy, the four-pattern name validator with hotfix PATCH ≥ 1, the
  remote-side refspec policy, the fail-closed stdin parse with its `--no-verify` escape, the
  preserved tag/deletion carve-out, and the develop-diff-keyed verdict. Pre-commit stays
  warn-only. Frontmatter `tldr`/`summary`/`token_estimate` updated.
- `specs/memory/quality-assurance.md` — the `## CI` section gains the `main`/`develop`-only
  push triggers and `pr-source-guard` as a **required** check on `main`, including the
  `env:`-bound, quoted-literal comparison of the fork-controlled head ref. Frontmatter
  `tldr`/`summary`/`token_estimate` updated.
- `specs/memory/product/distribution/public-asset-distribution.md` — states the universal-skill
  projection contract (one canonical `.agents/skills/` home plus `.claude/skills/`, read
  natively by Codex and Kimi Code, no per-harness derivation and no
  `public/entities/registry.json` entry) and names `dadaia-gitflow` as shipping that way.
  Frontmatter `summary`/`token_estimate`/`last_updated` updated.
- `specs/memory/architecture.md` — the chokepoint inventory line now reads
  "`public/scripts/pre-push-ci-gate.sh` - CI preflight, branch policy, and develop-diff
  security verdict". No layer boundary moved; no dependency rule changed.
- `specs/memory/tech-stack.md` — **no change, deliberately.** This release added no
  dependency (0 manifest files touched across the shipped range, verified by the security
  review), changed no Python version, moved no packaging contract, and altered no harness
  roster. `dadaia-gitflow` is an asset inside the existing skills asset type, not a new
  technology; `pr-source-guard` is an inline shell step in the existing workflow, not a new
  action or tool.
- `specs/memory/product/{index.md,catalog.json}` — **not hand-edited.** Four atoms changed
  their frontmatter `tldr`/`summary`, so `catalog.json` must be **regenerated** by the
  catalog generator; see the request in the closing handback.

## Dispositions

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/backlog/gitflow-standardization.md` | backlog | `DELIVERED — v0.6.0` | This CLOSURE in full; the file's own `## Disposition` table maps all six intents to the FR that consumed each (FR1→T-060-02, FR2→T-060-01, FR4→T-060-04, FR3→T-060-03, FR5→T-060-05/09, FR6→T-060-03/04) |

No bug was picked into this release, so no bug row exists.

**Not re-dispositioned here (stated per SPEC §4).** The superseded 2026-08-11 v0.6.0 draft
consumed `test-runtime-efficiency` and `test-artifact-hygiene`; both were closed **on the
bug track** the same day (`test-suite-real-venv-and-ci-longpole`,
`panel-e2e-artifacts-no-consumer`) because the tool was violating contracts it already
promised — Arm B, fixed on the spot. This release neither picked nor re-dispositioned them,
and their archived entries are untouched.

## Backlog returns

- `backlog/candidates.md` ← `specs/backlog/retire-dead-hotfix-surface.md` — **registered**
  (status `candidate`). Removes the surface the revoked lifecycle left behind: the
  `dadaia specs hotfix open` verb, `release_hotfix.md.j2`, `closure_hotfix.md.j2`, and the
  SPEC-DOC-023 check that still nags for the revoked `## Hotfixes pendentes` intake. Filed
  in response to the code review's LOW residue, so `product-engineer.md`'s "removal queued
  in the backlog" is a true statement.
- Candidate noted, not yet filed — **tighten the tag-push channel**: require a pushed tag to
  point at a commit already reachable from remote `develop`/`main`, so tags publish only
  already-reviewed history. Raised as the security review's LOW finding; routed to
  `project-manager` for backlog curation.
- Candidate noted, not yet filed — **extend the privacy-denylist scan** beyond
  `dadaia_workspace/public/**` to the whole tree of this public repository. Raised as an open
  operator decision across three consecutive pushes; routed to `project-manager`.

## Archive decision

**MOVE** — `specs/releases/v0.6.0/` moves to `specs/_archive/releases/v0.6.0/` via `git mv`.
`ACTIVE.md` phase is set to `ARCHIVED` here and repointed to `release: none` /
`phase: none` after the move: no next release is defined yet.
