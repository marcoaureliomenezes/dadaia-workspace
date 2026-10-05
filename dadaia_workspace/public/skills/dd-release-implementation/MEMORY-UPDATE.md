# MEMORY-UPDATE — dd-release-implementation (RC-FLOW step 5 detail)

Disclosed reference reached at `SKILL.md` step 7 — `dd-product-engineer` runs it inside the Reconciliation job (`RC-FLOW.md` step 4), after every other job merged. Memory is reconciled from the code diff, never appended to.

## Protocol — delete, update, add

1. `python3 .agents/skills/dd-release-implementation/scripts/release.py phase CLOSURE --sha <sha>` — it refuses while another `wt/*` of the repo is open; no memory write before it.
2. `python3 .agents/skills/dd-release-implementation/scripts/release.py drift` — the window opens at the live release's last `kind: memory` entry's `until`, else its `defined.sha`; exit 1 means there is work. The worklist is every atom at least one of whose `sources` globs matched a changed path, and every `features/<pkg>/` package or `hooks/*.py` module no atom's sources cover.
3. For each listed atom, read `git diff <since>..HEAD -- <matched paths>` in full, then edit the atom in this order and no other:
   - DELETE every claim the code no longer supports — a verb, a file, a behavior, a number.
   - UPDATE every claim whose behavior changed; the tldr and summary are claims too.
   - ADD what is new, only after the two passes above.
4. For each uncovered package, write one atom (`product/<area>/<slug>.md`, frontmatter with `sources`); for a feature that died, delete its atom and its wikilinks.
5. A line naming a date, a release, a candidate, a task or an FR is history: `LINT-1` rejects it (history lines, `MEM-NARRATIVE-1:` prefix) — say what the product does, never when it started.
6. `python3 .agents/skills/dd-spec-navigator/scripts/memory.py catalog generate`, then `memory.py check`.
7. In the same Reconciliation tree, before its merge: re-derive each section of `README.md`, `llms.txt` and `docs/*.md` whose atom changed from that atom and re-record its `derived-from` marker's `sha256:<12 hex>`; `docs/cli.md` regenerates from `.dadaia/.venv/bin/dadaia help tree` whenever a verb changed.
8. Commit the atoms, then `python3 .agents/skills/dd-release-implementation/scripts/release.py memory --reviewed <slugs> --changed <slugs>` — it derives the same window, computes the worklist itself and records `since`/`until`; `reviewed` names the entries read and left as they were, `changed` those rewritten or created; it refuses a worklist entry in neither list, a name outside the worklist, a `changed` atom that did not move over the window, and any phase but `CLOSURE`.
9. `.dadaia/.venv/bin/dadaia doctor`: `LEDGER-RELEASE-SCHEMA` (the memory record), `MEM-DRIFT-1/2`, `LINT-1` (history lines included) and `LEDGER-MEMORY-SCHEMA` clean; the candidate PR stays red until they are.

## Canonical memory

- `ARCHITECTURE.md` and `QUALITY.md` change only as the memory law says (`specs/memory/AGENTS.md` §1).

## Product memory is a folder catalog

- `product/index.md` and `product/catalog.json` are generated together — never edited by hand.
- `product/<area>/<slug>.md`: one atom per feature — what it does for its user, its boundaries, its current behavior, its runtime state, its dependencies as `[[slug]]` links; no implementation tour, no principle.

*Done when:* the `kind: memory` entry covers every worklist entry, `.dadaia/.venv/bin/dadaia doctor` is clean and the derived-docs test is green on the Reconciliation job's HEAD — an atom and its derived sections land in one merge.
