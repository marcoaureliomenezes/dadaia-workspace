# Closure: Release — v0.1.11

> **Status:** Aprovado
> **Release ID:** v0.1.11
> **Owner:** product-engineer
> **Closed:** 2026-06-11

## Summary

v0.1.11 ("Lifecycle Hygiene + Kernel Tail") closes **all 6 open bugs** and burns down the
full ranked residual list (R1–R10) of the v0.1.10 final re-audit. The concurrency kernel
is finished: the last probe-less surfaces (`dadaia lock steal`, `lease._main` acquire)
now honour the pid-liveness no-steal invariant, dead-holder stale leases gained a safe
GC/reclaim path (`LOCK-GC`, probe-gated), bind records are heartbeat-renewed so a live
READ session never silently decays, and `specs doctor` SPEC-DOC-029 stopped calling a
stale lease "forgery" — it now triages dead-stale (WARN + remediation) vs live-incoherent
(ERR) vs coherent.

The lifecycle hygiene loop is closed end-to-end: the release-closure skill carries a
mandatory **disposition sweep** (executed for the first time by this very CLOSURE — bug
B1 eats its own dogfood), and two new doctor invariants (SPEC-DOC-031/032) backstop it.
Validation seams stopped dead-ending honest workflows: ci-preflight runs poetry-free from
the resolved venv, handoffs can reference committed `repos/<slug>/specs/audits/`
artifacts, and the context `repo_url` lifecycle (create `--url`, alive/dead back-fill,
`update --url`, CTX-URL-1) makes contexts portable. The panel Bearer left launch URLs
(single-use ≤60 s launch token), ctx-inject injection shrank 67.9%, the plugin-install
fiction was honestly relabeled, and public-source hygiene (`__pycache__`, repos.xlsx
privacy posture) was settled.

## Tasks completed

Per-task implementation handoffs did not record individual commit SHAs; every task's
diff is contained in the rc-1 ship tree `feature/v0.1.11 @ e1f2de3`
(e1f2de38f99618852a12eb2a18ccd400ea06c5b8, clean tree), verified 7/7 by qa with the
post-review fix `62e8db5` folded. Evidence column = task handoff under
`.dadaia/handoff/dadaia-workspace/` (timestamps abbreviated) or named commit.

