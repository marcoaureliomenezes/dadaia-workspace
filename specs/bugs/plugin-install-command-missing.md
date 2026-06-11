---
name: plugin-install-command-missing
status: Closed
closed: 2026-06-11
fixed_by: v0.1.11
severity: MEDIUM
session_id: null
reported: 2026-06-10
surface: dadaia CLI (plugin subcommand) vs plugin-scope rule
---

**Symptom:** The projected `plugin-scope` rule (and agent stubs for `frontend-engineer`, `design-specialist`, `devops-engineer`) instructs: "Install with: `dadaia plugin install <name>`". The CLI has no such command: `dadaia plugin install devops` → `Error: No such command 'plugin'`.

**Repro:** In a consumer or self-hosting workspace, run `<ws>/.dadaia/.venv/bin/dadaia plugin install devops`. Exit non-zero, "No such command 'plugin'".

**Expected:** Either the `dadaia plugin` command group exists and installs the named plugin packs, or the plugin-scope rule/stubs must not reference a nonexistent command. As shipped, any workflow that legitimately needs a plugin agent (e.g. CI/CD work routed to `devops-engineer`) dead-ends: the core agent refuses with `[PLUGIN REQUIRED] ... Install with: dadaia plugin install devops`, and the install command does not exist.

**Notes:** Hit during a real release (CI workflow authoring task blocked). Impact: plugin-domain tasks are unroutable without operator hand-authoring. Workaround used: operator-proxy authored the CI YAML directly, decision recorded in the release artifacts. Version: v0.1.10 line.

**Resolution (v0.1.11, 2026-06-11):** Honest-relabel per ADR-4 (verified at definition:
no plugin pack assets exist anywhere under `dadaia_workspace/` — an install command would
have nothing to install). The `plugin-scope` rule and the 3 plugin stubs no longer
reference the nonexistent command; `[PLUGIN REQUIRED]` wording states packs are not yet
distributed and routes to the operator with the backlog pointer (T-011-12). Pinned
permanently by `tests/contract/test_plugin_install_residue.py::test_no_plugin_install_references_under_public`.
The real feature (plugin pack distribution + a working `dadaia plugin install`) is
registered as backlog return `specs/backlog/plugin-packs-and-install-command.md`.
Verified at `feature/v0.1.11 @ e1f2de3`.
