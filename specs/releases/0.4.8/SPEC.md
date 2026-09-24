# SPEC — Release: 0.4.8

**Status:** Approved
**Release ID:** 0.4.8
**Owner:** dd-product-engineer
**Opened:** 2026-09-24
**Origin:** operator-demand

---

## 1. Problem and context

Candidate 1 — "onboarding in three levels". Operator demand 2026-09-23 (full onboarding audit: install ->
first Spec Context Project -> first canonical specs) and order 2026-09-24: "Faça, trabalhe, conserte o
processo de onboarding, para ontem." Grill closed 2026-09-23, operator: "sigo recomendações" (D1–D13 below).

- Live audit (docker uv, file:// repos): PyPI 0.4.7 scored 24/100; after the 0.4.7 Arm B batch (B1–B8 +
  3 rework bugs, PR #270) the wheel at 48ee108f scores 45/100. Evidence: `.dadaia/tmp/onboarding-audit/20260924/`
  (`run.sh`, `transcript.txt`).
- What remains is design, not contract: onboarding is `init` -> `context create` -> `context alive` -> `bind`
  -> an implicit specs scaffold inside `alive` that auto-commits on the user's `main`, detects nothing,
  stamps foreign trees v7 and leaves v6 trees in a dead end; no step tells the user what comes next.
- Live residuals R1–R6 (transcript): R1 `init` prints ~150 asset lines; R2 `doctor` silent at zero contexts;
  R3 a failed create/alive leaves a DEAD context owning the slug; R4 `doctor --context <ghost>` falls back to
  `<workspace>/specs`; R5 `alive` never installs the pre-push hook (HOOKS-DRIFT-1 on arrival) and
  `doctor --context X` reports other contexts' hooks; R6 v6 tree: `alive` says "run specs upgrade", upgrade
  says "no-op", doctor still errors.
- Reviewer residuals of the last review: RV1 the `create` refusal `fix:` for a URL-less main repo drops the
  associated repos; RV2 the `context-management` atom names only one fix variant.
- Bug history of the surface (ledger): `python_env.py` 10 bugs, `cli/commands/context.py` 8,
  `spec_context/service.py` 7, `init.py` 3, `scaffolder` 3, `doctor_structural.py` 3 — the create/alive
  split and the scaffold-inside-alive are the recurring sites; this candidate removes them, not patches them.

## 2. Objective

One `uvx` line takes a user from nothing to a bound, hook-guarded Spec Context Project; one verb gives its
main repo a canonical specs tree without destroying or committing anything; every step prints the next one;
a CI journey from a built wheel proves it — and the onboarding code shrinks.

## 3. Decided design (grill 2026-09-23, D1–D13)

- D1 `init [DIR] [--harness] [--repo …]`: missing fields prompted only on a TTY; non-TTY -> exit 2 + `fix:`;
  a prompted name -> `./<name>`; flags and prompts fill ONE plan object.
- D2 every doc and `fix:` line uses `.dadaia/.venv/bin/dadaia`; `init` prints the absolute venv path.
- D3 `uvx dadaia-workspace@X init <existing ws>` IS the upgrade (venv version compared, reinstall, reconcile);
  the "works offline" claim is removed.
- D4 the workspace venv stays stdlib venv + pip (no uv as installer).
- D5 `context create [<name>] --main-repo <url> [--associated-repo <url>]…` clones + installs the hook +
  ALIVE + binds in one step; default name = main-repo slug; an existing `repos/<slug>` is adopted; NO specs
  writing; `init --repo` delegates to it.
- D6 no auto-commit into the user's repo; written files stay in the worktree, listed on stdout.
- D7 a dadaia specs tree = `specs/constitution.md` carrying `specs_pattern_version`; anything else is foreign.
- D8 level 3 = `specs init --context <c>`: dadaia -> compliance+repair (`specs upgrade`); foreign -> confirm
  (or `--replace-foreign`) -> `git mv specs specs-bkp` -> scaffold; `doctor --fix` never deletes.
- D9 a dadaia tree below v6 is treated as foreign; no migration chain reopened.
- D10 first audit: deterministic worklist (`memory.py drift` uncovered units + `audits_histo` stamp) +
  `dd-audit-project` "first pass" where `dd-product-engineer` fills memory from code + `specs-bkp/`; no new skill.
- D11 onboarding status is DERIVED from disk, no state file; `doctor` shows it; `init`, `context create` and
  SessionStart print the same next step.
- D12 root `AGENTS.md` gains a 4–5 bullet onboarding section; procedure in `dd-cli-library` (levels 1–2) and
  `dd-audit-project` (level 3); the quickstart is doc-as-test.
- D13 contract breaks were fixed as Arm B on 0.4.7; this candidate is the Arm A redesign.
- Answered by inspection: a consumer's first release is `0.1.0` with no tag, else last tag + 1 patch; the
  "last PyPI + 1" rule is this library's own and moves to `repos/dadaia-workspace/AGENTS.md`; associated repos
  are prompted until a blank line; schema key `repo_slug` stays.

**ADR candidates** (appended `proposed` in `specs/ADRs/decisions.jsonl`, shape 2, before implementation;
the operator flips them): A1 = D5, amending the `.dadaia/AGENTS.md` line "the context surface is frozen";
A2 = D11, derived onboarding status, no state file; A3 = D8+D9, foreign or <v6 specs -> `specs-bkp`;
A4 = D6, no auto-commit into the user's repo; A5 = D3, re-init is the upgrade.

## 4. Terms (enter `CONTEXT.md` with the implementation)

- **Onboarding level** — 1 workspace (`init`), 2 Spec Context Project (`context create`), 3 canonical specs
  + first audit (`specs init`, first pass). _Avoid_: phase (collides with `_RELEASE.json` `phase`).
- **Onboarding status** — the next unmet level, derived from disk on every read; never stored.
- **Dadaia specs tree** / **foreign specs tree** — per D7; a dadaia tree below v6 counts as foreign.
- **specs-bkp** — the foreign tree renamed in place inside the main repo, tracked by git; the only backup.
- **First pass** — the first `dd-audit-project` run over a context, stamped in `audits_histo.jsonl`.
- Specs scaffold here is the specs-tree renderer, never the SCAFFOLD test tier.

## 5. Functional requirements

`DADAIA` = `.dadaia/.venv/bin/dadaia`; `UVX` = `uvx --from <wheel|dadaia-workspace==X> dadaia-workspace`.
Every refusal below exits non-zero with exactly one `fix:` line whose command is runnable as printed.

### FR1 — Level 1: workspace (D1, D2, D4, R1)

- AC1.1 `UVX init ws --harness claude` on a non-TTY exits 0; stdout ≤ 12 lines: one asset-count line (no
  per-path listing), the absolute path of `ws/.dadaia/.venv/bin/dadaia`, and the onboarding next step (FR6).
- AC1.2 `UVX init` with no DIR on a non-TTY exits 2 with `fix: uvx dadaia-workspace init <dir> --harness <h>`;
  missing `--harness` on a non-TTY exits 2 likewise; a missing `--repo` is never an error.
- AC1.3 On a TTY, prompts ask name (-> `./<name>`), harness, main-repo URL (blank = none), then associated
  URLs until a blank line; the resulting tree + `spec_contexts.json` (timestamps aside) equal the flag
  invocation's — one plan object, one code path (test via pty).
- AC1.4 `init --help` shows `DIR` and `--harness` as optional; no `init` output names a bare `dadaia …` verb.
- AC1.5 `init --repo <url> [--associated-repo <url>]…` produces exactly what FR3's `context create` produces.
- AC1.6 `init` leaves no re-packed wheel in the system temp dir; a base Python without `ensurepip` is reported
  as missing `ensurepip`/`venv`, not as noexec.
- AC1.7 `init` never writes outside the workspace except the documented kimi-code user config (unchanged).

### FR2 — Upgrade: re-init is the upgrade (D3)

- AC2.1 On a workspace whose venv carries version A, `UVX` at version B > A running `init <ws>` (no
  `--harness` needed) reinstalls B into the venv, runs reconcile, prints `upgraded A -> B`, exits 0;
  `<ws>/.dadaia/.venv/bin/dadaia --version` prints B; `DADAIA doctor` exits 0.
- AC2.2 Same version: exits 0, prints `already at A`, no file under the workspace changes.
- AC2.3 B < A: exits 1, no write, `fix: uvx dadaia-workspace@A init <ws>`.
- AC2.4 No README/doc/memory atom claims the install works offline.

### FR3 — Level 2: Spec Context Project (D5, D6, R3, R5, RV1)

- AC3.1 `DADAIA context create --main-repo <url> [--associated-repo <url>]…` clones main + associated repos
  under `repos/`, installs the pre-push hook in each, registers the context ALIVE, binds it, exits 0; name
  defaults to the main-repo slug; immediately after, `DADAIA doctor --context <name>` reports 0 errors.
- AC3.2 One slug rule for context name and repo slug: a URL basename `my.repo.git` derives `my-repo`
  (every char outside `[A-Za-z0-9_-]` -> `-`); no URL derivable into a valid slug reaches a refusal.
- AC3.3 `repos/<slug>` already holding a checkout whose `origin` equals the URL is adopted (no clone, hook
  installed); any other occupant -> exit 1, nothing registered.
- AC3.4 Transactional: any clone failure -> exit 1, no context record, every directory this call created
  under `repos/` removed; re-running the corrected command with the same slug succeeds (R3).
- AC3.5 A refusal's `fix:` line reproduces the full invocation, every `--associated-repo` included (RV1).
- AC3.6 `create` writes nothing inside any cloned repo but the hook; `git -C repos/<slug> status --porcelain`
  is empty and HEAD equals the remote's.
- AC3.7 `context alive <name>` (DEAD -> ALIVE, e.g. after `import`) clones, installs the hook, writes no
  specs, commits nothing (R5); `DADAIA doctor --context X` checks only X's repos' hooks (R5).
- AC3.8 `context create --url` and `--associated-repos` no longer exist (exit 2); no help, doc or memory
  text mentions a repos catalog.

### FR4 — Level 3: canonical specs (D6–D9, R6)

- AC4.1 `DADAIA specs init --context <c>` (bound context when omitted; none bound -> exit 2 + fix) on a main
  repo with no `specs/`: scaffolds the canon, exits 0, lists every written path on stdout, commits nothing
  (HEAD unchanged, paths untracked/modified in `git status`).
- AC4.2 Scaffolded `constitution.md` is English; `memory/ARCHITECTURE.md` carries `## Principles`,
  `## Tech Stack`, `## Structure` and `memory/QUALITY.md` `## Principles`, `## Test architecture`, `## Gates`;
  `DADAIA doctor --context <c>` reports 0 errors.
- AC4.3 Dadaia tree v6 or v7: delegates to `specs upgrade` — a v6 tree ends stamped v7 with its fixed law
  sections present, `doctor --context <c>` 0 errors (R6); a v7 tree is repaired in place, no data moved.
- AC4.4 Foreign tree (or dadaia < v6) on a non-TTY without `--replace-foreign`: exit 2, nothing written,
  `fix: … specs init --context <c> --replace-foreign`; on a TTY a y/N confirm, N = the same no-write exit.
- AC4.5 Confirmed/flagged foreign: `specs/` becomes `specs-bkp/` (tracked files renamed via `git mv`, staged
  not committed; every file byte-identical), then AC4.1 runs; an existing `specs-bkp/` -> exit 1, no write.
- AC4.6 `DADAIA doctor --fix` on any specs tree deletes no file (regression of B1 kept in the journey).
- AC4.7 `context alive`/`create` print no "run specs upgrade" hint; no verb names a backup outside git.

### FR5 — Level 3: first audit (D10)

- AC5.1 A context with no first-pass stamp in `audits/_archive/audits_histo.jsonl` has a deterministic
  worklist: the `memory.py drift` invocation named by the onboarding status lists every code unit no atom
  covers, from the repo's first commit, exit 0.
- AC5.2 `dd-audit-project` carries a "first pass" section: `dd-product-engineer` fills `ARCHITECTURE.md`,
  `QUALITY.md` and product atoms from code + `specs-bkp/`, then records the stamp; done = worklist covered and
  `memory.py check` exit 0. No new skill. Agentic — asserted by contract test on the skill text, not in CI
  (ADR 0025).

### FR6 — Guidance: derived onboarding status (D2, D11, D12, R2, R4)

- AC6.1 `DADAIA doctor` derives the next unmet level on every run and reports it as one info finding
  (exit code unaffected) with one `fix:` line: zero ALIVE contexts -> `context create`; an ALIVE context
  without a dadaia specs tree -> `specs init --context <c>`; no first-pass stamp -> the FR5 worklist command;
  complete -> no finding. Zero contexts no longer prints nothing (R2). No state file is written.
- AC6.2 `init`, `context create` and the SessionStart hook print the same next-step text as AC6.1 (one
  derivation, three callers); SessionStart at zero contexts no longer prints `[no bound context]` alone.
- AC6.3 `DADAIA doctor --context <ghost>` exits 1: `Error: Context 'ghost' not found.` +
  `fix: .dadaia/.venv/bin/dadaia context list`; no specs check runs (R4).
- AC6.4 Contract test: every shipped `fix:` line and doc command that invokes the CLI uses
  `.dadaia/.venv/bin/dadaia` (pre-venv `uvx dadaia-workspace init` lines excepted).
- AC6.5 Root map template gains a ≤ 5-bullet onboarding section; `dd-cli-library` carries the levels 1–2
  procedure; the `.dadaia/AGENTS.md` template's frozen-surface line is amended per A1.

### FR7 — Docs and memory (D12, RV2)

- AC7.1 `docs/quickstart.md`'s shell block runs verbatim in the E2E with only `REPO_URL` set; README,
  `getting-started`, `llms.txt` describe the same three levels and D2 paths.
- AC7.2 `dd-gitflow-default` states the consumer versioning rule; the PyPI+1 rule lives only in
  `repos/dadaia-workspace/AGENTS.md`.
- AC7.3 Closure memory pass rewrites `workspace-init`, `context-management` (every fix variant — RV2),
  `spec-context-project`, `specs-migration`, `workspace-doctor`, `pypi-distribution`; `memory.py check` exit 0.

### FR8 — E2E journey (T-G)

- AC8.1 `tests/e2e/test_onboarding_journey.py` drives `uvx --from <built wheel>` over file:// bare repos:
  greenfield; dadaia v6 specs; foreign specs (+ `doctor --fix` deletes nothing); second project with an
  associated repo; failed create then corrected retry; re-init upgrade from the previous PyPI version.
- AC8.2 After each level of each scenario `DADAIA doctor --context <c>` reports 0 errors, and the user repo's
  HEAD equals its remote's.
- AC8.3 Runs in CI on every PR (uv provided by the job) and in `release.yml` before publish; the post-publish
  smoke job runs the greenfield scenario from PyPI (`--repo` + `specs init` + doctor).

### FR9 — Simplification (operator standing rule)

- AC9.1 Deleted: `core/specs_backup.py` and its callers/tests; `alive`'s specs scaffold, upgrade hint and
  `chore(scaffold)` auto-commit; `init`'s per-asset listing; `create --url`/`--associated-repos`; the
  `.dadaia/tmp/specs-upgrade-backups/` usage; `features/workspace/bootstrap.py` reduced to a call into
  `context create` or removed.
- AC9.2 Onboarding needs 2 verbs where it needed 4 (`init --repo` + `specs init` vs `init`, `create`, `alive`,
  `bind` + implicit scaffold); no new verb, no new state file.
- AC9.3 Net production diff under `dadaia_workspace/` (Python, `public/` Markdown excluded) from the
  definition commit to closure is ≤ 0 lines; PLAN justifies every growth against replace-don't-layer.

## 6. Acceptance gate

- FR8 green in CI on the develop PR (every job), doctor 0 errors after each level of each scenario.
- The quickstart executed verbatim (AC7.1).
- The audit script re-run (scenarios updated to the new CLI) scores ≥ 90/100 on the rubric: level 1 20,
  level 2 20, level 3 20, guidance/agent 15, docs 10, upgrade 5, E2E 10.
- Live instance: `public stage` + `public install` + `DADAIA doctor` exit 0 after every library change.

## 7. Out of scope

- uv as the venv installer (D4); marketplaces; Windows `init` coverage beyond today's smoke; kimi-code
  user-level config; `context repo add` cloning; a migration chain for trees below v6 (D9).

## 8. Risks and dependencies

- The source wheel and the last PyPI release share `0.4.7` until release-please bumps: the E2E builds its
  wheel with a local version segment (`+e2e`) so AC2.1 observes a real version change.
- A1–A5 must be appended before implementation; A1 changes projected law — reproject in the same task.
- The first pass is agentic and never runs in CI (ADR 0025); only its worklist and skill text are tested.
- `.dadaia/tmp/` evidence is TTL-reaped; FR8 is the durable form of `run.sh`'s scenarios.

## 9. Traceability

| FR | Decisions / residuals | Task group |
|---|---|---|
| FR1 | D1 D2 D4 R1 | T-A |
| FR2 | D3 | T-A |
| FR3 | D5 D6 R3 R5 RV1 | T-B |
| FR4 | D6 D7 D8 D9 R6 | T-C |
| FR5 | D10 | T-E |
| FR6 | D2 D11 D12 R2 R4 | T-D, T-F |
| FR7 | D12 RV2 | T-F, closure |
| FR8 | acceptance gate | T-G |
| FR9 | standing rule | all |