| Task ID | Description | Final commit / evidence |
|---------|-------------|--------------------------|
| T-011-00 | Release start: ACTIVE.md → v0.1.11 IMPLEMENTATION | contained in `e1f2de3` |
| T-011-01 | Probe side doors: `lock steal` + `lease._main` (no-steal everywhere) | contained in `e1f2de3` |
| T-011-02 | Stale-lease GC/reclaim (`LOCK-GC`, doctor `--fix`) | `2026-06-11T000000Z-…-T-011-02-doctor-pid-probe` + fix `62e8db5` |
| T-011-03 | SPEC-DOC-029 three-state triage (stale-dead ≠ forgery) | `2026-06-11T022220Z-…-T-011-03` |
| T-011-04 | Bind-record GC: heartbeat-renewed `last_seen_at` (ADR-8) | contained in `e1f2de3` |
| T-011-05 | Session-path ownership: 3 sites → `session_identity` (ADR-12) | contained in `e1f2de3` |
| T-011-06 | ci-preflight runner-derived argv (poetry fallback only) | `2026-06-10T161500Z-…-T-011-06` + symlink fix `774a076` |
| T-011-07 | Handoff resolver: workspace-rooted relative artifact paths | `2026-06-10T161500Z-…-T-011-07` |
| T-011-08 | Context repo_url lifecycle (`--url`, back-fill, `update`, CTX-URL-1) | `2026-06-11T024003Z-…-T-011-08` |
| T-011-09 | Closure skill: mandatory disposition sweep (source) | `2026-06-11T020529Z-…-T-011-09-closure-disposition-sweep` |
| T-011-10 | SPEC-DOC-031 (consumed backlog) + SPEC-DOC-032 (bug status canon) | `2026-06-11T023835Z-…-T-011-10` |
| T-011-11 | Lifecycle-asymmetry map: contract test + map completion | `2026-06-11T020842Z-…-T-011-11-asymmetry-map` |
| T-011-12 | Plugin honest-relabel (rule + 3 stubs) | `2026-06-11T020604Z-…-T-011-12-plugin-honest-relabel` |
| T-011-13 | Panel launch token (Bearer never in a URL) | `2026-06-11T021252Z-…-T-011-13` |
| T-011-14 | ctx-inject tldr-digest + inject-time sentinel GC | `2026-06-10T161500Z-…-T-011-14` |
| T-011-15 | Public-source hygiene: `__pycache__` + repos.xlsx disposition | `2026-06-11T020737Z-…-T-011-15` |
| T-011-16 | R8 code nits: docstring + probe dedup | `2026-06-10T000000Z-…-T-011-16` |
| T-011-17 | R9 venv tooling bumps → explicit DEFER with reason | `2026-06-10T154500Z-…-T-011-17` (see Drifts) |
| T-011-18 | R10 non-memory WARN cleanup (SPEC-DOC-027 legacy allowlist) | `e1f2de3` (alpha-1 delta fix commit) |
| T-011-19 | Reprojection of changed public assets | `dadaia public doctor` exit 0, `[ok] public-privacy` (qa check 6) |
| T-011-20 | Release final gate (battery 1–9) | qa rc-1 handoff `2026-06-11T031509Z-…-v0111-rc1-ship-verification` |
| T-011-21 | Memory truth + token_estimate regeneration + CLOSURE (this file) | this CLOSURE + memory diff |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Full suite green | `pytest -q -p no:cacheprovider` | 2894 passed / 0 failed / 7 skipped (Windows-runner-only) — qa handoff `2026-06-11T031509Z-qa-engineer-v0111-rc1-ship-verification.handoff.json` |
| Format + lint clean | `ruff format --check && ruff check --no-cache` | 507 files formatted; all checks passed (same qa handoff) |
| Strict typing clean | `mypy --strict dadaia_workspace` | 0 issues in 219 files (same qa handoff) |
| Layer contracts kept | `lint-imports` | 5 contracts kept, 0 broken; ignore cap not increased (same qa handoff) |
| SDD structure green | `dadaia specs doctor` | exit 0, 0 errors; SPEC-DOC-027 WARNs 9 → 0 (legacy allowlist); live SPEC-DOC-029 WARNs in other contexts carried GC remediation wording, zero forgery wording — B3 fix observably live (same qa handoff) |
| Projection consistent | `dadaia public doctor` | exit 0, `[ok] public-privacy` (same qa handoff) |
| B2 real-tree proof | `env PATH=/usr/bin:/bin dadaia ci preflight` | 4/4 PASS with poetry absent from PATH (final-gate item 7, same qa handoff) |
| ctx-inject digest reduction | unit test measurement (AC-W4-03) | injected catalog 25659 B → 8238 B (−67.9%) — handoff `2026-06-10T161500Z-software-engineer-T-011-14.handoff.json` |
| rc-1 ship trio | reviewer dispatch | qa **APPROVE** (`…T031509Z-qa-engineer-v0111-rc1-ship-verification`); security **APPROVE**, no CRIT/HIGH, 1 MED tool-venv CVE deferred with operator command (`…-security-reviewer-v0111-rc1-ship`); code-reviewer **REQUEST_CHANGES → fix `62e8db5` → delta APPROVE** (`2026-06-11T012000Z-code-reviewer-v0111-rc1-delta-review`) |
| alpha-1 qa gate | reviewer dispatch | qa REQUEST_CHANGES (T-011-18 missing) → `e1f2de3` → delta APPROVE (`…T025833Z` + `…T030711Z` qa handoffs) |
| token_estimate regeneration (CLOSURE half of AC-W5-03) | `generate-memory-catalog.py` semantics replicated at CLOSURE (see Drifts: `closure-executed-without-shell`) | all atom `token_estimate` values re-synced to `round(words × 1.35)` within the 20% LINT-1 tolerance; `catalog.json` regenerated from frontmatter |

### 6/6 bug → named regression test (final-gate item 8)

