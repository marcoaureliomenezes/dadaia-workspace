# Closure: Release — v0.1.62 — Injection Contract & Fan-out Containment

> **Status:** Aprovado
> **Release ID:** v0.1.62
> **Owner:** product-engineer
> **Closed:** 2026-07-07
> **Branch:** `feature/v0.1.62` · **Base:** post-v0.1.61 `main` (`3965df4c` lineage) · **Merged:** `352969da` (PR #118, squash of `feature/v0.1.62`, 2026-07-07) · **Closure branch:** `chore/v0.1.62-closure`
> **Ship gates:** qa-engineer **APPROVED** (handoff `2026-07-07T175126Z`, 3 INFO findings — incl. the "8 kept vs 9 kept" SPEC-drift note, see Drifts) · security-reviewer **APPROVED** (push-gate keyed to the pushed ref sha `066471e0`) — **emitted as a REAL handoff-v1.2 with `self_pull.refs`, the feature validating itself**; the QA reviewer's own first draft handoff was **REJECTED by the new FR2 coverage check** (live end-to-end proof of the shipped validator) · CI **all checks green at merge** (one pull_request-event flake on `workflow-policy-harness-toggle`; same-sha push-event run + rerun green — LOW bug filed, see Drifts).
> **Mandate:** Second of the fixed four-release queue v0.1.61 → v0.1.62 → v0.1.63 → v0.1.64 (Rulings 61-A/61-B, 62-A/62-B). Consumes HIGH bug `reports-sidecar-version-detection-misroutes-future-tokens` (Ruling 62-E).

## Summary

v0.1.62 makes **Layer-1 self-pull mechanically verifiable**: the handoff contract bumps to
**`handoff-v1.2`** with a `self_pull.refs` audit line recording the memory atoms a session
actually read, enforced version-conditionally by `dadaia reports validate` (service-layer
conditional + ref existence + role→atom-map coverage via the new pure `core/role_atom_map.py`
leaf), with the historical v1/v1.1 corpus valid forever (transition posture, corpus-locked
golden-first). Both Layer-2 code emitters emit v1.2 from the run's recorded `InjectedContext`
refs (role-map fallback → honest v1.1 on zero refs), both accept-sets widened, and all **16
emission-instruction surfaces** (12 agent bodies + the emitter skill's two examples +
handoff-AGENTS + the output-handoff fragment) adopted the instruction under a file-enumerated
16/16 contract test. The release also **fixed the picked HIGH bug**: a v1.2 token no longer
misroutes into the v1.0-compat path's spurious `findings[]` hard error.

Two hardening fronts shipped alongside: the **consumer fan-out is contained** — hostile
`repo_slug` values are lexically rejected at derivation (POSIX + Windows forms, non-silent
`[reject]` line, fail-open) with a write-time containment assert, and destination-file
**symlinks are refused** (never written through, including dangling; doctor classifies them
`[foreign]` and exits 0) while symlinked consumer DIRs (the CI `ln -sfn` pattern) stay
legitimate; and the **panel response-guard e2e now requires the memory chip** — both
null-guards replaced by required-presence assertions (graceful-empty branch removed), proven
by the AC-9 sabotage replay that pre-fix passed "2 passed" and post-fix fails both the unit
DOM lock and the browser journey.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-62-01 | W0 definition — SPEC/PLAN/TASKS from the 2026-07-07 code read + mandatory grill (operator unavailable → ADR-1..9); dual-review REJECT folded (QA62-1..5 + ARCHX/QAX); PM Rulings 62-A/62-B/62-E; HIGH bug consumed with AC-4 = its repro verbatim | `977593cf` (queue definition) · phase flip `52606197` |
| T-62-10 | W1 AC-1 back-compat corpus lock FIRST (5 fixtures, real validator + real schema, 6 tests green pre-bump) + QAX-4 branch-point collect pin 4701 | `aa5e8600` |
| T-62-11 | W1 FR1/FR2 — schema bump to v1.2 (`self_pull` optional, whitelisted keywords only) + `core/role_atom_map.py` relocation w/ same-object re-export + service-layer conditional (presence/existence/coverage) + `_detect_sidecar_version` fix (**resolves the picked HIGH bug**); AC-2/3/4 RED-first + AC-10(a)(b)(c)(d) sabotages | `5f169f0d` |
| T-62-20 | W2 FR3 — accept-sets `{v1, v1.1, v1.2}` in `gates.py` + `runtime_files.py`; both L2 emitters v1.2 via `resolve_emitted_handoff_version` (InjectedContext dedup → role-map fallback → honest v1.1); tree-wide `rg 'handoff-v1'` sweep fate-ledgered; AC-5 round-trip | `bce7e1af` |
| T-62-30 | W3 FR4 — 16-surface instruction adoption (12 agent bodies, emitter skill table + both examples, handoff-AGENTS, output-handoff fragment); AC-6 negative grep (8 fate-ledgered survivors) + positive 16/16 contract test (19/19); 6 gate goldens re-baselined as deliberate recorded amendments (machine-verified EXACT-INSERTION-ONLY) | `89620050` |
| T-62-40 | W4 FR5/FR6 — lexical slug containment + write-time assert + symlink write-through refusal + symlink-aware doctor; AC-7/AC-8 RED-first + AC-10(e)(f) sabotages; v0.1.60 provenance suites byte-identical (204 passed) | `3be0e698` |
| T-62-50 | W5a FR7 — both response-guard null-guards → `waitForSelector('.memory-chip')` required presence; AC-9 sabotage replay captured (unit lock AND e2e now fail; pre-fix e2e "2 passed") | `70e1310c` |
| T-62-60 | W5 gates + ship — AC-11 full gate set green; self-hosting reconcile (stage → install --target all → doctor, `[ok] public-privacy`); QA ship-gate + security push-gate; push; CI watched green; PR #118; merge `352969da` | `066471e0` |
| T-62-70 | W6 — this CLOSURE.md + memory rebase (5 atoms) + disposition sweep + backlog flips + archive handoff to PM | (this closure) |

## Validations

Each row is a triple: description, command, evidence (SHA / stdout snippet / handoff path).
Gate evidence captured at the ship tree (`066471e0`) and merged as PR #118 (`352969da`).

| Description | Command | Evidence |
|-------------|---------|----------|
| AC-11 full suite green | unpiped `pytest` (real exit) | `4755 passed, 17 skipped, exit 0` — `066471e0` (branch-point pin 4701 collected at `52606197`, T-62-10; growth = the release's new tests) |
| AC-11 format + lint clean | `ruff format --check` · `ruff check --no-cache` | both exit 0 — `066471e0` |
| AC-11 types clean | `mypy --strict dadaia_workspace` | exit 0 — `066471e0` |
| AC-11 import contracts | `lint-imports --no-cache` | **9 kept / 0 broken**, ignore-cap UNCHANGED (`core/role_atom_map.py` stdlib-only core leaf; `features→core` legal) — the SPEC's "8 kept" predates v0.1.61's 9th contract, see Drifts — `066471e0` |
| AC-11 SDD + backlog doctors | `dadaia specs doctor` · `dadaia backlog doctor` | both exit 0 — `066471e0` |
| AC-1 back-compat corpus lock (golden-first) | `pytest tests/unit/features/reports/test_handoff_v12_validation.py` (corpus section) | 6 tests green on the pre-bump tree (`aa5e8600`) AND green post-FR1/FR2 (`5f169f0d`) — transition posture proven, not asserted |
| AC-2 v1.2 conditional (RED-first, staged) | `test_schema_version_matrix` (ONE named parametrized 4-case test) | pre-FR1: enum-only reject; post-FR1 pre-FR2: schema-blind pass; post-FR2: `self_pull`-pathed error; v1 ✓ / v1.1 ✓ / v1.2+self_pull ✓ / v1.2−self_pull ✗ — `5f169f0d` |
| AC-3 existence + coverage + pattern | targeted tests in `test_handoff_v12_validation.py` | indexed `self_pull.refs[1] ref does not exist`; qa-engineer coverage miss fails / software-engineer unmapped passes; `..`/absolute refs rejected by schema pattern; fail-soft on root None — `5f169f0d` |
| AC-4 detection fix (RED = the picked bug's repro VERBATIM) | `dadaia reports validate <v1.2 sidecar>` | pre-fix exit 1 `ERROR: Missing required field 'findings[]'… v1.0 … incompatible with v1.1`; post-fix same sidecar (no findings[]) exit 0, `1 valid` — `5f169f0d` |
| AC-5 Layer-2 emitter round-trip | `tests/integration/test_handoff_v12_roundtrip.py` (×3) + `tests/unit/features/lifecycle/test_handoff_v12_emission.py` (10) | emit → gates accept → runtime_files accept → `reports validate --strict` exit 0; zero-refs fallback emits honest v1.1 — `bce7e1af` |
| AC-6 adoption, both halves | `rg 'handoff-v1\.1' dadaia_workspace/public/` · `pytest tests/contract/test_handoff_instruction_adoption.py` | negative: 8 survivors, all fate-ledgered back-compat/non-instructional (T-62-30 ledger); positive: 16/16 surfaces asserted, 19/19 passed (roster-completeness pinned) — `89620050` |
| AC-7 containment (RED-first) | hostile-slug matrix in `tests/unit/infrastructure/test_consumer_fanout_containment.py` | RED: pre-fix `"../evil"` landed `AGENTS.md` OUTSIDE `repos/`; post-fix nothing written outside `repos/`, one `[reject]` stderr line per bad slug, doctor protected — `3be0e698` |
| AC-8 symlink refusal (RED-first) | same suite, (a)–(d) | RED: pre-fix `shutil.copy2` wrote THROUGH the link (target sha `7d5eba05… → 5a67bc07…`); post-fix target byte-identical + `[foreign] … (symlink)`; dangling refused; doctor `[foreign]` exit 0; symlinked consumer DIR stays `[ok]` (CI pattern pin) — `3be0e698` |
| AC-9 response-guard sabotage replay | rename `.memory-chip` in `index.py` → unit lock + local playwright | sabotaged: unit lock FAILED + e2e `2 failed` (both guards timeout at `waitForSelector`, where pre-fix yielded "2 passed"); reverted: unit 578 passed, e2e `2 passed` — `70e1310c` |
| AC-10 mutation-sanity (a–f) | one-line sabotages per task line | (a) conditional dropped ⇒ matrix FAILS; (b) existence skipped ⇒ AC-3(a) FAILS; (c) coverage skipped ⇒ AC-3(b) FAILS; (d) detection reverted ⇒ AC-4 FAILS; (e) slug reject dropped ⇒ 10 FAILED; (f) `is_symlink()` dropped ⇒ 3 FAILED — all reverted; T-62-11/T-62-40 evidence blocks |
| Frozen v0.1.50 no-steal suite | `git diff` vs main on the lease/gate test files | **zero-diff** — `066471e0` |
| Self-hosting reconcile | `dadaia public stage` → `install --target all` → `public doctor` | exit 0 incl. `[ok] public-privacy`; W3 surfaces projected — `066471e0` |
| QA ship gate | `dadaia reports validate <handoff>` | **APPROVED** — handoff `2026-07-07T175126Z` (3 INFO findings → Drifts) |
| Security push gate (per push-cycle) | pre-push security-verdict chokepoint | **APPROVED** — keyed to pushed ref sha `066471e0`; emitted as a REAL v1.2 handoff with `self_pull.refs` (dogfooding); the QA reviewer's first draft handoff was REJECTED by the new FR2 coverage check — live end-to-end proof |
| CI (PR #118) | GitHub Actions | all checks green at merge `352969da`; one pull_request-event flake on `workflow-policy-harness-toggle` (same-sha push-event run + rerun green → Drifts) |

## Drifts

### spec-8-kept-predates-v0161-ninth-contract (QA INFO finding)

**Description:** SPEC AC-11 / PLAN W5 / T-62-60 pinned `lint-imports` at "**8 kept / 0
broken**" — text authored before v0.1.61 merged and landed the 9th contract
(`cli-no-infrastructure`). The actual gate result throughout this release is **9 kept / 0
broken**, ignore-cap unchanged.

**Resolution:** Adjudicated as a Ruling 62-A rebase note (recorded on T-62-11 and T-62-60
evidence blocks and in the QA ship-gate INFO finding): the release rebased on v0.1.61's
closed state and re-verified; the SPEC figure is pre-rebase text, not a gate regression. No
spec re-edit post-approval.

**Memory updates:** none needed beyond the rebase itself — `specs/memory/architecture.md`
already documents the 9 contracts from v0.1.61's closure (rebased, never reverted).

### e2e-panel-harness-toggle-ci-flake (LOW bug filed, NOT consumed)

**Description:** One pull_request-event CI run flaked on the
`workflow-policy-harness-toggle` e2e-panel spec; the same-sha push-event run and a rerun
were green. Not caused by this release's FR7 changes (different spec file).

**Resolution:** Registered as NEW LOW bug `e2e-panel-harness-toggle-ci-flake`
(`specs/bugs/20260707T18Z-00.jsonl`, `reported` event) — **not consumed by this release**;
it rides a later pick per bug-always-solved at that release's definition. All checks green
at merge.

**Memory updates:** none (a flake under investigation is not product truth).

### instance-handoff-emission-deferred-until-w5-reconcile

**Description:** The W1/W2 implementation handoffs were emitted as `handoff-v1.1`: the live
instance's projected schema and emitter-skill instruction still carried v1.1 until the W5
self-hosting reconcile (`public stage → install → doctor`, T-62-60) projected the v1.2
schema + the 16 instruction surfaces. Source-vs-instance lag inherent to the plan (W3
surfaces project at W5 by design).

**Resolution:** Honest emission per the transition posture (v1.1 documents stay valid
forever; ADR-2) — never a fabricated v1.2 without a projected contract. Post-reconcile
handoffs are real v1.2: the security push-gate handoff carried `self_pull.refs` and the QA
reviewer's non-compliant first draft was rejected by the new coverage check — the feature
validating its own release.

**Memory updates:** none beyond the planned pass — the transition posture and the
sanctioned v1.1 fallback are documented in `agent-comms.md`.

## Memory updates

Memory describes the product **as it is now**; the change history lives here and in
`_archive/`. All edits landed in this CLOSURE phase (MEMORY gate open), **rebased on
v0.1.61's closed state per Ruling 62-B** (this release closes after v0.1.61, before
v0.1.63/64; no sibling correction reverted — verified by reading each atom's current state
before editing). `release_origin: v0.1.62` + `last_updated: 2026-07-07` set on every edited
atom. **Catalog regen required** (PM follow-up: `dadaia memory catalog generate`) —
tldr/summary changed on `agent-comms`, `public-asset-distribution`, and
`lifecycle-foundation`; regen accumulates v0.1.61's prior deltas per Ruling 62-B.

- `specs/memory/product/agents/agent-comms.md` — **primary.** Contract is the handoff-v1
  family at current token `handoff-v1.2`: the `self_pull.refs` proof line (`specs/`-prefixed,
  context-relative, only actually-read atoms — the Layer-1 mirror of FRAG-COH-4); the
  service-layer version-conditional (v1.2 ⇒ `self_pull` required + ref existence +
  role-map coverage via `core/role_atom_map.py`); the sidecar detection truth (v1.2 =
  modern, never v1.0-compat); the transition posture + the honest v1.1 zero-refs fallback
  (the only sanctioned v1.1 emission); adoption section rewritten to the 16-surface
  contract-tested roster.
- `specs/memory/product/distribution/public-asset-distribution.md` — fan-out containment:
  lexical hostile-slug rejection (POSIX + Windows, non-silent `[reject]`, fail-open,
  protects install AND doctor), write-time containment assert, destination-file symlink
  refusal incl. dangling (`[foreign] … (symlink)`, doctor exits 0), symlinked consumer DIRs
  explicitly legitimate (CI `ln -sfn` pattern).
- `specs/memory/product/sdd/lifecycle-foundation.md` — Layer-2 emitters produce v1.2 with
  `self_pull.refs` from `InjectedContext` dedup → role-map fallback → honest v1.1;
  accept-sets `{v1, v1.1, v1.2}`; `ROLE_ATOM_MAP` data relocated to `core/role_atom_map.py`
  with a same-object re-export through `role_atoms.py`; the (N4) layer-grounding-honesty
  paragraph updated — both layers now carry a mechanical proof (the deferred-L1 note and
  the consumed backlog pointer retired).
- `specs/memory/quality-assurance.md` — **rebase edit** (v0.1.61's warning-clean law,
  bootstrap-script rows, and coverage-gate note untouched): NEW required-presence e2e law
  (never null-guard a data-dependent selector; response-guard chip assertion as
  defence-in-depth behind the byte-identical DOM-contract unit lock); live-scale bracket
  re-validated (4,701/v0.1.61 → **4,755 passed + 17 skipped at v0.1.62 ship**); agent-comms
  dependency row updated to the v1-family token + the 16-surface adoption contract test.
- `specs/memory/architecture.md` — **assess verdict: warranted** (the §core/ leaf
  enumeration is exhaustive): `core/role_atom_map.py` added as a pure stdlib-only core leaf
  consumed by `features/reports` + re-exported same-object by `features/lifecycle`
  (no cross-feature edge); the `lifecycle` and `reports` feature blurbs and the data-plane
  handoff-version mention updated to match.
- `specs/memory/tech-stack.md` — **no change:** the release adds no dependency and no tool
  (SPEC §8 expectation confirmed).

## Dispositions

Disposition sweep per the ADR-11 vocabulary — the picked HIGH bug (Ruling 62-E,
never silently absorbed) + the three consumed backlog items. The LOW flake bug filed
mid-release (`e2e-panel-harness-toggle-ci-flake`) stays **open** — not consumed here.

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| bug `reports-sidecar-version-detection-misroutes-future-tokens` (`specs/bugs/20260707T03Z-00.jsonl`) | bug (JSONL) | `resolved — v0.1.62` (terminal event appended by PM at archive: `dadaia bugs append --bug-id reports-sidecar-version-detection-misroutes-future-tokens --event resolved --release v0.1.62`) | AC-4 test `test_v12_sidecar_never_routes_to_v10_compat_cli` (repro verbatim, RED→GREEN) + FR2 commit `5f169f0d` |
| `specs/backlog/layer1-selfpull-handoff-audit-line.md` | backlog | `delivered` (`delivered_in: v0.1.62`) | FR1–FR4, `5f169f0d`/`bce7e1af`/`89620050`; anchor `hooks/ctx_inject.py#main` survives **byte-identical** (Ruling A never reopened); flipped this closure; PM `git mv` → `specs/_archive/v0.1.62/consumed-backlog/` |
| `specs/backlog/fanout-repo-slug-containment.md` | backlog | `delivered` (`delivered_in: v0.1.62`) | FR5/FR6, `3be0e698` (the "REJECTED — trusted-input" override DECLINED per ADR-9/PM retier); anchor `workspace_guardrail.py#_install_guardrail_pair` survives hardened; flipped this closure; PM `git mv` → archive |
| `specs/backlog/response-guard-chip-presence-hardening.md` | backlog | `delivered` (`delivered_in: v0.1.62`) | FR7, `70e1310c`; anchor `test_index_dom_contract.py#test_memory_chip_present_with_populated_context` survives byte-identical (primary lock); flipped this closure; PM `git mv` → archive |

**Consumed-backlog archive payload** (PM writes this as
`specs/_archive/v0.1.62/consumed-backlog/consumed_backlog.json` — PE does not write
`_archive`):

```json
{
  "release": "v0.1.62",
  "consumed": [
    {
      "slug": "layer1-selfpull-handoff-audit-line",
      "shipped_anchors": [
        "dadaia_workspace/hooks/ctx_inject.py#main"
      ],
      "note": "DELIVERED — v0.1.62 (archived at CLOSURE, anchor survives BYTE-IDENTICAL — the release verifies self-pull, it never reopened Ruling A). handoff-v1.2 schema bump ($id/title/enum; optional self_pull {refs, minItems 1, no-traversal pattern} on whitelisted stdlib-validator keywords only); version-conditional service-layer check in ReportsValidationService (v1.2 => self_pull required + ref existence repos/<context>/<ref> -> <workspace>/<ref> fail-soft + role-map coverage via NEW core/role_atom_map.py, same-object re-export through role_atoms.py); _detect_sidecar_version fix resolving the picked HIGH bug reports-sidecar-version-detection-misroutes-future-tokens; both L2 emitters v1.2 from InjectedContext refs (role-map fallback -> honest v1.1 on zero refs — the only sanctioned v1.1 emission); accept-sets widened {v1, v1.1, v1.2}; 16-surface instruction adoption pinned by tests/contract/test_handoff_instruction_adoption.py (16/16); AC-1 corpus lock proves the transition posture golden-first. Live proof at ship: the security push-gate handoff was a real v1.2 with self_pull.refs and the QA reviewer's first draft was REJECTED by the new coverage check. Ship PR #118, squash 352969da."
    },
    {
      "slug": "fanout-repo-slug-containment",
      "shipped_anchors": [
        "dadaia_workspace/infrastructure/workspace_guardrail.py#_install_guardrail_pair"
      ],
      "note": "DELIVERED — v0.1.62 (archived at CLOSURE, anchor survives hardened). The 'REJECTED — trusted-input' override was DECLINED (ADR-9; PM retier LOW->MEDIUM on two independent security reviews + the 2026-07-06 pass). Lexical slug validation at derivation (_consumer_repos_for_root: single relative non-dot component; rejects /, \\, ., .., absolute incl. Windows drive/UNC via PurePosixPath AND PureWindowsPath parts; non-silent [reject] stderr line; fail-open; protects install AND doctor) + write-time containment assert in _install_guardrail_pair + FR6 symlink write-through refusal (dst.is_symlink() incl. dangling => never written, [foreign] ... (symlink); doctor symlink-aware, exit 0; symlinked consumer DIRs stay legitimate — the CI ln -sfn pattern pinned green by AC-8(d)). RED-first: pre-fix '../evil' received the pair OUTSIDE repos/ and copy2 wrote through the link. v0.1.60 provenance suites byte-identical (204 passed). Ship PR #118, squash 352969da."
    },
    {
      "slug": "response-guard-chip-presence-hardening",
      "shipped_anchors": [
        "tests/unit/features/panel/test_index_dom_contract.py#test_memory_chip_present_with_populated_context"
      ],
      "note": "DELIVERED — v0.1.62 (archived at CLOSURE, anchor survives byte-identical — the primary DOM-contract lock). Both response-guard.spec.ts null-guards replaced with required presence (waitForSelector('.memory-chip', {timeout: 8000}) -> click -> settle); graceful-empty branch REMOVED (ADR-8 — the CI fixture deterministically seeds >=1 context + memory atoms and fast-fails otherwise). AC-9 sabotage replay: chip renamed => unit lock FAILED AND e2e 2 failed (pre-fix e2e passed '2 passed'); reverted => 578 unit + 2 e2e green. Defence-in-depth behind the never-re-baselined unit lock, codified as the required-presence e2e law in quality-assurance.md. Ship PR #118, squash 352969da."
    }
  ]
}
```

## Backlog returns

**None.** The TASKS.md conditional return (`l1-read-proof-hardening` — a per-atom read-proof
beyond self-report) was to be filed **only if the trio review demanded it**: the QA ship-gate
APPROVED with 3 INFO findings (none requesting it) and the security push-gate APPROVED — no
reviewer demanded it, so no return is filed. The self-report honesty boundary is recorded in
`agent-comms.md` and `lifecycle-foundation.md` (N4) as current truth, and ADR-3's stronger
override remains available to a future operator pick.

## Cross-release closure order (Ruling 62-B)

This release closes **second** in the fixed queue v0.1.61 → v0.1.62 → v0.1.63 → v0.1.64 —
after v0.1.61 (whose closed state every shared atom edit here was rebased on: 9 import
contracts, warning-clean law, bootstrap-script rows all preserved), before v0.1.63/64. The
later-closing siblings rebase `quality-assurance.md`, `public-asset-distribution.md`, and
`architecture.md` on THIS closure's state (never reverting the v1.2 contract, the
containment/symlink posture, or the required-presence e2e law), and every subsequent
`catalog.json` regen accumulates this closure's tldr/summary deltas. PM owns the phase
schedule; `ACTIVE.md` is a single pointer.

## Archive decision

**MOVE** — `specs/releases/v0.1.62/` moves to `specs/_archive/releases/v0.1.62/` via `git mv`
(PM/operator; PE issues no git mutations and runs no shell). PM then executes, in order:

1. `dadaia bugs append --bug-id reports-sidecar-version-detection-misroutes-future-tokens
   --event resolved --release v0.1.62` (evidence: the AC-4 test + `5f169f0d`);
2. `git mv` the 3 delivered backlog files → `specs/_archive/v0.1.62/consumed-backlog/` and
   write `consumed_backlog.json` there (payload above, verbatim);
3. `dadaia memory catalog generate` (required — tldr/summary changed on 3 product atoms;
   regen includes v0.1.61's prior deltas);
4. `dadaia specs doctor` + `dadaia backlog doctor` (both must exit 0);
5. the release-dir `git mv specs/releases/v0.1.62 specs/_archive/releases/v0.1.62`;
6. advance `ACTIVE.md` → `release: v0.1.63`, `phase: DEFINITION` per the queue schedule.

**Order law honored: the memory rebase + this disposition sweep land BEFORE `ACTIVE.md`
leaves CLOSURE.**
