# PLAN — Release 0.5.2

**Status:** Aprovado

- Order: ledger corrections → code fixes (TDD) → lib skill + reprojection → measurements → disposition sweep → memory (CLOSURE) → closure narrative.
- T-052-01 (F001/F003): `dadaia bugs update <id> --set caused_by=<parent>` ×2; verify by re-reading the fold.
- T-052-02 (F010): RED test in `tests/unit/core/` asserting a single-registration-line commit staging only `specs/bugs/BUGS.jsonl` derives `registration_granularity="exact"`; fix `_granularity` to take the line kind into account (registration vs resolution); resolution semantics unchanged (`ledger-only` remains the sweep smell for resolutions).
- T-052-03 (F015/F036): RED test in `tests/unit/features/chokepoints/` — `pre_commit_decision` over a staged set holding `specs/bugs/BUGS.jsonl` plus another `specs/**` path yields one advisory warn naming FR8 isolation; allowed stays True always (NO-LOCKS). Wire staged-paths input at the CLI composition root.
- T-052-04 (F016): add shape 6 to `dadaia_workspace/public/skills/dd-gitflow-default/SKILL.md` §4; `dadaia public stage` → `install --target all` → `public doctor`; re-record behavior-map hash if flagged.
- T-052-05 (F033): `python -m venv` in scratch, `pip install vulture==<pin>`, run over `dadaia_workspace/`, record findings count + verdict in F033's reason (delete anything genuinely dead it proves, if trivial).
- T-052-06: rewrite the 32 finding records (disposition/release/reason); append audit summary to `audits_histo.jsonl`; remove the audit directory (git rm).
- T-052-07 (F041 + closure): CLOSURE phase — QUALITY.md P-21 Measured-by names the three timeout node ids; closure `log` entries; final preflight (`ruff format --check`, `ruff check`, `mypy --strict`, `pytest`).
- Bug rider: fix `backlog-new-append-reported-as-created` (message states append vs create), shape 3.