| Bug | Named regression test(s) |
|---|---|
| `release-closure-leaves-consumed-backlog-unsanitized` (HIGH, W3) | `tests/unit/features/specs/test_doctor_ledger_invariants.py` — SPEC-DOC-031: `test_nonterminal_backlog_referenced_in_archived_closure_reports_doc_031_warning`, `test_open_backlog_referenced_in_archived_spec_reports_doc_031_warning`, `test_backlog_slug_only_in_backlog_returns_section_is_silent`, `test_terminal_backlog_referenced_in_archived_closure_is_silent`, `test_doc_031_skips_candidates_and_ideas_aggregate_files`; SPEC-DOC-032: `test_bug_with_noncanonical_status_reports_doc_032_warning`, `test_bug_with_rejected_status_reports_doc_032_warning`, `test_doc_032_skips_readme_and_silent_when_bugs_dir_absent`. Skill sweep step projected, guarded by `tests/e2e/features/test_public_pipeline.py` |
| `ci-preflight-checks-hardcode-poetry-run` (MED, W2) | `tests/unit/features/ci_preflight/test_resolve_tool.py` — `test_resolve_tool_prefers_venv_sibling_of_python`, `test_resolve_tool_sibling_of_python_symlink_not_its_target`, `test_resolve_tool_falls_back_to_dadaia_bin_when_no_venv_sibling`, `test_resolve_tool_poetry_fallback_when_missing_everywhere`, `test_resolve_tool_never_calls_shutil_which`, `test_all_five_checks_built_through_resolve_tool`, `test_preflight_works_with_poetry_off_path`; real-tree proof = final-gate item 7 (PASS) |
| `doctor-stale-lease-misdiagnosed-as-forgery` (MED, W1) | `tests/unit/features/spec_context/test_doctor_lock_gc.py` — `test_ttl_expired_dead_pid_reported_and_reclaimed`, `test_ttl_expired_pidless_record_reported_and_reclaimed`, `test_ttl_expired_alive_pid_never_reclaimed`, `test_reclaim_helper_decision_table`; `tests/unit/features/specs/test_doctor_ledger_invariants.py` — `test_stale_dead_holder_lease_reports_doc_029_warning_with_remediation`, `test_stale_pidless_lease_with_fresh_read_bind_warns_not_err` (+ live proof: gate check 5 emitted SPEC-DOC-029 WARN with GC remediation, zero forgery wording) |
| `handoff-artifact-path-cannot-reference-specs-audits` (MED, W2) | `tests/unit/features/reports_validation/test_resolve_artifact_path.py` — `test_resolve_repos_specs_audits_artifact_validates`, `test_resolve_legacy_handoff_dir_relative_still_validates`, `test_workspace_root_wins_when_path_resolvable_both_ways`, `test_absolute_path_outside_workspace_rejected`, `test_dotdot_escape_path_rejected` |
| `plugin-install-command-missing` (MED, W4) | `tests/contract/test_plugin_install_residue.py` — `test_no_plugin_install_references_under_public` (honest-relabel per ADR-4: no public asset advertises the nonexistent command) |
| `context-repo-url-not-settable-or-repairable` (MED, W2) | `tests/unit/features/spec_context/test_service_repo_url.py` — `test_create_persists_explicit_repo_url`, `test_create_persists_empty_url_when_unknown`, `test_update_url_repairs_through_store`, `test_update_url_preserves_state_and_branch`, `test_update_url_missing_context_raises`, `test_alive_backfills_repo_url_from_origin_remote`, `test_dead_backfills_repo_url_before_rmtree`; `tests/integration/test_cli_context_repo_url.py` — `test_create_url_persists_and_overrides_catalog`, `test_update_url_repairs_empty_record`, `test_update_url_unknown_context_exits_1`, `test_doctor_flags_alive_empty_repo_url`, `test_context_repo_url_export_import_clone_regression` |

## Drifts

### venv-symlink-escape-in-resolve-tool

**Description:** During T-011-06, the first `_resolve_tool` cut resolved the venv-sibling
directory through the symlink **target** of `sys.executable`, escaping the venv to the
base interpreter's bin dir on symlinked venvs.

**Resolution:** Fixed in commit `774a076`: the sibling is resolved from the symlink
itself, pinned by `test_resolve_tool_sibling_of_python_symlink_not_its_target`.

**Memory updates:** none — implementation detail below memory granularity.

### container-pid-probe-dead-on-arrival

**Description:** rc-1 code review caught a HIGH: `container.build_doctor_service`
constructed `DoctorService` without `pid_probe`, so `dadaia doctor --fix` LOCK-GC ran
TTL-only and would have reclaimed a TTL-expired lease whose holder pid was still alive —
violating the very no-steal invariant this release finishes.

**Resolution:** Fixed in commit `62e8db5`: `container._build_pid_probe()` (lazy import of
the hook-layer builder) wires the probe at the composition root; code-reviewer delta
APPROVE. A follow-up backlog return (the probe-seam consolidation entry, see `## Backlog returns`) consolidates the now
4 import sites of `hooks.sdd_gate._build_pid_probe`.

