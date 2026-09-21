# SPEC — Release: 0.4.7

**Status:** Approved
**Release ID:** 0.4.7
**Owner:** dd-project-manager
**Opened:** 2026-09-21
**Origin:** backlog:release-please-semantics
**Consumes:** release-please-semantics

---

## 1. Problem and context

Candidate 10 — "the release is a release PR" — is the last entry of the 2026-09-18..20 grill
(Q6 A: adopt release-please in the LAST candidate of the cycle so the plane is not changed in
flight; Q19 A: no event-driven audit). ADR 0021 was accepted on 2026-09-21 (operator ruling, D2); ADR 0005, 0006, 0008, 0009 and
0014 stay `accepted` until FR3 deletes their 15 live citations and flips them to `superseded`
in the same commit (`ADR-SUPERSEDED-CITATION` errors on any citation of a superseded record).

Measured on the candidate 9 closure (449c4267):

- **The version is minted by hand.** `pyproject.toml` `version` is bumped in a commit; the
  release workflow's `check` job compares it with the existing `v*` tags and publishes when the
  number is new; the tag is created by the publish job; `CHANGELOG.md` (119 KB) is hand-written
  per candidate. `SPEC-DOC-045` requires pyproject to equal the live release id.
- **Candidates archive by copying.** `release.py rc-archive` moves the closed trio to `rc-N/`
  (nine of them under `0.4.7/`), `release.py fold` reconciles, `release.py archive` moves the
  whole release under `_archive/<id>/` at promote; `RELEASE-TREE-*` doctor rules police the
  layout; `_release_rc.py`, `_release_fold.py`, `_release_fold_plan.py`, `_release_archive.py`
  are four of the twelve release scripts (1,381 lines under V36).
- **The promote decision is a manual approve** on the `release-gate` environment inside the
  same workflow run that publishes; nothing reviews the version or the notes before the tag.

## 2. Objective

One candidate, one CLOSURE: release-please owns the version (Conventional Commits), the
CHANGELOG and the tag through a long-lived release PR on `main`; the publish workflow fires on
the tag release-please creates; the trio per candidate stays at `specs/releases/<id>/`, the
closed candidate's trio is overwritten by the next candidate's, and git is the archive — `rc-N/`,
`rc-archive`, `fold` and `archive` retire with their doctor rules and scripts; promote = merging
the release PR; ADR 0006, 0008, 0009 and 0014 are marked superseded by 0021.

## 3. Scope (candidate 10)

### FR1 — release-please owns version, CHANGELOG and tag

- `.github/workflows/release-please.yml` on `push` to `main`: `googleapis/release-please-action`
  (pinned by sha), `release-type: python`, config + manifest files at the repository root
  (`.release-please-manifest.json` carrying the current version, `release-please-config.json`
  with `changelog-sections` for `feat|fix|refactor|docs|ci|test|chore`, `include-component-in-tag:
  false`, tag `v<version>`). The action maintains one release PR `chore(main): release <version>`
  that bumps `pyproject.toml` and prepends the generated section to `CHANGELOG.md`.
- `.github/workflows/release.yml` triggers on `release: published` (the event release-please
  emits on merge) instead of a pushed version bump: the `check` job that compares pyproject to
  tags dies; `publish` no longer creates the tag; `approve` (the `release-gate` environment)
  stays as the second key before the upload; `smoke-test` and `publish-skills-repo` stay.
- The hand-written CHANGELOG stops at 0.4.7's section: everything above `## [0.4.7]` is
  release-please's from the first release PR; nothing below is rewritten.
- **AC1.1** `tests/contract/test_ci_workflow_hygiene.py`: the release-please workflow exists,
  is sha-pinned, and `release.yml` has no version-vs-tag comparison and no `git tag` step;
  `tests/contract/test_release_semver_canon.py` (ADR 0021 measured_by) asserts the manifest
  version equals `pyproject.toml` version.

