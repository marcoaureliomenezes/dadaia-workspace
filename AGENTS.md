# repos/dadaia-workspace — the library source tree

Hand-authored, repo-scoped. Not a projection: `dadaia public install` never writes
into the source tree it projects from, so nothing here is regenerated.

- This repo is the **library** that scaffolds dadaia-workspace instances; the tree
  around it (`../../.dadaia/`, `../../.claude/`, root `AGENTS.md`/`DADAIA.md`) is the
  **instance**, projected from `dadaia_workspace/public/`.
- The always-on law is the workspace's, one file up twice: read `../../DADAIA.md`.
- Change law or any AI-entity file at its source under `dadaia_workspace/public/`,
  then re-project: `dadaia public stage` -> `dadaia public install --target all` ->
  `dadaia public doctor`.
- A library change is unfinished until the instance reflects it; never hand-edit a
  projected instance file to fake the result.
- Any failure of a workspace operation here is a product bug of this library:
  register it in `specs/bugs/`.
