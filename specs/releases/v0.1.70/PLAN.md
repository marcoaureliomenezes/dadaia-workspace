# PLAN — Release v0.1.70 — Contract & Repo-Hygiene Drift

> **Status:** Aprovado
> **Release ID:** v0.1.70
> **Owner:** product-engineer

## Strategy

Two independent self-inconsistency fixes, each RED-first. Small, contained — the
final release of the remediation arc.

- **Wave A — FR1 (agent_tier doc↔schema truth).** RED: a doc-consistency test asserts
  the authoring docs no longer claim the schema tolerates `agent_tier` and instruct
  its removal — FAILS today. GREEN: correct the two `public/` doc copies (lib source)
  + the two MEMORY-class copies (`specs/memory/AGENTS.md`, `architecture.md`), then
  re-project (`dadaia public stage && install --target all && public doctor`). The
  schema is untouched; its absent-pin stays green. The two MEMORY-class edits are done
  in the DEFINITION phase (memory is writable to product-engineer in DEFINITION/CLOSURE
  per the gate) — they are factual corrections, part of defining the fix.
- **Wave B — FR2 (gitignore intake).** RED: a repo-hygiene test proves a
  `remote-bugs/*.md` probe is git-ignored. GREEN: add the negation lines mirroring the
  `backlog/_archive` idiom; re-run → not ignored.
- **Wave C — FR3 (validation).** Full suite + gates + `dadaia public doctor` exit 0.

Waves A/B are disjoint (docs+memory+public vs `.gitignore`) and may proceed in parallel.

## Projection note (critical)

FR1 edits **lib-originated** `public/` sources. After editing, the projection MUST be
re-run so staging hashes + the workspace-root instance match, else `dadaia public
doctor` reports drift (non-zero). The tri-copy `specs/memory/AGENTS.md` is NOT synced
by `install` — it is corrected by hand in Wave A (FR1.2). Never hand-edit the
manifest-tracked projected instance files at the workspace root; let `install` project them.

## Test plan
- FR1 doc-consistency test (executed-path over the real doc files) — RED then GREEN.
- FR2 repo-hygiene test (real `git check-ignore` over probe files) — RED then GREEN.
- Full `pytest -p no:cacheprovider`, ruff, `mypy --strict`, `lint-imports` (9),
  `dadaia public doctor` (exit 0, `[ok] public-privacy`).

## Risk
- FR1 is docs-only + a re-projection; zero runtime-behavior change (agent_tier has no
  consumers). Lowest risk. Guard: the schema-absent pin + digest-strip tests stay green.
- FR2 is a `.gitignore` edit; guard: the hygiene test proves intake paths are tracked
  and doesn't over-un-ignore (only `*.md` under the intake subtrees).

## Review gate
- software-architect REVIEW on SPEC+PLAN before implementation (confirm the fix is
  docs-not-schema, and the re-projection/tri-copy handling is correct).
- Post-implementation: qa-engineer suite/gate validation + security-reviewer push-cycle
  handoff keyed to the pushed sha.
