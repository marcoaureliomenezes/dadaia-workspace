# SPEC — Release v0.1.70 — Contract & Repo-Hygiene Drift

> **Status:** Aprovado
> **Release ID:** v0.1.70
> **Owner:** product-engineer
> **Picked set:** 2 open HIGH bugs — shipped self-inconsistencies

## Objective

Fix two places where the library contradicts itself and misleads users, each at
root cause, no workarounds:
1. The memory schema **correctly** rejects `agent_tier`, but the authoring contract
   (three doc copies + one memory-atom body) still tells authors "the schema
   tolerates it" — so consumer workspaces emit `agent_tier` and their `specs doctor`
   then hard-fails. Fix the **docs to match the schema**; never re-add `agent_tier`
   to the schema (it has zero consumers and was deliberately dropped in v0.1.61).
2. `.gitignore` ignores the `specs/backlog/remote-bugs/` intake subtree, so remote
   bug reports land on disk but are silently omitted from commits unless force-added.

## Picked bugs

| Bug id | Severity | Disposition |
|---|---|---|
| `specs-doctor-rejects-current-memory-agent-tier-frontmatter` | HIGH | Fixed (FR1) |
| `remote-bugs-gitignore-blocks-new-intake` | HIGH | Fixed (FR2) |

Both fixed directly; neither superseded.

## Reproduction & TDD mandate — no workarounds

Under `feedback-reproduce-rootcause-no-workaround`. FR1's proof is a doc↔schema
consistency test that FAILS while the docs lie and PASSES once corrected (with the
existing schema-absent pin `test_agent_tier_property_absent_from_schema` kept
green — the schema is the correct side). FR2's proof is a repo-hygiene test that
FAILS while a `remote-bugs/*.md` probe is git-ignored and PASSES after the negation.

---

## Root causes (verified by inspection)

### FR1 — Authoring docs claim the schema tolerates `agent_tier`; it rejects it

The memory frontmatter schema
(`dadaia_workspace/public/schemas/memory/memory-frontmatter-v1.schema.json`) has
`"additionalProperties": false` and does not list `agent_tier` — so any atom carrying
it is a hard `LINT-1` error (pinned by
`tests/unit/scripts/test_lint_memory_atoms.py::test_agent_tier_property_absent_from_schema`;
`generate-memory-catalog.py:73` correctly documents the v0.1.53 removal). `agent_tier`
has **zero runtime consumers** (the `ctx_inject` digest tests prove the digest strips
it). But four surfaces still tell authors the opposite:
- `dadaia_workspace/public/scaffold/memory/AGENTS.md:52` — "`agent_tier` is
  deprecated-optional since v0.1.53: the schema tolerates it, …"
- `dadaia_workspace/public/data/memory-AGENTS.md:52` — byte-identical false claim.
- `specs/memory/AGENTS.md:52` — the projected/hand-synced third copy (tri-copy;
  `install` does NOT sync this one), same false claim. **MEMORY-class path.**
- `specs/memory/architecture.md:281` — "the schema retains a deprecated optional
  `agent_tier` property … slated for removal". **MEMORY-class path.**

Consumers (e.g. sample-consumer) follow the doc, emit `agent_tier`, and their doctor
rejects it. **The schema is correct; the docs are wrong.**

**Invariant to restore:** all four surfaces state that `agent_tier` was removed
(v0.1.61) and is now **rejected** by the schema (`additionalProperties: false`) —
authors must not include it. No schema change. A doc↔schema consistency test guards
against the lie reappearing.

### FR2 — `.gitignore` ignores the `remote-bugs/` intake subtree

`.gitignore` lines 133-138 handle `specs/backlog/`:
```
!/specs/backlog/            134:/specs/backlog/*
!/specs/backlog/*.md        !/specs/backlog/_archive/  /specs/backlog/_archive/*  !/specs/backlog/_archive/*.md
```
`/specs/backlog/*` (line 134) excludes the `remote-bugs/` **subdirectory**, and the
`!/specs/backlog/*.md` re-include (line 135) only rescues top-level `backlog/` files —
git cannot re-include a file under an excluded directory. There is **no** negation for
the `remote-bugs/` subtree, so new `remote-bugs/*.md` intake reports are ignored
(existing ones are tracked only because they were force-added). This contradicts the
`.gitignore`'s own stated intent that backlog Markdown is PM-curated repo truth.

