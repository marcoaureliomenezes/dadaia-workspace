---
name: dadaia-grill-me
description: >
  Backlog/intake refinement mode — interviews the operator about a demand, SPEC,
  or feature until full shared understanding is reached. Resolves inconsistencies,
  scope gaps, and open decisions.
  PRIMARY CALLER (post-agents-r1-v1): project-manager during the intake phase.
  product-engineer may invoke when consulted as a leaf specialist for a specific
  spec question. The final report goes to
  .dadaia/reports/<context-name>/<caller-agent>/<YYYY-MM-DDTHHMMSSZ>-refine-specs.html.
  Use when the operator mentions "grill", "refine specs", "review backlog", or "/dadaia-grill-me".
applyTo: "specs/**"
---

# dadaia-grill-me — SDD Spec Refinement

## Purpose

Identify and resolve — before implementation — the problems that destroy specs:

| Problem type | Example |
|---|---|
| **Inconsistency between specs** | `feature/my-feature` references paths from `platform/my-platform` but that feature is not done yet |
| **Spec vs implementation** | `service/my-service` security section says socket `:ro` but the service needs write access |
| **Open question already answered by code** | "What is the operator ID?" — it is in the service env file |
| **Divergent names for the same concept** | `ALLOWED_IDS` in the security spec vs `OWNER_ID` in the env file — same concept, two names |
| **Ambiguous syntax** | `{{VAR}}` in config templates but `envsubst` uses `${VAR}` |
| **Undeclared dependency** | `feature/my-feature` depends on `platform/my-platform`; dependency not declared |
| **Incorrect category** | A feature called "guardrails" actually specifies config backups |
| **Stale constitution** | `constitution.md` says Provider A is primary; a later release implemented Provider B as primary |

**The operator only answers what the code cannot answer.** The model inspects first.

### Mandatory trigger — release definition

A `dadaia-grill-me` session is **mandatory** when a release is being defined from
bugs + backlog (the `dadaia-release-definition` protocol). `product-engineer` runs
it on the picked bug + backlog set **before** writing the SPEC; `project-manager`
will not let the release advance to SPEC without the resulting refinement report.
This is not optional even when the scope "looks obvious". See the
`release-governance` rule and the `dadaia-release-definition` skill.

---

## How to Invoke

```
/dadaia-grill-me                       → entire backlog
/dadaia-grill-me <feature-id>          → one specific spec + its dependencies
/dadaia-grill-me report                → generate report with Q&A accumulated in the session
```

---

## 3-Phase Protocol

---

### Phase 0 — Inspection (before any question)

**Never ask what can be discovered. Inspect first.**

```bash
# 1. List all specs and status
grep -r "Status:" specs/ --include="SPEC.md" -l | xargs grep "Status:" | sort

# 2. Check real container state vs what specs claim
docker compose -f <COMPOSE_FILE> ps
docker inspect <CONTAINER_NAME> --format '{{range .Mounts}}{{.Source}}→{{.Destination}} {{end}}'

# 3. Check real env vars vs what specs say
grep -r "<ENV_VAR_TARGET>" <config-path>/

# 4. Check paths specs reference but may not exist
ls <workspace-data-path>/ 2>/dev/null || echo "path does not exist"
```

After inspection, build internally a list of **findings** by type before starting the interview:

```
FINDINGS (internal — do not show the operator yet):
  [INCONSISTENCY] ...
  [DRIFT spec↔code] ...
  [OPEN QUESTION ANSWERABLE] → already answered: <value>
  [OPEN QUESTION UNANSWERABLE] → needs operator
  [UNDECLARED DEPENDENCY] ...
  [DIVERGENT NAMING] ...
  [STALE CONSTITUTION] ...
```

Resolve the "ANSWERABLE" ones internally. Only bring "UNANSWERABLE" ones to the operator.

---

### Phase 1 — Focused Interview on Real Problems

**One question per turn. Always anchored in real specs and files.**

Required format for each turn:

