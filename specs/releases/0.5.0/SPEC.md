# SPEC — Release: 0.5.0

**Status:** Approved
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-09-27
**Origin:** bugs:sa-reaper-destroys-its-own-hold-before-ttl,sa-context-dead-removes-repos-outside-the-reaper,sa-public-install-unlinks-operator-files-outside-its-ledger,sa-gate-allows-root-entries-the-reaper-moves,sa-doctor-reaps-harness-owned-entries,sa-public-install-writes-the-root-map-into-product-repos,sa-scoped-public-install-prunes-the-gate-wiring,sa-ledger-verbs-append-histo-before-validating-the-pair,sa-private-match-rendering-has-three-renderers,sa-gate-blind-on-cursor-copilot-devin,sa-codex-policy-allows-write-capable-commands,sa-specs-upgrade-writes-through-symlinks,pre-push-gate-never-runs-under-core-hookspath,sa-seven-workspace-root-rules,sa-bind-has-two-stores,sa-fix-lines-not-built-by-cli-line,sa-rich-printer-wraps-fix-lines,sa-unfixable-doctor-findings-say-doctor-fix,sa-placement-rules-contradict-tree8,sa-registry-schema-version-has-three-grammars,sa-spec-doc-033-duplicates-bugs-check,sa-ledger-write-seam-redacts-less-than-push-refuses,sa-backlog-status-has-no-single-authority,sa-promote-has-no-verb,sa-status-line-has-two-parsers,sa-adr-measured-by-pattern-refuses-real-checks,sa-specs-tree-state-read-five-ways,sa-memory-atom-has-two-grammars,sa-release-json-validated-three-times,sa-reconcile-certify-skip-the-workspace-walk,sa-doctor-job-not-a-required-check,sa-context-repo-mapping-falls-back-to-the-name,sa-editable-install-reports-a-frozen-version,sa-subjects-resolve-is-circular,sa-hook-parity-claims-false-and-interpreter-rules-diverge,sa-reviewer-persona-body-contradicts-its-tools,sa-specs-init-writes-unrendered-law,sa-gate-path-classes-diverge-from-the-law,sa-tool-caches-land-outside-the-cache-zone,sa-live-work-branch-named-three-ways,sa-principal-branch-defaults-to-main-and-cut-point-diverges,sa-audit-close-archives-without-validating,sa-staged-assets-without-consumers,sa-expiry-has-two-clocks,sa-handoff-self-pull-requirement-diverges,sa-specs-upgrade-stamps-any-target-and-memory-vocabulary-diverges,sa-ledger-vocabulary-and-atomic-write-duplicated-in-scripts,sa-text-restates-rules-the-code-contradicts,sa-consumer-law-carries-library-facts

---

## Problem and context

Operator, 2026-09-26: "não adicione fix em cima do que ta quebrado ... agora so aceito 80% pra mais com
o restante permanecendo mapeados". 2026-09-27: "se não resolvermos os testes é impossível resolver o problema na raiz".

- Ledger: 49 open (22 C, 11 H, 11 M, 5 L), exactly the Origin: 48 packages from 142 verified findings
  plus the hooks-path bug (`2c1faf65`).
- 0.4.7's first-run rubric D1–D10: **44/100** (Claude 50, non-Claude 40); 3 stalls.
- As-is (PLAN §1): every authority unit carries ≥ 2 prior bugs, so REBUILD; net about −2569 lines.
- Tests: 65k lines against 31k production; candidate 3 moved +4241/−3111 for +318; fakes and the hook
  harness hard-code 5 questions.

## Objective

Each question the 49 bugs name gets one authority, behavior row and public seam; every other mechanism,
tests and fakes included, consults it or goes; definition, review, CI and closure refuse a second
authority or an uncited assertion; code and tests shrink; 0.5.0 publishes per FR7.

## Terms (enter `CONTEXT.md`, AC5.6)

- **Authority** — the one symbol, command or file answering a question; others **consult** (call) it.
- **Systemic ambiguity** — two mechanisms (code, or law an agent executes) answering one question with
  divergent rules. _Avoid_: drift, duplication.
- **Behavior row** — a Given/When/Then statement `<bug-id>#<id>` naming its authority and seam.
- **Cross-check test** — one input set fed to two live readers, asserting one verdict.
- **Ratchet allowance** — violations a ratchet tolerates: `file:symbol` → the open bug id deleting it,
  or `parity:<test>`. _Avoid_: baseline.
- **Resolution contract** — a RED at the question's seam failing at definition; GREEN; losers gone with
  their tests and fakes; `bugs.py resolve` with the evidence triple, net-negative unless an AC excepts it;
  commit shape 3.

## Decisions

