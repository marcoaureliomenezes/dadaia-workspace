---
name: tasks-write-scope-traversal-hardening
status: superseded
superseded_by: lifecycle-pipeline-correctness-and-diagnosability (consolidation 2026-07-10)
opened: 2026-07-09
owner: project-manager (curates)
source: "v0.1.68 closure return — code-reviewer MEDIUM + security-reviewer INFO on the FR3 write-scope parser (both non-blocking for v0.1.68; routed here per reviewer recommendation)"
intents:
  - subject: { kind: code, ref: "dadaia_workspace/features/lifecycle/tasks_write_scope.py#_extract_globs" }
    change: "reject at parse time any Write-set glob token that is an absolute path (leading `/`), contains a `..` traversal segment, or begins with `~`/`$` (home/env expansion). Today these pass through verbatim and are INERT because the implement-step allowed_paths union only feeds the in-process Ring-1/Ring-2 advisory scope check (core/scope_match.matches_path, literal-prefix matching — write authority is actually enforced by the SDD gate + git chokepoints, which never consult allowed_paths). This is defense-in-depth so the parser cannot silently widen scope if matches_path ever gains real glob/normalization semantics. Add executed-path unit cases proving each rejected token maps to no captured glob."
---

# BACKLOG — Harden the TASKS.md write-scope parser against traversal/absolute tokens

**Priority:** LOW (defense-in-depth). Introduced with v0.1.68 FR3
(`write_scope_from_tasks`), which parses a reserved task's `Write set:` and unions
the derived globs into the implement step's `allowed_paths`. Both the
code-reviewer (MEDIUM, `tasks_write_scope.py:116-132`) and security-reviewer
(INFO) flagged that the parser passes `..`, leading-`/`, `~`, and `$` tokens
through verbatim.

**Why non-blocking for v0.1.68:** traced non-exploitable today — `allowed_paths`
only feeds the advisory in-process scope check (`core/scope_match`), pure literal
string matching; real write authority is the SDD gate + git chokepoints, which do
not consult `allowed_paths`. Same trust level as the pre-existing `--write-scope`
CLI hatch. Widening requires an author writing an explicit, human-visible,
reviewable glob.

**Acceptance sketch:** `write_scope_from_tasks` drops (never captures) any glob
token that is absolute, contains `..`, or starts with `~`/`$`; executed-path unit
tests prove each token → no glob; the frozen FR3 grammar tests still pass.
