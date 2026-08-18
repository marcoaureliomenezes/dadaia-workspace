release: none
phase: none

No release is active. **v0.4.3 "claims-made-true / backlog-zero"** closed on 2026-08-18 and
is archived at `specs/_archive/releases/v0.4.3/` (CLOSURE `**Status:** Aprovado`); its ship
task, T-043-53, runs after this archive per the release order review → closure → archive →
ship (D8/FR5). **Publish number:** it ships as package **`0.4.2`** together with the merged,
never-published internal release v0.4.2 (operator lineage ruling 2026-08-18 — the registry's
latest published version is 0.4.1, so the next mint is `published+1 = 0.4.2`; the
internally-minted 0.4.3 number is retired unpublished — see CHANGELOG `[0.4.2]` and bug
`minted-version-skips-published-lineage`).

`specs/backlog/BACKLOG.md` `## ACTIVE` is **empty**: v0.4.3 picked the entire queue in one
release under the operator's standing order, and all 25 records carry a terminal `LEDGER`
line. The next release is defined when the operator creates demand — `project-manager`
curates it into the backlog, `product-engineer` defines the release from the picked set.

Phase ladder for the next release, when one opens:
DEFINITION → SPEC → PLAN → TASKS → IMPLEMENTATION → CLOSURE → ARCHIVED.
