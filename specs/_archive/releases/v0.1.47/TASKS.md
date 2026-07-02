# TASKS — v0.1.47

**Status:** Aprovado

Markers: `[ ]` open · `[-]` in progress · `[x]` done. One `[-]` per owner unless disjoint
write sets are declared (PLAN write-set boundaries apply).

## W0 — Definition

- [x] T-47-00 Backlog sanitization: archive 8 delivered items; fix panel-ux-overhaul +
  specs-truth doc anchors; `backlog doctor` exit 0 (owner: coordinator/PM)
- [x] T-47-01 GRILL/SPEC/PLAN/TASKS authored; QA REJECT→fix→APPROVE cycle run; ACTIVE.md →
  v0.1.47 DEFINITION; `.gitignore` re-includes (GRILL/OQ-DECISIONS ×3 groups;
  `specs/bugs/*.jsonl` + `_archive/*.md`); definition commit (owner: coordinator/PE)

## W1 — Code fixes (owner: software-engineer)

- [x] T-47-10 Codex exec argv fix + stderr mapping + pin-test update (W1-1)
- [x] T-47-11 Remove inert codex config keys `approved_commands` + `[skills] paths` (W1-2)
- [x] T-47-12 Persona injection all verbs: shared helper + 5 bodies + CLI step path +
  per-verb prompt-content tests (W1-3)
- [x] T-47-13 Pre-commit backlog gate staged-path scoping (W1-4)
- [x] T-47-14 Preflight excludes `tests/performance` (W1-5)
- [x] T-47-15 Root-whitelist first-path-component classification + tests (W1-6)
- [x] T-47-16 ctx-inject bind attribution (harness pid) + two-session test (W1-7)
- [x] T-47-17 specs_resolver persisted-bind fallback + tests (W1-8)
- [x] T-47-18 Doctor guards: SPEC-DOC-037 no-enum; loose-audit WARN; `hooks` allowed subdir
  (W1-9)
- [x] T-47-19 SPEC-DOC-031 remediation text ↔ BL-SCHEMA vocabulary (W1-10)
- [x] T-47-20 FAKE closure smoke; fix iff broken (W1-11)
- [x] T-47-21 `setup.cfg` import-linter comment trued (not CI-enforced; cite backlog)
  (W1-12)

## W2 — Constitution + AGENTS.md (owner: product-engineer)

- [x] T-47-30 Constitution lean rewrite (WS-A1..A6; ≈200 lines; invariant+citation;
  Governance section)
- [x] T-47-31 `public/data/AGENTS.md` truth fixes (reports-validate wording; injection
  claim; harness-preference convention) + 8-rule stale sweep
- [x] T-47-32 One-time manual refresh of `repos/dadaia-workspace/AGENTS.md` from source
  (SPEC W2b; automated fan-out redesign stays deferred)

## W3 — Memory canon (owner: product-engineer)

- [x] T-47-40 tech-stack.md: `#Agent runtimes` = roster single-source; PI auth fix;
  kimi-2.7; dep list (pytest-randomly, hypothesis); mermaid-CDN claim removed
- [x] T-47-41 product-vision.md + harness-primitives.md de-stale (WS-B1)
- [x] T-47-42 Projection/runtime atoms de-stale (WS-B2 set)
- [x] T-47-43 architecture.md de-narrate + slim + extract-to-owners + stale-line fixes
  (WS-B7); kanban contradiction resolved to code truth; auth sections pass the
  no-bearer grep acceptance; import-linter CI claim reworded to deferred
- [x] T-47-44 quality-assurance.md re-truing (WS-C; 5 governance jobs)
- [x] T-47-45 v0.1.46 catch-up: sdd-bug-backlog-governance rewrite (JSONL store);
  specs-doctor.md inventory; R-2 FROZEN rows in sdd-gate-v3 + architecture
- [x] T-47-46 panel.md + agent-monitoring.md + brand-identity.md truth (no-auth reality,
  module lists, SQLite filename, token home); spec-context-project.md injection claim;
  workspace-doctor.md codes; platform atom nits; ACCEPT: no-bearer grep == 0 + positive
  loopback/Host-guard statement + import-linter-CI grep clean across memory
- [x] T-47-47 NEW memory/product/harness/{claude-code,codex,pi}.md (grill D-5)
- [x] T-47-48 dadaia-workflows atom (WS-B4) + §13 index.md (WS-B3) + catalog regenerate
  (WS-B8, LAST)

## W4 — Fragments + personas (owner: ai-engineer)

- [x] T-47-50 Shared fragments de-slop (output_handoff, anti_slop, memory_selection, etc.)
- [x] T-47-51 release_definition + backlog_definition fragment sets
- [x] T-47-52 audit / research / bug_report fragment sets
- [x] T-47-53 pipeline phase fragments (implementation/review/closure)
- [x] T-47-54 8 personas rewrite (sub-agent mandates; zero fragment overlap)
- [x] T-47-55 dadaia-handoff-emitter skill root-resolution instruction
- [x] T-47-56 stage + install --target all + public doctor exit 0 (clears live drift)
- [x] T-47-57 Second-reviewer content sign-off over all rewritten fragments/personas
  (APPROVE verdict + per-workflow prompt-assembly dumps as evidence)

## W5 — Dispositions (owner: product-engineer + coordinator)

- [x] T-47-60 Deferral backlog entries (10 named in SPEC §W5, incl.
  lifecycle-verb-governance-uniformity + hygiene-and-dead-code-cleanup)
- [x] T-47-61 Bug terminal events per SPEC §W5 state table (resolved set, 2 supersedes,
  7 deferred-with-backlog-ref, hollow-event backfill → resolved, mypy-cache repro →
  rejected-or-open)
- [x] T-47-62 Audit archive sweep (15 dirs, disposition lines incl. this release's audit)

## W6 — Ship (owner: coordinator)

- [x] T-47-70 Full validation matrix green (PLAN table)
- [x] T-47-71 qa checkpoint → commits; security APPROVE handoff per pushed sha; push;
  CI watch to all-green; PR
