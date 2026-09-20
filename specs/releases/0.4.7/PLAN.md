# PLAN — Release: 0.4.7

**Status:** Aprovado
**Release ID:** 0.4.7
**Owner:** software-engineer

---

## Design (codebase-design vocabulary)

Candidate 5 is a deletion pass: every FR must shrink the touched feature's bug surface and
pass the deletion test (nothing behaves differently, no decision loses its record). The only
additions are replacements smaller than what they replace: one skill script (server registry),
one CI job (security review), six lens checklists (for six personas), one doctor rule (for the
score machinery), two policy templates (for the panel's model UI).

- **Seams kept.** `agent_model_policy.json` (interface, validated by `public doctor`);
  `server_registry.json` (shape unchanged, new owner: `dd-cli-library/scripts/registry.py`);
  the PR head (the security-review check replaces the sha-keyed file at the same seam).
- **Seams removed.** Presence (gate <-> spec_context), governance events (CLI <-> telemetry
  <-> doctor), verdict (chokepoints <-> ci <-> doctor), the nine-persona router.
- **Locality.** Each deleted feature leaves through its own package plus its call sites; no
  cross-feature helper survives it (`_governance_event.py`, `verdict.py`, `presence.py`).
- **Deletion tests.** For every FR a RED test under `tests/tmp/` asserts the module, verb, rule
  or file is gone; they are not committed. The committed proof is the re-measured ratchet and
  the contract tests named per task.

## Order of work (tracer bullets)

1. FR2 first half: move the throttle marker into the reaper, keep presence importing it — green.
2. FR2 second half: delete presence, the zone, the hook, the three verbs; fix the 33 importers.
3. FR1: telemetry + HANDEDIT + governance events, then the panel, then `mistune`; policy JSON
   templates last (the install path must stay green between steps).
4. FR3: skill + script + tests; then delete the CLI group and the feature package.
5. FR5: add the `security-review` job; delete verdict machinery and the two jobs; pre-push wiring.
6. FR6: lenses into `dd-code-review`; delete the six personas; `CORE_AGENTS`, behavior map,
   grants, router; least-privilege render; Fable ban; owner rows.
7. FR4: doctor scores out, `ADR-SUPERSEDED-CITATION` in.
8. FR7: `_ideas/` and the uncited verbs; `docs/cli.md` regenerated.
9. FR8: ratchets, CHANGELOG, memory pass, stage/install/doctor on the live instance, preflight,
   push, review, merge, gate.

## Verification

- `dadaia ci preflight` green after every task; full suite green at closure.
- `tests/contract/test_slop_ratchets.py`, `test_test_suite_ratchets.py`,
  `test_module_size_ceiling.py` re-pinned downward; `test_behavior_map.py`,
  `test_agentic_entities_derivation.py`, `test_every_cited_dadaia_verb_exists`,
  `test_push_gate_wiring.py`, `test_ci_v2_gitflow_pr_gate.py` green with the new shapes.
- Live instance: `public stage` -> `public install --target all` -> `public doctor`
  `[ok] public-privacy` -> `dadaia doctor` with no error-class finding and no score line.
- CI: every job green on the push; `security-review` reports on the PR (D1 satisfied).
