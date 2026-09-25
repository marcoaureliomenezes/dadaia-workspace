# SPEC — Release: 0.5.0

**Status:** Approved
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-09-25
**Origin:** operator-demand

---

## 1. Problem and context

Candidate 3 — "onboarding foundation: a derived state machine the agent loops on, a published first
project, and the project gitflow". Operator demand 2026-09-24 (verbatim):

> "não quero gambiarras altamente suscetíveis a bugs, quero uma jornada robusta e resiliente, com
> orientações claras ao agente para ele se auto-resolver... superfície de bugs deve ser minimizada...
> auto-recovery pelo agente"

> "usuários devem conseguir ver nosso gitflow básico... ter um default... customiza se quiser...
> constitution é para isso... gates determinísticos customizáveis... não provoque locks ou stop sem
> sentido fazendo agente parar de trabalhar e não ter para onde ir. Esse é o maior problema."

Grill rounds 1–3 (handoffs `2026-09-25T031500Z-main-thread-onboarding-foundation-grill`,
`2026-09-25T050500Z-main-thread-foundation-grill-r3`), every recommendation accepted. The law of this
candidate is ADRs 0033–0038, 0040, 0042–0046 (0039 docs belongs to candidate 4). As-is review (definition
step 2): `.dadaia/tmp/claude/20260925/inventory-c3-foundation-state-machine.md` and section A of
`inventory-c3-gitflow-and-c4-docs.md`; they become PLAN §1.

As-is, with its bug evidence (555 records, 0 open):

- Onboarding ends at level 3 with a stamp (`audits_histo`), never commits or pushes; a clean first pass
  could not be stamped (`audit-close-refuses-a-clean-audit`). SessionStart gained a second `next_step`
  call site to fix `session-start-bound-session-omits-onboarding-next-step`.
- Two spellings of the CLI (`DADAIA_BIN` in 10 files, `cli_path` in 2) and hand-built fix strings per
  call site: 9 bugs of one family closed 2026-09-24 (ADR 0045 context). FIXED-2 cites a bare `dadaia`
  the venv guard blocks; TREE-5 tells a consumer to copy a library path it does not have — a stall.
- `context baseline` births only an unborn repo on `feature/0.1.0`, with no `main`/`develop`; two bugs
  (`baseline-refuses-alive-scaffold-commit`, `context-baseline-rejects-official-scaffold-followup`)
  were patched by a convergent `has_commits` branch — a symptom patch.
- The pre-push gate refuses every `main`/`develop` push; its fix (`gh pr create --base develop`) fails
  while `develop` does not exist — a consumer's first PR has no target (a stall).
- Branch names are hard-coded in three regexes, the library CI and ~36 shipped-text lines: 8 bugs, each
  fix patching one literal site before the next broke.
- `init` and `context create` write a session record keyed on their own pid, which dies at once; the
  bind/session surface carries ~15 bugs.
- `ObjectSource.parents`, `branch_name_is_permitted`, `parse_push_refs` have no production caller.

## 2. Objective

One derived, ordered list of onboarding steps — each a real-state predicate and one fix line built by one
builder — that an agent loops on (run doctor, execute `fix:`, repeat) from an empty directory to a project
published on its principal, integration and work branches under a gitflow the project declares in its
constitution; no step can stall, and the touched features shrink.

## 3. Terms (enter `CONTEXT.md` with the implementation)

- **Onboarding step** — one entry of the ordered list: id, kind, a real-state predicate ("pending"), one
  fix line. Ids in order: `context`, `bind`, `specs` (3a), `first-pass` (3b), `publish` (3c).
  _Avoid_: stage, wizard step, onboarding state.
- **Step kind** — `command` (the fix line is a shell command) or `agent` (the fix line names a skill
  section and a pending list an agent works through). _Avoid_: type, mode.
- **Onboarding level** (amended) — 1 workspace, 2 context (steps `context`, `bind`), 3 specs (3a `specs`,
  3b `first-pass`, 3c `publish`); derived, never stored.
- **Next step** (amended) — the first pending onboarding step, printed identically by `doctor`, `init`,
  `context create` and SessionStart.