```
**Inconsistency/Gap #N:**
Spec(s) involved: `specs/.../SPEC.md` (section X) and `specs/.../SPEC.md` (section Y)
Problem: [precise description of the conflict, gap, or ambiguity]
My recommendation: [suggested solution with justification]
→ How do you want to resolve this?
```

**Never two questions in the same turn.**

**Priority order:**

1. **Inconsistencies that block implementation** — implementing X based on spec Y will cause immediate rework
2. **Spec↔code drift** — what was implemented diverges from what the spec says; which prevails?
3. **Order dependencies** — which feature must come before which, and is that declared?
4. **Naming** — the same concept has two names; which one to standardize?
5. **Unanswerable acceptance criteria** — FRs without a defined "how to verify"
6. **Stale constitution** — the law document is lying about the current state

**Do not ask about:**
- Aesthetic formatting preferences
- Implementation choices already made and working
- Details the operator clearly does not care about (anything that can be "whatever is reasonable")

---

### Phase 2 — Synthesis per Spec (at the end of each spec)

```
## Synthesis: <feature-id>

**Core problem resolved:** [1 sentence]
**Post-refinement status:** Ready for approval | Needs editing | Blocked by <dependency>

**Required changes in SPEC.md:**
  - [ ] [section] → [what to change and why]

**Declared dependencies:** [list or "none new"]
**ADRs recorded in this session:**
  - [decision] — reason: [short justification]
```

---

### Phase 3 — Generate Report

When done (or at `/dadaia-grill-me report`), write `.dadaia/reports/<context-name>/product-engineer/<YYYY-MM-DDTHHMMSSZ>-refine-specs.html`:

---

## Report Format (`.dadaia/reports/<context-name>/product-engineer/<YYYY-MM-DDTHHMMSSZ>-refine-specs.html`)

```markdown
# Spec Refinement Report
> Generated at: <ISO 8601>
> Scope: <entire backlog | feature-id>
> Problems found: <N> | Resolved: <M> | Open: <P>

---

## Problem Summary

| # | Type | Specs involved | Status |
|---|------|-----------------|--------|
| 1 | Inconsistency | platform/my-feature ↔ platform/my-platform | Resolved |
| 2 | Spec↔code drift | service/my-service security section | Resolved |
| 3 | Stale constitution | constitution.md primary provider | Pending |
| ... | | | |

---

## Prioritized Backlog (post-refinement)

Recommended order with dependency justification:

| Order | Feature | Depends on | Reason |
|-------|---------|-----------|-------|
| 1 | service/my-service | — | zero risk, unblocks security |
| 2 | platform/my-platform | — | unblocks dependent features |
| 3 | feature/my-feature | my-platform | paths assume my-platform already present |
| ... | | | |

---

## Details per Problem

### Problem #N — <short title>

**Type:** Inconsistency | Drift | Dependency | Naming | Unanswerable criterion | Stale constitution
**Specs:** `specs/.../SPEC.md` section X; `specs/.../SPEC.md` section Y
**Description:** [what is wrong, with literal citation of the problematic text]
**Question asked:** [text of the question to the operator]
**Answer:** [operator's answer or "answered via inspection: <value>"]
**Resolution:** [how the spec should be updated]
**Pending:** [what still needs to change in the file — or "none"]

---

## Pending Spec Edits

Consolidated list of all changes to make:

| File | Section | What to change |
|---------|-------|-------------|
| `specs/constitution.md` | Stack | Update primary provider |
| `specs/releases/<release-id>/SPEC.md` | FR1/FR2 | Declare dependency on my-platform |
| ... | | |

---

## Next Steps

1. Edit the files listed above (in dependency order)
2. Mark `[x] Approved` on ready specs
3. Create PLAN.md for approved specs without a PLAN
```

---

## Absolute Rules

- **Inspect before asking** — any factual data (path, env var, status, ID) must be found in code or containers, never asked of the operator
- **Cite specs literally** — every question must include the exact section and the problematic text
- **One question per turn** — no exceptions
- **Do not suggest implementation** — output is spec refinement, not code
- **Record "answered via inspection"** — when resolving something without asking, document it in the report
- **Do not accept "it depends"** — if the operator says this, explore the decision tree until you have an actionable answer

---