A parenthesized `00NN` is an ADR: 0050–0088 hold the operator-accepted decisions, appended at
definition (handoffs in `reports/main-thread/20260927-050-c4-evidence/`); per-bug ones sit in the
table. Over the as-is, the grill wins.

- 0.5.0 is CRITICAL (`_RELEASE.json` log 2026-09-26T23:02:09Z); every verified package is a bug; Flow 2
  plus a never-again mechanism (0050): FR5 generic, FR6 library (0052).
- DEC-1..13 as recommended, one ADR each (0058–0069 in order): 1a 2a 3b 4a 5a 6a 7a 8a 9b (+a on
  Devin) 10a 12a 13a; DEC-11 deferred (0053).
- Publish gate: FR7, overriding "0 open bugs before publish" for 0.5.0 only (0051).
- Behavior first: the single behavior is stated before any test is touched; a failing old test is a
  question, never an order (0070). Test strategy: FR9 (0071).

## Bugs, their question and the one authority

WP = plan package (HP: hooks-path bug); † = candidate-3 files; tests = audit net test lines before
FR9's pruning; mirr = mirrored (each side pinned by its own tests) / all findings.

| WP | bug id | question | the one authority | tests | mirr |
|---|---|---|---|---|---|
| | **Wave 0 — data loss, leaks, gate holes (14)** | | forced-pass 8 | +503 | 17/37 |
| 02 | sa-reaper-destroys-its-own-hold-before-ttl | may a hold die before its TTL | `sweep.move`; N moves = N holds; "one hold per origin per day" void (0074) | +40 | 1/2 |
| 03 | sa-context-dead-removes-repos-outside-the-reaper † | how a dead repo leaves disk | `_reap_dead_repo` over `all_repos()`; unpublished = any branch | +78 | 2/3 |
| 04 | sa-public-install-unlinks-operator-files-outside-its-ledger | who deletes in harness dirs | `_reconcile_install_ledger` | +5 | 1/1 |
| 05 | sa-gate-allows-root-entries-the-reaper-moves | may a root entry exist | `workspace_layout.verdict` (0058) | +75 | 3/5 |
| 06 | sa-doctor-reaps-harness-owned-entries | who judges harness dirs | the install ledger (0059) | +2 | 0/2 |
| 07 | sa-public-install-writes-the-root-map-into-product-repos † | who writes a repo `AGENTS.md` | `canon.REPO_LAW` via `specs init` | -119 | 2/3 |
| 08 | sa-scoped-public-install-prunes-the-gate-wiring | what a whole install is | one `InstallPlan` | +14 | 1/2 |
| 09 | sa-ledger-verbs-append-histo-before-validating-the-pair | did a refusal write | the script checks both files, then writes the pair | +80 | 0/2 |
| 11 | sa-private-match-rendering-has-three-renderers † | how a match is shown | `redaction.mask` everywhere, `privacy_check.py:318` too (0086) | +25 | 2/4 |
| 12 | sa-gate-blind-on-cursor-copilot-devin | is every tool call judged | `pre_gate` + `HOOK_DIALECTS`; no blocking contract = "gate not enforced" (0054) | +60 | 2/6 |
| 13 | sa-codex-policy-allows-write-capable-commands | unprompted Codex commands | the rendered `.rules`: `rg ls cat`, `sed -n` | +37 | 0/1 |
| 14 | sa-specs-upgrade-writes-through-symlinks | how a fixed section is written | one symlink-refusing writer | +65 | 1/2 |
| 32 | sa-doctor-job-not-a-required-check | which checks gate | `ci.yml`; `checks_for()`; an in-repo required-checks file (0078) | +71 | 1/3 |
| HP | pre-push-gate-never-runs-under-core-hookspath | where git runs the gate | `git rev-parse --git-path hooks` for install and doctor; a foreign `pre-push` refused with its one line (0057, 0085) | +70 | 1/1 |
| | **Wave 1 — stalls, loops, fixes that never clear (15)** | | forced-pass 20 | +13 | 27/49 |
| 15 | sa-seven-workspace-root-rules † | the workspace root | `resolve_workspace_root` | +108 | 1/3 |
| 15 | (fence) | which roots may a dadaia process act on | `core/workspace_resolver` fence (0088) | +10 | — |
| 16 | sa-bind-has-two-stores † | is the session bound | `resolve_bind` (0060); a native id, no bind: `repos/<slug>/` writes refused, fix `context bind <owner>` (0072) | +115 | 1/3 |
| 17 | sa-fix-lines-not-built-by-cli-line † | how a fix line is written | `core/cli_line` | +140 | 3/7 |
| 18 | sa-rich-printer-wraps-fix-lines † | who prints a refusal | `cli/_fail.fail`, exit 1; Click usage errors keep 2 (0073) | +75 | 3/4 |
| 19 | sa-unfixable-doctor-findings-say-doctor-fix | fix of an unfixable finding | the finding's own `fix_line` | +100 | 1/1 |
| 20 | sa-placement-rules-contradict-tree8 | where a stray specs file goes | TREE-8 | -40 | 1/3 |
| 21 | sa-registry-schema-version-has-three-grammars † | readable registry versions | `parse_schema_version` | +100 | 3/3 |
| 22 | sa-spec-doc-033-duplicates-bugs-check | is a bug record valid | `bugs.py check` + schema | -670 | 3/4 |
| 23 | sa-ledger-write-seam-redacts-less-than-push-refuses | what a ledger may store | the pre-push matcher, refusing at the write seam | +10 | 2/2 |
| 24 | sa-backlog-status-has-no-single-authority | live status; the pick | `backlog.py`; SPEC `Origin` (0062, 0063); `deferred` is live (0076) | -40 | 3/4 |
| 25 | sa-promote-has-no-verb | how a promote is recorded | `release.py ship` (0064) | -70 | 2/3 |
| 26 | sa-status-line-has-two-parsers | which `**Status:**` counts | `extract_status` at line start; no blockquote form (0075) | +60 | 0/1 |
| 27 | sa-adr-measured-by-pattern-refuses-real-checks | what `measured_by` names | free text; `doctor_adr` (0065) | -10 | 0/2 |
| 28 | sa-specs-tree-state-read-five-ways † | the specs tree state | `specs_version.state()` | +145 | 2/4 |
| 29 | sa-memory-atom-has-two-grammars | atom valid; catalog fresh | `_memory_schema.parse` | -10 | 2/5 |
| | **Wave 2 — consolidations (8)** | | forced-pass 2 | +475 | 11/17 |
| 30 | sa-release-json-validated-three-times | valid state; live release | `release.py check`; legacy `next/` not live; `new` refuses while `check` is red (0077) | -100 | 3/5 |
| 31 | sa-reconcile-certify-skip-the-workspace-walk | is an upgrade clean | doctor; `certify` (0069) | +116 | 1/2 |
| 33 | sa-context-repo-mapping-falls-back-to-the-name | a context's repo | the context registry | +101 | 1/2 |
| 34 | sa-editable-install-reports-a-frozen-version | the running version | `provider_version()`, rebuilt in place | +91 | 0/1 |
| 35 | sa-subjects-resolve-is-circular | does a subject ref resolve | doctor `SubjectRegistry` | +39 | 2/3 |
| 36 | sa-hook-parity-claims-false-and-interpreter-rules-diverge | hooks; interpreter | `HOOK_DIALECTS`; the wrapper (0066, 0067); Devin gets `ctx_inject`, `pre_gate`, the reaper (0079) | +147 | 2/2 |
| 37 | sa-reviewer-persona-body-contradicts-its-tools | may the reviewer write | persona `tools`, `read_only` | +48 | 1/1 |
| 38 | sa-specs-init-writes-unrendered-law | the canon table text | `render_registry_tables` | +33 | 1/1 |
| | **Wave 3 — design debt (12)** | | forced-pass 5 | -139 | 14/30 |
| 39 | sa-gate-path-classes-diverge-from-the-law | PROTECTED/ADDITIVE paths | one classifier; the literal hook-wiring floor, never the manifest (0055) | -5 | 2/5 |
| 40 | sa-tool-caches-land-outside-the-cache-zone | where caches live | absolute `.dadaia/tmp/<tool>-cache`; `.dadaia/.cache/` deleted (0080) | +30 | 1/1 |
| 41 | sa-live-work-branch-named-three-ways † | version; work branch | release-please; `<work><live id>` from `_RELEASE.json` (0068) | +37 | 0/2 |
| 42 | sa-principal-branch-defaults-to-main-and-cut-point-diverges † | an undeclared principal | the `specs init` detector | +44 | 1/2 |
| 43 | sa-audit-close-archives-without-validating | is an audit closable | `audit.py`; mixed deferred/rejected closes `deferred`, none `none` (0081) | -340 | 2/3 |
| 44 | sa-staged-assets-without-consumers | consumed assets | the real consumer | -100 | 2/3 |
| 45 | sa-expiry-has-two-clocks | has a marker expired | zone TTL via `sweep` | +10 | 2/2 |
| 46 | sa-handoff-self-pull-requirement-diverges | is `self_pull` required | handoff schema v1.2 | +5 | 1/1 |
| 47 | sa-specs-upgrade-stamps-any-target-and-memory-vocabulary-diverges | the upgrade target | `CANONICAL_SPECS_VERSION`; a two-tier tree refused unstamped (0082) | +10 | 1/2 |
| 48 | sa-ledger-vocabulary-and-atomic-write-duplicated-in-scripts | ledger vocabulary | the stdlib scripts; the doctor compares exactly (0083) | +45 | 1/3 |
| 49 | sa-text-restates-rules-the-code-contradicts | a restated rule | the code or its test | +80 | 1/5 |
| — | sa-consumer-law-carries-library-facts | projected law | the consumer's tree; free-text surfaces, only `unknown` refused (0084) | +45 | 0/1 |

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
- AC5.6 `CONTEXT.md` carries the Terms above and `wave`, a harm-ordered group of a candidate's bugs.
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
- AC7.2 Of the 49 bug ids in this SPEC's **Origin** (the ledger's open set at definition), at least 40 (80%)
  are `resolved`, all 14 wave-0 ids among them.
