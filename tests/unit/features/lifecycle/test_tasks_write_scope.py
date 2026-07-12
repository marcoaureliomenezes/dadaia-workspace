"""FR3 (v0.1.68) — ``write_scope_from_tasks`` grammar (SPEC FR3.1 / AC3.3).

Grammar under test (deterministic, architect F3):

- **Reserved task:** the task whose marker is ``[-]``. If NOT exactly one ``[-]``
  exists (zero, or multiple), return ``()`` — never guess.
- **Write-set line:** the ``Write set:`` bullet within that task's block, up to the
  next ``- **``/``###`` bullet or a blank line (multi-line continuation joined).
- **Glob extraction:** backtick-delimited spans that are path-shaped (contain ``/`` or
  a filename extension) AND appear before the first ``(`` on the line. A trailing
  parenthetical annotation is stripped; its inner backticks are NOT captured.
- ``none`` (case-insensitive) => ``()``.
- Absent TASKS.md / no releases dir => ``()`` (no crash).

CRITICAL: never-guess ambiguity (() on 0/N reserved) + real-consumer fixture — this
output feeds the write-scope union in the gate.

v0.1.71 FR1 — the REAL consumer grammar (bug pipeline-write-scope-parser-wrong-grammar).
The v0.1.68 parser only recognized the internal grammar (H3 heading + inline `[-]` marker
+ bold `**Write set:**` key + single trailing parenthetical). Real dd-chain-capture
releases use a DIFFERENT grammar the parser silently returned () for:
  - task heading is a **bold line** `**T-3.1 - ...**` (not `###`),
  - the active marker is a **fenced block** ```\\n[-] T-3.1\\n``` elsewhere in the file,
  - the write-set key is **plain** `- Write set:` (not bold),
  - each path carries its OWN trailing parenthetical `(new)`, `(reuse ...)`.
These are the axis the arc missed: fixtures were internal-only. The canonical fixture is
the REAL dd-chain-capture v0.2.0 TASKS.md, committed verbatim (v0.1.71 real-consumer law).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.lifecycle.tasks_write_scope import (
    _extract_globs,
    write_scope_from_tasks,
)

_RELEASE = "v-grammar-test"


def _write_tasks(specs_dir: Path, body: str) -> None:
    tasks_dir = specs_dir / "releases" / _RELEASE
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / "TASKS.md").write_text(body, encoding="utf-8")


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
    `- Write set:` key + per-path parentheticals -> all three paths captured."""
    _write_tasks(tmp_path, _CONSUMER_T31)
    assert write_scope_from_tasks(tmp_path, _RELEASE) == (
        "docker/hermes-capture/workspace/scripts/telegram_listener.py",
        "docker/hermes-capture/supervisord.conf",
        "docker/hermes-capture/workspace/scripts/secret_resolver.py",
    )


# --- ① internal-grammar positives param -------------------------------------------------

_POSITIVE_CASES = (
    (
        "single-glob",
        """# TASKS

### T-1 — do a thing `[-]`
- **Owner:** software-engineer
- **Write set:** `foo/bar.py`
- **Task:** do the thing.
""",
        ("foo/bar.py",),
    ),
    (
        "comma-separated-multi-glob",
        """# TASKS

### T-1 — do a thing `[-]`
- **Owner:** software-engineer
- **Write set:** `a/b.py`, `c/d.py`
- **Task:** do the thing.
""",
        ("a/b.py", "c/d.py"),
    ),
    (
        "annotation-inner-backtick-not-captured",
        """# TASKS

### T-1 — do a thing `[-]`
- **Owner:** software-engineer
- **Write set:** `a/b.py` (`some_func` only)
- **Task:** do the thing.
""",
        ("a/b.py",),
    ),
    (
        "multiline-continuation-joined",
        """# TASKS

### T-1 — do a thing `[-]`
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/container.py`,
  `dadaia_workspace/features/lifecycle/agent_runner.py`,
  `tests/integration/cli/test_x.py` (FR1.5 — invert FR8 assertion)
- **Preconditions:** none
""",
        (
            "dadaia_workspace/container.py",
            "dadaia_workspace/features/lifecycle/agent_runner.py",
            "tests/integration/cli/test_x.py",
        ),
    ),
    (
        "bare-extension-no-slash-is-path-shaped",
        """# TASKS

### T-1 — do a thing `[-]`
- **Write set:** `pyproject.toml`
""",
        ("pyproject.toml",),
    ),
    (
        "stops-at-next-bullet",
        """# TASKS

### T-1 — do a thing `[-]`
- **Owner:** software-engineer
- **Write set:** `foo/bar.py`
- **Task:** something involving `unrelated/path.py` mentioned in prose.
""",
        ("foo/bar.py",),
    ),
    (
        "stops-at-blank-line",
        """# TASKS

### T-1 — do a thing `[-]`
- **Write set:** `foo/bar.py`

Some unrelated prose mentioning `other/path.py` after a blank line.
""",
        ("foo/bar.py",),
    ),
)


