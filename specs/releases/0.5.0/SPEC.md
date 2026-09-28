# SPEC — Release: 0.5.0

**Status:** Approved
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-09-27
**Origin:** bugs:sa-reaper-destroys-its-own-hold-before-ttl,sa-context-dead-removes-repos-outside-the-reaper,sa-public-install-unlinks-operator-files-outside-its-ledger,sa-gate-allows-root-entries-the-reaper-moves,sa-doctor-reaps-harness-owned-entries,sa-public-install-writes-the-root-map-into-product-repos,sa-scoped-public-install-prunes-the-gate-wiring,sa-ledger-verbs-append-histo-before-validating-the-pair,sa-private-match-rendering-has-three-renderers,sa-gate-blind-on-cursor-copilot-devin,sa-codex-policy-allows-write-capable-commands,sa-specs-upgrade-writes-through-symlinks,pre-push-gate-never-runs-under-core-hookspath,sa-seven-workspace-root-rules,sa-bind-has-two-stores,sa-fix-lines-not-built-by-cli-line,sa-rich-printer-wraps-fix-lines,sa-unfixable-doctor-findings-say-doctor-fix,sa-placement-rules-contradict-tree8,sa-registry-schema-version-has-three-grammars,sa-spec-doc-033-duplicates-bugs-check,sa-ledger-write-seam-redacts-less-than-push-refuses,sa-backlog-status-has-no-single-authority,sa-promote-has-no-verb,sa-status-line-has-two-parsers,sa-adr-measured-by-pattern-refuses-real-checks,sa-specs-tree-state-read-five-ways,sa-memory-atom-has-two-grammars,sa-release-json-validated-three-times,sa-reconcile-certify-skip-the-workspace-walk,sa-doctor-job-not-a-required-check,sa-context-repo-mapping-falls-back-to-the-name,sa-editable-install-reports-a-frozen-version,sa-subjects-resolve-is-circular,sa-hook-parity-claims-false-and-interpreter-rules-diverge,sa-reviewer-persona-body-contradicts-its-tools,sa-specs-init-writes-unrendered-law,sa-gate-path-classes-diverge-from-the-law,sa-tool-caches-land-outside-the-cache-zone,sa-live-work-branch-named-three-ways,sa-principal-branch-defaults-to-main-and-cut-point-diverges,sa-audit-close-archives-without-validating,sa-staged-assets-without-consumers,sa-expiry-has-two-clocks,sa-handoff-self-pull-requirement-diverges,sa-specs-upgrade-stamps-any-target-and-memory-vocabulary-diverges,sa-ledger-vocabulary-and-atomic-write-duplicated-in-scripts,sa-text-restates-rules-the-code-contradicts,sa-consumer-law-carries-library-facts,sa-implementation-adds-before-it-deletes,sa-hook-files-written-by-table-and-by-hand,sa-projected-file-judged-by-four-verifiers,sa-codex-effort-set-by-policy-and-by-tier,sa-frontmatter-split-five-ways,sa-privacy-match-has-two-matchers,sa-denylist-file-has-three-shapes,sa-ledger-script-paths-in-two-tables,sa-json-schema-validated-by-two-engines,sa-doctor-finding-has-four-shapes,sa-session-liveness-has-two-rules,sa-agent-model-resolved-by-two-modules,sa-release-id-has-three-grammars,sa-missing-memory-file-reported-twice,sa-command-tree-walked-twice,sa-path-segment-judged-by-two-matchers,sa-certify-children-resolve-the-live-workspace,sa-git-output-split-by-unicode-line-breaks
- Operator demand, 2026-09-28 (FR10), verbatim: "SE ESTAMOS RESOLVENDO AMBIGUIDADES, QUER DIZER QUE HAVIA
  REPETIÇÕES. COMO QUE AUMENTOU O NUMERO DE LINHAS DE CODIGO E NUMERO DE TESTES???? ISSO EU NÃO ACEITO." /
  "VC VIOLOU A REGRA FUNDAMENTAL DE DELEÇÃO -> ATUALIZAÇÃO / REFAZER / RECONSTRUIR E SOMENTE DEPOIS
  ADICIONAR. ISSO É FUNDAMENTAL DO DADAIA-WORKSPACE. REGISTRE, SIGA, OBEDEÇA" / "TESTES DEVEM DIMINUIR PELO
  MENOS EM 40% E MELHORAR A QUALIDADE E MEDIÇÃO DE COMPORTAMENTOS" / "NÃO ACEITO MENOS QUE 40% DOS TESTES E
  EM RELAÇÃO A IMPLEMENTAÇÃO REDUÇÃO DE PELO MENOS 40% DAS LINHAS DE CODIGO COM TODAS AS FUNCIONALIDADES
  ESPECIFICADAS FUNCIONANDO E SEM AMBIGUIDADE SISTEMICA. REGISTRE ISSO, AO FINAL VC DEVE PRESTAR CONTAS"
