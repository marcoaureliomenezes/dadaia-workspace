# Closure: Release — v0.3.0

> **Status:** Aprovado
> **Release ID:** v0.3.0
> **Owner:** product-engineer
> **Closed:** 2026-08-07

## Summary

v0.3.0 removes the dadaia-workflows engine from dadaia-workspace. The bug-ledger audit of
416 bugs produced one unambiguous finding — the engine was the bug factory (200 of 416
bugs in the `features/lifecycle` cluster, a 96% fix-ratio inside it, and a median 0.48 day
from `resolved` to the next same-family re-report) — and the operator ruled: demolish. The
engine core, its four workflow bodies, the `dadaia lifecycle` verb group, the Layer-2
worker adapters, the panel Workflows and Model-policy tabs, the fragment and persona asset
trees, the workflow schemas, the container wiring, the import-linter contracts and every
line of prose that described them are gone.

What survives is what the ordered lifecycle always actually was: a flow governed by
documents — backlog, SPEC, PLAN, TASKS, CLOSURE, the bug ledger — executed by dispatching
the owning agent, and bounded by the deterministic gate and the git chokepoints. The
workspace no longer ships an agent-execution runtime. `DADAIA.md` §1 was rewritten so Arm A
is the agent-dispatched SDD flow; Arm B (bugs) is unchanged, verbatim.

In the same release `infrastructure/public_assets.py` was de-flagged before it repeated the
same accretion story: `install()` keeps its port-conforming public signature and is now the
boundary translator, resolving its arguments once into an immutable install plan and running
an ordered list of flag-free steps. Private step signatures went from 16 boolean parameters
to 1. The default install path is byte-neutral — the goldens passed unchanged.

## Metrics

Measured against the baseline `main @ ec301ae3`
(source: `.dadaia/reports/dadaia-workspace/qa-engineer/2026-08-07T040247Z-v030-demolition-metrics.html`).

| Metric | Before | After | Δ |
|---|---|---|---|
| Diff vs `main @ ec301ae3` | — | 348 files, +1,775 / −61,883 | **net −60,108** |
| Production LOC | 70,208 | 44,789 | −25,419 |
| Test LOC | 92,272 | 59,951 | −32,321 |
| Tests passed | 2,973 | 2,074 | −899 |
| Test functions | 1,671 | 1,121 | −550 |
| Production modules | 332 | 264 | −68 |
| import-linter contracts | 10 | 9 | −1 |
| import-linter ignore cap | 29 | 16 | −13 |
| `public_assets.py` private-step bool params | 16 | 1 | −15 |
| Panel governance tabs | 6 | 5 | −1 |
| Capabilities schema | `dadaia-capabilities-v1` | `dadaia-capabilities-v2` | breaking mint |
| Package version | 0.4.2 | 0.5.0 | minor bump |

## Tasks completed

All thirteen tasks are `[x]` on branch `feature/v0.3.0`. Per-task commit SHAs are the
branch history between `main @ ec301ae3` and the branch head; the branch was not squashed.

| Task ID | Description | Final commit |
|---|---|---|
| T-30-01 | Sever the CLI edge; delete `cli/commands/lifecycle.py` and `features/ai_surface/` | `feature/v0.3.0` |
| T-30-02 | Sever the panel edge; delete the Workflows and Model-policy tabs | `feature/v0.3.0` |
| T-30-03 | Sever certification + capabilities; mint `dadaia-capabilities-v2` | `feature/v0.3.0` |
| T-30-04 | Sever `container.py` (~1,400 of 2,300 lines) | `feature/v0.3.0` |
| T-30-05 | Delete the engine and its adapters, models, protocols and tests | `feature/v0.3.0` |
| T-30-06 | Delete the engine assets and their projection dirs | `feature/v0.3.0` |
| T-30-07 | Rewrite `DADAIA.md` §1 (Arm A without the engine) and re-project | `feature/v0.3.0` |
| T-30-08 | Grep-driven prose sweep to zero residue | `feature/v0.3.0` |
| T-30-09 | Prune import-linter contracts, lower the caps, update the contract tests | `feature/v0.3.0` |
| T-30-10 | De-flag `infrastructure/public_assets.py` into a flag-free step pipeline | `feature/v0.3.0` |
| T-30-11 | Quality gates, residue grep, CHANGELOG | `feature/v0.3.0` |
| T-30-12 | Quantified removal report (LOC + deleted tests) | `feature/v0.3.0` |
| T-30-13 | Memory atoms, CLOSURE | this commit |