@pytest.mark.parametrize(
    "body,expected",
    [c[1:] for c in _POSITIVE_CASES],
    ids=[c[0] for c in _POSITIVE_CASES],
)
def test_internal_grammar_positive_matrix(
    tmp_path: Path, body: str, expected: tuple[str, ...]
) -> None:
    _write_tasks(tmp_path, body)
    assert write_scope_from_tasks(tmp_path, _RELEASE) == expected


# --- ② none + non-path-token -> () param -------------------------------------------------

_NONE_CASES = (
    (
        "write-set-none-titlecase",
        """# TASKS

### T-1 — do a thing `[-]`
- **Owner:** qa-engineer
- **Write set:** None
- **Task:** do the thing.
""",
    ),
    (
        "write-set-none-lowercase",
        """# TASKS

### T-1 — do a thing `[-]`
- **Write set:** none
""",
    ),
    (
        "non-path-shaped-backtick-token",
        """# TASKS

### T-1 — do a thing `[-]`
- **Write set:** `run_implement_review_loop` only
""",
    ),
)


# --- ③ never-guess param: zero/multiple reserved x internal/consumer grammar (4 cases) --

_NEVER_GUESS_CASES = (
    (
        "internal-zero-reserved",
        """# TASKS

### T-1 — do a thing `[ ]`
- **Write set:** `foo/bar.py`

### T-2 — do another thing `[x]`
- **Write set:** `baz/qux.py`
""",
    ),
    (
        "internal-multiple-reserved",
        """# TASKS

### T-1 — do a thing `[-]`
- **Write set:** `foo/bar.py`

### T-2 — do another thing `[-]`
- **Write set:** `baz/qux.py`
""",
    ),
    (
        "consumer-zero-reserved-across-fenced-markers",
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
    ),
    (
        "consumer-multiple-reserved-across-fenced-markers",
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
    ),
)


_EMPTY_RESULT_CASES = _NONE_CASES + _NEVER_GUESS_CASES


@pytest.mark.parametrize(
    "body", [c[1] for c in _EMPTY_RESULT_CASES], ids=[c[0] for c in _EMPTY_RESULT_CASES]
)
def test_never_guess_matrix(tmp_path: Path, body: str) -> None:
    _write_tasks(tmp_path, body)
    assert write_scope_from_tasks(tmp_path, _RELEASE) == ()


# --- ④ absent TASKS.md / absent releases dir + per-path-parenthetical-not-terminator ----


def test_absent_tasks_absent_releases_dir_and_per_path_parenthetical_not_terminator(
    tmp_path: Path,
) -> None:
    # No TASKS.md at all ⇒ (), never a crash.
    assert write_scope_from_tasks(tmp_path, _RELEASE) == ()

    # No releases/ dir at all ⇒ (), never a crash.
    assert write_scope_from_tasks(tmp_path, "no-such-release") == ()

    # A parenthetical after the FIRST path must not truncate the rest (the old
    # split('(', 1)[0] bug kept only path #1).
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


# --- ⑤ v0.1.78 T-E / FR-E — traversal hardening: reject absolute / `..` / `~` / `$` ------
#
# Defense-in-depth (SPEC FR-E, absorbed backlog `tasks-write-scope-traversal-hardening`):
# inert today because ``allowed_paths`` only feeds the ADVISORY scope check
# (``core/scope_match.py``), but the parser must not silently WIDEN scope if matching ever
# gains real glob semantics. A rejected token maps to NO captured glob (never a raised
# error — this derivation stays additive-optional / never-crash).

_TRAVERSAL_REJECTED_TOKENS = (
    ("absolute-unix-path", "/etc/passwd"),
    ("absolute-repo-path", "/home/operator/repo/secrets.env"),
    ("dotdot-segment-prefix", "../../etc/passwd"),
    ("dotdot-segment-mid", "foo/../../../etc/passwd"),
    ("dotdot-segment-suffix", "foo/bar/.."),
    ("tilde-home-expansion", "~/secrets.env"),
    ("tilde-mid-path", "foo/~/bar.py"),
    ("dollar-env-var", "$HOME/.ssh/id_rsa"),
    ("dollar-brace-env-var", "${HOME}/.ssh/id_rsa"),
    ("dollar-mid-path", "foo/$USER/bar.py"),
)


