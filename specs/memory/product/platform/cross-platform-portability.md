---
slug: cross-platform-portability
title: cross-platform-portability
tldr: Linux, macOS and Windows through one OS boundary, the kernel's _platform.py, deciding every host fact; core/platform.py is the package's door to it.
summary: The kernel module dd-bug-resolution/scripts/_platform.py decides every host fact — text codec and newlines, child processes, venv layout, exec bit, process liveness and listeners, filesystem swap and links, the sandbox home and shell spelling — as functions over one capability value; skill scripts import it as a sibling, the package reaches it through core/platform.py, tests through tests/helpers/oslib.py; no port, adapter pair or file lock exists for portability.
tags: [platform, cross-platform, portability, windows, macos, linux]
sources:
  - dadaia_workspace/core/platform.py
  - dadaia_workspace/public/skills/dd-bug-resolution/scripts/_platform.py
---

## The boundary

- The package imports and the CLI starts on Linux, macOS and Windows with no platform check scattered in feature code: the kernel's `dd-bug-resolution/scripts/_platform.py` is the one module that reads `sys.platform` or spells a shell word, shared by the package and every skill script ([[bug-ledger]]).
- Each host fact is one kernel function over a `Caps` value (`scripts_dir` `bin`/`Scripts`, `exe_suffix` empty/`.exe`, `windows`): the venv layout (`venv_dir`, `venv_tool`, `python_in`, `cli_path`, `cli_argv`), path rooting and separators, the exec bit, process liveness, listeners and file owner, the atomic swap and links, the variables a child reads its home from, text I/O and child processes.
- `core/platform.py` is the package's door: its `PLATFORM` singleton (`venv_scripts_dir`, `venv_exe_suffix`, `windows`) is the current host's capabilities, each door function feeds it to the kernel, and the functions that read no capability are handed out unchanged; `python_in` also takes another host's capabilities, so a renderer spells a file for a host it does not run on; a test swaps `PLATFORM` to judge another host. Tests reach the OS only through `tests/helpers/oslib.py`, which re-exports the kernel.
- Text is UTF-8 with LF on every host: a read of bytes that are not UTF-8 is refused with an `Agent action:` to re-encode the named line of that file in place, the doctor reports such a file once per path as `SPEC-DOC-002` ([[workspace-doctor]]); child output is decoded as UTF-8 with bad bytes replaced, and every entry point makes its stdout and stderr UTF-8.
- On Windows a held-open destination of an atomic swap is retried briefly before the swap raises; a junction counts as a link; a symlink the host refuses falls back to a copy ([[public-asset-distribution]]).

## Shell spelling

- Every runnable line a fix or message prints comes from one producer, the kernel's `command(*argv)`, with real values; `inline` is the same words inside a sentence, and `quote` and `head` spell one word. `core/cli_line.py` builds the workspace CLI's words and hands them to it ([[sdd-gate-v3]]).
- POSIX spells each word with `shlex` quoting. Windows spells backslashes as `/`, leaves letters and digits of any alphabet and `._-/:+` bare (`=` too, except in the command head), and wraps any other word, a number-like word and the empty word in double quotes — the one form Git Bash, cmd and PowerShell all read alike.
- On Windows a word holding `"`, `$`, `` ` ``, `%`, `!`, a line break, a typographic quote or a Unicode space other than blank and tab has no spelling, nor has a command head that would need quotes (a head holding a blank among them). A line with such a word is printed as `Agent action: run <the words as they are>, quoting <word> for your shell`, never as a runnable line.
- A test hands printed lines to every installed shell (Git Bash, cmd, PowerShell where present) and checks the words come back unchanged.

## Validation

- Portability needs no port and no adapter pair: `container.py` selects nothing per platform, and no file lock exists anywhere — context and session state are coordinated without locking.
- `core` imports no OS primitive (`fcntl`, `signal`, `subprocess`, `msvcrt`); the import-linter contract `core-no-os-primitives` measures it ([[ARCHITECTURE]] P-03).
- Harness governance hooks are Python modules invoked through per-harness wrappers (sh scripts, or `cmd.exe` batches where a harness's Windows shell is cmd); the git hooks are shell shims that find the workspace venv and run Python behind the boundary ([[sdd-gate-v3]]).
- Skill scripts are stdlib Python; the dev-server registry judges a PID's liveness on every host and lists listeners only where `/proc` and `ss` exist ([[server-registry]]).
- CI runs Windows and macOS legs beside Linux, and `pyproject.toml` declares exactly those three OS classifiers.

## Dependencies

[[workspace-init]], [[sdd-gate-v3]], [[ARCHITECTURE]], [[public-asset-distribution]], [[server-registry]], [[bug-ledger]], [[workspace-doctor]].
