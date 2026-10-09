# PILLAR-MEMORY — memory drift

Disclosed sibling of `SKILL.md`, pillar 3. Input: canonical memory (`ARCHITECTURE.md`, `QUALITY.md`), every `specs/memory/product/**` atom and `specs/constitution.md`, over the audit window.

## 1 — Every principle, run through its own named check

1. For each `P-NN` block in both canonical files, execute exactly the check its `Measured by:` line names.
2. Record pass, fail, or "check does not run" — the last is a finding against whoever authored the principle.
3. A principle carrying no `Measured by:` line, or `ADR: NNNN` naming a record that is not `accepted`, is a finding on its own.
4. Report only — fixing belongs to an ADR or to the operator.

## 2 — "Canonical memory changed without an accepted ADR"

```bash
git log -p <from-sha>..HEAD -- specs/memory/ARCHITECTURE.md specs/memory/QUALITY.md
```

1. Every `### P-NN` hunk pairs with a `docs(adr): accept NNNN-<slug>` commit — the same commit — whose record names the statement; other sections follow `specs/memory/AGENTS.md` §1.
2. A `### P-NN` hunk without that pairing is HIGH.
3. Exception: the first-inventory case — read `specs/ADRs/AGENTS.md` §5.1 before scoring a CREATING commit.

## 3 — Product memory vs code (scored)

1. `python3 .agents/skills/dd-spec-navigator/scripts/memory.py drift --since <from-sha> --json` — every atom it lists that no `kind: memory` entry of the window names in `reviewed` or `changed` is HIGH (a closure that did not reconcile); every uncovered package is HIGH.
2. For each atom in the window, read its `sources` and check every functional claim against the code: a claim with no implementation evidence is HIGH; code behavior no atom describes is LOW.
3. Run `memory.py check` and the doctor's `LINT-1` (history lines, `MEM-NARRATIVE-1:` prefix), `MEM-DRIFT-1/2` over the tree; any finding is MEDIUM (the closure should have left them clean).
4. `git log --format=%h <from-sha>..HEAD -- specs/memory/product`: an atom commit whose diff only adds lines to an existing atom is evidence of stacking — LOW, named per commit.
5. Tech stack: for each line of `ARCHITECTURE.md`'s `## Tech Stack`, confirm the technology and its pin in the repo's manifest and lockfile; an undeclared dependency or a line with no manifest counterpart is MEDIUM.

## 4 — Dead-code detection

Supports §3 — a module claimed live in memory but unreachable is drift. Every install pins an exact version, never `latest`.

- Run the repo's own dead-code and unused-import checkers (a linter's unused rules, a language-specific unused-symbol tool), each pinned to an exact version.
- Flag a zero-importer, no-entry-point-role module as a dead-layer candidate.

## 5 — `constitution.md` violations

- Check every absolute law in `constitution.md` against the window's commits and current tree state.
- A violated absolute law is CRITICAL by definition.

## Findings

- Every check above emits `pillar: "memory"` records via `FINDINGS-FORMAT.md`'s shape.
