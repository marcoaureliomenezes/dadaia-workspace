# SPEC — Release: 0.5.1

**Status:** Aprovado
**Release ID:** 0.5.1
**Owner:** product-engineer
**Opened:** 2026-08-28
**Consumes:** deepening-simplification-k1-k11

**Title:** Deepening simplification K1–K11 — one decider per fact.
**Source audit:** `software-architect` REVIEW-mode deepening audit of `c4a539c1`, 2026-08-28 —
handoff `.dadaia/handoff/dadaia-workspace/2026-08-28T183644Z-software-architect-deepening-audit.handoff.json`,
report `.dadaia/reports/dadaia-workspace/software-architect/20260828T183644Z-deepening-audit/`.
**Grill:** by inspection, 2026-08-28 — ten rulings **R1–R10**
(`.dadaia/tmp/claude-code/20260828/0.5.1-rulings.md`); no frontier question remained for the
operator after the `/goal` order.
**Vocabulary:** `codebase-design` / `DEEPENING.md` — *module*, *interface*, *seam*, *adapter*,
*depth*, *leverage*, *locality*, *deletion test*, *replace-don't-layer*.
**Branch:** `feature/0.5.1`, cut from `main` at the shipped `0.5.0`
(`DADAIA.md` §4; mechanics `dd-gitflow-default`).
**Segments:** `alpha-1 … alpha-4` — internal work boundaries, each closed by a `qa-engineer`
stewardship verdict committed on the branch; no merge, no PR, no `rc` burned (`RC-FLOW.md`).

---

## 1. Problem and context

**Ratification.** The operator ratified this release's scope (all of K1–K10, K11 as a ruling) and
its four waves by direct order on **2026-08-28** (`/goal`, recorded as rulings R1–R2). This SPEC
carries that order; it does not re-litigate it.

**The diagnosis, in the audit's words: layering enforced by lint, not by depth.** Nine
import-linter contracts are green, and every one of the repeated bug families is still two
shallow modules disagreeing about the same fact. A fact that matters is decided in several
places; a fix lands in one decider; the next reader reproduces the bug.

Measured over 110 inspected files at `c4a539c1`:

| Fact | Deciders today |
|---|---|
| "which context am I in" | **8** (`specs_resolver`, `cli/_specs_resolution`, `container.resolve_context` — 0 callers, `ctx_inject`, `sdd_post_gate`, `container._context_specs_dir`, `context show`, `sdd_gate`) |
| "which session am I" | **3** sid ladders; the record is keyed by the CLI-minted sid and read by the harness sid |
| "is this record stale" | **4** staleness predicates |
| "who reaps a dead record" | **4** GC authorities (`doctor`, `sdd_post_gate`, `ctx_inject`, `tmp_gc`); `presence-warn-*` reaped by nobody |
| "what a specs tree contains" | **3** canon definitions (`specs_canon` patterns, `scaffolder` writes, `doctor_structural` TREE sets) |
| "is a projection current" | **5** compare semantics, **4** sha sites, harness literals branching in 6 modules across 3 layers |
| "is this bug record valid" | **4** ledger parsers; **488** records incomplete for their status |
| "where is this handoff's artifact" | **10** readers; `core/models/handoff` has **0** importers |
| "is a frontmatter block well formed" | **4** parsers, **7** copies of `_FRONTMATTER_RE` |

Scale: production **53,059 LOC / 240 modules**; tests **82,935 LOC / 250 unit files** mirroring
those modules one-to-one; **642** bug records, **15** open at the audit (**12** at this
definition), **79** `caused_by` chains, **4** mutual-cause cycles. Dead weight shipped in the
wheel: **~180 LOC** of container lifecycle closures (including a `git add -A` committer, zero
callers since `b94aede3`) and **~1,700 LOC** of pre-v6 migrations. **23** core protocols, of
which **3** have two production adapters — the other 20 are hypothetical seams. **18** suppressed
import-linter edges.

The evidence is the ledger, not taste: `container.py` carries **22** fix commits on a file that
should have none; adding the `kimi` harness (`a94f112a`) touched **6** modules; the projection
clusters A–D hold **29** records and **13/13** of their fix commits *added* code; the
scaffold-fails-its-own-doctor property was violated **six times in six weeks**; the same
unicode-line-split defect was fixed in the record store on 08-24 and again in the doctor on
08-27. No ledger bug was ever fixed by swapping an adapter behind a hypothetical seam.

---

## 2. Objective

Give every fact in the list above exactly one deep module that decides it, and delete the
shallow deciders it replaces — net-negative in production LOC, with the tests rewritten at each
deepened interface.

