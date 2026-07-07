---
name: frontend-component-architecture
description: >
  Use this skill when designing or refactoring the component architecture of a
  browser UI — component decomposition, state placement, props contracts,
  hooks/effects discipline, and rendering performance for React and peer
  component frameworks. Shipped by the frontend-design plugin pack; owned by
  frontend-engineer.
---

# Skill: frontend-component-architecture

The component-architecture protocol for the `frontend-design` pack. `frontend-engineer` uses
it when the task is *structural* — decomposing a UI into components, placing state, defining
props contracts, or fixing rendering performance — as opposed to styling fidelity, which the
`browser-frontend-implementation` skill owns. Written against React idioms; the principles
map to peer component frameworks (Vue, Svelte, and similar).

## When to use

- Breaking a design spec into a component tree before writing markup.
- Deciding where state lives and how data flows between components.
- Defining or reviewing a component's props contract.
- Diagnosing re-render storms, effect loops, or slow interaction paths.

## 1. Decomposition

| Rule | Detail |
|---|---|
| One responsibility | A component renders one concept from the design spec; if its name needs "and", split it. |
| Container/presentational split | Data fetching and orchestration live in containers; leaf components are pure render targets of their props. |
| Composition over configuration | Prefer `children`/slots over an ever-growing boolean-prop matrix; a component with many mode flags is several components. |
| Match the design system | Component boundaries follow the design spec's anatomy — one spec'd component maps to one implemented component, not a soup of divs. |
| Colocation | A component's styles, tests, and subcomponents live next to it; shared pieces are promoted only on the second consumer, not speculatively. |

## 2. State placement

Decide where each piece of state lives, in this order:

1. **Derived?** If it can be computed from props/other state, compute it — never store it.
2. **Local:** used by one component → component state.
3. **Lifted:** shared by siblings → nearest common ancestor, passed down as props.
4. **Context:** genuinely cross-cutting (theme, session, locale) → context/provider; keep
   contexts small and split by change-frequency so consumers don't re-render on unrelated
   updates.
5. **External store / URL:** server-cache state belongs to a data-fetching layer; state that
   should survive navigation or be shareable belongs in the URL.

Server state is not client state: cache, revalidate, and reflect loading/error explicitly —
never copy fetched data into local state "to be safe".

## 3. Props contracts

- Explicit types on every exported component's props and return value (TS strict where the
  project uses TS).
- Props express **what**, not **how**: pass data and callbacks, not imperative instructions.
- No prop drilling beyond ~2 levels — restructure with composition or context instead.
- Stable identities across renders: memoize callbacks/objects passed to memoized children;
  never create fresh inline objects in hot paths.
- Events flow up via callbacks, data flows down via props — one direction, no back-channel
  mutation of parent state.

## 4. Hooks and effects discipline

| Rule | Detail |
|---|---|
| Effects are for synchronization | With something *outside* the render (DOM APIs, subscriptions, timers) — not for deriving state or reacting to prop changes that a render expression already handles. |
| Honest dependency arrays | List every dependency; fix the design rather than suppressing the lint rule. |
| Cleanup always | Every subscription/timer/listener registered in an effect is removed in its cleanup. |
| Custom hooks own a concern | Extract reusable stateful logic into a named hook with a typed return; keep components declarative. |
| No render side effects | Rendering is pure; mutations happen in handlers and effects only. |

## 5. Rendering performance

- Measure before optimizing — use the framework's profiler; do not sprinkle memoization blind.
- Keys are stable and identity-bearing; never an array index on reorderable lists.
- Split heavy routes/components with lazy loading; keep the initial bundle lean.
- Virtualize long lists; paginate rather than render thousands of nodes.
- Keep expensive work off the main thread or debounced; interaction latency is a design
  requirement, not a nice-to-have.

## Guardrails

| Rule | Detail |
|---|---|
| Styling fidelity | Tokens, accessibility gates, responsive strategy, and the preview loop live in `browser-frontend-implementation` — this skill owns structure, that one owns fidelity. |
| Design authority | Component anatomy follows the design spec; visual decisions belong to `design-specialist`. |
| No backend | Server/API code belongs to `software-engineer`; contract mismatches go back via PM. |
| No E2E ownership | Component/unit tests are yours; the E2E suite belongs to `qa-engineer`. |
| Handoff | Emit handoff JSON via `dadaia-handoff-emitter` under `.dadaia/handoff/<context>/` after the task. |
