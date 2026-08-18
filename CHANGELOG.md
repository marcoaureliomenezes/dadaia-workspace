# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Versioning note (SPEC v0.4.2 FR13 — the PyPI lineage is the only version axis)

ADR R2 (v0.4.2) retires the two-axis split between "package version" and "internal
spec-release id": the **published PyPI lineage is the only axis this project tracks**,
and the release id *is* the minted version (this release is `v0.4.2`, minting package
version `0.4.2`). Measured directly against the package index at implementation time
(`https://pypi.org/pypi/dadaia-workspace/json`, captured
2026-08-16T17:32:59Z — evidence:
`.dadaia/tmp/software-engineer/20260816/t-042-16-pypi-versions.json`): **13 versions are
published**, `0.1.0` through `0.4.1`; `0.4.2` is not yet published — it is minted at this
release's ship.

The headings below from **`[0.9.0]` down through `[0.5.0]`** (inclusive of the three
`[Unreleased] — spec release vX` sections nested among them) were **minted internally
and never published to PyPI** — kept exactly as written, never renamed, renumbered or
removed, mapped here to the internal spec-release id each one documents:

| CHANGELOG heading | Internal spec-release id |
|---|---|
| `[0.9.0]` — 2026-08-15 | `v0.12.0` ("backlog-tooling-single-source") |
| `[0.8.0]` — 2026-08-15 | `v0.11.0` ("scan-v2") |
| `[0.7.1]` — 2026-08-15 | hotfix (Arm B, `hotfix/0.7.1`) — hotfixes mint no spec-release id, by design |
| `[0.7.0]` — 2026-08-15 | `v0.10.0` (`dd-lifecycle-skills-family`) |
| `[0.6.0]` — 2026-08-14 | `v0.9.0` (`push-range-denylist-scan`) |
| `[0.5.2]` — 2026-08-14 | hotfix (Arm B, `hotfix/v0.5.2`) — hotfixes mint no spec-release id, by design |
| `[0.5.1]` — 2026-08-14 | hotfix (Arm B, `hotfix/v0.5.1`) — hotfixes mint no spec-release id, by design |
| `[Unreleased] — spec release v0.7.0` | `v0.7.0` (self-named in its own heading) |
| `[Unreleased] — spec release v0.6.0` | `v0.6.0` (self-named in its own heading) |
| `[Unreleased] — spec release v0.5.0` | `v0.5.0` (self-named in its own heading) |
| `[0.5.0]` — Unreleased | `v0.3.0` (self-named in its own heading, "spec release v0.3.0") |

**From `0.4.2` onward, one `## [x.y.z]` section corresponds to exactly one published
package version** — no further internal spec-release id is minted under a
package-version-shaped heading; the `[0.4.2]` section for this release is added at ship.

**Known, separate gap — observed here, not reconciled by this preamble.** The same
package-index measurement shows further pre-existing discrepancies between the
CHANGELOG's `[0.1.x]` section headings and the real PyPI lineage — out of SPEC v0.4.2
FR13's scope (reconciling them would add/rename/backfill headings, which A13.2 forbids
for this task, so none is touched here):

- Three existing headings do not match any published version: `[0.1.24] — Unreleased`,
  `[0.1.7]` — 2026-06-13, and `[0.1.3]` — 2026-06-03 (PyPI's `0.1.x` lineage runs
  `0.1.0`, `0.1.1`, `0.1.2`, `0.1.4`, `0.1.5`, `0.1.6` — there is no published `0.1.3`,
  `0.1.7` or `0.1.24`).
- Ten published versions have no CHANGELOG section at all: `0.1.2`, `0.1.5`, `0.1.6`,
  `0.2.0`, `0.2.1`, `0.2.2`, `0.2.3`, `0.3.0`, `0.4.0`, `0.4.1`.

Left exactly as written; a future task can pick this up.

## [0.4.3] — 2026-08-18

Hotfix (Arm B, `hotfix/0.4.3`) — bug
`specs-upgrade-emits-atoms-violating-frontmatter-schema` (HIGH).

`memory-frontmatter-v1` is a closed schema (`additionalProperties: false`), so every key
dropped from it turns existing consumer atoms into doctor errors. v0.1.72 shipped that
migration for `agent_tier` as a hard-coded single-key step; when `token_estimate` was
dropped later, no migration followed. `dadaia specs upgrade` therefore rewrote consumer
atoms and then failed its own post-upgrade doctor with LINT-1 `Additional properties are
not allowed ('token_estimate' was unexpected)`, pointing the operator at a backup and
leaving the tree stuck at its old pattern version — reproduced on three independent
consumer trees.

Fixed as a class, not an instance: the new `retired-frontmatter-keys` step (pattern
version **4 → 5**) derives the retired set from the shipped schema's `properties` at run
time, so a future schema-drop is migrated by construction. The frontmatter fence scanner
moved to `features/migrate/frontmatter_keys.py` and the historical `agent-tier-frontmatter`
step now delegates to it — one scanner, two callers. `CANONICAL_SPECS_VERSION` is 5 and
the scaffold constitution stamp follows it.

**Consumer action:** run `dadaia specs upgrade` per context to reach pattern version 5.

---

Second hotfix folded into this same unpublished mint (no separate PATCH number is minted
for a version that never reached the index — the `[0.4.2]` publish-number collapse above
is the precedent): bug `upgrade-never-refreshes-uncustomised-scoped-law-projection`
(MEDIUM).

`specs/AGENTS.md` is projected once and never refreshed: TREE-5 reports drift and
`--fix` declines, because overwriting could destroy operator customisation. With no way
to recognise our own earlier output, a file nobody had ever edited was frozen exactly like
a hand-written one — so instances kept scoped law ordering agents to run
`dadaia lifecycle`, a command the CLI no longer exposes.

The tool now ships the evidence it was missing: `public/templates/shipped-hashes.json`
records the sha256 of every published version of a template. When the on-disk bytes match
one of them the file is provably untouched, TREE-5 becomes **fixable**, and
`dadaia specs doctor --fix` refreshes it losslessly. Bytes we never shipped are operator
content and remain warn-only — re-verified inside the repair itself — and an instance with
no history file keeps the old conservative behaviour. The history is append-only by
contract, pinned by a test that fails if a template is edited without recording its new
digest.
Trees already at 4 are repaired by the new step; the migration is byte-preserving,
idempotent and dry-run-capable, and prose mentions of retired keys in document bodies are
never touched.

## [0.4.2] — 2026-08-18

One published version carrying the two merged, previously-unpublished internal releases
below (operator lineage ruling, 2026-08-18: the registry's latest published version is
0.4.1, so the next mint is 0.4.2; the internally-minted 0.4.3 number is retired
unpublished — internal provenance ids in code comments, task ids and `specs/_archive/`
directory names keep their historical spelling, mapped by the subheadings below).

### v0.4.3 "claims-made-true / backlog-zero" (2026-08-18)

The operator's standing order (the entire `## ACTIVE` backlog queue in one release,
residuals minimised to zero) shipped as one segmented release: 6 `alpha-N` increments
plus a shipping candidate, 32 FRs, 53 tasks, 24 backlog slugs delivered. Archived at
`specs/_archive/releases/v0.4.3/`.

#### Added
- **The push gate reads commit objects, not just blobs**: the header/body boundary is
  respected and a term is never amnestied path-less (fail-closed) — closes the
  commit/tag-body scanning gap.
- **Privacy baseline v8**: carve-outs now carry a stated rationale, the dotted-chain class
  has a structural rule, and the law-mandated co-author trailer no longer refuses its own
  push.
- **Cache guard**: the venv-guard layer refuses to let a pytest/ruff/mypy cache be born
  inside a repo working tree.
- **Governance primitives**: a non-terminal `picked` bug-ledger event; `specs/memory/`
  dotfiles ratified into the MEMORY path class; a repo-`AGENTS.md` destination write
  refuses a symlink target.
- **Suite curation + a first complexity ratchet**: the LARGE (E2E) census measured and
  curated (102 → 100); `C901`/`PLR1702` pinned at their measured maxima (63 / 6,
  downward-only ratchet); a first mutation-testing baseline (`mutmut==3.7.0`, 90.4% kill
  rate, off the push path).
- **Codex fidelity**: personas compacted −8.3% (law loaded once, never restated per
  session), a version-qualified trust boundary, and a live `codex exec` certification
  probe.
