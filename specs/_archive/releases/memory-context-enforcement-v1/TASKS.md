# TASKS — Release: memory-context-enforcement-v1

**Status:** Aprovado
**Release ID:** memory-context-enforcement-v1
**Owner:** product-engineer
**Derived from:** PLAN.md (Status: Aprovado)
**Date:** 2026-05-31

---

## Gate note

Wave A tasks (T-MCE-01..T-MCE-06) have fully disjoint write sets and may proceed in
parallel — multiple `[-]` markers are safe only if each owner declares its task `[-]`
in a separate commit and the write sets do not overlap.

Wave B tasks (T-MCE-07..T-MCE-08) depend on Wave A being fully `[x]`. One `[-]` at a
time per owner within Wave B.

T-MCE-09 (propagation) may only begin after all Wave A + Wave B tasks are `[x]` and
committed.

T-MCE-10 (QA gate) may only begin after T-MCE-09 is `[x]` and `dadaia public doctor`
exits 0.

---

## Wave A — Parallel (disjoint write sets)

---

### T-MCE-01 — C-2: catalog.py generator + tests

**Owner:** software-engineer-python
**Cluster:** C-2
**Write set:**
- `dadaia_workspace/features/specs/catalog.py` (NEW)
- `tests/unit/features/specs/test_catalog.py` (NEW)

**Preconditions:** none

**Work:**
1. Create `catalog.py` with public function `generate_catalog(specs_dir: Path) -> dict`
   that reads `specs_dir/memory/product/index.html`, parses the `<ol class="catalog">`
   entries, and returns a dict matching the catalog JSON schema from SPEC §4/C-2.
2. Write `catalog.json` to `specs_dir/memory/product/catalog.json`.
3. Include envelope fields: `generated_at` (ISO-8601 UTC), `context` (from
   `specs_dir` basename or `primary_context.json`), `features` list.
4. Each feature entry must have: `rank`, `slug`, `title`, `summary`, `path`, `tags`,
   `depends_on`.
5. Write unit tests using `tmp_path`; no venv creation; conftest backstop untouched;
   cover: valid parse, missing index.html error, empty catalog, slug/path consistency.

**Done criterion:** `poetry run pytest tests/unit/features/specs/test_catalog.py` passes;
coverage contribution keeps suite at or above 80%.

**Acceptance criteria:** AC-C2-2, AC-C2-3, AC-C2-4, AC-C2-7 (unit-level)

---

### T-MCE-02 — C-2: CAT-1 doctor check + tests

**Owner:** software-engineer-python
**Cluster:** C-2
**Write set:**
- `dadaia_workspace/features/specs/doctor.py` (add CAT-1 check — additive only)
- `tests/unit/features/specs/test_doctor.py` (extend — add CAT-1 test cases)

**Preconditions:** T-MCE-01 `[x]` (catalog.py module must exist for doctor to import)

**Work:**
1. Add CAT-1 check to the existing `check_specs` function in `doctor.py`.
2. Logic: enumerate `*.html` in `memory/product/` excluding `index.html` → `html_slugs`.
   If `catalog.json` absent and `html_slugs` non-empty: emit CAT-1 WARNING.
   If `catalog.json` present: parse slugs, compare, emit one CAT-1 WARNING per
   out-of-sync slug/file. Check ID must be `"CAT-1"`.
3. Severity: WARNING (not ERROR).
4. Doctor message must name the specific out-of-sync slugs/files.
5. Add test cases to `test_doctor.py` using `tmp_path`:
   - catalog.json absent + 3 feature HTMLs → CAT-1 warning.
   - catalog.json present, in sync → no CAT-1.
   - catalog.json present, stale slug → CAT-1 warning names the slug.
   - catalog.json present, extra HTML → CAT-1 warning names the file.

**Done criterion:** `poetry run pytest tests/unit/features/specs/test_doctor.py` passes;
full suite green; no existing doctor tests regressed.

**Acceptance criteria:** AC-C2-5, AC-C2-6, AC-DOC-1, AC-DOC-2

**Risk note:** This is the shared-surface task. `doctor.py` is also modified by
`spec-context-session-locks-v1` (LOCK-1..6) and `spec-context-tree-v2` (TREE-1..7).
CAT-1 must land as a strictly additive check with a unique ID. Confirm no in-flight
branch is modifying `doctor.py` before rebasing.

---