- Operator demand, 2026-09-28 (FR10 refinement), verbatim: "VOCÊ DEVE REDUZIR AS LINHAS DE CÓDIGO ENTRE 30
  E 40% SEM QUEBRAR AS FUNCIONALIDADES. SE VOCÊ QUEBRAR UMA FUNCIONALIDADE OU FEATURE OU COMPORTAMENTO
  ESPERADO E JÁ DEFINIDO VOCÊ ESTÁ ERRADO. NÃO VÁ APAGAR COISAS INDEVIDAS"
- Operator demand, 2026-09-28, verbatim: "devemos sempre, sempre, sempre minimizar as linhas de código,
  minimizar os testes, mantendo qualidade, requisitos, features especificadas e documentadas funcionando,
  sem ambiguidade e contradições sistêmicas... Sou contra algo verboso que poderia ser feito de forma
  menos verbosa."

---

## Problem and context

Operator, 2026-09-26: "não adicione fix em cima do que ta quebrado ... agora so aceito 80% pra mais com
o restante permanecendo mapeados". 2026-09-27: "se não resolvermos os testes é impossível resolver o problema na raiz".

- Origin: 67 ids — the 49 open at definition (22 C, 11 H, 11 M, 5 L: 48 packages from 142 verified
  findings plus the hooks-path bug `2c1faf65`), the work-order bug (`11fe60bb`) FR10's survey (`c3f48ab8`) and the git-output bug (`32310314`).
- 0.4.7's first-run rubric D1–D10: **44/100** (Claude 50, non-Claude 40); 3 stalls.

## Objective

Each question an Origin bug names gets one authority, behavior row and public seam; every other mechanism,
tests and fakes included, consults it or goes; definition, review, CI and closure refuse a second
authority or an uncited assertion; code and tests shrink; 0.5.0 publishes per FR7.

## Terms

`CONTEXT.md` §Authorities holds them (AC5.6).

## Decisions

A parenthesized `00NN` is an ADR: 0050–0088 hold the operator-accepted decisions, appended at
definition (handoffs in `reports/main-thread/20260927-050-c4-evidence/`); per-bug ones name their
bug. Over the as-is, the grill wins.

- 0.5.0 is CRITICAL, Flow 2 plus a never-again mechanism: FR5 generic, FR6 library (0050, 0052).
- DEC-1..13: 0058–0069; DEC-11 deferred (0053).
- Publish gate: FR7 (0089).
- Behavior first (0070); test strategy FR9 (0071).

## Bugs, their question and the one authority

PLAN §1.1 gives each Origin bug's question its one authority; PLAN §2 its wave and WP.

## Functional requirements

### FR1 — Wave 0

- AC1.1 Every wave-0 bug meets the resolution contract; net-positive exceptions: `context dead` (+3),
  the Cursor/Copilot/Devin gate (+12), the hooks-path install (+5).
- AC1.2 A file outside the prior install ledger survives `public install`; two same-day reaps leave two
  holds; `context dead` refuses an unpushed branch or a linked worktree, else holds the repo in
  `.dadaia/reaped/`; `specs upgrade` and `doctor --fix` never write a symlink target.
- AC1.3 With `core.hooksPath` set, a push carrying a denylisted term is refused; the doctor reports a
  foreign `pre-push` at `git rev-parse --git-path hooks` with a runnable `fix:`.
- AC1.4 Per harness, a vendor-documented native payload gets the Claude payload's verdict through the
  rendered wrapper; no wrapper emits an explicit allow.
- AC1.5 The rendered Codex policy allows no write- or exec-capable prefix.
- AC1.6 `release-please-config.json` carries `"release-as": "0.5.0"` until the release PR merges; the
  next commit drops it.
- AC1.7 `release.yml` consumes `ci.yml`; a contract test pins every `ci.yml` job in the in-repo
  required-checks file.

### FR2 — Wave 1

- AC2.1 Every wave-1 bug meets the resolution contract; exception: unfixable findings (+7).
- AC2.2 Every BLOCK, refusal and doctor finding prints one `fix:` that, run as printed from the root
  and from `repos/<slug>`, clears it.
