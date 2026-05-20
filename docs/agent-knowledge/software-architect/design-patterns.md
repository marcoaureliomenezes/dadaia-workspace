---
name: architect-design-patterns
description: >
  Reference and decision protocol for Design Patterns. Use when evaluating whether a pattern is
  correctly applied, over-engineered, missing, or abused in a codebase or design. Also covers OOP
  principles (SOLID), modern architectural patterns, and anti-patterns. Invoked by the
  software-architect in both DRAFT (design selection) and REVIEW (pattern audit) modes.
---

# Design Patterns — Reference and Decision Protocol

This skill is a living reference. When reviewing or designing, apply the evaluation protocol in the
final section to every pattern you encounter or propose.

---

## GoF Creational Patterns

| Pattern | Use when | Do NOT use when |
|---------|----------|-----------------|
| **Singleton** | Resource genuinely exists only once (logger, registry, thread pool) | You just want global access — use dependency injection instead |
| **Factory Method** | A base class must defer instantiation to subclasses; clients should not depend on concrete types | Object creation is trivial and will never vary |
| **Abstract Factory** | You need families of related objects without specifying concrete classes | Only one product variant exists — over-engineers for no gain |
| **Builder** | Object has many optional parameters or construction requires ordered steps | Object has ≤ 3 fields — a constructor is clearer |
| **Prototype** | Cloning is cheaper than initialization; object graph is complex | Simple objects — just call the constructor |

**Singleton red flag:** If a "singleton" is being passed around as a parameter or injected, it is not
really a singleton — it is a service. Use dependency injection properly.

---

## GoF Structural Patterns

| Pattern | Use when | Do NOT use when |
|---------|----------|-----------------|
| **Adapter** | Integrating an incompatible interface you cannot modify | You own both sides — fix the interface directly |
| **Bridge** | Abstraction and implementation should vary independently | Only one variation exists — adds indirection for nothing |
| **Composite** | You need to treat trees and leaves uniformly (UI widgets, file systems) | The hierarchy has exactly one level |
| **Decorator** | Adding responsibilities at runtime without subclassing; wrapping a stream | Stacking more than 3 decorators — consider redesigning |
| **Facade** | Simplifying a complex subsystem behind a clean interface | You are hiding a design problem — fix the root cause |
| **Flyweight** | Sharing fine-grained objects to save memory (glyphs, particles) | Object count is not in the thousands |
| **Proxy** | Controlling access, lazy loading, logging around a heavy object | Adding a proxy just to add a layer — costs readability |

**Facade red flag:** A facade that does nothing but delegate every call 1:1 to the subsystem is not a
facade — it is noise. A facade must reduce complexity, not just rename it.

---

## GoF Behavioral Patterns

| Pattern | Use when | Do NOT use when |
|---------|----------|-----------------|
| **Chain of Responsibility** | Multiple handlers may process a request; handlers decided at runtime | Fixed, known handler — just call it directly |
| **Command** | Parameterizing requests, supporting undo/redo, queuing operations | One-shot action with no history requirement |
| **Iterator** | Traversing a collection without exposing its internals | Built-in language iteration is sufficient |
| **Mediator** | Many objects communicate in complex ways; reducing coupling | Only 2 objects interact — direct reference is clearer |
| **Memento** | Capturing and restoring state without violating encapsulation | State is trivial to reconstruct — store the delta instead |
| **Observer** | One-to-many change propagation; decoupling publisher from subscribers | Order of notification matters and is not guaranteed |
| **State** | Object behavior changes significantly based on internal state | 2–3 boolean flags manage state — use an enum or if/else |
| **Strategy** | Interchangeable algorithms; avoiding conditionals based on type | Only one algorithm exists now and extensibility is not needed |
| **Template Method** | Skeleton algorithm with steps that subclasses fill in | Steps are not stable — composition is more flexible |
| **Visitor** | Adding operations to an object hierarchy without modifying it | The hierarchy changes frequently — each change breaks all visitors |

**Strategy vs inheritance:** When behavior varies, prefer Strategy (composition) over subclassing.
Inheritance for code reuse — not for behavior variation — is a design smell.

**Observer red flag:** If handler A must always run before handler B, Observer is the wrong tool.
Use a pipeline or Chain of Responsibility with explicit ordering instead.

---

## Modern / Architectural Patterns

### Repository
- **Purpose:** Abstract persistence behind a domain-aligned interface.
- **Correct:** `UserRepository.find_by_email(email)` — returns domain objects, hides SQL/ORM.
- **Violation:** Returning `Row`, `QuerySet`, or ORM objects — persistence leaks into domain.
- **Violation:** Repository methods that accept SQL strings or filter dicts — abstraction is broken.

### Service Layer
- **Purpose:** Orchestrate use cases; coordinate domain objects and repositories.
- **Correct:** Service calls domain methods, commits transactions, raises domain errors.
- **Violation:** Business rules living in the service instead of in the domain — Anemic Domain Model.
- **Violation:** Service directly manipulating domain object internals (bypassing domain methods).

### CQRS (Command Query Responsibility Segregation)
- **Purpose:** Separate write model (commands) from read model (queries) when they diverge significantly.
- **Use when:** Read model needs denormalized projections; write model is normalized.
- **Do NOT use:** When both models are identical — CQRS adds 2× the infrastructure for no gain.

### Hexagonal Architecture (Ports & Adapters)
- **Purpose:** Isolate the domain from all external systems (DB, HTTP, messaging).
- **Port:** An interface defined by the domain (what the domain needs).
- **Adapter:** A concrete implementation wiring a port to a specific technology.
- **Violation:** Domain code importing from infrastructure packages.

