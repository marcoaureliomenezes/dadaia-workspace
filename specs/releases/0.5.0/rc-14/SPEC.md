# SPEC — Release: 0.5.0, candidate 14 — one owner per fact; Wave 1 law, skills and dev loop

**Status:** Approved
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-11
**Origin:** backlog:dd-ask-me-owned-questioning-skill,architecture-adr-section-generated,public-law-language-neutral,test-suite-diet,programmatic-dates-in-skills,impacted-test-selection,law-one-home-residual,bug-batch-cause-trigger-and-attempt-cap,define-backlog-merge-runs-verify,hotfix-specs-revert-commit-shape,harness-specific-surface-minimized,adr-0122-zero-backlog-destined-to-this-release,job-gate-runs-the-law-deletion-check,merge-entry-times-survive-rebase,hypothesis-cache-stays-out-of-repo-trees,task-gate-drops-deleted-paths-itself,architecture-principles-measured-by-re-pointed,fix-reader-rebuild-under-c,task-gate-declared-owner-tests,pr-merge-method-pinned,phase-implementation-has-a-place,stage-gate-keeps-only-the-red-check,verdict-author-unbound,judge-config-outside-the-script-dir,gate-reuses-a-green-result-for-the-same-tree,process-proportional-to-change-size,bug-status-deferred-banned,quality-scorecard-ruler,task-lines-carry-seam-and-adr-clause,skill-scripts-one-kernel,tests-one-contract-one-home,tests-tmp-expire-at-job-merge,policy-tests-leave-pytest,review-mutation-on-the-diff,closure-test-suite-readouts; bugs:worktree-new-crashes-on-an-unreadable-release-state,release-check-admits-a-dag-that-phase-refuses,release-new-orphans-a-drafted-next-rc,verify-line-shlex-mangles-windows-paths,context-repo-refusals-carry-no-fix-line,codex-persona-frontmatter-drops-on-crlf,doctor-misses-worktrees-of-a-repo-that-left-its-context,job-gate-red-on-untracked-bytecode,cross-os-ci-masks-utf8,cli-refusals-print-no-fix-line,context-alive-crashes-on-a-non-git-repo-dir,skill-git-runners-read-the-callers-git-env,ledger-replace-destroys-a-symlinked-ledger,frontmatter-parsers-disagree-on-crlf-and-bom,slug-grammar-four-patterns-disagree

