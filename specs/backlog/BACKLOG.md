# Backlog — single source (ACTIVE + LEDGER)

Consolidated 2026-08-15 by `project-manager` (v0.12.0 FR7, task T-120-07) from the 31 live
per-entry files and `candidates.md` (both `git mv`-archived to `_archive/` at the v0.12.0
cutover, never deleted). Schema: `dd-backlog-definition` §2 — five required keys per
`ACTIVE` subsection plus the optional `Intents` key (OD-1); `LEDGER` grammar
`slug · DISPOSITION · release-or-reason · date`. Never-delete proven by count (ADR D4):
30 ACTIVE subsections + 52 LEDGER rows carry every pre-consolidation record; the
set-equality evidence is captured under `.dadaia/tmp/project-manager/20260815/`.
Entry numbering (`#N`) from the retired `candidates.md` index is carried in each Title —
rows are never renumbered, and LEDGER rows are never deleted.

**Pick-precedence notice (DADAIA.md §5).** At release-pick time, open bugs and
undispositioned audits outrank every fresh entry below. **Currently outranking: nothing**
— the bug ledger carries zero open bugs (the two LOWs closed by `hotfix/0.7.1`, merged
`d15bdf4e`); both 2026-07 audits are archived and fully dispositioned (v0.8.0).

