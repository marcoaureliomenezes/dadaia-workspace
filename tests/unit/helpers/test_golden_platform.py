"""Unit contract for ``tests.helpers.golden_platform`` (v0.1.64 FR1 / AC-2).

Each consolidated function is exercised against the KNOWN leak fixtures that motivated
it (the v0.1.58 three-round saga + the v0.1.57 Rich-width law) — these tests are the
mutation-sanity net for the 13-site adoption (AC-9 (a)/(b) were sabotage-verified
against this file).

Golden-regen-guard rows protect integration-owned goldens from silent rewrite.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.helpers.golden_platform import (
    assert_golden,
    canon_env_line,
    is_env_doctor_line,
    norm_panel_body,
    norm_path_line,
    norm_stderr,
    sort_line_lists,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# norm_path_line — host-state + path/version leak classes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "line_fn", "expected"),
    [
        (
            "windows_sep",
            lambda tp: f"[ok] installed {tp}{chr(92)}agents{chr(92)}x.md",
            "[ok] installed <WS>/agents/x.md",
        ),
        (
            "posix_form",
            lambda tp: f"[ok] installed {tp.as_posix()}/agents/x.md",
            "[ok] installed <WS>/agents/x.md",
        ),
        (
            # Host-state leak: the fresh-checkout (CI) baseline variant → the bare
            # marker.
            "ci_baseline_variant",
            lambda tp: "[ok] public-privacy (baseline structural scan, no operator denylist)",
            "[ok] public-privacy",
        ),
        (
            # The bare (operator-denylist-present) form is a fixed point.
            "already_canonical_fixed_point",
            lambda tp: "[ok] public-privacy",
            "[ok] public-privacy",
        ),
    ],
)
def test_norm_path_line_table(tmp_path: Path, name: str, line_fn: object, expected: str) -> None:
    line = line_fn(tmp_path)  # type: ignore[operator]
    assert norm_path_line(line, tmp_path) == expected


# ---------------------------------------------------------------------------
# canon_env_line — OS-phrase leak class (D-CX-9)
# ---------------------------------------------------------------------------

_DCX9_CANON = "[unsupported] codex hook wrapper probe failed .dadaia/hooks/pre_gate.sh (D-CX-9)"


@pytest.mark.parametrize(
    ("name", "raw", "expected"),
    [
        (
            "linux_phrasing",
            "[error] codex hook wrapper probe .dadaia/hooks/pre_gate.sh: exited 127 "
            "missing executable /usr/bin/python (D-CX-9)",
            _DCX9_CANON,
        ),
        (
            "windows_phrasing",
            "[error] codex hook wrapper probe .dadaia/hooks/pre_gate.sh: launch failed "
            "[WinError 193] %1 is not a valid Win32 application (D-CX-9)",
            _DCX9_CANON,
        ),
        (
            "unrelated_line_untouched",
            "[ok] stage:agents/x.md",
            "[ok] stage:agents/x.md",
        ),
    ],
)
def test_canon_env_line_table(name: str, raw: str, expected: str) -> None:
    assert canon_env_line(raw) == expected
    if name == "linux_phrasing":
        # The two OS phrasings of the SAME probe failure become one canonical line.
        windows = (
            "[error] codex hook wrapper probe .dadaia/hooks/pre_gate.sh: "
            "[WinError 193] %1 is not a valid Win32 application (D-CX-9)"
        )
        assert canon_env_line(raw) == canon_env_line(windows) == _DCX9_CANON


# ---------------------------------------------------------------------------
# sort_line_lists — iteration-order leak class
# ---------------------------------------------------------------------------


def test_sort_line_lists_locks_sorted_multiset_recurses_and_leaves_mixed_untouched() -> None:
    # Order-insensitive AND count-preserving (a dropped duplicate must still differ).
    windows_order = ["pi/extensions/gate.ts", "pi/SYSTEM.md", "pi/SYSTEM.md"]
    linux_order = ["pi/SYSTEM.md", "pi/extensions/gate.ts", "pi/SYSTEM.md"]
    assert sort_line_lists(windows_order) == sort_line_lists(linux_order)
    # Count-preserving: losing one duplicate changes the multiset.
    assert sort_line_lists(windows_order) != sort_line_lists(windows_order[:-1])

    obj = {
        "doctor": [
            "[error] codex hook wrapper probe .dadaia/hooks/w.sh: exited 127 (D-CX-9)",
            "[ok] a",
        ],
        "nested": {"install": ["b", "a"]},
        "scalar": 3,
    }
    out = sort_line_lists(obj)
    # NOTE the sorted order: '[ok]' < '[unsupported]' lexically, so the canonicalized
    # probe line now sorts AFTER the ok line (it sorted first as '[error]').
    assert out == {
        "doctor": [
            "[ok] a",
            "[unsupported] codex hook wrapper probe failed .dadaia/hooks/w.sh (D-CX-9)",
        ],
        "nested": {"install": ["a", "b"]},
        "scalar": 3,
    }

    mixed = ["b", 1, "a"]
    assert sort_line_lists(mixed) == mixed


# ---------------------------------------------------------------------------
# norm_panel_body — path/version (JSON-escaped) + clock leak classes
# ---------------------------------------------------------------------------


def test_norm_panel_body_scrubs_json_escaped_root_and_timestamps(tmp_path: Path) -> None:
    payload = {
        "root": str(tmp_path),
        "generated_at": "2026-07-07T01:02:03.456+00:00",
        "stamp": "2026-07-07T01:02:03Z",
    }
    body = json.dumps(payload).encode("utf-8")
    out = norm_panel_body(body, tmp_path)
    assert '"<WS>"' in out
    assert str(tmp_path) not in out
    assert out.count("<TS>") == 2
    assert "2026-07-07" not in out


# ---------------------------------------------------------------------------
# is_env_doctor_line — environmental-line exclusion
# ---------------------------------------------------------------------------


def test_is_env_doctor_line() -> None:
    assert is_env_doctor_line("[warn] git-dirty: 3 files modified")
    assert not is_env_doctor_line("[ok] stage:agents/x.md")


# ---------------------------------------------------------------------------
# assert_golden — compare / deliberate-regen mechanism. Golden-regen-guard rows
# protect integration-owned goldens from silent rewrite.
# ---------------------------------------------------------------------------


def test_assert_golden_pass_fail_and_custom_message(tmp_path: Path) -> None:
    pass_golden = tmp_path / "g_pass.json"
    pass_golden.write_text(json.dumps({"k": ["a", "b"]}, indent=2) + "\n", encoding="utf-8")
    assert_golden(pass_golden, {"k": ["b", "a"]}, "fixture")  # order-insensitive

    fail_golden = tmp_path / "g_fail.json"
    fail_golden.write_text(json.dumps({"k": ["a"]}, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="never the golden"):
        assert_golden(fail_golden, {"k": ["a", "z"]}, "fixture")

    custom_golden = tmp_path / "g_custom.json"
    custom_golden.write_text(json.dumps(["a"], indent=2) + "\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="golden \\(b\\)'s territory"):
        assert_golden(custom_golden, ["z"], "fixture", message="that is golden (b)'s territory")


def test_assert_golden_never_regenerates_without_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The e2e reproduction site must never rewrite the integration-owned golden."""
    golden = tmp_path / "g.json"
    golden.write_text(json.dumps(["a"], indent=2) + "\n", encoding="utf-8")
    monkeypatch.setenv("UPDATE_INSTALL_GOLDENS", "1")
    with pytest.raises(AssertionError):
        assert_golden(golden, ["z"], "fixture", update_env=None)
    assert json.loads(golden.read_text(encoding="utf-8")) == ["a"]  # untouched


