# PLAN — Release `v0.1.18`

> **Status:** Aprovado
> **Release ID:** v0.1.18
> **Owner:** product-engineer
> **Created:** 2026-06-25

## Strategy

Five threads (A–E) with **largely disjoint write sets** so three owners progress in
parallel. The one hard sequencing constraint is **Thread C before/with Thread B**:
`.pi/` is a new workspace-root entry and the `pre_gate` root-whitelist hook blocks new
root dirs, so the hook's `_WHITELIST` must accept `.pi/` before any live `--target pi`
projection write. Constitution (A) and memory (D) are independent of B/C and parallelize
freely. Thread E (pointer README) is trivial and independent.

Apply the architect design doc and the F1–F12 audit fix set **verbatim where given** —
do not re-derive. The constitution amendment text is ready-to-apply (Deliverable 1
blocks 1.1–1.6); the `.pi/` shape + installer wiring contract is Deliverable 2.

## Owners & disjoint write sets (enables parallel `[-]`)

| Owner | Write set (disjoint) | Threads |
|---|---|---|
| product-engineer | `specs/constitution.md`; `specs/memory/**`; `repos/dadaia-pi-workspace/README.md` | A, D-memory, E, CLOSURE |
| ai-engineer | `dadaia_workspace/public/pi/**`; `public/agents/ai-engineer.md`; `public/skills/harness-primitives/**`; `public/rules/{tmp-file-guardrail,bug-registration-guardrail}.md`; `public/data/AGENTS.md`; `public/plugins/sdd-gate.ts`; `public/skills/project-orchestration/**` | B-assets, C-surface, D-surface |
| software-engineer | `infrastructure/public_assets.py`; `infrastructure/public_assets_common.py`; `hooks/root_whitelist.py`; doctor ROOT check; `features/specs/catalog.py`; `lint-memory-atoms.py`; `.dadaia/agentic/manifest.json` (via stage); tests | B-wiring, C-hook, D-tooling |

Because the write sets are disjoint per owner, TASKS.md declares **safe parallel
ownership**: each of the three owners may hold one `[-]` concurrently. Within an owner,
max one `[-]` at a time. The exception is the **B/C dependency** — the live `--target pi`
smoke in B depends on C's hook edit being merged; sequence those.

## Layers affected

- **Public-asset distribution** (`infrastructure/public_assets*.py`) — new `pi` target,
  mirroring OpenCode. The most code-heavy slice; fully testable offline.
- **Hooks** (`hooks/root_whitelist.py` `_WHITELIST`) — additive `.pi/` allow.
- **Specs/memory** (constitution + memory atoms) — documentation of existing reality;
  MUTATING (constitution) + MEMORY-class (atoms, CLOSURE/DEFINITION phase).
- **Public AI-entity surface** (agents/skills/rules/data) — drift fixes, projected via
  `dadaia public stage && install --target all`.
- **Tooling** (`catalog.py` CLI, `lint-memory-atoms.py`) — index.md emission + allowlist.

## Execution order (thread sequencing)

```
              ┌─ Thread A  (constitution)        ── product-engineer  (parallel)
              │
START ────────┼─ Thread D-memory + D-surface     ── product-engineer + ai-engineer (parallel)
              │   + D-tooling (catalog/lint)      ── software-engineer (parallel)
              │
              ├─ Thread C  (root-whitelist hook + rule + AGENTS.md + doctor)  ◄── MUST precede B-smoke
              │        │
              │        ▼
              ├─ Thread B  (public/pi assets + _install_pi wiring + doctor + manifest)
              │        │
              │        ▼
              │   live `--target pi` smoke + re-install (depends on C merged)
              │
              └─ Thread E  (pi-workspace README pointer)  ── product-engineer (independent)

              ▼
   GLOBAL GATES task (ci preflight 4/4 + lint-imports 6/0 + public doctor + specs doctor
                      + live --target pi smoke)
              ▼
   GATE LADDER: qa + security + code review APPROVE
              ▼
   CLOSURE (product-engineer): CLOSURE.md + memory finalization + drift RE-AUDIT + archive
```

- **C is the spine before B's smoke.** B's source-authoring and installer-wiring can be
  written in parallel with C (they touch different files), but the *live projection smoke*
  (`dadaia public install --target pi` actually creating `.pi/`) must run only after C's
  `_WHITELIST` edit is in place — otherwise the gate blocks the write.
- **A and D are independent** of B/C and of each other (disjoint files) — full parallelism.
- **F11 (regenerate index.md) depends on F10** (catalog CLI emitting index.md) — order
  within Thread D-tooling/memory.

## Test strategy (TDD-first for code)

