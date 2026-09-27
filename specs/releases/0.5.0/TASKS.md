# TASKS — Release: 0.5.0

**Status:** Approved
**Owner:** dd-software-engineer

Paths as in PLAN (`f/` features, `i/` infrastructure, `pub/` public). Each bug = one shape-3 commit
`fix(bugs): <id> — <cause>` (code + regression test + its `BUGS.jsonl` line; loser tests and fakes
deleted in it); the task flip is its own `chore(tasks)` commit. `RED:` names the PLAN §2 row whose
`<bug-id>#<id>` statements the tests cite and which fail before the change; each write set includes its
tests. `Δ` = prod/test lines; PLAN §2.7 ceilings stop a task, never rise.

## Candidate 4 — systemic ambiguity remediation

### W0 — data loss, leaks, gate holes (FR1)

- [x] **T-050-23 — Reaper keeps its holds + `release-as`.** `W:` `f/spec_context/{sweep,doctor}.py`, `cli/commands/doctor.py`, `pub/skills/dd-cli-library/SKILL.md`, `release-please-config.json`
  `blocked by:` none · `delivers:` two same-second reaps leave two intact holds (AC1.2, AC1.6) · `RED:` PLAN §2 WP-02 · Δ −4/+40.
- [x] **T-050-24 — Install ledger owns harness dirs (04, 06).** `W:` `i/`, `f/spec_context/doctor.py`
  `blocked by:` T-050-23 · `delivers:` operator files survive install and `doctor --fix` · `RED:` PLAN §2 WP-04, WP-06 · Δ −131/+7.
- [x] **T-050-25 — `workspace_layout.verdict` (05).** Move, switch, delete. `W:` `core/workspace_layout.py`, `hooks/`, `f/spec_context/`, `pub/data/`
  `blocked by:` T-050-23 · `delivers:` gate ALLOW ⇔ doctor not SLOP · `RED:` PLAN §2 WP-05 · Δ −30/+75.
- [x] **T-050-26 — One `InstallPlan` (08).** `W:` `cli/commands/public.py`, `i/{projection_rules,public_assets}.py`
  `blocked by:` T-050-24 · `delivers:` a scoped install is impossible · `RED:` PLAN §2 WP-08 · Δ −40/+14.
- [x] **T-050-27 — Repo law only via `specs init` (07 †).** `W:` `i/`, `cli/commands/public.py`, `f/specs/canon.py`, `f/spec_context/service.py`
  `blocked by:` T-050-26 · `delivers:` install-first leaves the repo template; edits survive · `RED:` PLAN §2 WP-07 · Δ −230/−119.
- [x] **T-050-28 — Ledger pair checked first (09).** `W:` ledger `scripts/`
  `blocked by:` none · `delivers:` a refusal leaves both files byte-intact · `RED:` PLAN §2 WP-09 · Δ −10/+80.
- [x] **T-050-29 — One mask, one redactor (11 †).** `W:` `core/redaction.py`, `cli/`, `f/chokepoints/`, `i/privacy_check.py`
  `blocked by:` none · `delivers:` `z…x` from every surface · `RED:` PLAN §2 WP-11 · Δ −30/+25.
- [x] **T-050-30 — Gate judges every harness; Codex read-only (12, 13).** `W:` `i/runtime_*`, `hooks/`, `core/invocation.py`, `pub/entities/`
  `blocked by:` none · `delivers:` AC1.4, AC1.5 · `RED:` PLAN §2 WP-12, WP-13 · Δ +7/+97.
- [x] **T-050-31 — One symlink-refusing writer (14).** `W:` `f/migrate/`, `core/atomic_write.py`, `f/specs/`, `cli/commands/specs.py`
  `blocked by:` none · `delivers:` a symlink target is never written · `RED:` PLAN §2 WP-14 · Δ −30/+65.
- [x] **T-050-32 — Gate where git runs it; required checks (hooksPath, 32).** Two commits.
  `W:` `f/spec_context/{service,doctor}.py`, `core/workspace_layout.py`, `.github/`, required-checks file, `f/ci_preflight/`
  `blocked by:` none · `delivers:` AC1.3, AC1.7 · `RED:` PLAN §2 hooksPath, WP-32 · Δ −70/+141.
- [x] **T-050-33 — `context dead` holds (03 †).** `W:` `f/spec_context/`, `i/git_subprocess.py`
  `blocked by:` T-050-23, T-050-28 · `delivers:` unpushed branch/worktree refused, else held · `RED:` PLAN §2 WP-03 · Δ +3/+78.

### M — never-again mechanism (FR5, FR6)

- [x] **T-050-34 — Authorities refusal + skills (FR5).** AUTHORING; re-project.
  `W:` `dd-release-impl/{_release_phase,_release_new}.py`, `pub/skills/{dd-release-definition,dd-code-review,dd-audit-project,dd-spec-navigator}/**`, `CONTEXT.md`
  `blocked by:` T-050-23..33 · `delivers:` a two-authority PLAN refused, one fix line (AC5.1–5.8) · `RED:` fixture PLAN pair.
