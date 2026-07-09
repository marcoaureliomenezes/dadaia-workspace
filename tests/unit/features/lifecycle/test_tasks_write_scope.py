"""FR3 (v0.1.68) — ``write_scope_from_tasks`` grammar (SPEC FR3.1 / AC3.3).

Grammar under test (deterministic, architect F3):

- **Reserved task:** the task whose marker is ``[-]``. If NOT exactly one ``[-]``
  exists (zero, or multiple), return ``()`` — never guess.
- **Write-set line:** the ``Write set:`` bullet within that task's block, up to the
  next ``- **``/``###`` bullet or a blank line (multi-line continuation joined).
- **Glob extraction:** backtick-delimited spans that are path-shaped (contain ``/`` or
  a filename extension) AND appear before the first ``(`` on the line. A trailing
  parenthetical annotation is stripped; its inner backticks are NOT captured.
- ``none`` (case-insensitive) ⇒ ``()``.
- Absent TASKS.md / no releases dir ⇒ ``()`` (no crash).

RED-first (T-68-05): every assertion below FAILS on current code because
``write_scope_from_tasks`` does not exist yet (ImportError). After T-68-06 lands the
resolver, every case passes.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.lifecycle.tasks_write_scope import write_scope_from_tasks

_RELEASE = "v-grammar-test"


def _write_tasks(specs_dir: Path, body: str) -> None:
    tasks_dir = specs_dir / "releases" / _RELEASE
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / "TASKS.md").write_text(body, encoding="utf-8")


def test_single_glob_write_set(tmp_path: Path) -> None:
    _write_tasks(
        tmp_path,
        """# TASKS

### T-1 — do a thing `[-]`
- **Owner:** software-engineer
- **Write set:** `foo/bar.py`
- **Task:** do the thing.
""",
    )
    assert write_scope_from_tasks(tmp_path, _RELEASE) == ("foo/bar.py",)


def test_comma_separated_multi_glob_both_captured(tmp_path: Path) -> None:
    """AC3.3(i): a comma-separated multi-glob line captures BOTH paths."""
    _write_tasks(
        tmp_path,
        """# TASKS

