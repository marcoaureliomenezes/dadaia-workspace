---
name: architect-code-audit
description: >
  Structured 5-phase protocol for deep implementation auditing. Covers dead code detection, stale
  layer identification, architecture deviation analysis, OOP/SOLID violations, and design pattern
  misuse. Produces a structured report section appended to the standard review-{timestamp}.md.
  Invoked by the software-architect in REVIEW mode after loading architecture docs.
---

# Code Audit — 5-Phase Protocol

This skill provides the step-by-step procedure for a deep implementation audit. Always complete all
5 phases before writing the report. Never skim — incomplete analysis produces false confidence.

---

## Phase 0 — Context Loading

Before any code analysis, establish the architectural contract:

```bash
# Discover active context
dadaia context show --json

# Load these documents in order:
# 1. specs/constitution.md          — hard constraints and project philosophy
# 2. specs/memory/architecture.md   — layer diagram, module ownership, dependency rules
# 3. specs/foundation/SPEC.md       — foundational layer contract
# 4. specs/SPEC.md                  — product-level contract
```

Then map the implementation surface:
```bash
# Full module map
find repos/<slug> -name "*.py" | sort

# Top-level package structure
find repos/<slug>/src -maxdepth 3 -type d | sort

# All import statements (dependency graph raw data)
grep -rn "^from\|^import" repos/<slug> --include="*.py" | sort
```

Output of Phase 0: the architectural contract (what must be true) and the implementation map (what exists).

---

## Phase 1 — Dead Code and Stale Artifacts

**Goal:** Find all code that exists but serves no living purpose.

**Dead code is not neutral.** It misleads every developer who reads the codebase after it was written.
Name it, locate it, and recommend removal without ambiguity.

### 1a. Unreferenced definitions
Find classes and functions that are defined but never imported or called:
```bash
# List all defined names
grep -rn "^def \|^class \|^    def \|^    class " repos/<slug> --include="*.py"

# Cross-check: grep for each name across the codebase
# A name that only appears in its own file is a candidate for removal
grep -rn "<ClassName>" repos/<slug> --include="*.py"
```

### 1b. Commented-out code blocks
```bash
# Commented function/class definitions — removed but not deleted
grep -rn "^#.*def \|^#.*class \|^ *# *def \|^ *# *class " repos/<slug> --include="*.py"

# Large commented blocks (3+ consecutive comment lines)
grep -rn "^#" repos/<slug> --include="*.py" | awk -F: '{print $1}' | uniq -c | sort -rn | head -20
```

### 1c. Unused imports
```bash
# If ruff is available:
.dadaia/.venv/bin/ruff check --select F401 repos/<slug>

# Manual fallback: find imports never referenced in the same file
grep -rn "^import \|^from .* import" repos/<slug> --include="*.py"
```

### 1d. Stale naming patterns
```bash
# Files and identifiers with legacy suffixes
find repos/<slug> -name "*_old*" -o -name "*_v2*" -o -name "*_legacy*" -o -name "*_bkp*" -o -name "*_deprecated*"
grep -rn "_old\|_v2\|_legacy\|_bkp\|_deprecated\|_DEPRECATED\|_OLD" repos/<slug> --include="*.py"
```

### 1e. Dead feature flags and unreachable branches
```bash
# Boolean constants used as conditions
grep -rn "if True:\|if False:\|if 0:\|if 1:" repos/<slug> --include="*.py"

# Constants that likely control dead features
grep -rn "ENABLED\s*=\s*False\|DISABLED\s*=\s*True\|DEBUG\s*=\s*False" repos/<slug> --include="*.py"
```

### 1f. Stale TODOs and FIXMEs
```bash
grep -rn "TODO\|FIXME\|HACK\|XXX\|NOQA" repos/<slug> --include="*.py"
# For each: check git blame to determine age
git -C repos/<slug> log --follow -p --since="90 days ago" -- <file> | grep "TODO\|FIXME"
```

**Output:** Exhaustive list of dead/stale artifacts. No item too small to mention.

---

## Phase 2 — Architecture Deviations (Layer Violations)

