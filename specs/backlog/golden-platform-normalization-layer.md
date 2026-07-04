---
name: golden-platform-normalization-layer
status: candidate
opened: 2026-07-04
owner: project-manager (curates)
source: v0.1.58 closure backlog return (three-round golden CI saga — security reviewer meta-observation)
intents:
  - subject: { kind: code, ref: "tests/unit/infrastructure/test_install_target_goldens.py#_norm_path_line" }
    change: "consolidate the per-test golden-normalization helpers into ONE shared platform-invariance layer for golden capture. v0.1.58's W1 goldens leaked THREE environmental-state classes that turned CI red one round at a time on the -cross matrix — (1) host denylist state read from cwd (60f42904), (2) directory-iteration order Windows vs Linux (c02e74f6), (3) OS-phrased exec-probe text exited-127 vs WinError-193 (1dadfafe) — each fixed test-only with a bespoke helper (_norm_path_line, _sort_line_lists, _canon_env_line). Extract these into a single reusable platform-invariance module (host-state canonicalization + sorted-multiset report-list locks + OS-phrase canonicalization) so a new byte-golden is platform-invariant BY CONSTRUCTION, not by re-discovering each leak class in a fresh CI round. Extends the v0.1.55 golden-authoring law (specs/memory/quality-assurance.md)."
---

# BACKLOG — Consolidated golden platform-normalization layer

**Priority:** MEDIUM. v0.1.58 (R10) shipped only after a **three-round CI saga**: the W1
behaviour goldens leaked three distinct classes of host/OS-environmental state — a host
denylist read resolved from cwd (round 1, `60f42904`), directory-iteration order that differs
Windows-vs-Linux (round 2, `c02e74f6`), and OS-phrased exec-probe text (`exited 127` vs
`[WinError 193]`, round 3, `1dadfafe`). Each was fixed **test-only** (fix-the-consumer-never-
the-golden) with a bespoke, per-test helper.

The security reviewer's meta-observation at ship: three per-round patches to the SAME
golden-capture harness is the signal that the harness needs **one consolidated
platform-invariance layer** — a shared capture-time normalizer (host-state canonicalization +
sorted-multiset report-list locks + OS-phrase canonicalization) that every path/host/OS-bearing
golden runs through — so a new golden is cross-platform-stable by construction instead of
re-discovering each leak class one red CI round at a time. This extends the v0.1.55
golden-authoring law (which covered only platform-variant PATH rendering); v0.1.58 extended the
law's prose in `specs/memory/quality-assurance.md`, and this item tracks the **code**
consolidation of the helpers behind it.

**Anchor:** the v0.1.58 golden helpers in
`tests/unit/infrastructure/test_install_target_goldens.py` (`_norm_path_line`,
`_sort_line_lists`, `_canon_env_line`) + the v0.1.55 golden-authoring law.
