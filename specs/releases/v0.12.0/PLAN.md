# PLAN — Release v0.12.0 — backlog-tooling-single-source

**Status:** Aprovado
**Approval provenance:** operator-delegated approval, 2026-08-15 (goal directive)
**Release ID:** v0.12.0
**Owner:** product-engineer
**Source SPEC:** `specs/releases/v0.12.0/SPEC.md`
**Branch:** `feature/v0.12.0` (cut from `develop` at `523f0d8d`; branch contract: `dadaia-gitflow`)

---

## 1. Strategy

Build the new reader, the new checks and the new writer as **pure modules against
fixtures**, while the live tooling keeps validating the old shape. Then flip everything —
wiring, deletions, governance re-target and the document itself — in **one commit**. The
release is therefore three phases: *subtract* (delete what has no caller), *add* (pure
modules + tests, unwired), *flip* (one atomic commit), followed by documentation, review and
closure.

Two properties drive every ordering decision:

- **The doctors are chokepoints.** `backlog doctor` runs in pre-commit (scoped to staged
  `specs/backlog/` paths) and in CI; `specs doctor` runs in review. A commit that leaves them
  disagreeing blocks every later commit of the release.
- **The document and the tooling are one contract.** `BACKLOG.md` cannot exist before the
  tooling understands it (it would be parsed as an entry file with slug `BACKLOG`), and the
  tooling cannot be pointed at a document that does not exist. Hence the atomic flip.

---

## 2. Current-state inventory (measured at `feature/v0.12.0`)

**`features/backlog/` — nine modules.**

| Module | Role today | Live callers | Fate |
|---|---|---|---|
| `subject_registry.py` | canonical-anchor registry (5 kinds) | doctor, preview, CLI | **keep** (ADR D7) |
| `classifier.py` | DUPLICATE / DIVERGENT_CONFLICT verdicts | doctor | **keep** |
| `preview.py` | anchor preview **+** `load_backlog_items` (globs `specs/backlog/*.md`) | doctor, CLI `subjects`, `--explain` | **split**: preview kept, loader replaced by `document.py` |
| `doctor.py` | BL-SCHEMA/DUP/CONFLICT/STALE engine | CLI `doctor`, pre-commit, CI | **re-target** |
| `ledger.py` | `read_consumed` over archived sidecars | doctor (BL-STALE) | **keep unchanged** |
| `ledger_writer.py` | `write_consumed` | `removal_lifecycle` only | **delete** |
| `removal.py` | `apply_removal` (rewrite/unlink) | `removal_lifecycle` only | **delete** |
| `removal_lifecycle.py` | consume/remove facade | **none** (container builder, itself uncalled) | **delete** |
| `consumes.py` | `**Consumes:**` parser + binder | **none** | **delete** |

**CLI.** `cli/commands/newartifacts.py` — `backlog new` (via
`features/spec_artifacts/new_artifacts.backlog_new`), `backlog subjects`, `backlog doctor`
(+ `_explain_backlog`), `_resolve_backlog_roots`. `cli/anchors.py::derive_cli_anchors` feeds
the registry at three composition boundaries. **All three verbs survive**; only `new` and
`doctor` change surface.

**Chokepoints.** `cli/commands/ci.py::_run_backlog_doctor_gate` (+ `_staged_backlog_paths`)
— pre-commit, scoped to staged `specs/backlog/` paths; the full sweep runs in the CI job
`backlog-doctor` / *Backlog consistency (BL-SCHEMA/DUP/CONFLICT/STALE)*
(`.github/workflows/ci.yml:415-431`), whose comment falsely claims the tree is gitignored.

**`features/specs/doctor_governance.py`.** `check_backlog_schema` (SPEC-DOC-012 +
SPEC-DOC-022/023, `candidates.md`-only), `check_consumed_backlog_disposition`
(SPEC-DOC-031, globs entries, WARN), `check_unarchived_terminal_backlog` (SPEC-DOC-035,
globs entries, WARN), `_BACKLOG_AGGREGATE_FILES = {candidates.md, ideas.md, README.md}`,
`_BACKLOG_STATUS_RE`, `_archive_consumption_hits`.

**Container.** `build_backlog_removal_lifecycle` (uncalled), `_backlog_context_roots` (its
only caller), `_fake_spec_stub`, `_FAKE_BACKLOG_CANARY_SLUG`, `_fake_backlog_canary_slug`,
`_fake_backlog_canary_ref` (all uncalled).

