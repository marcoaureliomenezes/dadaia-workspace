# SPEC — Release: 0.4.7

**Status:** Approved
**Release ID:** 0.4.7
**Owner:** product-engineer
**Opened:** 2026-09-13
**Consumes:** docs-derived-from-memory-and-distribution

---

## 1. Problem and context

Candidate 4 — "docs derive from memory" — takes the operator's 2026-09-12 demand (the
tool must be usable by humans and by agents; the docs are bad and stale) and leaves
memory read end to end against the code, every human- and agent-facing document
derived from a named memory atom under a mechanical check, and the three discovery
surfaces (PyPI, GitHub, the repository root) saying one true thing. No bug is open.

- **Memory has never been read file by file.** Candidates 1–3 rewrote 11, 14 and 8
  atoms at closure, each pass scoped to that candidate's deltas. The 25 files —
  22 product atoms in `catalog.json` plus `ARCHITECTURE.md`, `QUALITY.md`,
  `TECHSTACK.md` — carry statements nobody has verified against the module, verb,
  path or number they name; the only mechanical drift checks are `MEM-DRIFT-1`
  (diagram packages) and the frontmatter/heading lint. `CONTEXT.md` retired `lease`,
  `mode`, the `MEMORY` class, `specs doctor`, `CONSUMED`; an atom written before a
  ruling may still carry the retired sense.