- **First pass** (amended) — level 3b; done when memory holds real content, never by a stamp.
- **Project publication** — level 3c: the first push of an onboarded project's specs, by
  `context baseline`. _Avoid_: publish step (the Publication boundary's _Avoid_), baseline (the pre-push
  published-history baseline).
- **Fix line** — the one runnable line a finding, refusal or step prints after `fix:`; every one naming
  the workspace CLI is built by `fix_line`. _Avoid_: hint, remedy text.
- **Project gitflow** — the `gitflow:` block of `specs/constitution.md` frontmatter naming three fixed
  roles: **principal branch** (deployed; default detected from `origin/HEAD`, else `main`),
  **integration branch** (default `develop`), **work branch** (`<work prefix><M.m.p>`, prefix default
  `feature/`). _Avoid_: branch policy (the gate's check), branching model.
- **Bootstrap birth** — a push creating the principal or integration branch that publishes no new
  object. _Avoid_: bootstrap push, first push.

## 4. Functional requirements

`CLI` = the absolute workspace CLI path `cli_path` returns. Files are library source; projections follow
by `public stage` + `public install`.

### FR1 — One onboarding derivation (ADR 0033)

- AC1.1 `features/workspace/onboarding.py` holds ONE ordered tuple of step definitions (id, kind,
  pending(state), fix(state)) in the §3 order; `next_step` returns the focus context's first pending step,
  else the first pending across ALIVE contexts, else `None`; `Step` carries `kind`.
- AC1.2 I1: every predicate reads real state (files, git, the session registry); writing
  `audits_histo.jsonl` changes no step (unit test).
- AC1.3 I3: a hypothesis property test over random real-state prefixes (tmp dirs, `file://` bare
  remotes) executes each pending command step's fix line and asserts that step is no longer pending;
  operator placeholders (`<clone-url>`, `<name>`) are the only tokens the test substitutes.
- AC1.4 I4: along every property run the printed step's index strictly increases; the loop ends within
  `len(steps)` command executions plus the agent steps.
- AC1.5 `doctor` (ONBOARDING info finding; `--json` carries `step` and `kind`), `init`, `context create`
  and SessionStart print the same `Step.text()`, which names the kind. SessionStart calls one helper for
  bound and unbound sessions; the second `next_step` call in `hooks/ctx_inject.py` `_emit_bootstrap` is
  gone; a hook test asserts both paths print doctor's text.
- AC1.6 The derivation issues no network call and reads no gitflow block (3c per FR4 is local).
- AC1.7 A `tests/contract/` census of the step list (id, kind, order) replaces the regex census
  `tests/contract/test_onboarding_text.py`.

### FR2 — One fix-line builder (ADR 0045; absorbs round-2 items)

- AC2.1 `core/cli_line.py` owns `cli_path(root)` (moved from `onboarding.py`) and
  `fix_line(root, *argv)`, joining with `shlex.join` on POSIX and `subprocess.list2cmdline` on Windows;
  a unit test pins both forms.
- AC2.2 `DADAIA_BIN` is deleted from `core/kernel_tunables.py`; every call site in the 9 importing
  modules (`features/specs/rules.py`, `features/spec_context/{service,doctor,gate_policy}.py`,
  `features/ci_preflight/service.py`, `cli/commands/{context,doctor}.py`,
  `infrastructure/ledger_scripts.py`, `hooks/venv_guard.py`) migrates in this candidate — no exception.
- AC2.3 FIXED-1/FIXED-2 (`doctor_memory.py`) and TREE-4/TREE-5 carry their remedy as a `fix_line`-built
  line; no finding description embeds a bare `dadaia` command.
- AC2.4 A missing scaffolded law file (`specs/AGENTS.md` or `specs/<area>/AGENTS.md`) is `fixable=True`:
  `CLI doctor --fix --context <ctx>` writes the shipped template (lossless); the copy-a-library-path prose
  is gone; a TREE-5 case `--fix` does not repair advertises no `doctor --fix` line.
  `tests/integration/test_doctor_fix_lines_clear_their_finding.py` covers both.
- AC2.5 An AST contract test fails when any module outside `core/cli_line.py` builds a fix line naming the
  workspace CLI other than through `fix_line` (a literal or f-string holding the venv CLI path or a bare
  `dadaia ` command).
- AC2.6 `init` refusals (`init.py:162,200,225`) and `context create` refusals build their fix via
  `fix_line`; the Windows form is asserted for one of them.

### FR3 — Level 3b, first pass by real state (ADRs 0034, 0043)

- AC3.1 `first-pass` (kind `agent`) is pending while `specs/memory/ARCHITECTURE.md` or `QUALITY.md`, fixed
  sections stripped (the `memory_canon` extract helpers), equals a stripped shipped digest, or
  `specs/memory/product/catalog.json` holds no atom; its fix line names the absolute path of the installed
  `dd-audit-project` SKILL.md first-pass section and the pending items.
- AC3.2 `features/specs/template_history.py` moves to `core/template_history.py` (stdlib only; callers
  updated; no re-export shim). `shipped-hashes.json` gains the stripped digests of every historical
  `scaffold/memory/ARCHITECTURE.md` and `QUALITY.md`, backfilled from `git log`; the append-only contract
  test covers them.
- AC3.3 A unit test proves a stub rewritten by `doctor --fix` (FIXED-2) still reads pending, and an edited
  body reads done.
- AC3.4 `dd-audit-project` SKILL.md's first-pass section applies while doctor's next step is
  `first-pass`, ends at `memory.py check` exit 0, and no longer creates `FINDINGS.jsonl` or runs
  `audit.py close`; `tests/contract/test_audit_first_pass.py` asserts it.

### FR4 — Level 3c and the one publish verb (ADRs 0035, 0042)

- AC4.1 `publish` (kind `command`) is pending while `git log --remotes -n1 -- specs/constitution.md` in
  the main repo is empty; its fix line is `CLI context baseline <ctx>`.
- AC4.2 `context baseline <ctx>` takes no `--yes` and no `--push`: invoking it is the consent. In order it
  checks git identity, refuses a dirty tree outside the onboarding paths (`specs/`, `specs-bkp/`, the
  repo-root `AGENTS.md`), fetches, ensures the principal and integration branches on the remote, cuts
  `<work prefix><version>` from the integration branch, commits only the onboarding paths, pushes it
  with upstream set, and leaves it checked out.
- AC4.3 Branch ensuring: unborn remote → both born from one empty root commit; principal present,
  integration absent → integration born at the principal's tip; both present → reused. Version: `0.1.0`
  with no tag, else last tag + 1 patch. Branch names come from the project gitflow (FR6).
- AC4.4 Idempotent: a second run on a published project exits 0, commits and pushes nothing.
- AC4.5 Refusals exit non-zero with one fix line each: dirty outside the paths (a lossless command whose
  execution lets the next run proceed); missing `user.name`/`user.email` (the `git config` line); fetch
  failure/offline (the same baseline line). A refusal before the first write leaves branches, HEAD, index
  and remote unchanged; a push failure after the commit is completed by re-running the same line.
- AC4.6 Integration tests, one per remote state: unborn; principal only; both; a tag present (+1 patch);
  dirty outside paths refused; second run no-op; only onboarding paths in the commit; offline; no identity.
- AC4.7 `features/certification/service.py` invokes baseline without the deleted flags.

### FR5 — Pre-push bootstrap birth (ADR 0036)

- AC5.1 A push to the principal or integration branch passes the branch policy only when its remote sha is
  zero on pre-push stdin AND `publishes_nothing(repo, sha)`: the range computed with the existing
  `_base_exclusions` is empty, or it is exactly one parentless commit whose tree is the empty tree (SHA-1
  and SHA-256 forms); the commit message is still denylist-scanned. Every other push to those branches
  is refused with its fix line.
- AC5.2 `publishes_nothing` replaces `ObjectSource.parents` on the port and `GitSubprocessObjectReader`;
  the test fakes' `parents` stubs are deleted; no second "already published" rule exists.
- AC5.3 `check_branch_policy(refs, gitflow, births)` stays pure; births are computed in
  `push_gate_decision` only for principal/integration refs with a zero remote sha. Stale remote-tracking
  refs make the range non-empty ⇒ refused with `fix: git fetch <remote>`.
- AC5.4 Tests: orphan empty root pushed as principal allowed; `git branch <integration> <principal>`
  pushed allowed; a birth carrying a new commit refused; an allowed birth publishes no object absent
  from the remote before the push.

### FR6 — The project gitflow (ADRs 0037, 0040, 0046)

- AC6.1 `core/gitflow.py`: a frozen `Gitflow(principal, integration, work_prefix)`, `DEFAULT`,
  validating `from_mapping` (valid ref names, principal ≠ integration, non-empty prefix), and
  `role_of(branch)` → principal | integration | work (`<prefix><M.m.p>`) | none. It replaces
  `_MAIN_RE`, `_DEVELOP_RE`, `_FEATURE_RE`.
- AC6.2 The block is `gitflow: {principal: <name>, integration: <name>, work: <prefix>}` in
  `specs/constitution.md` frontmatter, read by `core/frontmatter.parse`; `read_gitflow(specs_dir)`
  returns `(Gitflow, warning | None)` — absent or malformed ⇒ `DEFAULT` plus a warning. One
  frontmatter merge-writer serves both `specs_pattern_version` and `gitflow`, preserving every other key
  and the body byte-for-byte; `_STAMP_RE` is deleted.
- AC6.3 `specs init --context <ctx> [--principal] [--integration] [--work-prefix]`: principal defaults to
  `origin/HEAD` (`git symbolic-ref`, local) else `main`; writes the block on a fresh tree and merges it on
  an existing dadaia tree; same flags twice is a no-op; stdout names the gitflow written. The
  `specs` step's fix line carries the three flags with the detected values, so the agent shows them to
  the operator before running it; no confirmation is stored.
- AC6.4 Pre-push resolution in `cli/commands/ci.py`, once per push, working tree: (1)
  `<toplevel>/specs/constitution.md`; (2) an associated repo → the owning context's main-repo
  constitution via the existing `core/invocation.py` functions; (3) else `DEFAULT` with one stderr
  warning carrying a fix line — never a block. `push_gate_decision` requires the gitflow (no default).
- AC6.5 Pushable: work branches; principal/integration only by FR5; refusal messages and their
  `gh pr create --base …` fix lines name the configured branches. Tests with the default and a custom
  gitflow (`trunk`/`next`/`work/`), an absent block (warning, default), an associated repo inheriting.
- AC6.6 Doctor `GITFLOW-1` (specs section, beside SPECS-VERSION): WARN when the block is absent or
  malformed; fix line = the `specs init` line with detected flags; executing it clears the finding.
- AC6.7 The library's `specs/constitution.md` carries the block; `ci.yml` `pr-source-guard` reads it
  (`read_gitflow`) — integration PRs from work branches or Dependabot, principal PRs from the integration
  branch or `release-please--branches--<principal>`. Literal triggers (`ci.yml`, `release.yml`,
  `secret-scan.yml`, `dependabot.yml` target) stay literal; a contract test pins them equal to the library
  gitflow.
- AC6.8 Every shipped-text literal of PLAN §1 (the `pre-push-ci-gate.sh` wording, `data/AGENTS.md`,
  release/bug/audit skills, `RC-FLOW.md`, scaffold `releases/AGENTS.md`, `templates/specs-AGENTS.md`,
  `registry.json`, `release-state-v1` schema text, README, `docs/`, `llms.txt`, `CONTEXT.md`) is rewritten
  by role ("the principal branch", …) with a pointer to the constitution gitflow. `dd-gitflow-default`'s
  branch table reads by role; its text directs agents to the project's constitution gitflow;
  `CICD-AUTOMATION.md` stays a reference naming the block's keys.
- AC6.9 No pre-commit hook enforces the gitflow; no CI workflow is written into a consumer repo.

### FR7 — Only `context bind` binds (ADRs 0038, 0044)

- AC7.1 `init` and `context create` write no session record, print no `export DADAIA_*` line and call no
  bind; "and bound" leaves their output; the `bind_session` helper is inlined into `context bind`.
- AC7.2 `bind` is pending only when the caller has a resolvable session id and that session is unbound;
  no session identity ⇒ no bind step. Its fix line is `CLI context bind <ctx>`.
- AC7.3 Tests: init/create leave no session record; the bind step appears with `DADAIA_SESSION_ID`
  set and unbound, never without it, and clears after its fix runs.

### FR8 — Dead gate code deleted

- AC8.1 `branch_name_is_permitted` and `parse_push_refs` are deleted (tests use `parse_push_stdin`);
  `_run_specs_canon_scan` loses its unused `object_source`/`repo` parameters; the stale comments in
  `chokepoints/__init__.py`, `branch_policy.py` and `ci.yml` are removed or corrected.

### FR9 — Law, docs, glossary

- AC9.1 Every line claiming init/create binds or that level 3 ends at a stamp is rewritten: `data/AGENTS.md`
  (§7), `dd-cli-library` SKILL.md (levels 2–3, baseline without flags), `docs/quickstart.md`,
  `docs/index.md`, `docs/getting-started.md`, `README.md`, `data/CONSUMER_VALIDATION_RECIPE.md`,
  `CONTEXT.md`. Hand edits only; generated docs are candidate 4.
- AC9.2 `CONTEXT.md` carries §3's terms with their _Avoid_ lists.
- AC9.3 The closure memory pass rewrites `context-management`, `workspace-init`, `audits-canon`,
  `spec-context-project`, `product-vision`, the product index and every atom `memory.py drift` lists;
  `memory.py check` exit 0.
- AC9.4 `public stage`, `public install`, `public doctor` and `dadaia doctor` exit 0 on the live instance.

### FR10 — Autopilot E2E

- AC10.1 `tests/e2e/test_onboarding_journey.py`: from an empty directory, over `file://` bare remotes,
  with `DADAIA_SESSION_ID` set, after one `init … --repo <url>` line, a loop runs `doctor --json`, takes
  the ONBOARDING finding, executes its fix line (`shlex.split`) — the `agent` step by a scripted stand-in
  that fills memory — and stops at no finding or a cap of 10 iterations (reaching the cap fails).
- AC10.2 It ends with the remote holding the principal, integration and `<work prefix>0.1.0` branches,
  the work branch carrying `specs/constitution.md` with the gitflow block, and `doctor` 0 errors.
- AC10.3 Three parametrized remotes: greenfield (unborn), a v6 dadaia tree on the principal, a foreign
  tree on the principal (ending with `specs-bkp/` committed). The HEAD assertion is HEAD == upstream.

### FR11 — Shrink mandate (operator standing rule)

- AC11.1 New production modules: `core/cli_line.py` and `core/gitflow.py` only (`core/template_history.py`
  is a move). No new CLI verb, schema or state file; one new doctor code (`GITFLOW-1`); flags +3
  (`specs init`) and −2 (`context baseline`).
- AC11.2 Expected direction: the touched features shrink. `branch_policy.py`, `push_gate.py`,
  `cli/commands/init.py`, `cli/commands/context.py`, `hooks/ctx_inject.py`, `doctor_structural.py`,
  `core/specs_version.py` and `core/kernel_tunables.py` end with fewer lines than at the definition
  commit; growth is confined to the two new modules, the onboarding step list, the baseline rewrite and
  the new git reads.
- AC11.3 PLAN §1 states a per-unit line estimate; the closure note reports the measured net production
  Python lines (`dadaia_workspace/**/*.py` outside `public/`); exceeding the estimate is a HIGH review
  finding.

## 5. Replaces

- R1 `onboarding.py`'s if-chain `_lowest` (three levels, level 3 ending at the `audits_histo` stamp, a
  POSIX `$(git rev-list …)` fix) → FR1/FR3/FR4 step list.