## Validations

| Description | Command | Evidence |
|---|---|---|
| Full Python suite green after the cut | `.dadaia/.venv/bin/python -m pytest -p no:cacheprovider -q` | `2074 passed` (T-30-11) |
| Strict type check | `mypy --strict` | clean (T-30-11) |
| Format + lint | `ruff format --check` / `ruff check` | clean (T-30-11) |
| Import contracts with zero unmatched ignores | `lint-imports --config setup.cfg --no-cache` | green, 9 contracts, ignore cap 29→16 (T-30-09/T-30-11) |
| Residue grep | `grep -riE "dadaia.workflows\|dadaia lifecycle\|features[./]lifecycle" dadaia_workspace tests docs README.md CHANGELOG.md` | only historical `CHANGELOG.md` entries (T-30-11) |
| Deterministic certification on the live instance | `dadaia certify --json` | **11/11 PASS** (T-30-11) |
| Public projection round-trip | `dadaia public stage && dadaia public install --target all && dadaia public doctor` | green, no orphan `lifecycle_fragments/` or `personas/` tree left behind (T-30-06/T-30-11) |
| Install goldens unchanged by the de-flag | `pytest tests/unit/infrastructure/test_install_target_goldens.py` | passed **without** `UPDATE_INSTALL_GOLDENS` (T-30-10) |
| Quantified removal report | measurement pass vs `main @ ec301ae3` | `.dadaia/reports/dadaia-workspace/qa-engineer/2026-08-07T040247Z-v030-demolition-metrics.html` |

## Review outcomes

| Reviewer | First verdict | Final |
|---|---|---|
| `software-architect` | CHANGES-REQUIRED | corrected in-release; findings addressed before T-30-11 |
| `code-reviewer` | CHANGES-REQUIRED | remediated in T-30-11 |
| `qa-engineer` | acceptance list executed | all gates green; metrics report emitted (T-30-12) |
| `security-reviewer` | **not yet run** | required before push — see Operator decisions (b) |

## Drifts

### archive-path-is-frozen

**Description:** T-30-13 called for moving `product/sdd/dadaia-workflows.md` and
`product/sdd/lifecycle-foundation.md` into `specs/_archive/legacy-memory/2026-08-07/`.
`specs/_archive/**` is a FROZEN path class: the gate blocks every file-tool write there,
by design (`[RULE B] … is a frozen archive path (read-only)`). product-engineer has no
`Bash` tool, so it cannot perform the `git mv` itself.

**Resolution:** Both atoms were left **byte-untouched** so the move is lossless, and they
were removed from `product/index.md` and `product/catalog.json`. The archival is a pending
mechanical step recorded below under *Pending mechanical steps*. Stubbing the sources in
place was rejected — it would have destroyed the content being archived.

**Memory updates:** `specs/memory/product/index.md`, `specs/memory/product/catalog.json`.

### layer-2-prose-residue-outside-the-sweep

**Description:** T-30-08's acceptance grep was
`dadaia.workflows|dadaia lifecycle|features[./]lifecycle`. It does not match the string
`Layer-2`, so a small amount of stale prose describing a Layer-2 worker tier survived in
docstrings — notably `dadaia_workspace/core/harness_registry.py` (module docstring lines
1–7 still say "codex/pi are also Layer-2 workers" while the module now exposes exactly one
roster, `L1_ENTRY_HARNESSES`), plus incidental mentions in `public_assets.py`,
`core/role_atom_map.py`, `core/models/agent_model_policy.py` and
`public/kimi-code/AGENTS.md`.

**Resolution:** Cosmetic, not behavioural — the code has one roster and the tests pin it.
Routed to the backlog rather than widened into this release's write set at CLOSURE time
(see *Backlog returns*).