- **`README.md` is written beside memory and rots.** 15 KB, hand-written, PyPI's long
  description (`readme = "README.md"`). Verified dead claims: `ACTIVE.md` and
  `CLOSURE.md` (canon v6 replaced both with `_RELEASE.json`); "four AI harnesses"
  (`L1_ENTRY_HARNESSES` holds three); "a single per-context TTL lease with a PID veto"
  (NO-LOCKS: advisory presence); "six-axis reviews" (three-axis); handoffs under
  `specs/releases/<id>/handoffs/` (they live under `.dadaia/handoff/`); "event-sourced
  JSONL, `bugs append --event reported`" (one record per bug, transitions); `dadaia
  academy` and `dadaia clean` (absent from the command tree); panel tabs Academy and
  Games (four tabs); "memory writable only in DEFINITION/CLOSURE" (MUTATING in every
  phase since candidate 2); "pre-commit lease gate" (pre-commit warns). The CLI table
  is hand-kept (18 rows, 2 dead) while `dadaia help tree` already renders the command
  tree from the live Typer app. `docs/` holds one file, `01_medium_codex.md`, a June
  vision article. Nothing measures a README sentence against the atom that should have
  produced it.
- **Two of three discovery surfaces say nothing.** `pyproject.toml` `description`
  ("AI-native workspace management CLI for multi-agent development with Claude Code,
  Codex and Kimi Code") differs from the README tagline; `keywords` (11) and
  `classifiers` exist; `[tool.poetry.urls]` is absent, so PyPI shows no Homepage,
  Repository, Documentation or Changelog link. The GitHub repository (PM verified)
  carries the description "Set of tools to optimize my AI Workflows…", no topics, no
  homepage. An agent reaching the repository root finds no machine-readable index of
  what the tool is, how to install it, where the law, the CLI reference and the
  memory catalog are.

## 2. Objective

After candidate 4 every memory file has been read against the code with a recorded
verdict and every correction applied; `README.md`, `llms.txt` and `docs/*.md` are
derived documents — every section names the atom it derives from and its content
hash, and `tests/contract/test_docs_derived_from_memory.py` is red the moment an atom
changes without its section; the CLI reference is the committed output of `dadaia
help tree`; a dead verb or path in a memory atom is a `dadaia doctor` WARNING; PyPI,
GitHub and the repository root carry one tagline, one keyword set and the links; the
external channels and their state are listed in one document with the operator's
steps recorded, never delegated to a task.

## 3. Scope (candidate 4)

- FR1 — **Memory reviewed file by file; the review is a report.** Task T-047-34
  (`product-engineer`) reads every `specs/memory/product/**/*.md` (22) and the trio
  statement by statement against the code each statement names — module, symbol,
  verb, path, number, count — and against `CONTEXT.md`'s canonical senses. Each
  statement gets one verdict: *verified* (evidence `file::symbol` or the command
  run), *corrected* (the new statement plus evidence), or *deleted* (history, a
  restatement of another home, or no referent). Every Part-1 `Measured by:` command
  is executed and its result recorded; a principle whose measure does not run or does
  not pass is an operator finding (Part 1 moves only with a decision record), never a
  silent fix. Output: `.dadaia/tmp/product-engineer/<YYYYMMDD>/memory-review.md` —
  one table row per file (`file | verdict unchanged/corrected | verified/corrected/
  deleted counts | evidence`) and one section per corrected file listing each
  correction verbatim. **The atom corrections themselves land in the closure memory
  pass (RC-FLOW step 5, FR6), never in a task write set (SPEC-DOC-047)**; docs
  authored in FR2 derive from the report's corrected truth and record the hash of the
  atom as committed, and the closure commit corrects the atom and re-records the hash
  together. AC: the report lists all 25 files with a verdict and evidence; every
  `Measured by:` in P-01…P-28 has a recorded run; the `kind: memory` closure entry
  cites the report path and the unchanged/corrected split.
- FR2 — **Memory citations are a doctor WARNING, not a red build.** The two
  dead-citation finders in `tests/contract/test_behavior_map.py`
  (`_find_dead_path_citations`, `_find_dead_verb_citations`) relocate into
  `features/specs/citations.py::dead_citations(text, *, command_paths, repo_root)`,
  and the test's `_derive_command_tree` relocates into
  `cli/help_digest.py::command_paths()` — the one Typer walk the digest, the test and
  the doctor share; the test imports both and keeps its fixtures. `dadaia doctor`'s
  `specs` section gains `MEM-DRIFT-2` (WARNING, unit = atom) in
  `features/specs/doctor_memory.py` beside `MEM-DRIFT-1`: a memory atom citing a
  `dadaia <verb>` absent from the tree or a `specs/|dadaia_workspace/|.github/` path
  absent from the repo; the CLI root passes `command_paths()` in as plain data (as
  `live_shas` travels; `features` never imports `cli`). Memory drift stays a closure
  finding (QUALITY.md, CI gates), so a verb deleted mid-implementation never reddens
  an unrelated task. AC: a fixture atom citing `dadaia fixture-verb` yields one
  `MEM-DRIFT-2` line and exit 0; `grep -c "def _find_dead_" tests/contract/
  test_behavior_map.py` is 0; the doctor rule registry and `--fix` help carry the
  code with no fix (report-only).
- FR3 — **Documents derived from memory, under one contract test.** The derived set is
  `README.md`, `llms.txt` and every `docs/*.md` — a glob, never a list. Every `## `
  heading is followed by one or more markers `<!-- derived-from: <slug>
  sha256:<12 hex of the atom file> -->`; `<slug>` resolves by stem to exactly one file under
  `specs/memory/` (a product atom or `ARCHITECTURE`/`QUALITY`/`TECHSTACK`), the hash
  is that file's current sha256 (whole file, as `behavior-map.json`'s `hash_tuple`),
  and there is no `derived-from: none` — a section that can name no atom is slop or
  names a fact memory lacks (added at closure). `docs/cli.md` carries no marker and
  is instead body-equal, after its version-stamp line, to `render_digest()`;
  regenerate with `dadaia help tree > docs/cli.md`. `tests/contract/
  test_docs_derived_from_memory.py` (Intent: CONTRACT, SMALL) checks marker
  presence, slug resolution, hash currency and the `cli.md` body, failing with
  `<doc>#<heading>: derived-from <slug> stale — re-read <atom path>, re-derive the
  section, re-record sha256:<current>`; in-memory mutation fixtures prove each red
  direction. Content: `README.md` (≤ 10 KB, the PyPI long description) in the three
  blocks of Q1 — *What it is and principles* ([[product-vision]]), *A human installs
  and uses it* ([[pypi-distribution]], [[workspace-init]], [[context-management]],
  [[workspace-doctor]], [[panel]]), *An agent reads DADAIA.md and uses it*
  ([[harness-claude-code]], [[harness-codex]], [[harness-kimi-code]],
  [[agent-orchestration]], [[sdd-gate-v3]], [[agent-comms]]) — plus *Links*
  ([[pypi-distribution]]); `docs/getting-started.md` (install → `dadaia init` →
  `context bind` → `doctor` → `panel` → first candidate, what each step creates);
  `docs/concepts.md` (context, release and candidate, the flow, the gate, memory,
  bugs and backlog, audits — one paragraph each, `CONTEXT.md` for terms);
  `docs/cli.md`; `docs/distribution.md` (FR4); `llms.txt` at the repository root
  (llmstxt.org shape: `# dadaia-workspace`, `> <tagline>`, then link lists — what it
  is, install, the law `dadaia_workspace/public/data/DADAIA.md`, `docs/cli.md`,
  `specs/memory/product/index.md`; every line links, none restates).
  `docs/01_medium_codex.md` is deleted without replacement (Q6 corrected: a
  `docs/vision.md` restating the atom README block 1 already derives from fails the
  deletion test). Every sentence in the set traces to an atom statement or to the
  review report's corrected statement; no fact enters a doc that memory does not
  carry. AC: the test is green over the whole set; one added sentence with no atom
  fails the review, one changed atom byte fails the test; `wc -c README.md` ≤ 10240;
  `ls docs` is exactly `cli.md concepts.md distribution.md getting-started.md`.
- FR4 — **One tagline, one keyword set, the links, the channel list.** `pyproject.toml`:
  `description` becomes the tagline, `[tool.poetry.urls]` gains `Homepage`,
  `Repository`, `Documentation` (`docs/` tree URL), `Changelog`, `Issues`;
  `keywords` and `classifiers` are verified against the README (a keyword naming
  nothing the README says dies). The tagline has one home per surface and one test:
  `README.md`'s first non-badge paragraph == `pyproject.toml` `description` ==
  `llms.txt`'s `>` line (`tests/contract/test_docs_derived_from_memory.py`, same
  file). GitHub topics are the pyproject keywords, the description is the tagline,
  the homepage is the PyPI page (Q10) — settings state no file carries, so the PM
  runs `gh repo edit --description … --homepage … --add-topic …` and records the
  result and `gh repo view --json description,repositoryTopics,homepageUrl` in the
  `_RELEASE.json` `log` (as candidate 2 recorded branch protection).
  `docs/distribution.md` (derived from [[pypi-distribution]]) is one table —
  channel, artifact, state, who acts — over: PyPI (long description = README,
  automatic at the next publish), GitHub description/topics/homepage (PM, recorded),
  `llms.txt` (this candidate), awesome-lists of agentic tooling (operator
  submission), the Claude Code plugin/skills registry (blocked by backlog
  `plugin-packaging-and-skill-evals`). Operator steps are listed in the SPEC and the
  closure `dispositions` entry, never as tasks. AC: `pip download`-free check —
  `python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb'))['tool']
  ['poetry']; print(sorted(d['urls']))"` prints the five keys; the tagline test is
  green; the `log` carries the `gh repo view` line.
- FR5 — **The closure protocol re-derives.** `dd-release-implementation`'s
  `MEMORY-UPDATE.md` gains one protocol step after the atom update: run
  `pytest tests/contract/test_docs_derived_from_memory.py`; for every named section
  re-read the atom, re-derive the section, re-record its hash — in the same commit as
  the atom; RC-FLOW step 5's Done-when adds "the derived docs test is green".
  `behavior-map.json`'s hash for the skill is re-recorded; reprojected. AC:
  `grep -n derived-from dadaia_workspace/public/skills/dd-release-implementation/
  MEMORY-UPDATE.md` hits once; `dadaia public doctor` reports `[ok] public-privacy`.
- FR6 — **Closure.** Memory pass applying the FR1 report: every *corrected* and
  *deleted* statement lands; [[product-vision]] gains the tagline as its identity line
  and the two usage paths (human, agent) the README derives from;
  [[pypi-distribution]] records the metadata contract (tagline = description, urls,
  keywords = topics, README as long description) and the channel list;
  [[workspace-doctor]] gains `MEM-DRIFT-2`; `ARCHITECTURE.md` Part 2 rows for
  `citations.py` and `command_paths()`; `QUALITY.md` Part 2 names the derived-docs
  test beside the ratchets; catalog and index regenerated; every derived section
  whose atom changed re-derived and re-recorded in the same commit (FR5); `CHANGELOG.md
  [0.4.7]` candidate 4; `dadaia release phase CLOSURE`; `backlog exit
  docs-derived-from-memory-and-distribution --disposition delivered --release 0.4.7`;
  the `log` entries; `dadaia doctor` 100 % with zero `MEM-DRIFT-2` lines.

## 4. Out of scope

- A documentation site (mkdocs, Pages), a `dadaia docs` verb, section-granular atom
  hashing, translations.
- The plugin/skills-registry packaging (backlog `plugin-packaging-and-skill-evals`)
  and the external submissions themselves (operator steps, FR4).
- Any Part-1 principle change beyond what FR1's report surfaces as an operator
  finding; a new principle for doc derivation is Q8, a proposed decision record only.
- Gating docs at the push: the derived-docs test runs in the suite like every contract
  test; no hook, no doctor rule for docs.

## 5. Dependencies, risks, questions

- Sequencing: candidate 3 (T-047-25..33) edits `test_behavior_map.py` (body-pointer
  finder), `MEMORY-UPDATE.md`, `RC-FLOW.md`, the personas (`product-engineer` gains
  `Bash`) and eight atoms at its closure; candidate 4 starts after its merge and
  rc-archive, and T-047-34 reads post-candidate-3 memory. `docs/cli.md` is generated
  after candidate 3, so it carries `dadaia audit` and `release phase`.
- FR1 is the largest read of the release (25 files, ~14 k tokens of atoms) and
  produces no repo diff; its value is the report and the closure pass it drives. The
  review is by `product-engineer` alone — reading code is not implementing.
- FR3's hash is whole-file: any atom byte change reddens every section derived from
  it, and the reviewer re-reads the atom — the intended cost; `behavior-map.json`
  carries the same cost for skills today.
- FR2 relocates ~60 test lines into the package and adds one doctor rule; against the
  deletion test, without `MEM-DRIFT-2` a retired verb in an atom is found only by a
  human reading 25 files — the state this candidate exists to end.
- Net: additions are one test file, one doctor rule, one `citations.py`, one
  `command_paths()`, four docs, one `llms.txt`, one pyproject table; deletions are
  `docs/01_medium_codex.md`, the README's 2 dead verbs and 9 dead claims, the
  test-local finders and tree walk, the hand-kept CLI table. Production net is small
  and positive; the closure `summary` applies the deletion test to each addition.
- Privacy: `docs/00_medium_mine.md` stays gitignored (operator's own); the full
  denylist scan covers every new tracked file.

Q1–Q6 answered by the PM (recorded here; Q3 and Q6 corrected by inspection):

- Q1 README for the human first, the agent second, three blocks — adopted (FR3).
- Q2 one source: `derived-from` marker with the atom's content hash, re-recorded by
  review — adopted; no generator verb (JSONL/CLI-by-reflex rule; the behavior-map
  pattern re-records by review and the test names what to re-read).
- Q3 CLI reference generated, never hand-written — adopted; **corrected**: generated
  by the existing `dadaia help tree` renderer, not at `public stage` (which runs in
  consumer workspaces where `docs/` does not exist; a second renderer fails the
  deletion test).
- Q4 GitHub description + topics + homepage via `gh repo edit`, recorded in the
  `log`; pyproject metadata verified against the README — adopted (FR4).
- Q5 channels: PyPI, GitHub topics, `llms.txt`, awesome-lists, skills/plugin registry;
  artifacts by the candidate, submissions by the operator — adopted (FR4).
- Q6 `docs/01_medium_codex.md` deleted — adopted; **corrected**: no `docs/vision.md`
  (README block 1 is the atom's only derivation; a second one is slop).

Q7–Q10 answered by the PM under the operator's 2026-09-12 directive — the recommended
answers below are adopted (each reversible in one commit; Q8's decision record stays
`proposed` until the operator flips it):

- Q7 `Development Status :: 3 - Alpha` — keep; a classifier is a claim, and the
  consumer-validation gate has not certified a post-0.4.7 wheel yet.
- Q8 Admit "We derive every human- and agent-facing document from a named memory atom
  under a content hash" as QUALITY.md P-29 with a `proposed` decision record at
  closure (measured by `pytest tests/contract/test_docs_derived_from_memory.py`) —
  yes; the operator flips it.
- Q9 Docs author: `software-engineer` writes the derived docs from the atoms and the
  FR1 report (a mechanical derivation), `product-engineer` re-derives at every closure
  — recommended; the alternative (PE authors all prose) puts a repo artifact under a
  persona whose write set is `specs/`.
- Q10 GitHub homepage: the PyPI project page (no docs site exists) — recommended.
