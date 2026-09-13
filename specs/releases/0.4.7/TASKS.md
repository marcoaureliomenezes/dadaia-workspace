# TASKS — Release: 0.4.7

**Status:** Aprovado
**Release ID:** 0.4.7
**Owner:** product-engineer

---

## Candidate 4 — docs derive from memory

- [x] T-047-34 — FR1 (`product-engineer`): read every `specs/memory/product/**/*.md`
  (22) and `ARCHITECTURE.md`, `QUALITY.md`, `TECHSTACK.md` statement by statement
  against the code each names and against `CONTEXT.md`; run every Part-1 `Measured
  by:`; write `.dadaia/tmp/product-engineer/<YYYYMMDD>/memory-review.md` — one row
  per file (`file | unchanged/corrected | verified/corrected/deleted | evidence`) and
  one section per corrected file with each correction verbatim; a failing or absent
  measure is an operator finding in the report. No atom is edited here — the
  corrections land at closure (T-047-40, RC-FLOW step 5). Write set:
  `.dadaia/tmp/product-engineer/<YYYYMMDD>/memory-review.md`. Blocked by: none
  (disjoint from T-047-35). Delivers: the operator reads one table of 25 files, each
  with a verdict and its evidence.
- [x] T-047-35 — FR2 (`software-engineer`): `cli/help_digest.py::command_paths()` (the
  one Typer walk; `render_digest` uses it); `features/specs/citations.py::
  dead_citations(text, *, command_paths, repo_root)` relocated from
  `test_behavior_map.py`'s two finders (the test imports both, keeps every fixture,
  loses `_derive_command_tree`); `MEM-DRIFT-2` (WARNING, unit = atom, no fix) in
  `features/specs/doctor_memory.py` + its `rules.py` row; the doctor CLI root passes
  `command_paths()` as plain data (RED: a fixture atom citing `dadaia fixture-verb`
  yields one WARNING and exit 0; no store of the tree inside `features`). Write set:
  `dadaia_workspace/cli/help_digest.py`, `dadaia_workspace/cli/commands/doctor.py`,
  `dadaia_workspace/features/specs/{citations.py,doctor_memory.py,rules.py}`,
  `tests/**`. Blocked by: none (disjoint from T-047-34). Delivers: `dadaia doctor`
  names every memory atom citing a dead verb or path, as a WARNING.
- [ ] T-047-36 — FR3 core (`software-engineer`): `docs/cli.md` = `dadaia help tree`
  output; `llms.txt` at the repo root (link lists only); `README.md` rewritten ≤ 10 KB
  in the three blocks + Links, every `## ` followed by `<!-- derived-from: <slug>
  sha256:<hex64> -->`, content from the atoms and the T-047-34 report's corrected
  statements; `docs/01_medium_codex.md` deleted; `tests/contract/
  test_docs_derived_from_memory.py` (Intent: CONTRACT): glob set `README.md`,
  `llms.txt`, `docs/*.md`; marker after every H2, slug resolves under
  `specs/memory/`, hash current, no `none`; `docs/cli.md` body-equal to
  `render_digest()` after line 1; failure names `<doc>#<heading>`, the atom path and
  the re-record line; in-memory fixtures for stale hash, unknown slug, missing
  marker, `cli.md` drift; `dead_citations` over the same set is red (RED: today's
  README — `specs/releases/ACTIVE.md`, `dadaia academy`). Write set: `README.md`,
  `llms.txt`, `docs/**`, `tests/**`. Blocked by: T-047-34. Delivers: the PyPI long
  description is true, every section names its atom, and one changed atom byte is a
  red test.
- [ ] T-047-37 — FR3 rest (`software-engineer`): `docs/getting-started.md` (install →
  `dadaia init` → `context bind` → `doctor` → `panel` → first candidate, what each
  step creates) and `docs/concepts.md` (context, release/candidate, the flow, the
  gate, memory, bugs/backlog, audits — one paragraph each, `CONTEXT.md` for terms),
  both marker-derived. Write set: `docs/getting-started.md`, `docs/concepts.md`.
  Blocked by: T-047-36 (disjoint from T-047-38, T-047-39). Delivers: a newcomer
  walks from `pip install` to a first candidate on derived pages only.
- [ ] T-047-38 — FR4 (`software-engineer`): `pyproject.toml` `description` = the
  tagline, `[tool.poetry.urls]` Homepage/Repository/Documentation/Changelog/Issues,
  `keywords`/`classifiers` verified against the README; the tagline equality test
  (README first non-badge paragraph == `description` == `llms.txt` `>` line) in
  `test_docs_derived_from_memory.py`; `docs/distribution.md` (channel | artifact |
  state | who acts; derived from `pypi-distribution`). The `gh repo edit` +
  `gh repo view --json …` run is the PM's, recorded in the `log`, not in this task.
  Write set: `pyproject.toml`, `docs/distribution.md`, `tests/contract/
  test_docs_derived_from_memory.py`. Blocked by: T-047-36. Delivers: PyPI shows the
  tagline and five links; the channel list and each channel's state are one page.
- [ ] T-047-39 — FR5 (`ai-engineer`): `dd-release-implementation/MEMORY-UPDATE.md`
  gains the re-derive step (run the derived-docs test; re-read, re-derive, re-record
  in the atom's commit); `RC-FLOW.md` step 5 Done-when adds the green test;
  `behavior-map.json` hash re-recorded; `public stage` → `install --target all` →
  `public doctor`. Write set: `dadaia_workspace/public/skills/dd-release-
  implementation/{MEMORY-UPDATE.md,RC-FLOW.md}`, `dadaia_workspace/public/entities/
  behavior-map.json`, the instance projections via the CLI. Blocked by: T-047-36.
  Delivers: every future closure re-derives the docs whose atom it changed, by
  protocol.
- [ ] T-047-40 — FR6 closure (`product-engineer`): `CHANGELOG.md [0.4.7]` candidate 4;
  preflight; `dadaia release phase CLOSURE --sha`; `dadaia backlog exit
  docs-derived-from-memory-and-distribution --disposition delivered --release 0.4.7`;
  the `log` entries (`memory` citing the report path and the unchanged/corrected
  split, `summary`, `size`, `drifts`, `test-dispositions`, `dispositions` with the
  operator's external steps, `artifact-gc`, `reviews`); Q8's `proposed` decision
  record if the operator so rules. The memory pass — applying every correction of the
  T-047-34 report, `product-vision` (tagline, the two usage paths),
  `pypi-distribution` (metadata contract, channels), `workspace-doctor`
  (`MEM-DRIFT-2`), `ARCHITECTURE`/`QUALITY` Part 2 rows, catalog + index
  regenerated, and every derived section whose atom changed re-derived and
  re-recorded in the same commit — is closure procedure (RC-FLOW step 5), never a
  task write set. Write set: `CHANGELOG.md`, `specs/releases/0.4.7/**`,
  `specs/backlog/**`, `specs/ADRs/decisions.jsonl`. Blocked by: T-047-35, T-047-37,
  T-047-38, T-047-39. Delivers: candidate 4 closed with zero `MEM-DRIFT-2`, the
  derived-docs test green after the memory pass, ready for the `feature → develop`
  PR and the promote-or-continue gate.
