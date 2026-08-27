# T-050-16 Coverage Table — every block relocated out of `dd-bug-resolution`

**Release:** 0.5.0 · **Segment:** S2 · **Task:** T-050-16 (SPEC FR7 · A7.1–A7.5 · AS-11 ·
D8/D15) · **Author:** ai-engineer · **Date:** 2026-08-27

**Scope note (single-owner rule, SPEC D-B).** `dd-bug-fix/SKILL.md` — the file that
renames to `dd-bug-resolution` at **T-050-21** — is **not edited by this task**. This
table records, for every block this task's design **moves the intent of**, where the
text actually lives today and where it lands once T-050-21 performs the physical
`git mv` + rewrite. Nothing here is a claim that `dd-bug-fix/SKILL.md` already changed.

## Table

| # | Block | Origin (today) | Surviving home (this task) | Disposition at T-050-21 |
|---|---|---|---|---|
| 1 | §3 "The six-phase method" — phases 1–6 (red loop, minimise, hypotheses, instrument, seam test, cleanup), each with its *Done when* | `dd-bug-fix/SKILL.md` §3 | `dd-diagnose/SKILL.md` §3 (verbatim phase text, unchanged) | Deleted from the renamed `dd-bug-resolution/SKILL.md`; replaced by a pointer to `dd-diagnose` |
| 2 | The no-correct-seam clause ("No correct seam exists → register an architecture finding and dispatch `software-architect` before fixing") | `dd-bug-fix/SKILL.md` §3, phase 5 | `dd-diagnose/SKILL.md` §3, phase 5 (same wording) | Deleted from `dd-bug-resolution`; the pointer to `dd-diagnose` covers it |
| 3 | Lineage / prior-fix reading before a hypothesis is formed | **absent** — `dd-bug-fix`/`dd-bug-registration` carry zero text about prior-fix lineage (grill finding, 2026-08-26 handoff) | `dd-diagnose/SKILL.md` §2 (short) + `dd-diagnose/LINEAGE.md` (full: window, cap, diff-trust rule) | New law, not a relocation — first-authored here (FR7/AS-11) |
| 4 | The `caused_by` clause as the architecture-review trigger | **absent** — the standing "permanent architecture review, oriented by bug history" order (`DADAIA.md` §7) had no bug-record hook to fire from | `dd-diagnose/SKILL.md` §4 | New law; `dd-bug-resolution` keeps only a pointer, per AS-11 |
| 5 | The bug ledger's authoring rules (register/update, no per-bug Markdown, no session lock) | `specs/bugs/README.md` (legacy pre-`bug-record-v1` model — session-lock-gated Markdown-per-bug, retired) | `specs/bugs/AGENTS.md` (rewritten for `bug-record-v1`/D11: one record per bug, the three mutability classes, `dadaia bugs update` as the one governance seam) | `README.md` deleted in this same commit (`git rm`); no further T-050-21 action — the scoped `AGENTS.md` is this task's own surviving home, not a relocation target for a later task |
| 6 | Ledger field-class taxonomy (immutable-core / write-once / mutable-governance) | **absent from any scoped rule** — declared only in `bug-record-v1.schema.json`'s own `x-mutability` keyword | `specs/bugs/AGENTS.md` §"Field classes (D11)" (the three-class table only; the schema stays the sole per-field source, never re-declared here) | n/a — this is a pointer table, not a relocation |
| 7 | The bug-lifecycle rump: branch/concurrency (§2), GREEN/`resolved`-event/commit (§4), no-separate-release-ceremony (§5), the checklist (§6) | `dd-bug-fix/SKILL.md` §2, §4, §5, §6 | **stays** in the renamed `dd-bug-resolution/SKILL.md` — not moved; `dd-diagnose/SKILL.md` §5 ("Handback") points at it | T-050-21 rewrites these sections in place under the new name; content unchanged in substance |

## AI-surface net (FR7 alone; FR12 combined net reported at T-050-21, A7.4)

Measured against `dadaia_workspace/public/skills/` at HEAD before this commit (21
entries) and after (22 entries):

| Metric | Before | After | Delta |
|---|---|---|---|
| Skills | 21 | 22 | +1 (`dd-diagnose`) |
| Skill sibling files | — | +1 | `dd-diagnose/LINEAGE.md` |
| `SKILL.md` own line count (new skill) | — | 84 | well under the 500-line ceiling (`skill_md_line_ceiling`) |
| CLI files touched (`dadaia_workspace/cli/`) | — | +0 | A7.5 |
| Hook files touched (`dadaia_workspace/hooks/`) | — | +0 | A7.5 |
| Duplicated procedure (phases 1–6, restated a second time) | 1 copy (`dd-bug-fix`) | 1 copy (`dd-diagnose`) pending T-050-21's deletion of the `dd-bug-fix` copy | net-negative once T-050-21 lands; net-additive in AI-surface **lines** until then (both copies coexist by design — single-owner rule, D-B) |
| Production LOC | — | 0 | FR7 authors AI-surface text only |

This task's own diff is net-**additive** in AI-surface lines (a new skill + a new scoped
`AGENTS.md`, one legacy file deleted) and net-**zero** in production code — matching the
SPEC's own stated shape (§1.1, "net-additive in AI-surface lines, net-negative in
duplicated procedure; zero production LOC"). The duplicated-procedure figure only turns
net-negative once T-050-21 deletes the phases-1–6 copy from the renamed
`dd-bug-resolution/SKILL.md`; that deletion is out of this task's write set (D-B) and is
reported again, combined with FR12's own numbers, at T-050-21 (A7.4).

## Acceptance cross-reference

- **A7.1** — seven phases (0 through 6), each ending on a checkable *Done when*:
  `dd-diagnose/SKILL.md` §2–§3.
- **A7.2** — the window computation is stated once, in `dd-diagnose/LINEAGE.md` §"The
  window (stated once)"; FR14's audit pillar 1 (a later task) cites this text rather
  than restating it.
- **A7.3** — `dd-diagnose/LINEAGE.md` §"What to read — and what to distrust" instructs
  the reader to distrust a `release-squash`/`ledger-only` sha rather than diff it,
  with a real ledger example (`certify-cannot-install-installed-provider`).
- **A7.4** — this table.
- **A7.5** — no file under `dadaia_workspace/cli/` or `dadaia_workspace/hooks/` is in
  this commit's diff (verified: `git diff --stat` against those two prefixes is empty).