---

## 3. Scope

**Standing rules for every FR** (`DADAIA.md` §7, the operator's standing order):

- **Replace, don't layer.** The deepened interface is written first with its table-driven test;
  the mirrored unit files named on the card are then deleted. A test that survives only by
  reaching past the interface is deleted with its subject.
- **Every FR deletes at least one decider** and is **net-negative in production LOC** (R3). A
  task whose diff only adds is rejected at review, whatever the tests say.
- **One adapter is a hypothetical seam; two adapters is a real one** (`DEEPENING.md`).
- **No puxadinho:** no new branch, flag, special case, second code path, cross-feature reach-in
  or side effect added to an existing feature to make a symptom go away.
- **Green at every commit:** `dadaia ci preflight`, `dadaia specs doctor`, `dadaia backlog
  doctor`, `dadaia public doctor`, `lint-imports`. No `--no-verify`, ever.
- **RED before GREEN** on the executed path for every bug in FR-12.
- **Naming comes from `CONTEXT.md`** (FR-11), which lands first (R4).
- **`product-engineer` has no shell.** Every measured number is captured by a task step run by
  an agent with a shell, under `.dadaia/tmp/<agent>/<YYYYMMDD>/`.

---

### FR-1 — K1: one `Invocation`, resolved once per process · segment `alpha-1`

New deep module `core/invocation.py`:
`resolve(*, explicit=None, target_path=None, payload=None, env, cwd, clock) -> Invocation`
returning `Invocation(workspace_root, session_id, context_name, repo_slug, specs_dir, mode,
release, phase, rung)`. `features/spec_context/session_identity.py` moves into `core` as the sole
reader/writer/GC of session records (`read_live · bind · touch · release · gc`). Hooks build it
from the payload, the CLI from its flags; every policy receives the value. One sid ladder, one
staleness rule, name→slug resolved **inside** the module, `target_path` validation inside.
Hooks already may import `core` (P-12) — no linter change.

Deletes: the 8 context ladders, 3 sid ladders, 5 `_resolve_workspace` copies,
`context._load_session`/`_session_is_stale`, `container.resolve_context` (0 callers),
`_context_specs_dir`'s root fallback, `reports.py:709`'s env read, 5 copies of the name-allowlist
regex — **~350 LOC**.
Tests: ~14 mirrored files (`test_specs_resolver*`, `test_specs_resolution`,
`test_common_sid_precedence`, `test_bind_resolution_seam_*`, `test_cli_bound_session_resolution`,
`test_codex_thread_id_bind`, `test_context_name_differs_from_repo_slug`, the ladder halves of
`test_ctx_inject*`, `test_sdd_gate`) → one table-driven `tests/unit/core/test_invocation.py` over
`(env, cwd, payload, records) -> Invocation`.
Memory: P-09 names `core.specs_resolver.resolve_context` as the single home; the home moves to
`core.invocation`. The principle stays true; its named module changes, so the ADR record of
T-051-05 carries that rename as a **proposed** decision (agent proposes, operator accepts).

### FR-2 — K2: presence owns liveness end-to-end · segment `alpha-2`

`presence.gc(ws, *, now, own_sid)` becomes the only reaper over records, markers, sentinels and
empty dirs; `is_stale(record, ttl, now)` the only predicate. Callers: `doctor --fix` and the
post-gate on its throttle. `sdd_post_gate` shrinks to ~40 LOC — only its `renew` and `touch`
calls survive the deletion test.

Deletes: `sdd_post_gate.py:213-537`, `_reap_zombie_lifecycle_runs` (reaper for a demolished
engine), `gate_policy._heartbeat_age_seconds`, `tmp_gc/service._age_seconds` and its marker lane,
two throttle-marker idioms collapsed to one — **~400 LOC**.
Tests: `test_post_gate_reap`, `test_doctor_presence_sweep`, `test_doctor_gc`, the `tmp_gc` marker
tests → one `test_presence_gc.py`.
Depends on FR-1 for the sid (the current "own" guard uses the wrong one).

### FR-3 — K3: one `ProjectionRule` table; harness as a real seam · segment `alpha-3`

`features/public` owns
`ProjectionRule(label, harness, dst, render: () -> bytes, compare: bytes|owned-slice|managed-block, ownership)`
and `projection_rules(root, plan) -> tuple[ProjectionRule, ...]`. `install(rules) -> Transcript`
and `doctor(rules) -> list[Line]` are two folds over it; the ledger is `[r.dst for r in rules]`.
`HarnessProjection(Protocol)` with **three** adapters (`claude`, `codex`, `kimi`) — a real seam.
The renderer is the only verifier: codex TOML is byte-compared exactly as Claude agents already
are. The port stops sitting at CLI-verb altitude, so a rule has a home outside the adapter.

Deletes: `runtime_expectations`, every `_step_*`/`_install_*`, the `"[ok] "/"[skip] "`
transcript-string protocol and its parsing, `_KIMI_DIRS`, `remove_stale_files` (0 callers),
`_render_codex_pack_agent` (0 callers), `_doctor_guardrail_pair` duplication, the dcx1/2/4/5/10
regexes (~250 LOC), 8 `from runtime_config import` stanzas + 4 `noqa: F401` shims,
`workspace/service._install_for_harnesses` — **~900 LOC**.
Tests: `test_public_assets_{install,doctor,profile,kimi,hooks,render}`,
`test_install_target_goldens`, `test_consumer_fanout*`, `test_codex_*` (5) → one "rule set per
profile" table test + one write/compare pair + golden renders per harness adapter.

### FR-4 — K4: one `CANON` table; scaffold is canon rendered, doctor is canon checked · segment `alpha-3`

`features/specs/canon` holds
`CANON: tuple[CanonEntry(pattern, kind, required_at_birth, template, area)]` with three
consumers: `scaffold(specs_dir)`, `check_tree(specs_dir)` and
`scaffold_entry(specs_dir, "releases/<id>/SPEC.md")`. The property
**`scaffold(t) ⇒ doctor(t) == []`** becomes one test and replaces six regression tests.

Deletes: the `scaffolder` numbered `_write` blocks (which write `releases_histo.jsonl`, absent
from `DADAIA.md` §6.2), `check_tree4_required_dirs`, `check_tree8_canon_root`'s inline list,
`check_archive_dirs_exist`, and the whole `features/spec_artifacts` package — which exists only
to dodge the cross-feature lint; its two writers become `scaffold_entry` — **~300 LOC**.
**Law drift fixed here (R7):** `dadaia_workspace/public/scaffold/releases/AGENTS.md` still
describes `RELEASE.jsonl` and a `reviews/` member; canon is `RELEASE.json` and no `reviews/`.
The generated `specs/releases/AGENTS.md` is re-projected from the corrected source.

### FR-5 — K5: status transitions are the interface; one ledger parser · segment `alpha-2`

`BugRecord.resolve(*, cause, caused_by, resolved_release, solution, evidence)`,
`.supersede(by)`, `.defer(reason)`, `.reject(reason)` — each returns a `BugRecord` or raises
`IncompleteTransitionError`; a status is unreachable without the fields that make it true.
`BugService.transition(id, verb, **fields)` runs inside `store.update`;
`RecordStore.iter_records(strict=True)` yields `T | MalformedLine` so malformed-line diagnosis
lives in the one parser; `SpecsDoctor(bug_store_factory=…)` receives the store it already injects
for findings. `dadaia bugs resolve <id> --cause --solution` is the verb. Legacy v5-fold records
take `migration_note="v5-fold-incomplete"` once and stop warning (the 488).
**Same shape, same task — the backlog's four checkers:** `backlog-v1.schema.json`,
`document._parse_active_entry`, `backlog/doctor._check_schema` and
`doctor_governance:212-280` collapse onto one.

Deletes: `_iter_native_bug_records`, the inline re-parse loop, the `bugs/*.md` `Status:` regex
checker (that file shape died two migrations ago), `governance_completeness_gaps`,
`coherence_violations`, `_print_coherence_warnings`, the SPEC-DOC-033 WARNING branch, status
handling in `_parse_set_options` — **~250 LOC**.

### FR-6 — K6: `features/handoff` owns discovery, version routing and artifact resolution · segment `alpha-3`

`HandoffIndex(workspace_root).scan(roots) -> Iterable[Handoff]`;
`Handoff.artifact_path() · .schema_version · .findings_summary() · .validate() -> ValidationResult`.
One artifact-path rule, one version router, the validator internal.

Deletes: `panel/reports_doctor.py`, `_detect_sidecar_version` + `_check_v10_compat`,
`_handoff_artifact_paths`, `api_reports._iter_handoffs` and its severity/expiry re-derivations,
`ValidatorPort`, and `core/models/handoff.py`'s zero-importer model — **~330 LOC**.
Tests: 12 reports test files (**2,162 LOC**) + the panel sidecar fixtures → `HandoffIndex` tests;
the CLI tests become exit-code tests.

### FR-7 — K7: split `chokepoints.service`; one verdict store · segment `alpha-2`

`chokepoints/{branch_policy, pre_commit, push_gate, verdict}.py` — the four modules the 1,042-LOC
file already is, each of its three suppressed import-linter edges marking one boundary.
`verdict.covering_verdict(paths, head_sha)` is the one reader, used by `doctor_release`, the push
gate and a Python-backed `pr-verdict-check`. Verdicts stop being 2 stores × 4 readers.

Deletes: `iter_security_approvals`, `gc_consumed_push_verdicts` (reachable only by hand),
`LEDGER_RELPATH`, `_Approval`, `GcOutcome`, the `gc-push-verdicts` CLI verb, the legacy
`caller_pid`/`pid_probe`/`ancestry` params, the second `_PathMasker` masking predicate, and 2–3
import-linter suppressions — **~300 LOC**, ignore-edge cap **18 → 15**.
Depends on FR-1: the pre-commit presence lane reads the session id.

### FR-8 — K8: one telemetry connection owner; table-driven panel routes · segment `alpha-4`

`TelemetryStore(db_path)` owns `open_read · open_write · migrate · integrity_check · quarantine`;
`TelemetryService(store, readers: Sequence[Reader], clock)` exposes `refresh · list_agents ·
list_sessions_by_agent · aggregate_sessions`; `Reader.ingest(store, now)`. Panel routes become a
table `(method, pattern, view_name, param_spec) -> views[name](**groups, **qs)`.
The user-global sqlite at `~/.dadaia`, shared by every workspace, gets an owner — which is why its
corruption bug was deferred for lack of one.

Deletes: `_try_build_telemetry` (moves into the container and shrinks), one of
`store/models.py`/`aggregator/models.py`, the `pricing_module`/`reader_factory` injections,
`AuthClass` and `_BEARER_*` (inert since no-auth), `handler._dispatch_telemetry`'s 100-line ladder
and its legacy bypass, the inline `api_agent_sessions` branch, 3 of the 4 route tables — handler
**735 → ~250**, **~550 LOC** total.

### FR-9 — K9: purge the composition root; file single-consumer infrastructure · segment `alpha-1`

**Deletion half only, this release.** Delete `container.py`'s dead lifecycle logic —
`_workspace_python_bin`, `_repo_hygiene_sweeper`, `_definition_committer`, `_closure_committer`
(a `git add -A` committer), `_memory_lint_gate` (dead since `b94aede3`), `resolve_context` — and
`features/repos` with `ExcelReader` and the `openpyxl` dependency (14 LOC of feature behind a
protocol, an adapter and a third-party wheel, to read one xlsx). File single-consumer
infrastructure modules inside the feature that consumes them **only where no lint contract
breaks**. Keep the three real seams: `TelemetryRefreshLock`, `FilePermissionSetter`,
`ShutdownHandler`. Container becomes wiring.

**Protocol retirement is gated (R5).** The card's other half — retiring the ~17 one-adapter
protocol files and their `build_*` indirection — contradicts P-01/P-08 **as measured**
(`features-no-infrastructure`, `cli-no-infrastructure`), whose contracts produced the 880-LOC
container funnel they were meant to prevent. The ring rule (no upward imports) **stays**; the
"every adapter behind a protocol" requirement is proposed for retirement as an ADR record
appended `proposed` to `specs/ADRs/decisions.jsonl` (T-051-05). **Only the operator may flip a
decision to `accepted`** (`DADAIA.md` §6.5). Until then the protocol files stay.
Deleted this release: **~500 LOC** of the ~1,400 the card scopes; the balance waits on the accept.

### FR-10 — K10: delete the pre-v6 migration lineage and the shipped duplicates · segment `alpha-4`

Delete `features/migrate/{bugs_jsonl, bugs_single_file, tree_v2, agent_tier_frontmatter,
retired_frontmatter_keys, frontmatter_keys}.py` and `features/bugs/migrate_v5.py` (638 LOC,
self-labelled "deletable at 0.6.0"); the registry keeps exactly **"stamp v6 or refuse (<6:
upgrade to 0.4.x first)"**. Delete `public/scripts/generate-memory-catalog.py` (~400 LOC, a
duplicate of `features/specs/catalog.py` kept equal by a contract test that exists only to police
the duplicate) and its test. `core/models/adr.py` (0 importers) gets a composed store + verb or is
deleted — deleted, absent a consumer. **One frontmatter parser in `core`** replaces the 4 parsers
and 7 `_FRONTMATTER_RE` copies. **~1,700 LOC**, zero behaviour change: no bug has touched
migration steps 1–5 since 2026-07-09.

