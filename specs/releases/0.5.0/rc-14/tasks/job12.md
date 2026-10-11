# Job 12 — release skill: one grammar owner, one git runner, kernel owners adopted, the D-F functions below D (FR14, FR11)

**Status:** Draft

Wave 3, after Job 1 (which already rebuilt the state reader, the DAG decider and the next-candidate decider here) and Job 3 (the package now reads this skill's grammars). One skill, one job.

- **Grammar owners (AC14.4).** `_release_schema` owns the task-id, semver, candidate, tag and status-line grammars and reads the phase list from `release-state-v1`'s enum (`_release_schema.py:24,26,29`; `_release_phase.py:32,89`); the sha pattern (`:32`) reads `_git`'s object-id pattern (a log abbreviation is a prefix of it, named in the commit body). `_release_tree.py:298` reads the owner's tag grammar.
- **Git (AC11.2).** `_release_schema.py:119,123` call `_git.git`; a release test with `GIT_DIR` set to another repo is the RED case of T1.
- **Kernel owners (AC11.4).** `_release_store.py` loses `Refusal`, `serialize` and the commit loop; `_release_check.py` loses `finding()` (the copy without a code), `histo_findings` and its line parser; the clock helper (`_release_schema.py:46`) is `_clock`.
- **D to F functions (radon at `99a522b3d`).** `release.py:_ship` D28, `_release_check._log_errors` D22, `_release_tree._origin_findings` D28, `_release_tree._directory_findings` D23, `_release_schema.current_plan_jobs` D23; `dag_errors` D25 and `set_phase` D21 belong to Job 1's rebuild, which this job re-measures. Each is split into small named steps below rank D by a behaviour-preserving refactor: `test_release__characterization.py` and the existing release suites are the net, so no RED case except T1.
- Test-side first: T1. Then T2 to T6 in parallel (disjoint `W:`).
- Sweep lines in commit bodies: `git grep -n 'class Refusal\|def serialize\|def finding\|def histo_findings\|def commit' -- dadaia_workspace/public/skills/dd-release-implementation` (5 before, 0 after); `git grep -n 'subprocess' -- dadaia_workspace/public/skills/dd-release-implementation` (calls outside `_git`: 0 after); `radon cc -n D -s dadaia_workspace/public/skills/dd-release-implementation` (7 before, 0 after).
- Pre-review checklist: one reader per rule; the only cross-skill edge is the kernel's; sweep lines above; no platform fact; net production lines ≤ 0 (est. −90).

Tasks: 6 (1 jr, 5 sr). `who` names the dispatched role (`dd-release-definition` §5).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J12.T1 | sr | AC11.2 | `tests/public/skills/dd_release_implementation/scripts/test__release_schema.py` | RED, unit: with `GIT_DIR` and `GIT_WORK_TREE` pointing at another repo, the release skill's git reads (`_release_schema` shallow-clone check and its log reads) answer for the repo given. Owner `test__release_schema.py`; a Job 1 case in the same file stays |
| J12.T2 | sr | AC11.2, AC14.4, AC11.4 | `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_schema.py` | git through `_git`; the grammars as the intro says; `current_plan_jobs` (D23) split below D; the clock. Owner T1 and the existing suites. After T1. Fix commit of the git-env bug (release runner); Phase 0 block `caused_by: none`, `rebuild: the git runner` |
| J12.T3 | jr | AC11.4 | `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_store.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_new.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_phase.py` | adopt `_refusal`, `_jsonl.serialize` and `_commit`; delete the copies; `_release_phase` reads the phase list from the schema. Existing suites unedited |
| J12.T4 | sr | AC11.4 | `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_check.py` | `finding()` and `histo_findings` come from `_findings`, the line parser from `_jsonl`; `_log_errors` (D22) split below D. Existing suites unedited |
| J12.T5 | sr | AC14.4 | `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_tree.py` | `_origin_findings` (D28) and `_directory_findings` (D23) split below D into named steps; the tag grammar from the owner. Existing suites unedited |
| J12.T6 | sr | AC11.4 | `dadaia_workspace/public/skills/dd-release-implementation/scripts/release.py` | `_ship` (D28) split below D (the open-bug refusal, the authorization match and the ledger write become three named steps). Owner `test_release__release_script.py` and the characterization test, unedited. Also deletes the `cast` in `release.py` (`a9108723f`) that existed only because mypy could not follow the `sys.path` edges |
