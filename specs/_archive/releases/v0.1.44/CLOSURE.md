# Closure: Release — v0.1.44

> **Status:** Aprovado
> **Release ID:** v0.1.44
> **Owner:** product-engineer
> **Closed:** 2026-06-30

## Summary

v0.1.44 introduces the **persona** entity — the Layer-2 (codex/pi) equivalent of a
Claude Layer-1 sub-agent — and wires it into every dadaia-workflow worker step so that a
real PI/Codex worker is now handed *the behavioral mandate of its role*, not merely a
bare role token. A new harness-universal persona library (`public/personas/<role>.md`,
one atom per non-PM core role) is loaded and validated by a `PersonaLoader` that mirrors
the fragment loader, and the persona body is injected into the worker prompt envelope
alongside the fragment as an **operative directive** (the worker is explicitly told to
act per the mandate). `project-manager` is **excluded** by design (D-1): PM is the
Layer-1 orchestrator, not a Layer-2 worker persona, so the seven fragments that carried
`role: project-manager` were reassigned to real Layer-2 personas (scope/grill/synthesis →
`product-engineer`; audit/triage + bug-intake → `project-auditor`), and no model-driven
step binds `project-manager` anymore.

The release also **opens pi's model set** from a GPT-only-by-construction catalog to an
**allowlist-validated** one: a curated Layer-2-native allowlist `LAYER2_EXTRA_MODEL_IDS`
(including the OpenRouter id `kimi-2.7`) is unioned with the registry's codex ids, the
model registry is left untouched (avoiding the `codex_tier_views()` hot-path
`ValueError`), and the operator-overlay store can now register additional validated pi
ids without a code change. The hard **no-`claude-*`** safety bound is retained — the law
only widens, it never removes a safety guarantee. The GPT-only → allowlist-validated law
change is recorded as a new normative **constitution §8** clause (operator-confirmed),
superseding the archived ADR-B framing. A full fragment/persona optimization audit and a
two-surface anti-regression guardrail (fragment-layer + catalog-layer) close the loop.

## Tasks completed

All 18 tasks are `[x]` DONE. Per-task implementation commits live on the
`feature/v0.1.44` branch and are folded into the squash-merge to `main` (PR #78,
`7264f6c4`); the closure/memory work lands on `closure/v0.1.44`.

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-44-1 | Shared FrontmatterDocLoader base (loader DRY) | PR #78 (`7264f6c4`) |
| T-44-2 | Author the 8 persona atoms | PR #78 (`7264f6c4`) |
| T-44-3 | PersonaLoader + validation + lint + dangling-ref guard | PR #78 (`7264f6c4`) |
| T-44-4 | `persona` field on PromptScope + AgentRunRequest | PR #78 (`7264f6c4`) |
| T-44-5 | Emit persona as operative directive in build_prompt_envelope | PR #78 (`7264f6c4`) |
| T-44-6 | Resolve role→persona in pipeline._scope | PR #78 (`7264f6c4`) |
| T-44-7 | Reassign the 7 PM-role fragments | PR #78 (`7264f6c4`) |
| T-44-8 | Update worker-step catalog/pipeline role bindings | PR #78 (`7264f6c4`) |
| T-44-9 | Anti-regression: every resolved pipeline-step role → non-PM persona | PR #78 (`7264f6c4`) |
| T-44-10 | Fragment/persona optimization pass | PR #78 (`7264f6c4`) |
| T-44-11 | Layer-2-native model allowlist (REGISTRY untouched) | PR #78 (`7264f6c4`) |
| T-44-12 | Extend pi catalog + relax invariant to allowlist union | PR #78 (`7264f6c4`) |
| T-44-13 | Allowlist-validated operator-overlay pi registration | PR #78 (`7264f6c4`) |
| T-44-14 | Verify pi_runtime passthrough | PR #78 (`7264f6c4`) |
| T-44-15 | Doc edits: GPT-only → allowlist; persona entity; scoped doc-lint | PR #78 (`7264f6c4`) |
| T-44-16 | Constitution §8 amendment (operator-confirmed) | PR #78 (`7264f6c4`) |
| T-44-17 | Propagate lib-originated assets + full validation | PR #78 (`7264f6c4`) |
| T-44-18 | Update MEMORY atoms asserting GPT-only (this CLOSURE) | `closure/v0.1.44` |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Full test suite green | `pytest` | 4206 passed |
| Static types clean | `mypy --strict` | clean, 0 errors |
| Lint/format clean | `ruff format --check && ruff check` | clean |
| Public projection privacy + consistency | `dadaia public doctor` | `[ok] public-privacy` |
| SDD invariants clean | `dadaia specs doctor` | 0 errors |
| Spec-review trio verdict | (trio review of the release) | APPROVED (after 1 reject cycle) |
| QA acceptance, alpha-1 | (qa-engineer review) | APPROVED |
| Security verdict for push | (security-reviewer handoff) | APPROVED — `metrics.commit_sha` `d89f6c6f` |
| Merge to main + CI | PR #78 → `main` | merged `7264f6c4`, all CI green (35 pass) |

## Drifts

### plan-persona-root-depth

**Description:** PLAN §3.2 specified the persona-library root should be resolved via
`parents[2]` from the loader module. During implementation the loader module sits one
level deeper than PLAN assumed, so `parents[2]` pointed at the wrong directory and would
not have located `public/personas/`.