### FR-11 — CONTEXT.md: the glossary, first · segment `alpha-1`, **task 1**

No `CONTEXT.md` exists; **16 terms** carry two or more meanings in code, and the deepened modules
cannot be named until they carry one. Written at the repo root before any K task starts (R4),
each term with its canonical meaning and an **Avoid** list:

| Term | Canonical meaning |
|---|---|
| context | a spec-context tree; the **name** is `context_name`, the directory is `repo_slug` |
| session | one harness process, identified by ONE `session_id` — the harness sid; the CLI-minted `sess_*` is retired |
| bind | the session record naming its context |
| invocation | the resolved facts for one process: root, session, context, mode, release, phase |
| root | `workspace_root` only; a repo is `repo_root` |
| gate | the PreToolUse chain |
| chokepoint | a git hook |
| verdict | a `security-reviewer` APPROVED handoff for one sha |
| projection | a lib asset rendered into a runtime tree — `install` writes, `doctor` compares |
| harness | Claude Code \| Codex \| Kimi Code — never "target"/"runtime" |
| drift | projection ≠ render |
| record | one JSONL line — never "event"/"entry" |
| histo | an append-only archive JSONL |
| terminal | `resolved`/`superseded`/`deferred`/`rejected` — "closed"/"dispositioned" avoided |
| canon | the closed path set; **scaffold** = canon rendered |
| handoff | the JSON completion record; **report** = its HTML |
| doctor | a validator, always qualified by area |
| store / registry / service | a record store / a name→identity map / a feature's use-case module |

