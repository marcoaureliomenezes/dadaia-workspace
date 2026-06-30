---
name: software-architect-architecture-vs-code
audit: architecture-memory-vs-code-fidelity
date: 2026-06-30
surface: specs/memory/architecture.md + specs/constitution.md + dadaia_workspace/ code
session: 20260630T021228Z-251bb5f3
agent: software-architect
verdict: REJECTED (architecture-fidelity gate — the constitution misrepresents the runtime architecture)
---

# Architecture memory vs. code — fidelity audit

## Core Workflow trail (architect-core-workflow)

**Step 1 — Problem understood.**
- Core problem: the operator changed the architecture substantially (notably the v0.1.24
  OpenCode removal and the v0.1.28–v0.1.32 two-layer/workflow-engine maturation) and
  suspects memory/specs were not all updated to match the current code. Determine the
  *real* current architecture from code, then audit `architecture.md` (and the
  constitution boundary) for stale / contradicted / missing content, oversize, and slop.
- Constraints: READ-ONLY + ADDITIVE. No edits to memory, constitution, or code. Output is
  this audit file + a structured return for release-definition synthesis.
- Success criteria: an accurate module map; a ranked drift list keyed to file:section with
  severity; a size/split verdict on `architecture.md`; constitution↔architecture migration
  items; and a prioritized, acceptance-criteria-bearing release-scope list.
