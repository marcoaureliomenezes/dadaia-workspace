# Job 4 — one context-name grammar (FR3)

**Status:** Draft

Wave 2, the kernel owner before the verdict job (Job 8 waits on this one). Bug `verdict-context-pattern-disagrees-with-core`: `verdict.py` allows `^[a-z0-9][a-z0-9-]*$`, core registers `[A-Za-z0-9_-]+`, so a context core accepts cannot receive a verdict. The kernel `_grammar.CONTEXT_NAME_RE` becomes the one definition; `core/models/spec_context.py` loads it with `load_owner` (precedent: `core/models/git_scan.py:23`); `verdict.py` keeps an allowlist check against it because it builds `.dadaia/handoff/<context>` from the name (CWE-22: `.`, `/` and `\` stay outside the class).

- **Seams closed.**
  - `core/models/spec_context.py` keeps exporting the name `CONTEXT_NAME_RE`, so its five importers and `tests/core/test_session_store.py:119` are untouched.
  - The refusal text stays `--context must match <pattern>`; the pattern printed is the kernel's.
  - The prompt-path import now execs one small stdlib file: T3's commit body states `python -X importtime -c 'import dadaia_workspace.core.models.spec_context'` before and after (evidence, not a gate).
  - **Operator order, 2026-10-13 (AskUserQuestion): "Mover as linhas (Recommended)".** The parametrised refusal at `test_verdict.py:182-194` lists `_x` and `A` as refused values of `--context`; under the shared grammar both are valid contexts. The refused literals that climb out (`../../evil`, `a/b`, `a\b`, empty) stay refused for `--context`, and all six stay refused for `--slug`. Splitting the parametrisation moves two rows from the refused to the accepted partition, by that order; `--context` accepts exactly what the core grammar accepts. J4.T2 quotes the order in its `test(...)` commit.
- **Consumers.** `verdict.py` only widens (accepts `_` and capitals). Sweep: `git grep -n 'A-Za-z0-9_-\|a-z0-9\]\[a-z0-9-' -- dadaia_workspace` (other copies are messages or other questions: `session_store.py:35`, `service.py:117`, `invocation.py:52`).
- Test-side first: T1, T2. Then T3.
- Pre-review checklist: one definition; the only edge added into `core` is the loader; sweep above; no platform fact; net lines about 0.

Tasks: 3 (0 jr, 3 sr). `who` names the dispatched role (`dd-release-definition` §5).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J4.T1 | sr | AC3.1 | `tests/public/skills/dd_handoff_emitter/scripts/test_verdict.py` | RED, integration (new case): `--context My_Ctx` writes under `.dadaia/handoff/My_Ctx/`; `A` and `_x` are accepted. The existing parametrisation is untouched in this commit |
| J4.T2 | sr | AC3.1 | `tests/public/skills/dd_handoff_emitter/scripts/test_verdict.py` | the ordered change of the intro: split the parametrisation, keeping every refused literal of `--slug` and the four climbing literals of `--context`; the `test(J4.T2)` commit quotes "Mover as linhas (Recommended)". After T1 |
| J4.T3 | sr | AC3.1, AC3.2 | `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_grammar.py`, `dadaia_workspace/core/models/spec_context.py`, `dadaia_workspace/public/skills/dd-handoff-emitter/scripts/verdict.py` | the constant moves to `_grammar`, core loads it, `_CONTEXT` leaves `verdict.py`. Fix commit of the bug; Phase 0 block `caused_by: none`, `rebuild: none` (placement change). Owners T1, T2. After T1, T2 |
