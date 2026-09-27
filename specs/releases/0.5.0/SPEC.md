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

Grill rounds 1–3 (2026-09-25), all accepted. Law: ADRs 0033–0038, 0040, 0042–0049; as-is review: PLAN
§1. Amended in place 2026-09-26 (REJECTED 40a24031) and 2026-09-27 (reviews 6–7, the anchor-first
design, PLAN §1.4, the tests retro).

## 2. Objective

One derived, ordered list of onboarding steps — each a real-state predicate and one fix line built by one
builder — that an agent loops on (run doctor, execute `fix:`, repeat) from an empty directory to a project
published on its principal, integration and work branches under a gitflow the project declares in its
constitution; no step can stall, and the touched features shrink.

## 3. Terms

- **Onboarding step** — one entry of the ordered list: id, kind, a real-state predicate ("pending"), one
  fix line. Ids in order: `context`, `bind`, `specs` (3a), `first-pass` (3b), `publish` (3c).
  _Avoid_: stage, wizard step, onboarding state.
- **Step kind** — `command` (the fix line is a shell command) or `agent` (it names a skill section and a
  pending list). _Avoid_: type, mode.
- **Onboarding level** — 1 workspace, 2 context (`context`, `bind`), 3 specs (3a `specs`,
  3b `first-pass`, 3c `publish`); derived, never stored.
- **Next step** — the first pending onboarding step, printed identically by `doctor`, `init`,
  `context create` and SessionStart.
- **First pass** — level 3b; done when memory holds real content, never by a stamp.
- **Project publication** — level 3c: the first push of a main repo's specs, by `context baseline`.
  _Avoid_: publish step, baseline (the pre-push published-history baseline).
