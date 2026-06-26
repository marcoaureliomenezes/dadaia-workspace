# TASKS — Release: v0.1.25 — Backlog-consistency foundation (R1)

**Status:** Aprovado
**Release ID:** v0.1.25
**Owner:** product-engineer
**Opened:** 2026-06-26
**Implements:** `specs/releases/v0.1.25/SPEC.md` + `PLAN.md`

Markers: `[ ]` OPEN → `[-]` IN PROGRESS → `[x]` DONE. One `[-]` per owner at a time. Owner
is `software-engineer` unless noted. Every task's **Done-when** includes: `mypy --strict`
exit 0 on `dadaia_workspace/`, `ruff format --check` + `ruff check` clean, the task's tests
green, and **no in-repo `.dadaia/`/cache pollution** left in the working tree.

Tasks are ordered by the architect's 7-step sequence; the hardest module (registry, T-25-02)
lands early; backfill (T-25-07) lands after the preview surface exists.

---

## [x] T-25-01 — `intents[]` schema (typed `Subject`/`Intent` dataclasses)

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/core/models/backlog.py`,
  `tests/unit/test_backlog_models.py`
- **Preconditions:** none (foundational).
- **Description:** Pure, frozen `SubjectKind` StrEnum (`code,api,cli,panel,doc,invariant,
  catalog`), `Subject{kind,ref}`, `Intent{subject,change}`. Per-kind ref validation: `code`
  ref matches `path#symbol` and is **module-relative** (reject absolute/operator-local paths
  + private repo names — SPEC §3.8 finding #7). No resolution/binding here (that is T-25-02).
- **Done-when:** unit tests cover valid + each invalid ref shape; mypy/ruff clean.

## [x] T-25-02 — Canonical-subject registry (the linchpin) + 5-kind auto-derivation

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/backlog/__init__.py`,
  `dadaia_workspace/features/backlog/subject_registry.py`,
  `tests/unit/test_backlog_subject_registry.py`
- **Preconditions:** T-25-01.
- **Description:** `build_registry(*, source_root, catalog_path, alias_map_path, specs_dir)`
  recomputed from live truth. Auto-derive **five** kinds: `code` (AST walk + grep fallback),
  `cli` (Typer app-tree command ids), `catalog` (`catalog.json` slugs + atom ids), `doc`
  (`SPEC-DOC-NNN` + memory heading anchors), `invariant` (`INV-*`). `panel`/`api` bind via
  **alias map only** (no auto-derivation in R1 — SPEC §3.2/ADR-A). Alias-map path is
  **injected** (SPEC §3.8 #6). `bind(raw_ref, kind) -> Anchor | UNRESOLVED | AMBIGUOUS` —
  **HALT (reject, not silent NEW)** on unresolved/ambiguous with an actionable message
  naming the ref (acceptance §3.7.1, §3.7.5).
- **Done-when:** unit tests per kind over a fixed `tmp_path` `MINIMAL_*` source tree +
  minimal `catalog.json` + minimal alias map (SPEC §3.7.8); one **scoped** live-derivation
  test creates/deletes its own source file and asserts resolution changes; alias collapses a
  synonym to one anchor; HALT messages tested; mypy/ruff clean.

## [x] T-25-03 — Resolve/preview surface (`backlog subjects`, `doctor --explain`)

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/backlog/preview.py`,
  `dadaia_workspace/cli/commands/lifecycle.py` (extend `backlog_app`),
  `tests/unit/test_backlog_preview.py`, `tests/integration/test_cli_backlog_subjects.py`
- **Preconditions:** T-25-02.
- **Description:** Read-only `resolve_one(ref, kind)` + `list_anchors(kind?)`. CLI:
  `dadaia backlog subjects` (list anchors, optional `--kind`/`--resolve "<ref>"`) and
  `--explain` mode showing bound anchor or `UNRESOLVED`/`AMBIGUOUS` + candidate set + alias
  suggestion. **Never writes** a backlog file or the alias map (SPEC §3.4a). Lands BEFORE
  backfill so PE authors against real anchors.
- **Done-when:** unit + CLI integration tests over a fixture tree; mypy/ruff clean.

