# TASKS — Release: 0.4.7

**Status:** Approved
**Release ID:** 0.4.7
**Owner:** dd-software-engineer

---

## Candidate 10 — the release is a release PR

- [ ] T-047-87 — FR1: release-please owns the version, the CHANGELOG and the tag.
  New `.github/workflows/release-please.yml` on `push: branches: [main]` plus
  `workflow_dispatch`, `permissions: contents: write, pull-requests: write`, one job, one step:
  `googleapis/release-please-action@45996ed1f6d02564a971a2fa1b5860e934307cf7  # v5.0.0` with
  `config-file: release-please-config.json` and `manifest-file: .release-please-manifest.json`
  and `token: ${{ secrets.RELEASE_PLEASE_TOKEN || github.token }}` — **no `release-type:` input**:
  with a config file present it switches the action out of manifest mode (README "Breaking
  changes"), so `"release-type": "python"` lives inside the config's `packages["."]`.
  New `release-please-config.json` at the root: `packages: {".": {"release-type": "python",
  "changelog-path": "CHANGELOG.md"}}`, `"include-component-in-tag": false`,
  `"bump-minor-pre-major": true`, `"bump-patch-for-minor-pre-major": true` (pre-1.0: `feat` →
  patch, BREAKING → minor — what makes the first release PR propose 0.4.7, not 0.5.0), and
  `changelog-sections` for `feat|fix|refactor|docs|ci|test|chore`. New
  `.release-please-manifest.json`: `{".": "0.4.6"}` — the LAST PUBLISHED version, the floor it
  bumps from (PLAN D10: `pyproject.toml` follows in T-047-90 with `SPEC-DOC-045`'s death). The
  `GITHUB_TOKEN` cannot trigger a downstream workflow; the fallback keeps the release PR working
  before the operator adds `RELEASE_PLEASE_TOKEN`, and T-047-88's trigger is settled with the PM
  on that fact.
  Seam: the release PR on `main` — the one reviewable artifact before publication.
  RED: `test_release_semver_canon.py` — a new case parses both JSON files: the manifest maps
  `"."` to a bare SemVer equal to the latest `v*` git tag (0.4.6), the config sets both pre-1.0
  bump flags `true`, `include-component-in-tag` `false`, `packages["."].release-type == "python"`;
  `test_ci_workflow_hygiene.py` — `release-please.yml` exists, triggers on `push` to `main`, pins
  the action to a 40-hex sha with a trailing `# v<x.y.z>` comment, passes no `release-type`. Both
  fail today: the three files do not exist.
  Write set: `.github/workflows/release-please.yml`, `release-please-config.json`,
  `.release-please-manifest.json`, `tests/contract/`
  `{test_release_semver_canon,test_ci_workflow_hygiene}.py`.

- [ ] T-047-88 — FR1: `release.yml` executes a decision it no longer makes.
  `.github/workflows/release.yml`: `on: push: branches: [main]` becomes
  `on: release: types: [published]` (D8 default); the `check` job — the pyproject-vs-tags
  comparison and its `version`/`skip` outputs — is deleted whole, together with every
  `if: needs.check.outputs.skip == 'false'` guard and every `needs: [check, …]` entry; the
  version every downstream job interpolates becomes `${{ github.event.release.tag_name }}`
  stripped of its `v` (one `id: version` step in `build`, exposed as a job output), so artifact
  name, `approve` message, `pip install` line and skills-repo subject read one source. The `Create GitHub release tag` step in `publish` is
  deleted — release-please created the tag. `approve` (the `release-gate` environment),
  `publish` (OIDC trusted publishing), `smoke-test` and `publish-skills-repo` keep their bodies
  and their `needs:` chain unchanged. `CHANGELOG.md` gains release-please's header above the
  existing `## [0.4.7]` section; nothing at or below that line is touched, ever.
  Seam: the `release` event — the workflow stops deciding *whether* and only does *how*.
  RED: `test_ci_workflow_hygiene.py` — `release.yml`'s `on:` is exactly the `release`/`published`
  pair, no job is named `check`, no step text contains `git ls-remote --tags` or `git tag `, the
  four surviving jobs are present with `approve` carrying `environment: release-gate` and
  `publish` `needs:` it, and no `needs:` names a job the file does not define; fails today on the
  `on:` block, the `check` job and the tag step.
  Write set: `.github/workflows/release.yml`, `CHANGELOG.md`,
  `tests/contract/test_ci_workflow_hygiene.py`.

- [ ] T-047-89 — FR2: four scripts, two subcommands and the schema's `rc` die.
  Delete `_release_rc.py` (72), `_release_fold.py` (87), `_release_fold_plan.py` (101) and
  `_release_archive.py` (144) under `dd-release-implementation/scripts/`; `release.py` loses the
  `rc-archive`, `fold` and `archive` `_HELP` entries, their imports and their argument blocks —
  the roster becomes `new | phase | check`. `_release_schema.py` loses `RC_DIR_RE` and
  `rc_numbers()`; `release-state-v1.schema.json` loses the top-level `rc` and `implemented.rc`
  and stays `additionalProperties: false`, so an old document carrying `rc` is refused by name.
  `_release_phase.py` loses its `rc-archive` half and every `fix:` naming a dead verb
  (`_release_new.py:110` included) re-points at `release.py new` or `phase`. `_release_tree.py
  check` keeps tolerating existing `rc-N/` and `_archive/` read-only — no new branch enters it;
  the exclusion already lives in the name rule. No `--legacy` path (replace, don't layer).
  Seam: `release.py`'s subcommand table — three verbs, no aliases, no shims.
  RED: `test_release_state_schema.py` — the schema's property set equals `{schema_version,
  release_id, phase, origin, defined, implemented, shipped, log}`, no `rc` anywhere, a document
  carrying `rc` refused; `test_slop_ratchets.py` V36 re-pinned to ≤ 32 files / ≤ 3787 lines
  (measured after the deletion, whichever is lower); `test_public_scripts_thin_wrapper.py` roster
  unchanged for `release.py`, ceiling re-measured. Fails today: the schema still declares `rc`.
  Write set: the `dd-release-implementation/scripts/` survivors
  `{release,_release_phase,_release_schema,_release_new,_release_tree,_release_check,_release_histo}.py`
  plus deletion of `{_release_rc,_release_fold,_release_fold_plan,_release_archive}.py`;
  `public/schemas/releases/release-state-v1.schema.json`; `tests/contract/`
  `{test_release_state_schema,test_slop_ratchets,test_public_scripts_thin_wrapper}.py`.

- [ ] T-047-90 — FR2: the doctor stops policing an archive nobody writes.
  `features/specs/release_tree.py`: `_archive_issues()` and the `RELEASE-TREE-ARCHIVE-ID` /
  `RELEASE-TREE-ARCHIVE-UNSHIPPED` codes are deleted; the walk keeps listing `_archive/**` and
  keeps validating those documents against the schema, phase and ts-order rules (history stays
  readable, it just stops being ranked against a live id). In `doctor_release.py`,
  `SPEC-DOC-045` (pyproject == live release id) and its check method die,
  and `pyproject.toml`'s `version` returns to `0.4.6` — the last published version, the floor
  release-please bumps from (PLAN D10); both in this one commit so no intermediate tree is red.
  `release.py phase CLOSURE` gains ONE optional `--pr <n>`, recorded in the `log` note as the
  merged release PR — the number `archive --pr <n>` carried, moved from a deleted verb to a
  living one; `dadaia help tree` is byte-identical (ADR 0018: no verb enters).
  Seam: the `log` note — promote leaves a number, not a moved directory.
  RED: `test_release_tree_canon.py` — the two archive cases are REWRITTEN (not deleted) to assert
  the previously-refused fixtures now produce no issue, and `ARCHIVE-ID`/`ARCHIVE-UNSHIPPED`
  appear in no issue code anywhere; `test_doctor_pyproject_version.py` is deleted whole citing
  "feature removed" (`dd-test-stewardship` decision table), `SPEC-DOC-045` asserted absent from
  `test_every_block_carries_a_fix.py`'s roster; a new `phase CLOSURE --pr` case asserts the number
  lands in the `log` and that omitting the flag is still accepted. V32 (682), V33 (35) and the
  module ceiling (699/700) re-pinned DOWN to measured. Fails today: both rules still fire.
  Write set: `features/specs/{release_tree,doctor_release}.py`, `pyproject.toml`,
  `dd-release-implementation/scripts/{release,_release_phase}.py`, `tests/contract/`
  `{test_release_tree_canon,test_every_block_carries_a_fix,test_slop_ratchets}.py`, deletion of
  `tests/unit/features/specs/test_doctor_pyproject_version.py`,
  `specs/memory/product/platform/workspace-doctor.md`.

- [ ] T-047-91 — FR3: the law stops naming verbs that no longer exist.
  Every `rc-archive` / `release.py fold` / `release.py archive` / `rc-N` mention leaves
  `dadaia_workspace/public/`: `scaffold/releases/AGENTS.md` (lines 7, 10, 12, 16, 25 — one live
  release directory per version, the trio overwritten by the next candidate, promote = merging
  the release PR), `skills/dd-release-implementation/{SKILL,RC-FLOW,RELEASE-EVENTS}.md`,
  `skills/dd-release-definition/SKILL.md`, `skills/dd-gitflow-default/SKILL.md` (steps 9/11 and
  the `rc-N` branch line), `skills/dd-spec-navigator/SKILL.md` (step 1 and the glossary row),
  `templates/specs-AGENTS.md`, `data/AGENTS.md` + `data/CONTEXT-MAP.md` rows, and the root map's
  flow line; `specs/releases/AGENTS.md` follows by re-projection, never by hand. ADR 0005, 0006,
  0008, 0009 and 0014 flip to `"status": "superseded"` in `specs/ADRs/decisions.jsonl` **in this
  same commit** — `ADR-SUPERSEDED-CITATION` errors on any surviving citation, so the flip and the
  last deletion are atomic. `sdd-bug-backlog-governance.md` (lines 44, 46, 50),
  `pypi-distribution`, `ARCHITECTURE.md` line 126, `CONSUMER_VALIDATION_RECIPE.md` and the
  behavior map re-recorded. V35 falls, never rises: the deleted prose is the payment.
  Seam: `decisions.jsonl`'s `status` field — one flip retires five records and their vocabulary.
  RED: a new case in `test_every_block_carries_a_fix.py` (or the existing law-grep contract):
  `grep -rnE "rc-archive|release\.py fold|release\.py archive|rc-N"` over
  `dadaia_workspace/public/` and `specs/memory/` is empty, and every `fix:` names a verb
  `release.py --help` still lists; `ADR-SUPERSEDED-CITATION` green with the five records
  superseded; V35 re-pinned DOWN. Fails today on 15 ADR citations and ~25 verb mentions.
  Write set: under `dadaia_workspace/public/` — `scaffold/releases/AGENTS.md`,
  `templates/specs-AGENTS.md`, `data/{AGENTS.md,CONTEXT-MAP.md}`, `entities/behavior-map.json`,
  `CONSUMER_VALIDATION_RECIPE.md`, the skill files named above; plus
  `specs/ADRs/decisions.jsonl`, `specs/memory/ARCHITECTURE.md`,
  `specs/memory/product/sdd/sdd-bug-backlog-governance.md`,
  `specs/memory/product/platform/pypi-distribution.md`, `specs/releases/AGENTS.md`, `AGENTS.md`,
  `tests/contract/{test_every_block_carries_a_fix,test_slop_ratchets}.py`.

- [ ] T-047-92 — FR3: closure.
  `CHANGELOG.md` gains a "Candidate 10" section — the LAST hand-written section in this file,
  stated as such in the text: release-please owns everything written above it from the first
  release PR on. `_RELEASE.json` gains the closure `log` entry through `release.py phase CLOSURE
  --sha <sha>` (and `--pr <n>` once the release PR exists) naming the residue no test can cover:
  the first release PR observed proposing 0.4.7, emitting `release: published`, firing
  `release.yml`. The live instance is
  re-projected (`public stage` → `public install` → `public doctor` exit 0,
  `dadaia doctor --specs-dir repos/dadaia-workspace/specs` exit 0) so the instance runs the law
  T-047-91 rewrote; `docs/distribution.md` and `docs/cli.md` are re-derived with fresh
  `derived-from` hashes. No `rc-archive` runs at the gate — continue = the next candidate's
  `release.py new` overwrites the trio at the root; promote = the operator merges the release PR. The memory pass and the review verdict are the PM's.
  Seam: the live instance — proof the library change is real, never hand-edited.
  RED: `tests/contract/test_slop_ratchets.py` (V32/V33/V34/V35/V36 green at their new lower pins)
  plus the full `dadaia ci preflight` and
  `tests/contract/test_docs_derived_from_memory.py` (the two re-derived pages' hashes match their
  atoms); the closure is refused while `dadaia doctor` exits non-zero.
  Write set: `CHANGELOG.md`, `specs/releases/0.4.7/_RELEASE.json`, `docs/distribution.md`,
  `docs/cli.md`.