| Area | Test approach (failing test first) |
|---|---|
| Root-whitelist hook (C) | Unit test: a payload writing `.pi/settings.json` is **allowed**; a payload writing a non-whitelisted new root dir is still **blocked**. Add `.pi/` allow case to the existing hook test module. |
| `_install_pi` (B) | Unit test mirroring `_install_opencode` tests: `--target pi` copies `public/pi/` → `.pi/`, writes generated `settings.json`, is idempotent; `--target all` includes `pi`; factory/dispatch total. |
| `public doctor` PI lines (B) | Unit test: doctor emits `[ok] pi:SYSTEM.md` / `[ok] pi:settings.json`; `[drift]`/`[missing]` paths behave like other targets; `[ok] public-privacy` stays green with `public/pi/**` present. |
| Privacy gate (B) | `public/pi/**` contains no private names/paths/IPs — privacy check green (faked content, structurally tested). |
| `catalog.py` index emission (F10) | Unit test: `dadaia memory catalog generate` writes BOTH `catalog.json` and `index.md`; closes bug `memory-catalog-cli-skips-index-md`. Failing test first (asserts index.md written), then fix. |
| `lint-memory-atoms.py` allowlist (F9) | Unit test: the previously-WARNing legitimate headings (architecture "Multi-harness runtime parity", lifecycle-foundation "Purpose"/"Core services", etc.) no longer WARN after allowlist extension; EN/PT canon resolved. |
| Constitution (A) | `dadaia specs doctor` stays 0-error; SPEC-DOC-028 (constitution file-refs resolve) passes — the amendment adds only concept/symbol refs, no new file paths. |
| `.pi/` content (B) | **Faked / structural** — `.pi/` content is authored + projected + privacy/doctor-gated offline. The **live `pi` load** (Layer-1 native AGENTS.md read; Layer-2 `pi --mode json` schema) is the **operator-environment-verified seam**, NOT offline-tested. CI is never gated on a live `pi`. |

## Root-whitelist ↔ projection dependency (the critical detail)

The `pre_gate` root-whitelist policy (`hooks/root_whitelist.py` `_WHITELIST`) is the
**mechanical** guard that blocks new top-level root entries. The §0 constitution layout
amendment (Thread A) *authorizes* `.pi/` as a root entry, but authorization in law does
not change hook behavior — the hook's `_WHITELIST` set is the actual enforcement. Three
surfaces enumerate the whitelist and must all gain `.pi/` in this release:

1. `hooks/root_whitelist.py` `_WHITELIST` — the deterministic blocker (software-engineer).
2. `public/rules/tmp-file-guardrail.md` root-whitelist table — projected rule (ai-engineer).
3. `public/data/AGENTS.md` Workspace Root Law text — projected root law (ai-engineer).
4. Any `dadaia doctor` ROOT check enumerating the whitelist (software-engineer).

If only the constitution is amended and the hook is not, `dadaia public install --target
pi` is blocked the moment it tries to create `.pi/` — Thread B is dead on arrival. Hence
**C lands before B's live smoke**.

## Technical risks

- **Operator-environment seams (MEDIUM):** the live `pi` binary's Layer-1 AGENTS.md native
  read and the Layer-2 `pi --mode json` schema are verified in the operator's environment
  (Node + `ANTHROPIC_API_KEY`), not offline. Mitigation: `.pi/SYSTEM.md` is authored to
  degrade to a one-line import-bridge pointer if native read fails; the `--mode json`
  parser already has a degraded fallback (shipped). CI stays faked.
- **product-vision (F2) operator gate (MEDIUM):** F2 proceeds only after the operator
  confirms `docs/01_medium_codex.md` stance. If unconfirmed at CLOSURE, F2 is deferred
  (recorded reason) and the constitution amendment lands independently — it documents
  implemented reality, not the vision doc.
- **Manifest tracking (LOW):** `public/pi/**` staged → manifest-tracked automatically by
  `stage()`; confirm `.pi/**` projections are listed so the lib-guardrail (non-edit) applies.

## Validation plan (global gates — last implementation task)

1. `dadaia ci preflight` — 4/4 (ruff format --check, ruff check, mypy --strict, pytest).
2. `lint-imports` — 6/0.
3. `dadaia public stage && dadaia public install --target all && dadaia public doctor` —
   exit 0, includes `[ok] public-privacy` + `[ok] pi:` lines.
4. `dadaia public install --target pi` live smoke — produces `.pi/`; clean re-install
   (idempotent) — produces no drift.
5. `dadaia specs doctor` — 0 errors (warnings acceptable; the F9 allowlist + F5 token
   refresh + F11 index regen should reduce the warning count).

## End-state validation (what the operator can do at CLOSURE)

- **Layer 1:** `pi` in the workspace terminal → PI grounded by AGENTS.md (native) + `.pi/`
  pointing at the law + `dadaia` CLI.
- **Layer 2:** `dadaia lifecycle … --harness pi` → step runs on the `PI_HEADLESS` worker
  (already shipped; now documented).
- **Memory:** a drift re-audit at CLOSURE confirms the PI / two-layer surface drift
  resolved (the audit's floor-breach agent-surface dimension cleared).

## Deferred / uncertain seams (recorded)

- **WS-PI-4** Ring-1 `.pi/extensions/dadaia-sdd-gate.ts` — OUT. PI Layer-1 stays advisory +
  chokepoint; the law (§4/§8) and the shipped surface agree, so the scaffold does not
  over-claim enforcement.
- **Live `pi` behavior** — operator-environment-verified, not offline. The `.pi/` projection
  content is faked/structural-tested + privacy/doctor-gated; the live pi trust-load is the
  unverified seam, flagged in SPEC risks.
- **`dadaia context` DEAD-mark of `dadaia-pi-workspace`** — closure/operator follow-up
  (touches another repo, known `dead()` bugs), not a hard implementation task.
