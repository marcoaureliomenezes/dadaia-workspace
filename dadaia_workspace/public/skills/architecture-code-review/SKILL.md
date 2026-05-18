---
name: architecture-code-review
description: >
  Reference for code-reviewer agent. Defines the 6-axis review checklist
  (architecture, patterns, tests, security smells, perf smells, dead code),
  OOP/SOLID violation patterns, complexity heuristics, and report templates.
applyTo: ".dadaia/reports/**"
---

# architecture-code-review — PR/Branch Review Reference

## 6-Axis Review Checklist

Score each axis: PASS / WARN / FAIL. A single FAIL blocks merge approval.
WARN is advisory — reviewer documents the risk and recommended fix.

### Axis 1 — Architecture Alignment

Verify the change is consistent with `specs/memory/architecture.html`.

- [ ] New module/package matches the declared layer (domain, infra, interface)?
- [ ] No cross-layer import that skips a layer boundary (e.g., interface → domain bypassing application)?
- [ ] Public API surface matches what `architecture.html` declares for this component?
- [ ] No new external dependency without an ADR or software-architect approval?
- [ ] Hexagonal/Clean boundaries respected? (ports are interfaces, adapters are in infra layer)

### Axis 2 — Pattern Correctness

- [ ] Domain objects are pure (no I/O, no framework imports)?
- [ ] Repository/Service/Factory responsibilities clearly separated (no God objects)?
- [ ] No Singleton holding mutable state that affects test isolation?
- [ ] Observer/event patterns do not leak subscriptions (unsubscribe present)?
- [ ] Command/Query separation observed (methods either mutate or return, not both)?
- [ ] Factory methods do not embed business logic; logic belongs in domain?

### Axis 3 — Test Sufficiency

- [ ] Every new public function/method has at least one unit test?
- [ ] Happy-path AND at least one error-path tested per non-trivial function?
- [ ] Tests use fakes/stubs for external I/O, not real network/DB calls?
- [ ] No test that only asserts `assert True` or trivially passes?
- [ ] Test file names mirror source file names (`src/foo.py` → `tests/test_foo.py`)?
- [ ] `mypy --strict` passes (Python)? TypeScript `tsc --strict` passes (TS)?
- [ ] Code coverage does not regress below the project baseline?

### Axis 4 — Security Smells

Flag any of the following as FAIL; escalate to `security-reviewer` for deeper audit:

- [ ] No hardcoded secret, token, API key, or password in diff?
- [ ] No `eval()`, `exec()`, `subprocess.run(shell=True)` with user-supplied input?
- [ ] No direct SQL string concatenation (parameterized queries only)?
- [ ] No open redirect (user-controlled URL passed directly to `redirect()`)?
- [ ] No verbose error response that leaks stack trace or internal paths to users?
- [ ] `input()` or equivalent sanitized before use in any downstream operation?

### Axis 5 — Performance Smells

- [ ] No N+1 query pattern (loop issuing individual DB queries)?
- [ ] No unbounded in-memory collection build (`list(queryset.all())`)?
- [ ] Expensive operations (HTTP calls, heavy compute) not on the hot path without caching?
- [ ] No busy-wait loop (`while True: sleep(0.001)`)?
- [ ] New background tasks have error handling and do not silently drop failures?

### Axis 6 — Dead-Code Drift

- [ ] No commented-out blocks of production code longer than 5 lines?
- [ ] No imports that are unused per linter (`ruff`, `eslint`)?
- [ ] No exported symbol that has zero callers in the repo?
- [ ] No feature-flag condition with the flag permanently `True`/`False`?

---

## OOP/SOLID Violation Catalog

Each entry includes a code-smell snippet and the correct pattern.

### S — Single Responsibility Principle (SRP)

Smell: one class does data access AND business logic AND formatting.
```python
# BAD
class UserService:
    def get_user(self, uid): return db.query(f"SELECT * FROM users WHERE id={uid}")
    def validate_email(self, email): return "@" in email
    def format_json(self, user): return json.dumps(user.__dict__)
```
Fix: split into `UserRepository`, `UserValidator`, `UserSerializer`.

### O — Open/Closed Principle (OCP)

Smell: `if/elif` chain that must be edited to add a new type.
```python
# BAD
def calculate(op, a, b):
    if op == "add": return a + b
    elif op == "mul": return a * b
    # adding "div" requires editing this function
```
Fix: strategy pattern — map operation names to callables or use polymorphism.

### L — Liskov Substitution Principle (LSP)

Smell: subclass raises `NotImplementedError` for methods the base class declares.
```python
# BAD
class ReadOnlyRepo(BaseRepo):
    def save(self, entity): raise NotImplementedError
```
Fix: narrow the interface; `ReadOnlyRepo` should implement a `ReadableRepo` protocol, not `BaseRepo`.

### I — Interface Segregation Principle (ISP)