- AC2.3 Every refusal prints via `cli/_fail.fail`: `Error:`, then `fix:`, exit 1, unwrapped at any width;
  only a Click usage error exits 2.
- AC2.4 Cross-checks give one verdict from every live reader of bind, registry version, status line,
  specs-tree state, atom grammar, backlog status, bug record.
- AC2.5 A release runs `new` → IMPLEMENTATION → CLOSURE → `ship` → `new` by verbs, doctor clean at each
  step; a `* [ ]` task refuses CLOSURE.

### FR3 — Wave 2

- AC3.1 Every wave-2 bug meets the resolution contract; exception: unrendered law (+4).
- AC3.2 `certify` judges all three doctor sections; every recipe command passes the wheel's `--help`.
- AC3.3 Without `.dadaia/.venv` every wrapper exits 0 with one stderr warning.

### FR4 — Wave 3

- AC4.1 Every wave-3 bug meets the resolution contract; exceptions: principal detection (+2), path
  classes (capped at +5, else the task stops for the architecture lens).
- AC4.2 Baseline, gate and `work_name` name the work branch `<work prefix><live release id>`; the last
  tag + 1 rule is deleted.
- AC4.3 `CONTEXT.md` is the one glossary; `Part 1/Part 2` and "PyPI + 1 patch" leave shipped text.
- AC4.4 Consumer-projected law names no library layer, ratchet, test file or release tool.
- AC4.5 No shipped law names `.dadaia/.cache/` (root map §4, the `DADAIA_ZONES` table); tool caches sit
  at absolute `.dadaia/tmp/<tool>-cache`, `QUALITY.md`'s relative path too.

### FR5 — Never-again mechanism, generic layer

- AC5.1 `dd-release-definition` §2: PLAN §1 carries the Authorities table (`question | authority |
  consults | deleted`), a row per touched question.
- AC5.2 `release.py phase IMPLEMENTATION` refuses, one fix line each, a §1 without the table, with an
  empty authority, or with two authorities for one question — structure only (0041); a fixture pair
  proves it.
- AC5.3 The PLAN §1 skeleton the fix names carries the Authorities header.
- AC5.4 SLOP S10 is "second authority", HIGH; Axis 3 says "increased" for a diff adding one or an
  allowance key; the architecture lens checks `deleted` gone, `consults` calling.
- AC5.5 `dd-audit-project` pillar 2 gains a fixed hunt for restatements and second authorities.
- AC5.6 `CONTEXT.md` carries the Terms and `wave`, a harm-ordered group of a candidate's bugs.
- AC5.7 `dd-code-review`'s test lens: a test touching a question cites its statement id and no assertion
  changes without one; a miss is HIGH and the verdict REJECTED.
- AC5.8 V35 (2,863 skill lines, down-only) stays green: FR5's skill growth is paid by skill-text cuts.

### FR6 — Never-again mechanism, library layer

- AC6.1 `test_zone_registry.py`'s `_CANONICAL_SETS` gains ledger vocabularies, phases, trio names,
  gitflow keys; `_restated_law_lines` scans every `public/**/*.md` but archives.
- AC6.2 V37 flags duplicate top-level definitions across modules, skill scripts and hooks (a fixture
  trips it); `test_required_evidence_has_one_home.py` folds into it and is deleted.
- AC6.3 V38 flags destructive calls outside `features/spec_context/sweep.py`; import-linter forbids
  `shutil` elsewhere.
- AC6.4 V39: every doctor code has a fix-clears case or a `report-only` key.
- AC6.5 An unlisted hit fails, a vanished key fails stale; a value is an open bug id or `parity:<test>`.
- AC6.6 The closure allowance is a subset of the birth allowance; the closure log records both sizes.
- AC6.7 The ratchets and AC9.2's contract test run in a required CI job (AC1.7).
- AC6.8 The mechanism adds no production Python line outside `public/` and no verb.

### FR7 — Publish gate

- AC7.1 The rubric D1–D10, run fenced on the wheel built from the promote head, scores ≥ 80/100 on the
  first run; the three scores enter the closure log.
- AC7.2 Superseded by AC10.4.
- AC7.3 Superseded by AC10.4.

### FR8 — Shrink mandate