**Goal:** Verify that the dependency graph matches the architectural contract.

### 2a. Cross-layer imports
For a standard 4-layer architecture (CLI → Features → Core ← Infrastructure):
```bash
# Does core import from features?
grep -rn "from features\|import features" repos/<slug>/src/core --include="*.py"
grep -rn "from cli\|import cli" repos/<slug>/src/core --include="*.py"
grep -rn "from infrastructure\|import infrastructure" repos/<slug>/src/core --include="*.py"

# Do features import from other features directly?
for feature in repos/<slug>/src/features/*/; do
  grep -rn "from features\." "$feature" --include="*.py" | grep -v "from features.$(basename $feature)"
done

# Does CLI contain business logic?
grep -rn "def.*calculate\|def.*process\|def.*validate\|def.*compute" repos/<slug>/src/cli --include="*.py"
```

### 2b. Missing or multiple composition roots
```bash
# Find all places where concrete classes are instantiated
grep -rn "= [A-Z][a-zA-Z]*(" repos/<slug>/src --include="*.py" | grep -v "test_\|Test"
# The composition root should be one or very few files
```

### 2c. Persistence leaking into domain
```bash
# ORM/DB imports in core or features (should only be in infrastructure)
grep -rn "sqlalchemy\|django.db\|peewee\|tortoise\|motor\|pymongo" repos/<slug>/src/core repos/<slug>/src/features --include="*.py"
```

### 2d. HTTP/transport concerns in domain
```bash
# HTTP imports in core or features
grep -rn "import requests\|import httpx\|import aiohttp\|from fastapi\|from flask\|from django" repos/<slug>/src/core repos/<slug>/src/features --include="*.py"
```

**Output:** Per-violation finding with file:line, which rule is broken, and blast radius assessment.

---

## Phase 3 — OOP and SOLID Violations

**Goal:** Evaluate each principle systematically.

### 3a. Single Responsibility (S)
```bash
# Large classes (> 300 lines is a smell)
awk '/^class /{class=$0; count=0} {count++} /^class /{if(count>300) print FILENAME": "class" ("count" lines)"}' \
  $(find repos/<slug> -name "*.py")

# Classes with too many public methods (> 15)
grep -c "    def [^_]" repos/<slug>/src/**/*.py | sort -t: -k2 -rn | head -20

# Catch-all names
grep -rn "class.*Manager\|class.*Handler\|class.*Util\|class.*Helper\|class.*Service.*Service" \
  repos/<slug>/src --include="*.py"
```

### 3b. Open/Closed (O)
```bash
# if/elif chains that dispatch on type strings — classic OCP violation
grep -rn 'if.*type.*==\|elif.*type.*==\|if.*kind.*==\|elif.*kind.*==' repos/<slug>/src --include="*.py"

# isinstance chains in business logic
grep -rn "isinstance.*elif\|elif.*isinstance" repos/<slug>/src --include="*.py"
```

### 3c. Liskov Substitution (L)
```bash
# NotImplementedError in concrete subclasses (base method not overridden but must be)
grep -rn "raise NotImplementedError" repos/<slug>/src --include="*.py"

# Methods that accept None or return None where base type does not
# Manual review required — check subclass method signatures against base
```

### 3d. Interface Segregation (I)
```bash
# Large abstract classes / protocols (> 8 abstract methods)
grep -B5 "@abstractmethod\|@abc.abstractmethod" repos/<slug>/src --include="*.py" -A1 | grep "class " 
# Count abstractmethod decorators per class
grep -c "@abstractmethod" repos/<slug>/src/**/*.py | sort -t: -k2 -rn | head -10
```

### 3e. Dependency Inversion (D)
```bash
# Concrete instantiation in high-level modules (should use injection)
grep -rn "= [A-Z][a-zA-Z]*Repository\|= [A-Z][a-zA-Z]*Service\|= [A-Z][a-zA-Z]*Client" \
  repos/<slug>/src/features repos/<slug>/src/cli --include="*.py"

# Infrastructure imports in non-infrastructure code
grep -rn "from.*infrastructure import\|import.*infrastructure\." \
  repos/<slug>/src/core repos/<slug>/src/features --include="*.py"
```