- [x] **T-050-35 — V37–V39, zone widening, `shutil` contract (FR6).** `W:` `tests/contract/{test_slop_ratchets,test_zone_registry,test_required_evidence_has_one_home}.py`, `setup.cfg`
  `blocked by:` T-050-34 · `delivers:` AC6.1–6.8 · `RED:` one fixture per ratchet.

### H — test harness (FR9)

- [x] **T-050-36 — Real-git fixture; fakes out (AC9.4).** `W:` `tests/fakes.py`, `tests/fixtures/**`, 22 user files
  `blocked by:` T-050-35 · `delivers:` git questions tested against git · `RED:` `FakeContextStore` parity test · Δ 0/−500.
- [x] **T-050-37 — `DADAIA_FENCED_ROOTS`: declared feature, no dadaia process acts on a fenced root (0088).** `W:` `core/workspace_resolver.py`, `tests/conftest.py`, `tests/unit/cli/test_workspace_not_found_error.py`, `pub/data/dadaia-AGENTS.md`
  `blocked by:` T-050-36 · `delivers:` PLAN §2 FR9 fence · `RED:` `sa-seven-workspace-root-rules#S11` (AC9.12, 0088) · Δ +3/+10.
- [ ] **T-050-38 — Hooks spawn as production; `WORKSPACE_ROOT` gone (15 †, AC9.5).** `W:` `tests/fixtures/harness_env.py`, `core/`, `cli/commands/`, `f/migrate/`, `f/specs/memory_lint.py`, `registry.py`
  `blocked by:` T-050-37 · `delivers:` one root rule, honest hook tests · `RED:` PLAN §2 WP-15 · Δ −25/+108.

### W1 — stalls, loops, unclearing fixes (FR2)

- [ ] **T-050-39 — One bind (16 †).** `W:` `core/invocation.py`, `f/workspace/`, `hooks/`, `f/spec_context/`, `cli/`, `pub/data/`
  `blocked by:` T-050-38 · `delivers:` four readers agree · `RED:` PLAN §2 WP-16 · Δ −5/+115.
- [ ] **T-050-40 — Fix lines, one printer, unfixable fixes (17–19 †).** Three commits. `W:` `core/`, `hooks/`, `f/chokepoints/`, `f/spec_context/`, `cli/`
  `blocked by:` T-050-39 · `delivers:` AC2.2, AC2.3 · `RED:` PLAN §2 WP-17, WP-18, WP-19 · Δ −48/+315.
- [ ] **T-050-41 — TREE-8 alone (20).** `W:` `f/specs/` · `blocked by:` T-050-40 · `delivers:` one finding per stray path · `RED:` PLAN §2 WP-20 · Δ −115/−40.
- [ ] **T-050-42 — One registry-version grammar (21 †).** `W:` `i/json_context_store.py`, `f/migrate/`, `core/`, `cli/commands/`, `f/spec_context/` · `blocked by:` T-050-40 · `delivers:` readable ⇔ no migration · `RED:` PLAN §2 WP-21 · Δ −18/+100.
- [ ] **T-050-43 — Scripts own bug records and the seam (22, 23).** `W:` `core/`, `container.py`, `f/specs/`, `pub/skills/_shared/_privacy.py`, ledger `scripts/`, `pub/schemas/bugs/`, `i/public_assets.py`
  `blocked by:` T-050-28, T-050-40 · `delivers:` doctor = `bugs.py check`; seam ⇔ push · `RED:` PLAN §2 WP-22, WP-23 · Δ −700/−660.
- [ ] **T-050-44 — Backlog status and pick (24).** `W:` `f/backlog/`, backlog `scripts/`, `_release_new.py`, law · `blocked by:` T-050-43 · `delivers:` exit without hand edit · `RED:` PLAN §2 WP-24 · Δ −80/−40.
- [ ] **T-050-45 — `release.py ship` (25).** `W:` `dd-release-impl/scripts/`, `f/specs/`, releases law, RC-FLOW, gitflow · `blocked by:` T-050-44 · `delivers:` AC2.5 · `RED:` PLAN §2 WP-25 · Δ −40/−70.
- [ ] **T-050-46 — Status line; `measured_by` (26, 27).** `W:` `core/spec_status.py`, `f/specs/`, `pub/schemas/ADRs/`, `pub/scaffold/ADRs/` · `blocked by:` T-050-40 · `delivers:` one status token · `RED:` PLAN §2 WP-26, WP-27 · Δ −20/+50.
- [ ] **T-050-47 — `specs_version.state` (28 †).** `W:` `core/specs_version.py`, `cli/commands/ci.py`, `f/{specs,migrate,workspace,chokepoints}/` · `blocked by:` T-050-40 · `delivers:` pre-push judges the pushed commit · `RED:` PLAN §2 WP-28 · Δ −34/+145.
- [ ] **T-050-48 — One atom grammar (29).** `W:` navigator `scripts/`, `f/specs/`, `i/ledger_scripts.py`, `pub/scaffold/memory/` · `blocked by:` T-050-40 · `delivers:` one verdict per atom · `RED:` PLAN §2 WP-29 · Δ −155/−10.