**Standing operator decision, pending (v0.8.0 CLOSURE return #3).** Is `deferred`
terminal for bug `panel-telemetry-sqlite-corrupts-under-concurrent-access`, or does it
return to the queue? Undecided; keeps surfacing at every pick. The related
dangling-pointer repair is `panel-runtime-reliability-dangling-ledger-pointer` (#12)
and proceeds either way.

## ACTIVE

### test-suite-remediation-stewardship
- **Title:** Test-suite remediation — apply the stewardship doctrine to dadaia-workspace's own tests (#2)
- **Opened:** 2026-08-12
- **Status:** candidate
- **Description:** Rewritten 2026-08-14 by project-manager per grill ADR #6: the previous text carried a stale baseline ("26 LARGE files") and referenced a dossier that no longer exists (.dadaia/tmp is ephemeral — verified gone at HEAD). Live baseline, re-measured at HEAD on 2026-08-14 (commands in the body): 55 e2e-tier pytest tests collected under tests/e2e/** across 17 files, plus 41 Playwright cases in 11 browser specs (tests/e2e/panel/*.spec.ts) — broad LARGE census 96 total, against the declared LARGE cap of 30 (specs/memory/quality-assurance.md:145-146, WARN while above); 333 pytest test files repo-wide. The work: the first full curation of this repo's own suite under the shipped stewardship doctrine — LARGE census down to (or justified against) the cap, ownership declarations, tombstone/tautology cleanup, quarantine adoption, orphan tooling disposition. All curation lands as qa-engineer verdicts executed by software-engineer (steward is verdict-only), with the demotion map recorded at closure. EXCLUDED from the current release round (grill ADR #6); strong candidate for its own follow-up release.
- **Provenance:** operator request — v0.7.0 stewardship lineage (opened 2026-08-12); rewritten 2026-08-14 per grill ADR #6 (operator-ratified)
- **Intents:**
```yaml
- subject:
    kind: code
    ref: dadaia_workspace/infrastructure/public_assets.py#FileSystemPublicAssetManager
  change: 'Rework the tautological/implementation-coupled test families that orbit this surface
    — re-verified present at HEAD 2026-08-14: tests/unit/infrastructure/test_public_assets_doctor.py
    (byte-matching private methods -> assert observable doctor outcomes) and test_public_assets_hooks.py
    (generator-constant hand-copies -> externally-held contract frozensets, per the existing test_claude_scaffold_is_loadable.py
    pattern). NOTE: the previously named test_public_doctor_parity.py no longer exists — that
    finding is void; the pick-time scan re-derives the offender list instead of trusting this
    one.'
- subject:
    kind: doc
    ref: memory/quality-assurance.md#Test Health
  change: 'Suite-wide curation pass against the live 2026-08-14 baseline: bring the LARGE census
    (96 broad / 55 e2e-tier pytest vs cap 30) down via the demotion protocol or justify the excess
    explicitly; declare owners for every LARGE test; fix f(x)==f(x) self-consistency contracts
    (re-located at HEAD: tests/unit/infrastructure/runtime_transforms/test_model_mapping.py, tests/unit/features/telemetry/test_pricing.py)
    by pinning externally-held expectations; wire-or-delete tests/scripts/check_skill_orphans.py
    (still unwired at HEAD); carry every env-gate skip with a plan ref or delete it; sweep artifact
    residue. Every deletion/demotion is a qa-engineer verdict with evidence, executed by software-engineer.'
```

### retire-dead-hotfix-surface
- **Title:** Retire the dead hotfix-release surface (verb, templates, doctor nag) (#4)
- **Opened:** 2026-08-12
- **Status:** candidate
- **Description:** v0.6.0 revoked the hotfix-release lifecycle (operator ruling D4): bug fixes run on hotfix branches with a PATCH mint and no ceremony. The revoked lifecycle's surface still ships as dead code and must be removed: the CLI verb, the two Jinja templates, and the specs-doctor check that nags for the revoked backlog intake section. OD-2 (v0.12.0): SPEC-DOC-022/023 retire with check_backlog_schema at the v0.12.0 cutover, so this entry's residual is the CLI hotfix verb + templates + doctor nag only — the rewrite-down to that residual is a recorded v0.12.0 closure obligation.
- **Provenance:** operator request — v0.6.0 law revocation residual, curated 2026-08-12; OD-2 residual rewrite recorded at v0.12.0 (closure obligation)
- **Intents:**
```yaml
- subject:
    kind: code
    ref: dadaia_workspace/cli/commands/specs.py#hotfix_app
  change: Remove the `dadaia specs hotfix open` verb (the hotfix_app sub-app) and its tests —
    never invoked under the v0.6.0 law; product-engineer.md names it dead surface.
- subject:
    kind: code
    ref: dadaia_workspace/features/specs/doctor_governance.py#GovernanceValidator
  change: Retire the SPEC-DOC-023 check that requires a '## Hotfixes pendentes' intake section
    in specs/backlog/candidates.md — the intake it polices was revoked with the hotfix-release
    lifecycle.
- subject:
    kind: catalog
    ref: specs-doctor
  change: Remove public/templates/release_hotfix.md.j2 and closure_hotfix.md.j2 from the shipped
    template set (manifest + goldens follow); the doctor's template-facing checks drop with SPEC-DOC-023.
```

### consumer-side-validation-round
- **Title:** Consumer-side validation round — prove the assembled consumer journey on a real workspace (#5)
- **Opened:** 2026-08-14
- **Status:** candidate
- **Description:** Created by grill ADR #1 (2026-08-14 refinement report) as the inheritor of the two external findings of the consumer audit (2026-07-15) that this repo cannot close from the provider side alone. Both findings were dispositioned `deferred` — `rejected` would contradict the §6 approval law ("a candidate is approved when the operator and the consumer-side validation agent agree, after validating a real workspace"), and leaving them pending would block every future pick under §5 precedence. The audit archives citing this entry. The work: run a full consumer-side validation round on a real (disposable) consumer workspace against the current provider surface, with the two inherited findings as its acceptance criteria.
- **Provenance:** v0.8.0 grill ADR #1 — operator-ratified materialization 2026-08-14
- **Intents:**
```yaml
- subject:
    kind: catalog
    ref: consumer-agent-support
  change: 'A consumer-side validation round on a real disposable workspace certifies the assembled
    consumer journey through supported interfaces only, closing the two inherited audit findings:
    (1) the consumer prompt/tests must consume the installed version-matched skill/capability
    surface and exercise canonical workflow verbs — no preserved references to removed lifecycle
    commands; (2) the consumer owning repository must be governance-coherent — one-task-at-a-time
    markers, valid memory/schema state, immutable release evidence.'
```

### thin-wrapper-projected-scripts
- **Title:** Thin-wrapper projected scripts — one logic, one source (#6)
- **Opened:** 2026-08-14
- **Status:** candidate
- **Description:** Extraction of W6, the sole surviving finding of the resilience audit (2026-07-18), per grill ADR #2 (2026-08-14 refinement report): W6 is dispositioned `superseded` by this entry; every other finding of that audit is `rejected` (the audited object was demolished in v0.3.0, −60k lines); the audit archives citing this entry. The still true concern: projected/standalone scripts re-implement package behavior and drift (audit evidence: bugs 10, 24, README/CLI drift). The fix W6 proposed: projected scripts become thin wrappers that exec the workspace venv's package code — one logic, one source. Evidence of today's INVERSION of that principle: the package itself shells out to the standalone script — features/specs/doctor_memory.py:38-40 resolves _LINT_SCRIPT to public/scripts/lint-memory-atoms.py and :357 runs it via subprocess([sys.executable, "-B", str(_LINT_SCRIPT), ...]) inside MemoryValidator.check_lint1_memory_atoms (LINT-1), instead of importing one shared implementation.
- **Provenance:** v0.8.0 grill ADR #2 (W6 extraction) — operator-ratified materialization 2026-08-14
- **Intents:**
```yaml
- subject:
    kind: code
    ref: dadaia_workspace/features/specs/doctor_memory.py#MemoryValidator
  change: 'LINT-1 stops shelling out to the standalone lint-memory-atoms.py script (_LINT_SCRIPT
    at :38-40, subprocess at :357): the lint logic lives once in the package and is imported here;
    the projected script becomes a thin wrapper that execs the workspace venv''s package entry
    point.'
- subject:
    kind: cli
    ref: public doctor
  change: 'Every projected script under public/scripts/ follows the thin-wrapper contract: no
    re-implemented package logic in the projection; the wrapper resolves the workspace venv and
    delegates. Doctor/projection tests assert the contract so script↔package drift (the W6 defect
    class) is structurally impossible.'
```

### bug-picked-ledger-event
- **Title:** bug `picked` ledger event — a reservation marker for Arm B under NO-LOCKS (#7)
- **Opened:** 2026-08-14
- **Status:** candidate
- **Description:** Created by grill ADR #10/E-4 (2026-08-14 refinement report). TASKS.md has an observable reservation marker ([ ] → [-] plus the chore(tasks) commit); the bug ledger has no analogue: BugEventKind (core/models/bugs.py:30-40) is a closed 6-kind enum (reported, resolved, superseded, deferred, rejected, archived) with no reservation event. Under the NO-LOCKS doctrine two agents can pick the same open bug with nothing but an advisory presence warning between them — the race is accepted, but today it is not even observable in the ledger. The fix is a schema + coherence + CLI surface (software-architect + software-engineer), deliberately kept OUT of the dd-skills AI-surface release: dd-bug-fix documents today's advisory-presence signal only, and this entry owns the primitive.
- **Provenance:** grill ADR #10/E-4 — operator-ratified refinement session 2026-08-14
- **Intents:**
```yaml
- subject:
    kind: code
    ref: dadaia_workspace/core/models/bugs.py#BugEventKind
  change: Add a `picked` (reservation) event kind — a NON-terminal annotation, like `archived`
    — so an agent taking an open bug appends an observable event naming itself, mirroring the
    TASKS [-] marker.
- subject:
    kind: code
    ref: dadaia_workspace/core/models/bugs.py#advance_coherence
  change: 'Coherence rules for `picked`: valid only on an open (reported, non-terminated) stream;
    must not count as terminal; define behavior for repeated picks (the NO-LOCKS answer: allowed,
    surfaced — the second pick is visible in the stream, never blocked) and for pick-after-terminal
    (incoherent).'
- subject:
    kind: cli
    ref: bugs append
  change: '`dadaia bugs append --event picked` accepts the reservation fields (who picked, optional
    release/branch note); `dadaia bugs status` surfaces picked-by on open bugs; schema bug-event-v1
    evolves in lockstep (schema + fold + CLI in one change, per the v0.1.72 single-authority law).'
```

### codex-persona-law-context-dehydration
- **Title:** Codex runtime fidelity: compact personas, loaded law and live certification (#8)
- **Opened:** 2026-08-14
- **Status:** candidate
- **Description:** Repair the Codex harness as one fidelity boundary: shrink the nine 8-22 KB projected persona TOMLs to role identity and role-specific decisions; load canonical DADAIA.md once and prove parent plus delegated-agent visibility; replace the false claim that headless codex exec has no hooks with version-aware live evidence; make certification exercise the installed Codex rather than infer runtime behavior from static files; strengthen entities derivation from structural bijection to behavioral fidelity for personas, rules and universal projections; and correct stale Codex documentation, including the false 12-persona count. Also make native sandbox, output, memory injection and delegated-subagent contracts internally executable rather than contradictory. Scope is 100% Codex and must not change any other harness's generated bytes or behavior. Baseline re-measured post-v0.10.0 ship (P-5, 2026-08-15): nine TOMLs, 126,155 B total (was 124,557 B). Merged (intake #2 item 2-7): the stale public/rules taxonomy row at ai-harness-codex/SKILL.md:99.
- **Provenance:** adopted 2026-08-14 from a parallel Codex session (verified at adoption, a1b68aad); intake-report #2 item 2-7 approved as merge 2026-08-15 (operator-delegated adjudication)
- **Intents:**
```yaml
- subject:
    kind: code
    ref: dadaia_workspace/infrastructure/runtime_transforms/codex_assets.py#_render_codex_agent_toml
  change: 'Render compact Codex-only custom-agent instructions: keep only role identity, role-specific
    decisions, authority and write/refusal boundaries; remove shared DADAIA.md law and cross-role
    protocol repetitions; connect every Codex persona to one effective common-law loading path;
    and make each persona''s native sandbox, dispatch authority and HTML/handoff output contract
    mutually executable.'
- subject:
    kind: code
    ref: dadaia_workspace/infrastructure/codex_doctor.py#check_codex_rule_corpus_reachable
  change: Stop treating a literal AGENTS.md @DADAIA.md line plus target-file existence as proof
    that the model received the law. Distinguish static reference integrity from effective prompt
    visibility and require executed-path evidence before reporting a loaded/reachable Codex law.
- subject:
    kind: code
    ref: dadaia_workspace/infrastructure/codex_doctor.py#codex_trust_boundary_info
  change: Replace the stale interactive-only/headless-no-hooks claim with version-qualified observations
    from the installed Codex; live 0.147.0 evidence already proves both UserPrompt injection and
    blocking PreToolUse under codex exec.
- subject:
    kind: code
    ref: dadaia_workspace/features/certification/service.py#certify
  change: Add version-aware live Codex certification probes for common-law visibility, UserPrompt
    injection, blocking PreToolUse, evidence-role outputs, QA write scope and authorized/unauthorized
    nested delegation. Static projection/wrapper tests may validate shape but must never attest
    runtime behavior.
- subject:
    kind: code
    ref: dadaia_workspace/hooks/ctx_inject.py#_resolve_context
  change: 'Remove any first-alive Codex memory fallback and enforce the workspace law''s exact
    context order: environment, own session, cwd repository, otherwise generic preflight. Distinguish
    deterministic hook injection from discoverable/on-demand memory-ctx skill invocation.'
- subject:
    kind: code
    ref: dadaia_workspace/infrastructure/codex_doctor.py#check_entities_derivation
  change: Extend ENT-DERIVE-1 beyond persona-name bijection and behavior-key presence to behavioral
    fidelity of Codex personas, deterministic rules and universal projections, including exact
    registry-to-generated hook/wrapper path mappings, with mutation fixtures that prove each drift
    class blocks.
- subject:
    kind: catalog
    ref: harness-codex
  change: Make the common workspace law load exactly once in the effective Codex context for both
    the parent session and delegated custom agents; reconcile the Codex skill, memory and academy
    with live hook behavior, actual nine-persona registry, native sandbox/output constraints and
    proven PM/auditor delegation topology; leave all non-Codex harness behavior and projected
    bytes unchanged.
```

### python-env-interpreter-probe-hardening
- **Title:** python_env interpreter-probe hardening: absolute-path filter (CWE-426) + probe timeout/stdin isolation (#9)
- **Opened:** 2026-08-14
- **Status:** candidate
- **Description:** Materializes the two LOW findings of the APPROVED security review covering the v0.5.1 hotfix (handoff 2026-08-14T151941Z-security-reviewer-v0.8.0-plus-hotfix- full-range). (1) CWE-426 untrusted search path: interpreter candidates from shutil.which and from the running venv's pyvenv.cfg executable value are executed and handed to subprocess.run without an os.path.isabs check — under a malformed PATH shutil.which can return a bare relative name that subprocess.run then PATH-resolves. (2) _interpreter_version runs its probe subprocess with no timeout= and stdin inherited, so an unresponsive candidate (stale mount, stdin-reading wrapper) hangs dadaia init indefinitely. Both are defence-in-depth, declared non-blocking for that push and routed to the backlog — this entry is that routing, materialized after being asserted twice without a file existing.
- **Provenance:** APPROVED v0.5.1 security-review LOW routing — materialized 2026-08-14 (pre-ADR-15 regime)
- **Intents:**
```yaml
- subject:
    kind: code
    ref: dadaia_workspace/infrastructure/python_env.py#_path_candidates
  change: Reject any interpreter candidate for which os.path.isabs() is false — filter shutil.which
    results here and apply the same check to the _current_venv_pyvenv_executable() return value
    — before any candidate reaches _interpreter_version or subprocess.run. Optionally resolve
    with os.path.realpath and record the resolved path in the diagnostics string (CWE-426 closure,
    including the pyvenv.cfg bare-name case).
- subject:
    kind: code
    ref: dadaia_workspace/infrastructure/python_env.py#_interpreter_version
  change: Pass a bounded timeout= and stdin=subprocess.DEVNULL to the probe subprocess so a hung
    candidate degrades to None and is skipped (TimeoutExpired is already a SubprocessError subclass,
    so the existing except clause suffices once timeout= is supplied). Consider python -I isolated
    mode so inherited PYTHONPATH/sitecustomize cannot perturb the probe's stdout.
```

### spec-doc-031-citation-classes
- **Title:** SPEC-DOC-031: distinguish consumption citations from reference citations in archived SPEC/CLOSURE (#10)
- **Opened:** 2026-08-14
- **Status:** candidate
- **Description:** v0.8.0 CLOSURE backlog return, materialized 2026-08-14. SPEC-DOC-031 scans every archived release's SPEC.md and CLOSURE.md line by line for backlog slugs and WARNs when a matched slug's entry is non-terminal, excluding only lines inside a "## Backlog returns" section (doctor_governance.py:196-224). Any other mention — a legitimate inheritance citation (an entry named as inheritor of deferred/ superseded findings) or an explicit non-goal/out-of-scope citation — raises a WARN asserting consumption that demonstrably did not happen. Concrete case: archiving v0.8.0 raised exactly 3 such WARNs (consumer-side-validation-round, thin-wrapper-projected-scripts, push-range-denylist-scan), all predicted as false positives by that CLOSURE (V9). Proposed refinement: also exclude out-of-scope/non-goal sections, or key the check on a machine-readable consumed set (consumed_backlog.json) instead of free-text slug matching.
- **Provenance:** v0.8.0 CLOSURE return (operator-approved closure) — materialized 2026-08-14
- **Intents:**
```yaml
- subject:
    kind: doc
    ref: memory/product/sdd/specs-doctor.md#Validator Families
  change: 'Refine _archive_consumption_hits / check_consumed_backlog_disposition so a slug mention
    only counts as consumption evidence when it is one: either restrict matching to consumption-asserting
    contexts (and exclude non-goal / out-of-scope / inheritance sections the way "## Backlog returns"
    is already excluded), or key SPEC-DOC-031 on a machine-readable consumed set (consumed_backlog.json)
    instead of free-text slug matching. The v0.8.0 archive must stop producing its 3 documented
    false-positive WARNs without flipping the three cited entries and without editing the FROZEN
    archive.'
```

### changelog-version-axis-reconciliation
- **Title:** CHANGELOG version-axis incoherence: dated [0.5.1] atop stacked Unreleased spec-release sections (#11)
- **Opened:** 2026-08-14
- **Status:** candidate
- **Description:** v0.8.0 CLOSURE backlog return, materialized 2026-08-14 (CLOSURE destined it to ideas; promoted to candidate by operator mandate with owners software-engineer + product-engineer). CHANGELOG.md at HEAD carries "## [0.5.1] — 2026-08-14" (line 7) above three stacked "## [Unreleased] — spec release vX" sections (v0.7.0 line 30, v0.6.0 line 107, v0.5.0 line 177) and "## [0.5.0] — Unreleased (spec release v0.3.0)" (line 236): the hotfix minted a dated PATCH on top of a package version whose own section still reads Unreleased, so the file no longer states truthfully what a given package version contains. The two version axes are distinct by design (ADR-2: SDD release ids version the SDD process; the 0.x package version versions the shipped library) — the ask is a reconciled CHANGELOG convention honoring that split, not a renumbering.
- **Provenance:** v0.8.0 CLOSURE return — promoted from ideas lane by operator mandate, materialized 2026-08-14
- **Intents:**
```yaml
- subject:
    kind: doc
    ref: memory/product/distribution/pypi-distribution.md#Differentiator
  change: 'Define and record the CHANGELOG convention that reconciles the two axes: how spec-release
    sections nest under (or annotate) package-version sections, what happens to accumulated "[Unreleased]
    — spec release vX" sections when a package version is finally dated, and how a hotfix PATCH
    is placed relative to a still-Unreleased base version. Restructure CHANGELOG.md once to that
    convention so each package version''s section states exactly what it ships.'
```

### panel-runtime-reliability-dangling-ledger-pointer
- **Title:** Dangling panel-runtime-reliability deferral pointer in the bug ledger (#12)
- **Opened:** 2026-08-14
- **Status:** candidate
- **Description:** v0.8.0 CLOSURE backlog return, materialized 2026-08-14. The bug ledger's deferred event for panel-telemetry-sqlite-corrupts-under-concurrent-access (bugs.jsonl line 202, ts 2026-07-01T23:14:54Z) reads "deferred to backlog panel-runtime-reliability", but that backlog slug is terminal: it was consumed by release v0.1.52 and lives only at specs/_archive/v0.1.52/consumed-backlog/panel-runtime-reliability.md. No live backlog entry carries the slug, so the deferral points at a target that can never absorb the bug. The ledger is append-only — the correction is a new clarifying event, never a rewrite of the existing line.
- **Provenance:** v0.8.0 CLOSURE return (operator-approved closure) — materialized 2026-08-14
- **Intents:**
```yaml
- subject:
    kind: doc
    ref: memory/product/sdd/sdd-bug-backlog-governance.md#Bugs
  change: 'Per the append-only ledger governance this section states, append a clarifying event
    (via dadaia bugs append) to bug panel-telemetry-sqlite-corrupts-under-concurrent-access recording
    that the 2026-07-01 deferral target (backlog panel-runtime-reliability) was already consumed
    by v0.1.52 at deferral time, and naming the corrected disposition: either a live successor
    backlog entry or the operator''s ruling that deferred is terminal for this bug. No existing
    ledger line is modified; the mutation target is specs/bugs/bugs.jsonl data, not code.'
```

### mutation-testing-tool-selection-and-wiring
- **Title:** Mutation-testing tool selection and wiring (1×/release, off the push path) (#13)
- **Opened:** 2026-08-14
- **Status:** candidate
- **Description:** v0.7.0 CLOSURE backlog return, materialized 2026-08-14 (grill ADR #5 — the CLOSURE claimed this routing but it never happened). CLOSURE text: "Mutation-testing tool selection and wiring. The cadence (1×/release, off the push path) is declared in the skill and in memory; choosing between mutmut / cosmic-ray / another and wiring it is its own task (SPEC §4 non-goal)." Verified at HEAD 2026-08-14: no mutation tool is wired (no mutmut/cosmic-ray in pyproject.toml or .github/workflows/) — the declared cadence still has no executor.
- **Provenance:** v0.7.0 CLOSURE return (operator-approved closure) — materialized 2026-08-14
- **Intents:**
```yaml
- subject:
    kind: doc
    ref: memory/quality-assurance.md#Layers
  change: Select the mutation-testing tool (mutmut vs cosmic-ray vs other), wire it at the declared
    cadence (once per release, never on the push path), and record the chosen tool + invocation
    in the QA memory so the cadence claim is backed by a runnable command.
```

### intent-docstring-mechanical-enforcement
- **Title:** Mechanical enforcement of the test intent docstring (P9) (#14)
- **Opened:** 2026-08-14
- **Status:** candidate
- **Description:** v0.7.0 CLOSURE backlog return, materialized 2026-08-14 (grill ADR #5 — the CLOSURE claimed this routing but it never happened). CLOSURE text: "Mechanical enforcement of the intent docstring (P9). 384 existing files are non-compliant, so a check today would be unsatisfiable — a defect in the check under the Satisfiable Diagnostics law. Enforceable once the companion remediation lands." The companion remediation is the (rewritten) test-suite-remediation-stewardship entry; this check stays blocked on it.
- **Provenance:** v0.7.0 CLOSURE return (operator-approved closure) — materialized 2026-08-14
- **Intents:**
```yaml
- subject:
    kind: doc
    ref: memory/quality-assurance.md#Anti-Slop
  change: Once the suite remediation brings existing test files into intent-docstring compliance,
    add the mechanical check (lint/CI) that refuses a new test without a declared intent/size
    — satisfiable by construction only after the remediation, per the Satisfiable Diagnostics
    law.
```

### gitflow-reconciliation-merge-mechanic
- **Title:** dadaia-gitflow: record the reconciliation-merge mechanic (#15)
- **Opened:** 2026-08-14
- **Status:** candidate
- **Description:** v0.7.0 CLOSURE backlog return, materialized 2026-08-14 (grill ADR #5 — the CLOSURE claimed this routing but it never happened). CLOSURE text: "One line stating that every squash-merge to main requires a subsequent reconciliation merge of main into develop, and that such a merge resolves resurrected loose copies in favour of develop's archives. public/** is ai-engineer's surface." Verified at HEAD 2026-08-14: dadaia_workspace/public/skills/dadaia-gitflow/SKILL.md carries no "reconciliation" mention — the mechanic is still undocumented.
- **Provenance:** v0.7.0 CLOSURE return (operator-approved closure) — materialized 2026-08-14
- **Intents:**
```yaml
- subject:
    kind: catalog
    ref: sdd-bug-backlog-governance
  change: 'The dadaia-gitflow skill (canonical source under dadaia_workspace/public/skills/, ai-engineer
    surface) gains the reconciliation-merge line: every squash-merge to main is followed by a
    reconciliation merge of main into develop, resolving resurrected loose copies in favour of
    develop''s archives. Note: if the dd-skills release renames/absorbs dadaia-gitflow content,
    the line lands wherever the branch contract lives then.'
```

### memory-path-class-dotfiles
- **Title:** MEMORY path class vs dotfiles / SPEC-assigned memory writes (#16)
- **Opened:** 2026-08-14
- **Status:** candidate
- **Description:** v0.7.0 CLOSURE backlog return, materialized 2026-08-14 (grill ADR #5 — the CLOSURE claimed this routing but it never happened). CLOSURE text: "Decide whether specs/memory/.heading-allowlist (and dotfiles under specs/memory/ generally) belongs to the MEMORY class, and whether a SPEC may legitimately assign a memory-class path to a non-CLOSURE task." Verified at HEAD 2026-08-14: the gate classifies every path under specs/memory/ as MEMORY by prefix (features/spec_context/gate_policy.py:56 _MEMORY_PREFIX, :218-219), with writability restricted to DEFINITION/CLOSURE phases (:89 _MEMORY_WRITE_PHASES) — dotfiles included, undecided by doctrine.
- **Provenance:** v0.7.0 CLOSURE return (operator-approved closure) — materialized 2026-08-14
- **Intents:**
```yaml
- subject:
    kind: code
    ref: dadaia_workspace/features/spec_context/gate_policy.py#classify_path
  change: 'Decide and encode: (a) whether dotfiles under specs/memory/ (e.g. .heading-allowlist)
    are MEMORY-class or a carve-out; (b) whether a SPEC may assign a memory-class write to a non-CLOSURE/DEFINITION
    task, and how the gate should treat that assignment. The decision lands as code + a documented
    rule, not as an ad-hoc exception.'
```

### commit-paths-index-scope-hardening
- **Title:** commit_paths index-scope hardening: checked git add + path-scoped commit (CWE-754/CWE-668) (#18)
- **Opened:** 2026-08-14
- **Status:** candidate
- **Description:** Materializes the single LOW finding of the APPROVED security review covering the v0.5.2 hotfix (handoff 2026-08-14T172631Z-security-reviewer-hotfix-v0.5.2- scaffold-commit-scope). GitSubprocessClient.commit_paths discards the exit status of its `git add -- <paths>` and then commits the WHOLE INDEX (`git commit -m <msg>` with no pathspec). Two reachable divergences between `paths` and the index: (1) the target repo's .gitignore covers a scaffold path (e.g. specs/), git add exits non-zero and the failure is swallowed; (2) the operator had already staged unrelated content before `dadaia context alive`. Either way that content lands in the scaffold-titled commit — the same consent class as bug context-alive-sweeps-unrelated-worktree-changes (fixed in v0.5.2), narrowed to index-staged content. CWE-754 (Improper Check for Unusual or Exceptional Conditions) with a CWE-668 consequence; OWASP A08. Declared non-blocking for that push and routed as follow-up — this entry is that routing. Residual of the v0.5.2 fix; orbits the git_subprocess component alongside its v0.5.2 sibling surface.
- **Provenance:** APPROVED v0.5.2 security-review LOW routing — materialized 2026-08-14 (pre-ADR-15 regime)
- **Intents:**
```yaml
- subject:
    kind: code
    ref: dadaia_workspace/infrastructure/git_subprocess.py#GitSubprocessClient
  change: 'Make commit_paths honest by construction: (a) check the `git add -- <paths>` CompletedProcess
    and abort (raise GitSyncError) when returncode != 0, so a stage that did not happen never
    becomes a commit; (b) path-scope the commit itself — `git commit -m <msg> -- <paths>` — so
    unrelated index entries (operator pre-staged content) are ignored entirely. Option (b) subsumes
    (a) for the consent property; keep (a) anyway so silent stage failures surface instead of
    being swallowed by the caller''s contextlib.suppress.'
- subject:
    kind: code
    ref: dadaia_workspace/core/protocols/git_client.py#GitClient
  change: 'Defence in depth on the protocol-level primitive (reviewer INFO residual, unreachable
    today): git pathspec magic (`:/`, `:(glob)`, `:(exclude)`) survives the `--` separator, so
    a future caller passing an externally-influenced `:`-leading path would re-widen commit_paths
    back to a sweep. Prefix each element with `:(literal)` magic, or feed paths via `git add --pathspec-file-nul
    --pathspec-from-file=-` on stdin (which also removes the ARG_MAX ceiling noted at _stage_files_safe).'
```

### commit-message-scanning-residual
- **Title:** commit-message scanning: the residual channel the v0.9.0 blob-only scan leaves open — sized at 59 KB by the first squash-merge (#21)
- **Opened:** 2026-08-14
- **Status:** candidate
- **Description:** The one known hole left in the channel v0.9.0 closed, recorded deliberately at SPEC §4.2 (operator-ratified non-goal, "defer to backlog at closure") and routed by the CLOSURE. rev-list --objects lists commits WITHOUT a path and the shipped scanner reads blobs only, so a commit message (or annotated tag body) naming a private project is published with no refusal. The ship reviews sharpened the sizing decisively: the v0.9.0 main-reconciliation range published 0 bytes of scannable blob content and 59,263 characters (1,229 lines) of unscannable commit-message content — the GitHub squash-merge workflow concatenates every commit message of a PR into ONE commit object, so the residual is not "a subject line might name a client" but the entire authored narrative of a release in a single object the gate structurally cannot see. Scope per the reviewer: scan the range's COMMIT OBJECTS (message bodies), including the squash-merge shape and annotated tag bodies; for a reconciliation merge the commit objects are the only scan target since no blob is published. Both v0.9.0 ranges' bodies were verified clean by hand (27 + 2 commits; only the Co-Authored-By tooling trailer matched) — the manual check this entry mechanizes.
- **Provenance:** v0.9.0 SPEC §4.2 operator-ratified non-goal ('defer to backlog at closure') — pre-approved intake (ADR #15 retroactive ruling)
- **Intents:**
```yaml
- subject:
    kind: code
    ref: dadaia_workspace/container.py#build_git_object_reader
  change: Extend the reader seam (or build a sibling at the same composition root) to yield the
    commit objects of the pushed range — message bodies, and annotated tag bodies for tag refs
    — through the same batched conversation and typed-error contract, so the matcher can scan
    them like blobs.
- subject:
    kind: code
    ref: dadaia_workspace/features/chokepoints/service.py#push_gate_decision
  change: Feed range commit messages through the same three term layers with the same masked,
    satisfiable refusal shape; the healing action differs (reword/amend before push — for local
    unpublished commits this demands no published-history rewrite, same guarantee as the blob
    scope).
- subject:
    kind: doc
    ref: memory/product/sdd/sdd-gate-v3.md#Non-Goals
  change: 'Retire the blob-only limitation from the gate atom''s stated non-goals: coverage becomes
    blob + commit-object; record the squash-merge sizing evidence as the motivation.'
```

### baseline-carve-out-review-cadence
- **Title:** privacy-baseline pattern versioning + carve-out review cadence (three reactive exclusions in one release) (#24)
- **Opened:** 2026-08-14
- **Status:** candidate
- **Description:** v0.9.0 CLOSURE "Backlog returns" item, included at the PE's judgement because the drift it generalizes is a class, not a one-off. The RFC-2606 reserved-TLD gap was found only by the baseline refusing legitimate synthetic content on its first real run — by accident of timing, not by review — and the release then added three carve-outs reactively (RFC-2606 emails, the product's own workspace.local identity in two patterns, the stdlib Path.home call forms), taking privacy_baseline.json from v1 to v4 in one cycle. There is no defined moment at which the six patterns and their exclude_regex carve-outs are re-examined against the reserved/synthetic-value RFCs. The round-2 code review named the underlying treadmill: internal-hostname treats ANY dotted identifier chain ending in local|internal|lan|intranet|corp|home as a hostname, so `<name>.local`, `<attr>.internal`, `<x>.home` and every future equivalent will each demand another literal exclusion — the false-positive class is unbounded while carve-outs are literal-by-literal. Candidate shapes from the routing: a periodic review lane; a doctor check flagging baseline patterns lacking a documented carve-out rationale; and (from the review) a structural fix for the dotted-chain class instead of a fourth literal. A constraint to preserve, recorded in the CLOSURE accepted-without-action list: baseline patterns must stay single-line (the push scan matches line-by-line while the public-privacy doctor matches whole text).
- **Provenance:** v0.9.0 CLOSURE return — pre-approved intake (ADR #15 retroactive ruling, operator deferral)
- **Intents:**
```yaml
- subject:
    kind: code
    ref: dadaia_workspace/infrastructure/privacy_check.py#load_baseline_patterns
  change: 'Give the baseline a reviewable shape: each pattern carries a documented rationale for
    every exclude_regex carve-out, and a doctor/CI check flags patterns lacking one; version history
    stays in the JSON. Record the cadence itself (what triggers a re-examination and a version
    bump, and the single-line pattern constraint) as product truth in the gate atom at delivery.
    If baseline v5 is ever opened, evaluate the reviewer suggestion of a per-scan deadline that
    fails CLOSED.'
- subject:
    kind: code
    ref: dadaia_workspace/infrastructure/privacy_check.py#_scan_text_for_baseline
  change: Structural fix option for the internal-hostname dotted-chain false-positive class (require
    hostname-ish context, or exclude chains whose preceding label is a capitalised identifier),
    replacing the literal-by-literal treadmill; paired counter-fixtures keep proving narrowness.
```

### backlog-tooling-reconciliation
- **Title:** Backlog tooling reconciliation: point the per-entry-file tooling at single-source BACKLOG.md (incl. the Consumes checklist consumer) (#30)
- **Opened:** 2026-08-15
- **Status:** picked
- **Description:** v0.10.0 shipped the ADR #14 doctrine (law + dd-backlog-definition schema): the backlog converges to one specs/backlog/BACKLOG.md with an ACTIVE section and a LEDGER section. The tooling still implements the per-entry-file model end to end (v0.10.0 SPEC §4.5, operator-ratified deferral): features/backlog/{doctor,ledger,ledger_writer,preview, removal_lifecycle}.py, the `dadaia backlog new`/`backlog doctor` CLI verbs (new_artifacts.py + newartifacts.py), SPEC-DOC-031 in doctor_governance.py, the BL-SCHEMA/BL-STALE codes, public/scaffold/backlog/README.md, and public/data/CONSUMER_VALIDATION_RECIPE.md. Reconcile all of it with the single-source schema. FOLDED IN (intake report #2 item 2-2, approved as merge): dd-release-definition §5 keeps the `**Consumes:**` protocol as a checklist requirement while no CLI verb invokes removal_lifecycle.py — its former caller was the deleted workflow engine — so a required release-definition step has no executor; this release must either ship the CLI consumer for the removal lifecycle or rewrite the checklist to the mechanism that actually runs.
- **Provenance:** pre-approved intake P-1 (operator ratification at the v0.10.0 approval, SPEC §4.5/§4.10), materialized 2026-08-15; intake-report #2 item 2-2 approved as merge 2026-08-15 (operator-delegated); picked — v0.12.0 (SPEC §7)
- **Intents:**
```yaml
- subject:
    kind: code
    ref: dadaia_workspace/features/backlog/doctor.py#run_backlog_doctor
  change: Validate the single-source BACKLOG.md (ACTIVE subsection schema, LEDGER line grammar,
    terminal disposition tokens) instead of per-entry files; keep BL-SCHEMA/BL-STALE/BL-CONFLICT
    semantics over the new physical shape.
- subject:
    kind: cli
    ref: backlog new
  change: Author a new ACTIVE subsection in BACKLOG.md (title/opened/status/description/ provenance)
    instead of scaffolding a per-entry file.
- subject:
    kind: code
    ref: dadaia_workspace/features/backlog/document.py#load_document
  change: Load items from BACKLOG.md ACTIVE subsections (one item per subsection) instead of globbing
    per-entry files; intents/anchor binding preserved. T-120-08 cutover note (grill/PLAN §5) — the
    per-entry loader `preview.load_backlog_items` this intent originally named is DELETED by this
    same cutover, its replacement being exactly this anchor; the ref is repointed post-cutover so
    the entry stays BL-SCHEMA-resolvable across the whole picked window, per the standing green
    rule (ADR D1).
- subject:
    kind: code
    ref: dadaia_workspace/features/specs/doctor_governance.py#_BACKLOG_SINGLE_SOURCE_FILES
  change: Re-target SPEC-DOC-031 (and any sibling backlog-governance checks) at BACKLOG.md; drop
    checks that only make sense for per-entry files. T-120-08 cutover note (grill/PLAN §6) — this
    intent originally named `_BACKLOG_AGGREGATE_FILES`, DELETED by this same cutover and replaced
    by `_BACKLOG_SINGLE_SOURCE_FILES`; the ref is repointed post-cutover for the same reason as
    above.
```

### backlog-md-physical-consolidation
- **Title:** Physical BACKLOG.md consolidation: per-entry files + candidates.md → single-source ACTIVE + LEDGER (#31)
- **Opened:** 2026-08-15
- **Status:** picked
- **Description:** Execute the physical half of the ADR #14 convergence that v0.10.0 shipped as doctrine (law §5 Backlog + dd-backlog-definition §2): fold every live per-entry file under specs/backlog/*.md plus the candidates.md index into ONE specs/backlog/BACKLOG.md with an ACTIVE section (one strict-schema subsection per live candidate: Title, Opened, Status, Description, Provenance) and a LEDGER section (one line per closed item carrying its terminal disposition token). Never-delete law holds throughout: every terminal row from candidates.md and _archive/ frontmatter gets a LEDGER line; no record is lost. PM curation surface (specs/backlog/** is project-manager-owned). Sequences WITH/AFTER backlog-tooling-reconciliation — consolidating before the tooling ships would break `backlog new`/`backlog doctor`/SPEC-DOC-031, which still read and validate per-entry files (v0.10.0 SPEC §4.4/D5 + §4.5, R6).
- **Provenance:** pre-approved intake P-2 (operator ratification at the v0.10.0 approval, SPEC §4.4/D5), materialized 2026-08-15; picked — v0.12.0 (SPEC §7)
- **Intents:**
```yaml
- subject:
    kind: doc
    ref: memory/product/sdd/sdd-bug-backlog-governance.md#Backlog
  change: 'The runtime-state reality matches the atom''s single-source BACKLOG.md doctrine: specs/backlog/
    carries BACKLOG.md (ACTIVE + LEDGER) as the format of record; the per-entry files and candidates.md
    are consolidated in, with provenance lines preserved per entry; the atom''s pending-consolidation
    note is retired at the consolidating release''s CLOSURE.'
```

### dd-skills-applyto-glob-collisions
- **Title:** dd- skill family: applyTo glob collisions blur the one-skill-per-stage activation boundary (#32)
- **Opened:** 2026-08-15
- **Status:** candidate
- **Description:** The seven dd-* lifecycle skills' `applyTo` frontmatter globs collide pairwise — e.g. two skills both claim specs/backlog/** — so the one-skill-per-stage boundary the family was built on is not expressed in the activation surface: a harness resolving which skill governs a path can activate the wrong stage's skill or two at once. Verified live at HEAD 57dc4937 in all seven canonical SKILL.md frontmatters. Fix: partition the globs so each lifecycle stage owns a disjoint activation surface (or document an explicit precedence rule where genuine overlap is intended), and add a projection-time collision check so a future skill cannot silently reintroduce the ambiguity.
- **Provenance:** intake-report #2 item 2-1 (approved 2026-08-15, operator-delegated adjudication)
- **Intents:**
```yaml
- subject:
    kind: catalog
    ref: agentic-entities
  change: The dd- family's applyTo globs become pairwise disjoint (or carry a documented precedence
    rule); the agentic-entities derivation/lint surface gains a check that flags colliding applyTo
    globs across projected skills.
```

### dd-release-definition-orchestration-pointer-loop
- **Title:** Circular pointer: dd-release-definition ↔ project-orchestration release-definition playbook (#33)
- **Opened:** 2026-08-15
- **Status:** candidate
- **Description:** dd-release-definition/SKILL.md:103 sends the reader to the project-orchestration release-definition playbook for the authority/dispatch view, while v0.10.0 reduced that playbook to a pointer back at dd-release-definition — a reference loop with no content at either end. One of the two ends must carry the actual statement (the playbook keeps its one-line dispatch note but names what it owns, or the skill's pointer is dropped). Not in the dispatcher's brief for the intake compilation; added by PM verification — a review round's residual is never dropped silently. One-line fix; rides with the applyTo-glob entry in the same ai-engineer window.
- **Provenance:** intake-report #2 item 2-3 (approved 2026-08-15, operator-delegated adjudication)
- **Intents:**
```yaml
- subject:
    kind: catalog
    ref: agent-orchestration
  change: 'The dd-release-definition ↔ project-orchestration cross-references form a DAG again:
    exactly one of the two files carries the release-definition authority/dispatch content, the
    other points at it; no pointer loop remains in public/.'
```

### bug-event-redaction-always-on-reinforcement
- **Title:** Bug-event redaction rule is on-demand only — add one always-on reinforcement line in law §6 (#34)
- **Opened:** 2026-08-15
- **Status:** candidate
- **Description:** The v0.10.0 dehydration moved the bug-event redaction rule (no absolute local paths, IPs, hostnames, private names or secrets in any bug-event field) from the always-on law into the on-demand dd-bug-registration skill (§3). An agent that registers a bug without invoking the skill — bug paths are ADDITIVE and registration is deliberately frictionless — no longer sees the rule at the moment it writes the event. Fix shape named by the reviewer: ONE always-on reinforcement line in DADAIA.md §6's register-every-bug paragraph pointing at the redaction rule, keeping the full rule on-demand in the skill (no rehydration of the dehydrated block). Distinct from live entry #23 refusal-path-redaction: that is the push-refusal renderer printing blob paths; this is the bug-event field rule's always-on visibility — different surface, no dedupe (dedupe record in intake report #2).
- **Provenance:** intake-report #2 item 2-4 (approved 2026-08-15, operator-delegated adjudication)
- **Intents:**
```yaml
- subject:
    kind: catalog
    ref: public-asset-distribution
  change: public/data/DADAIA.md §6 (Register every bug) gains one always-on line reinforcing the
    redaction rule by reference to dd-bug-registration §3; projected law files re-installed; no
    second full statement of the rule enters the law.
```

### dd-audit-project-pinned-tool-installs
- **Title:** dd-audit-project: pin the third-party scan-tool installs (unpinned pip/npx guidance) (#35)
- **Opened:** 2026-08-15
- **Status:** candidate
- **Description:** Pre-existing supply-chain guidance carried through the v0.10.0 rename: the audit skill (dd-audit-project, formerly the audit skill under its old name) instructs installing third-party scanning tools via unpinned `pip install <tool>` / `npx <tool>` — an unpinned install at audit time executes whatever the registry serves that day, inside the workspace venv. Fix: version-pin (or hash-pin) every tool invocation the skill prescribes, and state the rule once so future tool additions inherit it.
- **Provenance:** intake-report #2 item 2-5 (approved 2026-08-15, operator-delegated adjudication)
- **Intents:**
```yaml
- subject:
    kind: doc
    ref: memory/quality-assurance.md#Dependencies
  change: 'The audit-lane tool-install guidance is pinned: dd-audit-project prescribes exact versions
    (or hashes) for every third-party scanner it instructs installing, and the dependency-hygiene
    doctrine records that audit tooling follows the same pinning rule as production dependencies.'
```

### dadaia-cli-skill-agent-grant
- **Title:** dadaia-cli skill granted to no agent while its description claims all agents may use it (#36)
- **Opened:** 2026-08-15
- **Status:** candidate
- **Description:** F-1 (v0.10.0 SPEC §4 item 7, verified): the dadaia-cli skill's description claims "all agents may use it" while it appears in NO agent's frontmatter `skills:` list — under frontmatter-scoped grants it is reachable only by the top-level session, so every dispatched sub-agent that needs CLI literacy is working from a skill it cannot activate. Pre-existing, independent of the v0.10.0 family. Fix: decide the intended reachability and make grant and description agree — either grant dadaia-cli to the agents whose protocols invoke the CLI (with reasoned per-agent selection, not a blanket grant), or narrow the description to the top-level-session reality.
- **Provenance:** pre-approved intake P-3 (v0.10.0 SPEC §4.7 finding F-1), approved 2026-08-15 (operator-delegated)
- **Intents:**
```yaml
- subject:
    kind: doc
    ref: memory/product/agents/agentic-entities.md#Registry
  change: 'The registry/frontmatter skill grants and the dadaia-cli skill description agree: each
    agent whose protocol requires CLI invocation carries the grant, or the description stops claiming
    universal reachability; the derivation surface records the decided reachability so grant/description
    drift is checkable.'
```

### codex-skill-ref-phantom-memory-ctx-prefix
- **Title:** memory-ctx phantom prefix in _CODEX_SKILL_REF_PREFIXES (#37)
- **Opened:** 2026-08-15
- **Status:** candidate
- **Description:** v0.10.0 SPEC §4 item 8 (verified in-release): the _CODEX_SKILL_REF_PREFIXES tuple in runtime_transforms/codex_assets.py names "memory-ctx", a skill that does not exist in public/skills/ — the only memory-ctx asset lives at public/runtime/codex/memory-ctx/ (a Codex runtime adapter, not a grantable public skill), so the persona skill-ref filter whitelists a prefix no persona frontmatter can legitimately carry. Pre-existing; v0.10.0's FR13 changed only the two entries its rename required and routed this as a PM observation. Fix: remove the phantom prefix (or re-point it at the real asset surface if Codex personas are ever meant to reference the runtime adapter), and bind the tuple to the actual public/skills/ inventory with a test so a future rename or removal cannot leave another dead prefix behind.
- **Provenance:** pre-approved intake P-4 (v0.10.0 SPEC §4.8), approved 2026-08-15 (operator-delegated)
- **Intents:**
```yaml
- subject:
    kind: code
    ref: dadaia_workspace/infrastructure/runtime_transforms/codex_assets.py#_CODEX_SKILL_REF_PREFIXES
  change: Every prefix in the tuple corresponds to at least one skill that exists in public/skills/
    (or an explicitly documented runtime-asset exception); a unit test derives the expectation
    from the inventory so drift fails loud.
```

### bugs-jsonl-whole-blob-per-append
- **Title:** bugs.jsonl republishes its whole file as a new blob on every append — the dominant scan-cost and content-resurfacing driver
- **Opened:** 2026-08-14
- **Status:** idea
- **Description:** v0.9.0 CLOSURE "Backlog returns" idea (routed to the ideas lane at the PE's judgement), reinforced twice by the ship security review. Because git stores a whole blob per file version, every `dadaia bugs append` republishes the entire ~900 KB specs/bugs/bugs.jsonl as a NEW blob in the pushed range. Two measured costs: (1) performance — one such blob appended twice inside v0.9.0's local range dominated the push-range scan (~2.7-3.4 s wall over 247 objects / 66 blobs) and is the reason the A7.3 2 s budget was recorded as partially missed (V14: cause is data, not mechanism); (2) content resurfacing — every append makes ALL long-published lines of the file "new" range content again, which is how the security review's wider-set probe surfaced two historical hits on bugs.jsonl:353 (a since-DEAD context name resident since v0.1.x). Candidate shapes to weigh at grill time: per-bug or per-period sharding of the ledger (e.g. bugs/<year>/ or bugs/<bug-id>.jsonl), an append-only segment scheme, or accepting the cost and letting prior-published-term-amnesty neutralize the resurfacing half. Constraints: the never-delete law (events are kept forever), the ADDITIVE gate classification of specs/bugs/**, the jsonl append contract used by dadaia bugs append/status/stats, and existing bugs.jsonl consumers (panel, doctor, release pick precedence).
- **Provenance:** v0.9.0 CLOSURE return (ideas lane) — pre-approved intake (ADR #15 retroactive ruling, operator deferral)

### flat-release-ship-task-evidence
- **Title:** Flat release's ship task cannot record its own completion (TASKS template shape defect)
- **Opened:** 2026-08-14
- **Status:** idea
- **Description:** v0.8.0 CLOSURE backlog return, materialized 2026-08-14. In a flat (no-segment) release, the closure/archive task freezes the release directory (git mv to specs/_archive/) before the ship task can flip its own marker: v0.8.0's T-080-07 (ship) archived as "[ ]" because T-080-06 (closure + archive) ran first and the archived TASKS.md is FROZEN — the ship marker can never be flipped afterwards. The release TASKS template needs a form of ship evidence that lives outside the archived directory: either make ship the last task BEFORE archive, or state in the template that the ship task's evidence is the merge/PR itself and that its marker is expected to archive open.
- **Provenance:** v0.8.0 CLOSURE return (ideas lane); second occurrence routed by the v0.9.0 CLOSURE — operator-approved closures

### repo-agents-md-symlink-hardening
- **Title:** Destination-file symlink hardening for the adjacent repo-AGENTS.md copy
- **Opened:** 2026-08-14
- **Status:** idea
- **Description:** v0.7.0 CLOSURE backlog return, materialized 2026-08-14 (grill ADR #5 — the CLOSURE claimed this routing but it never happened). CLOSURE text: "Destination-file symlink hardening for the adjacent repo-AGENTS.md copy, matching workspace_guardrail.py's four refusal sites. The new tests/AGENTS.md seam was hardened at review r2; its neighbour still follows the older shape." Verified at HEAD 2026-08-14: infrastructure/public_assets.py carries no symlink refusal (grep symlink/is_symlink: none) — the neighbour seam is still unhardened.
- **Provenance:** v0.7.0 CLOSURE return (ideas lane) — materialized 2026-08-14

### stewardship-relocation-grep-homonym-note
- **Title:** Note the relocation-grep homonym collision in the stewardship skill
- **Opened:** 2026-08-14
- **Status:** idea
- **Description:** v0.7.0 CLOSURE backlog return, materialized 2026-08-14 (grill ADR #5 — the CLOSURE claimed this routing but it never happened). CLOSURE text: "Note the relocation-grep homonym collision in the skill so a future auditor does not chase pre-existing, unrelated uses of 'scaffold'/'sentinel'/'quarantine' (QA finding F1)." Verified at HEAD 2026-08-14: dadaia-test-stewardship SKILL.md carries no such note. If the dd-skills release restructures the skill, the note lands in its successor.
- **Provenance:** v0.7.0 CLOSURE return (ideas lane) — materialized 2026-08-14

### tests-agents-md-placeholder-doctor-warning
- **Title:** doctor/lint warning for an installed tests/AGENTS.md still carrying <PLACEHOLDER> tokens
- **Opened:** 2026-08-14
- **Status:** idea
- **Description:** v0.7.0 CLOSURE backlog return, materialized 2026-08-14 (grill ADR #5 — the CLOSURE claimed this routing but it never happened). CLOSURE text: "A doctor/lint warning for an installed tests/AGENTS.md that still contains <[A-Z_]+> placeholders (code review r1 finding 8, half-implemented: the fill-me banner shipped, the check did not)." Verified at HEAD 2026-08-14: placeholder checks exist only for memory atoms (MEM-PLACEHOLDER-1, features/specs/doctor.py:119) — no check covers an installed tests/AGENTS.md.
- **Provenance:** v0.7.0 CLOSURE return (ideas lane) — materialized 2026-08-14

## LEDGER

- push-range-denylist-scan · DELIVERED · v0.9.0 · 2026-08-14
- redact-foreign-context-names-at-qa-authoring · DELIVERED · v0.9.0 · 2026-08-14
- tag-push-carve-out-reachability · DELIVERED · v0.9.0 · 2026-08-14
- 20260814-dd-lifecycle-skills-family · DELIVERED · v0.10.0 · 2026-08-15
- prior-published-term-amnesty · DELIVERED · v0.11.0 · 2026-08-15
- denylist-scan-skip-note-oversized-mislabel · DELIVERED · v0.11.0 · 2026-08-15
- registry-derived-foreign-name-set · DELIVERED · v0.11.0 · 2026-08-15
- refusal-path-redaction · DELIVERED · v0.11.0 · 2026-08-15
- push-ref-sha-validation-git-argv-hardening · DELIVERED · v0.11.0 · 2026-08-15
- git-objects-batch-parse-typed-error-boundary · DELIVERED · v0.11.0 · 2026-08-15
- git-objects-streamed-batch-reads · DELIVERED · v0.11.0 · 2026-08-15
- closure-v14-perf-figure-correction · DELIVERED · v0.11.0 · 2026-08-15
- self-scan-sentinel-integration-marker · DELIVERED · v0.11.0 · 2026-08-15
- loud-flake-stats-key-residual · DELIVERED · fixed before materialization · 2026-08-14
- frozen-wall-clock-baselines-in-repo-text · DELIVERED · baselines embedded in memory · 2026-08-14
- dispose-published-denylist-term · REJECTED · void by construction under the range-scoped scan · 2026-08-14
- 20260714-panel-games-pong-codex-v026 · REJECTED · surface removed in v0.3.0, nothing to validate · 2026-08-14
- 20260714-snake-wall-wrap-v025-pi-validation · REJECTED · same removal, nothing to validate · 2026-08-14
- intake-2-6-consumer-validation-recipe-glob · REJECTED · operator discard at intake (delegated) · 2026-08-15
- intake-2-8-spec-drafting-zero-hit-grep-lesson · REJECTED · operator discard at intake (delegated) · 2026-08-15
- 20260704-fast-tier-persona-validation · REJECTED · v0.1.64 · 2026-07-09
- 20260707-dispatch-band-legacy-fallback-removal · SUPERSEDED · deprecation-strips-and-doctor-cleanup (2026-07-10 consolidation) · 2026-07-10
- 20260707-platform-seam-todo-retirement · SUPERSEDED · lock-lease-session-identity-kernel (2026-07-10 consolidation) · 2026-07-10
- 20260707-specs-doctor-partial-archive-invariant · SUPERSEDED · deprecation-strips-and-doctor-cleanup (2026-07-10 consolidation) · 2026-07-10
- 20260708-panel-tab-reorg-agentic-layers · DELIVERED · v0.1.79 · 2026-07-11
- 20260709-central-bind-resolution-seam · DELIVERED · v0.1.77 · 2026-07-11
- 20260709-implement-review-write-scope-from-tasks-parity · SUPERSEDED · lifecycle-pipeline-correctness-and-diagnosability (2026-07-10 consolidation) · 2026-07-10
- 20260709-preflight-block-reasons-missing-operator-command · SUPERSEDED · lifecycle-pipeline-correctness-and-diagnosability (2026-07-10 consolidation) · 2026-07-10
- 20260709-tasks-write-scope-traversal-hardening · SUPERSEDED · lifecycle-pipeline-correctness-and-diagnosability (2026-07-10 consolidation) · 2026-07-10
- 20260709-test-suite-remediation-waves · CONSUMED · v0.1.75 (PR #145) · 2026-07-10
- 20260710-deprecation-strips-and-doctor-cleanup · DELIVERED · v0.1.81 (date gate operator-waived 2026-07-11) · 2026-07-11
- 20260710-lifecycle-pipeline-correctness-and-diagnosability · DELIVERED · v0.1.78 · 2026-07-11
- 20260710-lock-lease-session-identity-kernel · DELIVERED · v0.1.76 (NO-LOCKS doctrine) · 2026-07-10
- 20260711-context-name-allowlist-at-resolution-rungs · DELIVERED · v0.1.80 · 2026-07-11
- 20260715-bugfix-workflow-tdd · REJECTED · v0.3.0 engine demolition — strict-TDD bug flow is law (constitution §1) · 2026-08-12
- 20260806-clean-architecture-remediation · CONSUMED · v0.5.0 · 2026-08-12
- 20260806-dadaia-md-workspace-system-prompt · CONSUMED · v0.5.0 · 2026-08-12
- 20260810-security-low-carryforwards-v030 · CONSUMED · v0.5.0 · 2026-08-12
- backlog-definition-workflow-dedup-conflict-control · DELIVERED · v0.1.26 · 2026-07-02
- codex-runtime-fidelity · DELIVERED · v0.1.13 (WS-CDX waves; protocol+hygiene verified at HEAD) · 2026-07-02
- gitflow-standardization · DELIVERED · v0.6.0 · 2026-08-12
- l1-agent-model-governance-panel · DELIVERED · v0.1.65 · 2026-07-08
- lifecycle-prompt-fragments-ai-surface-dehydration · DELIVERED · v0.1.30 (Waves A/E) · 2026-07-02
- selfrepo-agents-md-doubled-header · DELIVERED · v0.1.61 · 2026-07-07
- shared-headless-adapter-base · DELIVERED · v0.1.30 Wave A · 2026-07-02
- test-artifact-hygiene · CONSUMED · bug panel-e2e-artifacts-no-consumer (operator ruling 2026-08-12 — bad tests are bugs) · 2026-08-12
- test-runtime-efficiency · CONSUMED · bug test-suite-real-venv-and-ci-longpole (operator ruling 2026-08-12 — bad tests are bugs) · 2026-08-12
- test-stewardship-standardization · DELIVERED · v0.7.0 · 2026-08-12
- wire-consumed-ledger-producer-at-release-definition · DELIVERED · v0.1.27 · 2026-07-02
- workflow-model-governance-operator-profiles-and-context-overlays · DELIVERED · workflow-engine era, terminal frontmatter (engine removed v0.3.0) · 2026-07-02
- workflow-model-governance-panel-control-plane · DELIVERED · v0.1.28 · 2026-07-02
- workflow-step-handoff-data-plane-cleanup · DELIVERED · workflow-engine era, terminal frontmatter (engine removed v0.3.0) · 2026-07-02
