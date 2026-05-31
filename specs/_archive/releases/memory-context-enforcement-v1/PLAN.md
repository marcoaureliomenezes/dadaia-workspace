# PLAN — Release: memory-context-enforcement-v1

**Status:** Aprovado
**Release ID:** memory-context-enforcement-v1
**Owner:** product-engineer
**Derived from:** SPEC.md (Status: Aprovado)
**Date:** 2026-05-31

---

## 1. Strategy

This release is purely additive: no schema migration, no breaking change, no new PyPI
dependency. Every cluster delivers one of the following primitive types: (a) a payload
extension to an existing firing hook, (b) a new generated artefact + doctor check,
(c) verbatim text blocks inserted into 21 agent personas, (d) a new local contract file,
(e) a new universal Codex skill. The five clusters are designed to be independently
implementable; their integration dependency is narrow and explicitly declared below.

**Guiding constraint:** All lib-originated assets (`public/scripts/`, `public/plugins/`,
`public/agents/`, `public/runtime/codex/`) are edited at SOURCE in the library and
propagated via `dadaia public stage && dadaia public install --target all`. Neither
ai-engineer nor any other implementer touches the projection files in `.claude/`,
`.codex/`, `.opencode/`, or `.agents/` directly. Propagation is the devops-engineer task
at the end of Wave B.

---

## 2. Layers affected

| Layer | Cluster | Files |
|-------|---------|-------|
| Shell hook (lib-originated) | C-1 | `public/scripts/ctx-inject.sh` |
| Python helper (lib-originated) | C-1 | `public/scripts/strip-memory-html.py` (NEW) |
| TypeScript plugin (lib-originated) | C-1 | `public/plugins/ctx-inject.ts` |
| Python source | C-2 | `dadaia_workspace/features/specs/catalog.py` (NEW) |
| Python source | C-2 | `dadaia_workspace/features/specs/doctor.py` (add CAT-1) |
| Python CLI | C-2 | `dadaia_workspace/cli/commands/memory.py` (add catalog subcommand) |
| Python tests | C-2 | `tests/unit/features/specs/test_catalog.py` (NEW) |
| Python tests | C-2 | `tests/unit/features/specs/test_doctor.py` (extend with CAT-1) |
| Python tests | C-2 | `tests/unit/cli/commands/test_memory.py` (extend with catalog) |
| Generated data file | C-2 | `specs/memory/product/catalog.json` (NEW, committed) |
| Agent personas (lib-originated) | C-3 | `public/agents/*.md` (21 files) |
| Consumer workspace file | C-4 | `repos/dadaia-workspace/specs/memory/AGENTS.md` (NEW) |
| Codex adapter (lib-originated) | C-5 | `public/runtime/codex/memory-ctx/SKILL.md` (NEW — auto-registered by directory iteration, ADR-CX-001) |

---

## 3. Technical approach per cluster

### C-1 — Payload the live hook

`ctx-inject.sh` currently resolves context name (~5 tokens) and exits. The extension
adds a second phase: after printing the context name, the script reads
`$SPECS_DIR/memory/tech-stack.html` and `$SPECS_DIR/memory/product/catalog.json`
(falling back to `$SPECS_DIR/memory/product/index.html` when catalog is absent), strips
the HTML via `strip-memory-html.py`, and emits the results inside bounded markers. Per
operator decision **D-5**, `architecture.html` is NOT injected (it is ~7.5K tokens of
prose/diagrams that barely strips); it is self-pulled by the agent before architectural
work, exactly like feature atoms. Lean payload ≈ 5K tokens.

```
=== workspace memory (tech + catalog) ===
...
=== end memory bootstrap ===
```

`strip-memory-html.py` uses Python `html.parser` (stdlib only) to remove `<head>`,
`<style>`, and Mermaid `<script>` blocks while preserving all prose and diagram content.
The script is invoked inline from `ctx-inject.sh` as
`python3 "$SCRIPT_DIR/strip-memory-html.py" "$FILE"` and writes to stdout.

