# Closure: Release — memory-markdown-source-v1

> **Status:** Aprovado
> **Release ID:** memory-markdown-source-v1
> **Owner:** product-engineer
> **Closed:** 2026-06-01

## Summary

This release retires the YAML/HTML dual-file memory model introduced by
`memory-structured-source-v1` and replaces it with a single Markdown-source format.
All 21 memory atoms now live as `.md` files with strict YAML frontmatter
(`memory-frontmatter-v1` schema; `additionalProperties: false`) and a Markdown body
validated by a `##` heading allowlist. The YAML source files and the committed HTML
files were deleted; HTML is now ephemeral — the panel renders `.md` → HTML in-memory
via `mistune~=3.0` (D-1) with custom hooks for Mermaid fences, `[[wikilink]]` anchors,
and an XSS sanitiser (D-4).

The Step-0 protocol was extracted from all 21 agent personas into a single shared skill
(`dadaia-step0-memory-bootstrap`), eliminating ~400 tokens of per-persona duplication.
`ctx-inject.sh` was repointed from `tech-stack.html` + a strip pass to `tech-stack.md`
verbatim, reducing the injection payload from ~4.6 K to ~2.4 K tokens (target ≤ 3 K).
The old `strip-memory-html.py` helper, four Jinja templates, four YAML schemas, and the
`dadaia memory render` / `dadaia migrate memory-yaml` CLI subcommands were all deleted.

The QA gate (T-MMS-13) reported APPROVED across all 10 acceptance criteria: 2399 tests
passed / 0 failed; ruff, mypy --strict, `dadaia specs doctor`, and `dadaia public doctor`
all exit 0; panel renders all 21 atoms from `.md` source with correct Mermaid blocks.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-MMS-W0-01 | Heading corpus enumeration (ai-engineer) | `see release branch` |
| T-MMS-W0-02 | stdlib vs mistune renderer proof-of-concept (ai-engineer) | `see release branch` |
| T-MMS-01 | `lint-memory-atoms.py` implementation (software-engineer-python) | `see release branch` |
| T-MMS-02 | `generate-memory-catalog.py` implementation (software-engineer-python) | `see release branch` |
| T-MMS-03 | `memory-frontmatter-v1.schema.json` (software-engineer-python) | `see release branch` |
| T-MMS-04 | Born-markdown scaffold template (software-engineer-python) | `see release branch` |
| T-MMS-05 | Shared Step-0 skill + 21 persona updates (ai-engineer) | `see release branch` |
| T-MMS-06 | Panel `md → html` inline render in `views/memory.py` (software-engineer-python) | `see release branch` |
| T-MMS-07 | `ctx-inject.sh` repoint to `tech-stack.md` verbatim (software-engineer-python) | `see release branch` |
| T-MMS-W2-FIX | Reconcile 11 failing tests + SPEC-DOC-002L guard fix (software-engineer-python) | `see release branch` |
| T-MMS-08 | Migrate 21 HTML atoms to `.md` (product-engineer, CLOSURE) | `see release branch` |
| T-MMS-09 | Lint all 21 atoms + generate final `catalog.json` (product-engineer, CLOSURE) | `see release branch` |
| T-MMS-10 | Delete `.yaml` and `.html` atom files; update `.gitignore` (product-engineer, CLOSURE) | `see release branch` |
| T-MMS-11 | Doctor rework: remove STRUCT/SYNC, add LINT-1, adapt checks #2 and #8 (software-engineer-python) | `see release branch` |
| T-MMS-12 | Delete lib assets (4 schemas, 4 templates, strip script, 3 yaml scaffolds) + propagate (devops-engineer) | `see release branch` |
| T-MMS-13 | QA acceptance gate — 10 AC verified, APPROVED (qa-engineer) | `see release branch` |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Full pytest suite — 2399 passed / 0 failed | `pytest` | `2399 passed, 0 failed` (QA report) |
| ruff linter clean | `ruff check .` | exit 0 |
| mypy --strict clean | `mypy dadaia_workspace` | exit 0 |
| specs doctor exit 0 — no STRUCT/SYNC warnings | `dadaia specs doctor` | exit 0, 0 errors, 0 warnings |
| public doctor exit 0 | `dadaia public doctor` | exit 0, 0 drift |
| lint-memory-atoms exit 0 on all 21 atoms | `python lint-memory-atoms.py specs/memory/` | exit 0 |
| catalog.json has 18 product feature entries | `python generate-memory-catalog.py` | 18 entries, slugs match `.md` files |
| ctx-inject.sh token injection ≤ 3 K | manual token count | ~2.4 K tokens (tech-stack.md + catalog.json) |
| Panel renders all 21 atoms from .md with Mermaid | `dadaia panel` + browser smoke | AC-4 PASS (QA report) |
| No .yaml or .html memory atoms committed | `git ls-files specs/memory/` | no `.yaml`/`.html` listed |
| QA gate — all 10 AC PASS | `.dadaia/reports/dadaia-workspace/qa-engineer/` | verdict APPROVED |

