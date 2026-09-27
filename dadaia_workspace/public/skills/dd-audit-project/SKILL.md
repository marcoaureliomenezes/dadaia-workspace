---
name: dd-audit-project
description: >
  The three-pillar drift audit (the reviewer's audit lens) — bug history, spec compliance, memory
  drift — over the sha window read from audits_histo.jsonl. Use when dispatched to
  audit a context.
---

# dd-audit-project — Three Pillars Over a SHA Window

> `dd-code-reviewer` drives this directly, dispatched by the operator or a dispatching
> agent. Suggested every 5 releases, never mandatory.

## 1. The window — computed once per audit

1. Open `specs/audits/AGENTS.md` (the area's scoped law) and follow it.
2. Window mechanics: `dd-bug-resolution`'s `LINEAGE.md` §The window, cited never restated.
3. Record the resulting `[from-sha, HEAD]` in `AUDIT.md`'s scope.

## 2. The three pillars — run together, never fewer

- **Pillar 1 — bugs** ([`PILLAR-BUGS.md`](PILLAR-BUGS.md)): compute all eight
  forensic metrics on every `BUGS.jsonl` record in the window; stamp `audited` on each
  reviewed record (`python3 .agents/skills/dd-bug-resolution/scripts/bugs.py update <id> --set audited=<slug>`, pillar 1's only write).
- **Pillar 2 — specs** ([`PILLAR-SPECS.md`](PILLAR-SPECS.md)): commit shapes, canon compliance, `_RELEASE.json` milestones over the window.
- **Pillar 3 — memory** ([`PILLAR-MEMORY.md`](PILLAR-MEMORY.md)): execute every
  Part-1 principle's named `Measured by:` check; match every Part-1 hunk in the
  window to an `accepted` ADR in the same commit, or flag HIGH.

Refuse to write `AUDIT.md` until all three pillar sections are present — fewer than
three is not an audit. Append one `FINDINGS.jsonl` record per claim
([`FINDINGS-FORMAT.md`](FINDINGS-FORMAT.md)).

## 3. First pass — a freshly onboarded context

- Applies while `.dadaia/.venv/bin/dadaia doctor`'s ONBOARDING next step is `first-pass`; its fix line lists the pending memory files.
- Worklist: `python3 .agents/skills/dd-spec-navigator/scripts/memory.py drift --since <root commit> --specs repos/<slug>/specs` (root commit: `git -C repos/<slug> rev-list --max-parents=0 HEAD`) — every uncovered unit.
- `dd-product-engineer` fills `ARCHITECTURE.md`, `QUALITY.md` and the product atoms from the code, and from `specs-bkp/` when present.
- Done = every worklist line covered and `.dadaia/.venv/bin/dadaia doctor --context <ctx>` exit 0 (LINT-1 owns the atoms, `memory.py check` only the generated pair) — the next step moves to `publish`; the first pass opens no audit window.

## 4. Done when

- Window recorded; eight bug metrics with baseline + target; every Part-1 check ran; `AUDIT.md` has all three pillars, each claim a `FINDINGS.jsonl` record.

## 5. References

- Script: `python3 .agents/skills/dd-audit-project/scripts/audit.py` — `disposition`, `close`, `check`: this ledger's ONE writer and validator.
- Lifecycle, pillars and verbs: `specs/audits/AGENTS.md`.
