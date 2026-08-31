# Deepening

How to deepen a cluster of shallow modules safely, given its dependencies. Assumes the
vocabulary in `SKILL.md`: module, interface, seam, adapter.

## Dependency categories — the category decides how the deep module is tested

1. **In-process** — pure computation, in-memory state, no I/O. Always deepenable: merge and test through the new interface directly; no adapter.
2. **Local-substitutable** — dependencies with local test stand-ins (in-memory store, tmp filesystem). Deepenable when the stand-in exists; the seam stays internal, no port at the external interface.
3. **Remote but owned** — your own services across a boundary. Define a port at the seam; logic lives in one deep module; transport is an injected adapter (production) beside an in-memory adapter (tests).
4. **True external** — third-party services you don't control. The deep module takes the dependency as an injected port; tests provide a mock adapter.

## Seam discipline

- One adapter = a hypothetical seam; two = a real one. A single-adapter port is indirection (this repo's ADR 0001 retired exactly that class).
- Internal seams stay private to the implementation and its tests — never exposed through the interface because a test happens to use them.

## Testing: replace, don't layer

- Old unit tests on the shallow modules become waste once interface-level tests exist — delete them (a `qa-engineer` pruning verdict, per `dadaia-test-stewardship`).
- New tests live at the deepened module's interface and assert observable outcomes, never internal state.
- A test that must change when the implementation changes was testing past the interface.