- **Onboarding anchor** — the commit holding the onboarding paths, made on a detached HEAD (an unborn
  clone's first commit); every later HEAD move keeps it as an ancestor. _Avoid_: baseline commit.
- **Unpublished range** — the commits of a ref origin does not hold (`unpublished()`); empty = already
  published. _Avoid_: publishes nothing, boundary.
- **Fix line** — the one runnable line a finding, refusal or step prints after `fix:`; every one naming
  the workspace CLI is built by `fix_line`. _Avoid_: hint, remedy text.
- **Project gitflow** — the `gitflow:` block of `specs/constitution.md` frontmatter naming three roles:
  **principal branch** (deployed; default from `origin/HEAD`, else `main`), **integration branch**
  (default `develop`), **work branch** (`<work prefix><M.m.p>`, prefix default `feature/`).
  _Avoid_: branch policy (the gate's check), branching model.
- **Bootstrap birth** — a push creating the principal or integration branch whose unpublished range is
  empty, or the first push to an origin holding neither. _Avoid_: bootstrap push, first push.

## 4. Functional requirements

`CLI` = the absolute workspace CLI path `cli_path` returns. Files are library source; projections follow
by `public stage` + `public install`.

### FR1 — One onboarding derivation (ADR 0033)

- AC1.1 `features/workspace/onboarding.py` holds ONE ordered tuple of step definitions (id, kind,
  pending(state), fix(state)) in the §3 order; `next_step` returns the focus context's first pending step,
  else the first pending across ALIVE contexts, else `None`; `Step` carries `kind`.
- AC1.2 Every predicate reads real state (files, git, the session registry); writing
  `audits_histo.jsonl` changes no step (unit test).
- AC1.3 A hypothesis property test over random real-state prefixes (tmp dirs, `file://` bare remotes)
  executes each pending command step's fix line and asserts that step is no longer pending; operator
  placeholders (`<clone-url>`, `<name>`) are the only tokens the test substitutes.
- AC1.4 Along every property run the printed step's index strictly increases; the loop ends within
  `len(steps)` command executions plus the agent steps.
- AC1.5 `doctor` (ONBOARDING info finding; `--json` carries `step` and `kind`), `init`, `context create`
  and SessionStart print the same `Step.text()`, which names the kind. SessionStart calls one helper for
  bound and unbound sessions; a hook test asserts both paths print doctor's text.
- AC1.6 The derivation issues no network call; only `publish` reads the gitflow block (the local
  integration name). _Amended 2026-09-26._
- AC1.7 A `tests/contract/` census of the step list (id, kind, order) replaces the regex census
  `tests/contract/test_onboarding_text.py`.

### FR2 — One fix-line builder (ADR 0045; absorbs round-2 items)

- AC2.1 `core/cli_line.py` owns `cli_path(root)` (moved from `onboarding.py`) and
  `fix_line(root, *argv)`, joining with `shlex.join` on POSIX; on Windows forward slashes, double quotes
  only around a blank; a unit test pins both forms; a contract test runs a printed line in Git Bash, cmd
  and PowerShell on the Windows job (a path with a blank needs `& `). _Amended 2026-09-26._
- AC2.2 `DADAIA_BIN` is deleted from `core/kernel_tunables.py`; every call site in the importing
  modules (`features/specs/rules.py`, `features/spec_context/{service,doctor,gate_policy}.py`,
  `cli/commands/{context,doctor}.py`, `infrastructure/ledger_scripts.py`, `hooks/venv_guard.py`'s
  suggested command) migrates — no exception.
- AC2.3 FIXED-1/FIXED-2 (`doctor_memory.py`) and TREE-4/TREE-5 carry their remedy as a `fix_line`-built
  line; no finding description embeds a bare `dadaia` command.
- AC2.4 A missing scaffolded law file (`specs/AGENTS.md` or `specs/<area>/AGENTS.md`) is `fixable=True`:
  `CLI doctor --fix --context <ctx>` writes the shipped template (lossless); the copy-a-library-path prose
  is gone; a TREE-5 case `--fix` does not repair advertises no `doctor --fix` line; an integration test
  covers both.
- AC2.5 An AST contract test fails when any module outside `core/cli_line.py` builds a fix line naming the
  workspace CLI other than through `fix_line` (a literal or f-string holding the venv CLI path or a bare
  `dadaia ` command).
- AC2.6 `init` and `context create` refusals build their fix via `fix_line` (Windows form asserted once).

### FR3 — Level 3b, first pass by real state (ADRs 0034, 0043)

- AC3.1 `first-pass` (kind `agent`) is pending while `specs/memory/ARCHITECTURE.md` or `QUALITY.md`, fixed
  sections stripped (the `memory_canon` extract helpers), equals a stripped shipped digest, or
  `specs/memory/product/catalog.json` holds no atom; its fix line names the absolute path of the installed
  `dd-audit-project` SKILL.md first-pass section and the pending items.
- AC3.2 `features/specs/template_history.py` moves to `core/template_history.py` (stdlib only, no
  shim). `shipped-hashes.json` gains the stripped digests of every historical scaffold `ARCHITECTURE.md`
  and `QUALITY.md`, backfilled from `git log`; the append-only contract test covers them.
- AC3.3 A unit test proves a stub rewritten by `doctor --fix` (FIXED-2) still reads pending, and an edited
  body reads done.
- AC3.4 `dd-audit-project` SKILL.md's first-pass section applies while doctor's next step is
  `first-pass`, ends at `dadaia doctor --context <ctx>` exit 0 (LINT-1 owns the atoms,
  `memory.py check` only the catalog pair), and no longer creates `FINDINGS.jsonl` or runs
  `audit.py close`; `tests/contract/test_audit_first_pass.py` asserts it; no shipped text makes
  `memory.py check` the done criterion. _Amended 2026-09-27:_ bug fix 3886760e.

### FR4 — Level 3c and the one publish verb (ADRs 0035, 0042, 0048)

- AC4.1 `publish` (kind `command`) is pending while `origin/<integration>` is absent or
  `git log --remotes=origin -n1 -- specs/constitution.md` in the main repo is empty (a v6 tree on the
  principal alone is unpublished); its fix line is `CLI context baseline <ctx>`. _Amended 2026-09-26._
- AC4.2 `context baseline <ctx>` takes no `--yes`, `--push` or repo argument (invoking it is consent)
  and publishes the main repo only, anchor-first: git identity; fetch; commit the onboarding paths
  (`specs/`, `specs-bkp/`, root `AGENTS.md`) on a detached HEAD, the anchor; read the gitflow from it
  (ADR 0048, one reader); bring `<work prefix><version>` to the anchor; merge origin's start ref (first
  held of work, integration, principal); one atomic push of births and `<work>`, upstream set. HEAD never
  leaves the anchor line (an existing `<work>` is merged into the anchor, then fast-forwarded); the anchor
  never lands on the principal or any other existing branch. Unrelated histories merge only when the
  anchor's root holds only onboarding paths. A second foreign backup lands in `specs-bkp/<UTC>/`.
  _Amended 2026-09-27._
- AC4.3 Births: empty origin → principal and integration at the anchor commit, `<work>` carrying any
  stale local work; principal only → integration at `origin/<principal>`; both → reused; pushed by refspec
  `<sha>:refs/heads/<branch>`, no local head created, moved or reset. Version: `0.1.0`, else last tag + 1
  patch. _Amended 2026-09-27._
- AC4.4 One published answer (M4): the `publish` step and baseline's no-op read one predicate; "already
  published" (exit 0, nothing committed or pushed) only when it holds and HEAD has no unpublished range,
  never while the anchor is unpublished. _Amended 2026-09-27._
- AC4.5 Refusals exit non-zero; no fix is a bare re-run. _Amended 2026-09-27._
  - Before any write (HEAD, branches, index, remote unchanged), one fix line each: no checkout
    (`CLI context alive <ctx>`); no git identity (`git config`); no `specs/constitution.md` on disk or at
    HEAD (`CLI specs init --context <ctx>`).
  - Origin lacks the principal: refused after the anchor (the gitflow exists only there), HEAD on
    `<work>` at the anchor, every other branch untouched. One candidate head → `fix: CLI specs init
    --context <ctx> --principal <head>`; several → listed, fix with a `<principal>` placeholder, no guess.
  - A fetch, merge or push failure (offline, auth, wrong URL, non-fast-forward, conflict) carries git's
    full output (ruling R13); after the anchor it names the anchor sha; HEAD holds it.
  - Cut (h): work outside the onboarding paths is neither refused nor committed; git refuses a switch
    or merge it collides with ("commit … or stash").
- AC4.6 Integration tests, one per state: empty origin; principal only; both; a tag; a non-default
  principal; an unborn clone of a non-empty origin; principal absent (one, several heads); a local
  `<work>` with unrelated history; a conflict; offline; no identity; foreign work carried; only onboarding
  paths in the anchor; local principal unchanged; second run no-op; after each failure `publish` stays
  pending and no "already published" prints.
- AC4.7 `features/certification/service.py` invokes baseline without the deleted flags.
- AC4.8 An associated repo publishes by plain `git push` under the pre-push gate; a refusal or doctor
  finding about it names that one command. _Amended 2026-09-27:_ cut (f).
- AC4.9 `context dead --commit` never stages an unmerged entry (consented untracked files still are): git
  refuses a conflicted commit, no conflict marker is published; a push failure carries git's full output
  and removes nothing. Dead's work-branch refusal stays. With no git identity it refuses before any
  write, one fix line (`git -C <repo> config user.name '<user.name>'`); checkout, HEAD, origin and the
  ALIVE state unchanged. _Amended 2026-09-27._

### FR5 — Pre-push bootstrap birth (ADR 0036)

- AC5.1 A push to the principal or integration branch passes the branch policy only as a bootstrap birth:
  remote sha zero on pre-push stdin AND either origin holds neither role branch or the ref's unpublished
  range is empty. Every other push to those branches is refused with its fix line. _Amended 2026-09-27._
- AC5.2 `ObjectSource.parents` and its fake stubs are deleted; `unpublished` (origin-scoped) is the one
  "already published" rule for births, the rewrite fix and `unpushed`. _Amended 2026-09-27._
- AC5.3 `check_branch_policy(refs, gitflow, births)` stays pure; births are computed in
  `push_gate_decision` only for principal/integration refs with a zero remote sha. A ref is judged by the
  remote branch it lands on; a birth passes from any source. A birth carrying new objects to an origin
  holding a role branch, stale refs included, gets one fix: birth at the other role's published tip.
- AC5.4 Tests: an empty origin's three branches in one atomic push allowed; integration born at
  `origin/<principal>` allowed; a birth carrying a new commit to a non-empty origin refused; the rewrite
  fix, executed, clears a root-reaching and a mid-history range. _Amended 2026-09-27._
- AC5.5 The gate's rewrite fix is one formula for every unpublished range: `reset --soft <oldest
  unpublished commit of the refused ref>`, then the term removed and the commit amended (a branch HEAD is
  not on: `git switch <branch>` first). Operator-action text only for a tag or a detached HEAD. Refusing
  baseline's own push names `CLI context baseline <ctx>` as the step after the amend. _Amended 2026-09-27._
- AC5.6 Baseline and `dead --commit` run the pre-push matcher in-process on what they commit. One
  registry (`privacy_baseline.json` + operator terms), control characters stripped, refuses a
  secret-named key assigned a whole literal (quoted 8+ chars, or unquoted to line end, optional `#`
  comment); references, templates and code expressions pass. A private-key container
  (`.pem .key .p12 .pfx .jks .keystore .der`) is refused on presence alone; a public certificate
  (`.crt .cer`) passes. The `test_one_secret_matcher.py` matrix is the contract. _Amended 2026-09-27:_
  bug fix, R10-4, registry v14.

