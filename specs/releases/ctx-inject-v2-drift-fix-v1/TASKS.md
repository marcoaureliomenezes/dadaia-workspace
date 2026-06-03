# TASKS: ctx-inject-v2-drift-fix-v1

**Status:** Aprovado
**Release ID:** ctx-inject-v2-drift-fix-v1
**Owner:** product-engineer
**Created:** 2026-06-02

---

## Execution order

```
T-CIV-01 → T-CIV-02 → T-CIV-03 → T-CIV-04
```

T-CIV-01 and T-CIV-02 are sequentially ordered but may be combined into a single commit
by the implementer (disjoint files, same owner). T-CIV-03 must not start until both
T-CIV-01 and T-CIV-02 are `[x]`. T-CIV-04 must not start until T-CIV-03 is `[x]`.

Maximum one `[-]` at a time.

---

## Tasks

### T-CIV-01 — Fix ctx-inject.sh: remove dead branch + rewrite message

- **ID:** T-CIV-01
- **Status:** [x]
- **Owner:** ai-engineer
- **Target file:** `dadaia_workspace/public/scripts/ctx-inject.sh`
- **Preconditions:** SPEC.md and PLAN.md have `**Status:** Aprovado`; ACTIVE.md phase = `IMPLEMENTATION`

**Work:**
1. Delete the `STATE_FILE` variable declaration (line 9):
   `STATE_FILE="$WORKSPACE_ROOT/.dadaia/states/primary_context.json"`
2. Delete the entire `elif [ -f "$STATE_FILE" ]; then ... fi` block (the block that falls
   through when `$DADAIA_CONTEXT` is unset and attempts to read `primary_context.json`).
3. Replace the deleted `elif ... else ... fi` with a plain `else ... fi` that emits the
   correct v2 guidance message:
   - First line: `[context: none] — no context bound.`
   - Second line: reference to `eval $(.dadaia/.venv/bin/dadaia context bind <name> --mode read)`
   - Third line: reminder to export `DADAIA_CONTEXT` in the shell that launches the agent runtime.
4. Verify no occurrence of `context use` or `STATE_FILE` remains in the file.

**Done criterion:**
- `grep "context use" dadaia_workspace/public/scripts/ctx-inject.sh` returns empty
- `grep "STATE_FILE" dadaia_workspace/public/scripts/ctx-inject.sh` returns empty
- `grep "context bind" dadaia_workspace/public/scripts/ctx-inject.sh` returns the new guidance line
- Script runs without syntax error: `bash -n dadaia_workspace/public/scripts/ctx-inject.sh`

**Commit message:** `fix(ctx-inject): remove dead primary_context.json branch; rewrite v2 guidance (BUG 1+2+3)`

---

### T-CIV-02 — Fix SKILL.md: replace stale `context use` verb

- **ID:** T-CIV-02
- **Status:** [x]
- **Owner:** ai-engineer
- **Target file:** `dadaia_workspace/public/skills/dadaia-workspace-manager/SKILL.md`
- **Preconditions:** T-CIV-01 is `[x]`

**Work:**
In the `### Context management` CLI reference block, replace the stale entry:
```
dadaia context use <name>                    # eval $(dadaia context use <name>) — session isolation
```
with the correct v2 form (preserving the surrounding code fence):
```
eval $(.dadaia/.venv/bin/dadaia context bind <name> --mode read)   # bind context; exports DADAIA_CONTEXT into launching shell
```

**Done criterion:**
- `grep "context use" dadaia_workspace/public/skills/dadaia-workspace-manager/SKILL.md` returns empty
- `grep "context bind" dadaia_workspace/public/skills/dadaia-workspace-manager/SKILL.md` returns the new line
- File is valid Markdown (code block not broken)

**Commit message:** `fix(skill): replace removed 'context use' with 'context bind' in workspace-manager SKILL.md (BUG 4)`

---

### T-CIV-03 — Propagate: stage + install + doctor

- **ID:** T-CIV-03
- **Status:** [ ]
- **Owner:** devops-engineer
- **Target subsystem:** asset pipeline (`.dadaia/agentic/`, `.dadaia/scripts/`, `.claude/`, `.codex/`, `.opencode/`)
- **Preconditions:** T-CIV-01 and T-CIV-02 are both `[x]`

**Work:**
```bash
.dadaia/.venv/bin/dadaia public stage
.dadaia/.venv/bin/dadaia public install --target all
.dadaia/.venv/bin/dadaia public doctor
```

If `public doctor` reports `[drift]` for the two edited files, re-run install with
`--force` (devops-engineer is authorized):
```bash
.dadaia/.venv/bin/dadaia public install --force --target all
.dadaia/.venv/bin/dadaia public doctor   # must exit 0
```

After doctor exits 0, spot-check the projection:
```bash
grep "context use"  .dadaia/scripts/ctx-inject.sh   # must return empty
grep "STATE_FILE"   .dadaia/scripts/ctx-inject.sh   # must return empty
grep "context bind" .dadaia/scripts/ctx-inject.sh   # must return the new guidance line
```

**Done criterion:**
- `dadaia public doctor` exits 0
- All three spot-check greps return expected results

**Commit message:** `chore(propagate): stage + install + doctor after ctx-inject/SKILL.md v2 fixes`

---

### T-CIV-04 — QA gate: verify AC matrix

- **ID:** T-CIV-04
- **Status:** [ ]
- **Owner:** qa-engineer
- **Target subsystem:** source files + projection + Python pipeline
- **Preconditions:** T-CIV-03 is `[x]`

**Work:** Verify each acceptance criterion from SPEC.md §7.

| AC | Command | Expected evidence |
|----|---------|------------------|
| AC-1 | `grep "context use" dadaia_workspace/public/scripts/ctx-inject.sh` | Empty output |
| AC-2 | `grep "STATE_FILE" dadaia_workspace/public/scripts/ctx-inject.sh` | Empty output |
| AC-3 | `grep "context bind" dadaia_workspace/public/scripts/ctx-inject.sh` | Line containing `context bind <name> --mode read` and `.dadaia/.venv` hint |
| AC-4 | `grep "context bind" dadaia_workspace/public/skills/dadaia-workspace-manager/SKILL.md` | Line containing correct v2 form |
| AC-5 | terminal output of T-CIV-03 stage+install | No errors |
| AC-6 | terminal output of T-CIV-03 doctor | Exit 0 |
| AC-7 | T-CIV-03 spot-check greps on `.dadaia/scripts/ctx-inject.sh` | Matches source |
| AC-8 | `ruff check . && ruff format --check . && mypy dadaia_workspace` | Exit 0 |
| AC-9 | `pytest --tb=short -q` | No regressions; test count unchanged from last known green run |

Emit a QA handoff report at:
`.dadaia/reports/dadaia-workspace/qa-engineer/<UTC>-ctx-inject-v2-drift-fix-v1-qa.html`

**Done criterion:**
- All AC-1 through AC-9 pass
- QA report emitted with `next_handoff.agent = "product-engineer"` and verdict

**Commit message:** `test(qa): AC matrix ctx-inject-v2-drift-fix-v1 — all green`