**Memory updates:** none — `tech-stack.md` and `architecture.md` were rewritten from the
code's actual single-roster behaviour, not from the stale docstrings.

### constitution-edit-deferred-to-operator

**Description:** T-30-13's write set included `specs/constitution.md` (Layer-2 prose),
explicitly flagged in both SPEC §6 and TASKS as *requires explicit operator confirmation*.

**Resolution:** Not edited. Recorded under Operator decisions (a).

**Memory updates:** none.

## Memory updates

- `specs/memory/architecture.md` — rewritten: the "Lifecycle" subsystem section removed
  entirely; the overview now states the workspace ships **no agent-execution runtime**;
  panel described as 5 governance tabs; public-install described as plan-then-flag-free-steps;
  runtime-state table drops `runs/lifecycle/` and the Layer-2 policy overlay; "Agentic
  Layers" replaced by "Agent Surface" (documents own the ordered ritual).
- `specs/memory/tech-stack.md` — rewritten snapshot: one harness roster (Claude Code,
  Codex, PI, Kimi Code) single-sourced from `core/harness_registry.L1_ENTRY_HARNESSES`;
  Layer-2 model-profile bullet deleted; `dadaia lifecycle --help` replaced by
  `dadaia certify --json`; packaging note drops fragments/personas; package version 0.5.0.
- `specs/memory/quality-assurance.md` — rewritten: the "Workflow Validation" section
  removed; suite size restated (~2,100 collected); a "Root Cause, Always" section added
  carrying the empirical removal-beats-accretion law; consumer-side approval boundary kept.
- `specs/memory/product/agents/agent-orchestration.md` — rewritten: nine roles, two
  dispatchers, no personas, no four-workflow claim; new "How Ordered Work Happens"
  section grounds sequencing in the SDD documents.
- `specs/memory/product/agents/agent-comms.md` — severed: the FRAG-COH-4 / `InjectedContext`
  Layer-2 cross-reference and the `lifecycle_fragments/shared/output-handoff.md` surface;
  adoption contract restated as **15** surfaces (13 files + 2 skill examples), matching
  `tests/contract/test_handoff_instruction_adoption.py`.
- `specs/memory/product/panel/panel.md` — rewritten: seven tabs → five governance tabs plus
  the Games button; "Workflow Surface" replaced by "Model Governance Surface";
  `workflow_model_policy.json` dropped from runtime state.
- `specs/memory/product/philosophy/product-vision.md` — rewritten: pillar 2 is now
  "Documents are the lifecycle"; new pillar "No mechanism without a demand".
- `specs/memory/product/philosophy/spec-context-project.md` — severed: workflow execution
  removed from the unit's scope and from the enforce step.
- `specs/memory/product/harness/harness-claude-code.md` — rewritten: no Layer-1-only /
  Layer-2-exclusion framing (there is no Layer 2); `.claude/workflows/` removed from the
  scaffold; `.claude/rules/DADAIA.md` named as the projected law file.
- `specs/memory/product/harness/harness-codex.md` — rewritten as an entry harness:
  `CODEX_EXEC` worker, `--harness` auto-default, `DADAIA_CODEX_SANDBOX` worker override and
  the live-worker flow removed; TUI hooks, headless-hook asymmetry, Starlark policy and the
  `.codex/` scaffold kept.
- `specs/memory/product/harness/harness-pi.md` — rewritten as an entry harness:
  `PiHeadlessAdapter`, `agent-run-result-v1`, the Layer-2 model catalog and the "Workflow
  Use" section removed; `.pi/` projection, trust boundary and telemetry kept.
- `specs/memory/product/sdd/sdd-gate-v3.md` — severed: Non-Goals no longer defer ordered
  checks to "the four dadaia-workflows"; PROTECTED row now names the projected law files.
- `specs/memory/product/sdd/sdd-bug-backlog-governance.md` — rewritten: backlog section
  restated as PM-curated + continuously sanitized; pick-time precedence and audit-archival
  rule added; workflow dependency dropped.