### T-1 — do a thing `[-]`
- **Owner:** software-engineer
- **Write set:** `a/b.py`, `c/d.py`
- **Task:** do the thing.
""",
    )
    assert write_scope_from_tasks(tmp_path, _RELEASE) == ("a/b.py", "c/d.py")


def test_annotation_with_backticks_inner_token_not_captured(tmp_path: Path) -> None:
    """AC3.3(ii): a trailing parenthetical annotation containing backticks — only the
    path before the first ``(`` is captured; the annotation's inner backtick token
    (e.g. a function name) is NOT captured as a path."""
    _write_tasks(
        tmp_path,
        """# TASKS

### T-1 — do a thing `[-]`
- **Owner:** software-engineer
- **Write set:** `a/b.py` (`some_func` only)
- **Task:** do the thing.
""",
    )
    assert write_scope_from_tasks(tmp_path, _RELEASE) == ("a/b.py",)


def test_write_set_none_case_insensitive(tmp_path: Path) -> None:
    """AC3.3(iii): ``Write set: none`` (any case) ⇒ ``()``."""
    _write_tasks(
        tmp_path,
        """# TASKS

### T-1 — do a thing `[-]`
- **Owner:** qa-engineer
- **Write set:** None
- **Task:** do the thing.
""",
    )
    assert write_scope_from_tasks(tmp_path, _RELEASE) == ()


def test_write_set_none_lowercase(tmp_path: Path) -> None:
    _write_tasks(
        tmp_path,
        """# TASKS

### T-1 — do a thing `[-]`
- **Write set:** none
""",
    )
    assert write_scope_from_tasks(tmp_path, _RELEASE) == ()


def test_not_exactly_one_reserved_task_zero(tmp_path: Path) -> None:
    """AC3.3(iv): zero ``[-]`` tasks ⇒ ``()`` — never guess."""
    _write_tasks(
        tmp_path,
        """# TASKS

### T-1 — do a thing `[ ]`
- **Write set:** `foo/bar.py`

### T-2 — do another thing `[x]`
- **Write set:** `baz/qux.py`
""",
    )
    assert write_scope_from_tasks(tmp_path, _RELEASE) == ()


def test_not_exactly_one_reserved_task_multiple(tmp_path: Path) -> None:
    """AC3.3(iv): multiple ``[-]`` tasks ⇒ ``()`` — never guess which one."""
    _write_tasks(
        tmp_path,
        """# TASKS

### T-1 — do a thing `[-]`
- **Write set:** `foo/bar.py`

### T-2 — do another thing `[-]`
- **Write set:** `baz/qux.py`
""",
    )
    assert write_scope_from_tasks(tmp_path, _RELEASE) == ()


def test_absent_tasks_file_returns_empty(tmp_path: Path) -> None:
    """No TASKS.md at all ⇒ ``()``, never a crash."""
    assert write_scope_from_tasks(tmp_path, _RELEASE) == ()


def test_absent_releases_dir_returns_empty(tmp_path: Path) -> None:
    """No ``releases/`` dir at all ⇒ ``()``, never a crash."""
    assert write_scope_from_tasks(tmp_path, "no-such-release") == ()


def test_multiline_continuation_joined(tmp_path: Path) -> None:
    """The Write-set bullet may continue onto following indented lines up to the next
    bullet/blank line; continuation lines are joined before extraction."""
    _write_tasks(
        tmp_path,
        """# TASKS

### T-1 — do a thing `[-]`
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/container.py`,
  `dadaia_workspace/features/lifecycle/agent_runner.py`,
  `tests/integration/cli/test_x.py` (FR1.5 — invert FR8 assertion)
- **Preconditions:** none
""",
    )
    assert write_scope_from_tasks(tmp_path, _RELEASE) == (
        "dadaia_workspace/container.py",
        "dadaia_workspace/features/lifecycle/agent_runner.py",
        "tests/integration/cli/test_x.py",
    )


def test_non_path_shaped_backtick_token_not_captured(tmp_path: Path) -> None:
    """A backtick span with no ``/`` and no file extension (e.g. a bare function or
    flag name) is not path-shaped and must not be captured."""
    _write_tasks(
        tmp_path,
        """# TASKS

### T-1 — do a thing `[-]`
- **Write set:** `run_implement_review_loop` only
""",
    )
    assert write_scope_from_tasks(tmp_path, _RELEASE) == ()


def test_stops_at_next_bullet(tmp_path: Path) -> None:
    """The Write-set line stops at the next ``- **`` bullet, never bleeding into it."""
    _write_tasks(
        tmp_path,
        """# TASKS

### T-1 — do a thing `[-]`
- **Owner:** software-engineer
- **Write set:** `foo/bar.py`
- **Task:** something involving `unrelated/path.py` mentioned in prose.
""",
    )
    assert write_scope_from_tasks(tmp_path, _RELEASE) == ("foo/bar.py",)


def test_stops_at_blank_line(tmp_path: Path) -> None:
    _write_tasks(
        tmp_path,
        """# TASKS

### T-1 — do a thing `[-]`
- **Write set:** `foo/bar.py`

Some unrelated prose mentioning `other/path.py` after a blank line.
""",
    )
    assert write_scope_from_tasks(tmp_path, _RELEASE) == ("foo/bar.py",)


def test_file_extension_without_slash_is_path_shaped(tmp_path: Path) -> None:
    """A bare filename with an extension (no ``/``) is still path-shaped."""
    _write_tasks(
        tmp_path,
        """# TASKS

### T-1 — do a thing `[-]`
- **Write set:** `pyproject.toml`
""",
    )
    assert write_scope_from_tasks(tmp_path, _RELEASE) == ("pyproject.toml",)


# --------------------------------------------------------------------------------------
# v0.1.71 FR1 — the REAL consumer grammar (bug pipeline-write-scope-parser-wrong-grammar).
#
# The v0.1.68 parser only recognized the internal grammar (H3 heading + inline `[-]`
# marker + bold `**Write set:**` key + single trailing parenthetical). Real dd-chain-capture
# releases use a DIFFERENT grammar the parser silently returned () for:
#   - task heading is a **bold line** `**T-3.1 — …**` (not `###`),
#   - the active marker is a **fenced block** ```\n[-] T-3.1\n``` elsewhere in the file,
#   - the write-set key is **plain** `- Write set:` (not bold),
#   - each path carries its OWN trailing parenthetical `(new)`, `(reuse …)`.
# These are the axis the arc missed: fixtures were internal-only. The canonical fixture
# is the REAL dd-chain-capture v0.2.0 TASKS.md, committed verbatim.
# --------------------------------------------------------------------------------------

_DDCC_SPECS = Path(__file__).parents[3] / "fixtures" / "tasks" / "ddcc-specs"

_CONSUMER_T31 = """# TASKS: Release v0.2.0

**T-3.1 — Inbound `getUpdates` listener (no inbound port, no replay)** (HOP-1.3; FR-3.1)
- Owner: software-engineer
- Write set: `docker/hermes-capture/workspace/scripts/telegram_listener.py` (new),
  `docker/hermes-capture/supervisord.conf` (listener program),
  `docker/hermes-capture/workspace/scripts/secret_resolver.py` (reuse — no change expected)
- Precondition: Phase 1 complete

```
[-] T-3.1
```

**T-3.2 — Deterministic command handlers** (HOP-1.3; FR-3.2)
- Write set: `docker/hermes-capture/workspace/scripts/telegram_listener.py`

```
[ ] T-3.2
```
"""


def test_real_ddcc_v0_2_0_fixture_resolves_t31_write_set() -> None:
    """The REAL dd-chain-capture v0.2.0 TASKS.md (fixture, verbatim) with `[-] T-3.1`
    must yield T-3.1's three declared paths — the exact case that returned () on the
    remote against installed 574a84bd."""
    assert write_scope_from_tasks(_DDCC_SPECS, "v0.2.0") == (
        "docker/hermes-capture/workspace/scripts/telegram_listener.py",
        "docker/hermes-capture/supervisord.conf",
        "docker/hermes-capture/workspace/scripts/secret_resolver.py",
    )


def test_consumer_grammar_bold_heading_fenced_marker_plain_key(tmp_path: Path) -> None:
    """Consumer grammar: bold `**T-x —**` heading + fenced `[-] T-x` marker + plain
    `- Write set:` key + per-path parentheticals → all three paths captured."""
    _write_tasks(tmp_path, _CONSUMER_T31)
    assert write_scope_from_tasks(tmp_path, _RELEASE) == (
        "docker/hermes-capture/workspace/scripts/telegram_listener.py",
        "docker/hermes-capture/supervisord.conf",
        "docker/hermes-capture/workspace/scripts/secret_resolver.py",
    )


def test_consumer_grammar_per_path_parenthetical_not_a_terminator(tmp_path: Path) -> None:
    """A parenthetical after the FIRST path must not truncate the rest (the old
    ``split('(', 1)[0]`` bug kept only path #1)."""
    _write_tasks(
        tmp_path,
        """# TASKS

**T-9.9 — thing** (EPIC)
- Write set: `a/one.py` (new), `b/two.py` (reuse — no change)

```
[-] T-9.9
```
""",
    )
    assert write_scope_from_tasks(tmp_path, _RELEASE) == ("a/one.py", "b/two.py")


def test_consumer_grammar_zero_reserved_across_fenced_markers(tmp_path: Path) -> None:
    """No `[-]` among fenced markers ⇒ () — never guess."""
    _write_tasks(
        tmp_path,
        """# TASKS

**T-1 — a** (E)
- Write set: `a/one.py`

```
[x] T-1
```

**T-2 — b** (E)
- Write set: `b/two.py`

```
[ ] T-2
```
""",
    )
    assert write_scope_from_tasks(tmp_path, _RELEASE) == ()


def test_consumer_grammar_multiple_reserved_across_fenced_markers(tmp_path: Path) -> None:
    """Two `[-]` fenced markers ⇒ () — ambiguous, never guess."""
    _write_tasks(
        tmp_path,
        """# TASKS

**T-1 — a** (E)
- Write set: `a/one.py`

```
[-] T-1
```

**T-2 — b** (E)
- Write set: `b/two.py`

```
[-] T-2
```
""",
    )
    assert write_scope_from_tasks(tmp_path, _RELEASE) == ()
