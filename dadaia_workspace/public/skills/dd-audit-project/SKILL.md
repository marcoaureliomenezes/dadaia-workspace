---
name: dd-audit-project
description: >
  The periodic three-pillar drift audit of a whole context (one diff's review is dd-code-review's) — bug history, spec compliance, memory
  drift — over the sha window read from audits_histo.jsonl. Use when dispatched to
  audit a context or to run an onboarding first pass.
---

# dd-audit-project — Three Pillars Over a SHA Window

> `dd-code-reviewer` is the lens (read-only, it returns its report); the main thread writes the audit from it — `specs/audits/AGENTS.md`.

## 1. The window — computed once per audit

1. Open `specs/audits/AGENTS.md` (the area's scoped law) and follow it.
2. Window mechanics: `dd-bug-resolution`'s `LINEAGE.md` §The window, cited never restated.
3. Record the resulting `[from-sha, HEAD]` in `AUDIT.md`'s scope.

## 2. The three pillars — all three in one run

- **Pillar 1 — bugs** ([`PILLAR-BUGS.md`](PILLAR-BUGS.md)): compute all nine
  forensic metrics it lists on each `BUGS.jsonl` record in the window; the audit record and git history establish coverage.
- **Pillar 2 — specs** ([`PILLAR-SPECS.md`](PILLAR-SPECS.md)): commit shapes, canon compliance, `_RELEASE.json` milestones over the window.
- **Pillar 3 — memory** ([`PILLAR-MEMORY.md`](PILLAR-MEMORY.md)): principles through their `Measured by:` checks, canonical hunks against ADRs, product atoms against code.

The main thread refuses to write `AUDIT.md` until all three pillar sections are present. Append one `FINDINGS.jsonl` record per claim
([`FINDINGS-FORMAT.md`](FINDINGS-FORMAT.md)).

## 3. First pass — a freshly onboarded context

- Applies while `.dadaia/.venv/bin/dadaia doctor`'s ONBOARDING next step is `first-pass`; its fix line lists the pending memory files.
- Worklist: `python3 .agents/skills/dd-spec-navigator/scripts/memory.py drift --since <root commit> --specs repos/<slug>/specs` (root commit: `git -C repos/<slug> rev-list --max-parents=0 HEAD`) — every uncovered unit.
- `dd-product-engineer` fills `ARCHITECTURE.md`, `QUALITY.md` and the product atoms from the code, and from `specs-bkp/` when present.
- Done = every worklist line covered and `.dadaia/.venv/bin/dadaia doctor --context <ctx>` exit 0 (LINT-1 owns the atoms, `memory.py check` only the generated pair) — the next step moves to `publish`; the first pass opens no audit window.

## 4. Done when

- Window recorded; nine bug metrics with baseline + target; every PILLAR-MEMORY §1 check ran; `AUDIT.md` has all three pillars, each claim a `FINDINGS.jsonl` record; `python3 .agents/skills/dd-audit-project/scripts/audit.py check --specs <specs-dir>` exits 0.

## 5. References

- Script: `python3 .agents/skills/dd-audit-project/scripts/audit.py` — `disposition`, `close`, `check`: this ledger's ONE writer and validator.
- Lifecycle, pillars and verbs: `specs/audits/AGENTS.md`.
