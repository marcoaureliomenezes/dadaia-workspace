# EMISSION-FORMAT — dd-grill-me (report mode only)

Disclosed reference reached only when Step 5 writes the optional HTML report (operator asked for one, or the next handoff target is human).
Follows the canonical template in `.dadaia/reports/AGENTS.md` — this file adds only what that template leaves to the caller.

| Section (`.dadaia/reports/AGENTS.md`) | Fill with |
|---|---|
| `Summary` | Session scope (entire backlog / one feature-id) and the problem count |
| `Question resolved` | Every frontier question settled, its answer, "answered via inspection" vs operator decision (ADR line) |
| `Decision needed` | Any design-tree node still open when the session ended — empty once Step 4 clears |
| `Spec impact` | The consolidated list of pending spec edits: file, section, what changes |
| `Evidence` | Files, commands, and subagent findings used during Step 1 inspection |
| `Result` | `pass` once the operator confirmed shared understanding, `blocked` otherwise |
| `Next action` | e.g. "product-engineer authors SPEC.md" |
