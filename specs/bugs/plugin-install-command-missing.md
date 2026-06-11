---
name: plugin-install-command-missing
status: Open
severity: MEDIUM
session_id: null
reported: 2026-06-10
surface: dadaia CLI (plugin subcommand) vs plugin-scope rule
---

**Symptom:** The projected `plugin-scope` rule (and agent stubs for `frontend-engineer`, `design-specialist`, `devops-engineer`) instructs: "Install with: `dadaia plugin install <name>`". The CLI has no such command: `dadaia plugin install devops` → `Error: No such command 'plugin'`.

**Repro:** In a consumer or self-hosting workspace, run `<ws>/.dadaia/.venv/bin/dadaia plugin install devops`. Exit non-zero, "No such command 'plugin'".

**Expected:** Either the `dadaia plugin` command group exists and installs the named plugin packs, or the plugin-scope rule/stubs must not reference a nonexistent command. As shipped, any workflow that legitimately needs a plugin agent (e.g. CI/CD work routed to `devops-engineer`) dead-ends: the core agent refuses with `[PLUGIN REQUIRED] ... Install with: dadaia plugin install devops`, and the install command does not exist.

**Notes:** Hit during a real release (CI workflow authoring task blocked). Impact: plugin-domain tasks are unroutable without operator hand-authoring. Workaround used: operator-proxy authored the CI YAML directly, decision recorded in the release artifacts. Version: v0.1.10 line.