### T-MCE-03 — C-2: CLI wiring (`dadaia memory catalog generate`) + tests

**Owner:** software-engineer-python
**Cluster:** C-2
**Write set:**
- `dadaia_workspace/cli/commands/memory.py` (add `catalog generate` subcommand)
- `tests/unit/cli/commands/test_memory.py` (extend)

**Preconditions:** T-MCE-01 `[x]` (catalog.py must exist before CLI can import it)

**Work:**
1. Add `catalog_app = typer.Typer(...)` to `memory.py`; register under `app` as
   `app.add_typer(catalog_app, name="catalog")`.
2. Add `@catalog_app.command("generate")` that calls `generate_catalog(specs_dir)` and
   writes the resulting JSON to `catalog.json`, printing the output path.
3. Accept `--specs-dir PATH` option (reuse `_resolve_specs_dir` helper).
4. Write unit tests using `tmp_path`; cover: successful generation, missing specs_dir
   error, idempotent regeneration (second call overwrites cleanly).

**Done criterion:** `dadaia memory catalog generate --specs-dir <path>` produces valid
JSON; unit tests pass; full suite green.

**Acceptance criteria:** AC-C2-1 (via CLI invocation), AC-C2-7

---

### T-MCE-04 — C-2: Generate initial `catalog.json` for this repo

**Owner:** software-engineer-python
**Cluster:** C-2
**Write set:**
- `repos/dadaia-workspace/specs/memory/product/catalog.json` (NEW — generated, committed)

**Preconditions:** T-MCE-01 `[x]` and T-MCE-03 `[x]` (CLI must work before generation)

**Work:**
1. Run: `dadaia memory catalog generate --specs-dir repos/dadaia-workspace/specs`
2. Verify output: 18 feature entries (one per `*.html` excluding `index.html`), all
   required fields present, all `path` values resolve to existing files, valid JSON.
3. Commit the generated `catalog.json`.

**Done criterion:** `catalog.json` committed at `specs/memory/product/catalog.json`;
`dadaia specs doctor` emits no CAT-1 warning for this repo.

**Acceptance criteria:** AC-C2-1, AC-C2-2, AC-C2-3, AC-C2-4, AC-C2-7, AC-C2-6,
AC-COVER-4, AC-COVER-5, AC-DOC-3 (TREE-5 separate)

---

### T-MCE-05 — C-3: Step 0 blocks in 21 agent personas

**Owner:** ai-engineer
**Cluster:** C-3
**Write set:**
- `dadaia_workspace/public/agents/*.md` (all 21 files)

**Preconditions:** none

**Work:**
1. Insert the verbatim Step 0 block from SPEC §4/C-3 into all 21 agent persona files.
   Placement: immediately before or as the first section of the existing "Workflow
   Protocol" (or equivalent) section. If no such section exists, add after frontmatter.
2. P0 agents (code-reviewer, design-specialist, project-auditor, researcher,
   security-reviewer): also add `dadaia-workspace-spec-navigator` to `skills:` list in
   frontmatter if not already present.
3. P2 agents (software-architect, product-engineer, project-manager): align existing
   memory-read language to the Step 0 block phrasing; insert the canonical block verbatim
   (does not remove existing text — adds the standard block).
4. Verify locally: `grep -l "Step 0" dadaia_workspace/public/agents/*.md | wc -l` = 21.
5. Verify P0: all 5 P0 agent files contain `dadaia-workspace-spec-navigator` in skills.

**Done criterion:** Local grep produces 21; all 5 P0 agents have spec-navigator in
frontmatter; `poetry run pytest` still passes (no test regression from persona changes).

**Acceptance criteria:** AC-C3-1, AC-C3-2, AC-C3-3, AC-C3-5, AC-COVER-1, AC-COVER-2

---

### T-MCE-06 — C-4 + C-5: specs/memory/AGENTS.md and Codex memory-ctx adapter

**Owner:** ai-engineer
**Cluster:** C-4, C-5
**Write set:**
- `repos/dadaia-workspace/specs/memory/AGENTS.md` (NEW — consumer workspace file, not lib-originated)
- `dadaia_workspace/public/runtime/codex/memory-ctx/SKILL.md` (NEW)

**Preconditions:** none

**Work (C-4):**
1. Author `specs/memory/AGENTS.md` (≤ 80 lines) with the five content sections from
   SPEC §4/C-4: read contract, write contract (cites RULE A and `sdd-spec-gate.sh`),
   atomicity contract, file manifest, generation note for `catalog.json`.
