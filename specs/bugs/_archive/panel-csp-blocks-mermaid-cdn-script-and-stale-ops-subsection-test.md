---
name: panel-csp-blocks-mermaid-cdn-script-and-stale-ops-subsection-test
status: Open
severity: MEDIUM
reported: 2026-06-26
surface: features/panel (index.py inline mermaid script + CSP) / tests/e2e/panel (ops-tab OPS-02) / ci preflight scope
session_id: null
---

**Symptom:** The GitHub Actions "E2E panel (Playwright)" job failed on
`feature/v0.1.25` (run 28246442927) with 5 failing tests, all from two root
causes shipped in v0.1.24 and missed at closure:

1. **CSP violation (4 tests):** OPS-06, E2E-GUARD-02, E2E-SRV-01, E2E-TAB-04 each
   reported exactly one console error:
   `Executing inline script violates the following Content Security Policy
   directive 'script-src 'self' 'sha256-GRTndW6m…' 'sha256-u9QKVWf5…''. …
   a hash ('sha256-5YRJUPM6Z2462aK6lDuJhdzswItM+S6oQ+jQQelGOOI=') … is required.
   The action has been blocked.`
   The blocked hash is the inline `<script type="module">` mermaid-hydration
   block in `dadaia_workspace/features/panel/views/index.py` (added in v0.1.24
   cba8c22 for the dadaia-workflows catalog). Its sha256 was never added to the
   panel CSP allowlist (`_CSP_SCRIPT_HASH_*` in `handler.py`). Worse, the script
   is **doubly dead**: even if allowlisted, it does `import('https://cdn.jsdelivr.net/…mermaid…')`,
   and the panel CSP `script-src` is `'self'` + hashed inline only — it does not
   permit any external CDN origin, so the import can never execute. The panel is
   loopback/offline by design and already renders a server-rendered SVG DAG per
   workflow; client-side mermaid hydration is fundamentally incompatible with the
   panel's security posture and its existing no-CDN/no-mermaid invariant tests
   (E2E-TAB-06, workflows-tab "does not load Mermaid").

2. **Stale E2E assertion (1 test):** OPS-02 asserted the Ops sub-section at index
   2 is `ops-subsection-kanban`, but v0.1.24 inserted `ops-subsection-dadaia-workflows`
   between `workflows` and `kanban`, making the live order
   `agents → workflows → dadaia-workflows → kanban`. The test was not updated.

**Repro:**
```
cd repos/dadaia-workspace/tests/e2e/panel
PANEL_WEB_SERVER_COMMAND="<ws>/.dadaia/.venv/bin/python -m dadaia_workspace.cli.main panel --port 4999 --no-open" \
  npx playwright test ops-tab.spec.ts response-guard.spec.ts servers-tab.spec.ts tab-navigation.spec.ts
# pre-fix: 5 failures (OPS-02 mismatch + 4 CSP console errors)
```

**Expected:** A pushed branch that passes the pre-push gate should also pass the
GitHub Actions panel-e2e job. The panel must serve no CSP-violating inline
script, and E2E assertions must track the live panel layout.

**Process gap (the reason this reached `main`-bound CI red):** the pre-push CI
gate / `dadaia ci preflight` runs only `ruff format --check`, `ruff check`,
`mypy --strict`, and `pytest` — it does **not** run the Playwright panel E2E
suite. So a panel regression passes the local preflight and the pre-push gate and
is only caught by the GitHub Actions `E2E panel (Playwright)` job after the push.
Closure (qa+security APPROVE) likewise did not run the panel E2E job. Consider
either (a) adding a panel-e2e step to `dadaia ci preflight` (gated on node/browser
availability), or (b) documenting that panel E2E is CI-only and must be run by qa
before any release that touches `features/panel/`.

**Fix applied (this session):**
- Removed the dead inline `<script type="module">` mermaid-hydration block from
  `index.py` (kept the server-rendered SVG DAG and the `<pre class="mermaid">`
  raw-source block, which matches the memory-atom rendering convention). No CSP
  hash added — the script is gone, not allowlisted.
- Updated `tests/e2e/panel/ops-tab.spec.ts` OPS-02 to assert the 4-subsection
  order `agents → workflows → dadaia-workflows → kanban`.
- Verified: full local panel E2E suite 61/61 green; `dadaia ci preflight` PASS.

**Notes:** The operator explicitly wanted mermaid in the dadaia-workflows catalog
(`dadaia_catalog.py:224`). That intent is preserved as the raw mermaid source in
a styled `<pre>` plus the canonical server-rendered SVG. If true client-side
mermaid rendering is later desired, it must be a **self-hosted** bundle served
from `'self'` (no CDN) with its inline bootstrap hash added to the CSP allowlist —
tracked separately, not in this hotfix.
