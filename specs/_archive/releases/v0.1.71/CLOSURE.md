# CLOSURE — Release v0.1.71 — Real-consumer TASKS grammar + diagnostic context surface + evidence-doctor

**Release ID:** v0.1.71
**Status:** Aprovado

## Summary

Four bugs the v0.1.68–70 arc marked `resolved` were re-verified STILL OPEN by the operator
on the remote against installed source `574a84bd` (== `main`). Root cause of the miss: the
prior fixes were validated against internal test fixtures and fake harnesses, never against
the real `dd-chain-capture` consumer artifacts. This release fixes each at root cause,
RED-first, with the REAL consumer artifact as the test fixture, and its acceptance gate was
a **before/after replay of the operator's exact reporter commands on the remote**.

| Bug | Fix | Disposition |
|---|---|---|
| `pipeline-write-scope-parser-wrong-grammar` (HIGH) | FR1 — parser now handles the real consumer grammar (bold `**T-x**` headings, fenced `[-] T-x` markers, plain `- Write set:` key, per-path parentheticals via parenthetical-masking) as well as the internal grammar; fixture = real dd-chain-capture v0.2.0 TASKS.md | resolved |
| `lifecycle-status-handoffs-doctor-missing-context` (HIGH) | FR2 — `status` + `handoffs doctor` accept `--context`/`--release-id` as REAL run filters (LifecycleRun carries both); doctor disk scan scoped to matched runs; inverted the two v0.1.69 "must-reject" tests | resolved |
| `context-show-noarg-ignores-bound-session` (MEDIUM) | FR3 — no-arg `context show` resolves to the ALIVE context with a live bound session (newest) before first-ALIVE | resolved |
| `handoffs-doctor-blocks-terminal-promote-to-evidence` (HIGH) | FR4 — `unconsumed_required` exempts `promote_to_evidence` payloads (durable evidence, never consumed); heals pre-existing terminal runs on disk with NO migration | resolved |

## Validations

| Gate | Result | Evidence |
|---|---|---|
| Full test suite | PASS — 5041 passed / 19 skipped / 0 failed | `pytest -p no:cacheprovider` |
| Mutation-sanity | PASS — each fix RED under revert (FR1 real-fixture RED pre-fix; FR4/FR2 doctor revert → RED; delete_after_consumed control still flags) | local |
| Remote before/after replay | PASS — on operator remote vs `574a84bd`: R1 `()`→3 paths; R2 `No such option`→real filter + `ok:true`; R3 `dadaia-workspace`/null→`dd-chain-capture`/session; R4 `unconsumed_required`/blocked→`ok:true` | remote_validate replay |
| ruff format+check / mypy --strict | PASS | pre-push + CI |
| Security | APPROVED (low-surface lifecycle/CLI; no deps/auth; fixture clean) | security-reviewer handoff, keyed to pushed sha |
| CI (full matrix) | GREEN — PR #136 (all checks pass, ubuntu+Windows+macOS) merged `d4dd6d61`; post-merge main green | GitHub Actions |

## Drifts

None. No dependency, schema, auth, or lease-boundary changes. FR4 heals existing on-disk
lifecycle state via read-side semantics (no migration tool, no data rewrite).

## Memory updates

Reinforces the arc post-mortem law in `specs/memory/quality-assurance.md`
(workflow-boundary validation): a fix is not proven until it is replayed against the
**real consumer artifact** on the operator's environment — internal fixtures / fake
harnesses are necessary but not sufficient. This release adds the concrete corrective:
the real dd-chain-capture TASKS.md is now a committed test fixture, and remote before/after
replay is the acceptance gate. No new atom required; consolidated at closure.

## Next

Ship + close. Follow-up (separate): the `dadaia-cli` all-agent CLI-literacy skill
(operator-requested) — a concise, help-discovery-first CLI reference.