2. Verify: `dadaia specs doctor` no longer emits TREE-5 warning for this repo after file
   is created.

**Work (C-5):**
3. Create `public/runtime/codex/memory-ctx/SKILL.md` following the `design-ctx` adapter
   pattern. Must include the 5-step protocol from SPEC §4/C-5 (specs_dir resolution,
   architecture.html read+strip, tech-stack.html read+strip, catalog.json read with
   fallback, context block emission). Must state it fires before role-specific adapters.
   No `config.toml` is created or edited. The SKILL.md is auto-discovered and installed
   to `.codex/skills/memory-ctx/SKILL.md` by `_install_codex_runtime_adapters`
   (ADR-CX-001) on `dadaia public install`.

**Done criterion:**
- `specs/memory/AGENTS.md` exists, is ≤ 80 lines, contains all 5 sections.
- `public/runtime/codex/memory-ctx/SKILL.md` exists with 5-step protocol.
- `dadaia specs doctor` TREE-5 warning absent for this repo (after AGENTS.md created).

**Acceptance criteria:** AC-C4-1, AC-C4-2, AC-C4-3, AC-C4-4, AC-C4-5, AC-C5-1,
AC-C5-2, AC-C5-3, AC-C5-5, AC-COVER-6, AC-COVER-7, AC-DOC-3

**Note on write-set separation:** AGENTS.md is a consumer-workspace file (no stage/install
needed). The Codex runtime files are lib-originated (require propagation in T-MCE-09).
These two sub-tasks are bundled because their write sets are disjoint from all other Wave
A tasks and the work is small enough to keep in one task.

---

## Wave B — Depends on Wave A fully committed

---

### T-MCE-07 — C-1: ctx-inject.sh payload + strip-memory-html.py

**Owner:** ai-engineer
**Cluster:** C-1
**Write set:**
- `dadaia_workspace/public/scripts/ctx-inject.sh` (extend payload)
- `dadaia_workspace/public/scripts/strip-memory-html.py` (NEW)

**Preconditions:** T-MCE-01 `[x]`, T-MCE-04 `[x]` (catalog.json must exist for integration test)

**Work:**
1. Create `strip-memory-html.py` (~20-30 lines): Python `html.parser` (stdlib only);
   accepts a file path as argv[1]; removes `<head>`, `<style>`, Mermaid `<script>`
   blocks; writes stripped content to stdout. Must preserve all prose, heading, and
   diagram content.
2. Extend `ctx-inject.sh` after the context-name emission:
   a. Detect `$SPECS_DIR/memory/` exists; skip memory block if absent (graceful).
   b. Determine injection sentinel (OQ-1/OQ-2 working assumption: check sentinel file
      at `.dadaia/tmp/ctx-inject-fired-<SESSION_ID>` where SESSION_ID is from env; if
      fired, print context-name only and exit; otherwise create sentinel, inject full
      payload).
   c. Emit `=== workspace memory (arch + tech + catalog) ===` marker.
   d. Strip and emit `architecture.html`; strip and emit `tech-stack.html`.
   e. If `catalog.json` exists: emit it directly (JSON is already stripped). Else:
      strip and emit `product/index.html`.
   f. Emit `=== end memory bootstrap ===` marker.
3. Verify locally: `bash ctx-inject.sh` with `DADAIA_CONTEXT=dadaia-workspace` emits
   bounded markers; output contains arch/tech/catalog content; second call (sentinel
   present) emits only context name.
4. Verify token count: ~6,500–8,500 tokens (rough estimate via `wc -w` or tiktoken).

**Done criterion:** `ctx-inject.sh` emits bounded block on first call; skips on subsequent
calls; fallback to `index.html` when `catalog.json` absent; `strip-memory-html.py`
removes head/style/script and preserves prose.

**Acceptance criteria:** AC-C1-1, AC-C1-2, AC-C1-3, AC-C1-4, AC-C1-7, AC-COVER-3,
AC-TOK-1, AC-TOK-2

---

### T-MCE-08 — C-1: ctx-inject.ts first-message guard

**Owner:** ai-engineer
**Cluster:** C-1
**Write set:**
- `dadaia_workspace/public/plugins/ctx-inject.ts` (add first-message guard)