**First-message guard (OpenCode):** `ctx-inject.ts` fires on every `chat.message`. The
guard in `ctx-inject.ts` checks `_input.messageID` ordering or uses a session-scoped
sentinel file at `.dadaia/tmp/ctx-inject-fired-<sessionID>` (mechanism resolved by
devops-engineer per OQ-2). Once the payload is injected for a session, subsequent
messages see only the context-name line. Claude Code's `UserPromptSubmit` behaviour
(OQ-1) is confirmed by devops-engineer at implementation time; if it fires per-message,
the same sentinel approach is applied to `ctx-inject.sh`.

**Working assumption for OQ-1 (Claude Code trigger):** `UserPromptSubmit` fires on every
user message. The first-message guard is therefore implemented in both `ctx-inject.sh`
and `ctx-inject.ts`. If devops confirms single-fire at implementation time, the guard
in `ctx-inject.sh` is a no-op (never triggers unnecessarily) and can be simplified in
a follow-up hotfix.

**Working assumption for OQ-2 (first-message mechanism):** Use a sentinel file at
`.dadaia/tmp/ctx-inject-fired-<sessionID>` where `sessionID` is derived from a
session-specific env var available in both Claude Code and OpenCode contexts
(e.g., `$CLAUDE_SESSION_ID` or `$OPENCODE_SESSION_ID`). If no session env var is
available, fall back to a process-start sentinel scoped to `$$` (shell PID of the hook
process). devops-engineer confirms the available env var at implementation time.

**Working assumption for OQ-3 (strip-memory-html.py location):** `public/scripts/` is
the source location. This is consistent with `ctx-inject.sh` and ensures all consumer
workspaces receive the helper automatically on `dadaia public install`. If the manifest
or hook-path resolution creates an issue, the fallback is `.dadaia/scripts/` with a
SPEC note — but this should not be needed.

### C-2 — Machine catalog `catalog.json`

`catalog.py` is a new Python module at `dadaia_workspace/features/specs/catalog.py`.
Its public API is a single function `generate_catalog(specs_dir: Path) -> dict` that:

1. Reads `specs_dir/memory/product/index.html`.
2. Parses the `<ol class="catalog">` list to extract rank, slug (from `href`), title
   (from link text), and summary (from adjacent text or `title` attribute).
3. For each entry, resolves `tags` from a `data-tags` attribute on the `<li>` or a
   fallback empty list, and `depends_on` from a `data-depends` attribute or empty list.
4. Writes (or returns for the caller to write) `catalog.json` to
   `specs_dir/memory/product/catalog.json`.

The CLI entry point `dadaia memory catalog generate [--specs-dir PATH]` wraps this
function, resolves `specs_dir`, calls `generate_catalog`, writes the JSON, and prints
the path.

**CAT-1 check in `doctor.py`:** Added as a new `SpecsDoctorIssue` check in the existing
`check_specs` function. Logic:
- Enumerate `*.html` files in `specs_dir/memory/product/` excluding `index.html` → set
  `html_slugs`.
- If `catalog.json` is absent and `html_slugs` is non-empty: emit CAT-1 WARNING
  ("catalog.json absent; N feature HTMLs present; run `dadaia memory catalog generate`").
- If `catalog.json` exists: parse it, extract `slugs` from `features[].slug` → compare
  with `html_slugs`. For each slug in catalog but not on disk, emit CAT-1 WARNING
  (slug-only). For each file on disk not in catalog, emit CAT-1 WARNING (file-only).

Severity is WARNING (not ERROR) per SPEC §4/C-2. The check is strictly additive —
no existing check IDs are modified.

**Initial catalog generation:** software-engineer-python runs
`dadaia memory catalog generate --specs-dir repos/dadaia-workspace/specs`
to produce the initial `catalog.json` for this repo's 18 feature atoms and commits it.

**Tests (sandbox to `tmp_path`):** All test fixtures use `tmp_path`; no venv creation
anywhere in the test tree (conftest backstop remains untouched). Coverage threshold:
`--cov-fail-under=80`.

