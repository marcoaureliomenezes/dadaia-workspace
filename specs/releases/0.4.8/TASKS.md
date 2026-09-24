# TASKS — Release: 0.4.8

**Status:** Approved
**Owner:** dd-software-engineer

Paths under `dadaia_workspace/` abbreviated `dw/`. Tasks in one parallel group (PLAN §4) have disjoint write sets.

## Candidate 1 — onboarding in three levels

- [-] **T-048-01 — RED acceptance: the onboarding journey.**
  `tests/e2e/test_onboarding_journey.py`: builds the wheel with a `+e2e` local version, drives `uvx --from <wheel>`
  over file:// bare repos through the six AC8.1 scenarios; after every level asserts doctor 0 errors and user HEAD ==
  remote (AC8.2). Each level `xfail(strict=True, reason="T-048-nn")` naming the task that flips it.
  `RED:` collected, every scenario xfails for the named reason.
  `Write set:` `tests/e2e/test_onboarding_journey.py`
  `blocked by:` — · `group:` P1 · `delivers:` FR8 (RED)

- [-] **T-048-02 — Demolish alive's specs side effect.**
  Delete `dw/core/specs_backup.py` and its tests; remove from `SpecContextService.alive` the specs scaffold, the
  "run specs upgrade" hint and the `chore(scaffold)` commit; `alive` installs the pre-push hook in every repo.
  `RED:` alive on a DEAD context writes no specs, commits nothing, leaves the hook installed.
  `Write set:` `dw/core/specs_backup.py`, `dw/features/spec_context/service.py`, `dw/cli/commands/context.py` (`alive`),
  `tests/unit/**` + `tests/integration/**` covering specs_backup/alive
  `blocked by:` — · `group:` P1 · `delivers:` AC3.7 (alive half), AC4.7, AC9.1 (part)

- [-] **T-048-03 — context create is one transactional step.**
  `create [<name>] --main-repo <url> [--associated-repo <url>]…`: clone (or adopt a matching `origin`), hook, ALIVE,
  bind; rollback of every dir it created on failure; one slug rule (AC3.2); fix line rebuilt from the parsed
  invocation (RV1); `--url`/`--associated-repos` removed. Move `install_git_hooks`/`slug_from_url` into
  `spec_context/service.py`, delete `dw/features/workspace/bootstrap.py`, re-import in `cli/commands/ci.py`;
  `init.py` keeps compiling via a direct `SpecContextService.create` call.
  `RED:` create → doctor 0 errors, porcelain clean; failed clone → no record, re-run succeeds; `--url` exits 2.
  `Write set:` `dw/features/spec_context/service.py`, `dw/cli/commands/context.py`, `dw/features/workspace/bootstrap.py`,
  `dw/cli/commands/ci.py`, `dw/cli/commands/init.py` (import only), tests for these
  `blocked by:` T-048-02 · `group:` P2 · `delivers:` FR3 AC3.1–3.6, 3.8; flips journey level-2 xfails

- [-] **T-048-04 — init: one plan object, quiet output, --repo delegates.**
  `InitPlan` filled by flags or TTY prompts (name, harness from `core/harness_registry.py`, main URL, associated until
  blank); non-TTY missing DIR/`--harness` → exit 2 + fix; ≤ 12 lines (asset count, absolute venv path, next step);
  `--repo` → `SpecContextService.create`; no temp re-packed wheel; ensurepip absence named.
  `RED:` pty vs flags produce equal trees; stdout ≤ 12 lines; `init --help` shows DIR optional.
  `Write set:` `dw/cli/commands/init.py`, `dw/features/workspace/service.py`, `dw/infrastructure/python_env.py`, tests
  `blocked by:` T-048-03 · `group:` P3 · `delivers:` FR1, AC9.1 (init listing)

- [-] **T-048-05 — specs init: level 3 with specs-bkp.**
  `canon` classifies dadaia (constitution with `specs_pattern_version` ≥ 6) vs foreign; `specs init --context <c>`
  (bound when omitted, none → exit 2): absent → scaffold; dadaia → `specs upgrade` path (v6 → v7 with law sections);
  foreign → TTY y/N or `--replace-foreign`, `git mv specs specs-bkp` (staged), scaffold; existing `specs-bkp/` → exit 1.
  Never commits; lists written paths. English constitution; ARCHITECTURE/QUALITY fixed sections. `doctor --fix` deletes nothing.
  `RED:` v6 fixture ends v7 + doctor 0 errors; foreign non-TTY exit 2 no write; bkp bytes identical; HEAD unchanged.
  `Write set:` `dw/cli/commands/specs.py`, `dw/features/specs/{canon,scaffolder}.py`, `dw/public/templates/specs-AGENTS.md`, tests
  `blocked by:` — · `group:` P1 · `delivers:` FR4 AC4.1–4.6; flips journey level-3 xfails

