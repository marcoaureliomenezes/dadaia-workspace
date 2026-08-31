# Design It Twice

Your first interface is unlikely to be the best one. For a chosen deepening candidate,
design it at least twice — radically differently — then compare. Vocabulary from
`SKILL.md`; dependency categories from `DEEPENING.md`.

## Process

1. **Frame the problem space** — constraints any interface must satisfy, the dependencies and their categories, one grounding sketch (not a proposal). Show it, then proceed.
2. **Produce 3+ radically different designs.** In this workspace sub-agents cannot nest-dispatch: run the designs as PM-dispatched sibling agents, or as sequential passes in one session. Give each design a different constraint:
   - Minimal: 1–3 entry points, maximum leverage per entry point.
   - Flexible: many use cases, extension points.
   - Caller-first: the most common caller's case is trivial.
   - Ports-and-adapters (when a category-3/4 dependency exists).
   Each design states: interface (with invariants, ordering, error modes), a usage example, what hides behind the seam, the dependency/adapter strategy, and where leverage is thin.
3. **Compare and recommend** — contrast on depth, locality and seam placement; give ONE opinionated recommendation (or an explicit hybrid), never a menu.
