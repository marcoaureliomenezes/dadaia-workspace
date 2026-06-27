# PLAN — Release: v0.1.25 — Backlog-consistency foundation (R1)

**Status:** Aprovado
**Release ID:** v0.1.25
**Owner:** product-engineer
**Opened:** 2026-06-26
**Implements:** `specs/releases/v0.1.25/SPEC.md` (all clusters §3.1–§3.6, constraints §3.8)

---

## 1. Strategy

TDD throughout, bottom-up in the architect's seven-step sequence. Each module is a **pure**
feature under `dadaia_workspace/features/backlog/` (no I/O outside explicitly-injected
roots), mirroring `features/ci_preflight/` (injectable runner, single source of truth) and
`features/specs/doctor.py` (StrEnum check codes, no I/O outside the supplied dir). The CLI
layer (`cli/commands/lifecycle.py` `backlog_app`) and the shell chokepoint
(`public/scripts/`) are thin wirings over the pure core.

**Tests-first per module.** Every module lands its unit tests in the same task, written
against a **fixed `tmp_path` fixture tree** built from inline `MINIMAL_*` constants — never
the live repo (SPEC §3.7.8). Live derivation gets exactly one scoped create/delete test; the
git-hook chokepoint gets one e2e (SPEC §3.7.9). The four BL-* checks are one **parameterized**
test, not four copies (SPEC §3.8).

## 2. Layers affected

| Layer | Files | Nature |
|---|---|---|
| `core/models/` | `core/models/backlog.py` (new) | Pure typed `Intent`/`Subject` dataclasses + validation |
| `features/backlog/` | `subject_registry.py`, `classifier.py`, `doctor.py`, `ledger.py`, `preview.py` (new) | Pure logic, injected roots |
| `cli/commands/lifecycle.py` | extend `backlog_app` | `backlog doctor`, `backlog subjects` subcommands |
| `cli/commands/ci.py` | extend `pre-commit-check` | chain BL-* doctor into the pre-commit backend |
| `public/scripts/` | `pre-commit-lease-gate.sh` (touch) / new wiring | run BL-* at the chokepoint |
| `.github/workflows/` | `ci.yml` (touch) | run `backlog doctor` in CI |
| `.dadaia/states/` | `backlog_subject_aliases.txt` (new, operator/PE-seeded) | alias map (R1 sole panel/api bind path) |
| `specs/backlog/*.md` | 14 survivors | backfill bound `intents[]` |

`architecture.md` memory update is CLOSURE-only (add `features/backlog/`).

## 3. Execution order (architect's 7 steps → task groups)

1. **Schema** (`core/models/backlog.py`) — typed `Subject{kind,ref}` + `Intent{subject,
   change}` dataclasses; `kind ∈ {code,api,cli,panel,doc,invariant,catalog}`; pure
   validation (well-formed ref per kind; `code` ref matches `path#symbol`). No resolution.
2. **Registry + preview** (`subject_registry.py`, `preview.py`) — the linchpin, lands early.
   Five auto-derived kinds: `code` (AST walk of the injected source root + grep fallback),
   `cli` (walk the Typer app tree for command ids), `catalog` (`catalog.json` slugs + atom
   ids), `doc` (spec-doc ids: `SPEC-DOC-NNN` + memory heading anchors), `invariant` (named
   `INV-*`). `panel`/`api` resolve **alias-only** (no auto-derivation). Injected alias-map
   path. `bind(subject) -> Anchor | HALT(UNRESOLVED|AMBIGUOUS)`. Preview = read-only
   `resolve_one(ref)` + `list_anchors(kind?)` consumed by the CLI surface.
3. **Classifier** (`classifier.py`) — set-intersection over bound anchor sets. Empty → 
   `UNRELATED`; same anchors + same change → `DUPLICATE`; shared anchor + differing change →
   `DIVERGENT_CONFLICT` (fail-closed DEFAULT). Model-downgrade seam exposed but **offline**
   in R1 (a `Callable` param defaulting to "no downgrade"). `Verdict` StrEnum.
4. **Doctor** (`doctor.py`) — `BL-SCHEMA/DUP/CONFLICT/STALE` as a `StrEnum`; one
   parameterized check engine over the loaded backlog set; consumes registry + classifier +
   ledger. Returns structured findings (severity/code/message). Pure — injected specs-dir,
   alias-map path, archive root. Then CLI `backlog doctor` (+ `--explain`) and `backlog
   subjects`.
5. **Ledger reader** (`ledger.py`) — read `specs/_archive/*/consumed_backlog.json` by
   exact slug membership; tolerate absence (no-op). Feeds BL-STALE. Define the JSON shape
   (`{slug, shipped_anchors[]}`) as a typed dataclass; R1 reads only.
