# PLAN — Release v0.1.77 — Central bind-resolution seam

**Status:** Aprovado

## Approach

1. **T-1 (RED):** dynamic Typer-walk contract test (`tests/contract/`): walk
   `cli/main.py`'s app tree, classify resolver-driven subcommands (those exposing
   `--context`/`--specs-dir` or documented as context-scoped), and for each assert the
   bind-visibility contract (bind `<ctx>` → verb resolves `<ctx>`); read-only probe or
   seam-call assertion for verbs with side effects. Import-boundary lint contract in
   setup.cfg (new import-linter contract: only `cli/_specs_resolution.py` + the seam's
   own module may import the resolution internals). RED against HEAD (hardcoded
   defaults + private show algorithm fail it).
2. **T-2:** generalize the seam (`cli/_specs_resolution.py`): one function family
   `resolve_context_for_cli(explicit: str | None) -> str` + existing
   `resolve_specs_dir_for_cli`; canonical order per SPEC FR1. Fold `context show`
   no-arg resolution into it. Retire the 15 hardcoded lifecycle defaults
   (`None`-default → seam). Update `--help` epilogs. Make T-1 green.
3. **T-3:** full validation + ship gates (suite, mypy, ruff, lint-imports incl. the
   new contract, doctors, QA + security, push/PR/CI/merge/closure).

## Risks

- Consumer-visible default change (FR2): a consumer running lifecycle verbs unbound
  and relying on the literal "dadaia-workspace" default breaks — mitigated by the
  seam's first-ALIVE fallback + a clear resolution-failure message naming
  `dadaia context bind`.
- Typer `None`-default changes help output — tests pinning `--help` strings may need
  updates (fix the pins, honestly).