### Unit of Work
- **Purpose:** Group multiple repository operations into an atomic transaction.
- **Correct:** One `commit()` at the service layer end.
- **Violation:** Committing inside repositories — callers lose transaction control.

### Event Sourcing
- **Purpose:** Store the history of events; reconstruct state by replaying them.
- **Use only when:** Audit trail is a hard requirement AND projections diverge from the write model.
- **Cost:** High operational complexity — justify explicitly before adopting.

---

## Anti-Patterns — Always Flag

| Anti-pattern | Description | Severity |
|---|---|---|
| **God Object / God Class** | One class with dozens of responsibilities and thousands of lines | CRITICAL |
| **Anemic Domain Model** | Domain objects are data bags (only getters/setters); all logic lives in services | HIGH |
| **Premature Abstraction** | Pattern introduced before ≥ 3 real use cases justify it | MEDIUM |
| **Layer Bypass** | Controller or CLI calls repository directly, skipping domain and service | HIGH |
| **Shotgun Surgery** | A single conceptual change requires touching N unrelated files | HIGH |
| **Feature Envy** | Method uses another class's data more than its own | MEDIUM |
| **Parallel Inheritance Hierarchies** | Adding a subclass to A forces adding a subclass to B | HIGH |
| **Speculative Generality** | Abstract hook points with zero current implementations | MEDIUM |
| **Magic Numbers / Strings** | Unexplained literals scattered through the codebase | LOW |

---

## OOP Principles — SOLID

### S — Single Responsibility Principle
A class should have **one reason to change**.
- **Signal:** Class name contains "And", "Manager", "Handler", "Util", "Helper" (catch-all names).
- **Signal:** Method count > 15 or class line count > 300.
- **Fix:** Split into focused classes with clear domain names.

### O — Open/Closed Principle
Open for extension, closed for modification.
- **Signal:** Adding a new case requires modifying existing conditionals: `if type == "new_type": ...`
- **Fix:** Introduce Strategy, Factory, or Registry so new cases extend without modifying existing code.

### L — Liskov Substitution Principle
Subtypes must be substitutable for their base types without breaking correctness.
- **Violation:** Subclass throws `NotImplementedError` for a base method.
- **Violation:** Subclass narrows accepted input types or widens returned output types.
- **Fix:** Redesign the hierarchy; favor composition if substitutability cannot be guaranteed.

### I — Interface Segregation Principle
Clients should not depend on interfaces they do not use.
- **Signal:** Interface with 10+ methods; implementors return `NotImplementedError` for most.
- **Fix:** Split into focused, role-specific interfaces.

### D — Dependency Inversion Principle
High-level modules depend on abstractions, not concretions.
- **Signal:** Service instantiates its own dependencies with `ConcreteClass()` directly.
- **Signal:** `import` of an infrastructure module inside a core or feature module.
- **Fix:** Inject dependencies through constructor; depend on protocols/interfaces.

### Inheritance vs Composition
- **Use inheritance** for genuine IS-A relationships with polymorphic behavior.
- **Use composition** for HAS-A relationships and for sharing behavior.
- **Red flag:** Inheriting from a class to reuse 1–2 methods — extract those methods instead.
- **Red flag:** Deep inheritance chains (> 3 levels) — favor flat composition.

---

## Scalability Principles for Large Codebases

These apply when designing architecture for projects that will have many developers over time.

1. **Strict layer boundaries** — No layer may import from a layer above it. Violations compound under
   parallel development and create merge conflicts that are hard to diagnose.

2. **Explicit composition root** — One place where all dependencies are wired. If dependencies are
   instantiated in multiple places, the system becomes unpredictable under growth.

3. **Small, named modules** — Prefer many small modules with clear names over large generic ones.
   Developers working in parallel are less likely to conflict on small, focused files.

4. **No shared mutable state** — Global or class-level mutable state is the primary source of
   concurrency bugs and non-deterministic test failures.

5. **Dependency direction must be consistent** — In a 4-layer architecture (CLI → Features → Core ←
   Infrastructure), any import that crosses this graph in the wrong direction is CRITICAL.

6. **Stable abstractions** — Core interfaces change rarely. If a core interface changes frequently,
   the domain model is wrong — fix the model, not the callers.

---

## Evaluation Protocol

When you encounter a pattern during DRAFT or REVIEW:

1. **Identify** — What pattern is being used (or attempted)?
2. **Verify the problem exists** — Does the problem the pattern solves actually exist here?
3. **Verify the contract** — Is the implementation faithful to the pattern's structure?
4. **Verify simplicity** — Is there a simpler solution that covers the same need?
5. **Classify:**
   - `CORRECT` — Pattern applied appropriately and correctly
   - `OVER-ENGINEERED` — Pattern adds complexity without solving a real problem
   - `VIOLATED` — Pattern is attempted but breaks its own contract
   - `MISSING` — A pattern would solve a real problem that is currently handled by ad-hoc code
   - `ANTI-PATTERN` — An actively harmful pattern that should be removed

Always include file:line when reporting a finding.

---

## References

- **"Design Patterns"** — Gamma, Helm, Johnson, Vlissides (GoF)
- **"Refactoring to Patterns"** — Joshua Kerievsky
- **"Clean Architecture"** — Robert C. Martin
- **"Patterns of Enterprise Application Architecture"** — Martin Fowler
- **"A Philosophy of Software Design"** — John Ousterhout
- SOLID principles: Robert C. Martin (Uncle Bob)
