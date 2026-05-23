---
name: frontend-implementation-quality
description: Objective implementation gates for frontend-engineer browser work, including TDD, accessibility, responsiveness, design tokens, performance, and verification.
---

# Frontend Implementation Quality

Objective implementation quality gates for browser-facing code authored by `frontend-engineer`.

---

## Purpose

This skill defines the non-negotiable quality gates that every frontend implementation must pass before a task is marked `[x]`. Gates are objective and measurable — not design judgment (which belongs to `design-specialist`). Referencing this skill at the start of a task establishes the acceptance bar before any code is written.

---

## TDD protocol

Red-green-refactor in strict order. No skipping the red phase.

| Phase | What happens | Gate |
|---|---|---|
| Red | Write the test. Run it. It MUST fail. | If the test passes immediately, the test is wrong — fix it before writing production code. |
| Green | Write the minimum production code to make the test pass. | Only the failing test's requirement. No speculative code. |
| Refactor | Clean up duplication and naming without breaking green. | Run tests after every refactor step. |

A task that begins by writing production code before a failing test violates TDD. Stop and reorder.

---

## TypeScript strict mode

Every TypeScript file in a browser-facing project must compile under:

```json
{
  "strict": true,
  "noUncheckedIndexedAccess": true
}
```

- `any` is forbidden without an explicit justification comment: `// justification: <reason>`.
- `tsc --noEmit` must exit 0 before a task is marked done.
- Type assertions (`as Foo`) require a comment explaining why the assertion is safe.

---

## Component test requirements

Every component must have at least one unit test covering its primary render path.

| Requirement | Detail |
|---|---|
| Test runner | Vitest or Jest |
| Component testing | React Testing Library; query by role, label, or accessible name — never by class or test-id unless no semantic alternative exists |
| User interaction | `@testing-library/user-event` for clicks, typing, keyboard events |
| Coverage | `vitest run --coverage` or equivalent; no hard minimum % but every component file must appear in the report |
| Test location | Co-located (`ComponentName.test.tsx`) or in `__tests__/`; not in the E2E directory |

---

## Accessibility — WCAG 2.1 AA minimum

All browser-facing output must meet WCAG 2.1 AA as a baseline. AA failures are blocking.

| Gate | Requirement |
|---|---|
| Contrast ratio (normal text) | >= 4.5:1 |
| Contrast ratio (large text >= 18pt or 14pt bold) | >= 3:1 |
| Contrast ratio (UI components, icons) | >= 3:1 |
| Keyboard navigation | All interactive elements reachable and operable via keyboard alone |
| Focus indicator | Visible, high-contrast; never `outline: none` without a custom visible replacement |
| Screen reader labels | Every interactive element has an accessible name (via text content, `aria-label`, or `aria-labelledby`) |
| Touch targets | Minimum 44x44px |
| Motion | Respect `prefers-reduced-motion`; no auto-playing animations that cannot be paused |

---

## Responsive breakpoints

Implement and test at the three canonical breakpoints:

| Name | Value | Notes |
|---|---|---|
| mobile | 360px | Minimum supported width |
| tablet | 768px | Medium breakpoint |
| desktop | 1280px | Standard wide layout |

Mobile-first: default styles target 360px; wider layouts use `min-width` media queries.

---

## Performance budget

| Metric | Budget | Source |
|---|---|---|
| LCP (Largest Contentful Paint) | <= 2.5s | Core Web Vitals |
| CLS (Cumulative Layout Shift) | <= 0.1 | Core Web Vitals |
| INP (Interaction to Next Paint) | <= 200ms | Core Web Vitals |
| Lighthouse Performance score | >= 90 | Measured on staging |
| Lighthouse Accessibility score | >= 90 | Measured on staging |

If the task introduces a new route or heavy component, run a Lighthouse audit before closing the task. Capture the score in the implementation report.

---

## OWASP frontend checklist

| OWASP item | Rule |
|---|---|
| A03 — Injection | No `innerHTML` with user-supplied content; use `DOMPurify.sanitize` if HTML injection is unavoidable |
| A03 — Injection | Input sanitization on the client; never assume the server re-validates |
| A05 — Security Misconfiguration | CSP headers required; no inline `<script>`, no `eval()`, no `Function()` constructor |
| A07 — Auth failures | No auth tokens in `localStorage` (XSS risk); use httpOnly cookies set by backend |
| A07 — Auth failures | No sensitive data logged to console or analytics |
| A08 — Software and Data Integrity | Third-party scripts pinned with SRI hash if from CDN |
| A10 — Server-Side Request Forgery | Image/iframe `src` from API: allowlist domains; never echo arbitrary URLs |
| A10 — External links | `rel="noopener noreferrer"` on every `target="_blank"` link |

A task that introduces any OWASP violation is blocking. Stop, escalate, and fix before closing.

---

## Guardrails

- These gates apply to `frontend-engineer` only. `design-specialist` does not invoke this skill.
- Do not relax any gate for deadline reasons without explicit operator approval recorded in the implementation report.
- Do not mark a task `[x]` if `tsc --noEmit` fails, any test is red, or any OWASP blocking issue is open.
- Do not substitute manual browser testing for automated tests on the primary render path.
