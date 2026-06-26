# PLAN — Release: v0.1.26 — `backlog_definition` workflow body + removal-on-release (R2)

**Status:** Aprovado
**Release ID:** v0.1.26
**Owner:** product-engineer
**Opened:** 2026-06-26
**Implements:** `specs/releases/v0.1.26/SPEC.md` (clusters §3.1–§3.6, constraints §3.8)

---

## 1. Strategy

TDD throughout, mirroring R1's discipline and the v0.1.24 two-layer workflow shape. The
keystone is **structural parity with `release_definition.py`**: the new
`BacklogDefinitionWorkflow` reuses the audited seams (`FragmentLoader`, `ContextSelector`,
`build_fragment_suffix`, `PromptPrefix`, `LifecycleAgentRunner`, `RuntimeFactory`) rather
than inventing a new procedure. Pure backlog logic (ledger writer, removal hook,
`backlog_index` resolution) lands as injected-root functions under `features/backlog/`
and `features/lifecycle/`, never reaching for cwd.

**Build on R1, never duplicate (SPEC §3.8).** `subject_bind` calls the R1 registry; the
review steps call R1 `classify`; the ledger writer emits the exact R1 `ledger.py` reader
shape. No second registry/classifier/ledger schema.

**Tests-first per module**, against fixed `tmp_path` fixture trees built from inline
`MINIMAL_*` constants (never the live repo) — the same anti-flake rule R1 fixed. The
workflow gate behaviours are one **parameterized** step-matrix test, not copy-pasted per
step (SPEC §3.7.11).

## 2. Layers affected

| Layer | Files | Nature |
|---|---|---|
| `features/lifecycle/workflows/` | `backlog_definition.py` (new); `_deferred.py` (remove `backlog_definition` entry); `__init__.py` (re-export) | The §4 workflow body |
| `features/lifecycle/context_selector.py` | add `sel_backlog_index` + register `backlog_index` | New dynamic-input selector |
| `features/backlog/` | `ledger_writer.py` (new), `removal.py` (new) | Pure ledger writer + residual-aware removal hook |
| `cli/commands/lifecycle.py` | re-point `backlog_define` (`:327`) at the workflow | CLI wiring (per-step harness/model overrides) |
| `container.py` | `build_backlog_definition_workflow` factory | Mirror release-definition wiring |
| `public/lifecycle_fragments/backlog_definition/` | `intake_grill.md`, `conflict_scan.md`, `conflict_resolution_grill.md`, `backlog_authoring.md` (replace `_README.md`) | Real step fragments |
| release-definition / closure surface | invoke ledger writer + removal hook | Wire §6 into the lifecycle |
| `tests/` | unit + integration + e2e per below | TDD |

`architecture.md` memory update is CLOSURE-only (workflow + writer + selector).

## 3. Execution order (SPEC §6 sequencing → task groups)

1. **`backlog_index` selector** (`context_selector.py`) — lands first; steps 1–2 depend on
   it. `sel_backlog_index` walks `_dir_files("backlog")`, parses R1 `intents[]`
   frontmatter + status per item, excludes `ideas.md`/`candidates.md`/catalog, bounded by
   policy (frontmatter only). Register `"backlog_index"` in `_SELECTORS`.
2. **Real fragments** (`public/lifecycle_fragments/backlog_definition/`) — author the four
   model-step fragments before wiring the workflow (the loader fails on a fragment id with
   no source). Frontmatter modelled on `release_definition/*.md`; pure Python steps carry
   no fragment.
3. **Ledger writer + removal hook** (`features/backlog/ledger_writer.py`, `removal.py`) —
   independent of the workflow; can land in parallel after the selector. Writer emits the
   R1 `ledger.py` shape; removal hook is residual-aware with copy-before-remove.
4. **Workflow body** (`workflows/backlog_definition.py`) — the §4 `_SEQUENCE` + the
   `BacklogDefinitionWorkflow` class; depends on the fragments (2), the classifier feed
   (R1 + step 1), and the selector (1). Remove the `_deferred` entry; update `__init__.py`.
5. **Container factory + CLI wiring** — `build_backlog_definition_workflow`; re-point
   `backlog_define` from `_run_phase_step` to the workflow with per-step overrides.
6. **Wire §6 into the lifecycle** — invoke the ledger writer at release-definition and the
   removal hook at closure; prove the BL-STALE loop closes.
7. **Public stage + install + doctor** — propagate fragments to the instance.
8. **Final live-tree verification** — full `pytest`, `backlog doctor` exit 0, `public
   doctor` exit 0, `specs doctor` green.

## 4. Module contracts (pure, injected roots)

```python
# features/lifecycle/workflows/backlog_definition.py — mirrors release_definition.py
@dataclass(frozen=True)
class BacklogStep:           # label, role, fragment_id|None, shared_fragment_ids,
    ...                      # is_review, is_python_gate, runtime_kind|None
class BacklogDefinitionWorkflow:
    def __init__(self, *, context, release_id, run_store, runtime_factory,
                 context_selector, default_runtime_kind=AgentRuntimeKind.FAKE,
                 fragment_loader=None, prefix=None, prompt_builder=None,
                 state_machine=None, registry=None, classifier=None) -> None: ...
    def run(self, run_id, sequence=_SEQUENCE) -> BacklogDefinitionResult: ...

# features/lifecycle/context_selector.py
def sel_backlog_index(self, name, policy) -> SelectionResult: ...   # bound intents + status

# features/backlog/ledger_writer.py — injected archive root; emits ledger.py reader shape
def write_consumed(*, archive_root: Path, release_id: str,
                   consumed: Sequence[ConsumedEntry]) -> Path: ...  # {slug, shipped_anchors[]}

# features/backlog/removal.py — injected backlog + archive dirs; residual-aware
def apply_removal(*, backlog_dir: Path, archive_root: Path, release_id: str,
                  shipped_anchors: set[str]) -> RemovalResult: ...
#   per consumed item: residual>0 -> rewrite-to-residual (keep);
#   residual==0 -> copy to _archive/<release>/consumed-backlog/<slug>.md THEN unlink
```