### FR-12 — the 12 picked bugs · every segment

Every open bug is picked (R6). Nothing is silently dropped.

| # | Bug id | Maps to | Disposition |
|---|---|---|---|
| 1 | `sdd-gate-memory-phase-resolves-empty-when-cwd-is-a-linked-worktree-outside-repos` | K1 / FR-1 | **fixed in-task** T-051-03, RED case in `test_invocation.py` (root-from-cwd vs context-from-`target_path`) |
| 2 | `radon-undercounts-nested-class-in-function-complexity-vs-ruff-c901` | K8 / FR-8 | **superseded_by** `deepening-simplification-k1-k11` — the factory it measures is deleted by T-051-15 |
| 3 | `memory-lint-blames-missing-delimiter-for-a-yaml-parse-error` | K10 / FR-10 | **fixed in-task** T-051-16 — one parser, one diagnosis |
| 4 | `memory-trio-missing-required-frontmatter-fields` | K10 / FR-10 | **fixed across two tasks**: the required-field check in T-051-16; the trio's own frontmatter in T-051-25 (memory is writable only in CLOSURE) |
| 5 | `backlog-cli-help-cites-retired-ledger-and-bl-dup` | K5 / FR-5 | **fixed in-task** T-051-09 |
| 6 | `backlog-spec-doc-035-flags-agents-md-as-loose-file` | K5 / FR-5 | **fixed in-task** T-051-09 — RED case on the unified backlog checker |
| 7 | `bug-record-write-once-evidence-fields-can-embed-selfscan-triggering-literal-with-no-correction-path` | K5 / FR-5 | **superseded_by** `deepening-simplification-k1-k11` — the transition methods are the correction path |
| 8 | `reports-validate-resolves-self-pull-refs-against-the-checked-out-branch-not-the-reviewed-tree` | K6 / FR-6 | **fixed in-task** T-051-13 — resolution against the reviewed tree, RED first |
| 9 | `concurrent-sessions-share-git-index-commit-boundary-contamination` | K11 ruling | **stays open** unless the operator accepts the ADR inside this release (R1) |
| 10 | `concurrent-agent-git-add-clobbers-other-sessions-staged-files-into-unrelated-commit` | K11 ruling | **stays open** unless the operator accepts the ADR inside this release (R1) |
| 11 | `mutation-baseline-core-models-scope-omits-public-schemas-fixture-directory` | standalone | **fixed in-task** T-051-18 |
| 12 | `secret-scan-workflow-never-runs-on-develop-prs-so-its-required-context-blocks-every-merge` | standalone | **fixed in-task** T-051-19 |