- R2 Two CLI spellings — `DADAIA_BIN` and `onboarding.cli_path` — and per-site fix strings → FR2.
- R3 The second `next_step` call site in `ctx_inject._emit_bootstrap` → one helper (AC1.5).
- R4 `tests/contract/test_onboarding_text.py` regex census → AC1.7 + AC2.5.
- R5 FIXED-2's bare `dadaia doctor --fix` text; TREE-5's copy-a-library-path prose and `fixable=False`
  on a missing law file; TREE-5's advertised fix that does not clear → AC2.3/AC2.4.
- R6 First pass keyed on an empty `audits_histo` and closed by a stamp (`dd-audit-project`) → AC3.4.
- R7 `features/specs/template_history.py` and raw-byte comparison of memory stubs → AC3.2/AC3.1.
- R8 Unborn-only `baseline`, its convergent `has_commits` branch, the hard-coded `feature/0.1.0`, the
  `--yes`/`--push` flags and certification's use of them → FR4.
- R9 Pre-push refusing every principal/integration push, bootstrap included → FR5.
- R10 `ObjectSource.parents` and its fake stubs → `publishes_nothing` (AC5.2).
- R11 The three branch regexes, `branch_name_is_permitted`, `parse_push_refs`, unused
  `_run_specs_canon_scan` parameters, stale comments → FR6/FR8.