## Drifts

### mistune-added-to-runtime-venv

**Description:** D-1 decision (grill-me 2026-06-01) approved `mistune~=3.0` as a
runtime dependency. The stdlib renderer proof-of-concept (T-MMS-W0-02) confirmed that
stdlib coverage was insufficient for GFM tables. Adding `mistune` required updating
`pyproject.toml` and rebuilding the lock file.

**Resolution:** `mistune~=3.0` added to `pyproject.toml` runtime deps. Zero transitive
dependencies. The `jsonschema` dep was retained for `memory-frontmatter-v1.schema.json`
validation in `lint-memory-atoms.py`; the four per-atom YAML schemas that previously
drove STRUCT-1..4 were deleted.

**Memory updates:** `specs/memory/tech-stack.md` — added `mistune~=3.0` entry under
approved deps; updated `jsonschema` note; removed stale YAML/Jinja machinery note.

### ctx-inject-token-count-over-3k-target

**Description:** The SPEC AC-3 target was ≤ 3 K tokens for the total ctx-inject payload.
The implemented payload (tech-stack.md verbatim + catalog.json) measures approximately
2.4 K tokens — within the 3 K ceiling. However, on larger consumer repos where
`tech-stack.md` or the feature catalog is more verbose, the payload could approach the
limit. This is non-blocking for this repo.

**Resolution:** Accepted as non-blocking. The `token_estimate` field in each atom's
frontmatter gives future operators a signal to trim if needed. `lint-memory-atoms.py`
warns on > 20% drift (D-3).

**Memory updates:** `specs/memory/architecture.md` — lean payload table updated to
reflect ~2.4 K actual (not the former ~4.6 K).

### ac-2-wording-corrected

**Description:** SPEC §8 AC-2 originally stated "21 entries" for the catalog. In
practice, `architecture.md` and `tech-stack.md` are `category: core` / `agent_tier:
inject` and are excluded from the product feature catalog; `index.md` is the generated
TOC. The catalog correctly contains 18 product feature entries.

**Resolution:** AC-2 wording updated in `SPEC.md` to read "18 product feature entries
(architecture + tech-stack are core/injected; index.md is the generated TOC — all
excluded from the catalog features)".

**Memory updates:** None beyond SPEC.md correction.

## Memory updates

- `specs/memory/architecture.md` — rewrote "Structured-memory-source subsystem" section
  content (heading reused; content replaced with Markdown-source reality); updated lean
  payload table to ~2.4 K;
  updated ctx-inject.sh description (verbatim .md, no strip pass); updated catalog.json
  pipeline (frontmatter reader, not HTML scraping); updated CAT-1 check (.md files);
  updated Step-0 reference to shared skill; updated state runtime entry from `.html` to
  `.md`; updated mermaid diagram to show `.md` self-pull; `last_updated: 2026-06-01`,
  `release_origin: memory-markdown-source-v1`.
- `specs/memory/tech-stack.md` — added `mistune~=3.0` to approved deps; updated
  `jsonschema` usage note; updated `pyyaml` note; removed stale Jinja2 sentence;
  updated Linguagens table (consolidated Markdown/YAML row; removed strip-memory-html.py
  note; updated Bash ctx-inject token count); `release_origin: memory-markdown-source-v1`.
- `specs/memory/product/specs-doctor.md` — removed STRUCT-1..4/SYNC-1/YAML-absent
  section; added LINT-1 invariant table; updated SPEC-DOC-002 (now checks `.md`);
  added SPEC-DOC-002L (stray `.html`); noted SPEC-DOC-008 retired; updated Fluxo de uso;
  updated Estado runtime tocado (`.md` files); updated error codes line;
  `release_origin: memory-markdown-source-v1`.
- `specs/memory/product/panel.md` — updated summary frontmatter (memory .md via mistune);
  updated memory view description (in-memory render, not verbatim HTML, D-4); updated
  Diferencial (mistune dep, two-route split clarified); updated specs-doctor dependency
  line (SPEC-DOC-008 retired, LINT-1 active); updated Estado runtime tocado (.md atoms);
  updated runtime deps note (added mistune); `release_origin: memory-markdown-source-v1`.
- `specs/memory/product/index.md` — not updated (generated TOC; orchestrator regenerates
  from frontmatter via `generate-memory-catalog.py`).

## Backlog returns

- `backlog/candidates.md` — `memory-structured-source-migration-v2` entry superseded and
  removed; this release is its complete replacement. No new candidates filed.

## Archive decision

**MOVE** — release directory will be moved to
`specs/_archive/releases/memory-markdown-source-v1/` via `git mv`. `ACTIVE.md` will be
updated to `release: none` (or the next queued release, if any).

This release supersedes `memory-structured-source-migration-v2` (WIP preserved at commit
`b980991` on branch `release/memory-structured-source-migration-v2`). That branch is now
stale and may be deleted after archive.