**K11 (git-index boundary) is in scope as a ruling, not as code (R1).** `software-architect`
DRAFTs the two options — `bind` provisions a per-session worktree, or `pre_commit` refuses when
the index holds paths staged by a foreign presence — and appends a **proposed** ADR. Either option
*grows* a feature, which is why no code is written on an agent's authority. If the operator
accepts inside this release, the accepted option becomes an `rc` task; otherwise bugs 9 and 10
stay `open` and are re-picked by the next release.

---

## 4. Out of scope (non-goals)

- **Publication.** No tag, no PyPI release, no `release.yml` approval — publication stays
  withheld, as in 0.5.0, unless the operator orders otherwise (R9).
- **K9's protocol retirement before the ADR is accepted.** The ~17 one-adapter protocol files and
  their `build_*` indirection stay until the operator flips the P-01/P-08 decision to `accepted`.
  No agent flips it (`DADAIA.md` §6.5).
- **K11 code.** Only the ruling and the proposed ADR (R1).
- **New backlog scope.** This release consumes exactly one slug; an `rc-N ≥ 2` carries fixes on
  this scope only (`RC-FLOW.md` step 6). Residuals found at closure are compiled for the PM's
  operator-facing intake report — `product-engineer` creates no backlog entry.
- **Behaviour change.** Every K is a structural move: the observable contract of each surface is
  unchanged except where FR-12 names a bug.
