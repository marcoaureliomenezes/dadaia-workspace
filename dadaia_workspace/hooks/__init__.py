"""Cross-platform Python governance hooks (Windows-safe, 0.1.8).

The bash governance hooks (``public/scripts/*.sh``) are dead on stock Windows — no
Git Bash on a default install — so they are reimplemented here as a Python package the
harness invokes directly via ``python -m dadaia_workspace.hooks.<name>``. The Python
modules are behavior-for-behavior ports of the shell hooks (the rc-4 lock-correctness
invariants are preserved exactly); see the parity tests under ``tests/unit/hooks/``.

Modules
-------
- ``_common``        — shared stdin/stdout envelope, python-bin resolution, session-id
                       sanitization (CWE-22), atomic ``os.replace`` helper.
- ``sdd_gate``       — PreToolUse SDD gate; delegates to ``gate_policy.evaluate()`` /
                       ``classify_path()`` (no policy re-derivation).
- ``root_whitelist`` — PreToolUse workspace-root whitelist gate.
- ``ctx_inject``     — SessionStart / UserPromptSubmit context-injection hook.
- ``sdd_post_gate``  — PostToolUse session heartbeat renewal.

``pre_push_ci.py`` is intentionally NOT part of this package — the ``.sh`` pre-push hook
is retained (git-for-Windows ships bash, so it survives on Windows).
"""
