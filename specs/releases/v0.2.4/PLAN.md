# Plan: Hotfix Release - v0.2.4

> **Status:** Aprovado

1. Change the shared Claude hook command builder to emit `python -B -m`.
2. Change all generated Codex wrappers to execute `python -B -m`.
3. Change the PI extension subprocess arguments to `-B -m`.
4. Add static assertions for all three projections and an executed Codex-wrapper test that
   starts in a source-shaped repository and proves no bytecode appears.
5. Restage/install public assets, run focused tests and doctors, clean pre-fix bytecode,
   resolve the bug, and archive the hotfix.
