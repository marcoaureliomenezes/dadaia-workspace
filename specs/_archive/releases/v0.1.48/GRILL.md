# GRILL — v0.1.48 — Memory Single-Ownership + Truth + English Canon

**Status:** Aprovado
**Origin:** operator directives 2026-07-02 ("All specs must be in english. go v0.1.48") on the
scoping review committed as audit `specs/audits/20260702T015037Z-56b226fb/`.
**Picked set:** all 84 audit findings + open bug `memory-index-table-broken-gfm` (bugs-always-solved).

Decisions pinned before SPEC (grill format: hard question → decision → why):

- **G1 — How far does "all English" go?** Atom bodies + frontmatter (`title`/`tldr`/`summary`) +
  h2 headings + catalog/index output → English. The SDD status tokens `Aprovado` / `Em revisão` /
  `Draft` are **not** translated: root AGENTS.md declares them canonical and doctor/gate code
  greps them literally. Bug/backlog JSONL and archived artifacts are ledger, not truth — no
  retro-translation.
- **G2 — Does the heading allowlist break consumers?** No: `lint-memory-atoms.py` gains an
  English canonical Group-A set (Purpose / Usage flow / Typical trigger / Differentiator /
  Runtime state touched / Dependencies); PT legacy entries stay accepted so consumer workspaces
  with PT atoms keep LINT-1 green; only provably dead strings are pruned (e.g. "Adoção (15 de 15
  agentes)").
- **G3 — Translate or consolidate first?** Consolidate (W2) strictly before translate (W4):
  never translate an atom that W2 deletes/merges/archives (4 delete + 1 merge + 1 archive).
  W3's allowlist change lands before W4 so translated headings pass LINT-1.
- **G4 — Fix `agent_tier` now?** No invention: document it honestly in the memory-AGENTS source;
  wire-or-remove is deferred to backlog (`hygiene-and-dead-code-cleanup` gains the item). All 31
  atoms are `self-pull`; no runtime consumer exists today.
- **G5 — What about `rank`?** Drop from `ctx_inject._DIGEST_FIELDS` (alphabetical file order
  masquerading as priority in every bound session's digest). Keep in catalog.json, documented as
  file order.
- **G6 — `category` vs area?** Generator derives `area` from the parent directory and index.md
  groups by it; `category` frontmatter untouched except `quality-assurance.md` → `core` (trio
  consistency).
- **G7 — Constitution §0 vs §4 tension?** Architecture drops enum-token enumeration; posture
  prose keyed by lowercase harness names + `[[tech-stack]]` citation. Constitution §0 rephrased:
  it never enumerates the runtime-kind enum; harness *names* may appear where posture requires.
  SPEC-DOC-037 (uppercase tokens) unchanged.
- **G8 — Stray `specs/releases/v0.1.23/`?** `git mv` to `specs/_archive/releases/v0.1.23/`.
  No CLOSURE.md exists (pre-CLOSURE-era release; content shipped via the v0.1.28/29 PR #68) —
  noted in the commit, accepted as a legacy-archive warning.
- **G9 — The open bug?** `memory-index-table-broken-gfm` is fixed in W3 (both renderer
  implementations) and receives `resolved --release v0.1.48` at close.
- **G10 — May memory atoms be deleted?** Yes: memory is truth, not ledger — the never-delete law
  covers bugs/backlog/audits. Unique facts migrate before deletion; deletions are listed in
  CLOSURE; catalog + index regenerate after every structural change.
- **G11 — Audit governance?** The review is committed as a formal audit; v0.1.48 is its disposing
  release; every finding carries an explicit disposition in SPEC §Dispositions; the audit archives
  with `DISPOSITION.md` at close (audit-disposition law).
- **G12 — v0.1.47 closure?** Folded into this branch's first commit (archive move, `6c3e086e`) —
  avoids a second operator-gated closure PR; v0.1.47's CLOSURE.md was already written pre-merge.
