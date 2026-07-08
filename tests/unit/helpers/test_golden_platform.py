"""Unit contract for ``tests.helpers.golden_platform`` (v0.1.64 FR1 / AC-2).

Each consolidated function is exercised against the KNOWN leak fixtures that motivated
it (the v0.1.58 three-round saga + the v0.1.57 Rich-width law) — these tests are the
mutation-sanity net for the 13-site adoption (AC-9 (a)/(b) were sabotage-verified
against this file).
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


def test_norm_path_line_scrubs_workspace_root_and_sep(tmp_path: Path) -> None:
    line = f"[ok] installed {tmp_path}{chr(92)}agents{chr(92)}x.md"
    out = norm_path_line(line, tmp_path)
    assert out == "[ok] installed <WS>/agents/x.md"


def test_norm_path_line_scrubs_posix_form(tmp_path: Path) -> None:
    line = f"[ok] installed {tmp_path.as_posix()}/agents/x.md"
    assert norm_path_line(line, tmp_path) == "[ok] installed <WS>/agents/x.md"


def test_norm_path_line_canonicalizes_denylist_marker_variant(tmp_path: Path) -> None:
    """Host-state leak: the fresh-checkout (CI) baseline variant → the bare marker."""
    ci_variant = "[ok] public-privacy (baseline structural scan, no operator denylist)"
    assert norm_path_line(ci_variant, tmp_path) == "[ok] public-privacy"
    # The bare (operator-denylist-present) form is a fixed point.
    assert norm_path_line("[ok] public-privacy", tmp_path) == "[ok] public-privacy"


# ---------------------------------------------------------------------------
# canon_env_line — OS-phrase leak class (D-CX-9)
# ---------------------------------------------------------------------------

_DCX9_CANON = "[error] codex hook wrapper probe failed .dadaia/hooks/pre_gate.sh (D-CX-9)"


def test_canon_env_line_linux_phrasing() -> None:
    linux = (
        "[error] codex hook wrapper probe .dadaia/hooks/pre_gate.sh: exited 127 "
        "missing executable /usr/bin/python (D-CX-9)"
    )
    assert canon_env_line(linux) == _DCX9_CANON


def test_canon_env_line_windows_phrasing() -> None:
    windows = (
        "[error] codex hook wrapper probe .dadaia/hooks/pre_gate.sh: launch failed "
        "[WinError 193] %1 is not a valid Win32 application (D-CX-9)"
    )
    assert canon_env_line(windows) == _DCX9_CANON


def test_canon_env_line_both_os_phrasings_converge() -> None:
    """The two OS phrasings of the SAME probe failure become one canonical line."""
    linux = "[error] codex hook wrapper probe .dadaia/hooks/pre_gate.sh: exited 127 (D-CX-9)"
    windows = "[error] codex hook wrapper probe .dadaia/hooks/pre_gate.sh: [WinError 193] (D-CX-9)"
    assert canon_env_line(linux) == canon_env_line(windows) == _DCX9_CANON


def test_canon_env_line_leaves_unrelated_lines_alone() -> None:
    assert canon_env_line("[ok] stage:agents/x.md") == "[ok] stage:agents/x.md"


# ---------------------------------------------------------------------------
# sort_line_lists — iteration-order leak class
# ---------------------------------------------------------------------------


def test_sort_line_lists_locks_a_sorted_multiset() -> None:
    """Order-insensitive AND count-preserving (a dropped duplicate must still differ)."""
    windows_order = ["pi/extensions/gate.ts", "pi/SYSTEM.md", "pi/SYSTEM.md"]
    linux_order = ["pi/SYSTEM.md", "pi/extensions/gate.ts", "pi/SYSTEM.md"]
    assert sort_line_lists(windows_order) == sort_line_lists(linux_order)
    # Count-preserving: losing one duplicate changes the multiset.
    assert sort_line_lists(windows_order) != sort_line_lists(windows_order[:-1])


def test_sort_line_lists_recurses_dicts_and_canonicalizes_probe_text() -> None:
    obj = {
        "doctor": [
            "[error] codex hook wrapper probe .dadaia/hooks/w.sh: exited 127 (D-CX-9)",
            "[ok] a",
        ],
        "nested": {"install": ["b", "a"]},
        "scalar": 3,
    }
    out = sort_line_lists(obj)
    assert out == {
        "doctor": [
            "[error] codex hook wrapper probe failed .dadaia/hooks/w.sh (D-CX-9)",
            "[ok] a",
        ],
        "nested": {"install": ["a", "b"]},
        "scalar": 3,
    }


def test_sort_line_lists_leaves_mixed_lists_untouched() -> None:
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
# assert_golden — compare / deliberate-regen mechanism
# ---------------------------------------------------------------------------


def test_assert_golden_passes_on_multiset_equal_capture(tmp_path: Path) -> None:
    golden = tmp_path / "g.json"
    golden.write_text(json.dumps({"k": ["a", "b"]}, indent=2) + "\n", encoding="utf-8")
    assert_golden(golden, {"k": ["b", "a"]}, "fixture")  # order-insensitive


def test_assert_golden_fails_on_divergence_with_consumer_message(tmp_path: Path) -> None:
    golden = tmp_path / "g.json"
    golden.write_text(json.dumps({"k": ["a"]}, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="never the golden"):
        assert_golden(golden, {"k": ["a", "z"]}, "fixture")


def test_assert_golden_custom_message(tmp_path: Path) -> None:
    golden = tmp_path / "g.json"
    golden.write_text(json.dumps(["a"], indent=2) + "\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="golden \\(b\\)'s territory"):
        assert_golden(golden, ["z"], "fixture", message="that is golden (b)'s territory")


def test_assert_golden_regenerates_only_under_env_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    golden = tmp_path / "fresh" / "g.json"
    monkeypatch.setenv("MY_UPDATE_FLAG", "1")
    with pytest.raises(pytest.skip.Exception):
        assert_golden(golden, {"k": ["b", "a"]}, "fixture", update_env="MY_UPDATE_FLAG")
    written = json.loads(golden.read_text(encoding="utf-8"))
    assert written == {"k": ["a", "b"]}  # sorted at write


def test_assert_golden_update_env_none_never_regenerates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The e2e reproduction site must never rewrite the integration-owned golden."""
    golden = tmp_path / "g.json"
    golden.write_text(json.dumps(["a"], indent=2) + "\n", encoding="utf-8")
    monkeypatch.setenv("UPDATE_INSTALL_GOLDENS", "1")
    with pytest.raises(AssertionError):
        assert_golden(golden, ["z"], "fixture", update_env=None)
    assert json.loads(golden.read_text(encoding="utf-8")) == ["a"]  # untouched


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


def test_norm_stderr_default_variant_bytes() -> None:
    """The 7-site variant: box chars → space, ``\\s+`` → single space (no strip)."""
    assert norm_stderr("│ a  b │") == " a b "


def test_norm_stderr_wide_glyphs_variant_bytes() -> None:
    """The policy-CLI variant: wide glyph range incl. smart quotes, stripped."""
    assert norm_stderr("│ ‘a’  “b” │", wide_glyphs=True) == "a b"
    assert "No such option: --model" in norm_stderr(_BOXED, wide_glyphs=True)
