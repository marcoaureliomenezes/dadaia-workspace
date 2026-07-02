# SPEC — v0.1.48 — Memory Single-Ownership + Truth + English Canon

**Status:** Aprovado
**Branch:** `feature/v0.1.48` (base: `b8c40708`, v0.1.47 merge)
**Origin:** operator directives 2026-07-02 ("All specs must be in english. go v0.1.48") disposing
audit `specs/audits/20260702T015037Z-56b226fb/` (84 findings) + open bug
`memory-index-table-broken-gfm`. GRILL: `GRILL.md` (Aprovado, G1–G12).

## 1. Problem

The v0.1.47 memory canon is structurally right but carries: (a) 16 verified-false or divergent
claims against code `b8c40708`; (b) facts owned in 2–4 places (matcher ×3, bind-epoch ×2, lease
×2, codex-wrapper ×4) — the direct cause of every major divergence; (c) a broken generated
index.md table (open bug); (d) a 13 PT / 17 EN language split with mixed atoms, against the
operator's English canon; (e) tree hygiene strays.

## 2. Goals (what done means)

1. Every checkable claim in `specs/memory/**` + `constitution.md` is true against the code.
2. Every fact has exactly one owning file; other files reference it via `[[wikilink]]`.
3. All memory content (bodies, frontmatter, h2 headings, catalog/index output) is English.
   SDD status tokens `Aprovado`/`Em revisão`/`Draft` remain untouched (G1).
4. The catalog generator emits valid GFM, derives `area`, and stops exporting `rank` into
   session digests. Bug `memory-index-table-broken-gfm` resolved.
5. All 84 audit findings explicitly dispositioned (§5); audit archived with DISPOSITION.md at close.

## 3. Scope by wave

- **W1 — truth fixes** (memory content; DEFINITION phase): F-01..03, F-06..09, F-20, F-26, F-27,
  F-35, F-36, F-40, F-41, F-43/44, F-45, F-48..51, F-53, F-56..59, F-62..65, F-67, F-68, F-70, F-72.
  F-06/F-07 are fixed in THREE copies: `specs/memory/AGENTS.md` directly (the audited file —
  `install` never overwrites it; scaffold-on-missing only) plus both sources
  (`public/data/memory-AGENTS.md`, `public/scaffold/memory/AGENTS.md`), then
  stage/install/doctor for the staged copies.
- **W2 — ownership consolidation**: F-42 (delete 4 skill-mirror atoms after migrating unique
  facts), F-46 (merge agent-sdd-alignment → agent-orchestration), F-30 (archive sdd-hotfix-track +
  fix dangling wikilink + fold `specs hotfix open` note), F-60 (lease single-home: sdd-gate-v3
  owns acquire/liveness/heartbeat; context-management owns bind/release/session lifecycle),
  F-61 (projection/registration facts → public-asset-distribution), F-05 (architecture
  de-enumeration per G7), F-28/F-29 (lifecycle-foundation de-changelog + roster →
  `[[dadaia-workflows]]`), F-66 (repos-catalog → platform/), constitution nits F-11/12/13/19,
  scoping trims F-04/10/14/15/16/17/18/21/22/23/33/34/38/47/69/71. Catalog regen.
- **W3 — code**: F-73 GFM fix in BOTH renderers + contract test; F-84 align renderer output shape;
  F-75 `area` derivation + index grouping; F-77 drop `rank` from `_DIGEST_FIELDS`; F-78 docstring
  truth; F-79 English Group-A allowlist + prune dead strings (PT legacy kept, G2); F-25
  quality-assurance `category: core`; `core.js` stale `#agents` comment; bug
  `specs-doctor-tree5m-remediation-wrong` (TREE-5M remediation text claims `install --target all`
  projects `specs/memory/AGENTS.md`, which install cannot do — `features/specs/doctor.py:2518-2520`).
  Full pytest + ruff + mypy.
- **W4 — English canon sweep**: translate all surviving atoms + 3 top-level memory files +
  memory frontmatter to English (G1); refresh `token_estimate`; regenerate catalog + index;
  LINT-1 + CAT-1 green.
- **W5 — hygiene**: F-81 archive `specs/releases/v0.1.23/`; F-82 delete orphan
  `specs/backlog/img/` PNGs; F-83 delete empty `docs/img`; all doctors green.
