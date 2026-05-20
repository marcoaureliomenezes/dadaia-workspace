# qa-engineer — Report Templates

This file is referenced from `dadaia_workspace/public/agents/qa-engineer.md`.

---

## Report

After completing E2E validation or a test quality audit, write a report to:
```
.dadaia/reports/<context-name>/qa-engineer/<YYYY-MM-DDTHHMMSSZ>-<type>.md
```

Where `<type>` is `e2e-validation`, `deploy-validation`, or `test-quality-audit`.

Discover `<context-name>` via: `dadaia context show --json | python3 -c "import sys,json; print(json.load(sys.stdin)['name'])"`

### Deploy validation report format:
```markdown
# Deploy Validation — <context-name>
> Date: <ISO 8601>
> Deploy: <branch>@<commit>
> Environment: <staging|production|URL>

## Result: PASS | FAIL

## E2E Scenario Results
| Scenario | Result | Notes |
|---|---|---|
| [name] | ✅ PASS | |
| [name] | ❌ FAIL | [reproduction steps] |

## Blocking issues
[Any failures that block the task from closing]
```

### Test quality audit report format:
```markdown
# Test Quality Audit — <context-name>
> Date: <ISO 8601>

## Test count by layer
| Layer | Count | Expected | Status |
|---|---|---|---|
| Unit | N | N | ✅ / ⚠️ |
| Integration | N | N | ✅ / ⚠️ |
| E2E | N | N | ✅ / ⚠️ |

## Issues found
[Slope tests, mock inflation, volume padding — file:line for each]

## Required actions
[What must be fixed before next release]
```