### FR6 — The project gitflow (ADRs 0037, 0040, 0046)

- AC6.1 `core/gitflow.py`: a frozen `Gitflow(principal, integration, work_prefix)`, `DEFAULT`,
  validating `from_mapping` (valid ref names, principal ≠ integration, non-empty prefix not nested under
  a role name), and `role_of(branch)` → principal | integration | work (`<prefix><M.m.p>`) | none. Role
  names match exactly and case-sensitively (git's rule); a work name is the prefix plus a bare `M.m.p`,
  no suffix. It replaces the three branch regexes. _Amended 2026-09-27:_ nested prefix; exact names.
- AC6.2 The block is `gitflow: {principal: <name>, integration: <name>, work: <prefix>}` in
  `specs/constitution.md` frontmatter, read by `core/frontmatter.parse`; `read_gitflow(specs_dir)`
  returns `(Gitflow, warning | None)` — absent or malformed ⇒ `DEFAULT` plus a warning. One
  frontmatter merge-writer serves both `specs_pattern_version` and `gitflow`, preserving every other key
  and the body byte-for-byte; `_STAMP_RE` is deleted.
- AC6.3 `specs init --context <ctx> [--principal] [--integration] [--work-prefix]`: principal defaults to
  `origin/HEAD` (`git symbolic-ref`, local) else `main`; writes the block on a fresh tree and merges it on
  an existing dadaia tree; same flags twice is a no-op; stdout names the gitflow written.
  _Amended 2026-09-26:_ the `specs` step's fix carries no gitflow flag (a valid block is
  kept, else detected) and `--replace-foreign` only for a foreign tree; an unparseable frontmatter is its
  own doctor finding.
