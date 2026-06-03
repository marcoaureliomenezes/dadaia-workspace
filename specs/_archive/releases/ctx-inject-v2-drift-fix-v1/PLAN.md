# PLAN: ctx-inject-v2-drift-fix-v1

**Status:** Aprovado
**Release ID:** ctx-inject-v2-drift-fix-v1
**Owner:** product-engineer
**Created:** 2026-06-02

---

## 1. Strategy

Two lib-originated asset files require content-only edits. No Python source changes.
Execution is strictly sequential (source → propagation → verification) because public
doctor drift is expected between the source edit and the propagation step, and the
verification task depends on propagation being complete.

The propagation step is mandatory and non-skippable: `dadaia public stage &&
dadaia public install --target all` followed by `dadaia public doctor` exit 0.

**LIB-GUARDRAIL enforced throughout:** edit only `public/` source files. Never touch
`.dadaia/scripts/`, `.dadaia/agentic/`, `.claude/`, `.codex/`, `.opencode/` directly.

---

## 2. Layers affected

| Layer | Files touched | Owner |
|-------|--------------|-------|
| Public asset — scripts | `dadaia_workspace/public/scripts/ctx-inject.sh` | ai-engineer |
| Public asset — skills | `dadaia_workspace/public/skills/dadaia-workspace-manager/SKILL.md` | ai-engineer |
| Asset propagation | stage + install + doctor | devops-engineer |
| Verification | spot-check projection + AC matrix | qa-engineer |

---

## 3. Execution order

```
T-CIV-01 (ai-engineer)   fix ctx-inject.sh (BUG 1 + BUG 2 + BUG 3 message)
    ↓
T-CIV-02 (ai-engineer)   fix SKILL.md (BUG 4)
    ↓
T-CIV-03 (devops-engineer)   propagate: stage + install + doctor exit 0
    ↓
T-CIV-04 (qa-engineer)   verify AC matrix
```

T-CIV-01 and T-CIV-02 may be done in the same commit (both are public/ source edits,
disjoint files, both owned by ai-engineer). They are listed separately to keep the task
granularity clean, but the implementer may combine them if preferred — the done criterion
for each is file-level independent.

---

## 4. Technical details

### T-CIV-01 — ctx-inject.sh edits

Three changes in one file:

**a) Remove `STATE_FILE` variable (line 9):**
Delete the line:
```bash
STATE_FILE="$WORKSPACE_ROOT/.dadaia/states/primary_context.json"
```

**b) Remove dead `elif` block (lines 23–34 approximately):**
Delete:
```bash
elif [ -f "$STATE_FILE" ]; then
    CONTEXT_NAME=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('name',''))" 2>/dev/null)
    if [ -z "$CONTEXT_NAME" ]; then
        echo "[context: none] — run: eval \$(dadaia context use <name>)"
        exit 0
    fi
    SPECS_DIR="$WORKSPACE_ROOT/repos/$CONTEXT_NAME/specs"
    echo "[$CONTEXT_NAME]"
else
    echo "[context: none] — run: eval \$(dadaia context use <name>)"
    exit 0
fi
```
Replace with only:
```bash
else
    echo "[context: none] — no context bound."
    echo "  To bind a context: eval \$(.dadaia/.venv/bin/dadaia context bind <name> --mode read)"
    echo "  Then export DADAIA_CONTEXT in the shell that launches your agent runtime."
    exit 0
fi
```

**c) Fix the surviving `context use` reference (inside the `elif` body that is now being
deleted) — this is already handled by removing the block above.** Verify no residual
`context use` string remains in the file after the edit.

**Result after edit:** the `if/else` structure becomes:
```bash
if [ -n "$DADAIA_CONTEXT" ]; then
    ...existing DADAIA_CONTEXT branch (unchanged)...
else
    echo "[context: none] — no context bound."
    echo "  To bind a context: eval \$(.dadaia/.venv/bin/dadaia context bind <name> --mode read)"
    echo "  Then export DADAIA_CONTEXT in the shell that launches your agent runtime."
    exit 0
fi
```

### T-CIV-02 — SKILL.md edit

In the `### Context management` CLI reference table, replace:
```
dadaia context use <name>                    # eval $(dadaia context use <name>) — session isolation
```
with:
```
eval $(.dadaia/.venv/bin/dadaia context bind <name> --mode read)   # bind context; exports DADAIA_CONTEXT into launching shell
```

Note: the SKILL.md format uses a fenced code block for CLI commands, not a table row.
The replacement must preserve the surrounding code block formatting.

### T-CIV-03 — Propagation

```bash
cd /path/to/workspace
.dadaia/.venv/bin/dadaia public stage
.dadaia/.venv/bin/dadaia public install --target all
.dadaia/.venv/bin/dadaia public doctor
```

Doctor must exit 0. If drift is reported for the two edited files, that is a sign
`install` did not complete correctly — re-run with `--force` (devops-engineer is
authorized to use `--force`).

After propagation, spot-check:
```bash
grep "context use" .dadaia/scripts/ctx-inject.sh   # must return nothing
grep "STATE_FILE" .dadaia/scripts/ctx-inject.sh    # must return nothing
grep "context bind" .dadaia/scripts/ctx-inject.sh  # must return the new line
```

### T-CIV-04 — QA verification

Run AC-1 through AC-9 as listed in SPEC.md §7. Evidence for each AC:
- AC-1..4: `grep` output (empty or matching expected string)
- AC-5..7: terminal output of `dadaia public stage`, `install`, `doctor`, and spot-check greps
- AC-8: `ruff check . && mypy dadaia_workspace` output
- AC-9: `pytest --tb=short -q` output (count should be unchanged)

---

## 5. Technical risks

| Risk | Detail | Mitigation |
|------|--------|-----------|
| Bash quoting in `echo` strings | Dollar signs in the new message must be escaped with `\$` | Implementer must verify the script runs without interpolating `<name>` literally |
| SKILL.md code block formatting | The replacement line is longer than the original; surrounding context must remain valid Markdown | Implementer reads surrounding lines before editing |
| `public doctor` drift window | Between T-CIV-01/02 and T-CIV-03 the source and staging are out of sync | Documented expectation; T-CIV-03 closes it |

---

## 6. Validation plan

All validations are in TASKS.md T-CIV-04. Summary:

- Source-level: grep confirms no `context use` or `STATE_FILE` in source files
- Propagation-level: `public doctor` exits 0; projection file matches source
- Pipeline-level: ruff + mypy pass (no regressions from Bash-only changes)
- Test-level: pytest count unchanged (no Python touched)