**Invariant to restore:** `specs/backlog/remote-bugs/*.md` and its `_archive/*.md` are
explicitly un-ignored, mirroring the `backlog/_archive` idiom. A repo-hygiene test
asserts governance-intake probe files are not git-ignored.

---

## Functional requirements

### FR1 — Correct the `agent_tier` authoring contract (docs, not schema)
- **FR1.1** Rewrite the false "the schema tolerates it / retains it" statement in
  `public/scaffold/memory/AGENTS.md` and `public/data/memory-AGENTS.md` to the
  **two-phase truth (architect F2)**: `agent_tier` was deprecated in v0.1.53 and
  schema-dropped in v0.1.61 — the schema now **rejects** it (`additionalProperties:
  false`); do not include it. (lib-originated source — re-project after.)
- **FR1.2** Correct the same claim in the two MEMORY-class copies
  `specs/memory/AGENTS.md:52` and `specs/memory/architecture.md:281` (edited in the
  DEFINITION or CLOSURE phase per the memory-phase gate).
- **FR1.3** Re-project: `dadaia public stage && dadaia public install --target all &&
  dadaia public doctor` — `public doctor` must include `[ok] public-privacy` and exit 0
  (no drift). Do NOT hand-edit projected instance files.
- **FR1.4** NO schema change. The schema-absent pin
  (`test_agent_tier_property_absent_from_schema`) stays green.

**AC1.1 (architect F1)** A doc-consistency test asserts, across **all four** surfaces —
`public/scaffold/memory/AGENTS.md`, `public/data/memory-AGENTS.md`,
`specs/memory/AGENTS.md`, `specs/memory/architecture.md` — that the false claims do NOT
appear (matching each file's specific lie string: "schema tolerates it" in the three
AGENTS.md copies, "retains a deprecated optional `agent_tier`" in architecture.md) and
that each states `agent_tier` is rejected/removed. FAILS on current code, PASSES after FR1.
**AC1.2** `test_agent_tier_property_absent_from_schema` still green (schema unchanged).
**AC1.3** `dadaia public doctor` exit 0 with `[ok] public-privacy` after re-projection.
**AC1(repro)** the doc-consistency test is the executed-path RED→GREEN proof.

### FR2 — Un-ignore the `remote-bugs/` intake subtree
- **FR2.1** Add to `.gitignore`, after the `backlog/_archive` block, the negation for
  the `remote-bugs/` subtree (re-declare dir, re-exclude contents, opt `*.md` back in,
  same idiom as `_archive`), so `specs/backlog/remote-bugs/*.md` and
  `remote-bugs/_archive/*.md` are tracked.
- **FR2.2** A repo-hygiene test: for each governance-intake path (`specs/bugs/`,
  `specs/backlog/`, `specs/backlog/remote-bugs/`, and their `_archive/`), a probe
  `*.md` is NOT git-ignored (`git check-ignore` returns non-zero).

**AC2.1** `git check-ignore specs/backlog/remote-bugs/<probe>.md` returns non-zero
(not ignored) after FR2; returns 0 (ignored) before.
**AC2(repro)** the repo-hygiene test FAILS on current code, PASSES after FR2.

### FR3 — Regression & suite integrity
- **FR3.1** Full `pytest` green; `ruff format --check`, `ruff check`, `mypy --strict`,
  `lint-imports` (9), `dadaia public doctor` (exit 0) green.
- **FR3.2** No pre-existing test weakened; `test_agent_tier_property_absent_from_schema`
  and the digest-strip tests stay green (they encode the correct schema/behavior).

---

## Non-goals
- Re-adding `agent_tier` to the schema (it's dead metadata — that would be the
  workaround). Lifecycle/context work (Releases A/B, done). No PyPI. The
  `stray-dadaia-tmp-inside-repo` side-bug stays tracked (separate AI-surface concern).

## Out-of-scope paths (write allowlist)
- `dadaia_workspace/public/scaffold/memory/AGENTS.md` (FR1.1)
- `dadaia_workspace/public/data/memory-AGENTS.md` (FR1.1)
- `specs/memory/AGENTS.md`, `specs/memory/architecture.md` (FR1.2 — MEMORY, phase-gated)
- `.gitignore` (FR2.1)
- `tests/unit/scripts/**` or `tests/integration/**` (FR1 doc-consistency + FR2 hygiene tests)
- `specs/releases/v0.1.70/**`, `specs/bugs/**` (ADDITIVE)
- Re-projected instance files under the workspace root are updated by `install`, never hand-edited.
