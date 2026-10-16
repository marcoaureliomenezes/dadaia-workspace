"""The kernel's one producer of finished command text, over both host capabilities."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.skill_owner import load_owner
from tests.fixtures.harness_env import git_bash
from tests.helpers import oslib

K = load_owner("dd-bug-resolution", "_platform")
POSIX, WIN = K.detect("linux"), K.detect("win32")

_QUOTE = [
    # word, POSIX spelling, Windows spelling (None: no safe spelling)
    ("plain", "plain", "plain"),
    ("a/b-c_d.txt", "a/b-c_d.txt", "a/b-c_d.txt"),
    ("--set", "--set", "--set"),
    ("k=v", "k=v", "k=v"),
    ("C:\\x\\y", "'C:\\x\\y'", "C:/x/y"),
    ("a b", "'a b'", '"a b"'),
    ("", "''", '""'),
    ("a;calc", "'a;calc'", '"a;calc"'),
    ("a&calc", "'a&calc'", '"a&calc"'),
    ("a|b", "'a|b'", '"a|b"'),
    ("a,b", "a,b", '"a,b"'),
    ("(x)", "'(x)'", '"(x)"'),
    ("x'y", "'x'\"'\"'y'", '"x\'y"'),
    ("C:/Program Files (x86)/x", "'C:/Program Files (x86)/x'", '"C:/Program Files (x86)/x"'),
    ("João", "'João'", "João"),
    ("C:/Users/Shared/João/my ws", "'C:/Users/Shared/João/my ws'", '"C:/Users/Shared/João/my ws"'),
    ('a"b', "'a\"b'", None),
    ("a!b", "'a!b'", None),
    ("0x10", "0x10", '"0x10"'),
    ("1e3", "1e3", '"1e3"'),
    ("1kb", "1kb", '"1kb"'),
    ("10d", "10d", '"10d"'),
    ("007", "007", '"007"'),
    ("1n", "1n", '"1n"'),
    ("0x10n", "0x10n", '"0x10n"'),
    ("1ukb", "1ukb", '"1ukb"'),
    ("10lkb", "10lkb", '"10lkb"'),
    ("-1.5", "-1.5", '"-1.5"'),
    ("3000", "3000", "3000"),
    ("04052b4f6", "04052b4f6", "04052b4f6"),
    ("$x", "'$x'", None),
    ("`id`", "'`id`'", None),
    ("$(x y)", "'$(x y)'", None),
    ("%PATH%", "%PATH%", None),
    ("a\nb", "'a\nb'", None),
    ("\u201cq\u201d", "'\u201cq\u201d'", None),
    ("a\u00a0b", "'a\u00a0b'", None),
]


@pytest.mark.parametrize(("word", "posix", "windows"), _QUOTE)
def test_spell_is_the_host_spelling_or_none(word: str, posix: str, windows: str | None) -> None:
    assert K.spell(word, POSIX) == posix
    assert K.spell(word, WIN) == windows


def test_quote_of_a_word_with_no_safe_spelling_is_the_word_itself() -> None:
    assert K.quote('a"b', WIN) == 'a"b'
    assert K.quote("$(x y)", WIN) == "$(x y)"
    assert K.quote("a b", WIN) == '"a b"'


@pytest.mark.parametrize(
    ("word", "posix", "windows"),
    [
        ("/v/bin/dadaia", "/v/bin/dadaia", "/v/bin/dadaia"),
        ("C:/Program Files/x.exe", "'C:/Program Files/x.exe'", None),
        ("C:/a=b/x.exe", "C:/a=b/x.exe", None),
        ("C:/Program Files (x86)/x.exe", "'C:/Program Files (x86)/x.exe'", None),
        ("C:\\ok\\x.exe", "'C:\\ok\\x.exe'", "C:/ok/x.exe"),
        (
            "C:/Users/Shared/João/x.exe",
            "'C:/Users/Shared/João/x.exe'",
            "C:/Users/Shared/João/x.exe",
        ),
    ],
)
def test_a_windows_head_is_bare_or_has_no_spelling(
    word: str, posix: str, windows: str | None
) -> None:
    assert K.spell(word, POSIX, head=True) == posix
    assert K.spell(word, WIN, head=True) == windows
    assert K.head(word, POSIX) == posix
    assert K.head(word, WIN) == (windows or word)


def test_command_joins_the_head_and_the_quoted_words() -> None:
    argv = ("/v/bin/dadaia", "doctor", "--specs-dir", "/my repo/specs")
    assert K.command(*argv, caps=POSIX) == "/v/bin/dadaia doctor --specs-dir '/my repo/specs'"
    win = ("C:/v/Scripts/dadaia.exe", "doctor", "--specs-dir", "C:/My Repo/specs")
    assert (
        K.command(*win, caps=WIN) == 'C:/v/Scripts/dadaia.exe doctor --specs-dir "C:/My Repo/specs"'
    )


def test_a_windows_head_with_a_blank_is_an_agent_action_naming_it() -> None:
    line = K.command("C:/Program Files/x.exe", "a b", caps=WIN)
    assert line == (
        'Agent action: run C:/Program Files/x.exe "a b", quoting C:/Program Files/x.exe for your shell'
    )


def test_command_with_a_word_that_has_no_safe_spelling_is_an_agent_action_with_its_values() -> None:
    line = K.command(
        "C:/v/Scripts/dadaia.exe", "worktree", "merge", "C:/Users/Shared/Jo$x/ws", caps=WIN
    )
    assert line == (
        "Agent action: run C:/v/Scripts/dadaia.exe worktree merge C:/Users/Shared/Jo$x/ws, "
        "quoting C:/Users/Shared/Jo$x/ws for your shell"
    )


def test_command_names_every_unspellable_word_and_spells_the_others() -> None:
    line = K.command("python", "/s/w.py", "a b", "$x", "%y%", caps=WIN)
    assert line == 'Agent action: run python /s/w.py "a b" $x %y%, quoting $x, %y% for your shell'


def test_command_whose_head_has_no_safe_spelling_names_it_whole() -> None:
    line = K.command("C:/v$/dadaia.exe", "doctor", caps=WIN)
    assert (
        line == "Agent action: run C:/v$/dadaia.exe doctor, quoting C:/v$/dadaia.exe for your shell"
    )


def test_command_shows_a_control_character_escaped_in_the_agent_action() -> None:
    line = K.command("python", "a\nb", caps=WIN)
    assert line == "Agent action: run python a\\nb, quoting a\\nb for your shell"


def test_a_posix_host_has_a_spelling_for_every_word() -> None:
    assert K.command("git", "-C", "a\nb", "$x", caps=POSIX) == "git -C 'a\nb' '$x'"


def test_inline_is_the_line_when_every_word_spells_and_carries_the_warning_when_not() -> None:
    ok = ("python", "/s/w.py", "a b")
    assert K.inline(*ok, caps=WIN) == K.command(*ok, caps=WIN) == 'python /s/w.py "a b"'
    bad = K.inline("python", "/s/w.py", "a b", "$x", caps=WIN)
    assert bad == 'python /s/w.py "a b" $x, quoting $x for your shell'
    assert K.command("python", "/s/w.py", "a b", "$x", caps=WIN) == f"Agent action: run {bad}"
    assert "Agent action" not in bad


def test_git_inline_names_its_repo_and_warns_about_an_unspellable_one() -> None:
    assert K.git_inline("C:/r p", "log", caps=WIN) == 'git -C "C:/r p" log'
    unsafe = "git -C C:/Users/Shared/Jo$x/ws status, quoting C:/Users/Shared/Jo$x/ws for your shell"
    assert K.git_inline("C:/Users/Shared/Jo$x/ws", "status", caps=WIN) == unsafe
    assert (
        K.git_line("C:/Users/Shared/Jo$x/ws", "status", caps=WIN) == f"Agent action: run {unsafe}"
    )


def test_git_line_names_its_repo() -> None:
    assert K.git_line("/r p", "log", caps=POSIX) == "git -C '/r p' log"
    assert K.git_line("C:/r p", "log", caps=WIN) == 'git -C "C:/r p" log'


_SHELLS = {
    "sh": lambda line: ["sh", "-c", line],
    "bash": lambda line: [git_bash(), "-c", line],
    "powershell": lambda line: ["powershell", "-NoProfile", "-Command", line],
    "pwsh": lambda line: ["pwsh", "-NoProfile", "-Command", line],
    "cmd": lambda line: f"cmd /c {line}",  # a string: a list would re-quote the line for cmd
}
# Relative paths only: Git Bash on Windows rewrites a drive-letter path before a native exe sees it.
_ROUND_TRIP = [
    "plain", "a b", "a;b", "a&b", "a|b", "(x)", "x'y", "João", "k=v", "a,b", "--set",
    "a/b-c_d.txt", "my dir/Program Files (x86)/x", "José/my ws/x",
    "0x10", "1e3", "1kb", "10d", "007", "-1.5",
]  # fmt: skip
_AVAILABLE = [s for s in oslib.shells_for(K.detect()) if s == "bash" or shutil.which(s)]
_ECHO = "import sys; print(ascii(sys.argv[1:]))"


def _through(shell: str, line: str) -> tuple[int, str]:
    done = subprocess.run(_SHELLS[shell](line), capture_output=True, text=True, encoding="utf-8")
    return done.returncode, done.stdout.strip()


@pytest.mark.parametrize("shell", _AVAILABLE)
def test_every_installed_shell_hands_the_words_back_unchanged(shell: str) -> None:
    line = K.command(sys.executable, "-c", _ECHO, *_ROUND_TRIP)
    assert _through(shell, line) == (0, ascii(_ROUND_TRIP))


@pytest.mark.parametrize("shell", _AVAILABLE)
def test_a_head_with_a_blank_runs_where_the_host_can_spell_it_and_is_an_agent_action_where_not(
    shell: str, tmp_path: Path
) -> None:
    (tmp_path / "a b").mkdir()
    stub = oslib.stub_cli(tmp_path / "a b", "echoargs", f"#!python\n{_ECHO}\n")
    line = K.command(str(stub), "x", "y z")
    assert line.startswith("Agent action: ") is K.detect().windows
    if not K.detect().windows:
        assert _through(shell, line) == (0, "['x', 'y z']")
