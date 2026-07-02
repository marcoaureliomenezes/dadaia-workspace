# GRILL — v0.1.47 (context-surface truth + fragments/personas optimization + audit remediation)

**Date:** 2026-07-01 · **Coordinator session:** 0bcd6c19/sess_0fb5a586 · **Intake:** operator
`/goal` directive (verbatim in session log) + full audit `specs/audits/20260701T201136Z-0bcd6c19/`
+ backbone backlog item `specs-truth-realignment-constitution-memory` (architect-reviewed
blueprint from the 2026-06-30 audit).

## Operator mandate (distilled)

1. The context surface IS the product: specs, memory, constitution, rules, AGENTS.md, skills,
   sub-agents, fragments, personas, workflows must be reviewed, de-slopped, disambiguated,
   and made consistent. No verbose low-value text, no stale claims, no double-sourcing.
2. Fragments: each fragment is injected into exactly ONE step prompt and must state exactly
   what that step needs — inputs, task, output. Personas: sub-agent-like role context, also
   injected into the prompt. Both must be fully reviewed and optimized.
3. Macro architecture must be crisp: dadaia-workflows are Python bodies driving Layer-2
   worker prompts on pi/codex (headless/SDK); per-step model choice governed from the panel
   Workflows tab; fragments + persona context injected into each prompt.
4. Claude Code is the special Layer-1-only case: never a Layer-2 workflow worker; its
   scaffold (CLAUDE.md bridge, hooks, sub-agents, rules, skills) must be kept and documented.
5. Per-harness isolation is a first-class concept: a workspace can be created for Claude-only,
   Codex-only, PI-only, or combinations; scaffolding follows the choice. Document per harness
   in dedicated memory docs (capabilities + what dadaia scaffolds for each).
6. In Codex/PI entry sessions, dadaia-workflows are the preferred execution path (default
   Layer-2 harness = the entry harness; user may override to the other).

## Decisions (OQ resolutions — grill seeds from the backbone item + audit)

- **D-1 Scope.** v0.1.47 = context-surface truth (WS-A/B/C of the backbone item, consumed in
  full) + operator additions (harness memory docs, fragments/personas optimization) + the
  prompt-assembly and chokepoint code fixes from the 2026-07-01 audit + the disposition sweep
  ACTIVE.md already earmarked for v0.1.47. Deep code remediations that don't touch the
  context surface (lease-kernel identity, panel SQLite/kanban, context-dead exit path,
  import-linter CI wiring, consumer-AGENTS.md fan-out mechanism, heading-allowlist
  extensibility) are DEFERRED to named backlog entries with reasons (audit-disposition law).
- **D-2 Constitution size.** Target ≈200 lines, principle+rationale, each principle
  verifiable; mechanism moves to owning memory atoms (backbone WS-A3/A4/A5/A6 accepted as
  written).
- **D-3 Runtime-roster single source.** `memory/tech-stack.md#Agent runtimes` is the ONE home
  for the harness/runtime roster (it is bootstrap-injected). Constitution states the
  invariant and cites memory; enumerates nothing (WS-A2). A doctor invariant (WS-E) enforces
  it.
- **D-4 architecture.md.** De-narrate in place + extract mechanism depth to owning atoms
  (context-management, sdd-gate-v3, lifecycle-foundation, sdd-bug-backlog-governance) via
  `[[wikilink]]` citation; no child-atom split of architecture.md itself (WS-B7).
- **D-5 Harness docs.** NEW `memory/product/harness/` family: `claude-code.md`, `codex.md`,
  `pi.md` — per-harness capability matrix (Layer-1/Layer-2 availability, enforcement
  posture, transports) + scaffold matrix (what `dadaia public install --target <t>` projects)
  + isolation profile (what a harness-only workspace contains). This resolves backbone B5
  (PI Layer-1 atom: YES, as part of the family). The existing `ai-harness-*` atoms remain
  skill-mirrors for ai-engineer depth; harness/ atoms are the operator/agent-facing truth.
- **D-6 Persona injection fix.** Minimal-correct now: one shared resolution helper threaded
  into the 5 workflow bodies + the CLI single-step path, with per-verb prompt-content tests.
  The full FragmentGateWorkflow base-class extraction (~1,500 dup lines) is DEFERRED to a
  named backlog entry — too invasive to bundle with a truth release.
- **D-7 Harness preference (operator rule 6).** Documented as convention in the harness docs
  + AGENTS.md (entry harness codex ⇒ default `--harness codex`; entry pi ⇒ default
  `--harness pi`; explicit flag always wins). No code change: the engine already accepts
  per-step harness; auto-detection of the entry harness is DEFERRED (backlog:
  harness-isolation-profiles).
- **D-8 Isolation.** Already structurally present (`--target {agents,claude,codex,pi}`);
  v0.1.47 documents it as a first-class concept (harness docs + workspace-init atom).
  `dadaia init --harness <set>` profiles are DEFERRED (backlog: harness-isolation-profiles).
- **D-9 Bug-store tracking.** Discovered during definition: `.gitignore` opts in only
  `specs/bugs/*.md` — the entire JSONL event store (and `_archive/`) is untracked. Fixed in
  this release's definition commit (opt-in `*.jsonl` + `_archive/*.md`); GRILL.md +
  OQ-DECISIONS.md re-includes added for all three release-dir groups (open bug
  `grill-and-oq-decisions-records-gitignored-not-version-controlled`).
- **D-10 WS-D (fake closure bug).** The referenced bug exists in no store; W1 verifies FAKE
  closure behavior with a smoke test and fixes only if broken; otherwise records
  not-reproducible.
- **D-11 Reviews.** SPEC gets a QA-focused internal review before `Aprovado` (architect
  input already embodied in the backbone item's REJECTED→accepted gate); implementation
  follows the standard qa→commit / security→push checkpoints.
