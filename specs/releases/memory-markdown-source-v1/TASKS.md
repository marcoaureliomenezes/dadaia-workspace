# TASKS — Release: memory-markdown-source-v1

**Status:** Aprovado
**Release ID:** memory-markdown-source-v1
**Owner:** product-engineer

---

## Wave 0 — Decisions

### T-MMS-W0-01
- **Status:** `[x]`
- **Wave:** W0
- **Owner:** ai-engineer
- **Description:** Enumerate every `##` heading used across the 21 current HTML memory
  atoms. Produce a heading corpus report so PE can finalise the allowlist for
  `lint-memory-atoms.py`.
- **Write set:** `.dadaia/reports/dadaia-workspace/ai-engineer/` (report only; no source
  changes)
- **Preconditions:** None
- **Done when:** Report lists every distinct `##` heading found in all 21 atoms; PE
  confirms allowlist is complete (OQ-2 closed).

### T-MMS-W0-02
- **Status:** `[x]`
- **Wave:** W0
- **Owner:** ai-engineer
- **Description:** Proof-of-concept stdlib Markdown renderer: render `architecture.html`
  and `tech-stack.html` (two rich atoms with tables and Mermaid) using only Python stdlib
  (`html.parser`, string manipulation). Document what is lost vs not lost. Compare with
  `mistune` output on the same atoms. Deliver findings so PE can close OQ-1 and OQ-3.
- **Write set:** `.dadaia/reports/dadaia-workspace/ai-engineer/` (report only)
- **Preconditions:** None
- **Done when:** Report includes coverage assessment (tables, Mermaid fences, wikilinks,
  nested lists) for stdlib vs `mistune`; recommends one path; PE closes OQ-1 and OQ-3.

---

## Wave 1 — New toolchain

> Precondition for all W1 tasks: OQ-1, OQ-2, OQ-3, OQ-4 resolved (W0 done).
> W1 tasks are parallel and disjoint within the wave.

### T-MMS-01
- **Status:** `[x]`
- **Wave:** W1
- **Owner:** software-engineer-python
- **Description:** Implement `dadaia_workspace/public/scripts/lint-memory-atoms.py`.
  Checks: (a) frontmatter present and parseable as YAML; (b) required fields: `slug`,
  `title`, `category`, `tldr`, `summary`, `tags`, `agent_tier`, `token_estimate`,
  `last_updated`, `release_origin`; (c) `additionalProperties: false` (no extra fields);
  (d) `##` headings are a subset of the allowlist (from OQ-2); (e) no duplicate `##`
  headings; (f) `[[slug]]` wikilinks resolve to real `.md` files in `specs/memory/`;
  (g) `token_estimate` drift warning (> 20% from actual count, per OQ-3 resolution);
  (h) forbidden headings check (`## Changelog`, `## Histórico`, `## History`,
  `## Versions`). Exit 0 = all atoms valid. Exit 1 = at least one ERROR. Exit 2 =
  warnings only.
- **Write set:** `dadaia_workspace/public/scripts/lint-memory-atoms.py`; unit tests
  under `tests/`
- **Preconditions:** W0 complete; allowlist from T-MMS-W0-01 finalised by PE
- **Done when:** Unit tests pass for each check type (valid atom, missing field, extra
  field, forbidden heading, bad wikilink, duplicate heading, token drift); `pytest` green

### T-MMS-02
- **Status:** `[x]`
- **Wave:** W1
- **Owner:** software-engineer-python
- **Description:** Implement `dadaia_workspace/public/scripts/generate-memory-catalog.py`.
  Reads frontmatter from all `*.md` files in `specs/memory/product/`; writes
  `catalog.json` with schema `{generated_at, context, features: [{slug, title, category,
  tldr, summary, tags, token_estimate, agent_tier}]}`. Idempotent (safe to re-run).
- **Write set:** `dadaia_workspace/public/scripts/generate-memory-catalog.py`; unit tests
- **Preconditions:** W0 complete
- **Done when:** Unit tests cover: empty product dir, single atom, multiple atoms, missing
  frontmatter field (should error); output catalog.json matches expected schema; `pytest`
  green

