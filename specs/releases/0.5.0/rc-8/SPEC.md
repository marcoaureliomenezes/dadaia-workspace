# SPEC — Release: 0.5.0, candidate 8 (W8: the test law and the library pipeline leave; W9: bug lineage derived; W10: the open bugs; W11: agent-behavior evals, a parallel lane; W12: the bug loop stops; W13: the bug strategy)

**Status:** In review
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-10-03
**Origin:** backlog:agent-behavior-evals,cli-ships-no-library-pipeline,lib-test-guidance-dehydrated,tests-agents-scaffold-without-placeholders,test-intent-docstring-backfill,meta-tests-leave-pytest,preflight-ci-parity-derived,delete-text-count-inventory-asserts,adr-0143-measured-by-checks-the-concept,skill-md-soft-hard-line-limit,memory-update-states-the-truth-correction-lane,bug-fix-adds-never-rewrites-asserts,bug-fix-commit-derived-by-grep,caused-by-proposed-by-blame,focused-review-on-caused-by,bug-terminal-transition-commit-shape,architecture-survey-flat-core-infrastructure,doctor-context-ignores-other-contexts,guidance-messages-name-the-right-target,worktree-memory-states-plain-ledger-merge; bugs:test-suite-writes-outside-tmp,ci-preflight-writes-coverage-into-the-repo,hook-entrypoints-invisible-to-coverage,onboarding-next-step-names-another-context,init-on-a-copied-workspace-leaves-a-cli-bound-to-the-original,registry-row-missing-a-key-escapes-reg-schema,pre-push-warns-no-gitflow-block-for-an-absent-specs-tree,upgrade-leaves-reconcile-scratch-behind,bug-surface-schema-documents-the-deleted-regex,release-memory-appends-a-second-entry-on-rerun; findings:20260930-structural-convergence-F003,20260930-structural-convergence-F018,20260930-structural-convergence-F028,20260930-structural-convergence-F043,20260930-structural-convergence-F044,20260930-structural-convergence-F045,20260930-structural-convergence-F047,20260930-structural-convergence-F048,20260930-structural-convergence-F049,20260930-structural-convergence-F050,20260930-structural-convergence-F051,20260930-structural-convergence-F096,20260930-structural-convergence-F097,20260930-structural-convergence-F098,20260930-structural-convergence-F100,20260930-structural-convergence-F101,20260930-structural-convergence-F104,20260930-structural-convergence-F112,20260930-structural-convergence-F128,20260930-structural-convergence-F129,20260930-structural-convergence-F131,20260930-structural-convergence-F135,20260930-structural-convergence-F136

- Sources: grills of 2026-10-02 (rc-8, Q1–Q4) and 2026-10-03 (train, Q1–Q6); reviews B1–B11, H1–L6 on fb8a29a75, then re-review 2 on 196f611aa; PR #278 F1; for W11, the grills and draft its Origin names. Task ids start at T-050-153.
- Amendment 2026-10-04 (W12): grill `.dadaia/handoff/dadaia-workspace/2026-10-04T190000Z-main-thread-grill-fix-induced-bugs.handoff.json`, and the read-only audit at 76d7af604 (18 unregistered fix-induced breaks; surface verdicts). Operator words, verbatim (AskUserQuestion):
  - Q1 "Sempre bug, com caused_by (Recommended)". Q2 "Para e refaz a anterior (Recommended)". Q3 "Registrar + auditar 2 superfícies (Recommended)".
  - Q4 "Um comando = o CI Linux (Recommended)". Q5 "Auditoria → emenda rc-8 → script → REBUILDs (Recommended)".
  - Q6 "1. Merge roda o CI-local", "2. Hook: vermelho → só revert ou bug", "3. Hook: protege asserts".
  - Q7 "Sim, nunca reescreve (Recommended)". Q8 "Aceitar 0172, fazer no rc-8 (Recommended)". Q9 "Schema aceita task, depois 18 (Recommended)".
  - Q10, a free-text demand (handoff finding 10): audit the instruction corpus with a private command. Q11 "Aprovar como desenhado (Recommended)".
  - Q12 "rc-8 nos arquivos que ele já toca; resto no rc-10 (Recommended)". Q13 "Motivo curto só nas proibições (Recommended)". Q14 "Positivo por padrão; proibição só com falha real (Recommended)".
  - Q15 "Merge na lib; hooks 2 e 3 privados (Recommended)". Q16 "Recusa com fix: declarar (Recommended)". Q17 "Reescrever (Recommended)" (a private rule, outside the library).
  - Q18 "Prospectivo + exceções (Recommended)". Q19 "Manter a 0168 (Recommended)". Q20 "Shape refactor(T-NNN): REBUILD (Recommended)".
  - Q21 "Parada até os REBUILDs (Recommended)". Q22 "Auditar sweep + registrar o guard (Recommended)"; its read-only `sweep.py` audit fed Q23–Q25.
  - Q23 "REBUILD U1+U2 no rc-8 (Recommended)". Q24 "Registrar os 7 + corrigir (Recommended)". Q25 "Restringir (Recommended)". Q26 "Apagar o skip de refactor (Recommended)".
  - Earlier, for the `-B` provider probe (AC10.1): "Part of 169 (Recommended)".
  - Main thread, 2026-10-04: ff5245e08 gets its own retro record (AC12.4 row 19); Q13, the newer ruling, amends `AUTHORING.md` rule 9 here (AC12.11).
  - Answered via inspection, from Q18 and the root map's "fixes never rewrite old asserts": T-050-168's REBUILD (AC12.9) covers rows 10 and 12; row 11's repair is kept.
  - Answered via inspection, from Q1, Q2 and Q20: the REBUILD mechanics of AC12.2 and AC12.12; `bugs.py fix` and blame read the `refactor(bugs)` shape like shape 3.
  - Answered via inspection, from the bugs law §1: the operator's approval of this SPEC confirms AC12.4 row 19.
  - Answered via inspection, from Q18 and the rows 10 and 12 precedent: row 6 stays open until AC12.13, which reverts b9b28202d's OSError arm; its diagnosis was never reproduced on CI's 3.12 (audit F-QA-1).
- Amendment 2026-10-05 (W13): grill `.dadaia/handoff/dadaia-workspace/2026-10-05T005326Z-main-thread-grill-bug-window-review.handoff.json`, G1–G9, after the report https://claude.ai/artifact/AZMbDAsMvqBYPqbXd5WgZx (IBM DPP causal analysis per stage; ODC v5.2 opener/closer; ImpossibleBench; the Debugging Decay Index; Böckeler on TDD in the agent loop; Hashimoto's "engineer the mistake away"). Ledger scan 2026-10-05: 742 records; 537 product defects, 15 agent errors, 89 born in the release, 66 library dev-tooling, 35 doubtful. Operator words, verbatim (AskUserQuestion):
  - G1 "quando o bug foi identificado. e 2. quando a implementação que gerou o bug ocorreu. acredito que seja achado e nascido."
  - G2 "Ao encontrar um bug se ele barrar o avanço se resolve na hora. Se ele não barra o avanço se coloca ele na pilha para ser resolvido ao final da release"; "consertado se ele foi gerado durante a implementação do proprio RC ou se ele impede ou bloqueia ações"; "Lista fechada (Recommended)"; "onda final, opção 1".
  - G3 "Bugs (historico) sempre revisado na criação da primeira spec de 1 rc. mesmo bugs resolvidos. A janela olha bugs da release atual (gerados na release atual, todos os release candidates) e bugs de todos release candidates da versão anterior. Esse audit é permanente e anda como uma janela."; "Só por rc (Recommended)"; "Seção no SPEC + congela 199–208 (Recommended)".
  - G4 "Já no rc-8 (Recommended)"; "Reclassificar por classe (Recommended)".
  - G5 "dado que praticamos TDD os testes gerados pelo TDD devem ser rastreaveis"; "Nosso maior problema em fixes e bugs, é o overfitting"; "No registro do bug, conferido (Recommended)".
  - G6 "deveriamos ter gerado uma ADR, que tem um limiar muito mais alto"; "Por ADR que aposentou a superfície (Recommended)".
  - G7 "se o agente tentou fazer algo e deu erro, ou ele criou um teste e não passou é um erro dele, não é um bug do workspace".
  - G8 "Bugs devem ser consolidados em QUALITY.md"; "o ledger é as transações e o saldo (balance) é a soma"; "Mapa gerado + revisão escrita"; "Revisão a cada rc, consolidação por release (Recommended)".
  - G9 "é isso mesmo" (the merge as the boundary; the `bug` kind follows the pile). Summary: "Confirmo (Recommended)".
  - G10 "Conferido no resolve (Recommended)". G11 "Vai para a pilha (Recommended)". G12 "Voltam e são rearquivados por ADR (Recommended)".
  - G10 moved to rc-9 with AC13.5. Scope ruling (AskUserQuestion, 2026-10-05): "Dividir: balanço vai p/ rc-9 (Recommended)".
  - New demand for rc-9 (2026-10-05): "na consolidação do QUALITY.md … Deve ter um indicador ao final que mede uma taxa de se estamos convergindo ou não. Convergir significará estarmos tornando o dadaia-workspace mais saudavel, ou seja, bugs de features amadurecidas para de ser reportados e solução fica segura." On the W11 evals: "Eles serão de grande ajuda na identificação dos bugs."
  - Answered via inspection (main thread): the review names the retired bind/session-TTL surfaces, and their retroactive ADR cites only those; a record counts in the bug window by `found_in` or `introduced_in`; "born in the running rc" is judged at triage from the culprit the proposal names; the heading is `## Bug window review`; block-list item 4 reads "an open dependency-vulnerability alert".
- Bug history read (permanent architecture review): PLAN §1, the as-is review; for W12, the audit above; for W13, the 2026-10-05 ledger scan.
- Left out: `dependabot-pyjwt-open-on-main`, closing at the ship (rc-12); `removals-shipped-without-recorded-authority`, rejected (Q5).

## Objective

- The library ships no pipeline of its own: `ci preflight` and the pytest bootstrap leave first (Q2).
- Test knowledge leaves the library (0166); meta-tests leave pytest for one CI job; tests assert behaviour (0163, 0167).
- Bug lineage is derived from git, and a bug fix adds a case (0163, 0164). SKILL.md gets one size law (0170).
- The open bugs are fixed; production and tests end smaller (§G1).
- Agent behaviour is measured on the shipped wheel, from the associated repo `dadaia-evals`, beside W8–W10 (W11; 0177–0179).
- A fix that breeds a bug is reverted and redone, never patched forward; a worktree merge lands only a verified, unrewritten HEAD (W12).
- A bug that blocks nothing waits in the rc's pile and is fixed with its cause group; every rc opens with a review of the bug window; a record leaves the ledger only by an accepted ADR (W13).

## Terms

- `CONTEXT.md` holds the terms. **W8**–**W12** are this candidate; **DEL** and **FR** keep rc-5's meaning.
- **Meta-test**: a test whose subject is the suite or the repository (files outside the package, CI, ledgers), not a package module or shipped asset.
- **Guard script**: a meta-test's unique check, moved into a script the one CI job runs.
- **Fix-induced bug**: a break an already-merged fix caused; its `caused_by` names that fix's bug or task.
- **Owner file**: the one test file owning a module's behaviour; a RED enters it as a new case (0146 (5)).
- **Behaviour assert**: an assert on an exit code, an effect, or a stable id (finding code, slug, flag); a sentence, roster, or count with a source of truth is not one.
- **Evals repo**: AC11.1's `CONTEXT.md` entry. `eval.yml` is a workflow in that file's one sense.
- **Bug window**, **Pile**, **Block list**, **Cause group**: AC13.11's `CONTEXT.md` entries; **Wave** keeps its sense. "Window" is always qualified: bug window, lineage window (`LINEAGE.md`), drift window (memory).
- SCAFFOLD here is the test tier (V28), never the specs scaffold. Bare `preflight` is a homonym: `ctx_inject`'s generic preflight, `_dead_preflight` and `_ownership_preflight` stay.

