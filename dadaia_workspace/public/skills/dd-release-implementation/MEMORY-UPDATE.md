# MEMORY-UPDATE — dd-release-implementation (RC-FLOW step 4 detail)

Disclosed reference reached at `SKILL.md` step 7 — `dd-product-engineer` runs it in the rc's `wt-rc` reconcile commits (`RC-FLOW.md` step 4), after every other job merged. Memory is reconciled from the code diff, never appended to.

## Protocol — delete, update, add

1. `phase CLOSURE` already ran, per the order in `RC-FLOW.md` step 4; no memory write before it.
2. The memory pass is the closure's last step (`RC-FLOW.md` step 4). `python3 .agents/skills/dd-release-implementation/scripts/release.py drift` — the window opens at the newest of the live release's `kind: memory` `until`s, then its `defined.sha`, that HEAD reaches, else at the root commit (a rewrite only widens it); exit 1 means there is work, and its output is the authoritative worklist.
3. For each listed atom, read `git diff <since>..HEAD -- <matched paths>` in full, then edit the atom in this order and no other:
   - DELETE every claim the code no longer supports — a verb, a file, a behavior, a number.
   - UPDATE every claim whose behavior changed; the tldr and summary are claims too.
   - ADD what is new, only after the two passes above.
4. For each uncovered package, write one atom (`product/<area>/<slug>.md`, frontmatter with `sources`); for a feature that died, delete its atom and its wikilinks.
5. History lines are `LINT-1` errors (`specs/memory/AGENTS.md` §4) — say what the product does, never when it started.
6. `python3 .agents/skills/dd-spec-navigator/scripts/memory.py catalog generate`, then `memory.py check`.
7. In the same `wt-rc`, before its merge: reconcile the repo's derived docs from every changed atom.
8. Commit the atoms, then `python3 .agents/skills/dd-release-implementation/scripts/release.py memory --reviewed <slugs> --changed <slugs>` — it derives the same window, computes the worklist itself and records `since`/`until`; `reviewed` names the entries read and left as they were, `changed` those rewritten or created; it refuses a worklist entry in neither list, a name outside the worklist, a `changed` atom that did not move over the window, and any phase but `CLOSURE`.
9. Last, `.dadaia/.venv/bin/dadaia doctor`: `LEDGER-RELEASE-SCHEMA` (the memory record), `MEM-DRIFT-1/2` and `LINT-1` (history lines included) clean; the `wt-rc` merge waits until they are.

## Canonical memory

- `ARCHITECTURE.md` and `QUALITY.md` change only as the memory law says (`specs/memory/AGENTS.md` §1).

## Product memory is a folder catalog

- `product/index.md` and `product/catalog.json` are generated together — by `memory.py catalog generate` (step 6), which overwrites any hand edit.
- `product/<area>/<slug>.md`: one atom per feature — what it does for its user, its boundaries, its current behavior, its runtime state, its dependencies as `[[slug]]` links; no implementation tour, no principle.

*Done when:* the memory pass, the closure's last step, is complete: the closure's latest `kind: memory` entry covers every authoritative worklist entry, `.dadaia/.venv/bin/dadaia doctor` is clean, and each changed atom lands with its reconciled derived docs in the same `wt-rc` merge.
