# PLAN: v0.1.4.1 — agent-architecture-hardening

**Status:** Aprovado
**Release ID:** v0.1.4.1
**Owner:** product-engineer
**Created:** 2026-06-03

---

## 1. Strategy

All changes live in `dadaia_workspace/public/`. No Python application source is
touched. The release therefore avoids any risk of breaking the library's business
logic or test suite.

Work is sequenced in three waves:

- **Wave 1 (merge + gate fix):** T-HARD-00 and T-HARD-01 are the highest-risk
  items. Merge the security branch first (it is self-contained); then fix the
  gate context resolution. Both must be in before the asset chain is re-run.
- **Wave 2 (asset text fixes):** T-HARD-02 through T-HARD-06 are pure text edits
  to `public/` files. Each is independent; they may be done in parallel by the
  same implementer in sequence without conflict.
- **Wave 3 (propagation + verification):** T-HARD-11 re-runs the asset chain and
  verifies all acceptance criteria.

## 2. Layers affected

| Layer | What changes |
|-------|-------------|
| `dadaia_workspace/public/scripts/` | `sdd-spec-gate.sh` — context resolution chain + RULE F + one-[-]-warn |
| `dadaia_workspace/public/agents/` | `project-auditor.md`, `design-specialist.md`, `devops-engineer.md`, `ai-engineer.md` |
| `dadaia_workspace/public/skills/` | `dadaia-handoff-emitter.md`, `dadaia-workspace-spec-navigator.md`, `dadaia-step0-memory-bootstrap.md`, `dadaia-task-manager.md` |
| `dadaia_workspace/public/rules/` | `workspace-protocol.md` |
| `dadaia_workspace/public/data/` | `AGENTS.md` |
| Git | Merge `hardening/panel-auth-review` |

## 3. Execution order

```
T-HARD-00 (merge branch)
    ↓
T-HARD-01 (gate context-resolution fix)
    ↓
T-HARD-02 (purge activate/primary_context refs)
    ↓
T-HARD-03 (handoff-emitter schema fix)
    ↓
T-HARD-04 (broken refs + lang uniformity)
    ↓
T-HARD-05 (gate RULE F + one-[-]-warn)
    ↓
T-HARD-06 (de-bloat + write_allowlist tighten)
    ↓
T-HARD-11 (propagation + full verification)
```

Tasks T-HARD-02 through T-HARD-06 are sequential in ownership but have disjoint
write sets (different files). A single implementer may work through them in order
without collision.

## 4. Technical risks

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Gate fix breaks existing tests for RULE C | Medium | Run unit tests for gate after T-HARD-01 before Wave 2 |
| Merge conflict on `hardening/panel-auth-review` | Low | Branch was kept clean; rebase if needed |
| Broken skill refs in frontmatter cause doctor errors | Low | T-HARD-04 fixes them; doctor run in T-HARD-11 catches remainder |
| Asset propagation drift after text edits | Medium | T-HARD-11 forces `--force` reinstall + doctor exit 0 |

## 5. Design notes

### Gate fix (T-HARD-01)

The `sdd-spec-gate.sh` PRIMARY_SPECS resolution block (lines ~66-88) currently
reads only `primary_context.json`. The replacement reads in this order:

1. `DADAIA_CONTEXT` env var (already present — keep as-is).
2. `spec_contexts.json` — Python one-shot: load JSON, find entry with
   `state == "ALIVE"` and `is_primary == true`; fall back to first `ALIVE`
   entry; extract `specs_dir` or derive from `slug`.
3. `DADAIA_SESSION_ID` session file — if set, read
   `.dadaia/sessions/$DADAIA_SESSION_ID.json`, extract `context`, derive
   `$WS/repos/<context>/specs`.
4. Fail-open (unchanged behavior; add clearer warning log).

The existing `DADAIA_CONTEXT` branch already sets both `PRIMARY_SLUG` and
`PRIMARY_SPECS` correctly. The new steps fill in after it.

### Handoff skill fix (T-HARD-03)

The schema pattern `^[a-f0-9]{64}$` is the authority. The skill must match it.
Changes:
- Step 1 output: "This is the value for `artifact.content_hash`" (remove prefix
  instruction).
- Table row: `artifact.content_hash` → `string` → "SHA-256 hex digest (64
  lowercase hex characters, no prefix)".
- All example JSON: replace `"sha256:<hex>"` with a bare 64-char hex string.
- Guardrails section: delete the line "Never omit the `sha256:` prefix from
  `artifact.content_hash`."

### Language uniformity (T-HARD-04)

`project-auditor.md` contains a freestanding `## Scope and forbidden actions`
block followed by a Portuguese `# project-auditor-scope` embedded rule. This
embedded rule must be translated to English inline or merged into the existing
`## Hard rules` and `## Scope and forbidden actions` sections. The Portuguese
heading `## Domínio`, `## Permitido`, `## Proibido`, `## Output mandatório`, and
`## Score floor` become English equivalents or are collapsed into existing
sections.

`design-specialist.md` may contain Portuguese blocks from the same pattern.
Audit the body and convert any Portuguese prose or section headings.

### RULE F tmp pre-check (T-HARD-05)

Insert before the IS_PROD block:

```bash
# RULE F — tmp path fast-allow (T-HARD-05)
case "$FPATH" in
    "$WS/.dadaia/tmp/"*)
        _log "allowed — tmp path fast-allow: $FPATH"
        exit 0
        ;;
esac
```

### One-[-]-warn (T-HARD-05)

After the ACTIVE TASKS.md path is resolved (after the `ACTIVE=""` block), add:

```bash
if [ -n "$ACTIVE" ]; then
    _COUNT=$(grep -cE "$GREP_PAT" "$ACTIVE" 2>/dev/null || echo 0)
    if [ "$_COUNT" -gt 1 ]; then
        _HAS_PARALLEL=$(grep -c 'parallel_tasks:' "$ACTIVE" 2>/dev/null || echo 0)
        if [ "$_HAS_PARALLEL" = "0" ]; then
            _log "WARN: multiple [-] markers ($_COUNT) in $ACTIVE without parallel_tasks declaration"
        fi
    fi
fi
```

## 6. Validation plan

T-HARD-11 runs these commands in order. Each must exit 0:

```bash
# After git merge (T-HARD-00)
git log --oneline -5

# After gate fix (T-HARD-01)
poetry run pytest -q -m "unit and not slow" tests/unit
poetry run pytest -q tests/unit/features/specs/  # SDD gate unit tests

# After all Wave 2 tasks
dadaia public stage
dadaia public install --target all --force
dadaia public doctor

# Full suite
poetry run pytest -q -m "unit and not slow" tests/unit
dadaia specs doctor
```

Schema round-trip check (AC-HANDOFF-02):

```bash
echo '{"schema_version":"handoff-v1.1","agent":"test","context":"dadaia-workspace",
  "produced_at":"2026-06-03T12:00:00Z","scope":"test","metrics":{},
  "artifact":{"type":"other","content_hash":"'$(python3 -c "print('a'*64)")'"}}'  \
  | dadaia reports validate /dev/stdin
```