### C-3 — Universal Step 0 block in 21 agent personas

ai-engineer edits 21 files in `dadaia_workspace/public/agents/*.md` with the verbatim
Step 0 block from SPEC §4/C-3. Placement: immediately before or as the first section of
the existing "Workflow Protocol" (or equivalent workflow) section. If no such section
exists, it is added at the top of the agent body after the frontmatter.

**P0 agents** (code-reviewer, design-specialist, project-auditor, researcher,
security-reviewer) also receive `dadaia-workspace-spec-navigator` added to their
frontmatter `skills:` list. ai-engineer must not duplicate an entry that already exists.

**P2 agents** (software-architect, product-engineer, project-manager) have their existing
memory-read language aligned to the Step 0 block phrasing; no functional change. The
canonical block is inserted verbatim even if a functionally equivalent section already
exists — consistency across all 21 is the acceptance bar (AC-C3-5).

All 21 agent files are lib-originated. After authoring, propagation is required.

### C-4 — `specs/memory/AGENTS.md`

ai-engineer authors `repos/dadaia-workspace/specs/memory/AGENTS.md` (≤ 80 lines) with
the five content sections described in SPEC §4/C-4. This file lives in the consumer
workspace's own specs tree, not in `public/`; it is not lib-originated and does not
require `dadaia public stage/install`. Creating it also closes the TREE-5 `specs doctor`
warning on this repo.

### C-5 — Codex `memory-ctx` universal adapter

ai-engineer creates `public/runtime/codex/memory-ctx/SKILL.md` following the
`design-ctx` adapter pattern, with the 5-step protocol from SPEC §4/C-5. The skill
explicitly states it fires before role-specific adapters.

**Registration is automatic (ADR-CX-001).** `_install_codex_runtime_adapters` in
`infrastructure/public_assets.py` auto-discovers every `public/runtime/codex/<slug>/SKILL.md`
by directory iteration (`sorted(src_root.iterdir())`) and copies each to
`.codex/skills/<slug>/SKILL.md`. `memory-ctx` is registered purely by being a directory
with a `SKILL.md`. No `config.toml` file is created or edited — that file and a per-skill
universal-skills table do not exist. `dadaia public doctor` check D-CX-6 covers
leak/missing/drift for all adapters including `memory-ctx`.

After authoring, propagation is required.

---

## 4. Execution waves

```
WAVE A (parallel — disjoint write sets):
  A1: software-engineer-python — C-2 Python source (catalog.py + tests + doctor CAT-1 + tests + CLI wiring + tests)
  A2: ai-engineer — C-3 Step 0 blocks in 21 personas
  A3: ai-engineer — C-4 specs/memory/AGENTS.md
  A4: ai-engineer — C-5 Codex memory-ctx adapter (SKILL.md only; auto-registered)

  Note: A1, A2, A3, A4 have fully disjoint write sets. All four may proceed in parallel.
  Note: A1 MUST include generation and commit of catalog.json for this repo.

WAVE B (depends on Wave A complete and committed):
  B1: ai-engineer — C-1 ctx-inject.sh payload + strip-memory-html.py
  B2: ai-engineer — C-1 ctx-inject.ts first-message guard

  Note: B1 and B2 depend on catalog.json existing (from A1) for the integration test.
  Note: B1 and B2 may proceed in parallel (disjoint write sets: .sh vs .ts).

PROPAGATION BARRIER (after all of Wave A + Wave B committed):
  devops-engineer runs:
    dadaia public stage
    dadaia public install --target all
    dadaia public doctor   # must exit 0

QA GATE (after propagation exit 0):
  qa-engineer runs the full acceptance plan (SPEC §13 matrix).
```

**Integration dependency detail:** C-1's end-to-end validation (AC-C1-1, AC-C1-7, AC-TOK-1)
requires a real `catalog.json` to exist in the workspace. This is why `catalog.json`
generation (A1) must be committed before C-1 is authored (B1/B2). The C-1 author can
write and unit-test the script logic without `catalog.json`, but the integration test
requires it.

