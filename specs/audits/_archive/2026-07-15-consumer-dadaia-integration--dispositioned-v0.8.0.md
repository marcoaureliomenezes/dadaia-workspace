---
title: Consumer and dadaia-workspace integration audit
date: 2026-07-15
status: dispositioned
original_status: remediation-required
target_release: v0.2.5
disposing_release: v0.8.0
disposition_date: 2026-08-14
---

# Consumer and dadaia-workspace integration audit

> **Disposition:** v0.8.0 — all 12 findings dispositioned; see
> **[Disposition — release v0.8.0](#disposition--release-v080)** at the end of this file.
> Everything between this line and that section is the original 2026-07-15 record,
> unaltered.

## Verdict

The assembled Consumer consumer journey is not release-safe even though the
provider's isolated test suites are substantial. The failures are systemic:
provider and consumer surfaces have no versioned compatibility contract,
upgrades can leave the wheel, state, projections, prompt, and specs schema at
different versions, and the consumer starts fresh root-level Codex executions
without deterministically injecting the selected Spec Context.

Release `v0.2.5` is the mandatory remediation release. Every finding below is
in scope and must be closed with automated evidence before closure.

## Findings and required dispositions

| Severity | Finding | Required disposition in v0.2.5 |
|---|---|---|
| CRITICAL | No versioned provider-consumer compatibility contract exists. | Publish a machine-readable capability contract and enforce it from Consumer and provider tests. |
| HIGH | Consumer upgrades only the persistent wheel. | Add transactional, exact-version reconciliation of package, state, public projections, doctors, and rollback behavior. |
| HIGH | Consumer prompt and tests preserve removed lifecycle commands. | Consume the installed version-matched skill/capability surface and test canonical workflow verbs. |
| HIGH | Fresh root-level `codex exec` tasks miss target-repository context. | Resolve an explicit context and inject its scoped rules, memory, active release, and current task into every run. |
| HIGH | Existing E2E does not certify the assembled consumer journey. | Add deterministic contract tests, persistent-upgrade E2E, empty-remote E2E, panel/doctor/scaffold/workflow certification, and a bounded live canary. |
| HIGH | The Consumer owning repository is governance-incoherent. | Restore one-task-at-a-time markers, valid memory/schema state, and immutable release evidence before certification. |
| MEDIUM | `context list --json` is documented but unsupported. | Implement and test stable JSON output. |
| MEDIUM | `context heartbeat` ignores the persisted bind. | Resolve caller-owned session identity without requiring a manually exported environment variable. |
| MEDIUM | Unbound context resolution selects the first ALIVE context. | Remove foreign-context fallback and fail with an actionable explicit-selection error. |
| MEDIUM | Empty repository onboarding has no explicit baseline contract. | Add operator-consented baseline initialization and an unborn-remote journey test. |
| MEDIUM | Telegram delivery truncates diagnostic output. | Deliver bounded chunks or persist and link the complete result without losing the failure cause. |
| MEDIUM | Academy notes are mistaken for executable agent knowledge. | Package versioned operational knowledge as an installed skill and keep Academy as evidence only. |

## Acceptance boundary

The release is not complete until a clean disposable workspace proves all
public feature families through supported interfaces: initialization,
Spec Context create/alive/dead/bind/heartbeat/list, scaffold and specs doctors,
public projections, all four lifecycle workflows, reports/handoffs, server
registry and panel smoke, capability discovery, upgrade reconciliation, and the
Consumer consumer bootstrap/task path.

Mocks may cover failure injection, but they cannot be the only evidence for
the assembled journey. Closure requires clean-room tests against built
artifacts and a bounded real-worker canary for every supported harness that is
available in CI or the release environment.

---

## Disposition — release v0.8.0

**Disposing release:** v0.8.0 (`specs/_archive/releases/v0.8.0/`) — audit-disposition
release of the 2026-08-14 grill.
**Dispositioned:** 2026-08-14 · **Author:** product-engineer.
**Basis:** operator grill of 2026-08-14, ADR #1
(`.dadaia/reports/dadaia-workspace/product-engineer/2026-08-14T130830Z-refine-specs.html`),
over the finding-by-finding verification of
`.dadaia/reports/dadaia-workspace/product-engineer/2026-08-14T041500Z-deep-triage.html`
against HEAD `8a8f4f80`.

**Why the named remediation release did not close this audit.** `v0.2.5` shipped and is
archived, but its CLOSURE carries no finding-by-finding disposition of this audit (grep
`2026-07-15` / `consumer-dadaia-integration` in
`specs/_archive/releases/v0.2.5/CLOSURE.md` → 0 matches). Most of the work happened; the
*record* did not. This section is that record.

Findings are numbered `F-01…F-12` in the order of the table in **Findings and required
dispositions** above. Tokens are the canonical set of `DADAIA.md` §5: `fixed`,
`superseded`, `deferred`, `rejected`. Evidence paths are repo-relative at HEAD `8a8f4f80`.

| # | Sev | Finding (short) | Disposition | Evidence |
|---|-----|------|------|------|
| F-01 | CRITICAL | No versioned provider↔consumer compatibility contract | `fixed` | `dadaia_workspace/public/schemas/dadaia-capabilities-v2.schema.json`; `features/capabilities/service.py:11` (`CAPABILITY_SCHEMA_VERSION`); enforced at `features/certification/service.py:137` and `features/reconcile/service.py:142` — both reject a payload whose `schema_version != "dadaia-capabilities-v2"` |
| F-02 | HIGH | Consumer upgrade only replaces the persistent wheel | `fixed` | `features/reconcile/service.py:1` — "Post-install **transaction** for state, projections, doctors, and capabilities"; `_snapshot_state` `:37`, `_restore_state` `:55`, `rollback_required` `:24`, permission preflight `:90` |
| F-03 | HIGH | Consumer prompt and tests preserve removed lifecycle commands | `deferred` | Target is the external consumer repository — not provable from this tree. Inherited **in full, as acceptance criteria**, by `specs/backlog/consumer-side-validation-round.md` (grill ADR #1); that entry names this finding explicitly. `rejected` was refused because it would contradict the §6 approval model ("a candidate is approved when the operator and the consumer-side validation agent agree, after validating a real workspace"). Premise also shifted: v0.3.0 removed the whole `dadaia lifecycle` verb group (`specs/_archive/releases/v0.3.0/CLOSURE.md:10-17`) |
| F-04 | HIGH | Fresh root-level `codex exec` misses target-repository context | `fixed` | `dadaia_workspace/hooks/ctx_inject.py` (bind-driven context-memory injection) + the single resolution authority with PATH-first `target_path` at `hooks/sdd_gate.py:9-16`; ratified as law §3 |
| F-05 | HIGH | Existing E2E does not certify the assembled consumer journey | `fixed` | `dadaia_workspace/public/data/CONSUMER_VALIDATION_RECIPE.md` + `specs/memory/product/platform/consumer-agent-support.md:20-44`: the deterministic matrix F-01…F-26 is declared "necessary, never sufficient alone", and the real-use matrix R-01…R-08 (live chain with per-link artifact proof) is mandatory for every candidate. Resolved more strongly than requested — the release gate became the consumer-side validation agent, not an internal E2E |
| F-06 | HIGH | The consumer owning repository is governance-incoherent | `deferred` | External repository; no file in this tree attests its marker/memory/evidence state. Inherited **in full, as acceptance criteria**, by `specs/backlog/consumer-side-validation-round.md` (grill ADR #1) |
| F-07 | MEDIUM | `context list --json` documented but unsupported | `fixed` | `dadaia_workspace/cli/commands/context.py:201-226` — `--json` ("Output stable JSON contract"), 8 stable fields per context |
| F-08 | MEDIUM | `context heartbeat` ignores the persisted bind | `fixed` | `dadaia_workspace/cli/commands/context.py:649-665` — resolves the caller-owned session from the explicit eval-flow override **or** the harness-native session id persisted by `context bind`; actionable error when no identity exists |
| F-09 | MEDIUM | Unbound resolution selects the first ALIVE context | `fixed` | Single authority `container.resolve_context`; `hooks/sdd_gate.py:88-91` — a target under `repos/<slug>/` belongs to `<slug>` "regardless of `DADAIA_CONTEXT` or which context is first-ALIVE in the registry"; `first.?alive` in `core/specs_resolver.py` → 0 matches; the three resolution rungs are law §3 |
| F-10 | MEDIUM | Empty-repository onboarding has no explicit baseline contract | `superseded` by bug `context-alive-sweeps-unrelated-worktree-changes` | The baseline exists: `features/spec_context/service.py:360-420` — scaffold merge preserving a pre-existing tree, `repo-AGENTS.md`, conditional `tests/AGENTS.md`, baseline commit. What the audit asked for and is still missing — *operator-consented* initialization — is precisely the open bug's object: the baseline commit stages `git add -u` over the entire worktree (`infrastructure/git_subprocess.py:43`, called from `service.py:416-420`), committing unrelated operator WIP under a "specs baseline" message. Not an independent finding; carried by a registered open bug and fixed Arm B on `hotfix/{M.m.p}` (§1). Never dropped |
| F-11 | MEDIUM | Telegram delivery truncates diagnostic output | `rejected` — obsolete in this repository | The surface is gone. `telegram` appears **once** under `dadaia_workspace/`: `public/data/CONSUMER_VALIDATION_RECIPE.md:498-499`, and it is the *solution*, not the defect — a one-line bounded "Verdict line (Telegram-short)" ending in `evidência: <path>`, i.e. bounded delivery plus a link to the complete result, exactly the disposition the audit required. The transport itself belongs to the operator's private environment, declared out of this library's scope by `specs/memory/product/platform/consumer-agent-support.md:56-61` |
| F-12 | MEDIUM | Academy notes mistaken for executable agent knowledge | `fixed` | The separation exists: versioned operational knowledge ships as **skills** inside the wheel (`specs/memory/tech-stack.md:41-44` — public assets ship in-package: agents, skills, the `DADAIA.md` law, schemas, templates), while Academy is a read-only browse surface over `knowledge_basis` in the panel (memory atom `academy`, catalog rank 5) |

**Score:** 8 `fixed` · 1 `superseded` · 1 `rejected` · 2 `deferred` — 12 of 12
dispositioned, none dropped (law §5: an audit cannot silently drop a finding).

**Acceptance boundary (above) — status.** The boundary text is preserved as the historical
requirement of the v0.2.5 remediation. It is not re-opened by this disposition: F-05
records that the acceptance model itself changed — the assembled-journey proof is now the
consumer-side validation round (`consumer-agent-support`), whose execution is tracked by
`specs/backlog/consumer-side-validation-round.md`, the same entry that inherits F-03 and
F-06.

**Archive:** this file moves to
`specs/audits/_archive/2026-07-15-consumer-dadaia-integration--dispositioned-v0.8.0.md`
in release v0.8.0. Everything above this section is the original record, unaltered.