- R12 `_STAMP_RE` frontmatter regex → `core/frontmatter.parse` + one merge-writer (AC6.2).
- R13 Hard-coded branch names in the library `pr-source-guard`, the pre-push hook text, ~36 shipped-text
  lines and `dd-gitflow-default`'s table → AC6.7/AC6.8.
- R14 `init`/`context create` binding (session record, export lines, `bind_session` shared helper) → FR7.
- R15 Law, docs and atoms claiming bind-by-create/init or level 3 = stamp → FR9.

## 6. Out of scope (non-goals)

- Generated docs, CLI reference, step table page, docs site (candidate 4, ADR 0039).
- Trunk-based gitflow (`gitflow-trunk-based-model`), consumer server-side enforcement
  (`consumer-gitflow-server-side-enforcement`), per-repo override for an associated repo
  (`associated-repo-gitflow-override`) — backlog ideas.
- Skill-script command constants (`kernel_tunables.py` `python3 .agents/…`) — not CLI spellings.
- Any pre-commit hook, consumer CI job, confirmation stamp, state file, or network call in the derivation.
- Retrofitting consumer trees beyond `GITFLOW-1` + `specs init`.

## 7. Dependencies and risks

- Order (inventory R7): `core/cli_line.py` + `DADAIA_BIN` migration → `template_history` move →
  `core/gitflow.py` → FR5 birth → FR4 baseline → FR1 steps → callers, law, docs. FR5 must land before
  FR4 (the birth pushes pass through the hook).
