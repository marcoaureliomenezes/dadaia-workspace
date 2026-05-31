# Closure: Release — memory-context-enforcement-v1

> **Status:** Aprovado
> **Release ID:** memory-context-enforcement-v1
> **Owner:** product-engineer
> **Closed:** 2026-05-31

## Summary

This release delivers the foundation of "agents never work blind" across all three runtimes
(Claude Code, OpenCode, Codex). The central mechanism is a lean memory bootstrap injected at
session start: `ctx-inject.sh` now emits stripped `tech-stack.html` + `catalog.json` content
(~4,584 tokens / $0.0138 at Sonnet pricing) wrapped in bounded markers on the first message of
every session. Architecture is intentionally excluded from the injected payload (operator
decision D-5): it is the largest atom (~7.5K tokens) and is self-pulled by agents before
architectural or cross-layer work, exactly as feature atoms are self-pulled.

Alongside the hook payload, a machine-readable `catalog.json` was generated and committed at
`specs/memory/product/catalog.json` (18 entries, all fields populated). The `CAT-1` doctor check
now keeps the catalog in sync with the feature HTML files on disk. A mandatory "Step 0 — Memory
bootstrap" block was inserted into all 21 agent personas, making memory consumption commanded
rather than optional — 5 previously fully-blind agents (code-reviewer, design-specialist,
project-auditor, researcher, security-reviewer) also gained the `dadaia-workspace-spec-navigator`
skill in their frontmatter. A `specs/memory/AGENTS.md` local contract file was created, closing
the `TREE-5` specs doctor warning. A universal Codex `memory-ctx` adapter was added,
auto-registered by directory iteration (ADR-CX-001, no `config.toml` edit required). The full
test suite stands at 2304 passed / 1 skip / 1 xpass / 0 failed with 89.54% coverage. QA
approved all 16 acceptance criteria.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-MCE-01 | C-2: `catalog.py` generator + unit tests | (committed Wave A) |
| T-MCE-02 | C-2: CAT-1 doctor check + tests; SPEC-DOC-002L exemption added for AGENTS.md | (committed Wave A) |
| T-MCE-03 | C-2: CLI wiring `dadaia memory catalog generate` + tests | (committed Wave A) |
| T-MCE-04 | C-2: Generated and committed initial `catalog.json` (18 entries) for this repo | (committed Wave A) |
| T-MCE-05 | C-3: Step 0 memory bootstrap block inserted in all 21 agent personas; 5 P0 agents gained spec-navigator skill | (committed Wave A) |
| T-MCE-06 | C-4: `specs/memory/AGENTS.md` authored (71 lines, 5 sections); C-5: `public/runtime/codex/memory-ctx/SKILL.md` created | (committed Wave A) |
| T-MCE-07 | C-1: `ctx-inject.sh` extended with lean payload + sentinel guard; `strip-memory-html.py` created | (committed Wave B) |
| T-MCE-08 | C-1: `ctx-inject.ts` first-message guard added using sessionID sentinel file | (committed Wave B) |
| T-MCE-09 | Propagation: `dadaia public stage && install --target all`; public doctor exit 0 (225 ok, 0 drift, 0 missing); OQ-1..4 confirmed | (committed post-Wave B) |
| T-MCE-10 | QA acceptance gate: 16/16 ACs passed; suite 2304/89.54%; APPROVED | (QA report: `.dadaia/reports/dadaia-workspace/qa-engineer/2026-05-31T053403Z-memory-context-enforcement-v1-qa.html`) |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| All 21 agent personas contain Step 0 block | `grep -l "Step 0" dadaia_workspace/public/agents/*.md \| wc -l` | `21` |
| 5 P0 agents have spec-navigator in skills frontmatter | `grep -l "dadaia-workspace-spec-navigator" public/agents/{code-reviewer,design-specialist,project-auditor,researcher,security-reviewer}.md \| wc -l` | `5` |
| `ctx-inject.sh` emits bounded memory block | `bash .dadaia/scripts/ctx-inject.sh` with `DADAIA_CONTEXT` set | Markers `=== workspace memory (tech + catalog) ===` … `=== end memory bootstrap ===` present; architecture NOT included (D-5) |
| Injected payload token estimate | `chars/4 proxy: 18,338 chars` | ~4,584 tokens — within 3,500-6,000 range; cost $0.0138 ≤ $0.018 |
| `catalog.json` valid with 18 entries | `python3 -c "import json; d=json.load(open('specs/memory/product/catalog.json')); print(len(d['features']))"` | `18` |
| specs doctor clean (0 errors, 0 warnings) | `dadaia specs doctor` | 0 errors / 0 warnings; CAT-1 clean; TREE-5 absent |
| `memory-ctx` projected to Codex runtime | `ls .codex/skills/memory-ctx/SKILL.md` | File present; auto-discovered via ADR-CX-001 |
| public doctor exit 0 | `dadaia public doctor` | 225 ok, 0 drift, 0 missing |
| Full pytest suite green | `poetry run pytest` | 2304 passed, 1 skipped, 1 xpassed, 0 failed; 89.54% coverage |
| QA verdict | QA sidecar `handoff-v1.1` | `.dadaia/reports/dadaia-workspace/qa-engineer/2026-05-31T053403Z-memory-context-enforcement-v1-qa.handoff.json` — APPROVED, 16/16 ACs |