- **The 32 open findings of `audits/20260827-canon-v6-first-audit`** — dispositioned by their own
  remediation release, not folded in here.
- **Growing `specs upgrade`, the memory-lint heading allowlist, or any other 0.5.0 deferral.**

---

## 5. Acceptance criteria

**Release-wide (measured at scope-complete, T-051-21):**

- **A-0.1** `git diff --stat` over `dadaia_workspace/**` for the whole release range is
  **net-negative** in production LOC; each FR's own range is net-negative independently (R3).
- **A-0.2** Decider counts re-measured against §1: context deciders **8 → 1**, sid ladders
  **3 → 1**, staleness predicates **4 → 1**, GC authorities **4 → 1**, canon definitions
  **3 → 1**, bug-ledger parsers **4 → 1**, handoff readers **10 → 1**, frontmatter parsers
  **4 → 1**, `_FRONTMATTER_RE` copies **7 → 1**, projection compare semantics **5 → 1**.
- **A-0.3** `lint-imports` green with the ignore-edge cap **not raised** — 18 → 15 after FR-7;
  a new suppression is a review rejection, not a cap bump.
- **A-0.4** `dadaia specs doctor`, `backlog doctor`, `public doctor`, `ci preflight` clean at
  every commit; `dadaia specs doctor` reports **0 errors** at closure.
- **A-0.5** Test suite is **net-negative** in files and functions (`pytest --collect-only -q`
  before/after), and every deepened interface has a table-driven test **that existed and passed
  before** its mirrored files were deleted.
- **A-0.6** Every `qa-engineer` segment verdict records the deletion evidence per
  `dadaia-test-stewardship` and states the **bug-surface delta** of each touched feature with
  bug-history evidence (R8). "Tests green" is not a verdict.

**Per FR:**

