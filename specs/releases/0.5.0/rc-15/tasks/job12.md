# Job 12 — the `ADR:` label grammar and the pairing law leave (FR10, deletion half)

**Status:** Draft

Wave 4, after Job 2 (both edit `dd-gitflow-default/SKILL.md` §3a). ADR 0251 (a) and (b). It deletes; it adds nothing. This job is the only one in the candidate that edits canon-fingerprinted law, so it owns the one pin (canon 12 is unpublished: `main` stamps 7). No task names a path under `specs/memory`: the 19 `ADR:` lines of `ARCHITECTURE.md` and `QUALITY.md`, the generated block and the refresh of the `specs/memory/AGENTS.md` mirror are the Reconciliation's (shape 9). Seam for T3: if the job gate's doctor flags the stale `specs/memory/AGENTS.md` mirror, stop and return it to the main thread; do not write it.

- **Seams closed.**
  - Guard (T1): `_ADR_LINE`, the `adr-line` and `adr-exists` outputs, their two plants, and the `ADR: none` text inside the `principle-placement` plant leave `scripts/guards/repo.py`; `python scripts/guards/run.py` and `--planted` exit 0, and the commit body gives the check and plant counts before and after. Narrowing a guard's reach takes the main thread's ruling, named in the `test(J12.T1)` commit (root map §1).
  - Law (T2), scaffold sources: `public/scaffold/ADRs/AGENTS.md` loses the "naming every canonical memory statement" clause of §2, §5 whole and §5.1 whole; `public/scaffold/memory/AGENTS.md` loses the pairing clause of the intro line, of the §1 row ("only in the commit carrying its accepted ADR") and the optional `ADR:` label of the §2 principle line; `PILLAR-MEMORY.md` loses §2 (the pairing check; the missing-`Measured by:` finding of §1 stays); `dd-gitflow-default/SKILL.md` §3a drops "with its canonical-memory hunk" from the acceptance row. Net law lines are negative.
  - Mirrors and pin (T3): `specs/ADRs/AGENTS.md` comes from `dadaia specs upgrade --specs-dir specs` in the job tree, never by hand (the commit body names the run); `CANON_AT[12]` is re-pinned (`test_a_canon_change_bumps_the_stamp` computes the digest) and the new scaffold digests join `shipped-hashes.json`.
  - `test_memory_lint.py:346-350,427-431` stay unedited and green: no operator order covers them.
- **Consumers.** `git grep -n -i -E 'canonical-memory hunk|pairing law|ADR: (none|NNNN)' -- dadaia_workspace scripts tests AGENTS.md specs/ADRs` before and after (target after: only test inputs).
- Test-side first: T1. Then T2. T3 last.
- Pre-review checklist: one home per rule (the ledger holds status; the principle's `Measured by:` guards it); sweep line; no platform fact; net lines negative.

Tasks: 3 (1 jr, 2 sr). `who` names the dispatched role (`dd-release-definition` §5).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J12.T1 | sr | AC10.5 | `scripts/guards/repo.py` | the guard deletion of the intro, in a `test(J12.T1)` commit naming the main-thread ruling. Needs that ruling in the dispatch brief |
| J12.T2 | jr | AC10.5 | `dadaia_workspace/public/scaffold/ADRs/AGENTS.md`, `dadaia_workspace/public/scaffold/memory/AGENTS.md`, `dadaia_workspace/public/skills/dd-audit-project/PILLAR-MEMORY.md`, `dadaia_workspace/public/skills/dd-gitflow-default/SKILL.md` | the law deletions of the intro. No test, reviewer sweep with the consumer grep |
| J12.T3 | sr | AC10.5 | `specs/ADRs/AGENTS.md`, `dadaia_workspace/core/specs_version.py`, `dadaia_workspace/public/templates/shipped-hashes.json` | the ADR mirror, the pin and the digests of the intro. After T2 |