## Drifts

### codex-adapter-auto-registration

**Description:** SPEC §4/C-5 described registration via a config.toml per-skill table. In
reality, `_install_codex_runtime_adapters` in `infrastructure/public_assets.py` auto-discovers
every `public/runtime/codex/<slug>/SKILL.md` by directory iteration (`sorted(src_root.iterdir())`).
There is no config registry and no per-skill `config.toml` entry. This was discovered pre-implementation
by ai-engineer reviewing the existing `design-ctx` and `frontend-ctx` adapters.

**Resolution:** SPEC text was corrected at the C-5 section (ADR-CX-001 named and documented).
`memory-ctx` is registered purely by being a directory with a `SKILL.md` — exactly consistent
with the existing adapter pattern. No config edit was made or is needed.

**Memory updates:** `specs/memory/architecture.html` updated to note ADR-CX-001 and auto-discovery
pattern for Codex adapters (already described in the agent topology layer, clarified here).

### tree5-spec-bug-agents-path

**Description:** TREE-5 in the specs doctor checks for `specs/memory/AGENTS.md`. The SPEC (§4/C-4)
initially described the file as `specs/memory/AGENTS.md` but there was ambiguity about whether the
doctor checked `specs/AGENTS.md` (workspace-level) vs `specs/memory/AGENTS.md` (memory-level).
The doctor code was confirmed to check `specs/memory/AGENTS.md` — matching SPEC intent.

**Resolution:** `specs/memory/AGENTS.md` was created at the correct path. TREE-5 is now absent in
doctor output. `specs/AGENTS.md` is a separate file managed by `spec-context-tree-v2` TREE-5 at
that level; these are distinct files at distinct paths.

**Memory updates:** `specs/memory/AGENTS.md` finalized with D-5 lean injection model in the read
contract (RULE A gate-lock; AGENTS.md is governed memory-directory content).

### spec-doc-002l-agents-md-exemption

**Description:** Creating `specs/memory/AGENTS.md` as a Markdown file tripped the SPEC-DOC-002L
doctor check, which flags non-HTML files in `specs/memory/`. The SPEC explicitly called this out
(§9 AGENTS.md note): "The doctor SPEC-DOC-002L correctly exempts it from the HTML-only atom rule."

**Resolution:** An exemption was added to `doctor.py` for `AGENTS.md` in `specs/memory/` —
it is a contract/governance file, not a memory atom. The QA report confirms SPEC-DOC-002L did not
trip during acceptance (0 warnings).

