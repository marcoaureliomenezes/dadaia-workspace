# CLOSURE — Release v0.1.72 — Gate coherence: repair paths + preflight enforcement

**Release ID:** v0.1.72
**Status:** Aprovado

## Summary

Round-3 remediation: six bugs reported from the operator's remote against `c33a07aa`,
all in/around the v0.1.69 preflight subsystem. Root architectural failure, now
corrected: **gates shipped without repair paths, and an advisory gate the guarded verbs
never enforced** — probes validated on clean fixtures deadlocked a lived-in consumer
workspace (sample-consumer v0.2.0) completely.

| Bug | Fix | Disposition |
|---|---|---|
| `memory-agent-tier-migration-deadlock` (CRITICAL) | FR1 — `agent-tier-frontmatter` migration step (v2→3): the missing v0.1.61 schema-drop migration; real consumer tree heals v1→3, doctor clean | resolved |
| `rebind-does-not-adopt-same-process-lease` (HIGH) | FR2 — pid-lineage discrimination: `lease.holder_in_lineage` + `adopt_if_own_lineage` (bind adopts eagerly); preflight probe aligned with acquire's rung-1 `.ptr` canon | resolved |
| `hygiene-preflight-blocks-protected-residuals` (HIGH) | FR3 — `_check_hygiene` blocks only on the UNPROTECTED remainder | resolved |
| `context-current-branch-stale-for-alive-repo` (MEDIUM) | FR4 — live `current_branch` for ALIVE repos + `stored_branch` restore metadata | resolved |
| `fake-pipeline-blocks-missing-artifact-evidence` (HIGH) | FR5 — seam-preserving driving fake for the pipeline verb (parity with implement-review); the v0.1.68 E2E that ASSERTED the blocked outcome inverted | resolved |
| `workflow-verbs-run-despite-blocked-preflight` (HIGH) | FR6 — pipeline + implement-review enforce the preflight gate before creating a run; `--skip-preflight` explicit visible override; stale `--write-scope` help corrected | resolved |

New bug found during validation and registered (open, routed to next release):
`specs-upgrade-backup-trips-preflight-dirty-gate` — the upgrade's own `specs_bkp/`
byproduct re-trips the dirty-tree gate it repairs.

## Validations

| Gate | Result | Evidence |
|---|---|---|
| Full test suite | PASS — 5060 passed / 19 skipped / 0 failed | `pytest -p no:cacheprovider` |
| Mutation-sanity | PASS 4/4 — service.py/container.py/lease.py/registry reverts each RED their targeted tests; FR5/FR6 proven RED-first via the inverted E2E + Drive 0 | local |
| Remote full-chain replay (live sample-consumer v0.2.0) | PASS — upgrade v1→3 heals 8 atoms + doctor clean; adoption sandbox on-box (`adopted: True`, `live_foreign_holder: False`); pipeline WITHOUT skip REFUSES (honest reason, no run created); pipeline `--skip-preflight --harness fake` completes to closure; `context show` live branch `feature/v0.1.1` vs stored `main` | replay transcript |
| ruff format+check / mypy --strict | PASS | pre-push + CI |
| Security | APPROVED, keyed to pushed sha | security-reviewer handoff |
| CI (full matrix) | GREEN — PR #139 merged `6b517d79`; post-merge main green | GitHub Actions |

## Drifts

- The v0.1.68 "marquee" pipeline E2E asserted the fake pipeline's BLOCKED outcome —
  codifying the bug as expected behavior. Inverted; the smoke path must COMPLETE.
- Two v0.1.64 tests codified the plain-fake blocking contract; updated to the new
  contract (scripted no-evidence fake proves the engine gate; plain fake completes).
- 14 pipeline/implement-review CLI tests gained `--skip-preflight` (they test post-gate
  mechanics; the gate has its own executed-path tests).
- Doctor golden regenerated for the deliberate canonical-version bump (2→3).

## Memory updates

`specs/memory/quality-assurance.md` at closure: gate-coherence law — (1) a schema-drop
MUST ship its migration; (2) a gate must never demand an action its own tooling refuses
(protected evidence) or forbids (phase-locked memory) — every gate ships its repair
path; (3) the gate a diagnostic reports is the gate the verbs enforce (advisory gates
are theater); (4) probes must be validated against a LIVED-IN workspace (old atoms,
real lease lineage, accumulated evidence), not only clean fixtures.

## Operator runbook (sample-consumer, after upgrading dadaia-workspace)

1. Inside the Codex session: commit the migrated `specs/memory/` (already healed on the
   remote by this validation) and remove/relocate `specs_bkp/`.
2. `dadaia context bind sample-consumer --mode implementation --release v0.2.0` — the
   same-process lease adopts automatically.
3. `dadaia lifecycle preflight --context sample-consumer --release-id v0.2.0 --json` —
   passes (doctor clean, lease adopted, protected evidence exempt, tree clean).
4. Proceed with the v0.2.0 workflow verbs; a blocked preflight now refuses them with the
   actionable reason instead of running unsafely.

## Next

Ship + close. Open ledger: `stray-dadaia-tmp-inside-repo` (pre-existing),
`specs-upgrade-backup-trips-preflight-dirty-gate` (found during this validation).
