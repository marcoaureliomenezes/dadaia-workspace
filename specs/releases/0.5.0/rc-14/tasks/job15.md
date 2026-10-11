# Job 15 — closing sweep: ratchets lowered to what the skill jobs removed, the last clock site, the public-law guard line (FR4, FR11)

**Status:** Draft

Wave 4, after every code job: a ceiling can only be lowered, and a guard line only added, once the hits are gone. No behaviour changes here.

- T1 lowers `V32_COMMENTS` and `V32_DOCSTRINGS` in `scripts/guards/slop.py` and `PRIVATE_IMPORT_STATEMENTS`/`PRIVATE_IMPORT_FILES` in `scripts/guards/suite.py` to the counts measured at this base (the commit body quotes before and after); `python scripts/guards/run.py` and `--planted` exit 0.
- T2 adopts `core/clock` at `hooks/ctx_inject.py:186` (Job 13 edited that file in the same wave).
- T3 adds ONE pattern line to `test_public_law_names_no_private_pipeline` (`tests/infrastructure/test_privacy_check.py:126`): no `ADR <nnnn>` number and no `dadaia_workspace/` path in `public/**` (the provenance banner span stays exempt, AC4.1). It lands green because Jobs 5, 11 to 14 deleted the hits; its first run is the evidence, and a remaining hit is deleted in the owning file by this task, named in the commit body.
- Pre-review checklist: one ceiling per ratchet (never raised); no cross-component import; the sweep lines of AC4.1 and G3 (`git grep -n 'noqa: E402' -- dadaia_workspace` target 0; `git grep -c '_SKILL_SCRIPT' -- dadaia_workspace tests` target 0) with counts in T3's body; no platform fact; net lines ≤ 0.

Tasks: 3 (2 jr, 1 sr). `who` names the dispatched role (`dd-release-definition` §5).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J15.T1 | jr | AC4.1, AC11.4 | `scripts/guards/slop.py`, `scripts/guards/suite.py` | lower the four ceilings to the measured counts at this base (never raise one). Owner `python scripts/guards/run.py` and `--planted` exit 0 |
| J15.T2 | jr | AC11.4 | `dadaia_workspace/hooks/ctx_inject.py` | the one `now` read of `ctx_inject` goes through `core.clock`; the hook's tests stay green unedited |
| J15.T3 | sr | AC4.1 | `tests/infrastructure/test_privacy_check.py` | the pattern line of the intro. If its first run finds a hit, the task stops and returns the list to the main thread (it writes only its own file). Owner this file |