**Documents.** `public/scaffold/backlog/README.md` (per-entry authoring rules),
`public/data/CONSUMER_VALIDATION_RECIPE.md` (F-10, R-02, R-13),
`public/skills/dd-backlog-definition/SKILL.md` §2/§7, `public/skills/dd-release-definition/SKILL.md` §5.

**Live tree.** 31 per-entry item files + `candidates.md` (25 candidate rows, 5 idea rows,
20 LEDGER lines, 3 terminal tables, 1 history table) + `README.md`; 46 files under
`_archive/`; 18 historical `consumed_backlog.json` sidecars under `specs/_archive/`.

---

## 3. Target architecture

```
specs/backlog/
  BACKLOG.md          ← the single source: ## ACTIVE (subsections) + ## LEDGER (lines)
  README.md           ← authoring rules for the document
  _archive/           ← every superseded per-entry file + candidates.md (git mv, never deleted)

features/backlog/
  document.py         ← NEW: pure parser  BACKLOG.md -> (ActiveItem[], LedgerRow[], errors[])
  doctor.py           ← same engine, same four codes, reads the document model
  subject_registry.py + classifier.py + preview.py(anchor half) + ledger.py   ← unchanged
```

`document.py` is the only new module and the only place that knows the file's syntax.
`doctor.py` keeps its `_CHECKS` table, `Finding`, `Severity` and injected-roots signature;
`ActiveItem` exposes the same fields the checks already consume (`slug`, `status`,
`intents`, `intents_error`) plus `line` for located diagnostics, so the check bodies change
minimally and the classifier is untouched. `new_artifacts.backlog_new` gains a document
writer that appends one subsection; it is the only writer.

Dependency direction is unchanged: `features/backlog/**` imports `core` only;
`cli/**` composes; `container` no longer touches backlog at all after FR4.

---

## 4. Execution order and why

| # | Task | Why here |
|---|---|---|
| 1 | T-120-01 definition commit, T-120-02 milestone (a) | `dadaia-gitflow`: SPEC+PLAN+TASKS `Aprovado` ⇒ merge, security review, push |
| 2 | **T-120-03 subtract** — delete the dead write side + fakes + 4 test modules | zero live callers ⇒ nothing to sequence against; shrinks the cutover diff before it is written |
| 3 | **T-120-04 `document.py`** + unit tests over fixtures | the contract every later task binds to |
| 4 | **T-120-05 doctor checks** over the document model, unwired | needs the model; still fixture-only, live CLI untouched |
| 5 | **T-120-06 `backlog new`** writer, unwired | needs the model; A3.2's byte-diff needs the parser's shape |
| 6 | **T-120-07 PM authors `BACKLOG.md`** (content staged, not committed) | needs the schema fixed by T-120-04, and the count proof needs the pre-state intact |
| 7 | **T-120-08 CUTOVER** — wiring + loader deletion + governance re-target + document + `git mv` | the only commit where the shape changes; both doctors green before and after |
| 8 | T-120-09 docs (scaffold README, recipe, CI comment) + projection | describes the shipped model; must follow the flip to stay truthful |
| 9 | T-120-10 skills (ai-engineer) + projection | same reason; separate lane |
| 10 | T-120-11 QA (alpha-1 close) → T-120-12 memory → T-120-13 closure → T-120-14 ship | standard cadence |

The pre-commit backlog gate makes step 6 the delicate one: the PM's document must be
**written but unstaged** until the cutover commit, otherwise the old loader parses it. TASKS
states this explicitly in T-120-07's done criterion.

---

## 5. Design — `document.py`

```python
@dataclass(frozen=True)
class ActiveItem:
    slug: str; title: str; opened: str; status: str | None
    description: str; provenance: str
    intents: tuple[Intent, ...] = ()
    intents_error: str | None = None
    line: int = 0

@dataclass(frozen=True)
class LedgerRow:
    slug: str; disposition: str; release_or_reason: str; date: str; line: int

@dataclass(frozen=True)
class BacklogDocument:
    active: tuple[ActiveItem, ...]
    ledger: tuple[LedgerRow, ...]
    errors: tuple[DocumentError, ...]      # (section, slug|None, line, message)

def load_document(backlog_dir: Path) -> BacklogDocument: ...
```

Rules:

- Sectioning is by `^## ACTIVE` / `^## LEDGER`; items by `^### <slug>`; keys by
  `^- \*\*(Title|Opened|Status|Description|Provenance|Intents):\*\*`.