### T-MMS-03
- **Status:** `[x]`
- **Wave:** W1
- **Owner:** software-engineer-python
- **Description:** Write the frontmatter JSON schema (`memory-frontmatter-v1.schema.json`)
  used by `lint-memory-atoms.py`. Strict: `additionalProperties: false`. Required fields
  from SPEC §3.1. Place in `dadaia_workspace/public/schemas/memory/`. Update
  `lint-memory-atoms.py` to validate against it if OQ-3 resolution calls for it.
- **Write set:** `dadaia_workspace/public/schemas/memory/memory-frontmatter-v1.schema.json`
- **Preconditions:** W0 complete
- **Done when:** Schema file written; validates correctly against 2 positive and 2 negative
  fixture YAML blocks; lint script uses it

### T-MMS-04
- **Status:** `[x]`
- **Wave:** W1
- **Owner:** software-engineer-python
- **Description:** Born-markdown scaffold template: create `.md` atom scaffold files under
  `dadaia_workspace/public/scaffold/memory/`. Update `dadaia specs scaffold` (or
  `dadaia memory product add`) to generate `.md` output instead of `.yaml`. The scaffold
  `.yaml` files (`architecture.yaml`, `tech-stack.yaml`, `product/index.yaml`) are
  replaced by `.md` equivalents with frontmatter stubs and section placeholders.
- **Write set:** `dadaia_workspace/public/scaffold/memory/*.md`;
  `dadaia_workspace/features/spec_artifacts/memory.py` (or equivalent scaffolder path)
- **Preconditions:** T-MMS-03 done (frontmatter schema finalised)
- **Done when:** `dadaia memory product add <slug>` creates a `.md` file with valid
  frontmatter; unit test verifies scaffold output passes `lint-memory-atoms.py`

---

## Wave 2 — Panel render + ctx-inject + shared Step-0

> Precondition for all W2 tasks: W1 complete and `pytest` green.
> Track A (T-MMS-05) and Track B (T-MMS-06, T-MMS-07) are disjoint — may run in parallel.

### T-MMS-05 (Track A)
- **Status:** `[x]`
- **Wave:** W2 / Track A
- **Owner:** ai-engineer
- **Description:** Extract the Step-0 protocol into a single shared skill file at
  `dadaia_workspace/public/skills/dadaia-step0-memory-bootstrap.md`. Update all 21 agent
  persona files under `dadaia_workspace/public/agents/` to reference the skill instead of
  inlining the ~400-token Step-0 block. Verify that persona routing logic is unchanged.
- **Write set:** `dadaia_workspace/public/skills/dadaia-step0-memory-bootstrap.md`;
  21 files under `dadaia_workspace/public/agents/`
- **Preconditions:** W1 complete
- **Done when:** Shared skill file exists; all 21 personas reference it; no persona
  still contains an inline Step-0 copy; `pytest` green after propagation
- **Parallelism note:** Disjoint from T-MMS-06 and T-MMS-07 (different write sets)

### T-MMS-06 (Track B)
- **Status:** `[-]`
- **Wave:** W2 / Track B
- **Owner:** software-engineer-python
- **Description:** Panel `md → html` inline render in
  `dadaia_workspace/features/panel/views/memory.py`. The view reads the `.md` source
  file, converts it to HTML using the renderer resolved by OQ-1, sanitises output (no
  inline `<script>` / `<style>` passthrough), and returns the rendered bytes. Path
  traversal guard must extend to cover `.md` files. Retire SPEC-DOC-008 byte-identity
  invariant from docstring and tests (it applied to committed HTML; MD source is now the
  canonical artefact).
- **Write set:** `dadaia_workspace/features/panel/views/memory.py`; updated tests
- **Preconditions:** W1 complete; OQ-1 resolved (renderer choice known)
- **Done when:** Panel serves 3 reference atoms (architecture, tech-stack, one feature)
  from `.md` source with correct Mermaid blocks visible; path traversal test passes;
  SPEC-DOC-008 assertion removed from test; `pytest` green
- **Parallelism note:** Disjoint from T-MMS-05