- **W6 — ship**: CLOSURE flip + CLOSURE.md; bug terminal event `resolved --release v0.1.48`;
  audit archive + DISPOSITION.md; backlog note for deferred item; qa-engineer checkpoint;
  security-reviewer handoff keyed to final sha; push; CI watch to all-green; PR.

## 4. Out of scope

Fragments/personas (already English, optimized in v0.1.47); SDD status tokens; consumer
AGENTS.md fan-out (backlog `consumer-agents-md-fanout-redesign`); `agent_tier` runtime wiring
(deferred, §5); panel hash-route expansion (truth is corrected to match code; adding routes is
backlog `panel-ux-overhaul` territory); retro-translation of archived/ledger artifacts.

## 5. Dispositions (audit-disposition law — every finding, explicit)

- **fixed (W1):** F-01, F-02, F-03, F-06, F-07, F-08, F-09, F-20, F-26, F-27, F-35, F-36, F-40,
  F-41, F-43, F-44, F-45, F-48, F-49, F-50, F-51, F-53, F-56, F-57, F-58, F-59, F-62, F-63, F-64,
  F-65, F-67, F-68, F-70, F-72.
- **fixed (W2):** F-04, F-05, F-10, F-11, F-12, F-13, F-14, F-15, F-16, F-17, F-18, F-19, F-21,
  F-22, F-23, F-28, F-29, F-30, F-33, F-34, F-38, F-42, F-46, F-47, F-60, F-61, F-66, F-69, F-71.
- **fixed (W3):** F-25, F-73, F-75, F-77, F-78, F-79, F-84.
- **fixed (W4):** F-24, F-54, F-74, F-80.
- **fixed (W5):** F-81, F-82, F-83.
- **superseded (structural fix elsewhere):** F-39 → F-42 (atom deleted; harness-codex.md already
  correct); F-31, F-32, F-37 → F-30 (atom archived); F-52, F-55 → F-42/F-43 (content deleted).
- **deferred with named backlog home:** F-76 (`agent_tier` wire-or-remove →
  `specs/backlog/hygiene-and-dead-code-cleanup.md`; this release documents the field honestly).
- **rejected:** none.

Bug dispositions: `memory-index-table-broken-gfm` → resolved (W3, F-73);
`specs-doctor-tree5m-remediation-wrong` → resolved (W3; found by the QA definition checkpoint).

## 6. Acceptance criteria (mechanical)

- AC-1 truth greps = 0 hits: "não entra em \`poetry.lock\`" (memory), `events_daily` (memory),
  "aba Agents" (memory), `#projects` (panel atom), "pid do harness que bindou" / single-pid
  bind-epoch phrasing (memory), `ADR-X7`/`ADR-X5` (memory), `backend-engineer` (memory).
- AC-2 structure: the 6 removed/merged/archived atoms absent from `product/` (4 deleted + 1 merged
  + 1 archived); `repos-catalog.md` under `product/platform/`; catalog has exactly 25 entries;
  zero dangling wikilinks (LINT-1 = 0/0).
- AC-3 generator: regenerated `index.md` has no blank line between table separator and first data
  row; contract test pins it; both renderer implementations emit identical table shape.
- AC-4 English canon: `grep -rc "^## Propósito\|^## Fluxo de uso\|^## Trigger típico\|^## Diferencial\|^## Estado runtime tocado\|^## Dependências" specs/memory/` = 0;
  mechanical Portuguese proxy on generated output: `grep -c "ção\|çõ\|ã\|õ" specs/memory/product/catalog.json` = 0.
- AC-5 catalog fields: every entry carries `area` matching its parent dir; `rank` absent from
  `hooks/ctx_inject.py:_DIGEST_FIELDS`.
- AC-6 gates: full pytest green (minus CI-only performance dir); `ruff format --check` + `ruff
  check` + `mypy --strict` clean; specs doctor 0 errors; backlog doctor clean; public doctor exit 0;
  lint-memory-atoms 0/0.
- AC-7 governance: bug store 0 open; audit archived with DISPOSITION.md naming v0.1.48;
  CLOSURE.md names each of the 6 removed atoms literally (grep per filename = 6/6 hits, G10).
- AC-8 memory-AGENTS truth: `specs/memory/AGENTS.md` names all 10 schema-required frontmatter
  fields (grep each of `slug title category tldr summary tags agent_tier token_estimate
  last_updated release_origin` ≥ 1 hit) and its write-ownership section contains the word
  `discipline` (gate-enforced phase half vs discipline who half); both `public/data/` and
  `public/scaffold/` copies byte-identical to it.