def test_assert_golden_regenerates_only_under_env_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    golden = tmp_path / "fresh" / "g.json"
    monkeypatch.setenv("MY_UPDATE_FLAG", "1")
    with pytest.raises(pytest.skip.Exception):
        assert_golden(golden, {"k": ["b", "a"]}, "fixture", update_env="MY_UPDATE_FLAG")
    written = json.loads(golden.read_text(encoding="utf-8"))
    assert written == {"k": ["a", "b"]}  # sorted at write


# ---------------------------------------------------------------------------
# norm_stderr — Rich-width leak class (both site variants)
# ---------------------------------------------------------------------------

_BOXED = (
    "\x1b[31m╭─ Error ─╮\x1b[0m\n"
    "\x1b[31m│\x1b[0m No such option:  \x1b[31m│\x1b[0m\n"
    "\x1b[31m│\x1b[0m --model          \x1b[31m│\x1b[0m\n"
    "\x1b[31m╰─────────╯\x1b[0m\n"
)


def test_norm_stderr_collapses_rich_box_wrapped_output() -> None:
    out = norm_stderr(_BOXED)
    assert "No such option: --model" in out
    assert "\x1b[" not in out
    assert "│" not in out and "╭" not in out
    # The 7-site variant: box chars → space, ``\s+`` → single space (no strip).
    assert norm_stderr("│ a  b │") == " a b "
    # The policy-CLI variant: wide glyph range incl. smart quotes, stripped.
    assert norm_stderr("│ ‘a’  “b” │", wide_glyphs=True) == "a b"
    assert "No such option: --model" in norm_stderr(_BOXED, wide_glyphs=True)