### T-MMS-07 (Track B)
- **Status:** `[x]`
- **Wave:** W2 / Track B
- **Owner:** software-engineer-python
- **Description:** Repoint `ctx-inject.sh` from `tech-stack.html` + strip pass to
  `tech-stack.md` verbatim. Remove the `python3 "$STRIP" "$TECH_FILE"` invocation and
  `STRIP` variable. Update the catalog path logic: if `catalog.json` exists, use it
  (unchanged); else fall back to stripped `product/index.html` — **change fallback** to
  `product/index.md` verbatim if `.html` is absent. Total injection target: ≤ 3 K tokens.
- **Write set:** `dadaia_workspace/public/scripts/ctx-inject.sh`
- **Preconditions:** W1 complete
- **Done when:** `ctx-inject.sh` references `.md`; no call to `strip-memory-html.py`;
  manual token-count verification on a real atom ≤ 3 K; updated integration test passes
- **Parallelism note:** Disjoint from T-MMS-05

---

## Wave 3 — Migration (CLOSURE-phase, PE-only)

> Precondition: W2 complete, all tests green, ACTIVE.md phase = CLOSURE.
> These tasks are PE-only and sequential.

### T-MMS-08
- **Status:** `[ ]`
- **Wave:** W3 / CLOSURE
- **Owner:** product-engineer
- **Description:** Implement `migrate-html-to-md.py` (in-session script, not a permanent
  tool). Convert each of the 21 HTML atoms to Markdown using `html2text` or `pandoc`.
  Apply frontmatter scaffold from T-MMS-04. Review each converted atom for fidelity;
  fix conversion artefacts (escaped characters, broken tables, lost Mermaid fences).
  Write 21 `.md` files to `specs/memory/` and `specs/memory/product/`.
- **Write set:** `specs/memory/architecture.md`, `specs/memory/tech-stack.md`,
  `specs/memory/product/index.md`, `specs/memory/product/*.md` (18 feature atoms).
  Migration script itself is ephemeral (`.dadaia/tmp/`).
- **Preconditions:** ACTIVE.md phase = CLOSURE; W2 complete
- **Done when:** 21 `.md` files exist; each passes `lint-memory-atoms.py` (no errors)

### T-MMS-09
- **Status:** `[ ]`
- **Wave:** W3 / CLOSURE
- **Owner:** product-engineer
- **Description:** Run `lint-memory-atoms.py` on all 21 atoms; fix any remaining
  violations. Run `generate-memory-catalog.py` to produce final `catalog.json` with 21
  entries. Verify `catalog.json` matches current production feature list.
- **Write set:** `specs/memory/product/catalog.json`; possible fixes to `.md` atoms
- **Preconditions:** T-MMS-08 done
- **Done when:** `lint-memory-atoms.py` exits 0 on all 21 atoms; `catalog.json` has 21
  entries with correct slugs, titles, and tldr values

### T-MMS-10
- **Status:** `[ ]`
- **Wave:** W3 / CLOSURE
- **Owner:** product-engineer
- **Description:** Delete committed `.yaml` and `.html` memory atom files. Add
  `specs/memory/**/*.html` to the repository `.gitignore` (or the relevant
  `.gitignore` under `specs/memory/`). Verify no `.yaml` or `.html` atom files remain
  tracked by git.
- **Write set:** `specs/memory/` (deletes); `.gitignore`
- **Preconditions:** T-MMS-09 done
- **Done when:** `git status` shows no tracked `.yaml` or `.html` memory files; `.gitignore`
  excludes `*.html` under `specs/memory/`

---

## Wave 4 — Delete old subsystem + doctor + propagation + QA gate

> Precondition: W3 complete (21 atoms committed as `.md`).
> T-MMS-11 and T-MMS-12 may run in parallel (disjoint write sets).

### T-MMS-11
- **Status:** `[ ]`
- **Wave:** W4
- **Owner:** software-engineer-python
- **Description:** Update `dadaia_workspace/features/specs/doctor.py`:
  remove STRUCT-1..STRUCT-4 and SYNC-1 checks; remove YAML-absent warning; remove
  SPEC-DOC-008 byte-identity invariant; add LINT-1 check (calls `lint-memory-atoms.py`,
  ERROR on frontmatter violations, WARNING on token drift); adapt check #2 to require
  `.md` not `.html`; adapt check #8 to grep `.md` body (no escape hatch). Remove
  memory atom render path from `features/specs/renderer.py`. Add `.md` frontmatter
  reader to `features/specs/catalog.py`. Update `cli/commands/memory.py`: remove
  `dadaia memory render` and `dadaia migrate memory-yaml` subcommands. Adapt all
  affected tests.