**Memory updates:** No memory HTML change; the exemption is in Python source.

### d5-token-overage-lean-pivot

**Description:** The original SPEC target for the injected payload was 6,500-8,500 tokens (full
arch+tech+catalog). Measurement during implementation showed `architecture.html` barely strips
(it is prose + Mermaid diagrams, not boilerplate) and the full payload reached ~11.4-13K tokens —
~60% over target.

**Resolution:** Operator decision D-5 (amendment 2026-05-31) pivoted to lean payload: tech-stack +
catalog ONLY (~4,584 tokens, $0.0138). Architecture moved to self-pull tier. All acceptance criteria,
the Step 0 block, the Codex `memory-ctx` adapter, `ctx-inject.sh` marker text, and
`specs/memory/AGENTS.md` read-contract were updated to reflect D-5.

**Memory updates:** `specs/memory/architecture.html` (memory-injection subsystem description updated);
`specs/memory/AGENTS.md` read contract finalized (step ordering: tech+catalog injected; architecture
self-pull before architectural work).

### agents-md-closure-finalization

**Description:** `specs/memory/AGENTS.md` read-contract section could not be finalized during
IMPLEMENTATION because RULE A gate-locks `specs/memory/*.md` to product-engineer during CLOSURE —
by design. The C-4 draft listed the full canonical read order which remained valid; CLOSURE adds the
lean-injection mechanism detail and the D-5 step ordering.

**Resolution:** `specs/memory/AGENTS.md` read-contract is finalized here at CLOSURE (this document)
with the D-5 lean model. The SDD gate behaviour is correct and intentional.

**Memory updates:** `specs/memory/AGENTS.md` (read contract section updated with D-5 lean model and
step ordering).

## Memory updates

- `specs/memory/architecture.html` — added memory-injection subsystem section: `ctx-inject.sh`
  lean payload (tech-stack + catalog; architecture self-pull per D-5), `strip-memory-html.py`
  helper, first-message sentinel guard, `catalog.json` generation pipeline, CAT-1 doctor check.
  Also noted ADR-CX-001 Codex adapter auto-discovery pattern for `memory-ctx`.
- `specs/memory/AGENTS.md` — read-contract section finalized to D-5 model: lean bootstrap
  (tech-stack + catalog) injected at work-start; `architecture.html` self-pulled before
  architectural/cross-layer work; feature atoms self-pulled via catalog. Gate-locked write during
  CLOSURE as designed.
- `specs/memory/tech-stack.html` — `html.parser` stdlib usage noted in the Languages table for
  `strip-memory-html.py`; `catalog.json` noted as a new state file under JSON usage. Meta timestamp
  updated.
- `specs/memory/product/index.html` — catalog feature list unchanged (no new entry added — see note
  in product/index.html section below). Meta timestamp updated.

**Catalog feature list decision:** The memory-injection subsystem (ctx-inject.sh payload,
strip-memory-html.py, catalog.json generation) is infrastructure underlying existing features
(`agent-orchestration`, `public-asset-distribution`, `specs-doctor`, `sdd-gate-v3`). It does not
constitute a user-visible standalone feature in the product catalog. No new `<li>` entry was added
to `index.html`. The catalog.json was regenerated to reflect the updated `generated_at` timestamp
but the feature list (18 entries) is unchanged.

**index.html catalog change: NO** — feature list and order are unchanged. `catalog.json` must be
regenerated by the orchestrator (the `generated_at` timestamp in the current committed file is now
stale relative to this CLOSURE's memory updates, though the feature list itself is stable).

## Backlog returns

No items were discovered during implementation that exceeded release scope. All open questions
(OQ-1..OQ-5) were resolved by devops-engineer during T-MCE-09. No candidates or ideas to file.

## Archive decision

**MOVE** — release directory will be moved to `specs/_archive/releases/memory-context-enforcement-v1/`
via `git mv`. ACTIVE.md will be updated to point to the next release or `release: none`.
