# dadaia-context

Show the active dadaia-workspace Spec Context Project, its lifecycle phase, and the
SDD health of the workspace, then orient on what to do next.

Run, using the workspace venv `dadaia` binary:

1. `dadaia context show --json` — the active Spec Context Project and phase.
2. `dadaia specs doctor` — SDD structural health (resolve any errors before editing).

If there is an active release in IMPLEMENTATION, read its `TASKS.md` and reserve an
OPEN task (`[ ]` → `[-]`) before touching any production file. If no context is ALIVE,
report that there is nothing to work on and stop. Follow the binding `AGENTS.md` for
the full SDD discipline — this prompt only invokes the affordance, it does not restate
the law.