### FR2 — one directory per release id, no rc-N, git is the archive

- `release.py rc-archive`, `release.py fold` and `release.py archive` retire; `_release_rc.py`,
  `_release_fold.py`, `_release_fold_plan.py`, `_release_archive.py` are deleted; the
  `release-state-v1` schema loses `rc` and `implemented.rc`; a closed candidate's trio is
  overwritten by the next candidate's `release.py new`-seeded SPEC (the closed trio lives in git
  at the CLOSURE commit, named in the `_RELEASE.json` log).
- `specs/releases/0.4.7/rc-1..rc-9` and `specs/releases/_archive/**` stay as they are (history
  is never rewritten) but no new `rc-N/` or `_archive/<id>/` is ever created; the
  `RELEASE-TREE-ARCHIVE-*` and rc-layout rules in `features/specs/release_tree.py` and
  `doctor_release.py` become read-only tolerance of the existing dirs, then die with the last
  candidate that references them; `SPEC-DOC-045` dies (release-please owns the number).
- Promote = the operator merges the release PR; `release.py phase CLOSURE` on the last candidate
  plus the merged release PR number recorded in the `_RELEASE.json` log is the whole ceremony;
  the release directory id is the version release-please minted (renamed once at promote if the
  floor id and the minted version differ — D9).
- **AC2.1** `dadaia help tree` unchanged (no verb enters or leaves — these are scripts);
  `tests/contract/test_public_scripts_thin_wrapper.py` and V36 re-pinned DOWN (36 → 32 files);
  `tests/contract/test_release_state_schema.py` closes the schema without `rc`;
  `release.py check` passes on this repository's live state.

### FR3 — law, skills and memory follow

- `specs/releases/AGENTS.md` and `public/scaffold/releases/AGENTS.md`, `dd-release-definition`
  and `dd-release-implementation` `SKILL.md`, and `CONSUMER_VALIDATION_RECIPE.md` stop naming
  `rc-archive`/`fold`/`archive`; the root map's flow section names the release PR as promote;
  ADR 0005, 0006, 0008, 0009, 0014 → `status: superseded` in `decisions.jsonl`, in the same commit
  that deletes their last citation (`ADR-SUPERSEDED-CITATION`).
- Memory pass: `sdd-bug-backlog-governance` (the release state document, promote), 
  `pypi-distribution` (pipeline, one version axis), `agent-orchestration` if it names the verbs;
  docs re-derived; CHANGELOG "Candidate 10" is the LAST hand-written section.
- **AC3.1** grep for `rc-archive|release.py fold|release.py archive|rc-N` under `public/` and
  `specs/memory/` returns nothing; every `fix:` names an existing verb/script; `dadaia doctor`
  exit 0 on the live instance; CI green except the by-design red `security-review` (D1).

## 4. Out of scope

- Event-driven audit (Q19 A rejected); any change to bugs, backlog, audit or memory scripts.
- Rewriting `_archive/**` or `rc-1..rc-9`.
- The operator acts of candidate 9 (D3–D6) and the launch itself.

## 5. Decisions and constraints

- D2 done 2026-09-21: ADR 0021 accepted (`docs(adr): accept 0021-release-please-semantics`); the
  superseded flips land in FR3 with the citation deletions.
- D8 (operator): `release.yml` trigger — `release: published` (release-please's event) is the
  proposed default; `push: tags: v*` is the alternative.
- D9 (operator): the release directory id when release-please mints a minor instead of the
  floor patch — rename at promote (proposed) or keep the floor id and record the minted version
  in the log.
- D1 stays: `CLAUDE_API_KEY` + required check.
- ADR 0018: no verb enters; the scripts shrink (four files die).

## 6. Traceability

| Requirement | Tasks |
|---|---|
| FR1 | T-047-87, T-047-88 |
| FR2 | T-047-89, T-047-90 |
| FR3 | T-047-91, T-047-92 |
