# Tasks: Release — dadaia-workspace-brand-identity-v1

> **Status:** Aprovado
> **Approved:** 2026-05-17
> **Approved-by:** operator
> **Release ID:** dadaia-workspace-brand-identity-v1
> **Phase:** TASKS
> **Owner:** frontend-engineer (executor on Aprovado)
> **Created:** 2026-05-17
> **SPEC:** `specs/releases/dadaia-workspace-brand-identity-v1/SPEC.md` (Status: Aprovado)
> **PLAN:** `specs/releases/dadaia-workspace-brand-identity-v1/PLAN.md` (Status: Aprovado)

> Marker convention (`dadaia-task-manager`): `[ ]` OPEN → `[-]` IN PROGRESS → `[x]` DONE.
> All tasks below are OPEN. Implementation may begin — reserve via `dadaia-task-manager` protocol.

---

## Phase 1 — Paleta canônica + tokens CSS

- [ ] **T-BR-01** — Add `PALETTE` constant in `dadaia_workspace/features/panel/views/_assets.py`.
  - Constant: `PALETTE: dict[str, str] = {"accent": "#9cddc8", "accent_secondary": "#bfd8ad", "warning_bg": "#ddd9ab", "alert": "#f7af63", "cost": "#633d2e"}`.
  - Top of file, with a docstring linking to `specs/releases/dadaia-workspace-brand-identity-v1/SPEC.md`.
  - Files: `dadaia_workspace/features/panel/views/_assets.py`.
  - Parallel-safe: yes (no deps).

- [ ] **T-BR-02** — Update PANEL_CSS tokens in `_assets.py`.
  - Update `--color-accent: #7ec8e3` → `#9cddc8`.
  - Update `--color-primary-ring: #7ec8e3` → `#9cddc8`.
  - Update `--color-primary-bg: #f0faff` → `#f0fbf7`.
  - Add `--color-accent-secondary: #bfd8ad`.
  - Add `--color-warning-bg: #ddd9ab`.
  - Add `--color-alert: #f7af63`.
  - Add `--color-cost: #633d2e`.
  - Each entry comments the previous value (when applicable) and references SPEC § Mapeamento.
  - Files: `dadaia_workspace/features/panel/views/_assets.py`.
  - Parallel-safe: yes after T-BR-01 (uses the constant indirectly via comments; can be done in same commit).

## Phase 2 — Logo rinoceronte SVG

- [ ] **T-BR-03** — Create `dadaia_workspace/features/panel/views/assets/logo-rhino-24.svg`.
  - viewBox `0 0 24 24`, ≤ 3 elementos, `currentColor` em todos os `fill`/`stroke`.
  - Silhueta plana de cabeça de rinoceronte de perfil, olhando para a direita, com chifre único.
  - No hex hardcoded.
  - Files: `dadaia_workspace/features/panel/views/assets/logo-rhino-24.svg`.
  - Parallel-safe: yes (isolated artifact). May require operator visual review before merging.

- [ ] **T-BR-04** — Create `dadaia_workspace/features/panel/views/assets/logo-rhino-16.svg`.
  - viewBox `0 0 16 16`, same style as 24×24 but with simplified paths.
  - `currentColor` em todos os elementos.
  - Files: `dadaia_workspace/features/panel/views/assets/logo-rhino-16.svg`.
  - Parallel-safe: yes after T-BR-03 (reuses silhouette).

- [ ] **T-BR-05** — Load SVGs at module init in `_assets.py`.
  - Module-level constants `LOGO_RHINO_24` and `LOGO_RHINO_16` via `pathlib.Path(__file__).parent.joinpath("assets/logo-rhino-24.svg").read_text(encoding="utf-8")`.
  - Files: `dadaia_workspace/features/panel/views/_assets.py`.
  - Parallel-safe: yes after T-BR-03 + T-BR-04.