| Id | Check |
|---|---|
| **A-1.1** | `core/invocation.py` exists; `rg` finds exactly one `resolve_context`-class entry point in production; the 8 ladders are gone |
| **A-1.2** | `tests/unit/core/test_invocation.py` is table-driven over `(env, cwd, payload, records)`; the ~14 mirrored files are deleted under a QA verdict |
| **A-1.3** | Session records are keyed and read by the **same** sid; `test_common_sid_precedence`'s cases survive as rows in the table test |
| **A-1.4** | Bug 1 has a RED case that fails for the real reason on a linked worktree outside `repos/` before the fix |
| **A-1.5** | FR-1 range is net-negative (declared ~−350 LOC); `container.resolve_context` and `_context_specs_dir`'s root fallback are gone |
| **A-2.1** | `presence.gc` is the only reaper; `rg` finds one staleness predicate; `sdd_post_gate.py` ≤ 60 LOC |
| **A-2.2** | `test_presence_gc.py` replaces the four reaper test files; the `presence-warn-*` marker class is reaped and asserted |
| **A-2.3** | No reaper can delete a live session's own bind record — a regression case pins it |
| **A-2.4** | FR-2 range net-negative (declared ~−400 LOC) |
| **A-3.1** | `projection_rules()` returns the rule set; `install`, `doctor` and the ledger are folds over it with **no** second derivation of the managed set |
| **A-3.2** | `HARNESSES` holds three adapters behind one protocol; codex TOML is byte-compared to the renderer; the dcx regexes are gone |
| **A-3.3** | One "rule set per profile" table test + one write/compare pair + per-harness golden renders replace the 12+ named files |
| **A-3.4** | `dadaia public stage && public install --target all && public doctor` reports `[ok] public-privacy`, 0 drift |
| **A-3.5** | FR-3 range net-negative (declared ~−900 LOC) |
| **A-4.1** | One `CANON` table; a property test asserts `scaffold(t) ⇒ doctor(t) == []` on a fresh tree |
| **A-4.2** | `features/spec_artifacts` is deleted; its two writers call `scaffold_entry`; `lint-imports` still green |
| **A-4.3** | The six scaffold-vs-doctor regression tests collapse into the one property test |
| **A-4.4** | `public/scaffold/releases/AGENTS.md` names `RELEASE.json` and no `reviews/` (R7); the projected `specs/releases/AGENTS.md` matches |
| **A-4.5** | FR-4 range net-negative (declared ~−300 LOC) |
| **A-5.1** | A status is unreachable without its fields: `BugRecord.resolve/supersede/defer/reject` raise `IncompleteTransitionError` on missing input, pinned by a table test |
| **A-5.2** | The doctor reads bugs **through the store** (`bug_store_factory`); `rg` finds one ledger parser |
| **A-5.3** | The 488 legacy records carry `migration_note="v5-fold-incomplete"` and produce zero warnings |
| **A-5.4** | The backlog's four checkers are one; bugs 5 and 6 have RED cases first |
| **A-5.5** | FR-5 range net-negative (declared ~−250 LOC) |
| **A-6.1** | `HandoffIndex` is the only handoff reader; the other 9 readers call it; `core/models/handoff.py` is gone |
| **A-6.2** | `Handoff.artifact_path()` is the one artifact-path rule and `schema_version` the one router; bug 8 has a RED case resolving against the **reviewed tree** |
| **A-6.3** | The 12 reports test files (2,162 LOC) collapse onto `HandoffIndex` tests; CLI tests are exit-code tests |
| **A-6.4** | FR-6 range net-negative (declared ~−330 LOC) |
| **A-7.1** | `chokepoints/` holds four modules; no module exceeds 400 LOC; `service.py` is gone |
| **A-7.2** | `covering_verdict(paths, head_sha)` is the single verdict reader for the doctor, the push gate and `pr-verdict-check` |
| **A-7.3** | The import-linter ignore cap moves **18 → 15** in the same commit that removes the suppressions |
| **A-7.4** | One masking predicate remains; FR-7 range net-negative (declared ~−300 LOC) |
| **A-8.1** | `TelemetryStore` owns every connection; `rg` finds zero `dao._conn` reach-ins outside it |
| **A-8.2** | Panel routes are one table; `handler.py` ≤ 300 LOC; `AuthClass`/`_BEARER_*` are gone |
| **A-8.3** | `integrity_check`/`quarantine` exist and are exercised by a test — the deferred corruption bug now has an owner |
| **A-8.4** | Bug 2's factory no longer exists; the bug is `superseded_by` with the deleting commit named |
| **A-8.5** | FR-8 range net-negative (declared ~−550 LOC) |
| **A-9.1** | The six named container closures and `features/repos` are deleted; `openpyxl` leaves `pyproject.toml` and the lock |
| **A-9.2** | Container is wiring only; the three real seams remain; no new protocol is added |
| **A-9.3** | One ADR record `proposed` in `specs/ADRs/decisions.jsonl` for P-01/P-08's protocol-per-adapter requirement (+ P-09's home rename), status **never** `accepted` by an agent |
| **A-9.4** | `lint-imports` green, cap unchanged; FR-9 range net-negative (declared ~−500 LOC) |
| **A-10.1** | The 6 pre-v6 migration modules, `migrate_v5.py`, `generate-memory-catalog.py` and `core/models/adr.py` are deleted; the registry refuses `<6` with the upgrade instruction |
| **A-10.2** | One frontmatter parser in `core`; `rg '_FRONTMATTER_RE'` returns one definition |
| **A-10.3** | Bugs 3 and 4 (checker half) have RED cases: a YAML parse error is diagnosed as a parse error, not a missing delimiter |
| **A-10.4** | The duplicate-policing contract test is deleted with its subject; FR-10 range net-negative (declared ~−1,700 LOC) |
| **A-11.1** | `CONTEXT.md` exists at the repo root, resolving all 16 terms with an **Avoid** list each |
| **A-11.2** | Every module, class and field named by FR-1…FR-10 uses only canonical terms — checked at each segment's QA close |
| **A-12.1** | All 12 bugs carry a terminal token or a stated `open` with its reason (bugs 9, 10); zero silently dropped (`dadaia bugs stats` at closure) |
| **A-12.2** | Every `resolved` record carries its red-loop command, regression seam and diff direction (`dd-bug-registration`) |
| **A-12.3** | The two `superseded` records carry `superseded_by=deepening-simplification-k1-k11` and are set with `bugs update --set`, never `--event` |

---

## 6. Architecture constraints