**Memory updates:** `specs/memory/product/platform/workspace-doctor.md` (LOCK-GC described
as probe-gated).

### alpha-1-t-011-18-gap

**Description:** The alpha-1 qa review returned REQUEST_CHANGES because T-011-18
(SPEC-DOC-027 legacy allowlist) was not yet landed when the wave was presented.

**Resolution:** Delivered in commit `e1f2de3`; qa delta re-review APPROVE. SPEC-DOC-027
WARNs went 9 → 0.

**Memory updates:** `specs/memory/product/sdd/specs-doctor.md` (027 allowlist).

### stray-repo-level-dadaia-dir

**Description:** A subagent created a `.dadaia/` directory **inside** the repo working
tree during implementation — a hard violation of the repo-cleanliness law (`.dadaia/` is
workspace-level only; it corrupts workspace-vs-repo boundary detection).

**Resolution:** Contents relocated to the workspace-level `.dadaia/`; the stray dir
removed; tmp-file-guardrail discipline re-stated to implementers in the coordination
thread. No production impact.

**Memory updates:** none — governed by existing rules (tmp-file-guardrail), no product
truth changed.

### r9-tool-venv-cve-bumps-deferred

**Description:** R9 (opportunistic `pip`/`poetry`/`dulwich` bumps) could not be applied
in-lock: the CVEs are out-of-runtime (tool-venv only) and poetry is broken in the live
environment, so a lock regen was not safely executable this cycle.

**Resolution:** Explicit DEFER with reason recorded in a `pyproject.toml` comment
(T-011-17) and accepted by security review (1 MED deferred, no CRIT/HIGH). Operator
remediation command: `.dadaia/.venv/bin/pip install --upgrade 'pip>=25.3' 'poetry>=2.3.4' 'dulwich>=1.2.5'`.

**Memory updates:** `specs/memory/tech-stack.md` — no change (no pin changed).

### panel-core-js-legacy-token-bootstrap

**Description:** T-011-13 removed the Bearer from every URL server-side, but the browser
asset `features/panel/views/assets/js/core.js` still carries the legacy
`?token=`/localStorage bootstrap — now dead code for auth (the launch URL carries only
the launch token; the Bearer travels in the HttpOnly session cookie). Browser JS is
frontend-engineer (plugin) scope, so the implementer correctly did not edit it.

**Resolution:** The binding AC-W4-02 e2e contract passes without core.js changes. The
cookie-migration follow-up is recorded inside the plugin-packs backlog return (see `## Backlog returns`)
backlog return (frontend work requires the plugin pack to be routable at all).

**Memory updates:** none — panel atom auth posture unchanged at the contract level.

### closure-executed-without-shell

**Description:** This CLOSURE was executed by product-engineer dispatched without a shell
tool, so three mechanical steps could not be run in-session: (1) the
`generate-memory-catalog.py` script run, (2) `dadaia specs doctor` re-verification, and
(3) the `git mv` archive move.

**Resolution:** (1) The script's exact semantics (frontmatter-sourced catalog;
`token_estimate = round(body_words × 1.35)`, LINT-1 tolerance 20%) were replicated
manually: drifted atom frontmatter values updated and `catalog.json` regenerated by hand,
word counts measured mechanically per atom. (2)+(3) handed to the release coordinator as
the verbatim commands listed under "Archive decision"; doctor must report exit 0 and zero
`token_estimate` WARNs after the archive move.

**Memory updates:** `specs/memory/product/catalog.json` + atom frontmatter
`token_estimate` values.

## Memory updates

- `specs/memory/architecture.md` — incumbent-pointer mode-resolution parenthetical gains
  the liveness qualifier (DRIFT-M3); GC model now states probe-gated `LOCK-GC` (dead or
  unprobeable holder only; live-pid never reclaimed), heartbeat-renewed bind-record TTL GC
  (`last_seen_at`), and probe-gated `lock steal`.
- `specs/memory/product/sdd/sdd-gate-v3.md` — one-sentence `getppid` shell-wrapper caveat
  on holder-pid resolution (R8).
- `specs/memory/product/sdd/specs-doctor.md` — SPEC-DOC-029 three-state triage; new
  SPEC-DOC-031/032 disposition invariants; SPEC-DOC-027 legacy allowlist; cross-reference
  to workspace-doctor for runtime GC codes.