- AC8.1 Production and test lines meet AC10.1–AC10.2; both logged at closure.
- AC8.2 New units are the three as-is ADD rows: `workspace_layout.verdict` (a move), a stdlib
  `_shared/_privacy.py` pinned by byte parity, `release.py ship`; WP-34's `provider_version()` is an
  existing reader rebuilt in place. No new doctor code, state file or schema; flags only leave.

### FR9 — Test strategy

Baseline (the evidence's `c4/tests-audit-*.json`): 69/133 findings mirrored, 130/133 with no cross-check.

- AC9.1 Statements are the audits' `<bug-id>#<id>` rows, from the authority, the law or a decision, never
  a test. The closure memory pass adds each resolved bug's rows to `QUALITY.md` `## Test architecture` →
  `### Behavior rows` (0071; the law has no "Part 2").
- AC9.2 A test touching a question declares its `<bug-id>#<id>` per AC10.3; a contract test fails on an
  id found in neither the audits nor the rows.
- AC9.3 Each question has one public seam, a CLI verb subprocess or `pre_gate` via the rendered wrapper; an
  in-process test asserts only the authority function.
- AC9.4 `FakeGitClient` and the four `ObjectSource` fakes give way to one real-git tmp fixture;
  `FakeContextStore` passes `_store_contract.py` and a save/update parity test, or is deleted.
- AC9.5 The hook harness spawns the real rendered hook in production's environment (no `WORKSPACE_ROOT`,
  no cwd from it), driving `pre_gate` only; `_POLICY_DRIVER` is gone.
- AC9.6 Each second mechanism deleted here meets a cross-check while both readers live; the commit
  deleting the loser deletes it and the loser's tests and fakes (`git grep -w <symbol> tests/` empty).
- AC9.7 A deleted path's golden rows leave with it; a surviving row never changes in a commit touching
  `dadaia_workspace/**`; no expected value comes from the code under test (`rule_fix(rule)`).
- AC9.8 An assertion changed in the window cites a statement id; the review REJECTS one that does not.
- AC9.9 Superseded by AC10.2.
- AC9.10 mutmut runs on each row's authority function: review evidence, never a push gate.
- AC9.11 Closure re-measures the mirrored and cross-checked counts of resolved packages against the
  baseline, logging both; a resolved package has 0 mirrored findings and 0 live cross-checks.
