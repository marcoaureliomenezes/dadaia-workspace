---
name: dadaia-codebase-design
description: >
  The shared design vocabulary — seam, deep module, deletion test, adapter,
  locality, replace-don't-layer — plus the understand-the-problem discipline run
  before any recommendation, fix or verdict. Use when designing or reviewing a
  module's interface, deciding where a seam goes, judging whether a diff grows or
  shrinks a feature, or naming a structural problem.
---

# dadaia-codebase-design

Reviews, fixes and architecture findings speak ONE language. This vocabulary is the
anti-bug-loop law in words: the measured bug history showed additive fixes (branches,
flags, wrappers) breeding chains, and deletion-shaped fixes ending families.

## 1. When

- Before forming any recommendation, fix direction, or verdict about code structure.
- When a diff is about to GROW an existing feature — stop and run the deletion test first.
- When another skill or persona needs the deep-module vocabulary.

## 2. Vocabulary — use these terms exactly

- **Module** — anything with an interface and an implementation; scale-agnostic (function, class, package, tier-spanning slice). _Avoid_: unit, component, service.
- **Interface** — everything a caller must know to use the module correctly: signature PLUS invariants, ordering, error modes, configuration, performance. _Avoid_: API, signature.
- **Implementation** — the module's body. Distinct from adapter: a small adapter can hide a large implementation, and vice versa.
- **Depth** — leverage at the interface: behaviour exercised per unit of interface learned. Deep = small interface, large implementation. Shallow = pass-through.
- **Seam** — where behaviour can be altered without editing in that place; the location of an interface. Placing the seam is its own design decision. _Avoid_: boundary (collides with DDD).
- **Adapter** — the concrete thing satisfying an interface at a seam; a role, not a substance. Translate at the seam, never leak the foreign shape inward.
- **Leverage** — what callers get from depth: one implementation pays back across N call sites and M tests.
- **Locality** — what maintainers get from depth: change, bugs, knowledge and verification concentrate in one place. What changes together lives together.

## 3. Principles

- **Depth is a property of the interface, not the implementation** — internal seams (private, used by the module's own tests) never surface through the interface.
- **The deletion test** — imagine deleting the module: if complexity vanishes it was a pass-through; if it reappears across N callers it earned its keep. Apply it to the module you are about to GROW before growing it.
- **The interface is the test surface** — a test that reaches past the interface says the module is the wrong shape.
- **One adapter = a hypothetical seam; two = a real one** — never introduce a port with a single adapter; that is indirection, not design.
- **Replace, don't layer** — a fix that wraps the old path instead of replacing it is a layer, and layers are how the bug loop grows. The correct fix usually deletes a branch, collapses two paths, or moves logic back inside its owner.

When designing an interface, ask: can I reduce the number of methods? simplify the
parameters? hide more complexity inside?

Design for testability — good interfaces make testing natural:

1. **Accept dependencies, don't create them** — a module that constructs its own
   collaborators can only be tested whole.
2. **Return results, don't produce side effects** — a value can be asserted; a
   mutation must be observed.
3. **Small surface area** — fewer methods mean fewer tests; fewer parameters mean
   simpler test setup.

## 4. Steps — understand the problem, then test the growth

1. Extract the core problem: one sentence describing what must actually be solved.
2. Extract constraints: time, existing systems the solution must live inside, the write set.
3. Extract success criteria in testable terms, and make every implicit assumption explicit.
4. Read the bug ledger for the feature touched (`dadaia bugs stats`) — prior fixes to the same surface are evidence about the structure.
5. Call the Skill tool with `dd-grill-me` for operator-facing clarification; never ask what `Read`/`Glob`/`Grep` can answer.
6. Apply the deletion test to the module the change would grow; if the diff only adds, justify it against the replace-don't-layer principle explicitly.
7. Prefer the shape that raises depth: fewer entry points, simpler parameters, more hidden complexity.
8. Record in the emitted report/verdict: core problem, constraints, the deletion-test outcome, the chosen direction and its trade-off.

## 5. Done when

- The core problem, constraints and assumptions are written down.
- The deletion test was applied to every module the diff grows, with its outcome stated.
- The verdict names whether the change reduces or increases the touched feature's bug surface, with ledger evidence.

## 6. Going deeper

- Deepening a cluster given its dependencies: `DEEPENING.md` (dependency categories, seam discipline, replace-don't-layer testing).
- Exploring alternative interfaces: `DESIGN-IT-TWICE.md` (parallel designs compared on depth, locality, seam placement).
- Portfolio-level candidates from bug history: the `dd-architecture-survey` skill.
- Domain terms: the repo's `CONTEXT.md` (see `dd-domain-modeling`).