- AC6.4 Pre-push resolution in `cli/commands/ci.py`, once per push, from committed data:
  `specs/constitution.md` at HEAD; else the newest one reachable from a remote-tracking ref (local); else
  the owning context's main-repo constitution (`core/invocation.py`); else `DEFAULT` with one stderr
  warning — never a block. Refusal fixes name only refs that exist. `push_gate_decision` requires the
  gitflow (no default). _Amended 2026-09-26._
- AC6.5 Pushable: work branches; principal/integration only by FR5; refusal messages and their
  `gh pr create --base …` fix lines name the configured branches. Tests with the default and a custom
  gitflow (`trunk`/`next`/`work/`), an absent block (warning, default), an associated repo inheriting.
- AC6.6 Doctor `GITFLOW-1` (specs section, beside SPECS-VERSION): WARN when the block is absent or
  malformed; fix line = `specs init --specs-dir <specs>` (no flags); executing it clears the finding and
  never resets an operator's custom names. _Amended 2026-09-26._
- AC6.7 The library's `specs/constitution.md` carries the block; `ci.yml` `pr-source-guard` reads it
  (`read_gitflow`): integration PRs from work branches or Dependabot, principal PRs from the integration
  branch or `release-please--branches--<principal>`. Workflow triggers stay literal; a contract test pins
  them equal to the library gitflow.
- AC6.8 Every shipped-text branch literal PLAN §1 lists (hook text, law, skills, scaffold, schema text,
  README, `docs/`, `llms.txt`, `CONTEXT.md`) is rewritten by role with a pointer to the constitution
  gitflow; `dd-gitflow-default`'s branch table reads by role; `CICD-AUTOMATION.md` names the block's keys.
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
  (§7), `dd-cli-library` SKILL.md (levels 2–3, baseline without flags), `docs/`, `README.md`,
  `data/CONSUMER_VALIDATION_RECIPE.md`, `CONTEXT.md`. Hand edits only; generated docs are candidate 4.