## Decisions

- These ADRs decide: 0071 (amended by 0163), 0104, 0118, 0119, 0122, 0123, 0138, 0140, 0142, 0143 (amended by 0166, 0170), 0146 (5), 0149, 0152 (2), 0158, 0160 (amended by 0164), 0162, 0163, 0164 (amended by 0183), 0166, 0167 (partly; the rest is rc-9's), 0170.
- One new ADR: 0176 (proposed), AC8.10. The operator accepts it in the release worktree, in the commit carrying the nine `### P-NN` hunks (`specs/ADRs/AGENTS.md` §3); `amends: 0167` is written then (0151 M2). 0143's repair and AC8.10's repairs take the 0138 lane.
- 0181 (accepted 2026-10-03 at 1e1e9eee9; operator, "One ADR for rc-8's W8 law deletions (Recommended)") names every law line W8–W10 deletes or rewrites; every commit of this candidate deleting a law line cites it (0151 M3), T-050-183's cite 0177 and T-050-189's 0180. The operator accepts it before T-050-154's push.
- Operator, 2026-10-03, verbatim:
  - Train: "you will only create now the RC8 ... we will wait till we finish the RC8"; rc-9..rc-12 are §Carried.
  - Q1 "Keep in 0.5.0 as rc-11 (Recommended)". Q2 "Yes, into rc-8 (Recommended)".
  - Q3 "Register as bugs, fix in rc-8 W10 (Recommended)"; re-ruled for `init-announces-codex-trust`: "Not a bug: reject the entry (Recommended)".
  - Q4 "Derive it from `bugs.py fix` (Recommended)". Q5 "Reject; authority table goes to rc-12 notes (Recommended)". Q6 "rc-10 via dd-ask-me (Recommended)".
  - Amendment: "Amend AC8.9, delete them (Recommended)" (AC8.9's second deletion list); "Use the native tools (Recommended)" (AC8.10's P-07 and P-28).
  - Amendment (AskUserQuestion): "Add to rc-8 (Recommended)" (backlog `worktree-memory-states-plain-ledger-merge` joins the Origin, AC10.14); "Land eval.yml on main early (Recommended)" (AC11.5, AC11.6).
  - Amendment (AskUserQuestion, 2026-10-04): "Run pytest with -B (Recommended)" (AC10.1).
  - Amendment (AskUserQuestion, 2026-10-04): "Global test setup (Recommended)" (AC10.1; T-050-169 uses `tests/conftest.py`'s session env, not a per-test env builder).
- Order (root map §1): AC8.9; the rest of W8; W9; W10, after AC9.3 and AC8.1's `Intent:` strip. Width: the PLAN's Parallel schedule (0149). From 2026-10-04, W12's order (Q5) governs every open task; from 2026-10-05, W13's Order runs inside W12's step 2, after T-050-192 and before T-050-199 (AC12.4); W12's steps 3–4 follow AC13.4's verdict.
- W12 (amendment 2026-10-04): two new ADRs, proposed in the release worktree: the merge ADR (AC12.5, AC12.7; its ruling Q6, Q7, Q15, Q16 and Q19's words; 0168 cited as standing) and the bug-loop law ADR (AC9.3's Q26 line, AC12.1–AC12.3, AC12.6's reviewer line, AC12.11, AC12.12; its ruling Q1, Q2, Q9, Q12–Q14, Q18, Q20 and Q26's words; it cites 0164 (2), whose skip set Q26 amends after 0183, and 0164 (3) as amended). 0172 is ruled by Q8's words (AC12.8). The main thread writes every acceptance.
- W13 (amendment 2026-10-05): candidate ADRs; the main thread proposes and accepts each with the operator's words; nothing here touches `decisions.jsonl`:
  - A, "Per-rc bug window and pile" (G2, G3, G4, G7, G9, G11): the block list; the pile and its cause groups, harm-ordered and re-evaluated after each (0123); a cause needing more than one task becomes an ADR and a next-rc AC ("more than one task" is the main thread's reading of the redesign clause, for the operator to accept); window membership by `found_in` or `introduced_in`; the window review opening every rc's first SPEC; the merge as the boundary; the `bug` kind; a block-list fix opens at once and pauses the overlapping task; the per-class shape-4 subject. Amends 0019 ("a confirmed bug is still fixed at once"), 0149 (3) and 0186 (2); implements 0123; cites 0136, 0185. `measured_by`: every `fix(bugs)` body carries `block:`, `born-in-rc:` or `cause:` (a `git log --grep '^fix(bugs)'` readout), and AC13.2's and AC13.3's checks. Accept point: before T-050-194 merges.
  - B, "The bug record's lineage and lifecycle" (G1, G6, G12): `found_in`, `introduced_in` and `resolved_release` from one instant → candidate function; a record leaves the ledger only by an accepted ADR; the age archive deleted; the restore as its one-time writer exception. `measured_by`: AC13.1's and AC13.6's cases. Accept point: before AC13.1's task merges.
  - Retroactive (G6, G12): one per retired surface AC13.4 names (ENGINE/headless workflows; the named bind/session-TTL surfaces), each accepted before its `archive --adr` runs.
  - C (the `QUALITY.md` balance) moves to rc-9 with AC13.5, AC13.9 and AC13.10.
  - Every W13 commit deleting a law line cites A or B once accepted (0151 M3).
- W11 (amendment, operator 2026-10-03, AskUserQuestion, verbatim):
  - Fold (grill 170932Z): "fold into rc-8. make sure to define that it can surely be implemented in parallel ... because it's on other repo".
  - Q-W0: "Yes, only that slice (Recommended)". AC11.0 carries only "an associated repo's impl reads the main repo's Approved trio" of proposed 0174; the rest stays rc-11's.
  - 0179: "Accept as prepared (Recommended)".
- Accept points of 0176, 0177, 0179 and 0180: PLAN R7–R10. 0178 (`amends: 0122`) is accepted at closure, since it governs rc-12's promote.

## Gate — G1–G6, applied to W8–W10, W12 and W13

- G1 Principles, never a line-count limit (0142):
  - DELETE → REBUILD → UPDATE → KEEP → ADD; an ADD names what it could not delete. No question gets a second decider.
  - Readout, `<start>`/`<end>`: production lines `git ls-files -z 'dadaia_workspace/*.py' | xargs -0 cat | wc -l`; test functions `git grep -hE '^\s*(async\s+)?def test_' -- 'tests/*.py' | wc -l`; test lines `git ls-files -z 'tests/*.py' | xargs -0 cat | wc -l`; guard-script lines and checks over the PLAN's glob for them.
  - At birth (8f4ed785f): 25,307 / 1,233 / 45,464 / 0 / 0.
  - Production: rc-7 planned −160, measured +342 (PR #278 F1); rc-8 carries the 502-line miss and ends at or below 24,805, its ADDs counted; the PLAN names the DELETE rows, AC8.9 the largest.
  - Tests, guard scripts counted in (the c4 target): functions plus guard checks ≤ 1,167; test lines plus guard-script lines ≤ 43,232.
- G2 `bugs.py status` lists no open record whose `caused_by` names a W8–W13 bug or task.
- G3 Each open bug is re-run at `<end>`; one not reproducing is resolved, citing the commit that removed its cause.
- G4 CI green on the three OSes; `.dadaia/.venv/bin/dadaia doctor --context dadaia-workspace` exits 0. Wall-clock vs rc-7: one runner class, the median. The guard-script job is the only job added.
- G5 A test a DEL leaves dead leaves in the same commit. A new test follows the root-map test basics (AC8.1).
- G6 At closure, findings and `active[]` are re-audited; rc-9 is defined from §Carried; one `dispositions` entry logs open before, resolved, open after. Closure never waits on a ruling: a task still pending on an operator accept at closure (T-050-183, T-050-187, T-050-188 on 0177's; T-050-189 on 0180's) leaves T-050-181's `blocked by:` once §Carried rc-9 records it.

## W8 — the test law and the library pipeline leave: acceptance

- AC8.9 (first) The CLI ships no library pipeline (FR `cli-ships-no-library-pipeline`; supersedes FR `preflight-ci-parity-derived`, F104):
  - Deleted: the `preflight` verb and its imports in `cli/commands/ci.py` (group help reworded); `features/ci_preflight/`; `CiPreflightScopeError`; `container.is_source_repo_root`; `subprocess_runner_for_ci`; `_ensure_ci_toolchain`. `workspace_guardrail._is_source_repo_root` stays (`public_assets` guards `public install`).
  - With them: `setup.cfg` `features.ci_preflight`, `docs/cli.md`, `docs/getting-started.md`, `tests/conftest.py:436`, `tests/contract/README.md`, `test_preflight_doctor_scope.py`, `test_cli_ci.py`'s preflight cases, and every other line the grep below names; the preflight lines of `dd-gitflow-default/SKILL.md`, `RC-FLOW.md`, and, beyond the grep, `dadaia-AGENTS.md:14`, `tests/AGENTS.md:39`, `setup.cfg:59`, `pyproject.toml:99`, `core/workspace_resolver.py:26`, `test_cli_help_quality.py`'s case.
  - `ci push-gate-check` and `ci install-hook` (the pre-push chokepoint) stay; their cases (`test_cli_ci.py:62`, `test_push_gate_check.py:86`) stay green, no new test.
  - `code` anchors resolve any tracked path, the symbol optional. The `cli` anchor kind, `REPO_TREE_ARTIFACTS` reaping (and its consumers `privacy_check._PUBLIC_ASSET_IGNORED_DIRS`, `REPO_TREE_EXCLUDED`), `venv_guard`'s tool names and `_memory_drift`'s extension list turn language-neutral or leave (as-is review; deletion preferred). `public/scaffold/backlog/AGENTS.md` §4.1's `code` and `cli` rows and "no Python sources" bullet are rewritten.
  - Also deleted, for G1 (no backlog or histo record binds `api`; ledger: `sa-subjects-resolve-is-circular`, `backlog-doctor-default-alias-map-unresolved-from-repo-subdir`, `backlog-subjects-readme-uses-unsupported-positional-resolve`, `backlog-subject-registry-lacks-top-level-doctor-cli-anchor`):
    - the `api` anchor kind and its alias map: `subject_registry.py:80-107,330-348`, `SubjectKind.API`, the `api` of the backlog schema enum and `_backlog_write._KINDS`, `STATES_CANON`'s `backlog_subject_aliases.txt`;
    - `doctor --alias-map` and `--source-root` with their threading (`cli/commands/doctor.py:104-105,278-287,320,335,356-357`, `build_context`, `build_registry`); `cli/_backlog_roots.py` leaves whole. `code` anchors come from the repo's tracked paths through the process adapter;
    - `backlog.py subjects` (`backlog.py:93-101` and its wiring; `_backlog_write`'s kind refusal stops naming it);
    - SPEC-DOC-005: `PLAN_MAX_LINES`, `features/specs/doctor_release.py:33,108-128`, `rules.py:69-74` (0143, 0152 (2)).
  - With them: `public/scaffold/backlog/AGENTS.md` §4.1's `api` row and `subjects` bullet, `dd-backlog-definition/SKILL.md:62`, `CONSUMER_VALIDATION_RECIPE.md:37`, the `--source-root .` of `.github/workflows/ci.yml:345` and `docs/getting-started.md:113`, `tests/contract/README.md:91`, and the cases the grep below names. `test_backlog_definition_backlog_script.py:493`'s `panel` refusal (B4) stays, gaining an `api` row. The memory pass rewrites `backlog-ledger.md:30,41` and `workspace-doctor.md:28-29,56`; `QUALITY.md:71` is AC8.10's.
  - `TOOL_CACHE_ENV` stays (0080), language-neutral; the no-cache-in-tree case `test_tool_caches_stay_in_the_tmp_zone.py` stays green and gains a `pytest` parametrize row, not a new test.
  - This repo's `AGENTS.md` gains a line installing the `dev` group into the workspace venv; its CI equivalent lives there and in `.github/`.
  - Command: `git grep -niE 'ci.?preflight|CiPreflight|_ensure_ci_toolchain|subprocess_runner_for_ci|[^_]is_source_repo_root|alias.?map|backlog_subject_aliases|SubjectKind\.API|kind=api|"code", "api"|py subjects|SCRIPT\} subjects|"subjects":|--source-root|source_root[:=]|"source_root"|SPEC-DOC-005|PLAN_MAX_LINES|check_plan_line_limit' -- . ':!specs' ':!CHANGELOG.md'` prints nothing; `.dadaia/.venv/bin/dadaia ci preflight`, `.dadaia/.venv/bin/dadaia doctor --source-root .` and `backlog.py subjects` exit 2.
  - Case: `test_python_env.py:85-93` asserts no `pytest` install; CI's `dev`-group install proves the line; no new venv.
  - Case: a backlog `code` anchor to a `.go` file passes BL-SCHEMA.
  - At closure, `preflight-ci-parity-derived` exits `superseded --release 0.5.0`; the memory pass deletes the `ci-preflight` atom.
- AC8.1 Test knowledge leaves the library (FR `lib-test-guidance-dehydrated`; 0166; F112, F101):
  - Deleted: `public/skills/dd-test-stewardship/`, `public/templates/tests-AGENTS.md` and their wiring (persona `skills:`, `behavior-map.json` rows, `workspace_layout.REPO_LAW`, `canon.py`, the onboarding list, `doctor_memory.py`, CONTEXT-MAP rows, the tests pinning them).
  - The `Intent:` convention leaves with V28, V29 and V31 (this AC owns them) and every docstring `Intent:` line.
  - The root map gains the test basics by rewriting existing bullets: RED before the fix, at the lowest level; behaviour, not text; mock only at the boundary; a literal expected value; a fix commit never rewrites an old assert. `slop-tests.md`, the QUALITY scaffold and the personas point at them.
  - Command (0166's `measured_by`): `grep -rn 'dd-test-stewardship\|tests-AGENTS\|Intent:' dadaia_workspace/public` prints nothing, and `.dadaia/.venv/bin/dadaia public doctor` is clean; `git grep -n 'Intent:' -- tests` prints nothing.
  - At closure, `tests-agents-scaffold-without-placeholders` and `test-intent-docstring-backfill` exit `superseded --release 0.5.0`.
- AC8.2 One answer for canonical memory at closure (FR `memory-update-states-the-truth-correction-lane`; 0138): `MEMORY-UPDATE.md` states no canonical-memory rule of its own and points at the memory law (a `### P-NN` changes only with its ADR, any other section under 0138); its step 7 names no library-internal test. Command: `grep -c 'QUALITY.md' dadaia_workspace/public/skills/dd-release-implementation/MEMORY-UPDATE.md` prints `1`; `grep -rn 'never touched at closure' dadaia_workspace/public` prints nothing.
- AC8.3 Meta-tests leave pytest for one CI job (FR `meta-tests-leave-pytest`; 0163, 0166, 0167):
  - Deleted as duplicates: `stewardship_mechanics` beyond AC8.10's checks (conftest); `repo_self_scan` (gitleaks, pre-push); `test_adr_canon`'s committed-ledger case (the CI doctor job). V28, V29, V31: AC8.1.
  - `source_repo_hygiene` splits (T-050-155 review F1; the CI repo-hygiene job checks only tracked projection files; the `gitignore-…-recurrence` chain, 10 bugs):
    - Visibility rows: moved to guard check `specs-canon-tracked` (T-050-161, `repo.py`), derived from the canon, never a hand-kept list (`additive-globs-hand-kept-beside-the-canon`):
      - Probes: one path per row of `canon.py`'s `CANON`, its `dest` or a sample its `pattern` matches, each judged by `git check-ignore --no-index` (plain `check-ignore` passes any tracked path).
      - Expected not ignored, except a row where rendering its `TEMPLATES` source through `workspace_layout.render_registry_tables` changes it: that row is expected ignored. Today that is `AGENTS.md` alone (`.gitignore:132`); whether it gets tracked is backlog `doctor-in-a-fresh-worktree-lacks-rendered-specs-law`'s.
      - The ignored half, kept from F-20: `releases/_archive/<v>/local-notes.md` and `releases/_archive/<v>/tmp/<f>` are ignored. `release.py ship` renames the live directory with its untracked files (`release.py:124`), and nothing refuses them.
      - Planted: a temp `.gitignore` hiding `specs/releases/**/TASKS.md`, and one re-including `_archive/**/local-notes.md`, each turn it red.
    - Hidden rows elsewhere (`local-notes.md`, `tmp/`): the canon scan's, `canon_violations` (`features/specs/canon.py:172`) at pre-push (`push_gate.py:216-232`) and doctor (`canon.py:194-206`).
    - Stale rows (`ACTIVE.md`, `GRILL.md`, `OQ-DECISIONS.md`, `ALPHA-*-QA.md`, `PRE-PR-REVIEW.md`, `reviews/`, `specs/_archive/releases/`, `backlog/candidates.md`): dropped; the canon refuses those paths.
  - Deleted: the mutation tooling (`tests/scripts/run_mutation_baseline.sh`, its wiring tests, `test_mutation_baseline_scope_stdlib_only.py`, `[tool.mutmut]`, the `mutation` group); the memory pass states mutation evidence is operator tooling.
  - Moved to guard checks, each red on a planted violation: V26 (`test_test_suite_ratchets.py`); V32, V33, V37–V40 (`test_slop_ratchets.py`; V32's twin in `test_import_linter_ignore_cap.py`); `suite_cannot_reach_a_real_workspace`, `suite_cannot_reach_the_instance`; `test_ci_workflow_hygiene.py`, `test_memory_canonical_shape.py`; `test_release_semver_canon`'s release-please cases and `test_version_lineage_consistency.py` (P-30's check); `test_adr_canon`'s superseded-successor case; AC8.6's check; `test_frozen_clock_aging_ratchet.py` and `test_harness_env_contract.py` (the suite is their subject; no principle names either; 0020 is repaired, AC8.10).
  - Not meta-tests (package subject): `test_core_file_io_purity` (package AST), `test_behavior_map` (shipped `behavior-map.json`), `test_public_source_hygiene` (shipped text, wheel), `test_console_scripts` (the shipped entry-point table), `test_release_semver_canon`'s id-grammar case; `test_law_states_what_the_code_does` is AC8.4's. `test_docs_derived_from_memory.py` stays until rc-12 (AC8.10).
  - The as-is review may add files, never remove one; no unique guard is lost; the parity check dies with preflight.
  - Command: `git ls-files tests | grep -E 'suite_cannot_reach|stewardship_mechanics|repo_self_scan|source_repo_hygiene|test_suite_ratchets|mutation_baseline|slop_ratchets|import_linter_ignore_cap|preflight|ci_workflow_hygiene|memory_canonical_shape|version_lineage|frozen_clock_aging|harness_env_contract'` prints nothing; the CI job's log names each moved guard.
  - At closure, `meta-tests-leave-pytest` stays active: `test_docs_derived_from_memory.py` is its one leftover (AC8.10), so its done-when is unmet.
- AC8.10 Every principle whose test leaves pytest keeps a check (0176):
  - QUALITY P-21 `tier-timeout`, P-22 `quarantine-needs-bug`, P-23 `private-import-ratchet`, P-28, P-33 `no-model-api-in-ci`; ARCHITECTURE P-07, P-10 `ignore-cap`, P-30 `release-workflow-canon`, P-32 `memory-canonical-shape`.
  - The seven named are guard checks with a planted violation. Each check is named by its `Measured by` in 0176's accept commit. That commit drops `RELEASE-TREE-MEMORY` (F128) and `-k model_api` (F131), and strikes P-30's archive clause, false under 0152 (1) (`release.py ship`).
  - P-07 and P-28 are measured by the tool itself:
    - P-07 by `lint-imports`: contract `features-no-cross-feature` lists `modules = dadaia_workspace.features.*`, which import-linter 2.13 expands (verified 2026-10-03: kept on the tree, broken by a planted sibling import). `setup.cfg:97-109`'s hand-kept list and `test_import_linter_ignore_cap.py:57` leave.
    - P-28 by pytest's `--strict-markers`, added to `pyproject.toml:153` `addopts` (absent today; the suite collects under it, and a planted unregistered mark fails collection). `_KNOWN_MARKERS` (`tests/conftest.py:234-238`) and `test_stewardship_mechanics.py:100` leave; P-28's statement drops `_KNOWN_MARKERS`.
  - Command: 0176's `measured_by` grep prints nothing; `git grep -nE '_KNOWN_MARKERS|modules_equals_disk|marker_set_is_pinned' -- . ':!specs' ':!CHANGELOG.md'` prints nothing; `lint-imports --config setup.cfg --no-cache` and `pytest --collect-only -q` exit 0.
  - P-29 stays outside 0176, its test file too: its record 0012 is rejected, publish-gate check #7 (rc-12) rules on it, and a `### P-NN` line never takes the 0138 lane.
  - Repaired in place (0138), each by a `chore(adrs): repair …` commit in the release worktree right after its moving task merges (`impl` cannot stage `decisions.jsonl`; a6bca8d52): 0016, 0017, 0020, 0021, 0023, 0025, 0049, 0052, 0070, 0071, 0078, 0080, 0088. 0080 keeps `test_workspace_layout_zones.py` (it asserts no `.cache` zone) and swaps `test_no_pollution.py` for AC8.9's no-cache case.
  - Truth corrections (0138), at or before the accept commit, after the removing task: `QUALITY.md:46` (`suite_files`, the xdist reason); `50` (budget breach) and `52` (mutation evidence) rewritten per ADR 0166; `56-57, 60-61, 66, 68`, `69` ("sits beside the ratchets"); the Intent kinds, `PARAMETERS.md` homes and LARGE justification (`619e0ac43` lines 47, 51, 53) deleted; `ARCHITECTURE.md:102, 110`, `134` (13 packages become 12), `139`; `ARCHITECTURE.md:130` ("seven" import-linter contracts; `setup.cfg` holds seven) stays true.
  - After the last `QUALITY.md` edit, an `impl` task re-derives `docs/bug-ledger-lessons.md`'s markers (lines 45, 57, 66; T-050-150: `b9d7e4682`, `0800ec554`).
- AC8.4 Tests assert behaviour (FR `delete-text-count-inventory-asserts`; 0167):
  - No test pins a value owned elsewhere (a law sentence, a code roster or count); prose asserts on a doc, law or skill are deleted.
  - A CLI assert checks exit code, effect and stable id; an exception assert, type or attribute; a `fix:` line is executed. No new `--json`.
  - Count pins are deleted or derived from their source; CONTEXT-MAP loses its `Measured` column.
  - Command, the floor: `git grep -nE 'len\(.*\) *== *[0-9]{2,}' -- tests` prints nothing. Below it the reviewer judges the concept; the string-assert readout at `<start>`/`<end>` names each survivor's stable id.
- AC8.5 SKILL.md soft and hard limits (FR `skill-md-soft-hard-line-limit`; 0170): `behavior-map.json` carries `skill_md_line_soft` 333 beside `skill_md_line_ceiling` 500, declared in the schema; `doctor` emits `SKILL-MD-LENGTH` as a WARNING over the soft limit, with one `Operator action:` line naming the SKILL.md path and its split into `references/*.md` and/or `scripts/`; CONTEXT-MAP §3 loses the skills `Budget` column. Command: 0170's `measured_by`, verbatim.
- AC8.6 ADR 0143 measures the concept (FR `adr-0143-measured-by-checks-the-concept`; 0138 lane): its `measured_by` is repaired in place to a check that no test or script compares a file's line or byte count against a constant, except 0170's two `behavior-map.json` keys. The check is an AC8.3 guard; a planted size row turns it red.
- AC8.7 `CONTEXT.md` gains **Meta-test**, **Guard script**, **Owner file** and **Behaviour assert**; the SCAFFOLD test tier leaves the Scaffold homonym entry.
- AC8.8 `dd-architecture-survey` runs read-only over `core/` and `infrastructure/` (FR `architecture-survey-flat-core-infrastructure`), the ring rule unchanged; its proposals reach intake before rc-9's PLAN.

## W9 — bug lineage derived: acceptance

- AC9.1 A bug fix adds a case (FR `bug-fix-adds-never-rewrites-asserts`; 0163, 0164 (4)):
  - Phase 5 loses "existing test rewritten"; Phase 6 loses "production AND tests net ≤ 0".
  - The RED is a parametrize row in the owner file, with a literal expected value and a behaviour name; rewriting an old assert is its own commit, with a reason. The review names `git diff -U0 -- tests | grep -E '^-\s*assert'`.
  - `REQUIRED_BY_VERB` drops `evidence_seam` and `evidence_diff`; they turn optional in the schema, their verification code leaves; `evidence_loop` stays. `PILLAR-BUGS` metric 2 (row 26) counts records carrying `evidence_loop`; row 44 loses its `evidence_seam` clause.
  - Command (0163's `measured_by`): `grep -rn 'net test lines\|<bug-id>#<id>\|mutmut' dadaia_workspace/public` prints nothing; `git grep -n 'evidence.triple\|evidence_seam\|evidence_diff' -- dadaia_workspace/public` lists only the schema's two optional properties.
- AC9.2 The fix commit and its direction are derived, one decider (FR `bug-fix-commit-derived-by-grep`; 0164 (1); Q4):
  - `bugs.py fix <id>` prints the fix sha, test files and numstat, found through shape 3's `^fix\(bugs\): .*<id>` or shape 4's `(<sha>)`; no schema field is added; `LINEAGE.md` uses it in place of `git log -S`.
  - `bugs.py stats`' `direction:` rows and `PILLAR-BUGS` rows 27 (metric 3) and 45 read that numstat, never `evidence_diff`; F003 is re-measured by it and logged.
  - Command: for every record resolved since 2026-08-27, `bugs.py fix` prints a sha or lists it unlinked; both counts are logged.
- AC9.3 `caused_by` names a bug or a task, proposed by blame (FR `caused-by-proposed-by-blame`; 0164 (2), (3); 0183; Q9):
  - `caused_by` accepts a bug id or a task id such as `T-050-97` (`bug-record-v1`, `bugs.py`); every write and `check` refuse a task id no `TASKS.md` under `specs/releases/`, `_archive/` included, carries.
  - `resolve` blames the lines the staged diff removes, `tests/` included, and prints the candidates: the bug of a `fix(bugs)` or `refactor(bugs)` subject, the task of a `<type>(<task-id>)` subject. It skips only files `.gitattributes` marks `dadaia-generated` and squash `(#n)` commits; every refactor commit is a candidate (Q26), as `LINEAGE.md` step 2 states.
  - It refuses a `--caused-by` outside the candidates, and `none` when candidates exist, unless `--lineage-reason` is given and stored.
  - One semantics in the schema, `LINEAGE.md` and the bugs law: "the fix of X, a bug or a task, wrote the lines this fix corrects".
  - Cases: `none` with candidates exits non-zero, with `--lineage-reason` it passes; a staged diff removing a `tests/` line a `fix(T-050-168)` commit wrote lists `T-050-168`; one removing a line a `refactor(T-…)` commit wrote lists that task; `--caused-by T-999-999` exits non-zero.
- AC9.4 `caused_by` other than `none` makes the fix a REBUILD of the causing fix (AC12.2): the review reads every line the prior fix wrote and checks the revert (FR `focused-review-on-caused-by`; 0164 (5); Q2); it lives in `dd-code-review`, measured by `PILLAR-BUGS`, never gated.
- AC9.5 `dd-gitflow-default` §3a row 4 widens to every terminal transition without code: `chore(bugs): <verb> <id> — <reason, or by <task-id> (<sha>)>`, one edit with AC9.1's (FR `bug-terminal-transition-commit-shape`).

## W10 — the open bugs, harm-ordered (Arm B)

After AC9.3 and AC8.1's `Intent:` strip merge. Each RED is a behaviour assert in its owner file, except AC10.1's, an inner `pytester` session, because no per-test assert can see other tests' children; MEDIUMs first.

- AC10.1 One test session env, one owner (REBUILD, audit surface 1; DEL `test-suite-writes-outside-tmp`; F018, F049, F135, F136), re-cut 2026-10-04 (Q3, Q5):
  - Owner: a pure `suite_env(parent, home)` returning the suite's whole env; `tests/conftest.py`'s `pytest_configure` applies it once per process, the xdist controller and each worker; every child env is `suite_env(...) | overrides`.
  - Every child env derives from `suite_env`, `tests/contract/test_core_file_io_purity.py`'s gate-path purity child included.
  - Deleted: every env write outside that one apply (conftest import time, session fixtures, per-helper builders); `base_env`, `pin_child_env`, `child_keys`, `drop_operator_env`, `_CHILD_HOME`, `TESTS_PARENT_HOME`, and every env-name set but `suite_env`'s.
  - Reverted, then the smallest correct redo: 09d259133's pin and trio, 4ca3d7136's hunks (i, ii), b69ee15b9's in-process line, 76d7af604's conftest hunk.
  - Stay deleted: the ad-hoc copies and the scrubs. Kept: the heartbeat as a hook subprocess, the provider probe's `-B`.
  - `test_conftest_pollution_guard.py`'s conftest re-execution (`SimpleNamespace` configs) leaves; the tripwire is tested by a real inner session (`pytester`).
  - Case, `suite_env`'s owner file: a parametrize row with a literal parent env and a literal expected env (the operator's `DADAIA_*` and `HOME` out, the temp home and the suite keys in).
  - Case, `pytester`: an inner run under an operator `DADAIA_CONTEXT` and a foreign `HOME` passes, its child seeing the temp `HOME`; an inner run that writes a watched `__pycache__` exits 1.
  - Tripwire: `pytest_sessionfinish` exits the run 1 on a gained `__pycache__` under `dadaia_workspace/` or `tests/`, or a gained top-level entry under the `.cache` of the parent `HOME` `suite_env` received.
  - `-B`, delivered by T-050-173 after this AC: `tests/README.md`'s run and `ci.yml` run pytest with `-B` ("Run pytest with -B (Recommended)"), covering the controller's imports before any conftest line; `suite_env` carries `PYTHONDONTWRITEBYTECODE=1` to the workers.
  - Acceptance: on a checkout with no `__pycache__`, after `env -u PYTHONDONTWRITEBYTECODE HOME=<tmp> python -B -m pytest -q -n 2`, the run exits 0, `find dadaia_workspace tests -name __pycache__` prints nothing and `<tmp>/.cache/pip` is absent. F136 is scored from a CI E2E run.
  - Product writer: `python_env.py`'s provider probe runs the workspace venv's python with `-B`, so `dadaia init` writes no `__pycache__` into an editable checkout (4ca3d7136; "Part of 169 (Recommended)").
- AC10.2 Coverage data lands outside the repo (DEL `ci-preflight-writes-coverage-into-the-repo`; F048), re-cut on AC8.9: on every documented path (CI, the `pytest --cov` lines of `tests/README.md` and `tests/AGENTS.md`) no coverage file appears in the checkout; one decider, placed by the as-is review. Case: after each path, `git status --porcelain --ignored | grep -c coverage` prints `0`.
- AC10.3 Hooks are visible to coverage and bounded in cost (DEL `hook-entrypoints-invisible-to-coverage`; F051; 0118): `hooks/ctx_inject.py` and `sdd_post_gate` are above 0 in CI's coverage JSON. One case, parametrized over the hook lanes, counts operations at the boundary seam (the filesystem or subprocess fake), no counter in production code; it does not grow with workspace size.
- AC10.4 A run judges only its own context (DEL `onboarding-next-step-names-another-context`; FR `doctor-context-ignores-other-contexts`; FR `guidance-messages-name-the-right-target`, SessionStart part; F028, F096, F098): one decider, the bound context or the one `--context` names; the cross-context walk is deleted. Case: bound to X with two contexts, the next step's `step_id` and slug are X's. Case: with slop only in another context's repo, `doctor --context X` exits 0.
- AC10.5 A copied workspace gets its own CLI (DEL `init-on-a-copied-workspace-leaves-a-cli-bound-to-the-original`; F045): `init` reuses a venv only when its prefix and shebangs point at `DIR/.dadaia/.venv`. Case: after `cp -a` and `init <copy>`, `head -1 <copy>/.dadaia/.venv/bin/dadaia` names `<copy>`; the original is untouched.
- AC10.6 A registry row missing a key is unreadable (DEL `registry-row-missing-a-key-escapes-reg-schema`; 0162): the one parse raises `SchemaVersionError`; doctor reports `REG-SCHEMA` with an `Operator action:` line. Case: a row without `created_at` exits 1 with `REG-SCHEMA`, no `KeyError`.
- AC10.7 An absent specs tree is reported as absent (DEL `pre-push-warns-no-gitflow-block-for-an-absent-specs-tree`; F043): with no constitution, `core/gitflow.py` reports the absence with `fix: .dadaia/.venv/bin/dadaia specs init --context <ctx>`. Case: the finding is asserted and the fix line executed.
- AC10.8 An upgrade leaves no scratch and no silent rewrite (DEL `upgrade-leaves-reconcile-scratch-behind`; F044; 0104): `.dadaia/tmp/reconcile/` is absent after `init`; `init` rewrites a repo's `pre-push` only when it differs from the projected bytes, preferred over a new print. Case: a second `init` leaves the hook's bytes untouched; a differing hook is refreshed.
- AC10.9 Withdrawn: the bug was rejected (Q5); F069 moves to rc-12.
- AC10.10 `bug-record-v1.schema.json`'s `surface` description states the tracked-directory rule (DEL `bug-surface-schema-documents-the-deleted-regex`). Command: `grep -c 'a-z0-9_-' dadaia_workspace/public/schemas/bugs/bug-record-v1.schema.json` prints `0`.
- AC10.11 Resolved at closure by citation: F050 by b5013bbfb; F129 by bdb24bc64; F047 by `chore(bugs): reject removals-shipped-without-recorded-authority`; F100 by the commit exiting `init-announces-codex-trust` rejected (T-050-71 removed the trust INFO on purpose).
- AC10.12 HOOKS-DRIFT-1 states what it observed (FR `guidance-messages-name-the-right-target`, HOOKS-DRIFT-1 part; F098): one code, its message naming the observed state (absent or differing); the fix line (`ci install-hook --force`) serves both. Case: delete a projected hook; the message says absent, and its fix line, executed, restores it. T-050-146 delivered the root-whitelist clause.
- AC10.13 `release.py memory` is idempotent (DEL `release-memory-appends-a-second-entry-on-rerun`; F097): a rerun over the same window exits 0 and leaves the log unchanged. Case: the `kind: memory` entries are byte-equal after the rerun.
- AC10.14 Law and memory state the plain ledger merge (FR `worktree-memory-states-plain-ledger-merge`; 0180):
  - Memory, the closure pass (0138 lane, no `### P-NN`), once the `0.5.0d-bug` union fix merges, whatever 0180's status: `worktrees.md:5,35,36` and `bug-ledger.md:32` drop the union merge, citing the fix commit. In the same pass, `worktrees.md:35` ("trio `Approved` on that branch") states AC11.0's main-repo read. `catalog.json` is regenerated by `memory.py catalog generate`.
  - Law, only after 0180's acceptance, cited in the commit (0151 M3): `public/data/worktrees-AGENTS.md:30` (step 7) states 0180's writer re-run, in AC12.5 and AC12.7's one task (one task per law file), then `public stage`, `install`, `doctor`.
  - Check: `grep -rniw union specs/memory` states no union merge; `memory.py check` is clean; `public doctor` reports no drift.
  - At closure, the entry exits `delivered --release 0.5.0`; with 0180 still proposed, it stays active and rc-9 carries the law line alone.

## W11 — agent-behavior evals, a parallel lane in `dadaia-evals`: acceptance

- Origin: backlog `agent-behavior-evals` and the operator's fold (§Decisions). Detail lives in `.dadaia/handoff/dadaia-workspace/`: grills `2026-10-03T163043Z-main-thread-grill-evals-050` and `2026-10-03T170932Z-main-thread-grill-evals-format`, and draft `2026-10-03T173359Z-evals-enrichment-workflow-rc8-fr-draft` (finding 1).
- Parallel lane (0149):
  - AC11.2–AC11.6 write only in `repos/dadaia-evals`; no W8–W10 `W:` holds a path there. They run beside W8–W10, one `impl` worktree each, once AC11.0 merges.
  - AC11.0 and AC11.1 write here and queue like any task. AC11.0 shares `_worktree_new.py` and `test_worktree_new.py` with the open `0.5.0d-bug` worktree and T-050-164. AC11.1 shares the root map and `CONTEXT.md` with T-050-158, and `dd-gitflow-default/SKILL.md` with T-050-165.
- Order (root map §3, "no CI job calls a model API", binds until 0177 is accepted and AC11.1 merged): T-050-161 merges → the operator accepts 0177 → AC11.1 and AC11.5 merge, AC11.5 also onto `dadaia-evals` `main` → AC11.6. Before that, `dadaia-evals` holds no workflow that reads a model secret.
- G1 counts this repo only: AC11.0 (one function body and its case) and AC11.1's text. `dadaia-evals` lines are outside the readout; G4's "only job added" is this repo's CI.
- Operator prerequisites, the operator's GitHub acts on `dadaia-evals`:
  - an environment `evals` whose deployment-branch policy allows `main` only;
  - `claude setup-token`, stored as that environment's secret `CLAUDE_CODE_OAUTH_TOKEN`, never a repository secret;
  - extra usage off on the plan;
  - the `ci.yml` job required on `develop` and `main`.
  - Done: `main`, `develop` and `feature/0.5.0` on its origin (5c11f42).
- AC11.0 An associated repo's `impl` reads the main repo's Approved trio (0174's slice, Q-W0):
  - `_worktree_new.new(kind="impl")` reads the trio from the context's main repo, which is `repo` itself for a main repo. It goes through the `context list --json` read `flow_for` already makes: no second read, no branch on repo role.
  - Case, a parametrize row in the owner file `test_worktree_new.py`: an associated repo has `feature/<v>` and the main repo's trio is Approved. `worktree.py new <assoc> --kind impl` exits 0 and prints `[ok]` with `worktrees/<assoc>/<v><l>-impl`. With the main repo's PLAN Draft it exits 1, and its one fix line names `new <main> --kind release`.
- AC11.1 The model-API law is scoped by repo role (0177), shipped from `public/`:
  - The root map line (`public/data/AGENTS.md:43`) changes. No CI job of a context's repos calls a model API, except an evals repo's, and only in `workflow_dispatch` or `schedule` jobs (0177 (2)–(6)).
  - `dd-gitflow-default/SKILL.md` §3b and `CICD-AUTOMATION.md:17` state the same.
  - `CONTEXT.md` gains **Evals repo**: an associated repo whose one role is to measure agent behaviour against the distribution its context ships, and whose CI calls a model only under 0177. It sits beside **Scope** (`CONTEXT.md:102`, today the only entry naming associated repos).
  - The memory pass aligns `sdd-gate-v3`'s model-API line.
  - Check:
    - `grep -rl 'calls a model API' dadaia_workspace/public` and `grep -rl 'evals repo' dadaia_workspace/public` print the same three files.
    - `grep -r dadaia-evals dadaia_workspace/` prints nothing (0179).
    - The root map stays ≤ 8,293 B.
    - `public stage`, `install` and `doctor` are clean, and `no-model-api-in-ci` is green here.
- AC11.2 The `dadaia-evals` skeleton:
  - `AGENTS.md`: what lives here, how to run, `jobs/` never committed, no `push` or `pull_request` trigger calls a model.
  - `README.md`, and `.gitignore` (`jobs/`).
  - `tasks/t1-cold-onboarding/` and `tasks/t2-seeded-bug/`, each holding `instruction.md`, `task.toml`, `environment/Dockerfile`, `tests/test.sh` and `tests/test_grade.py`.
  - `scripts/compare.py`.
  - A Dockerfile holds the environment only (python, uv, git, Node, the Claude CLI pinned). The lib is its last layer, a wheel or a PyPI release (0179). No registry.
  - Check: each task's image builds with the 0.4.7 layer, and `git ls-files jobs` prints nothing.
- AC11.3 T1, cold onboarding:
  - `environment/` builds a `file://` bare repo with one commit, as `bare` does at `tests/e2e/test_onboarding_journey.py:136`.
  - `instruction.md` asks the agent to onboard it following only what `dadaia` prints.
  - `tests/test.sh` runs `uvx pytest tests/test_grade.py` and writes `/logs/verifier/reward.txt`.
  - It passes when `dadaia doctor --json` reports 0 errors, the context is ALIVE and specs are initialized.
  - Check: the unchanged grader passes on a hand-onboarded workspace of 0.4.7 and of the candidate, and fails on an empty one.
- AC11.4 T2, a seeded bug (Arm B):
  - `environment/` builds a small onboarded project with one planted contract break; the instruction gives the operator's confirmation.
  - It passes when:
    - a `BUGS.jsonl` record precedes the fix commit;
    - the RED test fails on the pre-fix sha and passes on the fix;
    - `git diff -U0 -- tests | grep '^-\s*assert'` prints nothing.
  - Check: as AC11.3's, on both versions, with one planted pass and one planted fail.
- AC11.5 The two workflows (0177, 0178), merged after 0177's acceptance and review to the `dadaia-evals` work branch, then through its PR edges to its `main` ahead of rc-12, since GitHub dispatches only a default-branch workflow. A PR edge carries every commit on its branch, so AC11.2–AC11.4 reach `main` too: "early" is before rc-12, not `eval.yml` alone (§Decisions).
  - `ci.yml` makes "CI green per PR edge" real: on `push` and `pull_request`, a GitHub-hosted runner, no secret, no environment. It runs the three checks below.
  - `eval.yml`:
    - Trigger: `workflow_dispatch` with the one input `lib_ref`; `permissions: contents: read`; a GitHub-hosted runner.
    - It stamps `release-please-config.json`'s `release-as` into `pyproject.toml`'s version line before `uv build`, and fails closed when `release-as` is missing.
    - harbor's `claude-code` agent runs three trials per task, at most two at once, on PyPI 0.4.7 and on the candidate wheel; pins and flags are the PLAN's; the model follows the economy template (0022).
    - Auth: the model job alone declares `environment: evals` and reads `CLAUDE_CODE_OAUTH_TOKEN` + `CLAUDE_FORCE_OAUTH=1` at job level.
    - `scripts/compare.py` blocks when a task passing ≥2/3 on 0.4.7 passes ≤1/3 on the candidate, or T1 is below 3/3 on the candidate. Anything else is readout.
    - A secret scan runs over `jobs/` and the summary before any upload or summary write, with the token's value among its patterns. It fails closed.
  - Check (0177's `measured_by`), run by `ci.yml` and by `eval.yml`'s first job, neither holding the secret:
    - The workflow check fails on a workflow that reads the secret or declares `evals`, if it has any of: a trigger other than `workflow_dispatch` or `schedule`, a non GitHub-hosted `runs-on`, the secret at workflow level, or an upload or summary write not preceded by the scan.
    - The scan exits non-zero on a fixture holding a planted token.
    - `compare.py` is red on a planted drop and on T1 at 2/3.
- AC11.6 The first run, as evidence:
  - One `eval.yml` run, `gh workflow run eval.yml -f lib_ref=<tip of feature/0.5.0>` on `dadaia-evals`, against 0.4.7, after AC11.1 merges and AC11.5 reaches `main` with the whole lane.
  - It confirms that the trial runs the candidate wheel: `dadaia capabilities --json` names the stamped version.
  - It confirms that two trials at once stay inside the plan's rate limit: no rate-limit error appears in `jobs/`.
  - A failing grader, unlike a failing agent, is fixed in the grader before closure.
  - Check: a `_RELEASE.json` log entry names the run URL, verdict, tokens and wall time.
- At closure, `agent-behavior-evals` exits `delivered --release 0.5.0`: that needs AC11.6 logged and 0177–0179 ruled (its done-when). The promote gate is rc-12's (§Carried).

## W12 — the bug loop stops (amendment, grill 2026-10-04): acceptance

- Not in scope: gate 2 (a red work branch takes only a revert or a registered bug) and gate 3 (a `fix(...)` commit keeps old asserts) are private developer hooks (Q15), outside the library.
- Not carried: dfa3aceb6 and 9b669af03, past fixes with no confirmed induced bug (Q18).
- AC12.1 A break a merged fix caused is a bug (Q1): `specs/bugs/AGENTS.md` §1's "own mistake" exclusion covers only unmerged rework inside a worktree; a break an already-merged fix caused is registered with `caused_by` (source `pub/scaffold/bugs/AGENTS.md`).
- AC12.2 One fix-induced bug triggers a REBUILD at once (Q2), going forward (Q18), in `LINEAGE.md`:
  - The culprit: the commits that wrote the lines the induced bug's repair corrects; each REBUILD AC names them.
  - A REBUILD is one commit holding the culprit's revert and the smallest correct redo, never a large rewrite (larger fixes induce more bugs; audit, research); its shape is AC12.12's.
  - A deletion or a smaller restore is a redo: AC12.7, AC12.8, AC12.9 and AC12.13 meet this AC.
  - Work in flight stops until the REBUILD lands (Q2, Q21); the ≥ 2 prior fixes trigger stays.
  - Observable, for REBUILDs after this AC merges: the commit body names each culprit sha, and blame on the restored and redone lines names the REBUILD commit.
- AC12.3 A red a merged fix caused is Arm B (Q1, Q2): `dd-release-implementation` §2a routes it to registration, revert and redo (AC12.2), never a follow-up commit; a flaky red is quarantined with a bug. Measured by the next audit's `PILLAR-BUGS` readout.
- AC12.4 The hidden breaks are registered (Q3, Q9, Q18, Q22, Q24), after AC9.3's task-id half merges:
  - One `chore(bugs): report …` commit: `bugs.py append` per row, then `bugs.py update --set caused_by=…`; the operator's approval of this SPEC confirms every row, row 19 included.
  - The same commit repairs `caused_by` on `dead-holds-main-repo-before-associated-push` (to `sa-context-dead-removes-repos-outside-the-reaper`) and on `tmp-expired-worktree-fix-line-never-clears` (to `reaper-deletes-linked-git-worktrees`).
  - Each sha row resolves by `resolve --caused-by <its caused_by> --lineage-reason "retro: repaired by <sha>"`, one shape-4 commit per row naming `(<sha>)`; an AC row stays open and resolves by that AC's commit.
  - Row 20's `--lineage-reason` records that T-050-160 moved the check (prior authors 6b6374273, 817290415); row 27 resolves with `--lineage-reason` (latent).
  - Check: `bugs.py status --all` shows each slug with its expected status, the open set exactly the AC rows; `bugs.py fix <slug>` prints exactly its row's sha(s).

| # | slug | sev | `caused_by` | resolution |
|---|---|---|---|---|
| 1 | `bootstrap-e2e-closure-walk-ignores-requirement-markers` | LOW | `bootstrap-e2e-mirror-seeded-from-stale-editable-metadata` | ef7262879 |
| 2 | `gate-path-purity-test-premise-died-with-t097` | LOW | `T-050-97` | 23d678b4f |
| 3 | `gate-path-purity-child-env-drops-pythonpath` | MEDIUM | `T-050-97` | e06583a46 |
| 4 | `dadaiaignore-doctor-breaks-bind-resolution-import-contract` | MEDIUM | `T-050-116` | a34f3b738 |
| 5 | `help-quality-mask-misses-folded-venv-path-on-ci` | LOW | `T-050-145` | c370b0c3a, bf5ffde97 |
| 6 | `sweep-remove-misses-oserror-on-python-3-14` | MEDIUM | `T-050-146` | AC12.13 |
| 7 | `host-shell-cmd-test-escapes-fix-line-quotes` | LOW | `T-050-149` | 013c37d0d |
| 8 | `windows-quoted-fix-left-behavior-map-hash-stale` | LOW | `windows-quoted-executable-fix-not-runnable-in-powershell` | 582535466 |
| 9 | `bugs-fix-nonrepo-test-not-portable` | LOW | `T-050-167` | f6d04aa56 |
| 10 | `t168-canon-change-without-stamp-bump` | MEDIUM | `T-050-168` | AC12.9 |
| 11 | `bugs-own-check-attr-keeps-cr-on-windows` | MEDIUM | `T-050-168` | d66e50c66 |
| 12 | `blame-refusal-test-asserts-a-posix-fix-line` | LOW | `T-050-168` | AC12.9 |
| 13 | `doctor-stub-drifts-from-doctorservice-signature` | LOW | `onboarding-next-step-names-another-context` | AC12.10 |
| 14 | `outside-tmp-home-pin-coupled-to-session-hooks` | MEDIUM | `test-suite-writes-outside-tmp` | AC10.1 |
| 15 | `workspace-venv-probe-writes-bytecode-into-editable-checkout` | LOW | `test-suite-writes-outside-tmp` | 4ca3d7136 |
| 16 | `heartbeat-test-drives-hook-in-process` | LOW | `suite-fails-under-an-operator-dadaia-context` | AC10.1 |
| 17 | `operator-env-scrub-row-leaves-stale-pinned-home` | MEDIUM | `suite-fails-under-an-operator-dadaia-context` | AC10.1 |
| 18 | `t151-fix-line-tests-compare-os-separator-paths` | LOW | `T-050-151` | b78e8fd68, c0b9989de |
| 19 | `bootstrap-e2e-mirror-seeded-from-stale-editable-metadata` | LOW | `none` | ff5245e08 |
| 20 | `hook-stdin-guard-misses-raw-assignment` | LOW | `T-050-160` (ae8d5b056 wrote the check) | AC12.14 |
| 21 | `sweep-remove-names-the-wrong-owner-when-rmtree-swallows-the-unlink-error` | LOW | `doctor-tmp-expiry-foreign-owned-entry-never-clears` | AC12.13 |
| 22 | `sweep-remove-prescribes-operator-removal-for-any-oserror` | LOW | `doctor-tmp-expiry-foreign-owned-entry-never-clears` | AC12.13 |
| 23 | `workspace-denylist-migration-reads-a-refused-hold-as-success` | LOW | `T-050-139` | AC12.13 |
| 24 | `context-dead-submodule-refusal-prints-a-worktree-move-that-cannot-run` | MEDIUM | `sa-context-dead-removes-repos-outside-the-reaper` | AC12.14 |
| 25 | `ttl-expire-lane-walks-each-expired-entry-content-twice` | MEDIUM | `T-050-99` | AC12.14 |
| 26 | `reaped-root-level-symlink-hold-expires-at-next-pass` | LOW | `reaper-judges-ttl-by-walking-every-file` | AC12.14 |
| 27 | `context-dead-hold-oserror-escapes-mid-loop` | MEDIUM | `none` (latent) | AC12.13 |

- AC12.5 `worktree.py merge` lands only a verified HEAD (Q6 gate 1, Q15, Q16):
  - Every kind: `merge` reads the repo's verification command from the HEAD it lands and runs it inside the worktree before the fast-forward; a non-zero exit lands nothing and leaves both branches and the tree unchanged.
  - The command is declared once per repo, in any language, opaque to `merge`; where it is declared is the PLAN's. No declaration: `merge` refuses with one `fix:` line naming where to declare it.
  - Trade-off: a worktree can weaken its own command; the reviewer sees it in the diff.
  - Under a 0168 carry, gate 1's run is the evidence for the landed sha.
  - Cases, `test_worktree_lifecycle.py`: a command exiting 1 refuses, the work branch tip unchanged; one exiting 0 lands; one printing `git rev-parse HEAD` prints the landed sha; no declaration refuses, its fix line naming the place; a worktree whose own commit adds the declaration lands.
- AC12.6 This repo declares one script running every Linux job of `.github/workflows/ci.yml` (Q4):
  - Steps: `ruff format --check`, `ruff check`, `lint-imports`, `mypy --strict`, `scripts/guards/run.py` and `--planted`, unit, the unit-plus-contract coverage run, integration, e2e, repo-hygiene, `doctor`. PR-event and Windows/macOS jobs are out.
  - One source: `ci.yml`'s Linux jobs call this script.
  - pytest runs with at most `-n 2`, in random order (`pytest-randomly` on).
  - It prints each step's verdict and exits non-zero when any step fails. Case: a planted ruff violation, and a planted failing test, each turn it non-zero.
  - `dd-code-review`: every verdict carries the output of the repo's declared verification command (AC12.5) for its sha and names Windows-only and macOS-only risk unverified; no output, no APPROVED.
- AC12.7 `worktree.py merge` never rewrites (REBUILD, audit surface 2a; Q7, Q19):
  - `merge` lands exactly the approved HEAD by fast-forward; when the work branch moved, it refuses with `fix: git -C <tree> rebase <work>` and changes nothing.
  - The agent rebases inside the worktree; a patch-identical result keeps its verdict by 0168's deterministic check; any other change goes back to the reviewer.
  - Deleted: the in-merge rebase (820bee3b0's step), the TASKS-marker replay (36ce79d7d), the already-contains early return (1cfc3b72d), `_worktree_end.py`'s `sys.path` reach-in to `dd-release-implementation`; 0111's replay case leaves with it. Kept: a8f226c8b's dirty-tree fix line.
  - The merge ADR amends `worktrees/AGENTS.md` §2 step 6 and 0111's TASKS clause and cites 0168 as standing; one task with AC12.5 rewrites `pub/data/worktrees-AGENTS.md` once: step 6, AC10.14's step 7 and the gate 1 line.
  - Cases: with the work branch moved, `merge` exits non-zero and both branches are unchanged; after the fix line, a patch-identical rebase lands under the old verdict, and one changing a patch refuses for review.
- AC12.8 `context dead` never commits (REBUILD per 0172, audit surface 2b; Q8):
  - Deleted: `dead --commit`, `commit_all`, dead's untracked-consent, secret and identity refusals, 1ee8aa30f's secret-refusal hunk. Kept: `unrecoverable()`'s stash count.
  - A dirty checkout refuses with one fix line per file and leaves tree and origin untouched; each 0154 direct writer commits its own output in the act.
  - dead's fast-forward push goes through the pre-push hook, never around it; the PLAN confirms it.
  - Case: 0172's `measured_by`.
- AC12.9 T-050-168 is rebuilt (audit; Q18), rows 10 and 12:
  - Row 10: a41c69967's re-pin and aed2ac322's rule-comment rewrite in `tests/unit/core/test_specs_version.py` are reverted, then `CANONICAL_SPECS_VERSION` is bumped.
  - Row 11's repair is kept: d66e50c66's NUL-delimited (`-z`) check-attr read.
  - Row 12: 7196e1473's `startswith`/`endswith`/`in` predicates go; the refusal test asserts the exact fix line again, its expected literal built per platform.
  - Cases: `test_a_canon_change_bumps_the_stamp` passes with its original assert and rule; the refusal row compares `stderr` lines for equality on every OS.
- AC12.10 `_StubDoctor` leaves (audit; 2 repairs in 2 days): `tests/unit/cli/test_exitcode_truthfulness.py` drives the real `DoctorService` over a tmp workspace; its cases keep their expected exit codes.
- AC12.11 The law files rc-8 rewrites meet one authoring bar (Q12–Q14):
  - Files: `pub/scaffold/bugs/AGENTS.md`, `S/dd-bug-resolution/SKILL.md` and `LINEAGE.md`, `S/dd-gitflow-default/SKILL.md`, `pub/data/worktrees-AGENTS.md`, `S/dd-release-implementation/SKILL.md`, `S/dd-code-review/SKILL.md`, `S/dd-ai-eng-knowhow/AUTHORING.md`; each rewritten once, in the task changing its law.
  - `AUTHORING.md` rule 9: a prohibition carries a short reason or a bug or ADR id (Q13 supersedes its "provenance … never in the skill").
  - Bar: positive by default; a prohibition stays only with a demonstrated failure and its short reason (a bug or ADR id); one line per instruction.
  - Acceptance: the deterministic passes of the operator's private `/corpus-audit` (developer tooling, not product) report 0 conflict, stale-ref and unprovenanced-prohibition findings on those files; P5, the LLM judge, is advisory. `public stage`, `install`, `doctor` clean.
- AC12.12 A REBUILD has its own commit shape (Q20), in `dd-gitflow-default` §3a:
  - Every REBUILD: `refactor(<task-id>): REBUILD <unit> — …` in a task worktree; `refactor(bugs): <bug-id> — REBUILD <unit>: …` in a bug worktree.
  - `bugs.py fix` finds `refactor\(bugs\): <id> — ` beside shape 3.
  - `dd-code-review`: no APPROVED on a `refactor(...)` commit deleting tests without an approved REBUILD verdict in the SPEC.
- AC12.13 `sweep.py`'s delete path and result protocol are rebuilt (Q23; REBUILD U1, U2; rows 6, 21–23, 27):
  - U1 (`sweep.py:97-101, 142-185`): `onexc` never raises; it chmods, retries once and records the first failing path, local to one `remove` call (no module-level state); file unlinks go through the same helper.
  - U1: `remove` judges by outcome (`occupied(target)`) and refuses naming the recorded entry and its parent's owner.
  - U1 culprits reverted: 8f329db3a's `_owner` leftover; af2154d5a's try/except arm and owner text, keeping its EXDEV `kept` return; b9b28202d's OSError arm.
  - U2: a refusal or a no-op is falsy and not a usable `str`; `succeeded` and `deleter` are deleted; `move` returns its `os.replace` failure as a refusal, never raises.
  - Kept: the TTL walk, the N-holds `-N` suffix, `_inside`, `walk`, `lstat`. Moved: `worktree_git_dir` to `service.py`, its one caller. Re-pointed: `deleter`'s callers `cli/commands/specs.py:52` and `:169`.
  - A fourth patch on `remove`'s except arm is refused at review.
  - Case: the failure test pins the recorded path, not `getpass.getuser()`.
  - Case, row 6: a non-empty directory is judged by `occupied`, with no branch on the Python version.
  - Case, row 22: only a permission failure prescribes the operator act.
  - Case, row 23: the denylist migration reads a refused hold as a refusal.
  - Case, row 27: an `OSError` in dead's hold loop refuses with a fix line and does not escape.
  - Cases, U2: a refusal is falsy; `move` returns its failure as a refusal.
- AC12.14 Own fixes, each RED first (Q22, Q24, Q25):
  - Row 20: the hook-stdin guard turns red on a planted raw `sys.stdin` assignment.
  - Row 24 (Q25): `linked_worktree` matches only a gitdir under `<common>/worktrees/`; a submodule's relative gitdir survives the move; `sweep.py:10`'s docstring says so.
  - Row 25: the expire lane walks each expired entry once; the linked-worktree decision is made once.
  - Row 26: a root-level held symlink keeps its hold clock (0074).
- Order (Q5); every other open rc-8 task, W11's lane included (Q21), stays paused until step 3 lands:
  1. The script, then gate 1, before any other Python lands ("script first", Q5): AC12.6 lands through today's merge; then one task for AC12.5 and AC12.7, T-050-189 folded in (they share `_worktree_end.py`, the merge ADR and the law file), declaring the script in its own commit (AC12.5's self-declaring case).
  2. The law and the lineage data: AC12.1–AC12.3, AC12.12, AC9.3, AC9.4, then AC12.4; every `dd-code-review` edit (AC9.4, AC12.6, AC12.12) in one task.
  3. The REBUILDs: AC10.1, AC12.8, AC12.13; then AC12.9, AC12.10, AC12.14.
  4. Only then the paused tasks: T-050-172 … T-050-181, T-050-185, T-050-186, T-050-188.

## W13 — the bug strategy (amendment, grill 2026-10-05): acceptance

- Sources are edited under `dadaia_workspace/public/`, then `public stage`, `install`, `doctor`; the instance is never hand-edited.
- Not in scope: the main thread's private rulings ("resolve on the spot", "keep a bug worktree busy"); the balance in `QUALITY.md` and the convergence indicator (rc-9, §Carried).
- AC13.1 Every bug record carries `found_in` and `introduced_in` (G1):
  - Both `write-once` in `bug-record-v1` (the class widens to "set once, at registration or later"; bugs law §3, T-050-194), shape `{release, rc}`.
  - One function, instant → candidate: a candidate opens at the commit adding `releases/<v>/rc-N/SPEC.md`, read with `git log --all --follow` across the move to `_archive/<v>/`; it closes when the next opens or the release ships. 0.4.7's archive holds `rc-1` … `rc-9` and a flat root trio (candidate 12's text), labelled `root`, open from the first commit after `rc-9`'s add that changes the root `SPEC.md`. No `release.py` field is added.
  - `bugs.py append` stamps `found_in` for the append instant; no flag sets it.
  - `bugs.py resolve` writes `introduced_in` for the instant of its culprit commit (`caused_by`'s), `unknown` when there is none or no candidate holds the instant; `resolved_release` comes from the same function and `--resolved-release` leaves.
  - Backfill, one `chore(bugs): backfill found_in and introduced_in` commit by `bugs.py update --set` from a script run once under `.dadaia/tmp/`: `found_in` from `ts` on every record; `introduced_in` on terminal records only, from the culprit or `unknown`, and `= found_in` on the 89 born-in-release records (the scan's class). An open record's `introduced_in` stays absent until `resolve`: each field has one write.
  - Cases, `test_bug_resolution_bugs_script.py`, over a temp repo whose `releases/9.9.9/rc-2/` and `rc-3/` SPECs are added in two commits and one archived layout with a flat root trio: append after `rc-3`'s add stamps `{"release": "9.9.9", "rc": "rc-3"}`; resolve with a culprit committed between the two adds writes `rc-2`; an instant in the archived root writes `root`; no culprit writes `unknown`; a second `--set found_in` is refused.
  - Check: `bugs.py check` clean; every record carries `found_in`, every terminal one `introduced_in`; the `unknown` counts are logged in `_RELEASE.json`.
- AC13.2 A bug is fixed at once only on the block list or when born in the running rc; every other waits in the pile (G2, G11; implements 0123):
  - The block list, closed, stated once in `specs/bugs/AGENTS.md` §2 (source `pub/scaffold/bugs/AGENTS.md`): (1) the work branch's CI is red; (2) a refusal whose own fix is blocked (Stall); (3) the running task cannot deliver its AC; (4) a security finding or an open dependency-vulnerability alert; (5) data loss or corruption. Every other file points there.
  - A block-list fix opens its `bug` worktree at once and pauses the open task whose `W:` overlaps it (amends 0149 (3)).
  - Born in the running rc: judged at triage from the culprit the proposal names, a task or a fix merged in the running candidate; `introduced_in` records it at resolve.
  - The pile: every open record no SPEC AC carries.
  - Cause groups, after the last planned task and before `RC-FLOW.md` step 3: the engineer groups the pile by structural cause; groups run in harm order, the pile re-evaluated after each (0123); each group is one task and one `bug` worktree holding its N bugs (0136), its one fix commit resolving each.
  - Each group enters TASKS and the Parallel schedule by a release-worktree amendment; the main thread writes its done marker there after the `bug` worktree merges (the `bug` kind holds no `TASKS.md`).
  - A cause needing more than one task becomes a proposed ADR and an AC of the next rc's SPEC; its bugs stay open, carried by id.
  - AC12.2 narrows (G11): a fix-induced bug stops work in flight only on the block list or when born in the running rc; any other, an earlier rc's fix included, waits in the pile, its REBUILD of the culprit being its group's task.
  - Every `fix(bugs)` body names `block: <item>`, `born-in-rc: <culprit>` or `cause: <group>` (`dd-gitflow-default` §3a shape 3).
  - Files: the root map §1 Arm B line, within 8,293 B (8,292 today); `pub/templates/specs-AGENTS.md` §6; `dd-bug-resolution` §1; `dd-release-implementation` SKILL §2a and `RC-FLOW.md`; `dd-gitflow-default` §2a and §3a.
  - Check: `grep -rnE 'bug[^.]*in any phase' dadaia_workspace/public` prints nothing; `grep -rl 'data loss or corruption' dadaia_workspace/public` names only `scaffold/bugs/AGENTS.md`; `/corpus-audit` clean.
- AC13.3 A review of the bug window opens every rc's first SPEC (G3):
  - The bug window: every record whose `found_in` or `introduced_in` is a candidate of the live release or of the previous published version, whatever its status, `_archive/bugs_histo.jsonl` included; it moves with each rc.
  - One read verb, `bugs.py window`, lists the records in it; Phase 0 of `dd-bug-resolution` reads it. `LINEAGE.md`'s audit window stays as the audit's.
  - `dd-release-definition` §1's first step: `dd-software-engineer` reads the window read-only, each cited test included, and hands its clusters to the grill beside the as-is review.
  - The SPEC's first section, `## Bug window review` (the operator's "Revisão de bugs"), by `dd-product-engineer`: one row per cluster — records, structural cause, verdict (DELETE, REBUILD, UPDATE or KEEP), the AC carrying it.
  - A repeated agent error yields a harness rule in the operator's private rules, never in `dadaia_workspace/public`, unless the operator rules otherwise.
  - `specs/releases/AGENTS.md` §2's lifecycle order opens with it; `release.py new`'s SPEC stub opens with the heading; `release.py check` refuses a live SPEC without it, one fix line, beside its PLAN §1 check.
  - Cases: `bugs.py window` lists a record found in the live release, one introduced in the previous published version, and an archived one, and omits one of an older version; `release.py new` writes the heading first; `check` on a live SPEC lacking it exits non-zero with one fix line (`test_release_implementation_release_script.py`).
- AC13.4 rc-8's first window review (G4, G12):
  - One task after AC13.1, AC13.6's verb and restore, and the backfill; T-050-199 … T-050-208 stay frozen until its verdict.
  - Window: 0.5.0 `rc-1` … `rc-8`, and 0.4.7's `rc-1` … `rc-9` and `root`.
  - The 179 restored records are read with the rest; the verdict names each record on a retired surface and the ADR retiring it, a retroactive one where none exists; the others stay live.
  - The verdict names exactly the retired bind/session-TTL surfaces; the reaper's live TTL is out of scope.
  - The 205 non-product records, by class, through `bugs.py` in a `bug` worktree, one shape-4 commit per class, `chore(bugs): <verb> class <class> — <reason>`, one id per body line:
    - agent error (15): `reject` with its reason;
    - born in the release (89): stays a bug; only never-merged rework is rejected;
    - library dev-tooling (66): kept; the verdict names their surfaces for rc-9's map; the 240 `unknown` surfaces stay out of recurrence counts (`surface` is `immutable-core`; they predate the tracked-directory rule);
    - debt: a backlog entry through the operator-gated intake, then `supersede --by <backlog-slug>`;
    - doubtful (35): each ruled in the review.
  - Verdict: rc-8's SPEC gains `## Bug window review` and its cluster ACs (shape 8) for the operator's approval; PLAN §6.6 re-plans T-050-199 … T-050-208 and the cluster ACs in one Parallel schedule.
  - Re-archiving runs after each named ADR is accepted, by `archive --adr`.
  - Check: one `_RELEASE.json` log entry names the counts per class before and after, and the records re-archived and kept live; `bugs.py stats` agrees.
- AC13.5 Moved to rc-9 (scope ruling): `evidence_seam` at resolve (G5, G10).
- AC13.6 A record leaves the ledger only by an accepted ADR (G6, G12):
  - `bugs.py archive --adr <id>` moves the named terminal records into `_archive/bugs_histo.jsonl`, each carrying the ADR id; an id not `accepted` in `decisions.jsonl` is refused.
  - Deleted, from code and law: the age path (`--threshold-days`, `--now`, the `closed_at` cutoff, `archivable`), `RC-FLOW.md` step 7's "Age the ledger" line, the bugs law's "ages by `closed_at`".
  - The 179 age-archived records return to `BUGS.jsonl` in one `chore(bugs): restore age-archived records` commit, in a `bug` worktree (0124), through the ledger's store: ADR B's one-time writer exception, no lasting verb.
  - Cases: `--adr` naming a proposed record exits non-zero, ledger unchanged; an accepted one moves exactly the named records; `--threshold-days` exits 2.
  - Check: every `_archive/bugs_histo.jsonl` record carries an accepted ADR id; `git grep -n 'threshold-days\|archivable' -- dadaia_workspace` prints nothing.
- AC13.7 The worktree merge is the boundary between an agent's error and a bug (G7, G9):
  - `specs/bugs/AGENTS.md` §1: a bug exists once a merged change breaks a documented contract; what fails inside an unmerged worktree (a wrong command, a stray quote, the agent's own failing test, review rework) is rework and gets no record. Gate 1 (0185) keeps a red from crossing the merge. AC12.1's line says the same.
  - `dd-bug-registration` §2 step 4 keeps its not-a-bug arms and adds the work-branch sha that reproduces the bug; the culprit is required only for a born-in-rc claim.
  - Check: `/corpus-audit` clean on both files.
- AC13.8 The `bug` worktree kind follows the pile (G9):
  - `worktrees/AGENTS.md` §1: `bug` — a registration; a block-list or born-in-rc fix, opened at once; or one cause group holding N bugs (0136). §2 step 1's Arm B bullet says the same (0149 (3) as A amends it).
  - `_worktree_kinds.KINDS` is unchanged.
  - Check: `grep -n 'one fix' dadaia_workspace/public/data/worktrees-AGENTS.md` prints nothing.
- AC13.9, AC13.10 Moved to rc-9 (scope ruling): `QUALITY.md`'s `## Bugs` balance and `docs/bug-ledger-lessons.md` derived from it (G8).
- AC13.11 `CONTEXT.md` gains **Bug window**, **Pile**, **Block list** and **Cause group**; **Wave** keeps its sense; **Resolution contract** names `evidence_loop` and drops the evidence triple and "net ≤ 0" (0163, 0164). Check: `grep -cE '^\*\*(Bug window|Pile|Block list|Cause group)\*\*:' CONTEXT.md` prints `4`; `grep -c 'evidence triple' CONTEXT.md` prints `0`.
- AC13.12 Every line W13 writes meets AC12.11's bar, line by line; whole-file rewrites stay AC12.11's files, the rest rc-10's (Q12); 0186 (5) stands.
- The drafted tasks against W13 (TASKS is the engineer's; each must now meet):
  - T-050-192: AC9.3 and AC12.12's half as drafted; its `W:` holds AC13.1's files, so the PLAN may fold AC13.1 into it.
  - T-050-194: AC12.1 as AC13.7 words it; AC13.1's §3 class; AC13.2's block list; AC13.6's law line.
  - T-050-195: AC12.2 as AC13.2 narrows it; AC13.2 in `dd-bug-resolution` §1 ("in any phase" leaves); Phase 0 reads `bugs.py window` (AC13.3).
  - T-050-196: AC12.3 stands (a red work branch is block-list item 1); AC13.2's cause groups in SKILL §2a and `RC-FLOW.md`; AC13.6's `RC-FLOW.md` line; its `W:` widens to `RC-FLOW.md`.
  - T-050-197: AC12.12 stands; AC13.2 and AC13.8 in §2a ("in any phase" leaves); shape 3's body line and AC13.4's per-class shape 4 in §3a; shape 3 and the `refactor(bugs)` REBUILD shape name a group's N ids, each found by `bugs.py fix`.
  - T-050-198: AC9.4's REBUILD read applies when the fix lands, at once or in its group; a group's worktree holds one cause and exactly its bugs' resolve lines (0136).
  - T-050-199 … T-050-208: frozen until AC13.4's verdict, then re-planned in PLAN §6.6.
  - `dd-bug-registration` (AC13.7) and `dd-release-definition` (AC13.3) have no task yet: the PLAN adds them.
- Order (W13), inside W12's step 2, after T-050-192 and before T-050-199:
  1. AC13.1: the schema, the stamp and the derivation.
  2. AC13.6: `archive --adr` and the age path's deletion, then the restore of the 179.
  3. AC13.1's backfill.
  4. AC13.4; T-050-193 … T-050-198 proceed beside it; its re-archive follows each ADR's acceptance.
  5. AC13.3's code; then T-050-199 … T-050-208 and the cluster ACs, in the PLAN's one Parallel schedule (0149).
- Net direction: law shrinks (the "any phase" lines, the age archive, "one fix"); production gains the two fields, the instant function, `window`, `archive --adr` and the SPEC heading check, less the age path and `--resolved-release`. Each ADD counts against G1's 24,805 ceiling.

## Replaces

- `ci preflight`, its scope error, runner and pytest bootstrap; the Python-only anchors, reaping list, tool names, extension list and `TOOL_CACHE_ENV` list (AC8.9).
- The `api` anchor kind and its alias map, `backlog.py subjects`, `doctor --alias-map` and `--source-root`, SPEC-DOC-005 (AC8.9).
- `dd-test-stewardship`, the tests-AGENTS template, the `Intent:` convention, V28, V29, V31; MEMORY-UPDATE's own canonical-memory rule.
- Duplicate meta-tests, the mutation tooling, meta-test pytest files; nine principles' pytest `Measured by` and P-30's archive clause (0176).
- The hand-kept `features-no-cross-feature` module list and `_KNOWN_MARKERS`, with their equality checks (0176).
- Prose, roster and count asserts; CONTEXT-MAP's `Measured` and skills `Budget` columns; 0143's symbol-list `measured_by`.
- Phase 5's "rewritten", Phase 6's "net ≤ 0"; required `evidence_seam`/`evidence_diff`, their verification, metric 2 over them, direction from `evidence_diff`; the `git log -S` recipe; an unreasoned `none`; the "reopen" wording; §3a row 4's resolve-only wording.
- Ad-hoc child envs, `COVERAGE_FILE` redirects; the cross-context walk; build-identity venv reuse; the bare `KeyError`; the no-block warning for an absent constitution; HOOKS-DRIFT-1's fixed "differs"; the reconcile scratch and unconditional hook rewrite; the deleted surface regex; the second `kind: memory` append.
- The test env written at import, in session fixtures and per helper; `base_env`, `pin_child_env`, `child_keys`, `drop_operator_env`, `TESTS_PARENT_HOME`, their name sets; the conftest re-execution tests (AC10.1).
- "Own mistake" covering a merged fix's break; the follow-up commit for a fix-induced red; "state REBUILD or why not"; `caused_by` bugs only; blame blind to `tests/` and to refactor commits (AC12.1–AC12.3, AC9.3, AC9.4).
- An unverified merge; merge's rebase, TASKS-marker replay, already-contains return and `sys.path` reach-in; 0111's marker clause (AC12.5, AC12.7).
- `dead --commit`, `commit_all`, dead's consent, secret and identity refusals, certification's `dead --commit` call (AC12.8); the stamp-9 re-pin and its rewritten rule; 7196e1473's loosened assert; `_StubDoctor` (AC12.9, AC12.10).
- `sweep.py`'s except-arm delete path, `succeeded`, `deleter`, the str refusal, `move`'s raise, `worktree_git_dir` there; a submodule read as a linked worktree (AC12.13, AC12.14).
- The map's unscoped "no CI job calls a model API", in the root map, SKILL.md §3b and `CICD-AUTOMATION.md` (0177); an `impl` worktree reading the trio from its own repo (AC11.0); memory's ledger union merge and step 7's bare conflict line (AC10.14).
- A confirmed bug fixed at once in any phase, the `bug` kind's "one fix", and a fix-induced bug stopping the line whatever its rc (AC13.2, AC13.8; 0019, 0149 (3), 0186 (2)).
- The age archive (`--threshold-days`, `--now`, the `closed_at` cutoff, `archivable`, RC-FLOW's "Age the ledger") and the 179 records it archived; the hand-typed `--resolved-release` (AC13.1, AC13.6).
- Phase 0's own window read; it reads `bugs.py window` (AC13.3).
- The agent's own judgement of "own mistake", in place of the merge boundary; `dd-release-definition` §1's bare `status`/`stats` read (AC13.3, AC13.7).
- CONTEXT's evidence-triple **Resolution contract** (AC13.11).

## Risks

| Weakness | Mitigation |
|---|---|
| A deleted text assert was a real guard. | It maps to a behaviour assert or a reason in the commit body; the reviewer checks. |
| The `Intent:` strip (about 239 files) conflicts with `bug` worktrees. | W10 waits on it. |
| The root map passes its soft budget (8,293 of 8,192 B). | Basics rewrite existing bullets. |
| The deletion goal is missed. | Planned row by row; the closure logs it. |
| A grader keyed on one version fakes a drop. | AC11.3 and AC11.4 run each grader on both versions. |
| Each merge now runs the Linux suite, and the reviewer runs it too. | The cost Q4 and Q6 chose; the PLAN measures one run's wall time. |
| AC12.6's script drifts from `ci.yml`, reopening the escape path. | `ci.yml`'s Linux jobs call the script (AC12.6). |
| A worktree weakens its own verification command. | The reviewer sees it in the diff (AC12.5). |
| A revert reintroduces the bug the culprit fixed. | The revert and its redo land in one commit, gate 1 green (AC12.2). |
| The pile hides a bug that turns blocking. | The block list is re-judged at each new fact; a bug meeting it leaves the pile at once (AC13.2). |
| A cause group grows into a rewrite. | A cause larger than one task becomes an ADR and a next-rc AC (AC13.2). |
| The backfill guesses a candidate. | Only the instant → candidate derivation writes; the rest is `unknown` (AC13.1). |
| The SPEC is past its 24 KiB recommendation (0152 (2)). | Q5 placed the amendment in rc-8; W12 lines stay one line each. |

## Carried — the 0.5.0 map (ADR 0140; one candidate at a time)

- rc-9: W13's balance (scope ruling 2026-10-05), from a backlog entry carrying G8, G10 and the convergence demand in the operator's words: AC13.5, AC13.9, AC13.10, ADR C and the convergence indicator, its criterion fixed at rc-9's grill from cited sources. Also: the tests tree mirrors the package, except `tests/contract/test_docs_derived_from_memory.py`, which P-29 names, until check #7 rules; the unit tier spawns no processes, carrying rc-7's slow-class G4 growth (operator 2026-10-02: "Same-runner-class rule; slow-class growth to rc-8 (Recommended)", tied to `unit-tier-without-processes`); the production-faithful hook harness (0163); `worktree-rows-injected-not-monkeypatched`; `windows-integration-coverage-gap`; `repo-ci-sast`. With rc-8, they complete 0167. If pending at rc-8's closure (G6): T-050-183, T-050-187, T-050-188 (0177's accept) and T-050-189 (0180's), with `agent-behavior-evals` or AC10.14's law line.
- rc-10: the rest of the instruction corpus to AC12.11's bar (Q12); `public-law-language-neutral`; `dd-ask-me-owned-questioning-skill`, delivering 0165 and `dd-ai-eng-knowhow/AUTHORING.md:134` ("asks the whole frontier at once"), caught by 0165's repaired `measured_by`; `adr-born-at-release-with-options`; `adr-ledger-triage-process-rules`; `architecture-adr-section-generated`; F088, F089, F139–F148.
- rc-11: workspace replication (7 entries, ADRs 0171–0175, 0174 less AC11.0's slice); F084.
- rc-12, the promote: docs site F109, clone detection F110, launch prep F111; the residue (`spec-context-refusals-print-prose`, `privacy-baseline-one-parser`, `ledger-refusals-guess-specs-from-command-shape`, `ledger-reader-one-numbered-tolerant-iterator`, `doctor-in-a-fresh-worktree-lacks-rendered-specs-law`, F060); memory drift F123–F127; bug metrics F001, F004, F005, F009 (re-measured over AC9.3's links); the publish gate F067; `test_docs_derived_from_memory.py` leaves pytest after check #7 rules, `meta-tests-leave-pytest` exits delivered then; the audit checks never run, F137; the removal-authority notes (F069); PyJWT, closing at the ship; the evals gate at the promote (0178): the promote PR head is evaluated and its run logged on the work branch before the merge; at `approve`, `git diff --name-only <evaluated>..<tag>` lists only `CHANGELOG.md`, `.release-please-manifest.json` and `pyproject.toml` (its version line), else `eval.yml` runs on the tag sha first and only a non-blocking verdict approves. Open, the operator's before the promote (F4): ADR 0122's zero active backlog against the four post-0.5.0 evals follow-ups, `evals-release-gate-status`, `evals-harness-lanes-and-benchmark`, `evals-windows-smoke` and `devin-subagent-projection`.

## Open questions for the operator

- None for W8–W13: the 2026-10-03, 2026-10-04 and 2026-10-05 grill frontiers are empty. F4 is rc-12's (§Carried). Operator acts: 0176, 0177, 0178 and 0180's acceptances (§Decisions); W11's GitHub prerequisites (the `evals` environment, its secret, the required `ci.yml` job).