**Why C-1 is Wave B (not Wave A):** C-1 builds on `catalog.json` for its fallback logic
(the fallback path is simpler without catalog) and its integration test. Placing it in
Wave B makes the dependency explicit and avoids partial integration tests.

---

## 5. Resolution plan for OQ-1..OQ-5

| OQ | Owner | Working assumption | Consequence if wrong |
|----|-------|-------------------|---------------------|
| OQ-1 (Claude Code `UserPromptSubmit` frequency) | devops-engineer | Fires every message; guard required in `ctx-inject.sh` | If single-fire, guard is redundant no-op — simplify in a follow-up hotfix (low priority) |
| OQ-2 (first-message guard mechanism, OpenCode) | devops-engineer | Sentinel file at `.dadaia/tmp/ctx-inject-fired-<sessionID>` using available session env var | If no session env var, fall back to PID-based sentinel (session correctness slightly weaker; acceptable for Phase 1) |
| OQ-3 (`strip-memory-html.py` source location) | devops-engineer | `public/scripts/` — propagated to all consumers with `dadaia public install` | If manifest issue, move to `.dadaia/scripts/` at workspace level with a doc note in C-1 |
| OQ-4 (Codex `memory-ctx` trigger sufficiency) | devops-engineer | Step 0 block + `_install_codex_runtime_adapters` auto-projection is sufficient (ADR-CX-001) | If Codex needs an explicit session-start trigger beyond skill presence, devops documents the gap; a dedicated hook entry is the fix |
| OQ-5 (injection staleness across long sessions) | n/a — accepted trade-off | First-message-only is the intended behaviour; SPEC §12/OQ-5 documents the operator note | No implementation consequence — informational only |

---

## 6. Risk register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| `doctor.py` shared surface (CAT-1 vs LOCK-1..6 vs TREE-1..7) | Low | Medium — merge conflict if another release touches the same method | CAT-1 uses a unique check ID with no overlap. software-engineer-python must confirm no in-flight branch modifies `doctor.py` before committing; additive check at the end of the function |
| OpenCode first-message guard token-blowup (OQ-1/OQ-2) | Medium | High — 10x token cost on long sessions if guard fails | Sentinel-file approach is simple and reliable; devops-engineer verifies in acceptance |
| Claude Code `UserPromptSubmit` per-message (OQ-1) | Medium | Medium — ~5K overhead per turn in long sessions | Guard implemented in `ctx-inject.sh` as working assumption; accepted Phase-1 cost if single-fire confirmed |
| `catalog.json` absent on consumer repos (fallback) | High (expected for Phase 1 consumers) | Low — graceful fallback to `product/index.html` already specified in C-1 | Fallback is a first-class requirement (AC-C1-4); consumers are unblocked |
| 21-file persona edit produces 1 missed file | Medium | Medium — AC-C3-5 (`grep wc -l = 21`) would fail | Acceptance check is machine-verifiable; qa-engineer catches any miss before QA gate passes |

---

## 7. Validation strategy

Validation maps directly to SPEC §13 acceptance criteria:

| Phase | Validator | Criteria |
|-------|-----------|---------|
| After Wave A | software-engineer-python | Suite green (`poetry run pytest --cov-fail-under=80`) for C-2 tests |
| After Wave A | ai-engineer | `grep -l "Step 0" public/agents/*.md | wc -l` = 21 locally before commit |
| After Wave A | ai-engineer | All 5 P0 agents have `spec-navigator` in skills frontmatter |
| After Wave B | ai-engineer | Manual: `bash ctx-inject.sh` with valid context emits bounded markers |
| After propagation | devops-engineer | `dadaia public doctor` exit 0; all 3 runtimes verified |
| After propagation | devops-engineer | `dadaia specs doctor` TREE-5 resolved (AGENTS.md exists) |
| QA gate | qa-engineer | Full SPEC §13 matrix: AC-COVER-1..8, AC-RT-1..3, AC-TOK-1..2, AC-DOC-1..3 |

---

*Product Engineer — dadaia-workspace | 2026-05-31*