1. **The standing order is an acceptance criterion, not advice.** Permanent architecture review
   oriented by bug history: each task reads the ledger for the surface it touches before
   proposing, and names the structural cause. A fix that adds a branch, a flag, a special case, a
   second code path, a cross-feature reach-in or a new side effect is a puxadinho and is rejected.
2. **Replace, don't layer.** New interface + its table-driven test **first**; then delete the
   mirrored files. Never both shapes live at once past a single commit boundary; never a
   compatibility shim that outlives the task.
3. **Every K deletes at least one decider.** A K that leaves its old decider reachable has not
   landed, whatever its diff says.
4. **One adapter is indirection; two is a seam.** New protocols are refused; existing ones are
   retired only under an accepted ADR (FR-9).
5. **The ring rule stands.** `core` imports nothing above it; `features` import no
   `infrastructure`, `cli` or `hooks`; hooks never import the container (P-12). `lint-imports`
   green at every commit, cap never raised.
6. **`qa-engineer` stewardship verdict per segment** (`RC-FLOW.md`): deletion evidence, the
   `file:line` map of superseding coverage, the pyramid shape, and the bug-surface delta. A test
   dies only under that verdict, executed by `software-engineer` — never pruned to go green.
7. **Memory is written only in DEFINITION and CLOSURE**, by `product-engineer`. FR-1's P-09
   rename and FR-9's P-01/P-08 proposal are ADR records at definition; the atom text changes at
   closure.
8. **Naming is `CONTEXT.md`'s.** A module named before FR-11 lands is renamed, not grandfathered.

---

## 7. Dependencies and risks

| # | Risk | Mitigation |
|---|---|---|
| **R-1** | **A deepening lands half-done** — the new interface exists and the old deciders survive, so the release *adds* a decider instead of removing one. | A-0.2 counts deciders after every segment; the QA close refuses a segment whose count did not fall. Each card's "deletes" list is the task's done criterion, not a suggestion. |
| **R-2** | **Test collapse hides a real regression** — 250 mirrored files carry cases the table test forgets. | Table test written and green **before** any deletion; the QA verdict carries the `file:line` map of superseding coverage per deleted file; deletion and its replacement land in the same commit. |
| **R-3** | **K1 is under everything.** A wrong `Invocation` breaks hooks, CLI and the gate at once, on the write hot path. | K1 is alone in `alpha-1` with only `CONTEXT.md` and the K9 deletion ahead of it; the whole 14-file test corpus becomes rows in the table test before the ladders die; `test_sdd_gate`'s payload cases are ported first. |
| **R-4** | **FR-1 and FR-9 both edit `container.py`.** | Serialized inside `alpha-1`: T-051-03 (K1) closes before T-051-04 (K9) opens; declared in PLAN §4 and in both task rows. |
| **R-5** | **The ADR is not accepted in time**, and K9 half-lands. | FR-9's deletion half is independent and self-sufficient; the protocol retirement is explicitly out of scope (§4) with no partial state. The proposal is appended `proposed`, never `accepted` by an agent. |
| **R-6** | **K3 touches the projection engine — 29 records, 13/13 fix commits added code.** | The rule table is authored first and the three folds are switched onto it one verb at a time (`install`, then `doctor`, then the ledger), each independently green; `public doctor` clean between steps; goldens per harness adapter. |
| **R-7** | **Concurrent sessions share one git index** (bugs 9, 10) while four segments run in parallel worktrees. | Disjoint write sets per task within a segment; stage exactly the task's write set, never `-A`; one `[-]` per TASKS.md unless the segment declares a disjoint pair. K11's ruling is in this release for exactly this reason. |
| **R-8** | **A deleted migration is still needed by a consumer sitting at v5.** | The registry keeps "stamp v6 or refuse" with the explicit "upgrade to 0.4.x first" instruction; no consumer is left without a path, only without an in-wheel one. |
| **R-9** | **CI portability** — 0.5.0's rc-1 burned five portability fixes (shallow checkout, bash-3.2, LF, radon, WSL bash). | Every push watched to green on **all** jobs before the next task opens; a red job stops the segment. |
| **R-10** | **The suite shrinks past its value** and a deletion removes the only coverage of a live seam. | `dadaia-test-stewardship` admission filter at birth; deletion only under a QA verdict; A-0.5 measures direction, and the QA close measures *coverage*, not only count. |

**Dependencies:** FR-2 and FR-7 depend on FR-1 (the session id). FR-4's law-drift fix depends on
nothing. FR-3, FR-5, FR-6, FR-8, FR-10 are independent of each other and of FR-1. FR-11 precedes
every K. The K11 ruling depends on the operator's sitting, not on code.
