---
name: memory-heading-allowlist-not-consumer-extensible
status: Open
severity: LOW
reported: 2026-06-11
surface: dadaia_workspace/public/scripts/lint-memory-atoms.py (heading allowlist) / specs doctor memory lint
session_id: null
---

> **Disposition (v0.1.14 release definition, 2026-06-12, product-engineer):**
> NOT PICKED — valid consumer-extensibility gap in the memory lint, stays Open;
> specs-doctor lint surface is outside the v0.1.14 kernel scope. Natural fit for
> the v0.1.15 governance release (doctor invariants are reworked there).

**Symptom:** `lint-memory-atoms.py` (invoked by `dadaia specs doctor`) warns
"not in the curated allowlist" on every valid domain-specific H2 heading in consumer
workspaces. The allowlist (`HEADING_ALLOWLIST`, Groups A+B+C) is hardcoded in the
script with dadaia-workspace-internal strings (e.g. "Adoção (15 de 15 agentes)",
"Model assignments (20 agentes)", "Codex Dispatcher Capability Matrix (ADR-3)") and
there is no mechanism for a consumer workspace to extend it. A consumer spec context
(e.g. an AWS data-platform repo) legitimately needs domain headings such as
"S3 Buckets", "Kinesis Data Streams", "Schema: `b_ethereum` — Bronze Ethereum",
"Catalog Summary" — all of which produce permanent WARN noise that cannot be cleared
without rewriting correct documentation or editing library source.

**Repro:**
```
# in a consumer workspace with domain-specific memory atoms
dadaia specs doctor
# -> WARN: '## S3 Buckets' is not in the curated allowlist — consider normalising
#    or adding it to the allowlist in lint-memory-atoms.py.
```
Also self-inconsistent: the library's own scaffold
`dadaia_workspace/public/scaffold/memory/quality-assurance.md` ships
`## Padrões de qualidade`, which is NOT in the allowlist — every freshly scaffolded
workspace starts with a WARN it cannot fix.

**Expected:** Either (a) a per-workspace allowlist extension file (e.g.
`specs/memory/.heading-allowlist` or a doctor config key) merged with Group A canon,
or (b) the allowlist scoped to forbidden-headings-only (changelog/history) +
Group A structural canon for product atoms, treating other headings as free domain
vocabulary. At minimum, the scaffold's own headings must be in the allowlist.

**Notes:** Found while executing v0.3.0 CLOSURE (T-R6-S6, deferred T-R5-F3) in the
dd-chain-explorer spec context. Decision there: domain headings were justified and
kept (renaming them to dadaia-internal Group B/C strings would corrupt meaning); new
atoms authored in that release use Group-A canon only. Groups B/C should arguably
live in the dadaia-workspace context's own extension file, not in the generic script.
