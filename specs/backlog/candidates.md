# Backlog index — PM-curated

> **Reconciled 2026-08-14.** The previous consolidation (2026-07-10) is fully delivered
> and retired to `_archive/` — see History. Every active claim below was re-verified
> against HEAD (`bb78dc40`) on 2026-08-14.

## Pick-precedence notice (DADAIA.md §5)

At release-pick time, open bugs and undispositioned audits **outrank** every fresh
backlog entry in this index. Currently outranking:

- **Audit, undispositioned:** `specs/audits/2026-07-15-consumer-dadaia-integration.md`
- **Audit, undispositioned:** `specs/audits/2026-07-18-architecture-resilience-review.md`
- **Open bug:** `context-alive-sweeps-unrelated-worktree-changes` (MEDIUM, `bugs.jsonl`)

Dispositioning the audits is release work (`product-engineer`, release-definition +
mandatory grill) — this index only makes the precedence visible; it does not
disposition anything.

## Active candidates (3)

| # | Entry | Status | PM priority | Verified at HEAD (2026-08-14) |
|---|---|---|---|---|
| 1 | `whole-tree-denylist-push-scan` | candidate | **P1** | Blind spot confirmed: `check_public_privacy` (`infrastructure/privacy_check.py:184`) scans `public/` only; anchor `push_gate_decision` (`features/chokepoints/service.py:309`) exists. Two identical leak incidents in consecutive releases (v0.6.0, v0.7.0) on record. **Operator decision pending** on scan scope + sanctioned-term exceptions — must be settled in the mandatory grill before SPEC. |
| 2 | `test-suite-remediation-stewardship` | candidate | **P1** | **Unblocked.** Its declared blocker `test-stewardship-standardization` was DELIVERED in v0.7.0 (2026-08-12; entry in `_archive/`). Ready to pick. |
| 3 | `retire-dead-hotfix-surface` | candidate | **P2** | Dead surface confirmed still in tree: `hotfix_app` (`cli/commands/specs.py:26,346`), SPEC-DOC-022/023 hotfix-section checks (`features/specs/doctor_governance.py`), `release_hotfix.md.j2` + `closure_hotfix.md.j2` still shipped. Small, riskless removal. |

Priority rationale (evidence above, not preference): #1 is a recurring privacy-leak
class that today survives only on manual review — the root-cause doctrine owes the
structural fix; #2 became actionable the day v0.7.0 shipped its doctrine; #3 is
confirmed dead-code removal, small and low-risk, no urgency driver.

Known open inconsistency (not resolved here): the SPEC-DOC-022/023 governance checks
still police a `## Hotfixes pendentes` intake section in this file that the v0.6.0 law
revoked — this index intentionally does not carry that section; entry #3 is the queued
removal of those checks.

## Rejected entries (retained per never-delete law)

Both archived 2026-08-14 by `git mv`, terminal `rejected_reason` in frontmatter:

| Entry | Reason | Location |
|---|---|---|
| `20260714-panel-games-pong-codex-v026` | Panel Games surface removed in v0.3.0; PI harness support removed — nothing left to validate | `_archive/` |
| `20260714-snake-wall-wrap-v025-pi-validation` | Same removal — nothing left to validate | `_archive/` |

## History — 2026-07-10 consolidation (fully delivered)

All 5 entries of the previous index shipped and live in `_archive/` with terminal
pointers in frontmatter. None of them is pickable work.

| Entry | Delivered in |
|---|---|
| `20260710-lock-lease-session-identity-kernel` (NO-LOCKS doctrine) | v0.1.76 |
| `20260709-central-bind-resolution-seam` | v0.1.77 |
| `20260710-lifecycle-pipeline-correctness-and-diagnosability` | v0.1.78 |
| `20260708-panel-tab-reorg-agentic-layers` | v0.1.79 |
| `20260710-deprecation-strips-and-doctor-cleanup` | v0.1.81 (date gate operator-waived 2026-07-11) |

The NO-LOCKS DOCTRINE ratified in that cycle is now workspace law (DADAIA.md §3); its
full decision record stays in the archived kernel entry.

## Archive

`_archive/` holds consumed/superseded/rejected entries; each carries its terminal
pointer in frontmatter.
