---
release: v0.1.70
phase: DEFINITION
---

# Active release: v0.1.70 — Contract & Repo-Hygiene Drift

**Phase:** DEFINITION (SPEC/PLAN/TASKS Aprovado; architect APPROVE F1/F2 folded). Kept in DEFINITION through implementation because FR1.2 corrects MEMORY-class atoms (specs/memory/*), gate-writable only in DEFINITION/CLOSURE.

Third and final remediation release for the 9 live dd-chain-capture bugs. Releases
A (engine) and B (context/CLI) are closed. Release C fixes two shipped
self-inconsistencies where the library contradicts itself.

**Picked bugs (2):**
- `specs-doctor-rejects-current-memory-agent-tier-frontmatter` (HIGH) — the memory
  schema correctly rejects `agent_tier` (removed v0.1.61), but three authoring-doc
  copies + one memory-atom body still claim "the schema tolerates it", misleading
  consumers into emitting it. Fix the docs, NOT the schema.
- `remote-bugs-gitignore-blocks-new-intake` (HIGH) — `.gitignore` `/specs/backlog/*`
  ignores the `remote-bugs/` intake subtree; add the negation lines.

After C: archive the remote-bugs, consolidate memory, and write the post-mortem.