Sources: the 0.5.0 scope grill of 2026-10-11 (report https://claude.ai/artifact/GGEzLQDmquUfrUhacFgmmK; "Confirmo, pode seguir (Recommended)"); each Origin entry's "Scope grill 2026-10-11" paragraph in `BACKLOG.json`; the duplicated-decider inventory at `dd10eb7de` (27 groups, about 110 copy sites, 12 diverged). Operator, 2026-10-11: "Eu so quero que vocÊ converja para 0 bugs ... qual é o problema core de tantos bugs ficarem aparecendo o tempo todo?"; "Isso é obvio né. Agora vc me fala desse problema arquitetural??? é esse o bug porra"; on the owner: "A: script da skill dona (Recommended)" (ADR 0246). FR18 is the operator demand `review-rework-prevention-2026-10-12`, ordered into rc-14 rather than the backlog; the Origin grammar has no clause for an operator demand beside backlog and bug ids, so it is recorded here. Operator, 2026-10-11/12: "Se está precisando de tanto retrabalho obviamente temos um problema serio que não será tolerado na proxima release."; "Não tolerarei nem mesmo 30% dessa quantidade de retrabalhos que tivemos."; "não porra, é materializado na lib ... algo que todo projeto usando dadaia-workspace siga ... e no eval, vai funcionar??? obviamente não"; "NÃO DEVE HAVER NADA NADA EM MEMORY QUE COMPETE COM NOSSAS FEATURES E CONTEXTO NATIVO DO DADAIA-WORKSPACE"; "EU FALEI HOTFIX OU AGORA ... NÃO É BACKLOG ... É AGORA."

FR19 is the operator demand of 2026-10-12 on the test suite and its docstrings, ordered into rc-14 rather than a hotfix or the backlog, recorded here like FR18 and accepted as ADR 0248 (amends 0166). Operator, verbatim core: "É COMPLETAMENTE PROIBIDO, ESCREVE, É LEI, PROIBIDO DOCSTRING QUE NÃO DESCREVA CONTRATO. DOCSTRING COM BUG, ADR ... NÃO SERÃO MAIS ACEITAS. TA PROIBIDO DOCSTRING COM INFORMAÇÕES DIFERENTES DO CONTRATO DO METODO. VC TAMBÉM DEVE TRATAR TODOS ESSES PROBLEMAS: [test-quality findings + L1–L6 + tests/tmp] ... BASE: REPORT https://claude.ai/artifact/Rn1qCNi2qEcR1wXTNzEznf ... precisamos melhorar esses pontos agora, agora, num hotfix ou incluindo na rc14."; on placement: "FR19 na rc-14 (Recommended)". The five backlog entries of the 2026-10-12 test audit join the Origin, absorbed by FR19.

Placement (main-thread inference, review MEDIUM): `skill-scripts-one-kernel` was destined to Wave 2. Its move into rc-14 is the main thread's reading of "totalmente agora ... é para ser feito exatamente nessa release" and "é esse o bug porra". The operator's Option A ruling confirmed it afterwards.

---

## Bug window review

rc-13 ran from `7a1ae384a` (2026-10-10) to its implementation at `d68a7c42f`. Three fixes closed in that window; one rc-13 verdict is carried.

| verdict | disposition | fixes |
|---|---|---|
| KEEP | `git show 44a9f58c8`: +34/−92, itself the REBUILD its `caused_by` required; no assert edited, no branch, no reach; no record names it in `caused_by`. | `agent-model-templates-pin-superseded-sonnet-and-haiku` |
| REBUILD — FR14 | `git show d68a7c42f`: the second fix in one day on `_release_phase._refuse_open_worktrees` (after `f1d59e9e6`). The unit computes the next candidate a second time; `_release_schema.next_candidate`'s copy fails as `release-new-orphans-a-drafted-next-rc`. | `release-closure-refuses-the-next-candidates-define-tree` |
| KEEP | `git show d7503ff81`: a specs revert, no code. Its cause, guard v33, is deleted (FR9); its commit shape is FR6. | `rc13-define-cites-an-unread-prefix-family` |
| REBUILD — FR14 (carried) | `2a8b5637f` added a second `_RELEASE.json` parser in `_worktree_new.py`; `worktree-new-crashes-on-an-unreadable-release-state` is that parser failing. | `worktree-new-opens-a-job-outside-implementation` |

Bugs law §2: Job 1 executes both REBUILD rows.

## 1. Problem

The root cause of the bug stream: one fact is decided in several places. The inventory counts 27 facts with two or more deciders and 12 that already diverged. Four divergences replay as bugs (FR11 to FR13). The projection makes the copies itself: `public_assets.py` `_SKILL_SCRIPT_SHARED` and `_SKILL_SCRIPT_SCHEMAS` copy `_ledger`, `_specs`, `_privacy`, the baseline and the schemas into each skill (3,869 lines in 31 files), and `slop.py` v37/v38 rows sanction twins.

The structural-audit bugs of 2026-09-27/28 (`sa-package-defines-a-fact-twice`, `sa-seven-workspace-root-rules`, `sa-live-release-resolved-by-two-readers`, `sa-ledger-vocabulary-and-atomic-write-duplicated-in-scripts`, `sa-frontmatter-split-five-ways`) closed while the copies stayed. Their premise, "the stdlib-only skill scripts and the package cannot share code", is false: ADR 0157 already has `privacy_check.py` import the skill's `_ledger.py`, and ADR 0135 makes the skill script the owner and the package its importer.

The Wave 1 law has its own defects: an expiring grill record, ADRs without threshold or options, a drifted `ADR:` status label, shipped law naming library internals, model-typed dates, a guard reading `specs/` prose, no impacted-test read.

Fifteen confirmed bugs are open.

Review rework (FR18): most of rc-14's reviewed trees were rejected on their first pass; AC18.5 counts it and the closure summary records the count (G7). The causes: the hand-off already failed its declared checks (5); a PLAN row or ruling was neither reproduced nor swept for consumers (4); a rework fixed the cited site and broke its contract (2); an implementer claim was unproven (2). Every finding was real. What was missing was a review before the code review, of the definer's spec and of the implementer's hand-off.

The test suite (FR19) behaves as an append-only evidence ledger. The 2026-10-12 audit measured 3,276 cases in 1,393 functions and a test/production line ratio of 1.86× (1.87× at `79484b173`: 47,994 tracked `.py` lines under `tests/` over 25,601 under `dadaia_workspace/`). One cross-cutting fix-line contract is retested by about 300 tests in about 55 files over three harnesses, and about 480 repo-policy cases run inside pytest. Docstrings cite governance ids: 203 in the package, 822 in tests and 10 in scripts (AST scan). Six law rules make every event add a test that never leaves (ADR 0248's L1 to L6).

## 2. Measurable Goals

- G1. Zero copies: for each inventory group the PLAN names one `git grep`, and each returns only the owner's definition.
- G2. `bugs.py status` lists none of the fifteen Origin bugs as open at closure.
- G3. `git grep -n 'noqa: E402' -- dadaia_workspace` returns nothing; each skill entry point keeps one bootstrap `sys.path` line.
- G4. radon reports no D–F function under `dadaia_workspace/public/skills/*/scripts` (constitution §5).
- G5. Every ADR proposed after rc-14 carries `options` and a self-contained `ruling.words`; no `ADR:` label carries a status token after the Reconciliation.
- G6. The FR4 grep over `public/` returns only the workspace's own operation; `git grep -n -- '--ts' dadaia_workspace/public/skills` returns nothing.
- G7. At the next candidate's closure, AC18.5's count shows REJECTED at most 30% of rc-14's and first-pass rejected at most 20%. rc-14's baseline is what `verdict.py stats` prints for rc-14 at its closure, recorded in its closure summary.
- G8. At rc-14 closure (operator: "Zeros + razão ≤ 1,2× (Recommended)"): zero governance ids in docstrings and comments (AC19.2); zero policy cases in pytest (AC19.9); an empty `tests/tmp` at every job merge (AC19.6); one home per cross-cutting contract (AC19.7); a test/production line ratio of at most 1.2×, measured as in §1 (today 1.87×, about −35% of test lines). Every deleted test is proven by the kill matrix (AC19.7).

## 3. Requirements

### Wave 1 law, skills and dev loop

#### FR1 — dd-grill-me complete, name kept (`dd-ask-me-owned-questioning-skill`; "Tudo, sem rename (Recommended)")

- AC1.1 (no test — reviewer sweep): `references/` holds one file per stage: backlog (a decision at all: problem measured, feature or bug, scope); release (before the SPEC); adr (FR2's threshold and the question bank: reversibility, drivers, a quality-attribute scenario whose response measure becomes `measured_by`, the surface's bug history, coupling, reuse, rollback, cost, security, what it deletes, the accepted drawback); plan (contradicts an accepted ADR, or carries a decision past the threshold). `SKILL.md` keeps one question at a time, 3 closed options with trade-offs, one recommended, free text through the tool.
- AC1.2 (no test — reviewer sweep): Three triggers, one line each: before `backlog.py new`; `dd-release-definition` §3 before the SPEC or an ADR; after the PLAN, only past the threshold.
- AC1.3 (no test — reviewer sweep): Every answer lands in a durable record in the same turn (backlog description, ADR `options` and `ruling.words`, or the SPEC); the handoff stays ephemeral; `grep -rn 'whole frontier\|grill-<slug>.md' dadaia_workspace/public` returns nothing (ADR 0165).
- AC1.4 (integration): The report is the harness artifact first, else HTML styled by one CSS file under `scripts/`; `public install` projects `references/` and the CSS.

#### FR2 — the ADR law and the ledger decisions (`law-one-home-residual`)

Operator: "Triagem + gerada (Recommended)", "ADR que supersede (Recommended)", "Ratificar os 4 (Recommended)". The clause "an ADR is born only in `dd-release-definition`" is dropped (main thread: an unruled agent default; the threshold serves "Se tudo é ADR nada é ADR"). Part (c), ADR 0193's `amends: null`, goes to the Wave 4 triage.

- AC2.1 (no test — reviewer sweep): The scaffold ADR law states the three-leg threshold in one line: one-way door, architecturally significant, at least two genuine options.
- AC2.2 (unit, RED first): `decision-record-v1` carries `options` (at least two of `name`, `tradeoff`, `rejected_because`), required for ids above 0246 (0246 was accepted without it); every existing record still validates.
- AC2.3 (no test — law line): `ruling.words` carries the question and the chosen option, never only an answer id.
- AC2.4 (no test — ledger): ADR 0246 was accepted at `54c85077b`, ADR 0242 at `80012b7be`. The operator gives the words for 0243, 0244 and 0245 in the reconcile tree, in the turn the main thread writes each acceptance commit, paired with its canonical-memory hunk (ADR law §2, §3a row 2).
- AC2.5 (no test — reviewer sweep): `git grep -n found_in -- dadaia_workspace tests` returns nothing.

#### FR3 — status only in the ledger (`architecture-adr-section-generated`, Wave 1 part)

- AC3.1 (unit): The memory-lint `ADR:` exemption is deleted; `test_memory_lint.py` stays green unedited.
- AC3.2 (no test — reviewer sweep): The status token leaves the `ADR:` grammar (the label cites the id only), the ADR law's label clauses and `PILLAR-MEMORY.md`. Job 2's guard tolerates old labels; 0245's acceptance commit in the Reconciliation is the strip: the 15 status tokens leave and P-01, P-09, P-14 and P-15 point at ADR 0243. The entry stays active for Wave 4.

#### FR4 — the shipped surface is language-neutral (`public-law-language-neutral`)

- AC4.1 (no test — reviewer sweep; grep and count in the commit body): `public/` names no package path of this library, no ADR number of this repo and no Python-only tooling, except `.dadaia/.venv` and `uvx dadaia-workspace`. Each finding is deleted, rewritten, or moved to `repos/dadaia-workspace/AGENTS.md`; `scripts/pre-push-ci-gate.sh` waits for Wave 3.

#### FR5 — harness-specific surface minimized (`harness-specific-surface-minimized`)

No harness is removed: the goal is cheap switching.

- AC5.1 (reviewer sweep; integration for the registry): One law line states that common behaviour lives in skills and `AGENTS.md` and each harness gets only what it cannot do without. `entities/registry.json` stops restating `implementations`; the entity doctor derives coverage from the harness records and the hook table, and the registry names only `gaps`.

#### FR6 — a specs-revert hotfix shape (`hotfix-specs-revert-commit-shape`)

- AC6.1 (no test — reviewer sweep): `dd-gitflow-default` §3a has one row for a hotfix reverting `specs/` text: the tree, the paths, the revert message with its `block:` item.

#### FR7 — bug batch trigger and attempt cap (`bug-batch-cause-trigger-and-attempt-cap`)

- AC7.1 (no test — reviewer sweep): One line in `dd-bug-resolution`: batch on the rc window or 20 registrations, whichever first; bugs sharing a cause are fixed together (ADR 0123's home).
- AC7.2 (no test — reviewer sweep): One line: two fix attempts per bug, then a fresh session with a written diagnosis.

#### FR8 — dates come from the clock (`programmatic-dates-in-skills`)

- AC8.1 (integration, RED first): `bugs.py` and `backlog.py` reject `--ts` and stamp from the clock.
- AC8.2 (integration, pin — passes on arrival): `verdict.py`'s file-name stamp and `produced_at` are one clock read.
- AC8.3 (no test — reviewer sweep): Every other skill-written date names its source; the model-written handoff takes its stamp from a clock command.

#### FR9 — dev loop: the diet, v33, CI (`test-suite-diet`, `define-backlog-merge-runs-verify`; bugs `job-gate-red-on-untracked-bytecode`, `cross-os-ci-masks-utf8`)

- AC9.1 (no test — reviewer sweep): The closed DELETE list leaves where it still exists (PLAN §1); each commit names the check that still catches what it caught.
- AC9.2 (integration): `scripts/ci.py` keeps only the job level.
- AC9.3 (no RED — guard run): v33 is deleted (31 orphan families, all noise); `scripts/guards/run.py` and `--planted` exit 0.
- AC9.4 (unit, RED first): The bytecode assertion judges tracked files (`git ls-files`): an ignored `.pyc` under `public/` stays green, a tracked one fails.
- AC9.5 (CI): `PYTHONUTF8` and `PYTHONIOENCODING` leave `ci.yml` (six hits to zero) with every leg green; an exposed encoding defect is proposed as a bug, never re-masked (ADR 0220 P5).

#### FR10 — impacted tests as a developer read (`impacted-test-selection`; "Mapa de impacto como leitura (Recommended)")

- AC10.1 (integration, RED first): `python scripts/ci.py --changed` lists and runs the tests that import, transitively, a changed module, and names each changed file it cannot map.
- AC10.2 (no test — reviewer sweep): No gate calls it; CI keeps the full suite.

### One owner per fact (`skill-scripts-one-kernel`, ADR 0246)

Each FR deletes its group's copies; the owner's tests stay green unedited.

#### FR11 — the kernel owner, `dd-bug-resolution/scripts` (bugs `skill-git-runners-read-the-callers-git-env`, `ledger-replace-destroys-a-symlinked-ledger`)

- AC11.1 (integration, RED first): `public install` projects no shared copy: each fact module and schema exists once under `skills/`; `_SKILL_SCRIPT_SHARED`, `_SKILL_SCRIPT_SCHEMAS`, their test staging and the v37/v38 rows are deleted; `load_owner` lives in `core/skill_owner.py`.
- AC11.5 (unit, RED first): Each schema lives in its writer skill's `scripts/schemas/` (ADR 0246). Every shipped text naming a schema path names the owner path, today `scaffold/bugs/AGENTS.md:6`, `scaffold/backlog/AGENTS.md:10`, `dd-audit-project/PILLAR-BUGS.md:5`, `FINDINGS-FORMAT.md:5` and `dd-release-implementation/RELEASE-EVENTS.md:11`. A test fails when shipped text names a schema path that is neither projected nor shipped. The `.dadaia/agentic/schemas/` projection is fed from the owner paths, or deleted when nothing reads it (the PLAN measures which). The scaffold edits re-pin the unpublished `CANON_AT[12]` and `shipped-hashes.json` inside the rc's single canon bump.
- AC11.2 (unit, RED first): Two repos A and B with `GIT_DIR=B/.git` set: every skill runner and `infrastructure/git_subprocess` answer for A, through the one `git()`.
- AC11.3 (unit, RED first): A symlinked ledger is refused by the one writer, `_atomic.py` (symlink refusal, uuid temp, `preserve_mode`, the Windows retry, `ensure_parent`); `_ledger.replace` and `core/atomic_write.py` reach it through `core/skill_owner.py`; the bare `os.replace` sites in `features/workspace/service.py` and `features/spec_context/sweep.py` leave; `tests/core/test_atomic_write__atomic_write_census.py` ends with one home.
- AC11.4 (no test — reviewer `git grep` per group): One definition each for the commit loop, `_validated`, `finding()`, `histo_findings`, the JSONL reader, `serialize`, `_values`, the workspace-root walk (venv owner first), the clock, the bug ledger's status vocabulary (group A5, read from its schema), and the platform facts: `os.name` and `sys.platform` are read only in the kernel's `_platform.py`.

#### FR12 — one frontmatter grammar (bugs `frontmatter-parsers-disagree-on-crlf-and-bom`, `codex-persona-frontmatter-drops-on-crlf`)

The owner is `_frontmatter.py` in `dd-bug-resolution/scripts`, a stdlib strict subset of YAML (ADR 0246). Measured: it equalled `yaml.safe_load` on 96 of 96 real blocks with 0 silent differences over 300k mutations; `_memory_schema.parse` mismatched on 55 of 96. `core/frontmatter.py` becomes a typed shim; `pyyaml` leaves the runtime.

- AC12.1 (unit, RED first): A BOM constitution keeps its `gitflow` block; a CRLF persona keeps its fields; a folded last key has no trailing newline; `7.0.0`, `yes`, `0755` and `2026-10-11` as plain scalars equal `safe_load` or raise. The Codex and `_memory_schema` parsers leave.
- AC12.2 (unit, differential): Over every shipped and instance frontmatter, the inline frontmatter fixtures in `tests/**` and a pinned mutation corpus, the owner equals `yaml.safe_load` or refuses.
- AC12.3 (unit, RED first): Persona `read_only` and `dispatch_band` are typed (bool, int), and `install_helpers.persona_read_only` compares typed values.

#### FR13 — one slug grammar, owned by the backlog schema (bug `slug-grammar-four-patterns-disagree`)

- AC13.1 (unit, RED first): `a--b` is accepted or refused alike by backlog, the schema, `verdict.py` and the worktree name parser, all reading the one owner.

#### FR14 — the release ledger: grammars and state reader in the kernel (`_grammar.py`, `_jsonl.parse_object`), release-only rules in `_release_schema` (bugs `worktree-new-crashes-on-an-unreadable-release-state`, `release-check-admits-a-dag-that-phase-refuses`, `release-new-orphans-a-drafted-next-rc`)

- AC14.1 (integration, RED first): A missing, malformed or non-object `_RELEASE.json` refuses job admission with `Error:` and one `fix:` line; no branch or worktree; one parser, the raw read in `_worktree_new.py` deleted.
- AC14.2 (integration, RED first): A DAG that differs from its `tasks/job<n>.md` fails `release.py check` with `phase`'s message; one comparison.
- AC14.3 (unit, RED first): With rc-1 live and a drafted `rc-2/SPEC.md`, `release.py new` adopts rc-2; the closure fence reads the same decider; `test_the_closure_spares_only_the_next_candidates_define_tree` stays unedited.
- AC14.4 (no test — reviewer `git grep`): One definition each, in the kernel's `_grammar.py`, for the task-id, sha, phase and semver/candidate/tag (group A3) grammars; the skills and core read them through the owner.

#### FR15 — the gitflow owner (bugs `verify-line-shlex-mangles-windows-paths`, `doctor-misses-worktrees-of-a-repo-that-left-its-context`)

- AC15.1 (unit, RED first): On Windows `python scripts\ci.py job` runs as `['python', 'scripts\\ci.py', 'job']`; one splitter serves `verify:` and `tests:` (ADR 0220 P3).
- AC15.2 (integration, RED first): A worktree of a repo that left its context is a doctor finding with one fix line (ADR 0112); one row filter serves doctor and `ctx_inject`.
- AC15.3 (no test — reviewer `git grep`): The `_worktree_git.py:25,117` semver and tag copies are deleted and gitflow calls `_grammar`; one definition each for the worktree path, list, dirty check, verdict reader and venv CLI path.

#### FR16 — core owners (package side)

- AC16.1 (unit, RED first): A naive timestamp reads the same in `session_store` and `ctx_inject` (one rule).
- AC16.2 (no test — reviewer `git grep`): `core/platform.py` reads neither `os.name` nor `sys.platform` and delegates to the kernel's `_platform.py`; `git grep -nE "os\.name|sys\.platform" -- dadaia_workspace` hits only `_platform.py`. The context-name pattern has one definition.

#### FR17 — a refusal carries its fix (bugs `cli-refusals-print-no-fix-line`, `context-repo-refusals-carry-no-fix-line`, `context-alive-crashes-on-a-non-git-repo-dir`)

Operator: "Registrar e corrigir no Job 5 (Recommended)", "Registrar, Job 5 (Recommended)".

- AC17.1 (unit, then integration; RED first): The raised error carries its fix, as `SchemaVersionError` does (`core/exceptions.py:87-93`); `fail` prints a caller fix only when the error has none. Each measured site prints `Error:` and one `fix:` line (ADR 0073): context registry (`repo add` ×3, `repo remove`, `create`'s conflict whose `context.py:168` fix clears nothing); git failures of `alive`, `baseline`, `dead`; `import` ×3; `reports validate` ×2; `init`'s venv failure; `specs` upgrade ×2; the unresolved `specs_dir`.
- AC17.2 (integration, RED first): Adding the context's own main repo exits 0 as a no-op.
- AC17.3 (integration, RED first): `context alive` on a non-git `repos/<slug>` refuses with one `fix:` line; the installer's off-repo condition is one domain refusal every caller consumes.

### Review rework prevented (operator demand, 2026-10-12)

#### FR18 — review rework prevented in the library's own flow

Every project using the library follows it, and evals run without private memory, so each rule lives in the shipped law or skills.

- AC18.1 (integration, RED first): `worktree.py preflight <tree>` answers exactly "`merge` would pass except for the review verdict". It runs the checks `merge` runs for the tree's kind (task, job, define/backlog/reconcile, plain and hotfix each keep their own set) through one function both verbs call, so the two never disagree. It prints `PREFLIGHT PASS <tree> <sha>` (exit 0) or `PREFLIGHT FAIL <tree> <sha>` (exit 1), the latter naming each failing check with one fix line; one RED case per kind. It reports and blocks nothing. `merge` still runs its own checks; a preflight therefore costs one extra `verify:` run per reviewed sha, paid so that a red tree never reaches review.
- AC18.2 (no test — reviewer sweep): The orchestration skill dispatches a review only for a tree whose preflight passes and hands the reviewer its `PREFLIGHT PASS` line. A behaviour ruling by the main thread carries its reproduction and its consumer sweep, a search across every repo of the context. A rework brief names the finding's contract class, requires a RED test for the finding first, and requires a sweep of every other site of that class.
- AC18.3 (no test — reviewer sweep): An implementer's hand-back carries evidence per item, extending the persona's evidence line (`dadaia_workspace/public/agents/dd-sw-engineer-sr.md` §4); a bare PASS goes back before review. The items: the consumer sweep for any changed grammar, format, public name or fix line; the search behind every negative claim; cross-platform evidence (no platform literal in a new assert, a child process env copied from the parent's); other repos of the workspace are reported only as a count, never by name; old asserts kept, per the root map §1 test line and the code-review QA lens. That root map line is the one authority over a failing old test: it is a question; any edit or removal of an existing assert carries a recorded main-thread ruling in a `test(...)` commit, and a change to a product contract also needs the operator. Every other text cites that line. The code-review skill judges a re-review against the finding's class.
- AC18.4 (no test — reviewer sweep): A PLAN row that REBUILDs or DELETEs a grammar, format, public name or fix line names its consumers. A read-only `dd-researcher` pre-mortem precedes the define review and lists the consumers touched, the existing tests and asserts that would go red, and the platform facts touched; the PLAN answers each.
- AC18.5 (integration, RED first): `verdict.py stats <release-candidate>` prints the candidate's verdicts, sequences, REJECTED and first-pass rejected. It reads the verdict records through the one record lister the merge gate's verdict check also calls: the handoff zone plus the reaper's hold; a record past the hold's TTL is gone. A sequence is one tree name's verdicts up to and including an APPROVED; the next verdict on that name opens a new one, so a reopened tree never inflates the counts. REJECTED is the number of REJECTED verdicts; first-pass rejected is the sequences whose first verdict is REJECTED, divided by the sequences. The closure summary carries its output.
- AC18.6 (no test — reviewer sweep): Every development-flow rule the developer kept in private memory is either stated once in the library's law or skills, cited `path:line`, or recorded as specific to this repo's own pipeline. A parallel `dd-researcher` produces the inventory and it lands in the PLAN; no flow rule depends on private memory.

### A contract-first suite (operator demand, 2026-10-12; ADR 0248)

#### FR19 — a contract-first suite and a contract-only docstring (`tests-one-contract-one-home`, `tests-tmp-expire-at-job-merge`, `policy-tests-leave-pytest`, `review-mutation-on-the-diff`, `closure-test-suite-readouts`; `test-suite-diet` amended)

A test asserts a contract and lives in that contract's one home. Scaffolding expires at the job merge, policy lives in guards, and a deletion is proven by the kill matrix. The shipped law states the rules and the revert check. Mutation, the kill matrix and the guards are this repository's own.

- AC19.1 (no test — reviewer sweep): The root map §1 states the docstring law once: a docstring or comment states only its unit's contract (inputs, output, raises, side effects), and never a bug id, ADR, FR or AC number, task id, candidate, review round or audit id. Every other text cites that line. Agent default, unruled: comments are held to the docstring rule, because v32 already counts both.
- AC19.2 (guard: `scripts/guards/run.py` and `--planted`): v32 (`scripts/guards/slop.py:130-146`) judges `dadaia_workspace/`, `tests/` and `scripts/` at ceiling 0 for comments and docstrings. Its patterns are the governance-id grammars plus every exact id in `specs/bugs/BUGS.jsonl` and `specs/backlog/BACKLOG.json`. A planted id in a test docstring and one in a `scripts/` comment each turn it red. The ceiling drops to 0 in the same job that deletes every hit.
- AC19.3 (no test — reviewer sweep): The root map §1 test line states the bug-test rule: a fix hardens the contract test in that contract's one home. It tightens an existing assert or adds the missing partition, and never loosens one. A new case is written only when no contract test covers the partition. The reviewer's revert check confirms the hardened test goes red with the fix reverted. "fixes never rewrite old asserts" leaves that line. `dd-bug-resolution` Phase 5's "a new case in the owner file" leaves and Phase 5 cites the new line; `tests/AGENTS.md`'s one owner per module becomes one home per contract, and its seam REDs go to `tests/tmp/<job>/` (AC19.6). Outside a fix, a failing old test stays a question under that line (AC18.3).
- AC19.4 (no test — reviewer sweep): The `dd-code-review` QA lens judges a fix by AC19.3: a loosened assert, or a fix without its revert-check evidence, is HIGH. The removed-assert grep and its HIGH leave. These smells become QA-lens items in the existing SLOP rules: conditional logic in a test, assertion roulette, a mystery guest, a mock of an internal, an assert on law text, a tombstone. A mystery guest that reads a live repo file is policy and moves to a guard (AC19.9).
- AC19.5 (integration, RED first): A script under this repository's `scripts/` mutates only the lines a diff changes against a base, at most a fixed number of mutants per line. It prints each mutant with the tests that killed it (the kill matrix) and the diff's mutation score. On a planted diff with one surviving mutant, it names that mutant. Any mutation dependency sits in the dev group only; the built wheel and `public install` carry none of it (reviewer: the wheel listing). `repos/dadaia-workspace/AGENTS.md` states that a review of a diff here carries that readout and the diff's branch coverage as evidence; no gate and no test reads it as pass or fail.
- AC19.6 (integration, RED first): Scaffolding (a seam RED, a refactor pin, a bug reproduction) lives in a versioned `tests/tmp/<job>/`, collected during the job; the `.gitignore` and `norecursedirs` exclusions of `tests/tmp` leave. `worktree.py merge` of a job tree refuses with `Error:` and one `fix:` line while `tests/tmp/<job>/` exists, so each test is promoted into its contract's home or deleted. The check runs in the job kind's merge set, so `preflight` reports it too (AC18.1). A task merge and a repo without that folder are unaffected.
- AC19.7 (measurement — the AC19.5 kill matrix): Each cross-cutting contract has one parametrized home over every site, at least: the fix-line contract (about 300 tests in about 55 files over three harnesses), the ledger kernel (tested today once per consumer), and `atomic_write` (47 cases; AC11.3 names the file). A test leaves only when the kill matrix shows every mutant it killed is killed by its home; the deleting commit names that row. The kill matrix replaces the curation verdict as deletion evidence.
- AC19.8 (no test — reviewer sweep): A contract home tests at its unit's public boundary: no private name by import, `load_owner`, `monkeypatch` of an internal, AST read or `runpy`. The P-23 private-import ratchet stays and only shrinks.
- AC19.9 (guard: `scripts/guards/run.py` and `--planted`; census at closure): Every repo-policy pytest case becomes a guard in `scripts/guards`, each with its plant, or is deleted when a guard or import-linter already covers it. pytest tests behaviour only. The census reports 0 pytest cases that assert the wording of a law, skill or doc, or read a tracked repo file outside their own fixtures; the PLAN pins its command. `statement-id-cited` (`scripts/guards/suite.py:176`) and `tests/fixtures/statement_ids.json` leave. A `Measured by:` line (`scaffold/memory/AGENTS.md:22`) and an audit statement may name a guard.
- AC19.10 (no test — closure summary): The rc-14 closure summary records the suite size (functions and cases), the test/production line ratio, the 8-week churn, and the mutation score of the candidate's reviewed diffs. Each sits beside the 2026-10-12 baseline (1,393; 3,276; 1.86×; +3,406/−3,345; 62–85% on `_jsonl.py`) as a trend, never a gate.
- AC19.11 (no test — Reconciliation, ADR 0248's canonical hunks): `QUALITY.md`'s "Mutation evidence is operator tooling, outside the repo" becomes the dev-group rule; its curation line and the fixed slop-tests pruning line name the kill matrix; the v32 ratchet line names the AC19.2 scope and ceiling. `test-suite-diet`'s mutation-removal clause is reversed; its other work stands.

## 4. Exits at closure

These entries need no rc-14 work; each exits once at closure with the reason from its paragraph.

| slug | disposition | reason |
|---|---|---|
| `adr-0122-zero-backlog-destined-to-this-release` | delivered | ADR 0242 accepted at `80012b7be`; promote readouts ride `promote-gate-050` |
| `define-backlog-merge-runs-verify` | superseded | "Consertar a raiz (Recommended)": v33 deleted (FR9) |
| `job-gate-runs-the-law-deletion-check` | superseded | obsolete by ADR 0230 |
| `merge-entry-times-survive-rebase` | superseded | obsolete by `e8c2683ca` |
| `hypothesis-cache-stays-out-of-repo-trees` | superseded | obsolete by ADR 0231 |
| `task-gate-drops-deleted-paths-itself` | superseded | ADRs 0231/0232/0236; dead code deleted (FR9) |
| `architecture-principles-measured-by-re-pointed` | superseded | delivered (`75150722f`, `6c9ea5f6d`); residue in ADR 0243 |
| `fix-reader-rebuild-under-c` | superseded | obsolete by `392769e97` |
| `task-gate-declared-owner-tests` | superseded | ADRs 0231/0232/0236 |
| `pr-merge-method-pinned` | superseded | delivered: `allow_rebase_merge` false |
| `phase-implementation-has-a-place` | superseded | delivered (`2a8b5637f`) |
| `stage-gate-keeps-only-the-red-check` | superseded | ADRs 0231/0232/0236 |
| `verdict-author-unbound` | superseded | "Disciplina + auditoria (Recommended)"; ADR 0218 |
| `judge-config-outside-the-script-dir` | superseded | 2026-10-08 "Apagar; o revisor cobre (Recommended)" |
| `gate-reuses-a-green-result-for-the-same-tree` | superseded | 2026-10-08 "somente job e tasks são suficientes" |
| `process-proportional-to-change-size` | superseded | 2026-10-08 "devemos ser por default leves", "Worktree livre" |
| `bug-status-deferred-banned` | superseded | delivered (ADRs 0223/0227) |
| `quality-scorecard-ruler` | superseded | the score-9 ruling, ADR 0239 |
| `task-lines-carry-seam-and-adr-clause` | superseded | job file slimmed (2026-10-08 questions 12, 15) |

The entries with work exit `delivered`, except `architecture-adr-section-generated`, carried past rc-14: it stays active for its Wave 4 triage and generated section. `law-one-home-residual`: (a) by FR2, its location clause dropped; (b) and (c) carried by the Wave 4 triage. `tests-one-contract-one-home`, `tests-tmp-expire-at-job-merge`, `policy-tests-leave-pytest`, `review-mutation-on-the-diff` and `closure-test-suite-readouts` are absorbed by FR19 and exit `delivered`. `test-suite-diet` exits `delivered` too, with its mutation-removal clause reversed by ADR 0248 (AC19.11).

## 5. Not in rc-14

- **Wave 3:** the D–F functions of `cli/` and `features/`; `spec-context-branch-field-deleted`, `worktree-layout-per-context`, `context-dead-snapshots-open-worktrees`, `context-show-derives-worktrees`, `export-soft-and-hard`, `init-from-export`, `multi-platform-by-construction-migration` (its two bugs are FR15 and FR9 here), `bug-stats-hotspots-and-age`, `audit-project-scorecard-cycle`, `repo-ci-sast-gates`.
- **Wave 4:** `architecture-adr-section-generated` (triage, generated section, ADR 0193's `amends`), `docs-site-zensical-pages`, `launch-operator-acts`, `eval-codex-lane-in-library-ci`, `promote-gate-050` (050 checks, D1–D10, findings, rc-13 residuals).
- **Not destined** (ADR 0242): `evals-benchmark-lanes`, `release-approve-requires-evals-gate`, `windows-smoke-t1-at-release`.
- **Operator item, not FR18:** proposed: two or three closed options, never padded; needs an amendment of ADR 0165 by the operator. FR18 leaves the grill's "3 closed options" rule (ADR 0165, accepted) as it is.
- **Left out:** the `dd-ask-me` rename; the `behavior-map.json` deletion (unruled); gate-side test selection.

## 6. Constraints and risks

### Replaces

- Projected copies of shared modules and schemas, their copy tables and allowance rows, become one owner per fact, loaded by core (FR11, ADR 0246).
- Every second decider of a fact leaves (FR11 to FR16).
- Per-site remedies become an error that carries its fix; the own-main refusal becomes a no-op (FR17).
- A review dispatched on an unchecked hand-off, an uncited ruling, a site-only rework brief and a bare PASS hand-back become a passing preflight line, a reproduced and swept ruling, a class-wide rework and per-item evidence (FR18).
- "Fixes never rewrite old asserts" and "the regression is a new case" become a fix that hardens the contract test in its one home, proven by the revert check (FR19, ADR 0248 amends 0166).
- The QA lens's HIGH on a removed assert in a fix becomes a HIGH on a loosened assert or a missing revert check (AC19.4).
- The local, ignored, uncollected `tests/tmp` becomes a versioned `tests/tmp/<job>/` that the job merge refuses while it exists (AC19.6).
- The per-module retest of a cross-cutting contract becomes one parametrized home, each deletion proven by the kill matrix (AC19.7).
- Mutation as operator tooling outside the repo becomes a diff-scoped script in this repository's dev group, never shipped (AC19.5).
- `statement-id-cited` and `tests/fixtures/statement_ids.json` leave; a `Measured by:` line or an audit statement may name a guard (AC19.9).
- Policy cases in pytest become guards in `scripts/guards`, or leave when a guard already covers them (AC19.9).
- The grill handoff as record, any decision as an ADR, id-only rulings, the `ADR:` status token, shipped library facts, `--ts`, v33, `ci.py` task and stage code, the working-tree bytecode check, the CI UTF-8 masks and hand-written registry `implementations` leave (FR1 to FR9).

### Governance sequencing

1. ADR 0246 is accepted (`54c85077b`, amends 0135). Under rule M2 the main thread sets the fields of the others at acceptance: 0244 supersedes 0205 and amends 0187; 0245 amends 0165.
2. One rule: the operator gives the words for 0243, 0244 and 0245 in the reconcile tree, in the turn of each acceptance commit, paired with its canonical-memory hunk; 0245's hunk is the label strip.

### Delivery constraints

- Bugs law §2: Job 1 executes the REBUILD rows; the PLAN reconciles that with the owner DAG.
- Tidy First: an owner moves before its behaviour changes; every bug fix lands its RED test first.
- One canon bump across the law and kernel jobs; shipped law reaches this instance only by projection.
- FR18 is public and language-neutral: it never requires CI, a remote, a PR host or a vendor CLI, adds no lock and no gate, and states each rule once.
- FR19's shipped part is the docstring law, the bug-test rule and the revert check, all language-neutral. Nothing in FR19 requires a user's repo to have CI, a remote, a vendor CLI or a language toolchain; the `tests/tmp/<job>/` merge refusal acts only where that folder exists. Mutation, the kill matrix and the guards are this repository's own.

### Risks

| risk | control |
|---|---|
| The frontmatter subset refuses a shape users write | it fails closed with a refusal, never a silent difference (AC12.2) |
| Five skills depend on `dd-bug-resolution` | ADR 0246 accepts it; projection always ships it |
| Unmasked CI legs expose encoding defects | each proposed as a bug, never re-masked |
| The 1.2× ratio pushes a real contract test out | a test leaves only on its kill-matrix row (AC19.7) |

## 7. Open questions

None.