- [-] **T-048-06 — Re-init is the upgrade.**
  `init <existing ws>` compares venv version: newer → reinstall + `reconcile` + `upgraded A -> B`; equal →
  `already at A`, no write; older → exit 1 + `fix: uvx dadaia-workspace@A init <ws>`. `--harness` not required.
  `RED:` three version cases on a fake venv (no real venv built in tests).
  `Write set:` `dw/cli/commands/init.py`, `dw/infrastructure/python_env.py`, `dw/features/reconcile/service.py`, tests
  `blocked by:` T-048-04 · `group:` P3 · `delivers:` FR2 AC2.1–2.3; flips journey upgrade xfail

- [-] **T-048-07 — Derived onboarding status, one derivation, three callers.**
  New `dw/features/workspace/onboarding.py` `next_step(root)`; doctor emits it as one info finding (exit unaffected,
  R2); `init`, `context create`, SessionStart (`hooks/ctx_inject.py`) print the same text; `doctor --context <ghost>`
  exits 1 + `fix: .dadaia/.venv/bin/dadaia context list`, no specs check (R4); hook check scoped to the context (R5).
  `RED:` each level fixture yields its step; ghost exit 1; no state file written.
  `Write set:` `dw/features/workspace/onboarding.py`, `dw/cli/commands/{doctor,init,context}.py`,
  `dw/features/spec_context/doctor.py`, `dw/hooks/ctx_inject.py`, tests
  `blocked by:` T-048-03, T-048-05, T-048-06 · `group:` P4 · `delivers:` FR6 AC6.1–6.3, AC3.7 (doctor half)

- [-] **T-048-08 — First pass in dd-audit-project.**
  "First pass" section: worklist = `memory.py drift` from the first commit + `audits_histo.jsonl` stamp;
  `dd-product-engineer` fills ARCHITECTURE/QUALITY/atoms from code + `specs-bkp/`; done = worklist covered +
  `memory.py check` 0. Contract test on the skill text; drift-from-root exit 0 on a fixture repo. Reproject.
  `Write set:` `dw/public/skills/dd-audit-project/SKILL.md`, `dw/public/skills/dd-spec-navigator/scripts/_memory_drift.py`
  (only if drift-from-root fails), `tests/contract/test_audit_first_pass.py`
  `blocked by:` — · `group:` P1 · `delivers:` FR5

- [-] **T-048-09 — Law and skills speak three levels.**
  `public/data/AGENTS.md` ≤ 5-bullet onboarding section; `public/data/dadaia-AGENTS.md` frozen-surface line amended per
  ADR 0027; `dd-cli-library` levels 1–2 procedure (new create shape); `dd-gitflow-default` consumer versioning rule;
  PyPI+1 rule moved to `AGENTS.md` (repo root); `CONTEXT.md` gains §4 terms; re-record behavior-map/CONTEXT-MAP hashes;
  `public stage`/`install`/`doctor` exit 0.
  `Write set:` `dw/public/data/{AGENTS.md,dadaia-AGENTS.md,CONTEXT-MAP.md}`, `dw/public/entities/behavior-map.json`,
  `dw/public/skills/{dd-cli-library,dd-gitflow-default}/**`, `AGENTS.md`, `CONTEXT.md`
  `blocked by:` T-048-07 · `group:` P5 · `delivers:` AC6.5, AC7.2

- [ ] **T-048-10 — Docs and the fix-line contract.**
  `docs/quickstart.md` one shell block (REPO_URL only); `README.md`, `docs/getting-started.md`, `docs/cli.md`,
  `llms.txt` describe the three levels with `.dadaia/.venv/bin/dadaia`; offline claim removed. Contract test: every
  shipped `fix:` literal and doc CLI line uses the venv path (uvx init lines excepted); no "repos catalog" text.
  `Write set:` `docs/**`, `README.md`, `llms.txt`, `tests/contract/test_onboarding_text.py`, `fix:` literals in `dw/cli/**`
  not held by an open task
  `blocked by:` T-048-07 · `group:` P5 · `delivers:` AC2.4, AC6.4, AC7.1 (text)

- [ ] **T-048-11 — Journey green in CI and release.**
  Flip remaining xfails; journey runs the quickstart block verbatim (AC7.1); `ci.yml` provisions uv for `e2e-python`;
  `release.yml` runs the journey before publish and the greenfield scenario from PyPI after it; re-run the audit
  script on the new CLI (≥ 90/100, recorded in `_RELEASE.json` log).
  `Write set:` `tests/e2e/test_onboarding_journey.py`, `.github/workflows/{ci.yml,release.yml}`,
  `tests/contract/test_ci_workflow_hygiene.py`
  `blocked by:` T-048-01…T-048-10 · `group:` P6 · `delivers:` FR8 AC8.1–8.3, §6 gate

Closure (dd-product-engineer, not a task): AC7.3 atoms, AC9.3 net-diff measurement, CONTEXT/memory check.
