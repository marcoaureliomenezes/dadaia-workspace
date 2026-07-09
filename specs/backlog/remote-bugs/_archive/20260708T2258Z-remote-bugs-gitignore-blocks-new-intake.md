# remote-bugs backlog intake is ignored by gitignore

- Bug ID: `remote-bugs-gitignore-blocks-new-intake`
- Severity: HIGH
- Surface: `specs/backlog/remote-bugs/*.md` intake
- Component: repository `.gitignore` / backlog governance
- Reported: 2026-07-08T22Z
- Event stream mirror: `repos/dadaia-workspace/specs/bugs/20260708T22Z-00.jsonl`

## Symptom

New Markdown reports under `specs/backlog/remote-bugs/` are ignored by the repository
`.gitignore`, even though the workspace uses that directory for active remote bug
intake. Existing files in that directory are tracked only because they were already in
the Git index.

Observed:

```bash
git -C repos/dadaia-workspace check-ignore -v \
  specs/backlog/remote-bugs/20260708T2239Z-codex-thread-id-bind-resolution-breaks-cli.md
```

Result:

```text
.gitignore:134:/specs/backlog/* specs/backlog/remote-bugs/...
```

## Reproduction

Create a new report:

```text
specs/backlog/remote-bugs/<new>.md
```

Then run:

```bash
git -C repos/dadaia-workspace status --short --untracked-files=all
git -C repos/dadaia-workspace check-ignore -v specs/backlog/remote-bugs/<new>.md
```

The file is ignored by the broad `/specs/backlog/*` rule.

## Expected

If `specs/backlog/remote-bugs/` is a supported remote bug intake surface, then these
paths should be explicitly opted in:

```text
!/specs/backlog/remote-bugs/
!/specs/backlog/remote-bugs/*.md
!/specs/backlog/remote-bugs/_archive/
!/specs/backlog/remote-bugs/_archive/*.md
```

The behavior should match the `.gitignore` comment that says backlog Markdown is
PM-curated repository truth.

## Impact

Critical triage notes can be left on disk but omitted from commits/releases, making
remote bug intake unreliable unless the operator remembers to force-add each file.

## Fix Direction

Update `.gitignore` to explicitly unignore `specs/backlog/remote-bugs/*.md` and its
archive directory, then add regression coverage or a repo hygiene check that catches
ignored governance intake paths.
