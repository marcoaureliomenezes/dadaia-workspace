# TASKS — Release: 0.4.7

**Status:** Approved
**Release ID:** 0.4.7
**Owner:** dd-software-engineer

---

## Candidate 10 — the release is a release PR

- [x] T-047-87 — FR1: release-please owns version, CHANGELOG and tag.
  New `.github/workflows/release-please.yml` on `push: branches: [main]` plus
  `workflow_dispatch`, `permissions: contents: write, pull-requests: write`, one job, one step:
  `googleapis/release-please-action@45996ed1f6d02564a971a2fa1b5860e934307cf7  # v5.0.0` with
  `config-file: release-please-config.json`, `manifest-file: .release-please-manifest.json`
  and `id: release-please` (its `release_created`/`tag_name` outputs are T-047-88's gate) —
  **no `release-type:` input**: with a config file present it switches the action out of manifest
  mode, so `"release-type": "python"` lives inside the config's `packages["."]`.
  New `release-please-config.json` at the root: `packages: {".": {"release-type": "python",
  "changelog-path": "CHANGELOG.md"}}`, `"include-component-in-tag": false`,
  `"bump-minor-pre-major": true`, `"bump-patch-for-minor-pre-major": true` (pre-1.0: `feat` →
  patch, BREAKING → minor — what makes the first PR propose 0.4.7, not 0.5.0),
  `changelog-sections` for `feat|fix|refactor|docs|ci|test|chore`. New
  `.release-please-manifest.json`: `{".": "0.4.6"}` — the LAST PUBLISHED version, its floor (PLAN D10: `pyproject.toml` follows in T-047-90 with `SPEC-DOC-045`'s death). No
  PAT and no second trigger: the publish jobs arrive in T-047-88 *inside this workflow*, because
  the `GITHUB_TOKEN` cannot start a downstream one.
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

- [x] T-047-88 — FR1: `release.yml` folds into `release-please.yml`; `release.yml` is deleted.
  PM ruling: ONE workflow, one trigger, same-workflow chaining (the action's documented
  pattern) — no PAT, no `release:` event, no `push: tags`. Every `release.yml` job but `check`
  moves verbatim into `release-please.yml` under
  `if: needs.release-please.outputs.release_created == 'true'`, each `needs:` reaching the
  `release-please` job; `release.yml` is then deleted. The `check` job — the pyproject-vs-tags
  comparison and its `version`/`skip` outputs — dies with it, and every
  `if: needs.check.outputs.skip == 'false'` guard with them; the version every job interpolates
  becomes `needs.release-please.outputs.tag_name` less its `v` (one `id: version` step in
  `build`, exposed as a job output) so artifact name, `approve` message, `pip install` line and
  skills-repo subject read one source. `publish`'s `Create GitHub release tag` step dies — the
  action created the tag. `approve` keeps `environment: release-gate`, `publish` its OIDC
  publishing, `smoke-test` and `publish-skills-repo` their bodies. `CHANGELOG.md` gains
  release-please's header above `## [0.4.7]`; nothing at or below it is touched, ever.
  Seam: `release_created` — one boolean decides publication; the workflow no longer decides.
  RED: `test_ci_workflow_hygiene.py` — exactly ONE workflow carries the release-please action;
  `release.yml` does not exist; no workflow listens to `release:` or `push.tags`; every
  publish-side job `needs` the `release-please` job and is gated on `release_created == 'true'`;
  no step text contains `git ls-remote --tags` or `git tag `; `approve` carries
  `environment: release-gate` and no `needs:` names an undefined job. Fails today on all clauses.
  Write set: `.github/workflows/release-please.yml`, deletion of `.github/workflows/release.yml`,
  `CHANGELOG.md`, `tests/contract/test_ci_workflow_hygiene.py`.

- [x] T-047-89 — FR2: four scripts, two subcommands and the schema's `rc` die.
  Delete `_release_{rc,fold,fold_plan,archive}.py` (72+87+101+144 lines) under
  `dd-release-implementation/scripts/`; `release.py` loses the
  `rc-archive`, `fold` and `archive` `_HELP` entries, their imports and argument blocks —
  the roster becomes `new | phase | check`. `_release_schema.py` loses `RC_DIR_RE` and
  `rc_numbers()`; `release-state-v1.schema.json` loses the top-level `rc` and `implemented.rc`
  and stays `additionalProperties: false`, so an old document carrying `rc` is refused.
  `_release_phase.py` loses its `rc-archive` half and every `fix:` naming a dead verb
  (`_release_new.py:110` included) re-points at `release.py new` or `phase`. `_release_tree.py
  check` keeps tolerating `rc-N/` and `_archive/` read-only — no new branch enters it, the
  exclusion already lives in the name rule. No `--legacy` path (replace, don't layer).
  Seam: `release.py`'s subcommand table — three verbs, no aliases, no shims.
  RED: `test_release_state_schema.py` — the schema's property set equals `{schema_version,
  release_id, phase, origin, defined, implemented, shipped, log}`, no `rc` anywhere, a document
  carrying `rc` refused; `test_slop_ratchets.py` V36 re-pinned to ≤ 32 files / ≤ 3787 lines
  (measured after the deletion, whichever is lower); `test_public_scripts_thin_wrapper.py` roster
  unchanged for `release.py`, ceiling re-measured. Fails today: the schema still declares `rc`.
  Write set: the `dd-release-implementation/scripts/` survivors
  `{release,_release_phase,_release_schema,_release_new,_release_tree,_release_check}.py`
  plus deletion of `{_release_rc,_release_fold,_release_fold_plan,_release_archive}.py`;

  `public/schemas/releases/release-state-v1.schema.json`; `tests/contract/`
  `{test_release_state_schema,test_slop_ratchets,test_public_scripts_thin_wrapper}.py`.

- [x] T-047-90 — FR2: the doctor stops policing an archive nobody writes.
  `release_tree.py`: `_archive_issues()` and the `RELEASE-TREE-ARCHIVE-ID` /
  `RELEASE-TREE-ARCHIVE-UNSHIPPED` codes are deleted; the walk keeps listing `_archive/**` and
  validating those documents against the schema, phase and ts-order rules (history stays
  readable, it stops being ranked against a live id). In `doctor_release.py`, `SPEC-DOC-045`
  (pyproject == live release id) and its check method die, and `pyproject.toml`'s `version`
  returns to `0.4.6` — the published floor release-please bumps from (PLAN D10); one commit, so
  no intermediate tree is red.
  `release.py phase CLOSURE` gains ONE optional `--pr <n>`, recorded in the `log` note as the
  merged release PR — the number `archive --pr <n>` carried, moved from a deleted verb to a
  living one; `dadaia help tree` is byte-identical (ADR 0018: no verb enters).
  Seam: the `log` note — promote leaves a number, not a moved directory.
  RED: `test_release_tree_canon.py` — the two archive cases are REWRITTEN (not deleted) to assert
  the previously-refused fixtures now produce no issue, and `ARCHIVE-ID`/`ARCHIVE-UNSHIPPED`
  appear in no issue code anywhere; `test_doctor_pyproject_version.py` is deleted whole citing
  "feature removed", `SPEC-DOC-045` asserted absent from
  `test_every_block_carries_a_fix.py`'s roster; a new `phase CLOSURE --pr` case asserts the number
  lands in the `log` and that omitting the flag is still accepted; `test_release_semver_canon.py`
  tightens to manifest version == `pyproject.toml` version == `0.4.6` (D10). V32 (682), V33 (35) and the
  module ceiling (699/700) re-pinned DOWN to measured. `_release_histo.py` dies with its importers.
  Write set: `features/specs/{release_tree,doctor_release}.py`, `pyproject.toml`,
  `.release-please-manifest.json`,
  `dd-release-implementation/scripts/{release,_release_phase}.py`, `tests/contract/`
  `{test_release_tree_canon,test_release_semver_canon,test_every_block_carries_a_fix,
  test_slop_ratchets}.py`, deletion of `test_doctor_pyproject_version.py` and
  `_release_histo.py`, `specs/memory/product/platform/workspace-doctor.md`.

- [x] T-047-91 — FR3: the law stops naming verbs that no longer exist.
  Every `rc-archive` / `release.py fold` / `release.py archive` / `rc-N` mention leaves
  `dadaia_workspace/public/`: `scaffold/releases/AGENTS.md` (lines 7, 10, 12, 16, 25 — one live
  release directory per version, the trio overwritten by the next candidate, promote = merging
  the release PR), `dd-release-implementation/{SKILL,RC-FLOW,RELEASE-EVENTS}.md`,
  `dd-release-definition/SKILL.md`, `dd-gitflow-default/SKILL.md` (steps 9/11 and the `rc-N`
  branch line), `dd-spec-navigator/SKILL.md` (step 1 and the glossary row),
  `templates/specs-AGENTS.md`, `data/{AGENTS,CONTEXT-MAP}.md` and the root map's flow line;
  `specs/releases/AGENTS.md` follows by re-projection, never by hand. ADR 0005, 0006,
  0008, 0009 and 0014 flip to `"status": "superseded"` in `specs/ADRs/decisions.jsonl` **in this
  same commit** — `ADR-SUPERSEDED-CITATION` errors on any surviving citation, so the flip and the
  last deletion are atomic. `sdd-bug-backlog-governance.md` (lines 44, 46, 50),
  `pypi-distribution`, `ARCHITECTURE.md` line 126, `CONSUMER_VALIDATION_RECIPE.md` and the
  behavior map re-recorded. V35 falls, never rises: the deleted prose is the payment.
  Seam: `decisions.jsonl`'s `status` — one flip retires five records and their vocabulary.
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
  stated as such: release-please owns everything above it from the first release PR on. `_RELEASE.json` gains the closure `log` entry through `release.py phase CLOSURE
  --sha <sha>` (and `--pr <n>` once the release PR exists) naming the residue no test can cover:
  the first release PR observed proposing 0.4.7 and its merge setting `release_created` true. The live instance is
  re-projected (`public stage` → `public install` → `public doctor` exit 0, `dadaia doctor
  --specs-dir repos/dadaia-workspace/specs` exit 0) so the instance runs T-047-91's law; `docs/distribution.md` and `docs/cli.md` are re-derived with fresh
  `derived-from` hashes. No `rc-archive` runs at the gate — continue = the next candidate's
  `release.py new` overwrites the trio at the root; promote = the operator merges the release PR. The memory pass and the review verdict are the PM's.
  Seam: the live instance — proof the library change is real, not hand-edited.
  RED: `test_slop_ratchets.py` (V32/V33/V34/V35/V36 green at their new lower pins), the full
  `dadaia ci preflight`, and `test_docs_derived_from_memory.py` (the two re-derived pages' hashes
  match their atoms); the closure is refused while `dadaia doctor` exits non-zero.
  Write set: `CHANGELOG.md`, `specs/releases/0.4.7/_RELEASE.json`, `docs/distribution.md`,
  `docs/cli.md`.
