# PLAN — Release: memory-markdown-source-v1

**Status:** Draft
**Release ID:** memory-markdown-source-v1
**Owner:** product-engineer

---

## 1. Strategy

Foundation-first across four waves. Each wave has a clear gate before the next begins.
OQ-1..OQ-4 are resolved at W0/W1 so no design decision defers to implementation.

The 21-atom CLOSURE migration (W3) is PE-only and gate-locked to the CLOSURE phase.
Everything before that is toolchain work that does not touch committed memory atoms.

---

## 2. Layers affected

| Layer | Change |
|-------|--------|
| `public/scripts/` | Delete `strip-memory-html.py`; update `ctx-inject.sh` |
| `public/schemas/memory/` | Delete 4 `memory-*.schema.json` files |
| `public/templates/` | Delete 4 `memory-*.html.j2` files |
| `public/scaffold/memory/` | Replace `.yaml` scaffolds with `.md` scaffolds |
| `features/specs/doctor.py` | Remove STRUCT/SYNC checks; add LINT-1; adapt check #2 and #8 |
| `features/specs/catalog.py` | Add `.md` frontmatter reader path |
| `features/specs/renderer.py` | Remove memory atom render path |
| `features/panel/views/memory.py` | Add `md → html` inline render; retire SPEC-DOC-008 |
| `cli/commands/memory.py` | Remove `dadaia memory render`; remove `dadaia migrate memory-yaml` |
| `specs/memory/*.md` (21 files) | Created in CLOSURE by PE via migration script |
| All 21 agent personas | Step-0 updated to reference shared skill |

---

## 3. Execution waves

### W0 — Decisions and open questions (product-engineer + ai-engineer)

Gate: all OQ resolved and documented as decisions in this PLAN before W1 begins.

- Resolve OQ-2: enumerate all `##` headings used across 21 current HTML atoms.
  ai-engineer scans the HTML corpus and reports the heading set to PE.
- Resolve OQ-1: evaluate stdlib Markdown renderer coverage. ai-engineer implements a
  proof-of-concept render of 2–3 rich atoms (one with tables, one with Mermaid). If
  stdlib covers it, no new dep. If not, `mistune` is added.
- Resolve OQ-3: lint token_estimate policy — auto-recompute requires `tiktoken` (PyPI);
  manual update with lint warning is acceptable if adding deps is undesirable.
- Resolve OQ-4: gitignore scope for rendered HTML output.

### W1 — New toolchain (software-engineer-python)

Gate: W0 decisions committed. W1 tasks may proceed in parallel within the wave.

- **T-MMS-01** `lint-memory-atoms.py`: frontmatter required-fields check,
  `additionalProperties` check, heading allowlist check, no-duplicate headings, wikilink
  resolution, token_estimate drift warning, forbidden-heading check.
- **T-MMS-02** `generate-memory-catalog.py`: frontmatter → `catalog.json`; output schema
  matches current catalog.json shape; idempotent.
- **T-MMS-03** Frontmatter JSON schema (single file replacing the 4 YAML schemas): strict,
  `additionalProperties: false`, required fields from SPEC §3.1. Used by lint script.
- **T-MMS-04** Born-markdown scaffold template (`.md` with frontmatter stub); update
  `dadaia specs scaffold` / `dadaia memory product add` to generate `.md` not `.yaml`.

### W2 — Panel render + ctx-inject repoint + shared Step-0 skill (parallel tracks)

Gate: W1 complete and tests green. W2 tracks A and B are disjoint and may run in
parallel.

**Track A — ai-engineer:**

- **T-MMS-05** Shared Step-0 skill: extract the Step-0 block (~400 tokens) into a single
  canonical skill file; update all 21 agent personas to reference it.

**Track B — software-engineer-python:**

- **T-MMS-06** Panel `md → html` render path in `features/panel/views/memory.py`.
  Retire SPEC-DOC-008 byte-identity invariant from the view's docstring and tests.
  Add path traversal guard for `.md` source files.
- **T-MMS-07** Repoint `ctx-inject.sh` from `tech-stack.html` + strip to `tech-stack.md`
  verbatim. Remove the `strip-memory-html.py` invocation; keep the catalog.json fallback
  path (no change there — catalog.json is still JSON, no strip needed).

### W3 — Migration (CLOSURE-phase, PE-only)

Gate: W2 complete, all tests green, and `ACTIVE.md` phase = `CLOSURE`.

- **T-MMS-08** (PE) `migrate-html-to-md.py`: one-time script using `html2text`/`pandoc`
  to convert the 21 HTML atoms to Markdown. PE runs it, reviews each output, applies
  frontmatter, and writes the 21 `.md` files.
- **T-MMS-09** (PE) Run `lint-memory-atoms.py` on all 21 converted atoms; fix any
  violations; run `generate-memory-catalog.py` to produce final `catalog.json`.
- **T-MMS-10** (PE) Delete the `.yaml` and `.html` memory atom files; add
  `specs/memory/**/*.html` to `.gitignore`.

### W4 — Delete old subsystem + doctor wiring + propagation + QA gate

Gate: W3 complete (memory atoms converted and linted).

- **T-MMS-11** (software-engineer-python) Remove STRUCT-1..STRUCT-4 and SYNC-1 from
  `doctor.py`; add LINT-1 check; adapt check #2 (look for `.md` not `.html`); adapt
  check #8 (grep `.md` body, no escape hatch). Remove `renderer.py` memory path.
  Adapt `catalog.py` to read `.md` frontmatter. Update `cli/commands/memory.py`:
  remove `dadaia memory render` and `dadaia migrate memory-yaml` subcommands.
- **T-MMS-12** (devops-engineer) Delete `public/schemas/memory/` (4 schema files);
  delete `public/templates/memory-*.html.j2` (4 template files); delete
  `public/scripts/strip-memory-html.py`; delete `public/scaffold/memory/*.yaml`;
  replace scaffold with `.md` templates. Run `dadaia public stage && dadaia public
  install --target all`. Run `dadaia public doctor` (exit 0).
- **T-MMS-13** (qa-engineer) Acceptance gate: verify all 10 AC criteria from SPEC §8;
  run full `pytest` suite (exit 0); verify `dadaia specs doctor` exit 0; record evidence.

---

## 4. Technical risks

| Risk | Wave | Mitigation |
|------|------|-----------|
| html2text/pandoc loses table structure or Mermaid fences | W3 | dry-run migration script; PE reviews each atom; fallback: manual re-author |
| Panel Markdown renderer incomplete (OQ-1) | W2 | OQ-1 resolved in W0; dep approved before W2 starts |
| Doctor STRUCT/SYNC removal breaks test fixture assumptions | W4 | Test adapter tasks included in T-MMS-11 |
| 21-persona update introduces regressions in persona routing | W2 | ai-engineer runs suite after T-MMS-05; no routing logic changed, only skill references |

---

## 5. Validation plan

- After W1: `lint-memory-atoms.py` and `generate-memory-catalog.py` have unit tests;
  `pytest` passes.
- After W2: panel renders at least 3 atoms correctly in manual smoke test; ctx-inject
  output verified token count ≤ 3 K.
- After W3: all 21 `.md` atoms pass `lint-memory-atoms.py`; `catalog.json` has 21
  entries; no `.yaml` or `.html` atoms remain committed.
- After W4: `dadaia specs doctor` exits 0; `dadaia public doctor` exits 0; full `pytest`
  suite green; QA gate (T-MMS-13) APPROVED.