**Preconditions:** T-MCE-07 `[x]` (ctx-inject.sh must include the sentinel-based guard
so the TS plugin's call to the script inherits the guard correctly)

**Work:**
1. Add a first-message-only guard to `ctx-inject.ts` in the `chat.message` handler.
2. Guard mechanism: check `_input.messageID` if available in the plugin API; or use
   the same `.dadaia/tmp/ctx-inject-fired-<sessionID>` sentinel pattern (sessionID from
   `_input.sessionID` if available).
3. If this is the first message: call `ctx-inject.sh` (which itself handles the
   sentinel); if not, skip injection entirely in the TS layer.
4. devops-engineer confirms the available fields in `_input` (OQ-2) before T-MCE-08
   is finalized; if the OpenCode plugin API exposes `sessionID`, use it; otherwise PID.
5. Maintain fail-open pattern: any error skips injection and never breaks the chat.

**Done criterion:** In a test OpenCode session, the 7.3K payload appears on message 1
only; message 2 and beyond do not re-inject.

**Acceptance criteria:** AC-C1-5, AC-RT-2

---

## Propagation barrier — depends on Wave A + Wave B fully committed

---

### T-MCE-09 — Propagation and verification

**Owner:** devops-engineer
**Cluster:** all (lib-originated assets)
**Write set:**
- `.dadaia/agentic/manifest.json` (updated by `dadaia public stage`)
- `.claude/agents/*.md`, `.claude/skills/**`, `.codex/agents/*.toml`, `.codex/config.toml`, `.codex/skills/**`, `.opencode/agents/*.md`, `.agents/skills/**` (updated by `dadaia public install`)

**Preconditions:** T-MCE-05 `[x]`, T-MCE-06 `[x]`, T-MCE-07 `[x]`, T-MCE-08 `[x]`
(all lib-originated source changes committed)

**Work:**
1. Run: `dadaia public stage`
2. Run: `dadaia public install --target all`
3. Run: `dadaia public doctor` — must exit 0, zero drift, zero missing.
4. Confirm `ctx-inject.sh` fires and emits memory payload when `DADAIA_CONTEXT` is set:
   - Claude Code runtime: verify the hook is wired in `.claude/settings.json`.
   - OpenCode runtime: verify `ctx-inject.ts` is present in `.opencode/` projection.
   - Codex runtime: verify `memory-ctx/SKILL.md` is projected to `.codex/skills/`.
5. Confirm OQ-1: determine whether Claude Code `UserPromptSubmit` fires once per session
   or on every message. Document the finding in a brief comment commit message.
6. Confirm OQ-2: identify the session env var available to `ctx-inject.sh` and
   `ctx-inject.ts` for sentinel scoping. If none found, confirm PID-based fallback is
   acceptable.
7. Confirm OQ-3: verify `strip-memory-html.py` projected to `.dadaia/scripts/` via
   manifest. If path issue found, escalate to ai-engineer for `ctx-inject.sh` path fix.
8. Confirm OQ-4: verify `memory-ctx/SKILL.md` is projected to `.codex/skills/memory-ctx/SKILL.md`
   and that `dadaia public doctor` D-CX-6 reports no drift/missing for it (auto-discovery
   via `_install_codex_runtime_adapters`, ADR-CX-001).

**Done criterion:** `dadaia public doctor` exits 0; all three runtimes confirmed; OQ-1..4
findings documented (commit message or brief note in T-MCE-10 QA context).

**Acceptance criteria:** AC-C1-6, AC-C3-4, AC-C5-4, AC-COVER-8, AC-RT-1, AC-RT-3

---

## QA gate — depends on T-MCE-09

---

### T-MCE-10 — Acceptance gate (SPEC §13 full matrix)

**Owner:** qa-engineer
**Cluster:** all
**Write set:**
- `.dadaia/reports/dadaia-workspace/qa-engineer/<UTC>-memory-context-enforcement-v1-qa.html` (QA report)
- `.dadaia/reports/dadaia-workspace/qa-engineer/<UTC>-memory-context-enforcement-v1-qa.handoff.json` (sidecar)

**Preconditions:** T-MCE-09 `[x]` and `dadaia public doctor` exit 0

**Work:**
Define and run validation plan covering all SPEC §13 acceptance criteria:

1. **AC-COVER-1:** `grep -l "Step 0" dadaia_workspace/public/agents/*.md | wc -l` = 21.
2. **AC-COVER-2:** Spot-check all 5 P0 agents for `dadaia-workspace-spec-navigator` in
   frontmatter `skills:`.
3. **AC-COVER-3:** `bash .dadaia/scripts/ctx-inject.sh` with `DADAIA_CONTEXT` set emits
   memory payload with `=== workspace memory … ===` markers.
4. **AC-COVER-4:** `catalog.json` exists; parse as JSON; verify all 18 entries have
   required fields; all paths resolve to files.
5. **AC-COVER-5:** `dadaia specs doctor` — no CAT-1 warning.
6. **AC-COVER-6:** `specs/memory/AGENTS.md` exists.
7. **AC-COVER-7:** `.codex/skills/memory-ctx/SKILL.md` exists in projection.
8. **AC-COVER-8:** `dadaia public doctor` exits 0.
9. **AC-RT-1:** Claude Code — verify injection hook wired; manually trigger session start
   and confirm payload in context (or verify from devops-engineer evidence in T-MCE-09).
10. **AC-RT-2:** OpenCode — first message receives payload; second message does not.
    Evidence: devops-engineer T-MCE-09 confirmation + manual test.
11. **AC-RT-3:** Codex — `memory-ctx` skill present in `.codex/skills/memory-ctx/SKILL.md`;
    `dadaia public doctor` D-CX-6 reports no drift/missing for it (auto-discovered by
    `_install_codex_runtime_adapters`, ADR-CX-001; no config.toml entry required).
12. **AC-TOK-1:** Measure token count of injected payload:
    `bash .dadaia/scripts/ctx-inject.sh 2>/dev/null | wc -w` (word count proxy); convert
    to token estimate; verify range 6,500–8,500.
13. **AC-TOK-2:** Cost = (tokens / 1,000,000) × $3.00 ≤ $0.026 per session start.
14. **AC-DOC-1:** Create a fixture with a mismatched slug in catalog.json; run
    `dadaia specs doctor`; confirm CAT-1 warning names the slug.
15. **AC-DOC-2:** Remove `catalog.json` from fixture; run `dadaia specs doctor` with
    feature HTMLs present; confirm CAT-1 warning.
16. **AC-DOC-3:** Confirm `specs/memory/AGENTS.md` exists → TREE-5 absent in doctor
    output.

Emit QA report HTML + sidecar (`dadaia-handoff-emitter` protocol). Report must include
pass/fail for each AC, evidence triples (command + stdout snippet or file path).

**Done criterion:** All 16 checks pass; report emitted; sidecar valid.

**Acceptance criteria:** Full SPEC §13 matrix (AC-COVER-1..8, AC-RT-1..3, AC-TOK-1..2,
AC-DOC-1..3)

---

## Summary

| ID | Owner | Cluster | Wave | Status |
|----|-------|---------|------|--------|
| T-MCE-01 | software-engineer-python | C-2 catalog.py + tests | A | [x] |
| T-MCE-02 | software-engineer-python | C-2 doctor CAT-1 + tests | A | [x] |
| T-MCE-03 | software-engineer-python | C-2 CLI wiring + tests | A | [x] |
| T-MCE-04 | software-engineer-python | C-2 generate catalog.json | A | [x] |
| T-MCE-05 | ai-engineer | C-3 Step 0 blocks (21 personas) | A | [x] |
| T-MCE-06 | ai-engineer | C-4 AGENTS.md + C-5 memory-ctx SKILL.md | A | [x] |
| T-MCE-07 | ai-engineer | C-1 ctx-inject.sh + strip-memory-html.py | B | [x] |
| T-MCE-08 | ai-engineer | C-1 ctx-inject.ts guard | B | [x] |
| T-MCE-09 | devops-engineer | Propagation + OQ confirmation | barrier | [x] |
| T-MCE-10 | qa-engineer | Acceptance gate (SPEC §13) | qa | [x] |

**Total tasks: 10**

**Tasks by owner:**
- software-engineer-python: T-MCE-01, T-MCE-02, T-MCE-03, T-MCE-04 (4 tasks)
- ai-engineer: T-MCE-05, T-MCE-06, T-MCE-07, T-MCE-08 (4 tasks)
- devops-engineer: T-MCE-09 (1 task)
- qa-engineer: T-MCE-10 (1 task)

---

*Product Engineer — dadaia-workspace | 2026-05-31*
