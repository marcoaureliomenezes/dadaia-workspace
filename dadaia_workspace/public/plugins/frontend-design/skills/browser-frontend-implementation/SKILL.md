---
name: browser-frontend-implementation
description: >
  Use this skill when implementing or reviewing browser frontend — HTML, CSS,
  and JS/TS/React (or another component framework) — against a design-specialist
  spec. Carries the token-fidelity checklist, accessibility gates, responsive
  strategy, and the dev-server preview loop shared by frontend-engineer
  (implementation) and design-specialist (visual review). Shipped by the
  frontend-design plugin pack.
---

# Skill: browser-frontend-implementation

The shared craft protocol for the `frontend-design` pack. `frontend-engineer` uses it to
implement; `design-specialist` uses the same checklist to review — so the bar the implementer
is held to is the bar the reviewer applies. Reach for it at the start of every browser-frontend
task.

## When to use

- Implementing markup/styles/components from a design spec (`frontend-engineer`).
- Reviewing a UI handoff against the design and the QA screenshot evidence (`design-specialist`).
- Any change that must stay faithful to the design system's tokens and meet accessibility gates.

## 1. Token fidelity — the non-negotiable

The design system (owned by `design-specialist`) is the single source of visual truth.
Implement against tokens, never magic numbers.

| Axis | Rule |
|---|---|
| Colour | Only design-token colours; never a hand-picked hex. Contrast meets WCAG AA. |
| Spacing | Only the documented space scale; no arbitrary pixel gaps. |
| Typography | Only the type scale (size/line-height/weight) from the spec. |
| Radius / elevation | From the token set; consistent across components. |
| Motion | Durations/easings from tokens; honour `prefers-reduced-motion`. |

A value that has no token is a gap in the design spec — return it to `design-specialist` via
PM; do not invent one.

## 2. Accessibility gates (WCAG AA floor)

| Gate | Check |
|---|---|
| Structure | Semantic HTML; one `<h1>` per view; landmarks; labelled controls. |
| Contrast | Text and UI meet AA contrast ratios. |
| Keyboard | Every interactive element reachable and operable by keyboard; logical focus order. |
| Focus | Visible focus indicator; focus trapped correctly in dialogs; restored on close. |
| Motion | Respect `prefers-reduced-motion`; no motion-only information. |
| Semantics | `aria-*` only where native semantics fall short — never as a band-aid over bad markup. |

## 3. Responsive + performance

- Mobile-first; breakpoints from the spec, not improvised. Prefer container/logical queries.
- No main-thread blocking; debounce/throttle expensive handlers; lazy-load heavy routes/assets.
- Framework hygiene: stable list keys, correct effect dependencies, no layout thrash, no
  unnecessary re-renders in hot paths.

## 4. Dev-server preview loop

1. Register the port through the `dev-server-registry` skill **before** opening it — never pick
   a port manually (prevents silent collisions between concurrent agents).
2. Preview the change and self-check against the design report and the gates above.
3. Capture evidence for the handoff; `qa-engineer` owns the E2E/Playwright screenshots used in
   `design-specialist`'s visual review.

## 5. Security (browser surface)

- No secrets/tokens in browser source or bundles — everything client-side ships to the user.
- Escape/encode all rendered user input; no `dangerouslySetInnerHTML` / `v-html` / `innerHTML`
  on unsanitized content (XSS).
- Add Subresource Integrity (SRI) for external scripts; never fetch arbitrary user-supplied URLs
  from the client without an allowlist.

## 6. Codex context adapters (reference, not duplication)

On the Codex runtime, per-session context is injected by the existing runtime adapters — do NOT
restate their protocol here:

| Adapter | Role | Location |
|---|---|---|
| `frontend-ctx` | Injects active release/task, latest design report, and dev-server state for `frontend-engineer` | `public/runtime/codex/frontend-ctx/SKILL.md` |
| `design-ctx` | Injects active context, latest design + QA screenshot reports for `design-specialist` | `public/runtime/codex/design-ctx/SKILL.md` |

Those adapters own the session-start context-gathering steps and their own emit format. This
skill owns the *craft* (tokens, accessibility, responsive, preview, security); the adapters own
the *context injection*. Consult the adapter for your role at session start, then apply this
checklist — the two compose, they do not overlap.

## Guardrails

| Rule | Detail |
|---|---|
| Design authority | Visual decisions (tokens/palette/spacing/type/motion) belong to `design-specialist`. Implement, do not redefine. |
| No E2E ownership | Playwright and browser evidence belong to `qa-engineer`. |
| No backend | Server/API code belongs to `software-engineer`. |
| Handoff | Emit handoff JSON via `dadaia-handoff-emitter` under `.dadaia/handoff/<context>/` after the task. |