- [ ] **T-BR-06** — Insert logo in topbar in `views/index.py`.
  - Before `.topbar-wordmark`: render `LOGO_RHINO_24` inline as raw HTML inside `<span class="topbar-logo" aria-hidden="true">{LOGO_RHINO_24}</span>`.
  - PANEL_CSS adds `.topbar-logo { color: var(--color-cost); display: inline-flex; align-items: center; margin-right: 0.5rem; }`.
  - Files: `dadaia_workspace/features/panel/views/index.py`, `dadaia_workspace/features/panel/views/_assets.py` (PANEL_CSS).
  - Parallel-safe: no — must come after T-BR-02 + T-BR-05.

## Phase 3 — Wordmark + tests

- [ ] **T-BR-07** — Update `.topbar-wordmark` CSS to use `--color-cost`.
  - In PANEL_CSS: `.topbar-wordmark { color: var(--color-cost); ... }` (keep existing spacing/weight).
  - Files: `dadaia_workspace/features/panel/views/_assets.py`.
  - Parallel-safe: yes after T-BR-02.

- [ ] **T-BR-08** — Add `tests/unit/features/panel/test_palette.py`.
  - Assert `PALETTE` has exactly 5 keys with the canonical hex values.
  - Assert no other hex from `PALETTE` is hardcoded in PANEL_CSS outside the token definition rules (regex grep across PANEL_CSS string).
  - Files: `tests/unit/features/panel/test_palette.py`.
  - Parallel-safe: yes after T-BR-01.

- [ ] **T-BR-09** — Add `tests/unit/features/panel/test_contrast.py`.
  - Implement WCAG ratio computation (stdlib, ~10 lines).
  - Assert ratio ≥ 4.5:1 for: `#222` over `#9cddc8`; `#3d3600` over `#ddd9ab`; `#222` over `#bfd8ad`.
  - Assert ratio ≥ 7:1 for `#633d2e` over `#ffffff` (AAA target for cost token).
  - Assert `#9cddc8` and `#f7af63` are NOT used as text color anywhere in PANEL_CSS (regex search for `color: #9cddc8` or `color: #f7af63`).
  - Files: `tests/unit/features/panel/test_contrast.py`.
  - Parallel-safe: yes after T-BR-02.

- [ ] **T-BR-10** — Add `tests/unit/features/panel/test_svg_validity.py`.
  - Parse `LOGO_RHINO_24` and `LOGO_RHINO_16` via `xml.etree.ElementTree.fromstring`.
  - Assert no `fill`/`stroke` attribute matches `/^#[0-9a-fA-F]{3,8}$/` — all must be `currentColor` or `none`.
  - Assert each SVG has ≤ 3 path/circle elements (recursive count).
  - Files: `tests/unit/features/panel/test_svg_validity.py`.
  - Parallel-safe: yes after T-BR-05.

- [ ] **T-BR-11** — Update memory: declare canonical palette in `specs/memory/product.html`.
  - Add a "Brand identity" section with the 5-color palette, mapped tokens, and link to this release SPEC.
  - This is an atomic memory edit (SPEC-DOC-008) — replace, not append.
  - Files: `specs/memory/product.html`.
  - Parallel-safe: yes; must coordinate with any other memory edits in flight.

- [ ] **T-BR-12** — Acceptance pass.
  - All 9 acceptance criteria from SPEC.md green.
  - `dadaia doctor` passes.
  - Operator visually validates panel local with new branding (screenshot captured).
  - Files: ad-hoc validation log in `.dadaia/reports/dadaia-workspace/product-engineer/<ts>-brand-identity-acceptance.html`.
  - Parallel-safe: no — gates CLOSURE.

---

## Parallelization summary

- **Wave A (independent):** T-BR-01, T-BR-02, T-BR-03 (logo desenho).
- **Wave B (after A):** T-BR-04, T-BR-05, T-BR-07, T-BR-08, T-BR-09.
- **Wave C (after B):** T-BR-06, T-BR-10, T-BR-11.
- **Wave D:** T-BR-12.
