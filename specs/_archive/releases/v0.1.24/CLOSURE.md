# Closure: Release — v0.1.24

> **Status:** Aprovado
> **Release ID:** v0.1.24
> **Owner:** product-engineer
> **Closed:** 2026-06-26

## Summary

v0.1.24 makes the operator's two-layer agentic model real. **Layer 1** (entry harnesses
the operator launches in the terminal) is exactly `{claude, codex, pi}` — **OpenCode is
deleted entirely**, both layers, full footprint. **Layer 2** (the `dadaia lifecycle`
workflow engine that drives bounded workers behind `AgentRuntimePort`) now enforces two
laws: **LAW 1** — workflow workers are `{pi, codex, fake}` only (Claude SDK is kept in
code and unit-tested but is no longer a selectable Layer-2 `--harness`, so running Claude
as a Layer-2 worker can never spend credits outside the operator's subscription); and
**LAW 2** — a discrete per-harness GPT model catalog selectable on the CLI (`--harness` +
`--model`, `--step-harness` + `--step-model`): pi → 3 models, codex → 2 models, no
`claude-*` id ever selectable at Layer 2.

On top of the reduced, law-bound harness set, the release introduces a library-owned
**prompt-fragment system** (`public/lifecycle_fragments/`) consumed by Python
"dadaia-workflows", a **dynamic context selector** with explicit max-context policies, and
migrates the **release-definition workflow end-to-end onto fragments + Python-validated
gates** as the first proof — the model recommends, Python decides transition legality.
Every dadaia-workflow is now **fully self-describing in the panel** (purpose, ordered
steps, per-step harness/model options, mermaid, availability), and each lifecycle run
record persists its **prompt composition** for observability. The broad
rule/skill/persona dehydration and the remaining workflow bodies are explicitly and
honestly staged into a follow-up release (§3.12 of the SPEC); v0.1.24 ships the operator's
stated floor as a coherent, testable increment.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-24-01 | Remove `AgentRuntimeKind.OPENCODE_RUN` + mypy-guided consumer purge (WS-1) | `6e89a97` |
| T-24-02 | Delete OpenCode files/tests/academy + conftest/CI refs (WS-1) | `6e89a97` |
| T-24-03 | Purge OpenCode from docs + reproject (WS-1) | `6e89a97` |
| T-24-04 | Discrete per-harness model catalog (WS-2, LAW 2) | `6e89a97` |
| T-24-05 | Thread discrete model through `build_agent_runtime` + PI + Codex (WS-2) | `6e89a97` |
| T-24-06 | CLI `--model`/`--step-model` + Layer-2 harness `{pi,codex,fake}`; reject claude (WS-2, LAW 1) | `6e89a97` |
| T-24-07 | Fragment library + loader + metadata + harness-universal checks (WS-3) | `cba8c22` |
| T-24-08 | Dynamic context selector + max-context policies + run-record audit (WS-4) | `cba8c22` |
| T-24-09 | Release-definition workflow body on fragments + gates (WS-5) | `cba8c22` |
| T-24-10 | Release-definition workflow e2e (FAKE) + adjacent-harness seam (WS-5) | `cba8c22` |
| T-24-11 | Fragment suffix for implementation + one review step; scaffold deferred workflows (WS-6) | `cba8c22` |
| T-24-12 | Panel workflow catalog: purpose + per-step harness/model + availability + mermaid (WS-8) | `cba8c22` |
| T-24-13 | Prompt observability: run-record fields + view + prefix byte-identity (WS-9) | `cba8c22` |
| T-24-14 | AI-surface dehydration: AGENTS.md pointers + AI-surface doctor check (WS-7) | `7ab6634` |
| T-24-15 | Mark v0.1.23 superseded; carry-forward note (WS-11 prep, ADR-F) | `7ab6634` |
| T-24-16 | Operator live-validation acceptance gate (WS-10) — operator-directed closure | (this closure commit) |
| T-24-17 | CLOSURE: write CLOSURE.md + update memory atoms (WS-11) | (this closure commit) |
| T-24-18 | Archive release + advance ACTIVE.md (WS-11) | (this closure commit) |

Segment mapping: T-24-01..06 = `alpha-1` (`6e89a97`); T-24-07..13 = `alpha-2` (`cba8c22`);
T-24-14..15 + qa-fixes = `rc-1` (`7ab6634`); T-24-16..18 = the pending closure commit.

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Type check clean (strict) | `mypy --strict` | `0` errors across 258 files |
| Full test suite green | `pytest` | `3472 passed, 14 skipped, 0 failed` |
| Lint + format clean | `ruff check . && ruff format --check .` | clean (exit 0) |
| Projection consistent + privacy + AI-surface | `dadaia public doctor` | exit 0; `[ok] public-privacy` + `[ok] ai-surface` |
| No OpenCode in live code/docs/academy | `grep -ri opencode dadaia_workspace/ tests/` | only historical mentions in `_archive`/CLOSURE; none in live code |
| Unknown target rejected | `dadaia public install --target opencode` | errors with unknown-target message |
| QA review | qa-engineer handoff | verdict **APPROVED-WITH-FINDINGS** — findings folded into rc-1 (`7ab6634`) |
| Security review (push-gate artifact) | security-reviewer handoff under `.dadaia/handoff/dadaia-workspace/` | referenced as the pre-push security-verdict artifact; **a maintainer confirms its verdict at push** (the pre-push chokepoint keys on `metrics.commit_sha`) |
| `--harness claude` rejected (LAW 1) | `dadaia lifecycle release define --harness claude ...` | maintainer-verified: rejected with LAW-1 / Layer-1 pointer message |
| Invalid `(harness, model)` rejected | `... --harness pi --model <bad>` | maintainer-verified: rejected, listing the harness's valid GPT catalog |
| `.opencode/` + `opencode.json` blocked at root | root-whitelist hook | maintainer-verified: blocked (stale root exception removed) |
| Panel workflow catalog live | `GET /api/dadaia-workflows` | maintainer-verified: release_definition=available, implementation=partial, 4 deferred; purpose + per-step pi/codex harness + GPT model_options + mermaid shown |

### WS-10 disposition (operator-directed)

The operator **directed closure** rather than performing the personal live-run sign-off.
Recorded honestly (no live pi/codex run is claimed to have passed):

- **Verified deterministically by the maintainer:** `--harness claude` rejection (LAW 1);
  invalid `(harness, model)` rejection with the GPT catalog listed; `.opencode/` +
  `opencode.json` blocked at root; the panel catalog live (`/api/dadaia-workflows` showing
  availability + per-step harness/model + mermaid + purpose).
- **Deferred to real use:** the `--harness pi` and `--harness codex` end-to-end live
  worker runs (WS-10 items 1 & 2) were **NOT** executed against real workers. The FAKE
  e2e (`tests/integration/cli/test_release_definition_workflow.py`) plus the unit tests
  prove the seam (adjacent-harness mixing, scoped fragment prompts, typed gates); live
  confirmation against real PI/Codex workers is explicitly deferred. Mocked tests cannot
  prove the upstream PI/Codex CLI contracts; that is left to first real use.

## Drifts

### root-whitelist-nested-gap

**Description:** During the `.opencode/`-block verification (WS-10), the maintainer found
that the root-whitelist policy classifies new **top-level** root entries but misses some
**nested** new-top-level writes. This is a pre-existing gate gap surfaced (not caused) by
this release's removal of the `.opencode/` root exception.

**Resolution:** Filed as bug `specs/bugs/root-whitelist-misses-nested-new-toplevel-writes.md`
(ADDITIVE; never blocks). The `.opencode/` + `opencode.json` root block was confirmed
working for the cases this release cares about; the broader nested gap is tracked as a
separate fix, not folded into v0.1.24.

**Memory updates:** none required — the gap does not change the current documented
gate contract; it is a tracked defect.

### lease-self-block

**Description:** During implementation a session that legitimately held the context's
MUTATING lease was observed being self-blocked by the gate on its own session.

**Resolution:** Filed as bug `specs/bugs/gate-self-blocks-lease-holder-own-session.md`
(ADDITIVE). Not in scope for v0.1.24; tracked for a follow-up gate fix.

**Memory updates:** none — the lease/gate contract in `architecture.md` already describes
the intended holder-safe behavior; this is a defect against that contract, tracked as a bug.

### live-validation-deferred

**Description:** The SPEC's WS-10 declared an operator personal live-run gate. The operator
instead directed closure with live pi/codex runs deferred.

**Resolution:** Recorded honestly in T-24-16 and in the WS-10 disposition above. The
deterministic acceptance items were maintainer-verified; the live worker runs are deferred
to real use. No live run is claimed to have passed.

**Memory updates:** the memory atoms describe the **mechanics** (the seam, the catalog, the
gates) which are tested, not a claim of live-validated worker behavior.

## Memory updates

- `specs/memory/architecture.md` — updated the two-layer model: harness set now
  `{claude, codex, pi}` (OpenCode removed from the entry set and from the asset projection
  chain); Layer-2 `AgentRuntimeKind` set reduced to `{FAKE, CODEX_EXEC, CLAUDE_SDK,
  PI_HEADLESS}` with LAW 1 stated (Layer-2 workflow workers = pi/codex/fake; CLAUDE_SDK
  kept-importable but not a selectable workflow harness); added the dadaia-workflows +
  prompt-fragment library + dynamic context selector + Python gates; added the discrete
  per-harness GPT model catalog (LAW 2). Removed `.opencode/` from the projection chain
  diagram and the rule listing.
- `specs/memory/tech-stack.md` — dropped OpenCode from supported harnesses/runtimes; noted
  Layer-2 workers = pi/codex (+ fake); recorded that the discrete Layer-2 model catalog is
  GPT-only (PI runs on the operator's Codex subscription); CLI versions left as TODO
  (verified versions not captured this cycle — not invented).
- `specs/memory/product/platform/multi-platform-parity.md` — removed OpenCode from the
  entry-harness projection parity; Layer-1 set = `{claude, codex, pi}`; Layer-2 worker set
  = `{FAKE, CODEX_EXEC, CLAUDE_SDK, PI_HEADLESS}` with the LAW-1 workflow-selectability
  note; dropped the OpenCode projection paragraph + the `OPENCODE_RUN` worker mention.
- `specs/memory/product/sdd/lifecycle-foundation.md` — removed `OPENCODE_RUN` from the
  `AgentRuntimeKind` enum and the factory; stated the Layer-2 workflow harness choices are
  `{pi, codex, fake}` (LAW 1) with discrete `(harness, model)` selection (LAW 2); replaced
  the model-tier note with the discrete-catalog reality; described the fragment-driven
  release-definition workflow + the prompt observability run-record fields; removed the
  deferred-OpenCode-adapter limit.

## Dispositions

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/backlog/lifecycle-prompt-fragments-ai-surface-dehydration.md` | backlog (epic) | `DELIVERED-IN-PART — v0.1.24` | this CLOSURE (Summary + §3.12 of SPEC) |
| `specs/bugs/gate-self-blocks-lease-holder-own-session.md` | bug | `Open` (filed this cycle; out of scope) | `## Drifts → lease-self-block` |
| `specs/bugs/root-whitelist-misses-nested-new-toplevel-writes.md` | bug | `Open` (filed this cycle; out of scope) | `## Drifts → root-whitelist-nested-gap` |

The epic backlog item is marked **delivered-in-part**: the release-definition workflow +
the fragment engine shipped; **deferred to a follow-up release** are deep AI-surface
dehydration, the backlog/audit/research/bug_report workflow bodies (scaffolded + fail-loud
only), and ctx-inject reduction. The two bugs filed this cycle are genuine, out-of-scope
defects left `Open` for a follow-up (never silently dropped, never picked into v0.1.24).

v0.1.23 disposition carried forward (ADR-F): v0.1.23 is `superseded_by: v0.1.24` (already
marked in its SPEC frontmatter, T-24-15); v0.1.23 was never deployed and must not be
closed/deployed independently — v0.1.24 carries its surviving acceptance forward and is the
shipping release.

## Backlog returns

- `backlog/candidates.md` ← (none new — the deferred scope stays tracked under the existing
  epic `lifecycle-prompt-fragments-ai-surface-dehydration`, marked delivered-in-part).

## Archive decision

**MOVE** — the release directory is ready to be moved to
`specs/_archive/releases/v0.1.24/` via `git mv` (delegated to a maintainer/devops). After
the move, ACTIVE.md is advanced (phase `ARCHIVED`, then pointed at the next release or
`release: none`). A maintainer runs `dadaia specs doctor` (must be green) before archiving.