- **Write set:** `dadaia_workspace/features/specs/doctor.py`;
  `dadaia_workspace/features/specs/renderer.py`;
  `dadaia_workspace/features/specs/catalog.py`;
  `dadaia_workspace/cli/commands/memory.py`; affected test files
- **Preconditions:** W3 complete
- **Done when:** `dadaia specs doctor` exits 0 on the workspace; no STRUCT/SYNC warnings;
  LINT-1 fires correctly on a malformed atom fixture; `pytest` green
- **Parallelism note:** Disjoint from T-MMS-12

### T-MMS-12
- **Status:** `[ ]`
- **Wave:** W4
- **Owner:** devops-engineer
- **Description:** Delete lib-originated assets no longer needed:
  `public/schemas/memory/memory-architecture-v1.schema.json`,
  `public/schemas/memory/memory-tech-stack-v1.schema.json`,
  `public/schemas/memory/memory-product-index-v1.schema.json`,
  `public/schemas/memory/memory-product-feature-v1.schema.json`;
  `public/templates/memory-architecture.html.j2`,
  `public/templates/memory-tech-stack.html.j2`,
  `public/templates/memory-product-index.html.j2`,
  `public/templates/memory-product-feature.html.j2`;
  `public/scripts/strip-memory-html.py`;
  `public/scaffold/memory/*.yaml` (3 files).
  Run `dadaia public stage && dadaia public install --target all`.
  Run `dadaia public doctor` (must exit 0).
- **Write set:** `dadaia_workspace/public/` (deletes); `.dadaia/agentic/` (staging);
  runtime projections
- **Preconditions:** W3 complete; T-MMS-11 not blocking (disjoint write sets)
- **Done when:** All 4+4+1+3 listed files deleted from `public/`; `dadaia public doctor`
  exits 0; `dadaia public install` propagated to all runtimes
- **Parallelism note:** Disjoint from T-MMS-11

### T-MMS-13
- **Status:** `[ ]`
- **Wave:** W4
- **Owner:** qa-engineer
- **Description:** Acceptance gate. Verify all 10 AC criteria from SPEC §8.
  Run `pytest` (exit 0). Run `dadaia specs doctor` (exit 0). Run `dadaia public doctor`
  (exit 0). Verify panel renders all 21 atoms correctly. Verify `ctx-inject.sh` injection
  token count ≤ 3 K. Verify no `.yaml` or `.html` memory atoms committed. Record
  evidence (commit SHAs or stdout snippets) for each AC.
- **Write set:** `.dadaia/reports/dadaia-workspace/qa-engineer/` (report)
- **Preconditions:** T-MMS-11 and T-MMS-12 both done
- **Done when:** QA report filed; all 10 ACs explicitly marked PASS; handoff verdict
  = APPROVED

---

## Parallelism summary

| Wave | Tasks | Can run in parallel? |
|------|-------|---------------------|
| W0 | T-MMS-W0-01, T-MMS-W0-02 | Yes (disjoint) |
| W1 | T-MMS-01..04 | Yes (disjoint write sets) |
| W2 | T-MMS-05 (Track A) ‖ T-MMS-06 + T-MMS-07 (Track B) | Track A and B are disjoint |
| W3 | T-MMS-08 → T-MMS-09 → T-MMS-10 | Sequential (PE-only, CLOSURE-gated) |
| W4 | T-MMS-11 ‖ T-MMS-12 → T-MMS-13 | 11 and 12 parallel; 13 after both |

> Maximum one `[-]` per owner at a time. The W3 tasks are all PE-owned and sequential;
> only one may be `[-]` at a time. The W4 parallel tasks have different owners (se-python
> and devops-engineer), so both may be `[-]` simultaneously.
