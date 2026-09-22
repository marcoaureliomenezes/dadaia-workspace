# MEMORY-UPDATE — dd-release-implementation (RC-FLOW step 5 detail)

Disclosed reference reached at `SKILL.md` step 7 — `dd-product-engineer` runs it at every closure, after the last task and before the closure narrative. Memory is reconciled from the code diff, never appended to.

## Protocol — delete, update, add

1. `python3 .agents/skills/dd-release-implementation/scripts/release.py phase CLOSURE --sha <sha>` — it refuses while any task is not `[x]`; no memory write before it.
2. `python3 .agents/skills/dd-spec-navigator/scripts/memory.py drift` — the window opens at the live release's last `kind: memory` entry's `until`, else its `defined.sha`; exit 1 means there is work. The worklist is every atom at least one of whose `sources` globs matched a changed path, and every `features/<pkg>/` package or `hooks/*.py` module no atom's sources cover.
3. For each listed atom, read `git diff <since>..HEAD -- <matched paths>` in full, then edit the atom in this order and no other:
   - DELETE every claim the code no longer supports — a verb, a file, a behavior, a number.
   - UPDATE every claim whose behavior changed; the tldr and summary are claims too.
   - ADD what is new, only after the two passes above.
4. For each uncovered package, write one atom (`product/<area>/<slug>.md`, frontmatter with `sources`); for a feature that died, delete its atom and its wikilinks.
5. A line naming a date, a release, a candidate, a task or an FR is history: `LINT-1` rejects it (history lines, `MEM-NARRATIVE-1:` prefix) — say what the product does, never when it started.
6. `python3 .agents/skills/dd-spec-navigator/scripts/memory.py catalog generate`, then `memory.py check`.
7. `pytest tests/contract/test_docs_derived_from_memory.py` — re-derive each red section of `README.md`, `llms.txt` and `docs/*.md` from its atom and re-record its `derived-from` marker's `sha256:<12 hex>` in the SAME commit as the atom; `docs/cli.md` regenerates from `dadaia help tree` whenever a verb changed.
8. Commit the atoms, then `python3 .agents/skills/dd-release-implementation/scripts/release.py memory --reviewed <slugs> --changed <slugs>` — it derives the same window, computes the worklist itself and records `since`/`until`; `reviewed` names the entries read and left as they were, `changed` those rewritten or created; it refuses a worklist entry in neither list, a name outside the worklist, a `changed` atom that did not move over the window, and any phase but `CLOSURE`.
9. `dadaia doctor`: `RELEASE-TREE-MEMORY`, `MEM-DRIFT-1/2`, `LINT-1` (history lines included) and `CAT-1` clean; the candidate PR stays red until they are.

## Canonical memory is out of scope here

- `ARCHITECTURE.md` and `QUALITY.md` are never touched at closure. A change to a statement is an ADR (`docs(adr): accept <slug>`, hunk and record in one commit); a rewrite of their text belongs to `dd-audit-project` pillar 3 or to the operator's explicit order.
- A stale statement found during reconciliation is a proposed ADR or a closure note, never an edit.

## Product memory is a folder catalog

- `product/index.md` and `product/catalog.json` are generated together — never edited by hand.
- `product/<area>/<slug>.md`: one atom per feature — what it does for its user, its boundaries, its current behavior, its runtime state, its dependencies as `[[slug]]` links; no implementation tour, no principle.

*Done when:* the `kind: memory` entry covers every worklist entry, `dadaia doctor` is clean and the derived-docs test is green.
