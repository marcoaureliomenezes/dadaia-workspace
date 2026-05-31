# Backlog Candidate — memory-context-enforcement-v1

> **Status:** Candidate (não autoriza implementação)
> **Phase:** 1 of 2 (foundation; precede `memory-structured-source-v1`)
> **Suggested owner:** ai-engineer (exclusive owner of agents/skills/rules/hooks)
> **Co-owners:** software-engineer-python (catalog generation + doctor check), devops-engineer (runtime hook wiring)
> **Source:** `.dadaia/reports/dadaia-workspace/product-engineer/2026-05-30T154500Z-memory-context-engineering-analysis.html`
> **Specialist input:** ai-engineer + software-architect reports (2026-05-30T153000Z) under `.dadaia/reports/dadaia-workspace/{ai-engineer,software-architect}/`

## Problem

dadaia-workspace enforces the **write** side of memory (gate RULE A locks `specs/memory/**` to
product-engineer in CLOSURE; `specs doctor` enforces atomicity/links/images) but has **no read-side
enforcement**. A gate intercepts writes; it cannot force a read. Result: **5/21 agents are fully blind
to product memory, 13/21 only "may" read it, 3/21 truly do.** The most expensive failure in an agentic
system — a worker acting without project context — is the one thing currently unguarded. This is the
core of dadaia-workspace's value proposition: an SDD-oriented, context-engineered development workflow.

## Intent (north star)

**Agents never work blind.** Every agent, on every task, has the architecture + the relevant
product-feature + tech-stack context available at work-start, and can navigate a machine-readable
catalog to pull only the feature it needs. Format and tokens are enablers in service of this.

## Scope (Phase 1 — additive, decoupled, near-free)

1. **Payload the live hook.** `ctx-inject.sh` already fires on every Claude Code + OpenCode prompt
   (`UserPromptSubmit`) but emits only ~5 tokens (active context name). Extend it to inject the catalog
   index + stripped `architecture` + stripped `tech-stack` (~7.3K tokens once). Add a first-message-only
   guard (OpenCode multi-turn) so the payload isn't re-paid every turn.
2. **Machine catalog `catalog.json`.** Per feature: `{rank, slug, title, summary, path, tags[], depends_on[]}`
   (~540 tokens for all 18). Agent matches task keywords → pulls only the 1–3 relevant features, never the
   ~32K of all feature files. Regenerated on `dadaia memory product add` + CLOSURE; a `specs doctor` check
   keeps catalog slugs ↔ feature files in sync.
3. **Universal "Step 0" block.** A verbatim *"Step 0 — Memory bootstrap (mandatory before any
   implementation/review/report)"* block in all 21 agent personas, making `spec-navigator` commanded, not
   optional. Covers runtimes/sessions where the hook isn't present (Codex, standalone). P0: the 5 blind
   agents (code-reviewer, design-specialist, project-auditor, researcher, security-reviewer). P1: the 13
   partial agents.
4. **`specs/memory/AGENTS.md`.** A local contract co-located with the atoms: canonical read order, write
   contract (RULE A), atomicity contract, file manifest. First thing an agent sees in the directory.
   (Also closes a `specs doctor` TREE warning.)
5. **Codex `memory-ctx` adapter.** Generalize the existing role-specific `design-ctx`/`frontend-ctx`
   adapters into a universal memory bootstrap, for 3-runtime parity.

## Locked decisions (operator, grill-me 2026-05-30)

- Enforcement = **soft injection at work-start** (not a hard gate / read-receipt). Guarantees the agent
  *sees* the map; does not prove it *used* it — accepted trade-off.
- North star = **agents never work blind**; format/tokens serve correctness.
- **Decoupled** — NO dependency on the spec-context chain. Rides the existing `ctx-inject.sh`. Can ship
  early / parallel to the panel + spec-context releases. A later release upgrades injection to the
  per-session bind context when `spec-context-session-locks-v1` lands.
- Catalog format = **JSON** (machine index). Content stays HTML in Phase 1 (stripped at injection);
  the YAML source-of-truth migration is Phase 2 (`memory-structured-source-v1`).

## Dependencies

- **None blocking.** Rides live infrastructure. Self-applies to this repo's memory AND to consumer repos
  (the injected behaviour is lib-originated). Phase 2 (`memory-structured-source-v1`) depends on THIS.

## Acceptance shape (to formalize at SPEC time)

- 21/21 agents have a mandatory Step-0 memory block; 0 fully-blind agents remain.
- `ctx-inject.sh` injects catalog + stripped architecture + tech-stack on first message across Claude
  Code + OpenCode; Codex via `memory-ctx`.
- `catalog.json` exists, is generated (not hand-authored), and a `specs doctor` check enforces
  slug↔file sync.
- `specs/memory/AGENTS.md` exists and is validated.
- Injection is tier-agnostic (Haiku → Opus) and cost-bounded (~$2/release at Sonnet/100 invocations).

## Biggest gain

One script change (payload the already-firing hook) ends agent blindness universally — highest
impact-to-effort ratio in the entire analysis.
