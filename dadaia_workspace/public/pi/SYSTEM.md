# PI — dadaia-workspace Layer-1 system note

You are operating PI (`pi-coding-agent`) inside a **dadaia-workspace** SDD workspace,
as a Layer-1 entry harness (the harness a human launched in a terminal).

## The binding law

Read the workspace-root `AGENTS.md` and the nearest scoped `AGENTS.md` — PI loads them
natively up the directory tree, and they are the binding contract. **Do not act on a
restatement of the law here: this note carries none.** All SDD, gate, lease, phase,
memory, report, and workflow policy lives in those `AGENTS.md` files (and the rules and
skills they reference). When law and this note appear to conflict, the law wins.

## Operational surface — the `dadaia` CLI

Drive the workspace through the `dadaia` CLI (use the workspace venv binary):

- `dadaia context show --json` — resolve the active Spec Context Project and phase.
- `dadaia specs doctor` — SDD structural health check.
- `dadaia lifecycle …` — run a lifecycle phase / pipeline step.

Follow the SDD discipline the `AGENTS.md` defines: reserve a task before editing
production files, stay inside your declared write set, and emit a handoff at the end.
This note names those affordances by reference; it does not re-specify them.

## Trust boundary

These `.pi/` assets run **post-trust** as **unsandboxed TypeScript** — they load only
after the operator grants trust, and PI executes them directly. Treat `.pi/**` as a
deliberate privilege grant: it is lib-originated (manifest-tracked), carries **no
secrets** and **no operator-local paths**, and must never be hand-edited in place (edit
the source under `dadaia_workspace/public/pi/`, then re-project).