- Assumptions made explicit: code is the source of truth (constitution §3 "memory is repo
  truth", but code is canonical for *mechanism*); the v0.1.41 `release_origin` stamp on the
  two atoms means they were touched recently, so drift is subtle, not wholesale.

**Step 2 — Prior art surveyed (doc-vs-code sync).** The established patterns for keeping an
architecture document honest against code are: (a) *executable architecture* — `import-linter`
contracts in `setup.cfg` are already the load-bearing, CI-enforced layer law (the doc should
defer to them, not re-narrate them); (b) *single-source enumeration* — runtime enums
(`AgentRuntimeKind`) must be named in exactly one prose location, ideally the code-derived
atom, and cited elsewhere, so the law cannot drift independently; (c) *memory-as-current-truth*
— release narrative belongs in `CLOSURE.md`/`_archive`, not in a living atom (root AGENTS.md
"Memory is current product truth, not history"; constitution §12 anti-slop "no fact in two
sources"). All three are already partially adopted here; the drifts below are precisely where
they were not followed.

---

## 1. Corrected current-architecture module map (from code)

Layering (hexagonal, enforced by `import-linter` in `setup.cfg`):

- **`cli/`** (`dadaia_workspace/cli/main.py`) — thin Typer app. **23 registered command
  surfaces** (not 22): `init`, `export`, `import`, `clean`, `context`, `lock`, `lifecycle`,
  `ci`, `repos`, `public`, `doctor`, `academy`, `orchestrate`, `reports`, `specs`, `server`,
  `migrate`, `panel`, `memory`, `release`, `backlog`, `bug`, `bugs`. `release`/`backlog`/`bug`
  apps come from `cli/commands/newartifacts.py`; `bugs` is a separate group from `bug`.
- **`features/`** — business logic, one folder per feature, depends only on `core/protocols/*`.
  Lifecycle engine lives in `features/lifecycle/` (state machine, `phase_workflow.py` single-step,
  `pipeline.py` multi-step ladder, `prompt_builder.PromptPrefix`, `workflows/{release_definition,
  backlog_definition,audit,research,bug_report}.py`, `workflow_handoffs.py` run-scoped step
  data plane, `policy_resolver.py`/`model_profiles.py`/`policy_doctor.py` workflow governance,
  `context_selector.py`, `antislop/{slop_scan,retention}.py`). Backlog-consistency engine in
  `features/backlog/`. Telemetry in `features/telemetry/` (`RuntimeAdapter` registry =
  claude/codex/pi). Panel in `features/panel/`.
- **`core/`** — pure (zero I/O). `models/` (incl. `models/lifecycle.py`), `protocols/`,
  `exceptions.py`, `platform.py` (sole `sys.platform` site), `kernel_tunables.py` (leaf),
  `scope_match.py` (shared Ring-1/Ring-2 path classifier), `harness_models.py`,
  `model_registry.py`, `lock_liveness.py`.
- **`infrastructure/`** — concrete adapters behind protocols, incl. the four agent-runtime
  adapters: `fake_runtime.py`, `codex_runtime.py`, `claude_sdk_runtime.py`, `pi_runtime.py`
  (all sharing `headless_adapter_base`). `opencode_runtime` is gone.
- **`hooks/`** — Python governance package, **8 modules** (`__init__`, `_common`, `pre_gate`,
  `sdd_gate`, `root_whitelist`, `venv_guard`, `ctx_inject`, `sdd_post_gate`). Merged PreToolUse
  entrypoint `pre_gate` (root-whitelist → venv-guard → SDD, first-block-wins).
- **`container.py`** — sole composition root.
- **`public/`** — canonical assets; install targets `{agents, claude, codex, pi}` (+`all`).

**Two agentic layers (from code):**
- Layer-1 entry harnesses: exactly **{claude, codex, pi}**.
- Layer-2 worker enum `AgentRuntimeKind` (`core/models/lifecycle.py:51`) = **FAKE, CODEX_EXEC,
  CLAUDE_SDK, PI_HEADLESS** — **four members, no `OPENCODE_RUN`.** Selectable workflow harnesses
  (LAW 1) = `{pi, codex, fake}`; `claude`/`opencode` rejected by `_LAYER1_ONLY_HARNESSES`
  (`cli/commands/lifecycle.py:62`) and by `policy_doctor` WMP-7.

This map matches `architecture.md` almost exactly. The one true OpenCode residue *inside*
`architecture.md` is the `OPENCODE_SESSION_ID` env var (see drift #3). The substantive
OpenCode rot is in the **constitution**, not in `architecture.md`.

---

## 2. Ranked drift list

### [CRITICAL] Constitution describes a 5-runtime / 4-entry-harness OpenCode world that no longer exists
Location: `specs/constitution.md` — §0 "What dadaia-workspace is" (L30); §0 "The two agentic
layers" (L117, L119, L121, L136–137, L144); §0 "Workspace root & operational layout" (L165 +
"ten allowed root entries"); §8 Layer-1 enforcement matrix (L444); §8 Layer-2 worker posture
(L449–451).
Issue: The constitution still states the operator "may launch Claude Code, Codex, **OpenCode**,
or PI"; lists `.opencode/` as projected assets and as root entry #5; names `opencode run`
(`OPENCODE_RUN`) as a supported Layer-2 transport; asserts "**The five `AgentRuntimeKind`s
today are FAKE, CODEX_EXEC, CLAUDE_SDK, OPENCODE_RUN, PI_HEADLESS**"; keeps an OpenCode row in
the Layer-1 matrix; and repeats the five-runtime claim in §8 Layer-2 posture. Code has **four**
`AgentRuntimeKind`s (no `OPENCODE_RUN`); OpenCode was removed entirely in v0.1.24; the root
whitelist (AGENTS.md) is 9 entries with no `.opencode/`.
Why it matters: The constitution is the permanent product law and the architecture-fidelity
reference. It now directly contradicts both the code and `architecture.md` (which correctly
says {claude, codex, pi} / 4 runtimes). An agent that trusts the law over the atom will
re-introduce OpenCode targets, `.opencode/` projection, or an `OPENCODE_RUN` worker — exactly
the "build on a stale layer" defect. The root-entry count ("ten" incl. `.opencode/`) also
contradicts the root-whitelist hook (9 entries), so the law disagrees with a deterministic gate.
Trade-off if fixed: Pure win — removes a contradiction between law, memory, and code. Cost is a
careful constitution edit in the DEFINITION/CLOSURE phase (MUTATING; product-engineer; lease
required). No code change.
Recommendation: In a release, strike every OpenCode reference from the constitution: §0 harness
list → {Claude Code, Codex, PI}; remove `.opencode/` from the two-layer governance prose and
from the root layout (renumber to 9 entries); delete `opencode run`/`OPENCODE_RUN` from the
Layer-2 transports; change "five `AgentRuntimeKind`s … OPENCODE_RUN …" to the four real members;
drop the OpenCode row from the §8 Layer-1 matrix; fix §8 Layer-2 posture to the four runtimes.

### [HIGH] architecture.md has become a changelog-in-memory (oversize + version-narrative accretion)
Location: `specs/memory/architecture.md` — whole file; frontmatter `token_estimate: 13000`;
pervasive `(v0.1.24)…(v0.1.32)` annotations and migration prose (e.g. L619–663 backlog
subsystem, L665–776 workflow control plane, L778–823 handoff data plane, L934–966 typed-gate
contract).
Issue: The file is ~93 KB / ~1007 lines. The Read tool measured ~40,892 tokens for the first
523 lines alone (cap 25,000), i.e. the full body is well over **30–40k tokens of actual
content** — the frontmatter `token_estimate: 13000` understates it by >2×. More important than
size: the atom is written as accreted release history ("substituíram os stubs", "o D-2 collapse
foi removido", "corrige a divergência v0.1.28 codex-gravado-enquanto-pi-rodava", per-feature
"(v0.1.NN)" stamps). Memory is supposed to be *current product truth, not history* (root
AGENTS.md; constitution §12/§13); changelog belongs in `CLOSURE.md`/`_archive`.
Why it matters: A current-state reader cannot tell which sentences are live truth vs. historical
narration, and the doc is too large to self-pull cheaply (it is deliberately excluded from the
lean inject payload precisely because it is large). The version-narrative style guarantees
future drift: each release appends a new "(v0.1.NN) X replaced Y" clause instead of editing the
statement to current truth. This is the structural slop that produced the constitution drift
elsewhere — facts narrated, not stated once.
Trade-off if fixed: Splitting/trimming costs product-engineer effort in a DEFINITION phase and a
catalog/wikilink update; the gain is a navigable, self-pullable map and a correct
`token_estimate`. Risk: over-aggressive splitting could fragment cross-cutting concerns —
mitigate by keeping the layer map + dependency law in the core atom and extracting *subsystems*.
Recommendation: (a) Rewrite to current-state voice — delete every "(v0.1.NN)"/"replaced"/"collapse
removed"/"corrige a divergência" clause; state only what *is*. (b) Split into atoms:
`architecture.md` keeps Visão geral + Camadas + Regras de dependência + the 3 report channels +
state-runtime index; extract `architecture-lease-concurrency.md` (lease schema/CAS/mode chain —
or fold into existing `sdd-gate-v3`/`context-management`), `architecture-workflow-engine.md`
(two-layer model + control plane + handoff data plane — or fold into `lifecycle-foundation`),
and `architecture-backlog-consistency.md` (or fold into `sdd-bug-backlog-governance`). Several of
these subsystems already have product atoms; prefer *citing* them via `[[slug]]` over duplicating.
(c) Recompute `token_estimate`.

### [MEDIUM] architecture.md residual OpenCode reference (OPENCODE_SESSION_ID)
Location: `specs/memory/architecture.md` L501 (Memory injection subsystem → ctx_inject step 2).
Issue: Lists `OPENCODE_SESSION_ID` as a harness-native session-id env var. `hooks/ctx_inject.py`
resolves the session id from `DADAIA_SESSION_ID → CLAUDE_CODE_SESSION_ID → CODEX_SESSION_ID →
stdin session_id → "workspace"` — there is no `OPENCODE_SESSION_ID`.
Why it matters: It is the only OpenCode residue left inside the otherwise-clean atom, and it
contradicts the same atom's own (correct) "OpenCode removed in v0.1.24" statements two paragraphs
above. Low blast radius but it is exactly the kind of stray that misleads.
Trade-off if fixed: Trivial one-line edit; pure correctness gain.
Recommendation: Drop `OPENCODE_SESSION_ID` from the env-var list in L501.

### [MEDIUM] import-linter contract description is stale (7 vs 17 edges; 2 vs 6 contracts)
Location: `specs/memory/architecture.md` §"Regras de dependência" → "Enforcement" (L344–348) and
§"Transitional debt (ADR-1)" (L348).
Issue: The atom says "import-linter tem **7** `ignore_imports`" and names only **two** contracts
(`features → infrastructure` ban + `core → OS-primitive` ban). `setup.cfg` actually defines
**six** contracts — `features-no-infrastructure`, `features-no-subprocess`, `core-no-os-primitives`,
`core-no-upper-layers`, `infrastructure-no-upper-layers`, `kernel-tunables-is-a-leaf` — and the
ignore-edge total is **17** (12 + 5), explicitly capped and pinned by
`tests/contract/test_import_linter_ignore_cap.py`.
Why it matters: The atom undersells the *strongest* part of the architecture — the executable
layer law. A reader doesn't learn that core/infrastructure upward-import bans and the
kernel-tunables leaf are CI-enforced, nor that the ignore cap is a governed debt ledger. Since
`import-linter` is the load-bearing enforcement, the doc should defer to it accurately.
Trade-off if fixed: Small doc edit; gain is the doc matches the CI-enforced reality and points
readers at the cap test as the debt ledger.
Recommendation: Update to "six import-linter contracts" and "17 capped ignore edges (cap pinned
in `test_import_linter_ignore_cap.py`)"; list the reverse-direction + leaf contracts.

### [LOW] CLI subcommand list off by one and missing `bugs`/`newartifacts`
Location: `specs/memory/architecture.md` §"Camadas" → cli/ (L45).
Issue: Says "22 subcommands"; `cli/main.py` registers **23** and the atom omits the `bugs` group
(distinct from `bug`) and does not mention `cli/commands/newartifacts.py` as the source of the
`release`/`backlog`/`bug` apps.
Why it matters: Low — a count/inventory nit, but inventories are exactly what readers trust.
Trade-off if fixed: One-line edit.
Recommendation: Correct to 23, add `bugs`, note `newartifacts.py` provides release/backlog/bug.

### [LOW] Academy course content still teaches OpenCode as a live 4th Layer-1 harness
Location: `dadaia_workspace/features/academy/knowledge_basis/08_pi_agent/04_pi_como_quarto_harness_dadaia.md`
(L7 "Code, Codex e OpenCode"; L19 table row "OpenCode | Layer-1 (entrada, advisory) | `.agents/`").
Issue: The academy lesson presents OpenCode as a current Layer-1 entry harness. It was removed in
v0.1.24. This is dead/misleading instructional content shipped in `public/` (it projects to the
Academy panel tab).
Why it matters: Onboarding readers are taught a runtime that no longer exists; it is the same rot
class as the constitution drift, in a learner-facing surface.
Trade-off if fixed: Course-content edit (ai-engineer surface) in a release; pure correctness.
Recommendation: Update the lesson to the {claude, codex, pi} set and remove the OpenCode row.

### Stray OpenCode refs that are CORRECT (keep — these are anti-regression guards)
The seed's "~9 stray opencode refs" are overwhelmingly **intentional residue detectors**, not
dead code. Verified and to be KEPT as-is:
- `cli/commands/lifecycle.py:62-67` `_LAYER1_ONLY_HARNESSES` (rejects `opencode`/`open-code`).
- `infrastructure/json_workflow_model_policy_store.py:55,317` (overlay rejects opencode).
- `features/lifecycle/policy_doctor.py:29,33,72,314` (WMP-7 residue check).
- `features/lifecycle/policy_public_doctor.py` (entire module = public-doc opencode-leak scanner).
- `features/lifecycle/policy_resolver.py:137,355` (rejection messaging).
- `cli/commands/public.py:152` (residue check comment).
- `public/schemas/workflow-model-policy-v1.schema.json:73` (schema enum description).
- `features/lifecycle/fragments/loader.py:91` (`.opencode/` in the harness-token denylist that
  lints fragments to *not* name opencode).
These name "opencode" precisely to forbid it. Do not remove them.

---

## 3. Verdict on architecture.md size/split

**Oversized and unfocused — split + de-narrate (see drift #2).** The layer map, dependency
rules, and 3-channel model are appropriately core-atom material and should stay. The four
heavy subsystems (lease/concurrency, workflow engine + control plane, handoff data plane,
backlog-consistency) are each large enough to be their own atom and several already have a
product atom that should own them (`sdd-gate-v3`, `context-management`, `lifecycle-foundation`,
`sdd-bug-backlog-governance`). The atom should cite those via `[[slug]]` rather than re-state
them. Re-stamp `token_estimate` after trimming.

---

## 4. Constitution ↔ architecture boundary (migration items)

- **Move the runtime enumeration out of the constitution.** §0 "two agentic layers" hardcodes
  "The five `AgentRuntimeKind`s today are …". That enumeration is **mechanism that drifts** — and
  it is exactly the line that went stale. The constitution should state the *concept* (two layers;
  entry-harness vs worker-harness; AgentRuntimePort seam) and the *invariant* (Layer-2 workers run
  GPT under the operator's subscription; claude is Layer-1 only), then cite `[[architecture]]` /
  `[[multi-platform-parity]]` for the concrete runtime set. Single-source the enum in the
  code-derived atom so the law cannot drift independently again.
- **Trim §8 mechanism to invariant-level.** §8 reproduces the lease record schema, the O_EXCL CAS,
  the by-session index, `kernel_tunables`, the four-step mode-resolution chain, and the pre_gate
  policy order — all duplicated near-verbatim in `architecture.md`/`sdd-gate-v3`. Per constitution
  §12.2 ("no fact recorded in two sources"), the constitution should hold the **binding
  invariants** (one MUTATING lease per context; live foreign lease never stolen; ADDITIVE never
  leased; READ non-acquiring; fail-open except PROTECTED; the never-instruct-rebind law) and cite
  `[[architecture]]`, `[[sdd-gate-v3]]`, `[[context-management]]` for the mechanism. This is a
  softer recommendation than the OpenCode strike, but it is the same root cause: mechanism narrated
  in two places drifts.
- **No genuine law was found mis-filed in memory.** The drift runs the other way: mechanism is
  over-replicated in the constitution. `architecture.md` is correctly mechanism-in-memory.

---

## 5. Biggest real drifts (summary)

1. The **constitution is stale on OpenCode** (5-runtime/4-harness world) — the law contradicts
   the code and the memory atom. (CRITICAL)
2. **architecture.md is a changelog-in-memory** — oversized, version-narrated, `token_estimate`
   understated >2×. (HIGH)
3. The runtime **enum is double-sourced** (constitution + atom), which is *why* #1 happened.
   (boundary)

---

## 6. Prioritized release-scope items (acceptance-criteria-bearing)

| # | Sev | Change | File(s) | Acceptance criterion |
|---|-----|--------|---------|----------------------|
| 1 | CRITICAL | Strike all OpenCode from the law | `specs/constitution.md` §0, §8 | `grep -ri opencode specs/constitution.md` returns 0 matches; §8 Layer-2 posture and §0 list the four real `AgentRuntimeKind`s; root layout lists 9 entries (no `.opencode/`); Layer-1 matrix has no OpenCode row |
| 2 | MEDIUM | Single-source the runtime enum | `specs/constitution.md` §0 | Constitution no longer enumerates `AgentRuntimeKind` members; it cites `[[architecture]]`/`[[multi-platform-parity]]`; the concrete enum appears in exactly one prose atom |
| 3 | MEDIUM | Remove `OPENCODE_SESSION_ID` residue | `specs/memory/architecture.md` L501 | The env-var list matches `hooks/ctx_inject.py` resolution chain; no OpenCode token remains in `architecture.md` |
| 4 | MEDIUM | Fix import-linter description | `specs/memory/architecture.md` L344–348 | Doc states 6 contracts and 17 capped ignore edges; references `test_import_linter_ignore_cap.py` |
| 5 | HIGH | De-narrate + split architecture.md | `specs/memory/architecture.md` (+ new/existing atoms) | No `(v0.1.NN)`/"replaced"/"collapse removed"/"corrige a divergência" clauses remain; core atom ≤ ~6–8k tokens; heavy subsystems live in/cite their product atoms; `token_estimate` re-stamped to measured value; `catalog.json` + wikilinks updated; `dadaia specs doctor` (LINT-1/CAT-1) green |
| 6 | LOW | Fix CLI subcommand inventory | `specs/memory/architecture.md` L45 | Says 23 subcommands incl. `bugs`; notes `newartifacts.py` |
| 7 | LOW | Update academy OpenCode lesson | `dadaia_workspace/features/academy/knowledge_basis/08_pi_agent/04_pi_como_quarto_harness_dadaia.md` | Lesson lists {claude, codex, pi}; no OpenCode row; re-staged via `dadaia public install` |

All edits to `specs/constitution.md` and `specs/memory/**` are MUTATING/MEMORY-class: they
must run in a release under the lease, with `specs/memory/**` written only in DEFINITION/CLOSURE
(product-engineer). Items 1–4 and 6 are low-risk text fixes that should be batched first; item 5
is the larger refactor; item 7 is an ai-engineer public-asset edit.

## Gate verdicts
- **Architecture-fidelity gate: REJECTED.** The constitution misrepresents the runtime
  architecture (OpenCode / five `AgentRuntimeKind`s) vs. the four-member code enum. Correction:
  release-scope item #1 (+ #2 to prevent recurrence).
- **Root-cause gate: PASS (with note).** No bug-fix workaround under review here; but note the
  *root cause* of the drift is the double-sourced runtime enum (item #2) — fixing only the
  OpenCode strings without single-sourcing the enum would leave the defect live.