- AC7.3 Every unresolved Origin id stays `open`, in the closure `dispositions` log entry with its reason
  and next vehicle; the entry states the 0.5.0-only override of "0 open bugs before publish".

### FR8 — Shrink mandate

- AC8.1 The candidate nets negative over `dadaia_workspace/**` minus tests (about −2569) and over
  production Python outside `public/`; both logged at closure.
- AC8.2 New units are the three as-is ADD rows: `workspace_layout.verdict` (a move), a stdlib
  `_shared/_privacy.py` pinned by byte parity, `release.py ship`; WP-34's `provider_version()` is an
  existing reader rebuilt in place. No new doctor code, state file or schema; flags only leave.

### FR9 — Test strategy

Baseline (the evidence's `c4/tests-audit-*.json`): 69/133 findings mirrored, 130/133 with no cross-check, 35
forced-pass commits; 261 KEEP, 157 REWRITE, 152 DELETE-LOSER, 24 DELETE-DUP, 27 DELETE-HOLLOW, 239 MISSING.

- AC9.1 Statements are the audits' `<bug-id>#<id>` rows, from the authority, the law or a decision, never
  a test. The closure memory pass adds each resolved bug's rows to `QUALITY.md` `## Test architecture` →
  `### Behavior rows` (0071; the law has no "Part 2").
- AC9.2 Every test module touching a question declares `Intent: CONTRACT — <bug-id>#<id>`; a contract
  test fails on an id found in neither the audits nor the rows.
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
- AC9.9 Net test lines are ≤ 0 at closure: the audits sum +852 (about +530 after FR6, AC9.4–9.5), so a
  suite-wide pruning pass removes DELETE-HOLLOW, DELETE-DUP, text pins outside law-file canon and the
  `WORKSPACE_ROOT`-rung tests. A positive net is a HIGH review finding.
- AC9.10 mutmut runs on each row's authority function: review evidence, never a push gate.
- AC9.11 Closure re-measures the mirrored and cross-checked counts of resolved packages against the
  baseline, logging both; a resolved package has 0 mirrored findings and 0 live cross-checks.
- AC9.12 `sa-seven-workspace-root-rules#S11` (0088; excepts S1's env clause): no dadaia process, nor
  a child inheriting it, acts on a root listed in `DADAIA_FENCED_ROOTS`; the suite and every mutating
  probe set it; one `.dadaia/AGENTS.md` line states it; seam `test_suite_cannot_reach_the_instance.py`.

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

## Candidate 3

- It resolved `sa-pre-push-and-publish-scan-disagree-on-secret-shapes` (`eb4f4b02`).
- Its cuts (f) associated-repo publish and (h) uncommitted-work refusal are taken; (g) dead's work-branch
  refusal stays (0056). Its AC6.1 matches role names exactly, case-sensitively (0087).
- `ffb30aa0` answered WP-41 with the losing side (`work_name` = last tag + 1); AC4.2 corrects it.

## Out of scope and deferred

- Candidates 5, 6, 7 (0039 included) → the next release, their bug parts (WP-05, 06, 39, 40) fixed
  here on today's code; DEC-11 with candidate 5 (0053).
- Operator actions: apply WP-32's required-checks file to branch protection, Compliance included;
  prune obsolete harness globs from `instance_exceptions.txt`.
- Clone detection.

## Dependencies, order and risks

- Order: wave 0 (WP-32 and `release-as` in it; the hold fix before other deleters); then FR5, FR6 (allowance born
  at today's counts, keyed to these bugs) and FR9's fakes and hook harness, on which every later
  wave's tests rest; then waves 1, 2, 3.
- Candidate 3 overlaps WP-03, 07, 11, 15, 16, 17, 18, 21, 28, 41, 42: each starts after it closes.
- Risk: AC9.5 turns about 60 hook tests red on the real root rung.
- Decided (0088): the fence is a feature, not a test rung (AC9.12).
- Risk: "gate not enforced" caps D8/D9; AC6.7 blocks merges only once protection lists the job.