**Resolution:** Implemented with `parents[3]`, which is the correct depth to reach the
`dadaia_workspace/public/personas/` root from the loader module. The PersonaLoader tests
(including `validate_all()` loading all 8 atoms) confirm the corrected path resolves.
Trade-off: none — the PLAN value was simply an off-by-one in the depth estimate.

**Memory updates:** none — this is an internal path-resolution detail, not a
product-visible or architectural fact carried in memory.

### gpt-only-was-not-a-live-constitution-law

**Description:** T-44-16 was scoped as a "constitution/ADR-B amendment" on the assumption
that a live normative "GPT-only" clause existed to edit. Inspection found the "GPT-only"
framing was **not** a live constitution law before this release — it existed only as an
**archived ADR-B** (under `specs/_archive/`, FROZEN) plus a code docstring in
`core/harness_models.py`. There was no in-force normative clause to amend.

**Resolution:** Rather than editing a non-existent clause, T-44-16 **added a new
normative constitution §8 clause** stating the Layer-2 model set is
registry/allowlist-validated (union of registry codex ids + `LAYER2_EXTRA_MODEL_IDS`)
with the hard no-`claude-*` bound retained. The new §8 clause **supersedes** the archived
ADR-B framing. This was written only after explicit operator confirmation (R1).
Trade-off: the change is a law *addition*, not an edit; the safety bound (no `claude-*` at
Layer 2) is preserved and stated explicitly.

**Memory updates:** none directly from this drift — the memory atoms updated in this
release (see below) reflect the shipped allowlist-validated law, consistent with the new
§8 clause.

## Memory updates

Two memory atoms were edited in this CLOSURE phase to reflect the shipped
allowlist-validated Layer-2 model law (registry codex ids + `LAYER2_EXTRA_MODEL_IDS`;
hard no-`claude-*` bound retained; pi may register validated ids via the operator
overlay). Both stay atomic (no changelog) and keep valid frontmatter (neither carries a
`token_estimate` field).

- `specs/memory/architecture.md` — LAW 2 block: `pi → 4 models` (adds curated OpenRouter
  `kimi-2.7` via `LAYER2_EXTRA_MODEL_IDS`); the "Both catalogs are **GPT-only** by
  construction" sentence rewritten to "**allowlist-validated** by construction" (a
  Layer-2 id must belong to `_known_codex_ids() | LAYER2_EXTRA_MODEL_IDS`), with the hard
  no-`claude-*` bound stated as **retained**.
- `specs/memory/product/sdd/lifecycle-foundation.md` — `core/harness_models.py` bullet:
  `pi → 3` → `pi → 4` (incl. OpenRouter `kimi-2.7`), "Both catalogs are GPT-only" →
  "allowlist-validated (union of registry codex ids + `LAYER2_EXTRA_MODEL_IDS`)"; and the
  `model_profiles` invariant line changed from "a `claude-*` id (GPT-only Layer-2
  invariant)" to "(registry/allowlist-validated Layer-2 invariant; never `claude-*`)".

Note (R4): the **`ai-engineer` persona atom is INTENTIONALLY unreferenced** by any
current fragment. It was authored for roster symmetry (all 8 non-PM core roles), and the
AC-4 audit verifies that *every model-driven step resolves to a persona* — it does **not**
require every persona to be used. The unreferenced `ai-engineer` persona is deliberate,
not dead code.

`specs/memory/tech-stack.md` — no change: the release did not alter approved technologies
or dependencies. Other `specs/memory/product/**` atoms — no change: untouched features
remain intact.

## Dispositions

This release was a feature release defined from a SPEC objective, not a bug/backlog pick
sweep; no `specs/bugs/**` or `specs/backlog/**` items were picked into or superseded by
v0.1.44. One new bug was **filed during** the build (see Backlog returns) and remains
Open for a follow-up release — it is not a disposition of this release.

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| _(none)_ | — | — | No bugs/backlog items picked into this release. |

## Backlog returns

- `backlog/candidates.md` ← **v0.1.45 panel redesign** (fast-follow) — Workflows diagram
  cards + Agentic-tab rework + styling; surfaces the persona entity defined here. Depends
  on v0.1.44; must not start before this release ships.
- Bug filed during build: **`precommit-backlog-doctor-blocks-unrelated-commits`** — the
  pre-commit backlog-doctor gate blocked commits unrelated to backlog changes. Filed to
  `specs/bugs/`, status Open, for a follow-up release.
- Security LOW defense-in-depth notes (recorded, not blocking):
  - implicit-vs-explicit `claude-*` rejection in the operator overlay — the overlay
    rejects `claude-*` implicitly (outside the union) rather than with an explicit
    named-token reject; consider an explicit reject message for clarity.
  - the persona `role → path` join has no traversal sanitization, but `role` is governed
    catalog data (a fixed set of non-PM core roles), not free operator input, so the
    exposure is bounded; sanitization is a hardening nicety, not a live vulnerability.

## Archive decision

**MOVE** — the release directory will be moved to
`specs/_archive/releases/v0.1.44/` via `git mv` by the coordinator (product-engineer does
not run Bash). ACTIVE.md will then be updated to point at the next release (v0.1.45) or
`release: none`.