- `specs/memory/product/platform/context-management.md` — repo_url lifecycle
  (`create --url`, alive/dead back-fill via git-ops port, `context update --url`,
  CTX-URL-1); probe-gated `lock steal`; bind-record GC vs heartbeat-renewed
  `last_seen_at`.
- `specs/memory/product/platform/workspace-doctor.md` — LOCK-GC and CTX-URL-1 invariants
  added (truth home for workspace-doctor codes; complements the SPEC's affected list).
- `specs/memory/product/agents/agent-comms.md` — workspace-rooted relative
  `artifact.path` resolution (covers `repos/<slug>/specs/audits/…`; workspace-root wins
  over the legacy handoff-dir fallback).
- `specs/memory/product/catalog.json` — regenerated from frontmatter (token_estimate
  sync, AC-W5-03 CLOSURE half).
- `specs/memory/tech-stack.md` — no change: no runtime or dev pin changed (R9 deferred).
- `specs/memory/product/philosophy/repos-catalog.md` — no change: repos.xlsx confirmed
  generic sample content (T-011-15); consumer already documented.
- `specs/constitution.md` — no change needed.

## Dispositions

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/bugs/release-closure-leaves-consumed-backlog-unsanitized.md` | bug | `Closed` | SPEC-DOC-031/032 named tests + skill sweep (this `## Dispositions` section is the first live execution); tree `e1f2de3` |
| `specs/bugs/ci-preflight-checks-hardcode-poetry-run.md` | bug | `Closed` | `test_resolve_tool.py` named tests + final-gate item 7 real-tree proof; tree `e1f2de3` |
| `specs/bugs/doctor-stale-lease-misdiagnosed-as-forgery.md` | bug | `Closed` | `test_doctor_lock_gc.py` + `test_stale_pidless_lease_with_fresh_read_bind_warns_not_err`; tree `e1f2de3` |
| `specs/bugs/handoff-artifact-path-cannot-reference-specs-audits.md` | bug | `Closed` | `test_resolve_artifact_path.py` named tests; tree `e1f2de3` |
| `specs/bugs/plugin-install-command-missing.md` | bug | `Closed` | `test_plugin_install_residue.py` (honest-relabel, ADR-4) + the plugin-packs backlog return (see `## Backlog returns`); tree `e1f2de3` |
| `specs/bugs/context-repo-url-not-settable-or-repairable.md` | bug | `Closed` | `test_service_repo_url.py` + `test_cli_context_repo_url.py` named tests; tree `e1f2de3` |
| `specs/bugs/handoff-artifact-path-resolver-ignores-workspace-root-contract.md` | bug | `Closed` (duplicate, pre-dispositioned) | `superseded_by: handoff-artifact-path-cannot-reference-specs-audits` in its frontmatter; fix evidence identical to B4 row |
| `specs/backlog/v0.1.11-audit-residuals.md` | backlog | `DELIVERED — v0.1.11` | R1–R10 mapped in SPEC "Residual inventory"; R9 DEFERRED to operator command (see Drifts); R10 escape-record axis out of scope per ADR-3 (time-earned) |
| `specs/backlog/candidates.md` § BACKLOG-V0111-AUDIT-RESIDUALS | backlog (index row) | `DELIVERED — v0.1.11` | row updated in place, points here |

## Backlog returns

- `specs/backlog/plugin-packs-and-install-command.md` ← ADR-4 honest-relabel return:
  design + distribute real plugin packs (frontend-design, devops) and a real
  `dadaia plugin install` command; includes the panel core.js cookie-migration follow-up.
- `specs/backlog/pid-probe-seam-consolidation.md` ← code-review LOW-2: promote
  `hooks.sdd_gate._build_pid_probe` (4 import sites) to a single public composition-root
  builder; target v0.1.12.

## Archive decision

**MOVE** — release directory moves to `specs/_archive/releases/v0.1.11/` (v0.1.10
precedent: archive at CLOSURE; the operator holds the branch merge of PR-stacked
`feature/v0.1.11`). Executed by the release coordinator (PE dispatched shell-less):

```bash
cd /home/marco/workspace/dadaia/repos/dadaia-workspace
git mv specs/releases/v0.1.11 specs/_archive/releases/v0.1.11
DADAIA_CONTEXT=dadaia-workspace dadaia specs doctor --specs-dir $(pwd)/specs   # must exit 0, zero token_estimate WARNs
```

`ACTIVE.md` is set to `release: none / phase: none`.
