# PLAN: v0.1.4.4 — workspace-root-sanitization

**Status:** Aprovado
**Release ID:** v0.1.4.4
**Owner:** product-engineer
**Created:** 2026-06-04

> Retro PLAN authored at CLOSURE to close the structural gap left when the
> original plan was not written before implementation began. The plan describes
> the realized approach; no implementation changes follow from it.

---

## 1. Strategy

Eliminate workspace-root pollution through four coordinated moves:

1. **Law first** — codify the root whitelist in `AGENTS.md` and the
   `tmp-file-guardrail` rule so every agent knows the law before the hook
   enforces it.
2. **Hook enforcement** — a deterministic PreToolUse hook (`root-whitelist-gate.sh`)
   blocks non-whitelisted root writes at the agent boundary; operator-tagged
   files in `root_exceptions.txt` bypass the block.
3. **Relocate and redirect** — move existing non-conforming artifacts to
   canonical `.dadaia/<subdir>` homes; redirect ruff and coverage caches off
   root via `pyproject.toml` config.
4. **Doctor visibility** — four additive `ROOT-*` checks in `dadaia doctor`
   surface violations deterministically; actionable fix hints per invariant.

No files outside the four SANITIZE tasks are touched. Report/retention surfaces
remain in v0.1.4.3.

---

## 2. Execution Order

```text
T-SANI-03 -> T-SANI-01 -> T-SANI-02 -> T-SANI-05 -> T-SANI-06
```

T-SANI-03 runs first because redirecting caches removes regenerated noise that
would otherwise appear as violations when T-SANI-02 audits the root. T-SANI-01
(law + hook) and T-SANI-02 (relocation) are independent after T-SANI-03 but
sequenced for safety. T-SANI-05 (doctor) comes after the surfaces it checks are
clean. T-SANI-06 (QA) is the terminal gate.

---

## 3. Design

### Root whitelist law

The canonical law is declared in `public/data/AGENTS.md` (fan-out source for
all consumer `AGENTS.md` files) and mirrored exactly in
`public/rules/tmp-file-guardrail.md`:

```
Allowed at workspace root:
  Directories: .agents/  .claude/  .codex/  .dadaia/  .opencode/  repos/
  File:        AGENTS.md
  Operator exceptions: any file/dir created by the human operator; never auto-deleted
```

`CLAUDE.md`, `opencode.json`, `.mcp.json`, and `scripts/` are removed from the
old whitelist because they do not belong there as canonical entries — tool-config
research (T-SANI-02) may promote them to `root_exceptions.txt` if relocation is
impossible.

### Root-whitelist hook

New script `public/scripts/root-whitelist-gate.sh`:

- Reads `tool_input.file_path` from the PreToolUse JSON payload.
- If the resolved path is directly under workspace root (depth 1) and not in
  the whitelist, emits `{"decision":"block","reason":"[ROOT-WHITELIST] …"}`.
- Reads `.dadaia/states/root_exceptions.txt` for operator-declared exceptions;
  entries matching the basename bypass the block.
- Wired into `.claude/settings.json` (PreToolUse) and `.codex/hooks.json` via
  `dadaia public install --target all`.

### Cache redirect (T-SANI-03)

`pyproject.toml` changes:
- `[tool.ruff]` — add `cache-dir = ".dadaia/cache/ruff"`.
- `[tool.coverage.run]` — add `data_file = ".dadaia/cache/coverage/.coverage"`.

Existing pytest (`-p no:cacheprovider`) and mypy (`cache_dir=/dev/null`) config
requires no change.

### Relocation table (T-SANI-02)

| Root entry | Action |
|---|---|
| `scripts/` | Move to `.dadaia/scripts/`; update any internal references |
| Regenerated caches (`.ruff_cache`, `.coverage`, `.pytest_cache`, `.mypy_cache`, `.playwright-mcp`, `.hypothesis`) | Delete |
| `CLAUDE.md` | Keep — Claude Code requires root; add to `root_exceptions.txt` |
| `.mcp.json` | Keep — Claude Code MCP discovery requires root; add to `root_exceptions.txt` |
| `opencode.json` | Keep — opencode requires root; add to `root_exceptions.txt` |
| `prompt.md`, screenshots | Keep — operator-created; covered by operator exception clause |

Research outcome stored in `specs/releases/v0.1.4.4/RESEARCH-configs.md`.

### Doctor invariants (T-SANI-05)

Four additive checks, none colliding with v0.1.4.3 `T-RET-05`:

| Check | What it asserts |
|---|---|
| ROOT-1 | Root contains only whitelisted dirs/files plus entries in `root_exceptions.txt` |
| ROOT-2 | No forbidden caches/outputs at root (`.ruff_cache`, `.coverage`, `.mypy_cache`, `.pytest_cache`, `.playwright-mcp`) |
| ROOT-3 | Tool configs that must stay at root are listed in `root_exceptions.txt` |
| ROOT-4 | `.dadaia/` contains only canonical top-level subdirs |

Each check emits an actionable fix hint on failure.

---

## 4. Implementation Surfaces

Area | Owner | Files
---|---|---
Root law + rule + hook | ai-engineer (T-SANI-01) | `public/data/AGENTS.md`, `public/rules/tmp-file-guardrail.md`, `public/scripts/root-whitelist-gate.sh`, `.claude/settings.json`, `.codex/hooks.json`
Cache redirect | software-engineer-python (T-SANI-03) | `pyproject.toml`
Root relocation + research | software-engineer-python (T-SANI-02) | workspace root entries, `.dadaia/scripts/`, `.dadaia/states/root_exceptions.txt`, `specs/releases/v0.1.4.4/RESEARCH-configs.md`
Doctor invariants | software-engineer-python (T-SANI-05) | `dadaia_workspace/features/specs/doctor.py` or `dadaia_workspace/cli/commands/doctor.py`, unit tests
QA verification | qa-engineer (T-SANI-06) | `.dadaia/reports/**`, `.dadaia/handoff/**`

---

## 5. Validation

```bash
# Tool cache redirect
ruff check .            # must not create .ruff_cache at root
pytest --cov .          # must not create .coverage at root

# Root cleanliness
dadaia doctor           # ROOT-1..4 must pass (exit 0, no ROOT-* findings)

# Full suite
pytest -q -p no:cacheprovider   # 2143 passed, 0 failed

# Hook live test
# Create a non-whitelisted file at root → hook blocks; create under .dadaia/tmp/ → hook allows
```

---

## 6. Risk and Mitigations

Risk | Mitigation
---|---
Hook too aggressive — blocks legitimate operator files | `root_exceptions.txt` provides the operator escape hatch; hook reads it before blocking
Research finds a tool that can be relocated | Relocate silently; if not, document in `RESEARCH-configs.md` and add to exceptions
T-SANI-05 doctor checks collide with v0.1.4.3 T-RET-05 | ROOT-* checks are additive; they check root paths, not report paths — orthogonal surfaces
`--force` requirement for propagation | SPEC forbids `--force`; standard `dadaia public install --target all` is sufficient for new hook/rule additions