### W2 — consolidations (FR3)

- [ ] **T-050-49 — `release.py check` (30).** `W:` `f/specs/`, `core/` · `blocked by:` T-050-45 · `delivers:` one live release · `RED:` PLAN §2 WP-30 · Δ −105/−100.
- [ ] **T-050-50 — Certify walks the workspace (31).** `W:` `f/{certification,reconcile}/`, recipe · `blocked by:` T-050-40 · `delivers:` AC3.2 · `RED:` PLAN §2 WP-31 · Δ −126/+116.
- [ ] **T-050-51 — Context repos; running version (33, 34).** `W:` `core/`, `i/`, `cli/`, `f/{capabilities,reconcile}/` · `blocked by:` T-050-39 · `delivers:` no name fallback; editable reports source · `RED:` PLAN §2 WP-33, WP-34 · Δ −18/+192.
- [ ] **T-050-52 — Subjects in the doctor (35).** `W:` backlog `scripts/`, `f/backlog/`, `core/models/backlog.py` · `blocked by:` T-050-44 · `delivers:` no circular RESOLVED · `RED:` PLAN §2 WP-35 · Δ −25/+39.
- [ ] **T-050-53 — Hook interpreter; reviewer persona (36, 37).** `W:` `i/`, `pub/agents/`, `pub/entities/` · `blocked by:` T-050-30 · `delivers:` AC3.3 · `RED:` PLAN §2 WP-36, WP-37 · Δ −27/+195.
- [ ] **T-050-54 — Rendered canon law (38).** `W:` `i/public_assets.py`, `core/workspace_layout.py`, `f/specs/`, `pub/templates/` · `blocked by:` T-050-27 · `delivers:` rendered tables · `RED:` PLAN §2 WP-38 · Δ +4/+33.

### W3 — design debt (FR4)

- [ ] **T-050-55 — One path classifier (39).** `W:` `f/spec_context/gate_policy.py`, `core/workspace_layout.py`, `f/specs/`, law · `blocked by:` T-050-25 · `delivers:` law = gate · `RED:` PLAN §2 WP-39 · Δ +5/−5.
- [ ] **T-050-56 — Caches in `.dadaia/tmp`; one TTL (40, 45).** `W:` `pyproject.toml`, `i/runtime_config.py`, `f/spec_context/markers.py`, `core/`, law · `blocked by:` T-050-23 · `delivers:` one clock · `RED:` PLAN §2 WP-40, WP-45 · Δ −67/+40.
- [ ] **T-050-57 — Work and principal branch (41, 42 †).** `W:` `f/spec_context/service.py`, `cli/commands/`, `f/specs/canon.py`, gitflow skill, repo `AGENTS.md` · `blocked by:` T-050-45 · `delivers:` AC4.2 · `RED:` PLAN §2 WP-41, WP-42 · Δ −1/+81.
- [ ] **T-050-58 — Audit close; script vocabulary + atomic write (43, 48).** `W:` `f/specs/`, `i/jsonl_record_store.py`, `core/models/`, ledger `scripts/`, `registry.py` · `blocked by:` T-050-43 · `delivers:` no invalid archive, no `.tmp` leak · `RED:` PLAN §2 WP-43, WP-48 · Δ −187/−295.
- [ ] **T-050-59 — Unconsumed assets leave (44).** `W:` `i/` · `blocked by:` T-050-26 · `delivers:` clean without the index · `RED:` PLAN §2 WP-44 · Δ −151/−100.
- [ ] **T-050-60 — Handoff v1.2; upgrade target (46, 47).** `W:` `pub/schemas/`, `core/handoff_index.py`, `cli/commands/specs.py`, `f/migrate/` · `blocked by:` T-050-31 · `delivers:` AC4.3 · `RED:` PLAN §2 WP-46, WP-47 · Δ −24/+15.
- [x] **T-050-61 — Restated rules; consumer law (49, FR-8).** `W:` `pub/{data,scaffold,schemas}/`, gitflow skill, `f/specs/canon.py`, `setup.cfg`, `CONTEXT.md` · `blocked by:` T-050-35 · `delivers:` AC4.3, AC4.4 · `RED:` PLAN §2 WP-49, FR-8 · Δ −60/+125.

### C — closure evidence (FR7, FR8, FR9)

- [ ] **T-050-62 — Prune and measure.** Execute the QA-lens pruning verdict (≥ 522 test lines, AC9.9); AC8.1 deltas, allowance subset, mutmut, AC9.11 counts, fenced rubric.
  `W:` tests, handoff · `blocked by:` T-050-23..61 · `delivers:` AC7.1–7.3, AC8.1, AC9.9–9.11 · `RED:` n/a.