@pytest.mark.parametrize(
    "token",
    [t[1] for t in _TRAVERSAL_REJECTED_TOKENS],
    ids=[t[0] for t in _TRAVERSAL_REJECTED_TOKENS],
)
def test_extract_globs_rejects_traversal_tokens_at_parse_time(token: str) -> None:
    """A single unsafe token yields NO captured glob (empty result, not a raised error)."""
    assert _extract_globs(f"`{token}`") == ()


@pytest.mark.parametrize(
    "token",
    [t[1] for t in _TRAVERSAL_REJECTED_TOKENS],
    ids=[t[0] for t in _TRAVERSAL_REJECTED_TOKENS],
)
def test_extract_globs_rejects_traversal_token_amid_safe_tokens(token: str) -> None:
    """An unsafe token mixed with legitimate paths maps to NO captured glob for itself —
    the safe siblings are still extracted (rejection is per-token, not whole-line)."""
    line = f"`safe/before.py`, `{token}`, `safe/after.py`"
    assert _extract_globs(line) == ("safe/before.py", "safe/after.py")


def test_extract_globs_accepts_ordinary_relative_paths_unaffected_by_hardening() -> None:
    """The hardening must not regress the ordinary relative-path grammar."""
    assert _extract_globs("`foo/bar.py`, `pyproject.toml`") == ("foo/bar.py", "pyproject.toml")


def test_write_scope_from_tasks_end_to_end_rejects_traversal_write_set(tmp_path: Path) -> None:
    """Executed-path proof through the full ``write_scope_from_tasks`` entry point: a
    TASKS.md whose declared Write set mixes a traversal token with a legitimate path
    captures ONLY the legitimate path."""
    _write_tasks(
        tmp_path,
        """# TASKS

### T-1 — do a thing `[-]`
- **Write set:** `foo/bar.py`, `../../etc/passwd`, `~/secrets.env`
""",
    )
    assert write_scope_from_tasks(tmp_path, _RELEASE) == ("foo/bar.py",)


def test_engine_authored_grammar_standalone_bold_key_bullet_list(tmp_path: Path) -> None:
    """Third real grammar — the engine's OWN tasks_create output (bug
    write-scope-parser-rejects-own-tasks-grammar): standalone '**Write set:**'
    paragraph, blank line, then a bullet list of backticked paths."""
    _write_tasks(
        tmp_path,
        """# TASKS

### [-] T-01 - Scaffold standalone

**Owner:** game-developer

**Write set:**

- `corrida/index.html`
- `corrida/game.js`
- `corrida/README.md`

**Descricao:**

Criar a pasta.

### [ ] T-02 - Outra task

**Write set:**

- `corrida/track.js`
""",
    )
    assert write_scope_from_tasks(tmp_path, _RELEASE) == (
        "corrida/index.html",
        "corrida/game.js",
        "corrida/README.md",
    )


def test_engine_authored_checklist_bullet_grammar_with_indented_write_set(
    tmp_path: Path,
) -> None:
    """Bug write-scope-parser-blind-to-own-tasks-create-checklist-grammar: the
    release-definition ``tasks_create`` step authors ``- [-] **T-x — title**``
    checklist bullets with indented ``  - **Write set:** ...`` sub-bullets
    (multi-line continuation). The parser must read the grammar the engine
    itself emits."""
    _write_tasks(
        tmp_path,
        """# TASKS — memoria-bichos-v1

## Tarefas

- [-] **T-MB-01 — Scaffold standalone, primeira tela e catalogo**
  - **Owner:** game-developer
  - **Write set:** `memoria-bichos/index.html`, `memoria-bichos/styles.css`,
    `memoria-bichos/game.js`, `memoria-bichos/README.md`, `index.html`.
  - **Depends:** none

- [ ] **T-MB-02 — Smoke Playwright offline e navegacao inicial**
  - **Owner:** qa-engineer
  - **Write set:** `tests/memoria-bichos/memoria-bichos.spec.js`, `package.json`.
""",
    )
    assert write_scope_from_tasks(tmp_path, _RELEASE) == (
        "memoria-bichos/index.html",
        "memoria-bichos/styles.css",
        "memoria-bichos/game.js",
        "memoria-bichos/README.md",
        "index.html",
    )


def test_checklist_bullet_grammar_zero_or_multiple_reserved_returns_empty(
    tmp_path: Path,
) -> None:
    _write_tasks(
        tmp_path,
        """# TASKS

- [-] **T-01 — a**
  - **Write set:** `a/x.js`.

- [-] **T-02 — b**
  - **Write set:** `b/y.js`.
""",
    )
    assert write_scope_from_tasks(tmp_path, _RELEASE) == ()