- Stale remote-tracking refs give a false `publish` pending; `baseline` fetches first and is idempotent.
- The property test (AC1.3) runs real git over `file://` — keep its example count bounded for CI time.
- Placeholders in the `context` step fix line: only the operator supplies a clone URL; the E2E starts
  from `init --repo`.
- Library's own gitflow change reaches `pr-source-guard` on the PR that carries it; the contract test
  (AC6.7) prevents trigger drift.
- The bind surface carries ~15 bugs: FR7 removes authors, never adds one.

## 8. Traceability

| FR | ADRs | Replaces | Surface |
|---|---|---|---|
| FR1 | 0033 | R1 R3 R4 | `onboarding.py`, `ctx_inject.py`, `doctor.py`, `context.py`, `init.py` |
| FR2 | 0045 | R2 R4 R5 | `core/cli_line.py`, 9 importers, `doctor_memory.py`, `doctor_structural.py`, `rules.py` |
| FR3 | 0034 0043 | R6 R7 | `core/template_history.py`, `shipped-hashes.json`, `dd-audit-project` |
| FR4 | 0035 0042 | R8 | `spec_context/service.py`, `git_subprocess.py`, `context.py`, certification |
| FR5 | 0036 | R9 R10 | `push_gate.py`, `branch_policy.py`, `git_objects.py` |
| FR6 | 0037 0040 0046 | R11 R12 R13 | `core/gitflow.py`, `specs_version.py`, `specs.py`, `ci.py`, `rules.py`, `ci.yml`, shipped text |
| FR7 | 0038 0044 | R14 | `init.py`, `context.py`, `onboarding.py` |
| FR8 | — | R11 | chokepoints, `ci.yml` |
| FR9 | 0033–0038 | R15 | law, docs, `CONTEXT.md`, atoms |
| FR10 | 0033 0035 0036 | — | `tests/e2e/test_onboarding_journey.py` |
| FR11 | standing rule | — | all |
