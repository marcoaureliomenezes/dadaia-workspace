---
release: none
phase: none
---

# Active release: none

**v0.1.71 SHIPPED + CLOSED (PR #136 `d4dd6d61`).** Four bugs the v0.1.68–70 arc marked
resolved were re-verified STILL OPEN on the operator's remote against installed
`574a84bd` — fixed at root cause, RED-first, with the REAL dd-chain-capture consumer
artifact as fixture, and proven by a before/after replay on the operator's remote:
- FR1 write-scope parser handles the real consumer TASKS.md grammar (was `()`)
- FR2 `lifecycle status`/`handoffs doctor` accept `--context`/`--release-id` (real filters)
- FR3 no-arg `context show` reflects a bare bind
- FR4 `handoffs doctor` exempts `promote_to_evidence` (heals stale terminal runs, no migration)

Bug ledger: 1 open (`stray-dadaia-tmp-inside-repo`, pre-existing side-bug). Memory:
`quality-assurance.md` — real-consumer-artifact + remote-replay corrective added to the
workflow-boundary law. Follow-up (separate): `dadaia-cli` all-agent CLI-literacy skill.