- **Event-driven artifact GC**: ack-on-consume for coordination handoffs, a push-verdict
  collector wired into the ship flow (`dadaia ci gc-push-verdicts`), a release-closure
  sweep, a reconciler that reaps what it already walks, write-time log rotation, and
  `dadaia tmp gc` as the sole calendar-based backstop.

#### Changed
- **Workspace-root resolution fixed** — the ancestor walk no longer silently mistargets
  from a nested working directory (found live by this release's own consumer round).
- **The whole assembled surface, GC included, validated on a throwaway real consumer
  workspace**, and the published CHANGELOG lineage backfilled from git history with no
  invention (this section's own predecessors, below).

### v0.4.2 "residual-convergence" (2026-08-16)

The first internal release under the one-axis rule (release id = minted package version,
PyPI lineage; latest published 0.4.1). Fixes the three root causes behind the recurring
per-release residual spray, at class level. Archived at `specs/_archive/releases/v0.4.2/`.

#### Added
- **Range-wide multi-path amnesty denial (fail-closed)**: a blob reachable at more than
  one path anywhere in the pushed range gets no prior-published-term amnesty — adapter
  side only, matcher untouched.
- **Privacy baseline v5**: structural home-path coverage for every declared platform —
  POSIX `/home`, macOS `/Users`, Windows `C:\Users` — with literal-anchored carve-outs
  and prose-form parity across the three patterns.
- **Self-scan sentinel covers archive-authored blobs**: a NEW blob authored directly
  into `specs/_archive/**` is scanned; `git mv` renames stay excluded (blob reuse).
- **Review-before-archive canon**: the six-axis code review runs on the thawed tree
  before close/archive (order: implementation → QA → code review → remediation →
  memory/CLOSURE/archive → ship). Proven on its own first run: two HIGH findings fixed
  and re-reviewed with zero reopened artifacts.
- **Calibrated intake routing**: reviews record everything; record-only observations
  terminate in the release CLOSURE or reviewer handoff; only actionable defects reach
  the operator's intake report.

#### Changed
- **One backlog grammar seam**: `backlog new` moved into `features/backlog/` and writes
  through the same fence-aware parser that validates the document (write-then-verify).
- **The refusal masker consumes the detector's own matchers** — one predicate for
  "what is a private name"; `GitObjectReadError` carries a structured, maskable path.
- **`token_estimate` is computed by the catalog generator** — the hand-maintained
  frontmatter key is deleted from every memory atom and from the schema; derived
  values are computed, never stored.
- **SPEC-DOC-031 counts consumption, not conversation** (an archived SPEC's
  `**Consumes:**` and CLOSURE `## Dispositions` rows) — the citation false-positive
  class died (12 → 0 warnings) instead of being annotated item by item.
- **Fence filter is O((H+F)·logF)** via bisect over ascending ranges; YAML loads via
  CSafeLoader.
- **Batch `missing` rows are classified by suffix**, so new paths containing spaces
  are absence, not a desync refusal; the git-read fail-soft is narrowed to the
  intentional early close only.

#### Removed
- **The dead hotfix-release scaffold surface**: `dadaia specs hotfix open`, both
  hotfix templates, and the unconditional `candidates.md` warning it emitted — Arm B
  needs no release ceremony by law, so the tooling for one was pure bug surface.

## [0.4.1] — 2026-07-20

*Retroactive section (T-043-48/FR31, SPEC R5) — derived strictly from `git log
v0.4.0..v0.4.1` (1 commit, `bd6c9f2a`); no invention, no category guessed from an
unread diff — the commit subject is quoted with any private name masked (`H…s` style,
DADAIA.md §7; the sha keeps every line reviewer-checkable) and the range is
reviewer-checkable.*

- `bd6c9f2a` feat: v0.2.9 — H…s real-use convergence (0.4.1) (#173)

## [0.4.0] — 2026-07-19

*Retroactive section (T-043-48/FR31, SPEC R5) — `git log v0.3.0..v0.4.0` (2 commits,
`987e76d4`..`a94f112a`); no invention.*

- `987e76d4` fix: H…s batch-4 - fake chains complete, index-free bootstrap repack,
  chain-proving certify (candidate 0.3.1) (#171)
- `a94f112a` feat: v0.2.8 — Kimi Code as Layer-1 entry harness (0.4.0) (#172)

## [0.3.0] — 2026-07-16

*Retroactive section (T-043-48/FR31, SPEC R5) — `git log v0.2.3..v0.3.0` (2 commits,
`86f4cd99`..`f20e4492`); no invention.*

- `86f4cd99` fix: 0.3.0 — consumer-validated hotfix line reconciled with v0.2.3 (#168)
- `f20e4492` fix: 0.3.0 H…s-validated fixes (slug help regex render, recipe
  precision, lifecycle help clarity) (#169)

## [0.2.3] — 2026-07-14

*Retroactive section (T-043-48/FR31, SPEC R5) — `git log v0.2.2..v0.2.3` (2 commits,
`2d7d93da`..`49f9940c`); no invention.*

- `2d7d93da` fix(lifecycle): gate-integrity overhaul from ALL-WORKFLOWS stress test —
  25 bugs root-caused (#162)
- `49f9940c` feat: v0.2.3 — simplified dadaia-workflows, release-folder handoffs,
  spark-only Layer-2 (#167)

## [0.2.2] — 2026-07-11

*Retroactive section (T-043-48/FR31, SPEC R5) — `git log v0.2.1..v0.2.2` (47 commits,
`4a433063`..`fa6e742d`, 2026-07-05 to 2026-07-11). Representative subjects below, not
exhaustive — the full range is git-checkable; no category breakdown invented from an
unread diff.*

- `11cfd37c` feat(v0.1.81)!: deprecation strips & doctor cleanup — tier: window closed
  (operator-waived date gate) (#159)
- `e002e7d9` feat(v0.1.77): central bind-resolution seam — one resolution path for
  every verb (#151)
- `5dbe209c` feat(v0.1.76): lock liberation — advisory presence replaces the blocking
  lease (#149)
- `3965df4c` feat: v0.1.61 Audit Remediation & Memory Truth — 41 dispositions,
  PluginStore wired, cli-no-infra cap (#116)
- `fa6e742d` chore: bump package version to 0.2.2 for PyPI release (#161) (tag commit)

## [0.2.1] — 2026-07-05

*Retroactive section (T-043-48/FR31, SPEC R5) — `git log v0.2.0..v0.2.1` (1 commit,
`b1cb28dc`); no invention.*

- `b1cb28dc` docs(readme): document current capabilities; release 0.2.1 to refresh
  PyPI page (#113)

## [0.2.0] — 2026-07-04

*Retroactive section (T-043-48/FR31, SPEC R5) — `git log v0.1.6..v0.2.0` (41 commits,
`a83589b1`..`13c85eea`, 2026-06-12 to 2026-07-04). Representative subjects below, not
exhaustive — the full range is git-checkable; no category breakdown invented from an
unread diff.*

- `4ccc6a21` feat: v0.1.60 Capability Tail — plugin packs + install command,
  efficiency-audit trigger, provenance-gated consumer fan-out (#110)
- `b0bd8217` feat: v0.1.58 Harness & Projection Distribution — typed registry, init
  profiles, profile-aware doctor, consumer fan-out (#106)
- `fc10dae7` feat: real Layer-2 workflows + coherent worker-output contract
  (v0.1.30–v0.1.32) (#69)
- `a83589b1` feat: PI fourth harness, two-layer model, drift elimination + Layer-1
  Ring-1 (v0.1.15→v0.1.21) (#66)
- `13c85eea` chore(release): bump version 0.1.7 -> 0.2.0 for PyPI deploy (#112) (tag
  commit)

## [0.1.6] — 2026-06-12

*Retroactive section (T-043-48/FR31, SPEC R5) — `git log v0.1.5..v0.1.6` (5 commits,
`8b80090e`..`6b637427`); no invention, all 5 commits listed.*

- `8b80090e` chore(release): 0.1.7 — Audit Remediation + Unlock the Workflow (#48)
- `db7aecbe` feat(release): 0.1.8 — Cross-Platform OS Compatibility
  (Linux/macOS/Windows) (#49)
- `9693121b` chore(release): bump version 0.1.7 -> 0.1.8 + CHANGELOG (#50)
- `91bbaeb9` fix(platform): 0.1.8 rc-2 — Windows graduation (hard-gated tri-platform
  CI) (#51)
- `6b637427` feat(release): v0.1.14 — Deterministic Lifecycle Kernel (chokepoints,
  bind-driven injection, zero-false-block) (#56) (tag commit)

## [0.1.5] — 2026-06-07

*Retroactive section (T-043-48/FR31, SPEC R5) — `git log v0.1.4..v0.1.5` (189
commits, `218d8303`..`29f8e3ed`, 2026-06-06 to 2026-06-07). Representative subjects
below, not exhaustive — the full range is git-checkable. The range includes commits
self-labelled with internal spec-release numbers ("v0.2.0", "0.2.1") that predate the
real published `0.2.x` versions below — the same internal-vs-published numbering split
this project later retired (v0.4.2 ADR R2); no category breakdown invented from an
unread diff.*

- `44757d83` feat: v0.2.0 agentic development lifecycle + soul & correctness fold
  (#39)
- `361019a7` feat(v0.2.1): open release + WS-1 vision canonization + WS-4 doctor
  fidelity
- `3e5ea863` feat(gate): T-R1-01 runtime→session ptr file env-free resolution
- `792052ae` feat(cli): reconcile hotfix flow with the alpha/rc model (T-ENG-07)
- `29f8e3ed` fix(codex): harden runtime projection compatibility (tag commit)

## [0.1.2] — 2026-05-28

*Retroactive section (T-043-48/FR31, SPEC R5) — `git log v0.1.1..v0.1.2` (1 commit,
`1f0687bd`); no invention.*

- `1f0687bd` chore(release): 0.1.2 — ad blocker fix, /health endpoint, context-gate
  fix, agent-friendly README (#15)

## [0.9.0] — 2026-08-15

Release v0.12.0 "backlog-tooling-single-source". Two pre-approved entries delivered
(`backlog-tooling-reconciliation`, `backlog-md-physical-consolidation`); archived at
`specs/_archive/releases/v0.12.0/`. Pre-PR code review returned APPROVE with two
MEDIUMs, both resolved before ship (fence-aware parsing; corrected closure evidence).

### Added
- **`specs/backlog/BACKLOG.md` is now the physical single source of the backlog**:
  an `## ACTIVE` section (one strict-schema subsection per live item — Title, Opened,
  Status, Description, Provenance, optional Intents) and an `## LEDGER` section (one
  line per closed item with its terminal disposition token). Consolidated from 31 live
  per-entry files + `candidates.md` with a countable never-delete proof: 82 slugs in,
  82 slugs out, both set differences empty.
- **`features/backlog/document.py`** — the pure single-source parser (`load_document`,
  `ActiveItem`, `LedgerRow`); diagnostic, never-throwing; absent document = empty
  model; **fence-aware section splitting** (a fenced `##` heading inside a subsection
  is content, never structure; an unclosed fence at EOF surfaces a diagnostic, never a
  silently shrunken model).
- **`backlog new` authors an ACTIVE subsection** into BACKLOG.md (byte-diff-safe
  insertion, slug uniqueness across ACTIVE ∪ LEDGER) instead of scaffolding a file.

### Changed
- **`backlog doctor` validates BACKLOG.md** — the four BL-* codes ride the document
  model: BL-SCHEMA, BL-DUP (plus ACTIVE/LEDGER duplicate slugs), BL-CONFLICT, and a
  re-defined BL-STALE (three ORed staleness conditions).
- **Governance re-target**: SPEC-DOC-031 now walks ACTIVE subsections; SPEC-DOC-035 is
  the loose-file single-source invariant (nothing loose in `specs/backlog/` beyond
  BACKLOG.md and README.md, excluding `_archive/` and `remote-bugs/`).
- **The `dd-backlog-definition` and `dd-release-definition` skills state the mechanism
  that runs**: `**Consumes:**` is SPEC provenance; consumption = purge-on-pick at the
  SPEC commit + the closure disposition sweep, backstopped by BL-STALE and SPEC-DOC-031.
- Fresh-scaffold backlog stubs author a BACKLOG.md skeleton (the old
  `candidates.md`/`ideas.md` stubs tripped the new single-source invariant); the
  skeleton is test-pinned to the `backlog new` writer and round-trips `load_document`.

### Removed
- **The dead removal/consumption write side**: `removal_lifecycle.py`, `removal.py`,
  `ledger_writer.py`, `consumes.py` and their container builder — zero production
  callers since the workflow engine's removal, and a rewrite-down contract that
  contradicted the never-delete law. `ledger.py`'s `read_consumed` survives as the
  live BL-STALE input. `check_backlog_schema` (SPEC-DOC-012, and with it
  SPEC-DOC-022/023) retired with the per-entry shape.

## [0.8.0] — 2026-08-15

Release v0.11.0 "scan-v2" — prior-published-term amnesty and push-gate hardening.
Nine backlog entries delivered (#19 #20 #22 #23 #25 #26 #27 #28 #29); archived at
`specs/_archive/releases/v0.11.0/`. Pre-PR code review returned APPROVE with three
MEDIUMs, all remediated before ship (amnesty predicate anchored to value equality;
term sources materialized once; evidence claims pinned by test).

### Added
- **Prior-published-term amnesty** (`prior-published-term-amnesty`, P1): a term already
  present in the remote-reachable version of the SAME path no longer refuses the push —
  the blob is new, the term is not. The suppression predicate re-runs the same layer's
  anchored matcher against the prior text and requires matched-value equality (never
  substring containment — a prior superstring cannot amnesty a new shorter value). The
  same term in a new path and a new term in an edited path still refuse. No
  sanctioned-terms list exists anywhere (the A4.1-class contract test is unmodified);
  the amnesty derives solely from published git state. No amnesty in the
  `--not --remotes` fallback shape, and oversized blobs are never amnestied — both
  deliberately fail-closed, both test-pinned.
- **Self-scan sentinel extended to `tests/**`** behind a shrink-only 29-row baseline
  (14 home-abs-path, 9 email-address, 5 ipv4-literal, 1 secret-token), plus the missing
  `integration` marker on the sentinel module.
- **`core/redaction.py`** — the masking primitive extracted stdlib-pure into `core`,
  consumed by both `cli/redact.py` and the gate renderers.

### Changed
- **Oversized blobs (>5 MB) are now partially scanned** — first 5 MB, remainder never
  fetched — and honestly reported: `skipped_binary_count` keeps only genuinely
  undecodable blobs, while each oversized blob gets a structured note naming path and
  size ("NOT fully scanned — verify by hand"). The old note mislabelled oversized text
  as "binary … not text-decodable" (CWE-778).
- **Foreign-name scan layer is registry-derived**: union of registry names, registry repo
  slugs and `repos/` directory names, minus the pushing repo's own identities — a DEAD or
  relocated context keeps protecting its name.
- **Gate refusals and notes mask private-name-bearing path segments** (CWE-532 residual
  closed; the redaction surface now covers the refusal renderer).
- **`cat-file --batch` conversation is chunk-bounded** (500 shas per chunk, constant
  resident set — 10× more blobs grows peak RSS ~22%); real-content measurement: fallback
  9,095 blobs / 130.29 MB at 0.423 s/MB, 285.5 MiB peak RSS.

### Fixed
- **Pre-push stdin shas are validated** (40/64-hex + all-zero sentinel) and count as
  malformed lines when option-shaped — closing the silent-no-op class
  (`--glob=…` yielded a successful empty rev-list; CWE-88/CWE-20). `--` end-of-options
  and a second-layer `local_sha` shape check added at every git argv interpolation site.
- **Batch-stream desync and unparsable size fields abort as `GitObjectReadError`**
  (typed, fail-closed) instead of escaping as raw `ValueError` or continuing into
  garbage (CWE-755). A path that was a directory at the remote base yields no prior
  text (non-blob prior objects are discarded, never decode-attempted).

## [0.7.1] — 2026-08-15

Hotfix (Arm B, `hotfix/0.7.1`). No release ceremony.

### Fixed
- **`pyproject.toml`'s `[tool.mypy]` comment no longer claims `incremental = false`
  alone keeps `.mypy_cache/` out of the repo tree** (bug
  `mypy-strict-cache-dir-created-without-cache-dir-env-override`, LOW). False under
  mypy 2.1.0: the cache dir (`CACHEDIR.TAG` + a version subdir) is written at its
  resolved `cache_dir` regardless of `incremental`, so a bare local
  `mypy --strict dadaia_workspace/` polluted the checkout. No portable, crash-proof
  `cache_dir` value exists (`$MYPY_CONFIG_FILE_DIR/..` assumes this checkout's depth
  under a dadaia workspace root, and an unwritable resolved target crashes mypy with
  an INTERNAL ERROR — verified). The comment and `.github/PULL_REQUEST_TEMPLATE.md`'s
  mypy checklist line now require the `MYPY_CACHE_DIR` redirect mypy itself supports —
  the same one `ci.yml` already uses, and what `dadaia ci preflight` already does
  automatically. New integration/slow test
  `tests/integration/test_mypy_local_invocation_hygiene.py` runs the PR template's
  literal documented command against an isolated copy of the real `[tool.mypy]`
  config and asserts no pollution.
- **Context/session-resolution unit tests no longer depend on an ambient
  `WORKSPACE_ROOT`** (bug `specs-resolver-context-tests-flaky-under-xdist-full-suite`,
  LOW). `core.specs_resolver._authority_workspace_root()` honours `WORKSPACE_ROOT`
  unconditionally (by design, the hook-transport channel) — ahead of, and regardless
  of, any `monkeypatch.chdir()` a test performs. Every context-resolution test file's
  isolation fixture scrubbed only the harness session-id and `DADAIA_CONTEXT`/
  `DADAIA_SESSION_ID` vars, never `WORKSPACE_ROOT` (`tests/unit/test_container.py`'s
  three `resolve_context` seam tests scrubbed nothing at all), so an ambient
  `WORKSPACE_ROOT` — inherited from the shell that launched pytest, or left behind by
  a concurrent `dadaia context bind`/`context show` sharing the real
  `.dadaia/sessions/` tree during a full-suite `-n auto` run — silently overrode every
  synthetic `tmp_path` workspace under test. Same flake class already fixed for
  `panel-e2e-readiness-flaky-under-xdist-load` /
  `panel-command-readiness-flaky-under-xdist-load`, this time isolation hardening at
  the fixture level rather than a timing bound. Centralized the isolation set
  (`CONTEXT_RESOLUTION_ENV_VARS` / `scrub_context_resolution_env`) in
  `tests/fixtures/harness_env.py` and wired it into `test_specs_resolver_resolve_context.py`,
  `test_specs_resolution.py`, `test_container.py`, `test_context_show_reflects_bind.py`,
  and `test_codex_thread_id_bind.py`.

## [0.7.0] — 2026-08-15

Release v0.10.0 (`dd-lifecycle-skills-family`).

### Added
- **The `dd-` lifecycle skill family** — seven skills, one per SDD stage, zero
  overlap, measurable style budgets: `dd-backlog-definition` (backlog curation,
  the BACKLOG.md ACTIVE/LEDGER schema, the disposition-token vocabulary, and the
  operator-gated intake protocol), `dd-release-definition`, `dd-release-implement`
  (owns the gate-cadence table), `dd-release-closure`, `dd-audit-project` (full
  merge of drift-detection), `dd-bug-registration`, `dd-bug-fix` (Arm B
  end-to-end). Three former skills renamed/merged in place; four net-new.
- **Contract test for the Codex D-CX-7 skill-reference gate** proving the `dd-`
  prefix family is validated (the rename would otherwise have degraded the check
  to a silent no-op).

### Changed
- **Always-on law dehydrated**: stage protocol moved out of `DADAIA.md` into the
  stage skills (backlog schema, hotfix flow, bug registration, watch-CI
  checkpoint); the law keeps only always-on content and points at the family.
- **Operator-gated backlog intake** (operator ADR, 2026-08-15): only the operator
  creates demand; agents route residuals to a PM intake report for operator
  adjudication; all personas and orchestration surfaces updated.
- **`ai-engineer`'s declared write surface corrected** to the real law-source
  paths (`public/data/*.md`, scaffold/template AGENTS files) — the previous
  allowlist named a non-existent directory.

## [0.6.0] — 2026-08-14

Release v0.9.0 (`push-range-denylist-scan`).

### Added
- **Push-range denylist scan at the pre-push gate**: every non-deletion ref (tags
  included) has its newly published objects scanned against three additive term
  layers — operator denylist (when present), packaged structural baseline
  (now v4, with carve-outs for RFC-2606 reserved-TLD emails, the product's own
  synthetic `workspace.local` identity, and stdlib `Path.home` call forms), and
  foreign `repos/` slugs (word-boundary, case-insensitive, self-slug excluded).
  Object reads run through a single batched `git cat-file` conversation with a
  per-blob size cap. Fail-closed on git failure; binary/oversized blobs skipped
  and counted; masked, satisfiable refusal that never echoes the matched term or
  line; `git push --no-verify` remains the single traceable bypass.
- **`--redact` output mode** on `dadaia doctor`, `dadaia context list` and
  `dadaia context show` (table and `--json`): foreign context names and repo
  slugs become stable ordinal placeholders; default output byte-for-byte
  unchanged.
- **Redaction-at-authoring doctrine** in the QA agent surface: diagnostic output
  transcribed into authored documents is captured with `--redact` or masked.

### Changed
- Packaging author email switched to the GitHub noreply form (operator decision
  during the release's own pre-PR review, whose scan refused the prior form).

## [0.5.2] — 2026-08-14

Hotfix (Arm B, `hotfix/v0.5.2`). No release ceremony.

### Fixed
- **`dadaia context alive` no longer sweeps pre-existing unrelated dirty tracked files
  into its scaffold commit** (bug `context-alive-sweeps-unrelated-worktree-changes`,
  MEDIUM). The `chore(scaffold): dadaia context alive specs baseline` commit called
  `GitClient.commit_all`, whose staging (`git add -u` + untracked sweep) is a blanket
  operation over the whole working tree — any pre-existing operator WIP on tracked files
  (e.g. a dirty `docker-compose.yml`/`supervisord.conf`) got silently folded into the
  tool-authored commit with no consent, and `git status` came back clean afterwards.
  `alive()` now tracks exactly which repo-relative paths the scaffold step itself
  created/modified (`specs/**` newly written, the individual files a merge into a
  pre-existing `specs/` actually added, `AGENTS.md`, `tests/AGENTS.md`) and stages only
  those via a new explicit-path `GitClient.commit_paths` — never `-A`/`-u` over a shared
  tree. Pre-existing unrelated worktree modifications now stay dirty and uncommitted.
  Closes the `architecture-resilience` audit finding F-10 lineage (superseded by this
  bug).

## [0.5.1] — 2026-08-14

Hotfix (Arm B, `hotfix/v0.5.1`). No release ceremony.

### Fixed
- **`ensure_workspace_venv` no longer inherits a degraded base-interpreter resolution
  for a freshly created workspace venv** (bug
  `init-venv-bootstrap-inherits-degraded-base-python`, HIGH). stdlib `venv.create()`
  resolved a NEW venv's base interpreter through `sys._base_executable` of the calling
  process; on a `--copies` venv (this workspace's own `.dadaia/.venv`), CPython's
  getpath.c re-derives that value via a landmark search for the OS-level *unversioned*
  `python3` name inside the recorded `home` directory — not the version-pinned
  `executable` its own `pyvenv.cfg` records. On a host where `/usr/bin/python3`
  symlinks to an older interpreter than the one actually running, every child venv
  silently degraded and `dadaia init` failed opaquely with "requires a different
  Python". `ensure_workspace_venv` now resolves an interpreter explicitly (its own
  `_base_executable` if it satisfies Requires-Python, else the running venv's own
  `pyvenv.cfg` `executable`, else a version-pinned `pythonX.Y` on PATH), verifies it by
  executing it, and creates the child venv via subprocess instead of the implicit
  `venv.create()`. A new pre-install post-condition also rejects an
  interpreter-mismatched venv (fresh or pre-existing/doctor-repaired) with an
  actionable message naming both versions, before ever reaching pip's bare error.

## [Unreleased] — spec release v0.7.0

Test stewardship. Lands in the same unreleased `0.5.0` package version as the spec releases
below — one dev-only dependency, no production dependency, no Python version and no
packaging contract change.

### Added
- **`dadaia-test-stewardship`, the single operational home of the test lifecycle.** A new
  universal skill carrying the intent taxonomy (CONTRACT / SENTINEL / SCAFFOLD /
  QUARANTINE, declared in the module docstring — never as a pytest marker, since the marker
  namespace already binds `contract` to a layer), the admission filter, the size tiers with
  their timeout table and the LARGE owner rule, demotion-at-closure, the deletion criteria
  with the tombstone ban and the separation of powers, the flake/quarantine pipeline,
  artifact hygiene, the health metrics with a trigger-based audit, and a parameter table
  carried as **declared adjustable defaults** so a consumer re-parameterizes without forking
  the doctrine. Projected to the canonical `.agents/skills/` home plus `.claude/skills/`;
  read natively by Codex and Kimi Code, so no per-harness derivation and no registry entry.
- **`## 8. Disciplina de Testes` in the scaffold constitution** and the new public template
  `templates/tests-AGENTS.md`, so the doctrine reaches a scaffolded workspace at law level
  and as a scoped rule file. The template is parameterized (`<ANGLE-BRACKET>` placeholders
  for the tier timeouts, the LARGE cap and the wall-clock baseline) and carries zero
  workspace-specific literals. No existing constitution section was renumbered.
- **Consumer repos receive `tests/AGENTS.md` at `alive()`** — copied only when `<repo>/tests/`
  is a real directory (a symlinked `tests/` is refused) and no `tests/AGENTS.md` exists. The
  copy never creates the directory and never overwrites an operator file.
- **Per-test timeouts by tier** via the new dev dependency `pytest-timeout`: unit 10 s,
  contract 30 s, integration 60 s, e2e 120 s, applied at collection and never overriding an
  explicit `@pytest.mark.timeout`. A test that needs more time is mis-tiered — the tier is
  what gets fixed.
- **Two markers, `flaky` and `quarantine`**, moved across all six marker surfaces in one
  change. A `quarantine` mark without `bug="<bug-slug>"` **refuses collection**, with the
  actionable message printed to stderr before the raise so it survives an xdist worker
  crash; a contract test pins `pyproject.toml`'s marker set against `conftest.py`'s so the
  surfaces cannot drift apart silently.
- **The panel E2E retry became loud.** A Playwright JSON reporter writes outside the repo
  tree and a CI step fails the job on any `passed`-after-retry result unless the test is
  registered as quarantined, naming the offending spec. The step is fail-closed: a missing,
  empty, malformed or non-numeric report exits 1. Demonstrated once on the branch with a
  deliberately flaky throwaway spec, removed in the same task.

### Changed
- **`DADAIA.md` §6 states the test lifecycle once**: intent and size declared at birth (an
  undeclared test is SCAFFOLD and expires); demotion is a step of release closure; the
  implementer never prunes to go green — pruning is a `qa-engineer` verdict with `file:line`
  evidence, executed by `software-engineer`; tombstone tests and expired SCAFFOLD are slop;
  test-artifact capture is failure-gated. Plus two sentences elsewhere: the never-delete law
  is **scoped to bugs and backlog only** (tests are prunable under the criteria), and a
  quarantine carve-out inside *Push green* — a green run with quarantined tests is green, an
  **unregistered pass-on-retry is a failure**. The law names no number and no marker; those
  live in the skill and in the repo. Always-on cost +221 tokens against a +400 cap.
- **One coverage stance, four sites.** The 80 % floor on `unit or contract` is a CI gate and
  a by-product metric — never an acceptance target, never a reason to write a test, never a
  score anchor. `drift-detection`'s Dimension E is rewritten off line-coverage anchors onto
  detection quality (intent declared, demotion performed, flake within ceiling, quarantine
  within cap and unexpired, LARGE owned). The gate itself is byte-unchanged.
- **Every gating selector excludes the quarantine lane** — six in `ci.yml`, four in
  `release.yml`, and the pre-push preflight's base arguments — so a quarantined test runs
  only under an explicit `-m quarantine` diagnosis invocation. `--durations=25` on the unit
  and unit+contract coverage jobs, and every pytest job carries a `timeout-minutes` ceiling
  ratcheted against the frozen baselines, so a budget change is a reviewable diff.
- **`qa-engineer` is verdict-only on curation** and its `write_allowlist` narrows from
  `tests/**` to `tests/e2e/**` plus the `alpha-N` review file, reports and handoffs, ending
  a standing contradiction between its frontmatter and its body. `software-engineer`
  **executes** curation verdicts, quoting the evidence in the commit message.
  `dadaia-release-closure` gained the demotion + disposition block, so demotion-at-closure
  finally has somewhere to land; `tests/README.md` collapsed to `## Commands` plus one
  pointer, ending its duplication of `tests/AGENTS.md`.

### Removed
- The dead `--ignore=tests/performance` in the CI preflight and the unit assertion pinning
  it — the directory no longer exists.

### Fixed
- Memory told the truth again: the stale "~2,100 collected tests" is now the measured
  2,123 collected / 55 LARGE, and `pytest-xdist` / `pytest-randomly` are documented in the
  tech stack, having been in use through `-n auto` without ever being listed.

## [Unreleased] — spec release v0.6.0

Gitflow standardization. Lands in the same unreleased `0.5.0` package version as the spec
releases below — this release changes no dependency, no Python version and no packaging
contract.

### Added
- **`dadaia-gitflow`, the single operational home of the git contract.** A new universal
  skill (89 lines) carrying the four-branch table, a seven-row stage table mapping every
  lifecycle stage to its branch, commit cadence, merge target and push trigger, the two
  merge milestones with their mandatory post-merge sequence, the hotfix PATCH-mint rule, and
  an explicit split between what is mechanically enforced and what is discipline. Projected
  to the canonical `.agents/skills/` home plus `.claude/skills/`; read natively by Codex and
  Kimi Code, so no per-harness derivation and no registry entry.
- **`pr-source-guard`**, a required check on `main`: any pull request targeting `main` whose
  head is not exactly `develop` fails and is mechanically unmergeable. The fork-controlled
  head ref is bound through `env:` and compared as a quoted literal, never interpolated into
  a shell string.

### Changed
- **`DADAIA.md` §5/§6 state one git contract.** Four branch patterns and no fifth — `main`,
  `develop`, `feature/{M.m.p}`, `hotfix/{M.m.p}` with PATCH ≥ 1; `develop` is the only
  pushable branch, feature and hotfix branches are local-only, and `main` advances only via
  a PR from `develop`. Stage placement, the two-milestone merge cadence
  (definition-trio `Aprovado` and ship, each followed by a diff-based security review of
  `origin/develop..develop` and a push of `develop`) and the finalization order
  memory → CLOSURE → archive are stated once at law level; every other skill and agent
  references the skill instead of restating it. Always-on cost +389 tokens against a +400
  cap.
- **BREAKING — the pre-push chokepoint enforces branch policy.** Any pushed ref other than
  `refs/heads/develop` is refused, branch names are validated against the four patterns, a
  refspec aiming local `develop` at another remote ref is refused, a local ref that is not a
  branch head gets its own diagnosis, and an unparseable stdin line now fails **closed**
  (the one traceable bypass, `git push --no-verify`, is named in the message). Tag pushes and
  branch deletions keep their carve-out, so publishing is unaffected. *Consumer workspaces
  with no `develop` branch, or with `release/*`-style branch names, will get hard push
  refusals after upgrading; bootstrap a `develop` branch first.*
- **The push-gate security verdict is keyed to the develop delta** — an APPROVED
  `security-reviewer` handoff covering `origin/develop..develop` — instead of a bare per-ref
  sha match. `security-reviewer` admits exactly one push-gate scan target, the diff; a
  full-tree scan survives only in the audit lane.
- CI push triggers are `main` and `develop` only. The `feature/**` and `hotfix/v*` triggers
  and the push-triggered `hotfix-branch-name` job are retired — those branches are
  local-only, and the PATCH ≥ 1 pattern now lives in the chokepoint validator, at the
  boundary that actually exists.

### Removed
- **The hotfix *release* ceremony is revoked.** A bug fix is Arm B in full, run on
  `hotfix/{M.m.p}`; at merge into `develop` the same commit bumps `pyproject.toml` and adds
  the `CHANGELOG.md` entry. No hotfix SPEC, PLAN, TASKS or CLOSURE, and no
  `specs/releases/<id>/` directory. The record is the bug ledger's `resolved` event plus
  that CHANGELOG entry. `product-engineer` states the revocation explicitly so the ceremony
  is not restored as a perceived regression; removal of the now-dead verb and templates is
  queued in the backlog.
- The operational restatements of the branch model across four skills and seven agents —
  relocated to `dadaia-gitflow`, proven by a relocation grep run independently by the author
  and by QA.

### Fixed
- The four dangling `release-governance` citations (two skills, two package modules) now
  cite `DADAIA.md` §5 or `dadaia-gitflow`.
- The scaffold constitution gained `## 11. Checkpoints de Revisão` and
  `## 13. Propriedade da Memória`, so every `constitution §N` citation across the shipped
  agents resolves.
- `scaffold/releases/README.md` states the canon release-directory regex
  `^v\d+\.\d+\.\d+$` — the previous expression rejected `v0.6.0` itself — and its `ACTIVE.md`
  block matches the v2 schema including the optional `segment:` line.
- `ai-engineer` inventories the real `public/scripts/` contents (5 files, 3 shell) instead
  of claiming `pre-push-ci-gate.sh` is the only asset there.

## [Unreleased] — spec release v0.5.0

Lands in the same unreleased `0.5.0` package version as spec release v0.3.0 below.

### Removed
- **The four competing context-resolution ladders and the bind-epoch marker
  subsystem.** `core.specs_resolver.resolve_context()` is now the single authority
  implementing the `DADAIA.md` §3 rung law verbatim (rung 0 caller input / explicit write
  target, rung 1 `DADAIA_CONTEXT`, rung 2 this session's own live record keyed by the
  harness-native session id, rung 3 the repo containing the cwd). The CLI seam, the SDD
  gate, `container` and the ctx-inject hook all consume it. Deleted with the ladders: all
  three marker-attribution algorithms, the `session_identity` marker writers/readers,
  `sdd_post_gate._adopt_attributed_bind`, `.dadaia/states/bind_epoch/`, and
  `cli._specs_resolution.current_ancestry_pids` — 132 occurrences across 18 files → 0.
  `core/specs_resolver.py` went 369 → 202 lines; the production package is net −194 lines
  across the release.
- The `DADAIA_SESSION_ID` **resolution** channel (it survives only as a session identity
  for the CLI/hook heartbeat), the dead `DADAIA_AGENT_RUNTIME` alias (zero writers), the
  hardcoded self-hosting-slug rung, the env pop/restore workaround, and the `cwd/specs`
  fallback in `resolve_specs_dir`. Resolution now reads one environment variable:
  `DADAIA_CONTEXT`.

### Changed
- **Context-memory injection triggers on the session record's `bound_at`** instead of a
  marker mtime. One intended behavior difference: a **same-context re-bind now
  re-injects**, so a mode or release change reaches a live session.
- **Kimi Code binds through `DADAIA_CONTEXT` exported at harness launch** (rung 1) — the
  harness exposes no session-id environment variable. `dadaia context bind` now prints a
  loud warning when it can neither key a harness-native record nor see `DADAIA_CONTEXT`,
  so a binding can never become a silent no-op.
- `DADAIA.md` §3 amended for precision and re-projected; the skills and
  `CONSUMER_VALIDATION_RECIPE.md` teach the three rungs, the plain-shell path and the kimi
  launch-env profile.
- The import-linter contract `bind-resolution-seam-is-a-single-home` rewritten for the new
  seam: exactly three sanctioned direct importers (`cli._specs_resolution`, `container`,
  `hooks`), still zero `ignore_imports`. Hooks import the authority directly by law — no
  hook imports `container`, pinned by a new attesting import-surface test (hook write-path
  latency 2.25 s → 0.46 s).

### Fixed
- **`dadaia specs doctor` is satisfiable again.** A bug-ledger coherence violation is now
  reported only while no later compensating `reported` event exists for the same `bug_id` —
  the append-only store's own vocabulary heals its history, while per-event enforcement is
  unchanged and a fresh uncompensated violation still ERRORs. Two legal appends healed the
  one historical row; the doctor exits 0 on the self-hosting context for the first time.
- Install-ledger relpaths are validated in `LedgerEntry.__post_init__` — empty, absolute,
  `..`-bearing, backslashed and non-normalized POSIX forms are rejected at the one
  construction authority, covering both the prune loop and the foreign-projection scan
  (CWE-22 class).
- `DoctorLine.render()` escapes control characters, so no producer can forge a second
  physical doctor line (CWE-117).
- The `entities-derivation` verifier emits a typed `ENT-DERIVE-1` error line for
  malformed-but-valid JSON shapes instead of letting `AttributeError`/`TypeError` escape.
- The kimi telemetry reader contains `sessionDir` lexically against the index parent before
  `stat`, degrading through its existing `OSError` branch; ships with the reader's first
  test file.
- A new `remove_legacy_bind_epoch_state` install migration sweeps orphan
  `.dadaia/states/bind_epoch/` markers left by earlier releases (retained one release).

## [0.5.0] — Unreleased (spec release v0.3.0)

### Removed
- **Removed the dadaia-workflows engine entirely.** The four `dadaia lifecycle`
  Python workflows (backlog-definition, release-definition, implementation-reviews,
  audit), the Layer-2 worker runtimes (codex/pi/claude-sdk/fake adapters,
  headless adapter base), workflow model policy + profiles, lifecycle fragments and
  personas assets, the lifecycle run store, workflow handoff models/doctors, the
  panel Workflows and Model-policy tabs, the `dadaia reports workflow-*` verbs, the
  certification `workflow-*` checks, `features/ai_surface`, and every related test
  (~52k LOC total). The SDD flow (Arm A) is now agent-dispatched and
  document-governed — SPEC/PLAN/TASKS + ACTIVE.md + the deterministic gate and git
  chokepoints are unchanged. Rationale: the bug-ledger audit measured 200/416 bugs
  (48%) in this subsystem with a 96% additive-fix ratio and 0.48-day median
  family recurrence; deleted surface goes quiet, patched surface does not.
- `dadaia-capabilities-v1` schema replaced by **`dadaia-capabilities-v2`** (breaking):
  the required `workflows` key and the certification `deterministic_fake_workflows` /
  `live_harness_canaries_required_for_release` constants are gone.

### Changed
- **`public_assets` install de-flagged**: `install()` now resolves its arguments once
  into an immutable `InstallPlan` and runs an ordered, flag-free step pipeline
  (`OverwritePolicy` replaces `force: bool` internally; `scope`/`only` select steps).
  Public port signatures and install output are byte-identical.

## [0.1.24] — Unreleased

*Unpublished-internal (T-043-48/FR31, SPEC A31.3): no `0.1.24` was ever published to
PyPI — verified against `https://pypi.org/pypi/dadaia-workspace/json` (13 published
versions, `0.1.0` through `0.4.1`). Kept exactly as written; heading neither removed
nor renamed.*

### Removed
- **Removed OpenCode support entirely (both agentic layers).** The OpenCode entry
  harness, the `OPENCODE_RUN` Layer-2 worker kind and its adapter, the `.opencode/`
  projection target, `opencode.json`, the OpenCode gate plugin, and all OpenCode
  references across code, tests, docs, and the AI surface are gone. The supported
  harness set is now exactly **Claude Code, Codex, and PI**.

## [0.1.7] — 2026-06-13

*Unpublished-internal (T-043-48/FR31, SPEC A31.3): no `0.1.7` was ever published to
PyPI — verified against `https://pypi.org/pypi/dadaia-workspace/json` (13 published
versions, `0.1.0` through `0.4.1`; the real published lineage runs `0.1.6` directly to
`0.2.0`). A `v0.1.7` git tag exists (`fb03d1ad`, 2026-06-13) but no corresponding
PyPI upload was ever made. The prose below's "the single published version after
`0.1.5`" claim is therefore superseded by this annotation, not corrected in place —
kept exactly as written; heading neither removed nor renamed.*

Consolidated release: the single published version after `0.1.5`. It folds in all
work from the never-tagged `0.1.6`–`0.1.10` development line — cross-platform
support, the process-execution layering law, spec/memory fidelity, the full
workspace-audit remediation, and panel/scaffolder/git security hardening — shipped
under one version through the release-candidate gate rather than as a string of
per-fix releases.

### Added
- **Cross-platform support (Linux / macOS / Windows).** `core/platform.py`
  platform-detection seam (sole `sys.platform` call site) + a port/adapter boundary
  for OS-sensitive domains: file locks (fcntl / msvcrt), telemetry refresh lock, file
  permissions (chmod / `icacls`), process probe, and signals/shutdown. New
  `dadaia_workspace/hooks/` Python governance package replaces the bash hooks so SDD
  governance is enforced on stock Windows (no Git Bash required). 3-tier resilience
  contract (fail-loud security / degrade-with-log / unsupported-at-construction).
  `import-linter` contracts enforce the layering law in CI.
- Phased 3-OS CI matrix: an importability-smoke job (Windows + macOS) plus
  Windows/macOS unit and contract legs (Ubuntu remains the hard gate).

### Changed
- **Model strategy unified on the registry single source** (`core/model_registry`):
  `MODEL_MAP` / `PRICING_TABLE` are derived views; public doctor validates agent
  `model:` frontmatter + key-set sync. Deep-tier personas (product-engineer,
  qa-engineer, ai-engineer, software-architect, project-auditor) and the
  dispatch-tier personas (software-engineer, security-reviewer, code-reviewer) all
  run `claude-opus-4-8`.
- Process-execution layering law completed: `features/` modules no longer import
  `subprocess` directly. New `ProcessRunner` Protocol
  (`core/protocols/process_runner.py`) with production adapter
  (`infrastructure/subprocess_runner.py`), consumed via DI by `import_`,
  `ci_preflight`, `specs/doctor`, and `server_registry`; `import-linter` contract
  `features-no-subprocess` enforces it. `container.py` platform branching reads the
  `PLATFORM` capability singleton.
- Bash hook quartet retired; Python hooks are the sole gate surface (PreToolUse
  scoped to write tools; Bash-tool writes documented out of the determinism envelope
  with doctor backstops).
- AI surface (AGENTS.md, rules, skills, personas) rewritten to describe real
  enforcement vs discipline (14 contradictions fixed); memory + constitution §8
  rewritten to the merged kernel. Agent persona parity pass: `[SCOPE ERROR]` redirect
  block in all 9 core personas; report-emission prose deduplicated to
  `workspace-protocol §4`; vestigial `opencode_model` frontmatter keys removed.
- `Operating System :: OS Independent` classifier corrected to
  `Operating System :: POSIX :: Linux` until the 3-OS CI matrix graduates to a hard
  gate.
- All text I/O specifies `encoding="utf-8"` (Windows cp1252 corruption fix); JSON
  stores route through a single `_atomic_write_text` chokepoint using `os.replace`.
  venv executable paths resolved via the platform seam (`Scripts/python.exe` on
  Windows).
- Test architecture: harness-env fixture contract (hook behavior tests run as real
  subprocesses; `DADAIA_*` setenv + hook-import ratchets at zero baseline), two-actor
  concurrency e2e asserting on lock-file history, drift-ratifying tests killed,
  consistency-contract + lifecycle-asymmetry policies.

### Fixed
- SDD gate classifier re-rooted context-relatively: ADDITIVE/MEMORY/FROZEN classes
  now live inside `repos/<slug>/` (unmatched in-repo ⇒ MUTATING, never UNGATED);
  symlinks canonicalized before classification. Kills the
  lease-theft-by-additive-write CRITICAL.
- Lease liveness = TTL + PID veto: holder records a long-lived harness pid
  (payload/getppid); TTL-stale + alive ⇒ yield (no takeover), dead ⇒ takeover; renew
  runs inside the same O_EXCL CAS (race fixed); heartbeat renews on every PostToolUse
  from the harness-native session id (Claude `*` matcher, Codex match-all).
- Session identity consolidated into a single owner module (`session_identity`); bind
  `--mode` optional (default read), persisted in the session record + context
  incumbent pointer; gate mode resolution env → record → live-incumbent →
  IMPLEMENTATION; READ binds are non-acquiring.
- `dadaia ci preflight` no longer self-pollutes (ruff `--no-cache`, mypy cache
  redirected, pollution guard = session snapshot diff) — the pre-push gate passes
  end-to-end; pre-push hook probes the workspace venv (`$DADAIA_BIN` → walk-up →
  poetry → repo venv, fail-closed).
- specs doctor ledger invariants (SPEC-DOC-024..029): phase↔markers,
  CLOSURE-before-archive, unique release ids, naming canon, constitution ref
  resolution, lease↔session coherence.
- Spec/memory fidelity: all 34 confirmed findings of the drift audit resolved —
  memory atoms document the real doctor check codes, the Python-hook SDD gate, the
  hard-gated 3-OS CI matrix, the full CLI/protocol inventory, and a roster without the
  phantom `researcher` agent.
- The CLI is now importable on Windows: the unconditional top-level `import fcntl` in
  the locking and telemetry modules (which crashed every `dadaia` invocation at
  import) is removed and delegated to platform adapters.
- Windows security no-ops closed: the panel auth token is owner-only via `icacls` or
  the panel refuses to start (CWE-732); `/proc` scans and `os.getuid` degrade safely
  off-Linux.

### Security
- Panel HTTP handler: enforce Bearer auth on workspace-sensitive routes that were
  previously served by the unauthenticated dispatch loop — `/reports/<path>`,
  `/api/panel-status`, `/api/contexts`, `/memory/<slug>/<path>`,
  `/memory-view/<slug>/<path>` — whenever the panel is NOT loopback-bound (defense in
  depth; loopback keeps the zero-friction local default). (F-01/F-02/F-04)
- Scaffolder renders templates with a Jinja2 `SandboxedEnvironment`, blocking template
  access to Python internals. (F-03)
- `GitSubprocessClient.clone` refuses unsafe URLs (`ext::` transport and
  option-injection via a leading `-`) before invoking git. (F-05)
- Panel loopback auth bypass removed (tokenless sensitive API ⇒ 401 even on
  127.0.0.1; tokenized-URL handoff, token file modes re-tightened to 0o600).
- `context dead` refuses untracked files without `--commit`; `--commit` runs a
  structural secret scan (incl. cert/key file suffixes) before any push.
- public-privacy gate fails closed: packaged baseline structural denylist scans even
  without an operator denylist.

## [0.1.4] — 2026-06-03

### Added
- Executable pytest taxonomy (`unit`/`contract`/`integration`/`e2e`/`slow`/`tmp` markers), a `tests/contract/**` public-contract layer, and a `tests/tmp/**` quarantine excluded from default collection (`test-suite-architecture`).

### Changed
- Coverage instrumentation removed from default pytest `addopts` (fast local default); coverage now enforced only by an explicit CI job. CI split into per-layer jobs (lint, typecheck, unit-fast, contract-coverage, integration, e2e-python, e2e-panel).

### Security
- Removed the last hardcoded private identifiers from shipped source: the public-privacy denylist no longer embeds operator-specific values. Terms are now loaded at runtime from outside the published package (`$DADAIA_PRIVACY_DENYLIST` or `<repo_root>/.dadaia/states/privacy_denylist.json`); the library ships with an empty default (dev-guardrail rule #4).
- Purged residual private identifiers from the full git history and genericized changelog entries that previously enumerated them.

## [0.1.3] — 2026-06-03

*Unpublished-internal (T-043-48/FR31, SPEC A31.3): no `0.1.3` was ever published to
PyPI — verified against `https://pypi.org/pypi/dadaia-workspace/json` (13 published
versions, `0.1.0` through `0.4.1`). Kept exactly as written; heading neither removed
nor renamed.*

### Security
- Removed two private academy modules (12 files) from the published wheel — they contained private-infrastructure operational docs.
- Purged private project identifiers (admin IP, hostname, and internal project/infrastructure slugs) from library source, tests, and fixtures; replaced with generic placeholders throughout.
- Removed hardcoded personal absolute paths (`/home/<user>/…`) from tests and fixtures.
- Re-seeded `sessions_seeded.sqlite` telemetry fixture to strip private session data.
- Genericized a private example in `core/workspace_resolver.py` docstring (shipped source).
- Neutralized canonical assets for open-source consumers: `public/data/AGENTS.md` language default changed to language-neutral; removed leaked operator-infra examples from the `dadaia-grill-me` skill.
- Trimmed bloated canonical rules to concise imperative form: `dadaia-workspace-dev-guardrail` 134→63 lines, `tmp-file-guardrail` 79→47 lines, `plugin-scope` 35→17 lines (removed dangling `ADR-X7` reference).
- Verified: built wheel + sdist contain zero private-identifier leaks; full test suite green (2404 passed, 88.69% coverage).

### Added
- Markdown-memory source (`memory-markdown-source-v1`): product memory is now `.md` atoms with YAML frontmatter; panel renders via `mistune`; deleted renderer/schemas/HTML templates from the old YAML/HTML memory approach.
- Panel Kanban tab: task-state board (`[ ]`/`[-]`/`[x]`) with `/api/kanban` endpoint; handoff verdict gate enforced at panel level (`panel-kanban-v1`).
- Spec-context tree-v2: `ALIVE`/`DEAD` context states, new verbs (`bind`/`unbind`), per-release session locks with `acquire`/`release` semantics (`spec-context-tree-v2`).
- Per-release TOCTOU-hardened session locks: `Impl-XOR-Review` lock enforcement with stale-lock detection and temp-race fixes (`r2-lock-toctou-hardening-v1`).
- `ctx-inject v2`: `context use` → `bind` rename; `primary_context.json` retired from hook; `ctx-inject.sh` updated to v2 context resolution.
- `dadaia public stage` sanitization: defaults for new workspaces scrubbed of private agentic config.

### Changed
- `specs/` carved out of the public repository: marked untracked + added to `.gitignore`; private infra paths and project slugs that had leaked via the specs tree are now excluded from the wheel and sdist.
- `public/data/AGENTS.md` language default is now language-neutral (was "Portuguese (BR) by default").
- GitHub Actions SHA pins corrected: malformed `actions/download-artifact` SHA in `release.yml` fixed; all action pins refreshed.

### Fixed
- `release.yml`: corrected malformed `actions/download-artifact` SHA pin that broke the trusted-publishing release job.

### Removed
- Two private academy modules removed from the `dadaia_workspace/` package tree (private infra docs; 12 files).

## [0.1.1] — 2026-05-23

### Added
- 21-agent universal topology: ai-engineer, software-engineer-python, software-engineer-node, data-engineer, data-analyst, data-architect (6 new personas since 0.1.0); all agents carry TOML projections for Codex.
- Codex orchestration parity: `_install_codex_agents()` generates `.codex/agents/*.toml` per agent with model mapping (Claude→Codex identifiers); `_install_codex_rules()` projects only frontmatter-bearing rules; `CodexAgentDispatcher` with parallel best-effort dispatch; doctor checks D-CX-1..5 for Codex drift.
- Handoff schema v1.1: `scope`, `metrics`, `findings[].detail_md`, `findings[].fix_recommendation` fields; CLI hard-error on missing `findings[]`; `dadaia reports lint` subcommand for orphan/oversized/missing-fields detection.
- Bug reporting infrastructure: `bug_reporter.py`, `.dadaia/bugs/reported.json` persistent store, CLI exception handler via `_safe_app()`, doctor persistence via `report_doctor_finding()`, open-bug surface during `dadaia specs` release creation.
- Doctor `[warn] git-dirty` check: detects uncommitted edits in `public/` working tree (blind spot for the doctor diff).
- Workspace panel r5: 7-tab canonical order (Projects, Agents, Workflows, Sessions, Reports, Academy, Settings), Projects tab redesign, Reports tab, Academy tab (infrastructure), logo redesign, dark-mode token coverage.
- DEV workspace self-reference section in `dadaia-workspace-dev-guardrail.md` (4 invariants for the editable-install loop).
- Spec-refinement workflow v0.3.0: `research_evidence` stage (researcher) added before `discovery`; `spec_write` stage post-synthesis.
- `dadaia public doctor`: `[not-applicable]` status for logical type mismatches (e.g. workflows in Codex runtime); codex rules filter (behavioral prose rules excluded).
- Runtime codex adapter skills (`runtime/codex/design-ctx/SKILL.md`, `runtime/codex/frontend-ctx/SKILL.md`) for plugin-scoped Codex surface.
- Shared skills: `frontend-design`, `frontend-implementation-quality`, `design-report-quality-gate`, `design-reference-research`, `ux-ui-review`.

### Fixed
- CLAUDE.md is now a 1-line stub delegating to AGENTS.md (T-41); no longer a source copy — reduces noise in consumer repos.
- 19 pre-existing test failures resolved: schema v1.1 fixture gaps, stale model identifiers in test fixtures (`claude-sonnet-4-5`→`claude-sonnet-4-6`), T-41 CLAUDE.md stub invariant, stale EXPECTED_SKILLS set, `commands/` staging dir removal, behavioral-prose rule excluded from `.codex/rules/` projection, workflow v0.3.0 stage ordering in e2e test.
- 4 `dadaia context deactivate` bugs: git subprocess upstream tracking, service layer error handling.
- Init legacy resolver replaced with `resolve_workspace_root_for_init`; no longer errors on un-initialized workspaces.
- CSP `script-src` unsafe-inline replaced with SHA-256 hash in panel server.
- SQLite dead tables dropped via migration 6; telemetry service hardened.
- Exit code 3 on uninitialized workspace for `dadaia reports validate` (workspace resolver moved inside try).

### Changed
- All agents default to `claude-sonnet-4-6` (ADR-X4); ai-engineer moved from Opus to Sonnet; researcher uses `claude-haiku-4-5-20251001`.
- `AGENTS.md` is the canonical guardrail file; CLAUDE.md is a 1-line pointer (Option C / T-41).
- Skills split: 16 universal skills after removing game-*, devops-gitflow-governance, devops-deploy-strategies, architect-*, github-actions-pipelines, security-audit-protocol.

## [0.1.0] — 2026-05-14

### Added
- `dadaia` CLI: `init`, `context {create, list, show, activate, deactivate, promote, delete, use}`, `repos`, `public {stage, install, doctor}`, `doctor`, `academy`, `export`, `import`, `orchestrate {list, show, run, status, resume}`.
- Spec Context Project model (v4.0): multi-active contexts, single `is_primary` flag, JSON-backed state.
- Universal agentic assets: 6 agents (`product-engineer`, `software-architect`, `software-engineer`, `qa-engineer`, `devops-engineer`, `game-developer`), 17 skills, 4 commands, 2 rules.
- Cross-tool parity for Claude Code, OpenCode, Codex, and `.agents/`.
- Workspace portability: `dadaia export` / `dadaia import` with branch tracking.
- Multi-Agent Orchestration v0.1 — `workflows/` first-class asset type, durable run state (`manifest.json` + `events.jsonl`), 4 dispatchers (Claude/CLI/OpenCode/Codex), 2 seed workflows (`spec-refinement`, `tdd-cycle`).
- `input_contract` block in every agent frontmatter (Handoff Schema v1).
- `[partial]`/`[unsupported]` doctor status classification per runtime.
- CI workflow (`.github/workflows/ci.yml`) with lint, typecheck, test, pr-title jobs.
- Release workflow (`.github/workflows/release.yml`) with OIDC trusted publishing to PyPI.
- SDD Gate v2 (`sdd-spec-gate.sh`): gates edits to `repos/<primary_slug>/` (active Spec Context), requires `[-]` IN PROGRESS task marker in TASKS.md, meta-edit bypass for spec files (TASKS.md, PLAN.md, SPEC.md), fail-open on any internal error.
- Task State Contract (RF-CONV-006): 3-marker convention `[ ]`/`[-]`/`[x]` with `dadaia-task-manager` skill propagated to all 6 agents.
- Coverage gate: `--cov-fail-under=80`; current coverage 82%+ across unit + integration tests.

### Fixed
- BUG-002: `ctx-inject.sh` and `sdd-spec-gate.sh` now resolve `WORKSPACE_ROOT` via their own script path; no longer depend on git rev-parse or `$HOME`.
- BUG-003: `dadaia import` now rewrites absolute workspace paths in `.claude/settings.json`, `.codex/hooks.json`, and `.opencode/opencode.json` after extraction (`patch_json_paths` phase).
