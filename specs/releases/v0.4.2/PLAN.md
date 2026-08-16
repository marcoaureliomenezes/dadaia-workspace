# PLAN — Release v0.4.2 — residual-convergence

**Status:** Aprovado
**Approval provenance:** operator-delegated, 2026-08-16 (resolva todos — goal directive)
**Release ID:** v0.4.2
**Owner:** product-engineer
**Source SPEC:** `specs/releases/v0.4.2/SPEC.md`
**Branch:** `feature/0.4.2` (cut from `develop` at `36412845`; branch contract: `dadaia-gitflow`)

---

## 1. Strategy

Fourteen entries, three root-cause classes, one ordering rule: **shrink first, then fix, then
state**. Deletion tasks run before the changes that would otherwise have to be applied twice
(FR12's dead surface goes first); the seams land next; the doc/skill statements land last, so
they describe shipped behaviour rather than intent (FR14 before FR3's skill pass is the one
hard sequencing constraint).

Three properties are non-negotiable throughout:

1. **RED before GREEN.** Every behavioural task writes its failing test first and observes it
   failing for the real reason (`DADAIA.md` §6).
2. **Green at every commit.** `dadaia ci preflight` + `backlog doctor` + `specs doctor` +
   `public doctor` before every commit. No `--no-verify`.
3. **Deletion beats addition (R5).** Where a task can remove code, it removes code. Net line
   count is expected to fall.

---

## 2. Layers affected

| Layer | Modules | FRs |
|---|---|---|
| `features/backlog` | `document.py`, `preview.py`, the relocated `backlog_new` | FR1, FR3(4), FR11 |
| `features/spec_artifacts` | `new_artifacts.py` (shrinks to `release_new`) | FR1 |
| `features/specs` | `catalog.py`, `doctor_governance.py`, `scaffolder.py` | FR2, FR12, FR14 |
| `features/chokepoints` | `service.py` (`_PathMasker`), `denylist_scan.py` (matcher export only) | FR4 |
| `features/telemetry` | `store/schema.py` (two comments) | FR3(5) |
| `infrastructure` | `git_objects.py`, `data/privacy_baseline.json` | FR7, FR8, FR10 |
| `core` | `protocols/git_object_reader.py` (`GitObjectReadError` field) — `redaction.py` **untouched** | FR4 |
| `cli` | `commands/specs.py`, `commands/ci.py`, `commands/newartifacts.py` | FR1, FR8, FR12 |
| `public/` (ai-engineer only) | `skills/dd-*`, `skills/dadaia-task-manager`, `agents/*`, `templates/*`, `scripts/generate-memory-catalog.py`, `scripts/lint-memory-atoms.py`, `schemas/memory/*` | FR2, FR3, FR5, FR6, FR12 |
| `tests` | unit/integration only — **zero new e2e** | all |
| `specs/memory`, `specs/assets` | closure window only | §5 |

**Layer rules hold unchanged:** `features/**` imports neither `cli`, `infrastructure` nor
`hooks`; `core/**` stays stdlib-pure with its existing authorized-I/O set; `cli` is the sole
composition point for injected ports. FR1 is executed as a **move inside `features/`**, not as
a new cross-feature import edge — `setup.cfg`'s import contract gains nothing.

---

## 3. Execution order

```
FR12 (delete dead surface)
   ↓
FR1 (grammar seam) → FR11 (parser perf, same module)
   ↓
FR14 (SPEC-DOC-031 semantics)            ← must precede FR3's skill pass
   ↓
FR2-code · FR4 · FR7 · FR8 · FR10 · FR9  (independent; serialized by the one-[-] rule)
   ↓
FR3-code (leaf import, DEAD markers)
   ↓
FR3-skills + FR5 (ai-engineer)  ·  FR6 (ai-engineer)
   ↓
FR13 (CHANGELOG preamble)
   ↓
qa-engineer alpha-1  →  code-reviewer six-axis (BEFORE archive — R3)
   ↓
memory window (FR2-memory, §5 atoms, diagram)  →  CLOSURE  →  archive  →  ship
```

FR9 lands after FR10 so the sentinel's new archive coverage is measured against the final
baseline, and the `_TESTS_SCOPE_BASELINE` delta is attributable to exactly one task (D9).

---

## 4. Per-FR implementation notes

### FR12 — dead hotfix surface (first, pure deletion)

Remove `hotfix_app` + `hotfix_open` from `cli/commands/specs.py` (including the
`candidates.md` pre-condition block), `scaffold_hotfix_release` + `_HOTFIX_TASKS_STUB` from
`features/specs/scaffolder.py`, both `.j2` templates, and their tests. `_render_template` stays
(other callers). Regenerate `tests/unit/infrastructure/_golden/doctor_all_four_v0158.json`
through the sanctioned regeneration path, never by hand. `core/specs_version.py` and
`doctor_release.py` mention hotfixes only in comments — leave them; they describe branch names,
which are still law.

### FR1 — one grammar, one writer

`backlog_new` becomes `features/backlog/authoring.py::backlog_new` (name is PLAN-level; the
task may fold it into an existing module if that is smaller). It:

- loads the document through `load_document` for slug membership (ACTIVE ∪ LEDGER);
- gets its insertion offset from a **fence-aware** helper exported by `document.py` — the same
  `_fenced_ranges`/`_top_level_sections` machinery the parser already runs, promoted to public
  API rather than duplicated;
- writes, then **re-parses and asserts** the fresh slug is present, raising otherwise;
- validates with `fullmatch`;
- redacts the path in the unreadable-document diagnostic.

`cli/commands/newartifacts.py` imports from the new home. The three private regexes
(`_ACTIVE_HEADING_RE`, `_LEDGER_LINE_RE`, `_LEDGER_HEADING_RE`) are **deleted**, not moved.
The skeleton constant and the teaching comment travel unchanged (the v0.12.0 A3.1/A3.2
guarantees ride on them).

### FR11 — parser perf (same module, immediately after FR1)

`_outside_fences` sorts the fenced ranges once and uses `bisect_right` over their start
offsets, checking only the candidate range that could contain the match. `load_document` selects
`yaml.CSafeLoader` when importable, else `yaml.SafeLoader`, through one module-level constant.
The budget test generates a ~140 KB document programmatically and asserts a generous ceiling
(sub-second with headroom — a budget, not a stopwatch).

### FR14 — SPEC-DOC-031 evidence

`_archive_consumption_hits(slug)` reads, per archived release dir:

- `SPEC.md`: the `**Consumes:**` line **and its continuation lines** (subsequent lines until a
  blank line or the next `**Key:**` line), tokenized on non-slug characters; a slug counts when
  it appears as a whole token;
- `CLOSURE.md`: rows of the `## Dispositions` table only.

Everything else in both documents is ignored. `_BACKLOG_RETURNS_HEADING_RE` and its branch are
deleted. Message text, code id, WARNING severity and the ACTIVE-iteration surface are unchanged.
Capture the SPEC-DOC-031 count before and after as evidence (A14.4).

### FR2 — token_estimate, code half

`features/specs/catalog.py` gains `estimate_tokens(body)` (the linter's formula, moved not
copied) and calls it instead of reading frontmatter.
`public/scripts/generate-memory-catalog.py` computes identically; a parity test asserts both
emit byte-identical catalogs for one fixture tree. `memory-frontmatter-v1.schema.json` drops
`token_estimate` from `required` (it stays in `properties` until the closure half).
`lint-memory-atoms.py` loses the drift check and its `_estimate_tokens`.

### FR4 — masker parity

`denylist_scan.py` exports its compiled matchers (the slug patterns and the operator-term
predicate) as a small factory; `service._PathMasker` consumes them for
`_segment_is_offending`, dropping its own `compile_candidates` call. `core/redaction.py` is a
**zero-diff file** this release. `GitObjectReadError` gains an optional `path` field; both
raise sites in `git_objects.py` pass it structurally and stop interpolating it into the
message; `service.py`'s git-failure branch renders the masked path through the same
`_PathMasker` instance and never interpolates raw `{exc}`.

### FR7 — fail-closed multi-path amnesty

`_rev_list_candidates` already yields every `(sha, path)` pair. `_blob_info` keeps
`{sha: (path, size)}` for reporting but additionally computes the set of shas seen at **more
than one path**. `_read_blobs` passes `prior_texts` only for single-path shas; a multi-path sha
gets `prior_text=None`. The matcher is untouched. The tree-order fixture builds a repo with the
same content at two paths and asserts identical refusal under both name orderings.

### FR8 — fail-soft width

1. `_read_oversized_blob_prefix` captures `proc.returncode` after `wait`, and raises
   `GitObjectReadError` when `len(prefix) < _MAX_BLOB_BYTES` **and** `returncode not in (0,)`.
   A full-cap read keeps swallowing the terminate/EPIPE outcome.
2. `container.load_registry_context_identities` surfaces a degradation signal (an extra return
   value or a typed result) and `cli/commands/ci.py` prints one `[pre-push]` stderr note. The
   scan proceeds either way.
3. `_blob_info`: a row that is not three fields, or whose size is non-numeric, raises the typed
   error naming the row; a `blob`-type filter miss (a tree) is still an ordinary skip.
   `_resolve_prior_texts`: a documented `<spec> missing` row stays absence; anything else
   raises.

### FR10 — baseline v5

Two new patterns beside `home-abs-path`, each single-line, each with the placeholder
`exclude_regex` mirroring the existing one:

- `users-abs-path` — `/Users/<name>`;
- `windows-users-path` — `C:\Users\<name>` (escaped, backslash-aware, case-insensitive drive
  letter).

`_header.version` → `5`; `_header.excludes` documents both carve-out sets and the `/root`
boundary (D10). Positive fixtures use synthetic non-identifying names and their literals are
added to `_TESTS_SCOPE_BASELINE`, listed in the task (D9).

### FR9 — sentinel archive coverage

`_tracked_paths` keeps its exclusion for archive prefixes, then **adds back** archive paths
whose blob sha is absent from `HEAD^`'s tree (`git ls-tree -r HEAD^` → sha set, one
subprocess). `HEAD^` unavailable ⇒ no add-back. The two fixtures (planted authored file;
`git mv`'d file) run against a temporary repo, not this one.

### FR3 / FR5 / FR6 — the statement layer (ai-engineer)

All three passes edit canonical sources under `dadaia_workspace/public/` and re-project
(`stage` → `install --target all` → `doctor`). They overlap on `dd-release-closure/SKILL.md`,
so they are strictly serialized. Each pass states its fact **once** and points at the owner for
the rest — no new duplication is created while removing old duplication.

### FR13 — CHANGELOG

Read the published version list from the package index (evidence captured), then insert one
preamble block under the file header. No existing heading is touched. The `[0.4.2]` section is
written at ship, in the same commit as any final version confirmation.

---

## 5. Test strategy

**Feature-focused, extending existing modules — no new e2e test, no scaffold.**

| FR | Where the tests live | Kind |
|---|---|---|
| FR1 | `tests/unit/features/backlog/test_document.py` (+ the relocated writer's existing module) | CONTRACT |
| FR2 | `tests/integration/scripts/test_generate_memory_catalog.py`, `tests/contract/cli/test_cli_memory_catalog.py` | CONTRACT + parity |
| FR3 | existing import/lint tests; a grep-shaped contract test only where one already exists | CONTRACT |
| FR4 | the existing chokepoints refusal/masking module | CONTRACT (paired fixtures) |
| FR7 | the existing amnesty module | CONTRACT (tree-order pair) |
| FR8 | the existing `git_objects` module | CONTRACT (RED on nonexistent oid + tree sha) |
| FR9 | `tests/integration/test_repo_self_scan.py` | SENTINEL |
| FR10 | the existing privacy-baseline module | CONTRACT (paired positive/placeholder) |
| FR11 | the parser module | CONTRACT + one budget regression |
| FR12 | deletion of `tests/unit/features/specs/test_scaffolder.py`'s hotfix cases as **recorded supersessions** | — |
| FR14 | the existing governance-doctor module + its golden fixtures | CONTRACT |

Every added test declares `Intent: CONTRACT — v0.4.2 <A-id>` or `Intent: SENTINEL — <seam>` at
birth. The only deletions permitted are FR12's recorded supersessions (their subject ceases to
exist); anything else requires a `qa-engineer` verdict with evidence
(`dadaia-test-stewardship`).

---

## 6. Validation plan

| id | What | Command |
|---|---|---|
| V1 | Full preflight at every commit | `dadaia ci preflight` |
| V2 | Backlog document validity | `dadaia backlog doctor --specs-dir specs --source-root .` |
| V3 | Specs governance, before/after SPEC-DOC-031 count | `dadaia specs doctor` |
| V4 | Projection integrity | `dadaia public stage && dadaia public install --target all && dadaia public doctor` |
| V5 | Import boundaries, no new edge | `lint-imports --config setup.cfg --no-cache` + `git diff setup.cfg` |
| V6 | FR12 zero-hit greps (standing exclusions) | `rg -n 'hotfix_app\|hotfix_open\|scaffold_hotfix_release\|_HOTFIX_TASKS_STUB\|release_hotfix.md.j2\|closure_hotfix.md.j2\|Hotfixes pendentes'` |
| V7 | FR1 zero-hit grep for private grammar regexes | `rg -n '\^###\|\^##\[ \\t\]\+LEDGER' dadaia_workspace` |
| V8 | FR2 zero-hit grep after the closure half | `rg -n 'token_estimate' specs/memory dadaia_workspace/public/schemas` |
| V9 | Self-scan sentinel incl. archive-authored blobs | `pytest tests/integration/test_repo_self_scan.py` |
| V10 | Parser budget | `pytest -k backlog_document_budget` |
| V11 | CLI redaction unchanged | `pytest tests/**/test_*redact*` + `git diff dadaia_workspace/core/redaction.py` (empty) |
| V12 | Zero open bugs at pick time (OD-3) | `dadaia bugs status` |
| V13 | Published version lineage (OD-3) | package-index version listing for `dadaia-workspace` |
| V14 | Push-gate behaviour end to end | the pre-push gate on the real push (milestones a and b) |

Every validation's output is captured and lands in `CLOSURE.md` as an evidence triple.

---

## 7. Technical risks (beyond SPEC §6)

- **The FR1 move touches the CLI's import graph.** Mitigation: the move and the CLI rewire are
  one commit; V5 proves no new accepted edge; the CLI contract tests are unmodified.
- **FR8(2) changes a container function's signature.** Mitigation: it is called from exactly one
  production site; the change is additive (a result object or a second return value) and every
  test that constructs it is updated in the same commit.
- **FR14 rewrites a check consumers rely on.** Mitigation: severity, id and message shape are
  unchanged; only the evidence surface narrows; the golden fixtures carry both a firing and a
  non-firing case.
- **The memory window is large** (every atom loses a frontmatter key). Mitigation: it is a
  mechanical single-key removal, followed by regeneration and `specs doctor`; it rides the
  closure commit where memory writes are legal and nothing else competes for the tree.

---

## 8. Definition of done

1. Every FR's acceptance ids hold, evidenced by V1–V14.
2. `qa-engineer` APPROVED the `alpha-1` increment.
3. `code-reviewer` APPROVED the delta **before** the archive move (R3, dogfooded).
4. Memory updated per SPEC §5, `CLOSURE.md` written with both calibrated intake sections
   (R4), the 13 dispositions swept to `DELIVERED — v0.4.2`, the release archived.
5. `security-reviewer` APPROVED the `origin/develop..develop` delta at both milestones;
   `develop` pushed green; PR `develop` → `main` merged with CI green.