- `specs/memory/product/sdd/specs-doctor.md` — severed: `dadaia-workflows` dependency edge.
- `specs/memory/product/index.md` + `specs/memory/product/catalog.json` — regenerated:
  29 → 27 features (the two sdd engine atoms removed), every `depends_on` edge to
  `dadaia-workflows` / `lifecycle-foundation` dropped, tldr/summary/token_estimate rows
  refreshed for every rewritten atom.
- `specs/memory/product/sdd/dadaia-workflows.md`, `specs/memory/product/sdd/lifecycle-foundation.md`
  — **left byte-untouched, pending `git mv` to the archive** (see drift
  *archive-path-is-frozen* and *Pending mechanical steps*).
- Untouched, with reason: every other product atom (`agent-monitoring`, `academy`,
  `plugin-packs`, `public-asset-distribution`, `pypi-distribution`, `harness-kimi-code`,
  `brand-identity`, `consumer-agent-support`, `context-management`,
  `cross-platform-portability`, `multi-platform-parity`, `repos-catalog`,
  `server-registry`, `workspace-doctor`, `workspace-init`, `workspace-portability`) —
  none carried an engine claim.

## Dispositions

| File | Kind | Terminal status | Evidence |
|---|---|---|---|
| `specs/backlog/20260806-clean-architecture-remediation.md` — Item 1 (fate of dadaia-workflows) | backlog | `CONSUMED — v0.3.0` | Demolition executed; Summary + Metrics above |
| `specs/backlog/20260806-clean-architecture-remediation.md` — Item 2 (retry/bounded-revision machinery) | backlog | `SUPERSEDED — v0.3.0` | Subsumed: `_fragment_gate.py` and `pipeline.py` were deleted with the engine (T-30-05); nothing remains to de-retry |
| `specs/backlog/20260806-clean-architecture-remediation.md` — Item 3 (de-flag `public_assets.py`) | backlog | `CONSUMED — v0.3.0` | Delivered as FR6/T-30-10; private-step bool params 16 → 1, goldens unchanged |
| `specs/backlog/20260806-clean-architecture-remediation.md` — Item 4 (one context-resolution rung) | backlog | **OPEN** | Declared out of scope in SPEC §4; `specs_resolver.py` / `ctx_inject.py` were not consolidated by this release and the accreted ladder plus its env-var reads are unchanged |
| `specs/backlog/20260806-clean-architecture-remediation.md` — Item 5 (conduct law, `DADAIA.md` §6) | backlog | **OPEN** | Declared out of scope in SPEC §4. `DADAIA.md` §6 was not amended: the additive-fix-justification and family-recurrence-reopens-the-original rules are still unwritten law. The principle is now recorded in `specs/memory/quality-assurance.md` ("Root Cause, Always") but memory is not always-on law — the §6 amendment still owes the enforcement text |
| `specs/backlog/20260806-clean-architecture-remediation.md` — Item 6 (deferred-debt triage) | backlog | **OPEN** | Declared out of scope in SPEC §4; the 12 deferred bugs have not been individually dispositioned. Note: several are engine-surface bugs whose surface no longer exists, so the triage is now cheaper than when it was filed |
| `specs/backlog/20260806-dadaia-md-workspace-system-prompt.md` | backlog | **OPEN (partially delivered)** | `DADAIA.md` ships, is projected byte-identically to each harness dir, is PROTECTED by the gate and §1 was rewritten by T-30-07. **Not yet done: the named-migrations retirement.** That is the remaining acceptance of this entry and is carried to the next release |
| `specs/backlog/20260715-bugfix-workflow-tdd.md` | backlog | **routed to `project-manager`** | The entry specifies a `bugfix` workflow body under `features/lifecycle/workflows/` plus a fragment set under `public/lifecycle_fragments/` — a surface this release deleted. It cannot be implemented as written. PM to re-scope it as a skill/agent protocol (its strict-TDD sequence is still the desired behaviour) or give it a terminal `REJECTED — targets a deleted surface` disposition. **Not silently dropped** |
| Open engine bugs in `specs/bugs/bugs.jsonl` | bug | **pending — `superseded` events not yet appended** | SPEC §5 requires each open engine bug to receive a `superseded_by: v0.3.0` disposition. The bug ledger is append-only through `dadaia bugs append`; product-engineer has no `Bash` tool and must not hand-edit the JSONL. See *Pending mechanical steps* |

