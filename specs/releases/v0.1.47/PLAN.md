# PLAN — v0.1.47

**Status:** Aprovado
**Sequencing rationale:** code fixes first (W1) so the truth pass documents the FIXED
system, not the broken one; constitution before memory (memory reconciles against the
corrected law — backbone sequencing); catalog regeneration and projection install last in
their waves; dispositions after the fixes they reference exist.

## Order of execution

1. **Definition commit** (this): backlog sanitization (done pre-branch), GRILL/SPEC/PLAN/
   TASKS, ACTIVE.md → v0.1.47/DEFINITION, `.gitignore` re-includes (GRILL/OQ ×3 groups,
   `specs/bugs/*.jsonl` + `_archive` opt-in), commit + first tracked bug-store snapshot.
2. **W1** (software-engineer): W1-1..W1-12, TDD per item, one commit per coherent group:
   (a) codex argv + inert keys (W1-1/2); (b) persona injection (W1-3); (c) chokepoint
   scoping + preflight (W1-4/5); (d) hooks: root-whitelist + ctx-inject attribution
   (W1-6/7); (e) resolver fallback (W1-8); (f) doctor guards + 031 text + fake smoke +
   setup.cfg comment truth (W1-9/10/11/12). Full suite green per commit.
3. **W2** (product-engineer): constitution rewrite + AGENTS.md/rules sweep. Gate note:
   memory writes require DEFINITION phase — ACTIVE.md stays `phase: DEFINITION` through
   W2–W4 (implementation of W1 code is lease-covered; phase governs only MEMORY-class
   writes; constitution is MUTATING, not MEMORY).
4. **W3** (product-engineer): memory atoms in backbone order (tech-stack roster home first,
   then product-vision/harness-primitives, projection atoms, architecture.md de-narrate,
   QA atom, v0.1.46 catch-up atoms, panel/telemetry truth, NEW harness/ docs, index.md,
   catalog regenerate LAST). `lint-memory-atoms` + CAT-1 green after each batch.
5. **W4** (ai-engineer): fragments (per-workflow batches: shared → release_definition →
   backlog_definition → audit/research/bug_report → pipeline phases), personas, handoff
   skill; then `public stage && install --target all && public doctor` (clears live drift).
6. **W5**: backlog entries for deferrals; bug terminal events + backfill; audit archive
   sweep with disposition lines.
7. **W6**: full validation matrix; qa checkpoint; security APPROVE handoff per pushed sha;
   push; CI watch to green; PR; CLOSURE phase (memory stamps `last_updated`/
   `release_origin`, CLOSURE.md, archive).

## Validation matrix (gates per wave)

| Wave | Must pass |
|---|---|
| W1 | pytest full, ruff, mypy --strict; targeted new tests per item |
| W2 | WS-A acceptance greps (`grep -ci opencode == 0`, no kind enumeration); specs doctor; SPEC-DOC-037 green |
| W3 | lint-memory-atoms (LINT-1), CAT-1, specs doctor; per-atom acceptance greps from backbone; no-bearer grep == 0; import-linter-CI-claim grep clean |
| W4 | fragment/persona loaders, persona_doctor, `lifecycle workflow doctor`, public doctor exit 0, second-reviewer content APPROVE + prompt-assembly dumps |
| W5 | backlog doctor, `bugs status` reflects dispositions, specs doctor (incl. new loose-audit WARN = 0) |
| W6 | everything above + `dadaia doctor` + CI all-green on the PR |

## Write-set boundaries (discipline)

- W1: `dadaia_workspace/{infrastructure,features,hooks,cli,core}/**` + `tests/**` +
  `setup.cfg` (comment truth only).
- W2: `specs/constitution.md`, `dadaia_workspace/public/data/AGENTS.md`,
  `dadaia_workspace/public/rules/**`, one-time `repos/dadaia-workspace/AGENTS.md` refresh
  (W2b; performed at the instance level by the coordinator).
- W3: `specs/memory/**` only (MEMORY class — DEFINITION phase).
- W4: `dadaia_workspace/public/{lifecycle_fragments,personas,skills}/**` (+ projections via
  install, never hand-edited).
- W5: `specs/backlog/**`, `specs/bugs/**`, `specs/audits/**` (ADDITIVE) + `_archive` moves
  via git/Bash (sanctioned archive flow).