- AC9.12 `sa-seven-workspace-root-rules#S11` (0088; excepts S1's env clause): no dadaia process, nor
  a child inheriting it, acts on a root listed in `DADAIA_FENCED_ROOTS`; the suite and every mutating
  probe set it; one `.dadaia/AGENTS.md` line states it; seam `test_suite_cannot_reach_the_instance.py`.

### FR10 — Reduction and the work order

Baseline `9cd5fbf4`. Lines: `git grep -h '' <sha> -- '<pathspec>' | wc -l`; test functions: the sum of
`git grep -c 'def test_' <sha> -- 'tests/*.py'`.

- AC10.1 Production `dadaia_workspace/**/*.py` ≤ 23,480 lines (−30%, the floor), aiming at ≤ 20,125
  (−40%); baseline 33,543, pathspec `'dadaia_workspace/*.py'`.
- AC10.2 Tests `tests/**/*.py` ≤ 39,773 lines (baseline 66,289) and ≤ 1,237 test functions (baseline
  2,063); both −40%, pathspec `'tests/*.py'`.
- AC10.3 Every specified feature works. First, no documented feature, functionality or expected behavior
  breaks: every documented behavior (memory product atoms, `ARCHITECTURE.md`/`QUALITY.md`, Approved FRs,
  enforced law) maps to a test proving it, and that inventory stays green after every deletion batch.
  Then: the full suite is green on the three CI OSes; the fenced first-run rubric scores ≥ 80/100
  (AC7.1); each surviving test declares the ONE behavior it measures (a memory atom statement, an AC id
  or `<bug-id>#<id>`): its module's `Intent:` when every test in the module measures that behavior, else
  the first line of its own docstring; a table row carries its behavior id in the parametrize id; every
  behavior statement of every resolved 0.5.0 bug is cited by a test asserting its Then.
- AC10.4 Zero systemic ambiguity: every Origin bug id is `resolved`, replacing 0051's 80% floor (0089);
  the whole-library as-is survey finds no question answered by two authorities.
- AC10.5 The root map §1 (`public/data/AGENTS.md`) carries ONE bullet, binding production and tests at
  definition and implementation: "Every change minimizes code and tests: DELETE → REBUILD → UPDATE →
  KEEP → ADD last; verbose code, comments or tests that could be shorter are defects; every documented
  behavior keeps working."
  - A DELETE proves one of: no documented behavior; a duplicate whose one authority keeps the behavior;
    dead code.
  - A bug fix nets ≤ 0 in production and tests; the only exceptions are the production ceilings of
    AC1.1, AC2.1, AC3.1, AC4.1; tests have none.
  - The RED proof is a rewritten existing test when one exists.
  - `dd-bug-resolution` Phase 5/6 and `dd-test-stewardship` admission comply without restating it;
    this resolves `sa-implementation-adds-before-it-deletes`.
- AC10.6 A CI ratchet records the production-line, test-line and test-function ceilings and fails when
  any is exceeded; ceilings only go down.
- AC10.7 Closure publishes an accountability report of AC10.1–AC10.4, measured before (`9cd5fbf4`) and
  after: production lines, test lines, test functions, ambiguities resolved.

## Replaces

- Extra deleters: `move`'s hold removal, `dead`'s `rmtree`, install glob prunes, legacy removers,
  `reap_markers`, `Handoff.expires_at`.
- Second classifiers: the gate's "exists ⇒ operator" and glob matcher, the root `specs/` ADDITIVE arm,
  `_scan_harness_dirs`, basename `_is_law_path`, listed ADDITIVE prefixes.
- Second writers and renderers: the guardrail fan-out, `--only`, scope flags, the unrendered canon copy,
  `specs upgrade`'s writers, the `.git/hooks`-only install; `redact()` copies, `HistoRecord.redact`,
  `redact_text`, the doctor's redactor.
- Hooks answering allow: the explicit-allow translator, non-tool events, Kimi shim parsing, Codex
  `find`/`sed`, `_python_bin`'s fallback, parity claims.
- Extra resolution rules: `WORKSPACE_ROOT`, cwd walks, env-first binding, name fallbacks, six version
  readers, `work_name`'s last tag + 1, PyPI + 1.
- Hand-built fixes and printers: bare `dadaia`, `&&`, `doctor --fix` on unfixable findings, Rich
  wrapping, exit 3, exit 2 outside Click usage errors.
- Doctor ledger re-checks: `core/models/bugs.py`, SPEC-DOC-033/008/036/038, BL-SCHEMA's list, BL-STALE,
  CAT-1, `release_tree` rules, `JsonlRecordStore`'s write half, the case-folded dispositions.
- Extra grammars: SPEC-DOC-035, TREE-7, SPEC-DOC-002L, SPECS-VERSION, registry version ×3, the status
  window and blockquote, malformed → 0, the SemVer suffix, handoff v1/v1.1, terminal `deferred`.
- Hand-edit lifecycle: `picked`, `**Consumes:**`, ARCHIVED, `_archive/<v>/_RELEASE.json`, rc-N, a
  second task regex, histo before validation, four tmp-leaking writers.
- CI copies: `release.yml`'s matrix, certify's skipped section, transcribed recipe lines.
- Restated law: the `surface` enum, release-please in consumer law, `Part 1/Part 2`, `measured_by`'s
  pattern, `--target`, `setup.cfg`'s module list, false docstrings, `agents.index.json`, the `rules`
  family, the persona model fallback, `activity_class`, the `.dadaia/.cache/` zone.
- Tests as a third mechanism: `FakeGitClient`, the `ObjectSource` fakes, `_POLICY_DRIVER`, the injected
  `WORKSPACE_ROOT`, `test_required_evidence_has_one_home.py`, re-pinned goldens, the DELETE-* tests.
- Add-first fixes: the RED test written as an ADD before the fix (`dd-bug-resolution` Phase 5); the net
  rule measured on the feature's production only (Phase 6, `evidence_diff`).

## Candidate 3

Closed and merged (PR #273); its trio is in git at its CLOSURE commit, its decisions in 0056, 0087.

## Out of scope and deferred

- Candidates 5, 6, 7 (0039 included) → the next release, their bug parts (WP-05, 06, 39, 40) fixed
  here on today's code; DEC-11 with candidate 5 (0053).
- Operator actions: apply WP-32's required-checks file to branch protection, Compliance included;
  prune obsolete harness globs from `instance_exceptions.txt`.
- Clone detection.

## Dependencies, order and risks

- Order: FR10 DELETE batches first, then REBUILD/UPDATE (the open bug WPs), then ADD; the ratchets
  exist (T-050-35 done).
- Risk: "gate not enforced" caps D8/D9; AC6.7 blocks merges only once protection lists the job.