## Backlog returns

- `backlog/candidates.md` ← **Layer-2 prose residue sweep.** Retire the remaining `Layer-2`
  wording in `core/harness_registry.py` (module docstring), `infrastructure/public_assets.py`,
  `core/role_atom_map.py`, `core/models/agent_model_policy.py` and
  `public/kimi-code/AGENTS.md`. The code has exactly one roster (`L1_ENTRY_HARNESSES`); the
  prose still describes a tier that no longer exists. Cosmetic, zero behavioural risk.
- `backlog/candidates.md` ← **`specs/bugs/bugs.jsonl` rotation.** The monolithic ledger
  (414 `reported` events in one file) violates SPEC-DOC-033's canonical
  `<YYYYMMDDTHH>Z-<n>.jsonl` filename and its 1,000-row ceiling. Two pre-existing doctor
  errors, unchanged by this release — see *Known / out of scope*.

## Known / out of scope

- **2 pre-existing `SPEC-DOC-033` errors** in `dadaia specs doctor` (the bug-ledger JSONL
  filename convention and the row ceiling on `specs/bugs/bugs.jsonl`). They predate
  v0.3.0, are unrelated to the demolition, and are explicitly **not** fixed here — history
  is never rewritten (SPEC §4). Routed to the backlog above.
- Backlog Items 4, 5 and 6 remain OPEN by SPEC §4 decision, with reasons recorded in the
  Dispositions table.

## Pending mechanical steps (need `Bash`; product-engineer cannot run them)

```bash
# 1. Archive the two retired memory atoms (FROZEN path — git mv only, contents intact)
mkdir -p specs/_archive/legacy-memory/2026-08-07
git mv specs/memory/product/sdd/dadaia-workflows.md \
       specs/_archive/legacy-memory/2026-08-07/dadaia-workflows.md
git mv specs/memory/product/sdd/lifecycle-foundation.md \
       specs/_archive/legacy-memory/2026-08-07/lifecycle-foundation.md

# 2. Verify memory/catalog coherence after the move
.dadaia/.venv/bin/dadaia specs doctor

# 3. Append the engine-bug supersession events (one per open engine bug)
.dadaia/.venv/bin/dadaia bugs append --bug-id <id> --event superseded \
  --reported-by product-engineer --release v0.3.0 \
  --notes "surface removed by v0.3.0 demolition; superseded_by v0.3.0"
```

Until step 1 runs, `specs doctor` will report the two atoms as present on disk but absent
from `catalog.json`/`index.md` — an expected transient, not a memory defect.

## Operator decisions pending

**(a) `specs/constitution.md` — Layer-2 prose edit.** The constitution still describes a
Layer-2 worker tier and the four-workflow lifecycle. product-engineer owns the file but
`specs/constitution.md` requires **explicit operator confirmation** before any edit
(TASKS T-30-13; SPEC §6). The edit was therefore **not made**. On confirmation, the change
is: remove the Layer-2 persona/worker prose and the four-workflow lifecycle description,
and restate the ordered lifecycle as agent-dispatched and document-governed — the same
framing already applied to `DADAIA.md` §1 and to memory.

**(b) Push / PR of `feature/v0.3.0`.** The branch has not been pushed. The pre-push
chokepoint requires an APPROVED `security-reviewer` handoff whose `metrics.commit_sha`
equals each pushed ref sha; no security review has been run for this branch. Ship sequence:
`security-reviewer` → push → PR → watch CI to green → merge.

**(c) consumer-validator history-rewrite option 2.** Unrelated carry-over from a prior session,
surfaced here so it is not lost. No v0.3.0 dependency in either direction.

## Archive decision

**MOVE** — after decisions (a) and (b) are resolved and the pending mechanical steps run,
move the release directory to `specs/_archive/releases/v0.3.0/` via `git mv` and repoint
`specs/releases/ACTIVE.md`. **Deliberately not performed in this task:** archiving and
repointing `ACTIVE.md` are the operator's ship decision, and repointing now would close the
CLOSURE phase while memory writes and the disposition sweep are still outstanding.