- AC9.2 `CONTEXT.md` carries §3's terms with their _Avoid_ lists.
- AC9.3 The closure memory pass rewrites `context-management`, `workspace-init`, `audits-canon`,
  `spec-context-project`, `product-vision`, the product index and every atom `memory.py drift` lists;
  `dadaia doctor --context <ctx>` exit 0. _Amended 2026-09-27._
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
- AC11.2 The touched features shrink: `branch_policy.py`, `push_gate.py`, `cli/commands/init.py`,
  `cli/commands/context.py`, `hooks/ctx_inject.py`, `doctor_structural.py`, `core/specs_version.py` and
  `core/kernel_tunables.py` end with fewer lines than at the definition commit; growth only in the two
  new modules, the step list, the baseline and the new git reads.
- AC11.3 The closure note reports the net production Python lines (`dadaia_workspace/**/*.py` outside
  `public/`) of the candidate's own commits, 5364ba0d..closure, excluding the operator-ordered shrink
  deletions (800c5e2d 009721d6 f38f7ff8 de4e3179 114be682) and Arm B fixes; above +362 net is a HIGH
  review finding. _Amended 2026-09-27:_ operator ceiling (PLAN §1.1), never raised.

## 5. Replaces

- `onboarding.py`'s if-chain `_lowest` (level 3 = the `audits_histo` stamp) → the FR1 step list;
  `ctx_inject._emit_bootstrap`'s second `next_step` call → one helper (AC1.5).
- `DADAIA_BIN`, `onboarding.cli_path` and per-site fix strings → FR2; the regex census → AC1.7, AC2.5.
- FIXED-2's bare `dadaia`; TREE-5's library-path prose and `fixable=False` → AC2.3, AC2.4.
- First pass closed by a stamp; `features/specs/template_history.py`; raw-byte stub comparison → FR3.
- Unborn-only `baseline`, its `has_commits` branch, `feature/0.1.0`, `--yes`/`--push` → FR4.
- The publish that commits where HEAD is, then switches; the foreign-change preflight and its stash
  fix; `_sync_failure`'s rerun and by-cause fixes; associated-repo publish through baseline → AC4.2,
  AC4.5, AC4.8.
- Pre-push refusing every principal/integration push → FR5; `ObjectSource.parents`, the empty-tree
  `publishes_nothing` and the rewrite fix's no-fix root arm → `unpublished` (AC5.1, AC5.2, AC5.5).
- `_SECRET_SCAN_RULES`/`scan_file_for_secrets` → one registry (AC5.6).
- The three branch regexes, `branch_name_is_permitted`, `parse_push_refs`, unused
  `_run_specs_canon_scan` parameters → FR6, FR8; `_STAMP_RE` → one merge-writer (AC6.2).
- Hard-coded branch names in `pr-source-guard`, hook text, shipped text → AC6.7, AC6.8.
- `init`/`context create` binding and the `bind_session` helper → FR7; law and atoms saying so → FR9.

## 6. Out of scope (non-goals)

- Generated docs, CLI reference, step table page, docs site (candidate 4, ADR 0039).
- Backlog ideas `gitflow-trunk-based-model`, `consumer-gitflow-server-side-enforcement`,
  `associated-repo-gitflow-override`.
- Skill-script command constants (`python3 .agents/…`) — not CLI spellings.
- Any pre-commit hook, consumer CI job, confirmation stamp, state file, or network call in the derivation.
- Retrofitting consumer trees beyond `GITFLOW-1` + `specs init`.

## 7. Dependencies and risks

- Order: FR2 → FR3's move → `core/gitflow.py` → FR5 → FR4 → FR1 → FR9.
- Stale remote-tracking refs give a false `publish` pending; `baseline` fetches first.
- The property test (AC1.3) runs real git; its example count stays bounded.
- The library's gitflow change reaches `pr-source-guard` on the PR carrying it; AC6.7 pins the triggers.

## 8. Traceability (FR → ADRs)

FR1 0033 · FR2 0045 · FR3 0034 0043 · FR4 0035 0042 0048 · FR5 0036 ·
FR6 0037 0040 0046–0048 · FR7 0038 0044 · FR8 — · FR9 0033–0038 · FR10 0033 0035 0036 · FR11 standing rule