6. **Chokepoint + CI wiring** — chain BL-* doctor into `dadaia ci pre-commit-check` backend
   (or a sibling `backlog doctor` invocation in the shell hook) + add a `backlog doctor`
   step to `ci.yml`. Git-hook-level e2e proves block/pass.
7. **Backfill** (owner: product-engineer) — run the preview over the 14 survivors, seed the
   alias map for genuine gaps, author bound `intents[]`, drive `backlog doctor` to exit 0.

## 4. Module contracts (pure, injected roots)

```python
# core/models/backlog.py
@dataclass(frozen=True)
class Subject: kind: SubjectKind; ref: str
@dataclass(frozen=True)
class Intent: subject: Subject; change: str

# subject_registry.py — all roots injected, never cwd
def build_registry(*, source_root: Path, catalog_path: Path,
                   alias_map_path: Path, specs_dir: Path) -> Registry: ...
class Registry:
    def bind(self, raw_ref: str, kind: SubjectKind) -> BindResult  # Anchor | UNRESOLVED | AMBIGUOUS
    def list_anchors(self, kind: SubjectKind | None = None) -> list[Anchor]

# classifier.py
def classify(new: Sequence[Intent], existing: Sequence[BacklogItem],
             *, downgrade: Downgrade = no_downgrade) -> list[Classification]

# ledger.py
def read_consumed(archive_root: Path) -> dict[str, set[str]]  # slug -> shipped_anchors; {} if absent

# doctor.py
def run_backlog_doctor(*, specs_dir: Path, source_root: Path, catalog_path: Path,
                       alias_map_path: Path, archive_root: Path) -> list[Finding]
```

`Path` arguments are **always injected** (SPEC §3.8 finding #6) — no `os.getcwd()`. Code
anchors are **module-relative** (`path#symbol`); the registry rejects absolute/operator-local
paths and private repo names from committed intents (SPEC §3.8 finding #7).

## 5. Technical risks (from SPEC §6, with the plan's mitigation)

| Risk | Plan mitigation |
|---|---|
| Registry AST coverage under/over-resolves (HIGH, linchpin) | AST walk + grep fallback for `code`; unit-test each of the 5 kinds against fixtures; HALT-on-ambiguous is the default; alias map is the documented escape hatch; backfill (T-25-07) is the integration proof over all 14 real items. |
| Ledger has no writer in R1 | `read_consumed` returns `{}` on absence → BL-STALE no-op; unit-test against a hand-crafted sidecar fixture. |
| Backfill binds wrong/fabricated anchor | Preview surface (T-25-03) authored-against; BL-SCHEMA forces resolution; PE never fabricates — aliases for genuine synonyms only. |
| Pre-commit chokepoint blocks legit commits / slows hook | Mirror `ci pre-commit-check`; keep derivation scoped; clean tree must pass (e2e tests both block + pass). |
| Model-adjudication seam unexercised | Fail-closed default → only over-reports (safe); seam unit-tested offline; R2 owns the live model. |

## 6. Validation plan

- **Per module:** `pytest` over the module's `tests/unit/test_backlog_*.py` (fixed
  `tmp_path` `MINIMAL_*` trees). `mypy --strict` clean. `ruff format --check` + `ruff check`.
- **Live-derivation scoped test:** one test creates a temp source file with a known symbol,
  asserts the registry resolves it, deletes it, asserts it no longer resolves.
- **Integration:** `tests/integration/test_backlog_doctor.py` — `backlog doctor` over a
  fixture specs-dir with planted BL-SCHEMA/DUP/CONFLICT/STALE (one **parameterized** test)
  and a clean tree.
- **e2e:** `tests/e2e/features/test_backlog_precommit.py` — install the hook in a fixture
  git repo, plant a divergent twin → commit BLOCKS; clean tree → commit PASSES.
- **Live tree:** final `pytest` (full suite) + `dadaia backlog doctor` exit 0 on the real
  `specs/backlog/` after backfill (T-25-08).
- **No pollution:** all tests run with caches redirected/off; no in-repo `.dadaia/`,
  `.mypy_cache/`, `.pytest_cache/` left behind (conftest repo-root write guard backstops).

## 7. Out of scope (R2) — restated for the implementer

The workflow body (`backlog_definition`), the removal-on-release closure hook, the ledger
**writer**, the real fragments, the live model-adjudication step, and the `backlog_index`
selector are all **R2 (v0.1.26)**. R1 ships only the deterministic foundation + read paths
+ backfill. Do not implement any R2 surface; expose the seams only (SPEC §4).
