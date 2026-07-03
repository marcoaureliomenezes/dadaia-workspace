# TASKS — v0.1.53 — Legacy Purge

**Status:** Aprovado

Markers: `[ ]` open · `[-]` in progress · `[x]` done. Shared files (PLAN §Write
sets) are sequential — one owner, no parallel `[-]`.

## W0 — definition

- [x] T-53-01 SPEC/PLAN/TASKS authored from the 2026-07-03 inspection (all targets
  caller-verified; GONE items recorded: academy.js mermaid / kanban CSS /
  drift-check / factory / repos-.dadaia WARN-intent REJECTED-stale; persona regex
  claim stale = no-op; migrate audit = keep both steps); dual definition review REJECT×2 — architect (dead launcher chain caught; rewire seam named w/ golden fixture; agent_tier required-vs-properties sequence; identity+scan agreement test; archival invariants stated) + QA (AC-5 probe generalized — /home/ubuntu leak; per-symbol AC-1; counts 12/3 + two mixed-assertion test files enumerated; AC-8 ledger; chmod seams; import-linter delete+run probe) — ALL folded; `Aprovado`; definition commit. Owner: product-engineer
  (orchestrated).

## W1 — FR1 legacy CLI + package retirement

- [ ] T-53-10 DELETE bug-new chain (command + cli/main.py registration +
  spec_artifacts backing + tests); DELETE `server dashboard` (+tests); RETIRE
  `features/orchestration` (package + `build_orchestration_service`;
  `orchestrate.py list/show` rewired onto `features/workflows` with the same
  output contract — CLI tests updated; `run/status/resume` verbs REMOVED);
  DELETE the two dead exceptions; inline `DEFERRED_WORKFLOWS` into its 2 consumers and DELETE `_deferred.py`; DELETE the dead panel launcher chain (SPEC FR1 enumeration; confirm workflow_state_store orphan status and record). Record the migrate-audit no-deletion result + the AC-8 ledger on this line. Golden fixture for list/show --json captured BEFORE the rewire. NO specs/backlog paths staged. Owner: software-engineer.

## W2 — FR2 dead-code sweep

- [ ] T-53-11 Pre-check: grep projections/public for direct
  `hooks.sdd_gate`/`hooks.root_whitelist` invocations (record result); DELETE the
  two legacy `main()`s; DELETE the `LEASE_TTL_SECONDS` re-export (lease.py internal uses repointed; __all__ entry dropped; 12 test files — kernel_tunables contract assertion deleted, ==120 assertion repointed); relocate `library_workflow_catalog` to `tests/unit/features/lifecycle/_workflow_catalog.py` (3 modules updated, zero production shim); DELETE `views/_assets.py` (verify zero importers); DELETE
  `TelemetryService.list_workflows` + the unreachable handler fallback; check +
  delete the aggregator shared-`dao` mode (v0.1.52 INFO-2); refresh core.js stale comments + the _assets.py comment refs (static.py, assets/__init__.py, tokens.py). AC-8 ledger on this line. NO specs/backlog paths staged. Owner: software-engineer.

## W3 — FR3 canon + config + budgets

- [ ] T-53-12 `RELEASE_SEMVER_RE` + `is_release_semver()` in
  `core/specs_version.py`; three modules import it; agreement/contract test (RED
  commit first: the test must FAIL against the current triplication — it asserts
  zero literal copies outside the canon). AC-7(a) sabotage: plant a literal copy
  ⇒ test FAILS (captured; reverted). Relocate `.import_linter_cache` (config →
  under `.dadaia/tmp/` or disabled; tree clean after a lint run). Re-tune the
  perf test to an op-count/CPU budget. `agent_tier` schema-side removal per the SPEC sequence (required-list drop, properties RETAINED; BOTH renderers lockstep incl. features/specs/catalog.py + render-contract test; catalog.json regen; `dadaia public stage && install --target all && public doctor` exit 0). NO specs/backlog paths staged. Owner:
  software-engineer.

## W4 — FR4 chmod + redaction

- [ ] T-53-13 Route both telemetry chmods through the injected
  `FilePermissionSetter` (PlatformSecurityError → INFO Tier-2 degrade); direct
  `os.chmod` only under `PLATFORM.has_posix_chmod`; unit tests for the
  Windows paths. AC-7(b) sabotage: restore an unguarded direct chmod ⇒ the
  contract test FAILS (captured; reverted). Redact the 12 tracked
  `specs/bugs/**` files (JSONL notes/repro + `_archive` .md via Bash — FROZEN
  class); JSONL lines re-parsed post-edit; record the backstop evaluation
  (redact() already masks — no code change). Owner: software-engineer.

## W5 — gates + ship (flat release: single ship gate)

- [ ] T-53-20 **Consumed-backlog archival at SHIP** (R4 discovery; invariants verified at definition): ONE ATOMIC commit moves all four entries → durable copies + `consumed_backlog.json` under `specs/_archive/v0.1.53/`; backlog doctor clean after; the ONLY push follows this commit. QA review (ship gate): AC-1 greps per deleted name; AC-2 CLI contract;
  AC-3/AC-7 sabotage evidence; AC-5 redaction grep + JSONL parse; AC-6 full
  suite UNPIPED real exit + `public doctor` exit 0. Verdict lands as a review
  commit. Owner: qa-engineer + orchestrator.
- [ ] T-53-21 Security review (push gate — attention: redaction completeness,
  deleted CLI surfaces, hook-entrypoint wiring, public-asset projection
  integrity): APPROVE handoff `metrics.commit_sha` = pushed sha; push; CI green;
  PR; merge. Owner: security-reviewer + orchestrator.

## W6 — closure (CLOSURE phase)

- [ ] T-53-30 CLOSURE.md (Validations + Drifts — SPEC-DOC-006); MEMORY edits:
  strip `agent_tier` from all atoms (+ catalog regenerate + lint),
  `context-management` bug-new legacy lines updated, the deprecation-expiry law
  recorded; archive; ACTIVE → none; candidates R5 row marked shipped —
  **the R1→R5 mandate is complete**. Owner: product-engineer.