`Path` args are **always injected** (SPEC §3.8) — no `os.getcwd()`. The ledger writer
reuses `LEDGER_FILENAME` from R1 `ledger.py`; anchors are module-relative `path#symbol`
(no operator-local paths / private names — SPEC §3.8).

The workflow folds `static_inputs` into the cacheable prefix, selects dynamic context per
fragment, builds the suffix, runs the worker on the injected `RuntimeFactory`, and reads
the Python gate via `LifecycleAgentRunner.evaluate_gate` — field-for-field as
`release_definition.py`. Step 1b/3/6 are Python steps (`fragment_id=None`): 1b calls the
R1 registry (HALT on UNRESOLVED/AMBIGUOUS); 2's deterministic disposition + 6's
re-validation call R1 `classify`; 3 enforces the NEW-only-if-all-`UNRELATED` gate; step 4
is conditionally skipped unless step 2's report carries a `DIVERGENT_CONFLICT`.

## 5. Technical risks (from SPEC §6, with the plan's mitigation)

| Risk | Plan mitigation |
|---|---|
| Container/runtime wiring diverges from `release_definition` (HIGH) | Mirror `release_definition.py` field-for-field; add `build_backlog_definition_workflow` paralleling the release factory; end-to-end `fake`-harness test asserts full gate semantics. |
| Conditional step-4 skip logic (MEDIUM) | Python-decided from step 2's overlap report; record skip vs run; test both branches. |
| Removal hook deletes the only copy of a CRITICAL record (HIGH) | Copy-before-remove invariant (ADR-C); unit test asserts archive copy exists at removal; residual-rewrite is the DEFAULT path. |
| Ledger shape drift from R1 reader (MEDIUM) | Round-trip test writer → `read_consumed`; reuse `LEDGER_FILENAME`; no second schema. |
| Model-downgrade seam over-trusts model (LOW) | Fail-closed default; offline path tested → `DIVERGENT_CONFLICT`; step 6 re-validates regardless. |

## 6. Validation plan

- **Per module:** `pytest` over the module's `tests/unit/test_backlog_*` /
  `tests/unit/test_lifecycle_*` (fixed `tmp_path` `MINIMAL_*` trees). `mypy --strict`
  clean. `ruff format --check` + `ruff check`.
- **Selector:** `tests/unit/test_context_selector_backlog_index.py` — bound intents +
  status per item; excludes `ideas.md`/`candidates.md`/catalog (acceptance §3.7.7).
- **Ledger writer:** round-trip `write_consumed` → `read_consumed` (R1) → expected map,
  keyed on shipped anchors (acceptance §3.7.8).
- **Removal hook:** both branches — residual>0 rewrite-and-keep; residual==0
  copy-then-remove with the archive copy asserted present at removal (acceptance §3.7.9).
- **Workflow:** `tests/integration/test_backlog_definition_workflow.py` — end-to-end on
  `fake`: full sequence runs in order; `subject_bind` HALT (§3.7.2); `DIVERGENT_CONFLICT`
  with model OFFLINE routes to grill (§3.7.3); `reconcile_decision` blocks NEW unless
  all-`UNRELATED` (§3.7.4); `backlog_review_gate` blocks a dirty result (§3.7.5). Gate
  behaviours are **one parameterized** step-matrix test (§3.7.11), not per-step copies.
- **CLI:** `tests/integration/test_cli_backlog_define.py` — `--harness fake` drives the
  real workflow (not `_deferred`); `--harness claude` rejected; bad `--model` rejected
  (acceptance §3.7.6).
- **BL-STALE loop:** `tests/integration/test_backlog_removal_loop.py` — run writer +
  removal hook, then `backlog doctor` reports zero BL-STALE; re-introduce a consumed slug
  → BL-STALE ERROR (acceptance §3.7.10).
- **e2e:** `tests/e2e/features/test_backlog_define_e2e.py` — `dadaia lifecycle backlog
  define` on `fake` over a fixture context runs the sequence to completion / blocks on a
  planted divergence.
- **Public propagation:** after fragment edits, `dadaia public stage && dadaia public
  install --target all && dadaia public doctor` exit 0 (`[ok] public-privacy`).
- **Live tree:** final full `pytest`; `dadaia backlog doctor` exit 0; `dadaia specs
  doctor` green; no in-repo `.dadaia/`/cache pollution (conftest repo-root write guard
  backstops).

## 7. Out of scope (restated for the implementer)

R1 is shipped + archived — **do not** touch or re-do the `intents[]` schema, registry,
classifier, `backlog doctor` BL-* checks, their pre-commit/CI wiring, or the backfill.
`workflow-model-governance-panel-control-plane` is the NEXT release — add **no** panel
surface or per-workflow model-governance plane here. Introduce **no** route registry / no
`panel`/`api` auto-derivation (still alias-only). Change **no** BL-* semantics — R2 wires
the ledger *writer* + removal hook; BL-STALE's read logic is R1's, unchanged.