## [x] T-25-04 — Deterministic conflict classifier (Python disposes, fail-closed)

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/backlog/classifier.py`,
  `tests/unit/test_backlog_classifier.py`
- **Preconditions:** T-25-02.
- **Description:** `classify(new, existing, *, downgrade=no_downgrade)`. Anchor-set
  intersection: empty → `UNRELATED`; same anchors + same change → `DUPLICATE`; shared anchor
  + differing change → `DIVERGENT_CONFLICT` (fail-closed DEFAULT). Model-downgrade seam is a
  `Callable` param, **offline** in R1. `Verdict` StrEnum.
- **Done-when:** unit tests prove `DUPLICATE` (acceptance §3.7.2) and the `C→D`/`C→E`
  `DIVERGENT_CONFLICT` with the model OFFLINE via a FAKE fixture (acceptance §3.7.3);
  mypy/ruff clean.

## [x] T-25-05 — `consumed_backlog` ledger reader (sidecar JSON, BL-STALE feed)

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/backlog/ledger.py`,
  `tests/unit/test_backlog_ledger.py`
- **Preconditions:** T-25-01.
- **Description:** Define the typed sidecar shape (`{slug, shipped_anchors[]}`) and
  `read_consumed(archive_root)` scanning `specs/_archive/*/consumed_backlog.json` by **exact
  slug membership**; returns `{}` on absence (no-op, never false ERROR — ADR-C, acceptance
  §3.7.6). **R1 reads only** (R2 writes).
- **Done-when:** unit tests over a hand-crafted sidecar fixture + absence case; mypy/ruff
  clean.

## [x] T-25-06 — `backlog doctor` (BL-SCHEMA/DUP/CONFLICT/STALE) + CLI + chokepoint + CI

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/backlog/doctor.py`,
  `dadaia_workspace/cli/commands/lifecycle.py` (add `backlog doctor`),
  `dadaia_workspace/cli/commands/ci.py` (chain BL-* into `pre-commit-check`),
  `dadaia_workspace/public/scripts/pre-commit-lease-gate.sh` (run BL-* at chokepoint),
  `.github/workflows/ci.yml`, `tests/integration/test_backlog_doctor.py`,
  `tests/e2e/features/test_backlog_precommit.py`
- **Preconditions:** T-25-02, T-25-04, T-25-05.
- **Description:** `run_backlog_doctor(*, specs_dir, source_root, catalog_path,
  alias_map_path, archive_root)` — all **injected** paths (SPEC §3.8 #6). `BL-*` StrEnum;
  **one parameterized check engine** (no copy-paste fan-out — SPEC §3.8 #8). Wire into the
  pre-commit chokepoint backend + CI, mirroring the `ci preflight` pattern. After `public/`
  edits run `dadaia public stage && dadaia public install --target all && dadaia public
  doctor` (exit 0) so the instance reflects the source.
- **Done-when:** integration test = **one parameterized** test planting each BL-* violation +
  a clean tree (acceptance §3.7 + §3.8); **git-hook-level e2e** installs the hook in a
  fixture git repo, divergent twin BLOCKS, clean tree PASSES (acceptance §3.7.9);
  `dadaia public doctor` exit 0; mypy/ruff clean.

## [x] T-25-07 — Backfill bound `intents[]` onto the 14 survivors (via preview)

- **Owner:** product-engineer
- **Write set:** `specs/backlog/<each of the 14 survivors>.md`,
  `.dadaia/states/backlog_subject_aliases.txt`
- **Preconditions:** T-25-03 (preview), T-25-06 (doctor exit-0 gate).
- **Description:** Run the preview (T-25-03) over each survivor's true subjects; seed the
  alias map for **genuine** gaps (incl. all `panel`/`api` subjects — alias-only in R1); author
  bound `intents[]` against the **real** anchors surfaced — never fabricated (SPEC §3.5).
  Module-relative anchors only; no operator-local paths/private names (SPEC §3.8 #7).
  `specs/backlog/` is ADDITIVE — gate-free.
- **Done-when:** every survivor carries valid bound `intents[]`; `dadaia backlog doctor`
  exits 0 over the live `specs/backlog/` (acceptance §3.7.7).

## [x] T-25-08 — Final live-tree verification

- **Owner:** software-engineer
- **Write set:** none (verification only; may touch a test fixture if a gap is found, raise
  to operator otherwise).
- **Preconditions:** T-25-01..T-25-07 all `[x]`.
- **Description:** Run the **full** `pytest` suite and `dadaia backlog doctor` on the live
  tree; confirm both exit 0 and no in-repo cache/`.dadaia` pollution remains. Confirm
  `dadaia specs doctor --specs-dir specs` is structurally green.
- **Done-when:** full `pytest` green; `dadaia backlog doctor` exit 0; `dadaia specs doctor`
  green; mypy/ruff clean; working tree clean of pollution.
