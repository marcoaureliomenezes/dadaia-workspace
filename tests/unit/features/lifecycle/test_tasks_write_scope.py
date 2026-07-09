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