### 3f. Inheritance vs Composition
```bash
# Deep inheritance chains (more than 2 levels for business classes)
# Manual review: check class hierarchy
grep -rn "^class .*(.*):$" repos/<slug>/src --include="*.py"

# Inheritance used for code reuse rather than polymorphism
# Signal: parent class methods never referenced polymorphically
grep -rn "super()\." repos/<slug>/src --include="*.py"
```

**Output:** Per-principle findings, ordered CRITICAL → HIGH → MEDIUM → LOW.

---

## Phase 4 — Stale Layers (Build-on-Stale)

**Goal:** Find code evolved by accumulation rather than replacement.

This pattern is the primary source of catastrophic, hard-to-diagnose incidents in large codebases.
A stale layer misleads every developer who builds on top of it.

```bash
# Wrapper chains — classes whose only methods delegate to another class
# Signal: every method body is one line calling self._inner.<same_method>
grep -A3 "def " repos/<slug>/src --include="*.py" -n | grep "return self\._\|return self\.inner\|return self\.wrapped\|return self\.delegate"

# Version-named modules alongside their replacements
find repos/<slug>/src -name "*.py" | xargs ls -la | sort
# Look for files that appear to be old versions kept alongside new ones

# Migration residue — old models/schemas kept for compatibility
grep -rn "# deprecated\|# legacy\|# old\|# backwards.compat\|# compat" repos/<slug>/src --include="*.py" -i
```

**Severity classification:**
- **CRITICAL:** Stale layer is in a write path (data mutation, initialization, auth)
- **HIGH:** Stale layer is in a frequently-called read path; misleads many developers
- **MEDIUM:** Stale layer is only in rarely-used paths
- **LOW:** Naming residue only (variable names, comments)

For each finding: describe what the stale layer wraps, which module builds on top of it, and what
the blast radius would be if a developer extends the stale layer instead of the live one.

---

## Phase 5 — Report Section

Append this section to the standard `review-<timestamp>.md` report:

```markdown
---

## OOP & Design Pattern Audit

### SOLID Violations

| Principle | Location | Description | Severity |
|-----------|----------|-------------|----------|
| S | file:line | <description> | CRITICAL/HIGH/MEDIUM/LOW |
| O | file:line | <description> | ... |
| L | ... | | |
| I | ... | | |
| D | ... | | |

### Patterns Misapplied

For each misapplied pattern:
**Pattern:** <name>
**Location:** file:line
**Classification:** OVER-ENGINEERED | VIOLATED | MISSING | ANTI-PATTERN
**Issue:** <what is wrong>
**Recommendation:** <specific corrective action>

### Anti-Patterns Identified

| Anti-pattern | Location | Impact |
|---|---|---|
| God Object | file:line | <impact description> |
| Anemic Domain | file:line | ... |

### Refactoring Recommendations (ordered by ROI)

1. **<Title>** — <1-sentence description> | Impact: <High/Medium/Low> | Effort: <High/Medium/Low>
2. ...
```

---

## Audit Completion Checklist

Before writing the report, confirm:

- [ ] Phase 0: Architecture contract loaded and understood
- [ ] Phase 1: Dead/stale code fully enumerated (not sampled)
- [ ] Phase 2: Every layer boundary checked with grep output as evidence
- [ ] Phase 3: All 5 SOLID principles evaluated, not just the obvious ones
- [ ] Phase 4: Stale layer patterns checked, severity classified
- [ ] Phase 5: Every finding has file:line, not just a module name

**Never report "no issues found" in a phase without showing the evidence commands and their output.**
A clean bill of health is only credible when the negative evidence is shown.

---

## References

- **"Clean Code"** — Robert C. Martin
- **"Refactoring: Improving the Design of Existing Code"** — Martin Fowler
- **"Working Effectively with Legacy Code"** — Michael Feathers
- **"Clean Architecture"** — Robert C. Martin
- **"A Philosophy of Software Design"** — John Ousterhout
- SOLID principles: Robert C. Martin
