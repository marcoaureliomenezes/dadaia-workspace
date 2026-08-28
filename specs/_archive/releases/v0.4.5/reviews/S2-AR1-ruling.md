# AR-1 — Ruling: the atomic-write primitive's home (T-045-11)

**Reviewer:** software-architect · **Date:** 2026-08-25 · **Release:** v0.4.5 · **Task:** T-045-11
**Subject:** SPEC D5 (`specs/releases/v0.4.5/SPEC.md:100–109`) / FR2 (`SPEC.md:251–285`) / AR-1 (`SPEC.md:631`)

## Verdict

**UPHOLD D5.** `core/atomic_write.py` is the correct and only legal home.
**Hooks duplicate required: NO** — the D5 fallback is not taken.

---

## Adjudication 1 — the no-cross-feature rule vs. the core file-I/O ratchet

**The consumer set spans three layers.** The eleven writers FR2 consolidates live in
`features/` (`features/migrate/frontmatter_keys.py:125`, `features/specs/doctor_structural.py:481`,
`features/spec_context/session_identity.py:112`, `features/spec_context/presence.py:95`,
`features/migrate/state_v2.py`, two inline in `features/import_/service.py`), in
`infrastructure/` (`infrastructure/public_assets_common.py:119`,
`infrastructure/json_agent_model_policy_store.py:236,239`), and in `hooks/`
(`hooks/_common.py:231`). The import-boundary contracts in `setup.cfg` rule out every
non-`core` home:

- `features-no-cross-feature` (`setup.cfg:174`, independence contract) — a feature-hosted
  home would add forbidden sibling edges from every other consuming feature.
- `features-no-infrastructure` (`setup.cfg:49`) — an infrastructure-hosted home would add
  new `features → infrastructure` edges to a capped, ratchet-down ignore list
  (`setup.cfg:22–29`; pinned in `tests/contract/test_import_linter_ignore_cap.py`).
- `infrastructure-no-upper-layers` (`setup.cfg:137`) — a feature- or hook-hosted home is
  unreachable from the two infrastructure consumers.
- `core-no-upper-layers` (`setup.cfg:126`) — `core` is the bottom layer; every consumer
  (`features`, `infrastructure`, `cli`, `hooks`) holds a legal downward edge to it.

`core/` is the unique intersection. This is byte-for-byte the `core/specs_repair`
precedent: its docstring (`dadaia_workspace/core/specs_repair.py:5–12`) states it exists
so "BOTH repair surfaces … share one home without a forbidden sibling edge. Layering: a
pure `core` leaf — stdlib only, no upward import." D5 quotes that precedent accurately —
**architecture-fidelity gate: PASS.**

**The ratchet is not re-opened — it is exercised as designed.** The ratchet
(`tests/contract/test_core_file_io_purity.py`, architect ruling A9: *GUARD, not
relocation*) exists to stop file I/O drifting into `core/` **by accident**; its own
failure message (`test_core_file_io_purity.py:114–116`) prescribes the deliberate path:
add the stem to `_AUTHORIZED_STEMS` **and** record the architecture rationale. The
"shared-mutable-helper hole" the ratchet guards is stateful convenience helpers hiding
coupling; `atomic_write` is a stateless, parameterized, stdlib-pure function with no
module-level mutable state — no hidden coupling channel exists.

**The bug history settles the duplication question.** The v0.4.4-era reading — "a shared
helper lives inside each feature" — is precisely what produced eleven hand-kept copies
that **diverged**: per the bug record (`specs/bugs/bugs.jsonl`, `reported`
2026-08-24T04:34:58Z), 6 of 8 named writers cleaned their temp file on injected
`os.replace` failure and 2 (`hooks/_common.py:atomic_write_text`,
`infrastructure/public_assets_common.py:_atomic_write_text`) leaked it forever. Divergent
copies of a correctness-critical primitive are the structural cause; per-site patching of
the two leakers would have been a symptom patch (refused in D4, correctly). FR2 is
deletion-shaped (11 → 1, net-negative LOC per A2.6). **Root-cause gate: PASS.**

## Adjudication 2 — the hooks-never-import-container latency law

**The law** (`specs/memory/architecture.md:80–86`): hooks are *sanctioned direct
importers* of `core` — "no hook imports `container`", pinned by an attesting
import-surface test; the 2.25s → 0.46s hook-load win came from cutting the
composition-root graph, not from banning `core` edges.

**Current posture of the call site.** `hooks/_common.py:27–28` already imports
`dadaia_workspace.core.platform` and `dadaia_workspace.core.session_env`. Their
transitive closure is pure stdlib (`platform.py`: `sys`, `tempfile`, `dataclasses`,
`pathlib`; `session_env.py`: `os`, `re`), and `core/__init__.py` carries zero imports,
so a `core` submodule import drags in nothing else. The hooks → core edge is already
paid on every gated tool call.

**Consequence.** Importing a stdlib-pure `core/atomic_write.py` adds one leaf module to
an already-warm import path — zero container, zero features, zero infrastructure,
guaranteed transitively by `core-no-upper-layers` (`setup.cfg:126`) under `lint-imports`.
The latency posture is preserved by construction. **No sanctioned import-light duplicate
in `hooks/_common` is required**; taking the fallback would recreate exactly the
two-divergent-copies shape the superseded bug documents, inside the very file that
carried one of the leakers.

## Conditions binding T-045-12 (and T-045-13/14)

1. **Stdlib-pure, zero package-internal imports.** `core/atomic_write.py` imports only
   the stdlib (`os`, `uuid`/`tempfile`, `pathlib`, `typing`) — no `dadaia_workspace.*`
   import, not even a `core` sibling. This is the fact Adjudication 2 rests on; a later
   internal import invalidates this ruling and must return to AR review.
2. **Stateless.** No module-level mutable state, no config global, no caching.
3. **Ratchet declaration.** Add stem `atomic_write` to `_AUTHORIZED_STEMS` in
   `tests/contract/test_core_file_io_purity.py` with an inline rationale citing this
   ruling (A2.5: "exactly one entry, with its rationale on the entry"). The matching
   `specs/memory/architecture.md` "Core file-I/O authorized set" update (line 259 set)
   is MEMORY-class and lands via `product-engineer` at CLOSURE, citing AR-1.
4. **No new accepted edge.** `lint-imports --config setup.cfg --no-cache` green with the
   ignore-edge cap unchanged (A2.5); all 11 consumer switches are plain downward
   `→ core` edges needing zero `ignore_imports`.
5. **Temp cleanup on every failure path, every parameter combination** (A2.3), battery
   re-pointed **before** any writer is deleted (D7 expand → switch → contract).
6. **No lingering aliases.** The contract step deletes all eight named writers including
   `hooks/_common.atomic_write_text` — no re-export shim that lets the old names survive;
   A2.2's scan-derived census is the proof.

## Bug-surface axis (FR24)

**Reduced.** Eleven divergent implementations of one correctness contract collapse to
one; the temp-leak class (`two-atomic-writers-leak-temp-file-on-injected-os-replace-failure`,
superseded 2026-08-25T01:47:10Z) becomes structurally impossible rather than
per-site-patched, and the A2.2 census blocks regrowth. Evidence: the 6-vs-2 behavioral
divergence recorded in the bug's `symptom` field is exactly the failure mode a single
primitive cannot exhibit.

## Gate record

| Gate | Verdict |
|---|---|
| Root-cause gate | **PASS** — FR2 fixes the divergence class, not the two leak sites |
| Architecture-fidelity gate | **PASS** — D5's layer claims match `setup.cfg` contracts and the `specs_repair` precedent verbatim |