Smell: large Protocol/ABC with 10+ methods; implementors stub most with `pass`.
Fix: split into focused protocols (`Readable`, `Writable`, `Searchable`).

### D — Dependency Inversion Principle (DIP)

Smell: high-level module imports low-level concrete class directly.
```python
# BAD
from infrastructure.postgres_repo import PostgresUserRepo  # in domain layer
class UserService:
    def __init__(self): self.repo = PostgresUserRepo()
```
Fix: inject a `UserRepository` Protocol; concrete binding happens in the composition root.

---

## Complexity Heuristics

| Metric | Threshold | Action if exceeded |
|---|---|---|
| Cyclomatic complexity | > 10 per function | WARN; > 15 = FAIL |
| Cognitive complexity | > 15 per function | WARN; > 20 = FAIL |
| Nesting depth | > 4 levels | WARN; > 6 = FAIL |
| Function length | > 50 lines | WARN; > 80 = FAIL |
| Class length | > 200 lines | WARN |
| Parameter count | > 5 per function | WARN; use dataclass/DTO |

Measure with:
```bash
radon cc -s <file.py>        # cyclomatic complexity
radon mi -s <file.py>        # maintainability index
lizard <file.py>             # cognitive complexity
```

---

## Design-Pattern Misuse Catalog

### Singleton Abuse

Symptom: `_instance` class variable holding mutable global state; tests interfere
with each other because the singleton carries state across test cases.
Fix: dependency injection; pass the shared resource as a constructor argument.

### Observer / Event Leak

Symptom: listeners registered in `__init__` with no corresponding unsubscribe;
object graph grows unboundedly in long-running processes.
Fix: return an unsubscribe handle; use `weakref` listeners; call cleanup in `__del__`
or a context manager.

### Factory Bloat

Symptom: `create_X(type_flag)` factory with 200+ lines and `if/elif` per type.
Fix: registry pattern — `_registry: dict[str, type]` populated via decorators
or explicit registration calls.

### Anemic Domain Model

Symptom: domain objects are pure data bags (only `__init__` + getters); all logic
lives in service classes.
Fix: move invariant-enforcing logic into the domain object itself; services
orchestrate, domain objects enforce rules.

### Premature Abstraction

Symptom: interface with exactly one implementation; indirection adds cognitive
load with no testability benefit.
Fix: keep the concrete class; introduce a Protocol only when a second
implementation is imminent or when testing requires a fake.

---

## `gh` CLI Cookbook

```bash
# View PR metadata (title, labels, reviewers, CI status)
gh pr view <PR-number> --repo <owner/repo>

# Show the full diff of the PR
gh pr diff <PR-number> --repo <owner/repo>

# List recent workflow runs for the PR's branch
gh run list --repo <owner/repo> --branch <branch-name> --limit 5

# Stream logs for a specific run (useful for test failures)
gh run view <run-id> --repo <owner/repo> --log

# Check failed jobs only
gh run view <run-id> --repo <owner/repo> --log-failed

# List checks on a PR
gh pr checks <PR-number> --repo <owner/repo>

# Approve a PR after review
gh pr review <PR-number> --approve --body "LGTM — architecture OK, tests green."

# Request changes on a PR
gh pr review <PR-number> --request-changes --body "<finding summary>"
```

---

## Output Template

Every code review report must include the following sections. Emit as HTML.

### Executive Summary

| Verdict | Justification |
|---|---|
| APPROVE / REQUEST-CHANGES / COMMENT | One-sentence rationale |

Axis scores:

| Axis | Score |
|---|---|
| Architecture Alignment | PASS / WARN / FAIL |
| Pattern Correctness | PASS / WARN / FAIL |
| Test Sufficiency | PASS / WARN / FAIL |
| Security Smells | PASS / WARN / FAIL |
| Performance Smells | PASS / WARN / FAIL |
| Dead-Code Drift | PASS / WARN / FAIL |

### Findings

Each finding entry:

```
Severity: [CRITICAL | HIGH | MEDIUM | LOW | INFO]
Axis: <axis name>
File: <path>:<line>
Description: <what is wrong>
Evidence: <code snippet — REDACT secrets>
Recommendation: <specific fix>
CWE: <CWE-ID if security-relevant>
```

Severity badges: CRITICAL = red, HIGH = orange, MEDIUM = yellow, LOW = blue, INFO = grey.

### Test Sufficiency Report

- Functions/methods added: N
- Functions/methods with tests: M
- Coverage delta: +X% / -Y%
- Missing test cases: list file:function pairs

### CI Status

```
Workflow: <name>
Run ID: <id>
Status: passed / failed / pending
Failed steps: <list>
```

### Recommendation

Final verdict: one of `APPROVE`, `REQUEST-CHANGES`, `COMMENT`.
Block merge until all FAIL findings are resolved.
WARN findings may be merged with documented trade-off acceptance by the author.