- `**Intents:**` is followed by a fenced block; the fence body is fed to the **existing**
  `core.models.backlog.parse_intents`, and a `ValueError`/`YAMLError` is captured as
  `intents_error` with the file line, reusing `preview._format_yaml_error`'s formatting so
  diagnostics stay identical in shape to today's.
- LEDGER lines split on `·` into exactly four fields; the disposition is upper-cased and
  matched against the six canonical tokens (which stay defined **once**, in
  `core/models/backlog.py`, imported by both the doctor and the governance validator).
- Absent file ⇒ empty document, no error (A1.2). Unreadable file ⇒ one `DocumentError`.
- No exception escapes `load_document`.

`preview.load_backlog_items` and `_NON_ITEM_STEMS` are deleted; `preview.py` keeps
`resolve_one`, `list_anchors`, `bound_anchor_changes` (now taking an `ActiveItem`) and
`PreviewResult`.

---

## 6. Design — the four checks over the document

`doctor.DoctorContext` swaps `items: list[BacklogItem]` for the document model and keeps
`registry`, `consumed` and the pre-bound anchor map. Check bodies:

- `_check_schema` — emits one BL-SCHEMA per `DocumentError`; then the existing three
  conditions per ACTIVE item (no bound intents unless `is_intents_exempt(status)`; invalid
  status; unresolved subjects) with unchanged messages, plus a slug-shape check.
- `_check_dup` / `_check_conflict` — unchanged `_pairwise` bodies over `BoundItem`s built
  from ACTIVE items, plus one new BL-DUP condition: a slug repeated inside ACTIVE or inside
  LEDGER.
- `_check_stale` — three ORed conditions (SPEC FR2/ADR D8): slug ∈ archived `consumed`
  (existing `read_consumed`), slug also present in LEDGER, or the item's own `Status` is a
  terminal token. Message names which condition fired.

Severities, ordering (check order then document order) and the "empty list ⇒ clean" contract
are unchanged, so `cli/commands/ci.py` and the CI job need **no** change beyond the false
comment.

