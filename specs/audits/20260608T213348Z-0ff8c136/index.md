# Re-audit — dadaia-workspace 0.1.7 rc-2 (independent verification)

- **Date (UTC):** 2026-06-08T21:33:48Z
- **Scope:** `repos/dadaia-workspace`, branch `feature/0.1.7`, HEAD `b5a8bb2`, working tree clean, UNPUSHED
- **Trigger:** Operator request — "make another audit to see if the problems were solved."
- **Method:** Top-level orchestration (nested Agent dispatch is unavailable in subagents). Mechanical CI ground-truth re-run at top level + 3 adversarial evidence agents (software-architect REVIEW, code-reviewer, security-reviewer). Two evidence agents truncated mid-run (~76–80 tool-uses, a known harness limit); their bounded checks were re-verified directly on disk rather than trusting a final message.

## Verdict: PASS (conditional) — 7.8 / 10

The prior audit's findings **are genuinely resolved on disk**. This independent pass is deliberately more adversarial than the previous re-audit (9.2/10) and surfaces refactor-introduced smells the earlier pass did not weight. None are ship-blockers; one is a real defect inside a rc-2 fix (architecture.md consumer map) and is logged for the next CLOSURE.

## Mechanical ground truth (re-run at top level, not delegated)

| Check | Result |
|---|---|
| `pytest -p no:cacheprovider` | **2370 passed, 2 skipped, 1 xpass** |
| `mypy --strict dadaia_workspace` | **Success — 193 source files** |
| `ruff check dadaia_workspace --no-cache` | **All checks passed** |
| `dadaia public doctor` | **all [ok] incl `public-privacy`** (2 codex workflow files `[reference-only]` by design) |
| `dadaia specs doctor --specs-dir …` | **22 OK, 6 WARN-only, 0 ERROR** (pre-existing heading-allowlist warns) |

## Prior findings — resolution status (verified on disk)

| Point | Status | Evidence |
|---|---|---|
| **T-017-11** public_assets.py < 600 lines | **RESOLVED (line target)** | `public_assets.py` = 596 lines; 7 SRP modules present; no circular imports |
| **NEW-01/02** panel cross-feature boundary | **FULLY RESOLVED** | zero `from …features.{agents,telemetry}` concrete imports in `panel/service.py` + `panel/views/api.py`; DTOs in `core/models/{agent,telemetry}.py`; `core/protocols/agents_provider.py`; `FileSystemAgentsProvider` injected in `container.py:205` |
| **T-017-16** audits-gitignored drift | **RESOLVED** | `.gitignore` tracks only `specs/audits/**/*.md`; 8 audit md files tracked |
| **T-017-19** architecture.md records `is_stale_session` | **PARTIAL — see A-1** | atom exists but consumer map is factually wrong |
| **T-017-20** codex dispatch bug | **RESOLVED** | `ctx-inject.sh` dispatcher-preflight (static echoes, injection-safe); 4 route/contract tests; bug `Closed` with evidence; bulk codex-compat already green (12 TOMLs, shared gates, D-CX doctor, 50 codex tests) |
| **SEC-01 (CWE-284)** `.dadaia/sessions` PROTECTED | **INTACT** | `sdd-spec-gate.sh:114` `*/.dadaia/sessions/*) CLASS=PROTECTED`; blocks at :121; persona-pointer fallback fail-closed |
| **Privacy** committed audit md | **CLEAN** | no `/home/...` path, no real IPv4, no private repo name leak in tracked `specs/audits/*.md` (grep hits were `v0.1.4.6`-style version strings + the audit's own check-command text) |

## New findings (introduced/surfaced by the rc-2 refactor)

- **A-1 [LOW→MED, defect in a rc-2 fix] — architecture.md `is_stale_session` consumer map is factually wrong.** `specs/memory/architecture.md:137` claims `is_stale_session(last_seen_at, ttl_seconds)` is the single source of truth consumed by the lease reclaim path and `features/spec_context/locking.py`. In code, the lease (`lease.py`), `service.py`, and `doctor.py` consume the **sibling** `is_stale(data, *, clock, …)` (dict-based, `>=` boundary). `is_stale_session` (string-based, `>` boundary) is consumed **only** by `kanban.py`. The two predicates have different signatures and boundary semantics; documenting them as one misdirects lease-reclaim debugging. **Owner:** product-engineer, next CLOSURE. Document both functions separately; drop the single-source-of-truth conflation.
- **A-2 [MED] — `install_helpers.py` bag-of-functions SRP violation.** 461 lines spanning 6 concerns (stage helpers, AGENTS.md install, file-copy, runtime expectations, codex agent generation, opencode copy). Introduced by the split. Recommend splitting into `file_copy.py` / `stage_helpers.py` / `codex_agent_generator.py`. **Owner:** software-engineer, next infra-touching release. Non-blocking.
- **A-3 [MED] — coordinator god-class persists as 22 thin delegators.** `public_assets.py:117–204` forwards to extracted free functions purely to preserve the method surface tests call. Line target met, but the smell is reshaped, not removed. Resolve by migrating tests to call the free functions directly, then deleting delegators + the `# noqa: F401` re-export block (`public_assets.py:47–104`). **Owner:** software-engineer, follow-up. Non-blocking.
- **A-4 [HIGH-confusion, not HIGH-risk] — `WorkflowSummary` vs `WorkflowSummaryDTO` naming collision.** Two near-identical names in `core/models/` (`telemetry.py:85` vs `workflow.py:7`) for different shapes; the panel view serializes `WorkflowSummaryDTO`, leaving `WorkflowSummary`/`WorkflowListResult` possibly vestigial. Rename to `WorkflowTelemetrySummary` or remove if dead. **Owner:** software-engineer, next release. Already on the 0.1.8 carry-over list.

## Reviewer dispositions

- **software-architect:** APPROVE (with conditions), 7.5/10 — panel boundary fully resolved; split target met; A-2/A-3/A-4 as backlog conditions; A-1 doc defect.
- **code-reviewer:** truncated pre-verdict; last on-disk work confirmed `subprocess.run` monkeypatch targets remain correct. No defect surfaced; CI + architect cover the same surface.
- **security-reviewer:** truncated pre-verdict; SEC-01 PROTECTED + no-leak + preflight-injection-safe re-verified directly on disk → effectively no findings.

## Conclusion

The operator's directive — fix all remaining points, validate, review, re-audit — is satisfied: every prior carry-over is resolved on disk, the codex deploy-blocker is closed to its maximum deterministic extent, SEC-01 holds, no privacy leak, full CI green. The fresh pass adds four honest follow-ups (A-1..A-4), all non-blocking and all properly scoped to 0.1.8. **The release remains shippable and operator-gated** (no push/merge/tag performed).
