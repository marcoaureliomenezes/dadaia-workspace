# PLAN — Release: 0.4.6

**Status:** Aprovado
**Release ID:** 0.4.6
**Owner:** product-engineer

---

## Candidate 2 — skills quality consolidation

### Method

1. **Standard first.** The 15-rule authoring contract lands in
   `dd-ai-eng-knowhow/AUTHORING.md` before any skill is edited, so every later
   task is applied *against* a written standard, not a session memory.
2. **Content merges before cosmetic passes.** The four merges (FR2–FR5) and the
   two reference-copy deletions run one task each, every task leaving the tree
   green: the merged skill is born/enriched, the retired directory deleted,
   persona grants, behavior-map row and cross-citations updated in the same
   commit (the behavior-map enforcer, orphan checker and FR27 citation test
   make a half-done merge RED — they are this candidate's safety net).
3. **Conformance pass over the 16 kept skills** (FR6), then the structural
   fixes/router/wiring (FR7–FR9) — content settles before names change.
4. **Rename sweep last** (FR10), exactly as the operator ordered: directory
   renames plus a whole-tree citation sweep (`public/**`, tests, memory
   atoms, `CONTEXT.md`), relying on FR27/behavior-map to catch residue.
5. **Equalize and reproject** (FR11): behavior-map hashes re-recorded as the
   deliberate final act, scaffold backlog AGENTS.md §5 aligned to the
   purge-on-pick law, `stage → install --target all → public doctor`, stale
   projected directories for renamed/deleted skills removed from every
   harness projection target, full local CI preflight.

### Risks and controls

- **Hash-tuple discipline**: every skill edit invalidates its behavior-map
  hash; each task re-records only the rows it touched (a deliberate act per
  A10.4), and T-046-16 does the final full verification.
- **Citation residue after renames**: FR27 (path-shaped citation check) and
  the behavior-map member-exists check are the mechanical backstop; the sweep
  greps for the old names before committing.
- **Stale projections**: `public install` overwrites but does not delete;
  renamed/deleted skill directories must be explicitly removed from
  `.claude/skills/`, `.agents/skills/`, and any other harness projection
  target, then `public doctor` must report `[ok] public-privacy`.
- **Bug-surface verdict**: this candidate is deletion-shaped (5 fewer skills,
  dead frontmatter and sediment removed); any diff that grows a skill must be
  justified against the replace-don't-layer principle in its task evidence.