**Governance (same commit).** `check_consumed_backlog_disposition` iterates
`load_document(...).active` and keeps `_archive_consumption_hits` verbatim;
`check_unarchived_terminal_backlog` becomes the loose-file invariant (any `*.md` directly
under `specs/backlog/` other than `BACKLOG.md`/`README.md`); `check_backlog_schema` and its
three regexes are deleted; `_BACKLOG_AGGREGATE_FILES` retires. `doctor_governance.py` may
import `features.backlog.document` (leaf → leaf; no sibling *validator* import, so the
module's leaf-only rule holds) — if `lint-imports` disagrees, the parser is invoked through
the coordinator instead, which is the fallback and must not become a duplicated parser.

---

## 7. Ownership split

| Lane | Owner | Write set |
|---|---|---|
| Production Python, CLI, doctors, tests | `software-engineer` | `dadaia_workspace/features/backlog/**`, `features/specs/doctor_governance.py`, `features/spec_artifacts/new_artifacts.py`, `cli/commands/{newartifacts,ci}.py`, `container.py`, `tests/**`, `.github/workflows/ci.yml` |
| The document | `project-manager` | `specs/backlog/BACKLOG.md`, the `git mv`s into `specs/backlog/_archive/` |
| Consumer docs | `software-engineer` | `public/scaffold/backlog/README.md`, `public/data/CONSUMER_VALIDATION_RECIPE.md` |
| Skills | `ai-engineer` | `public/skills/dd-backlog-definition/SKILL.md`, `public/skills/dd-release-definition/SKILL.md` |
| Definition, memory, closure | `product-engineer` | `specs/releases/v0.12.0/**`, `specs/memory/**` (CLOSURE), `specs/releases/ACTIVE.md` |
| Git, review dispatch | dispatcher | refs, merges, pushes, PR |

T-120-08 is the single dual-owner task (`project-manager` + `software-engineer`), sequenced
inside one commit: the PM's document is already written (T-120-07), the SE lands the wiring
and deletions in the same working tree, both doctors are run, then one commit stages
everything.

---

## 8. Test plan

**New (feature-focused, D6).** `tests/unit/features/backlog/test_document.py` — the FR1
parser matrix (A1.1–A1.5) over inline fixtures. `tests/integration/test_backlog_doctor.py` —
migrated in place to the new shape: BL-SCHEMA on a malformed subsection, the `idea`/
`candidate` intents gate, duplicate slug, divergent conflict, the three BL-STALE conditions,
the absent-file no-op. `tests/integration/cli/test_cli_newartifacts.py` +
`tests/unit/features/spec_artifacts/test_new_artifacts.py` — migrated: subsection authoring,
byte-diff on append, slug-uniqueness refusal across ACTIVE ∪ LEDGER.
`tests/unit/features/specs/test_doctor*.py` + `_golden/fixture_specs/backlog/` — migrated
fixtures for SPEC-DOC-031/035, including the A5.2 phantom-`BACKLOG`-slug regression.

**Deleted as recorded supersessions (subject deleted by FR4):**
`tests/unit/test_backlog_removal.py`, `tests/unit/test_backlog_ledger_writer.py`,
`tests/integration/test_backlog_removal_loop.py`, `tests/unit/backlog/test_consumes.py`.

**Adjusted in place:** `tests/e2e/features/test_backlog_precommit.py` and
`tests/integration/test_precommit_backlog_scoping.py` (same gate, fixture shape only — **no
new e2e**); `tests/integration/test_governance_intake_not_gitignored.py` (asserts
`BACKLOG.md` is tracked).

**Must pass unmodified (A9.4):** `test_backlog_classifier.py`,
`test_backlog_subject_registry.py`, `test_backlog_models.py`,
`tests/unit/backlog/test_classifier_clamp.py`, `tests/unit/test_backlog_ledger.py`.

Every added test declares `Intent: CONTRACT — v0.12.0 <A-id>` or `Intent: SENTINEL — <seam>`
at birth. LARGE census unchanged.

---

## 9. Validation plan

| # | What | Command / evidence |
|---|---|---|
| V1 | Preflight on every commit | `dadaia ci preflight` |
| V2 | Backlog gate, live tree | `dadaia backlog doctor --specs-dir specs --source-root .` |
| V3 | Backlog gate, planted violations | fixture tree per A2.2–A2.7, exit 1 with the expected codes |
| V4 | Specs doctor | `dadaia specs doctor` → 0 errors / 0 warnings on the backlog surface |
| V5 | Two-doctor agreement (R-13) | both doctors over the same consolidated tree and over one planted-violation tree |
| V6 | Dead-surface zero-hit | `grep -rn` for the A4.1 symbol list under the standing exclusions |
| V7 | Retired-check zero-hit | `grep -rn` for the A5.4 symbol list |
| V8 | Never-delete count | slug-set difference both ways, pre vs post, captured to `.dadaia/tmp/<agent>/<YYYYMMDD>/` |
| V9 | Rename-not-delete | `git log --diff-filter=D -- specs/backlog/` over the range; `git diff --stat` shows zero `specs/_archive/` modifications |
| V10 | Import purity | `lint-imports --config setup.cfg --no-cache` |
| V11 | Projection | `dadaia public stage` → `install --target all` → `doctor` (incl. `[ok] public-privacy`) |
| V12 | Consumer recipe | F-10, R-02, R-13 walked on a scaffolded context |
| V13 | CI | the `backlog-doctor` job green on the consolidated tree; full workflow green on the PR |
| V14 | Fresh-context no-op | `specs init` into a temp dir, then both doctors — clean with no `BACKLOG.md` |

---

## 10. Technical risks and how the plan absorbs them

- **The cutover commit fails its own gate.** The pre-commit hook runs `backlog doctor` over
  the *staged* backlog paths — i.e. over the new document with the new code already in the
  tree. T-120-08 runs V2+V4+V5 **before** committing; a failure is fixed in the working tree,
  never bypassed with `--no-verify`.
- **A parser divergence between the doctor and the writer.** Both go through `document.py`;
  `backlog new` never hand-formats a subsection it cannot re-read (A3.5 closes the loop).
- **`lint-imports` rejects the governance→document import.** Fallback stated in §6; under no
  circumstance is the parser duplicated inside `features/specs/`.
- **The archived-sidecar BL-STALE path silently dies** when the loader changes. A2.7 exercises
  it over the real 18 sidecars; `ledger.py` and its test are untouched (A4.2).
- **Review load on the flip.** Renames dominate the cutover diff; the reviewer is pointed at
  the three non-rename hunks (CLI wiring, loader deletion, governance re-target) by the task's
  own write-set list.
- **Curation drift while folding.** The PM works from a frozen pre-state (no backlog write
  between T-120-07 and T-120-08); if a bug is registered mid-release it lands in
  `specs/bugs/**`, which this release does not touch.
