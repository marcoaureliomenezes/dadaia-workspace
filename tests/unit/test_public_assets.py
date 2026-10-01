"""Intent: CONTRACT — v0.4.2 A10.1-A10.4, CR-2; v0.4.3 A12.1-A12.5, T-043-23; 0.4.7 FR4/FR7.

CRIT public-privacy gate (the repo went public and was reverted for an infra leak once —
never weaken). Operator terms are private, so every test runs with no operator denylist.
Hostname, home-path and trailer literals are composed at runtime, never contiguous in this
tracked blob (push-gate-refuses-its-own-privacy-baseline-fixtures; T-043-23 HIGH CWE-532).
"""

from __future__ import annotations

import importlib.resources
import json
import re
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.privacy_check import (
    _BaselinePattern,
    _check_baseline_exclude_rationale,
    _load_privacy_baseline,
    load_privacy_terms,
)
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager


def _host(*labels: str) -> str:
    return ".".join(labels)


_NOREPLY = "no" + "reply@" + _host("anthropic", "com")
_OTHER_MAILBOX = "someone" + "else@" + _host("anthropic", "com")


@pytest.fixture
def no_denylist(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DADAIA_PRIVACY_DENYLIST", raising=False)
    (tmp_path / "no_workspace").mkdir()
    monkeypatch.chdir(tmp_path / "no_workspace")


def _manager(public_dir: Path) -> FileSystemPublicAssetManager:
    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir  # noqa: SLF001
    return manager


@pytest.mark.parametrize(
    ("pattern_id", "text", "hit", "excluded"),
    [
        pytest.param("windows-users-path", "at C:\\Users\\zz-fixture-user and more", "C:\\Users\\zz-fixture-user", False, id="cr2-windows-prose-fires"),
        pytest.param("windows-users-path", "at C:\\Users\\username and more", "C:\\Users\\username", True, id="cr2-windows-prose-placeholder"),
        pytest.param("windows-users-path", "at C:\\Users\\Public.", "C:\\Users\\Public.", True, id="a12.3-trailing-period-placeholder"),
        pytest.param("email-address", _NOREPLY, _NOREPLY, True, id="privacy-baseline-noreply-local-part-not-carved-out"),
        pytest.param("email-address", _OTHER_MAILBOX, _OTHER_MAILBOX, False, id="a12.2-other-local-part-fires"),
        pytest.param("home-abs-path", "/hom" + "e/jdoe42", "/hom" + "e/jdoe42", False, id="fr7-realistic-home-fires"),
        pytest.param("internal-hostname", f"call {_host('Path', 'home')}()", _host("Path", "home"), True, id="path-home"),
        pytest.param("internal-hostname", f"call {_host('pathlib', 'Path', 'home')}()", _host("pathlib", "Path", "home"), True, id="pathlib-path-home"),
        pytest.param("internal-hostname", f"call {_host('SomeClass', 'home')}()", _host("SomeClass", "home"), True, id="a12.4-new-home-chain"),
        pytest.param("internal-hostname", f"call {_host('SomeClass', 'internal')}()", _host("SomeClass", "internal"), False, id="uppercase-outside-home-class"),
        pytest.param("internal-hostname", f"at {_host('db1', 'internal')} now", _host("db1", "internal"), False, id="lowercase-internal"),
        pytest.param("internal-hostname", f"at {_host('fileserver', 'corp')} now", _host("fileserver", "corp"), False, id="lowercase-corp"),
        pytest.param("internal-hostname", f"at {_host('build-agent', 'lan')} now", _host("build-agent", "lan"), False, id="lowercase-lan-hyphenated"),
        pytest.param("internal-hostname", f"at {_host('Marcos-MacBook-Pro', 'local')} now", _host("Marcos-MacBook-Pro", "local"), False, id="macos-mdns-personal-name"),
        pytest.param("internal-hostname", f"at {_host('DESKTOP-AB12CD', 'local')} now", _host("DESKTOP-AB12CD", "local"), False, id="windows-default-hostname"),
        pytest.param("internal-hostname", f"at {_host('vpn', 'Acme', 'internal')} now", _host("vpn", "Acme", "internal"), False, id="mixed-case-corp-name"),
        pytest.param("internal-hostname", f"at {_host('MYNAS', 'lan')} now", _host("MYNAS", "lan"), False, id="all-uppercase-label"),
    ],
)  # fmt: skip
def test_baseline_pattern_matches_and_carve_out(
    pattern_id: str, text: str, hit: str, excluded: bool
) -> None:
    """A pattern matches the exact token; its carve-out admits placeholders only."""
    pattern = {p.id: p for p in _load_privacy_baseline()}[pattern_id]
    match = pattern.regex.search(text)
    assert match is not None and match.group(0) == hit
    assert pattern.exclude is not None
    assert bool(pattern.exclude.search(hit)) is excluded


@pytest.mark.parametrize(
    ("name", "text", "flagged"),
    [
        pytest.param("AGENTS.md", "see /home/username/.config, /Users/username/Library, C:\\Users\\username\\AppData\nprose C:\\Users\\username here.\n", None, id="a10.1-placeholder-home-paths"),
        pytest.param("AGENTS.md", "bind 127.0.0.1 and 0.0.0.0; doc 192.0.2.10 / 203.0.113.5; v6 ::1\n", None, id="loopback-and-doc-ranges"),
        pytest.param("lock.json", '{"hash": "sha256:' + "a" * 64 + '"}\n', None, id="lockfile-sha"),
        pytest.param("AGENTS.md", "# clean generic content\n", None, id="a12.1-clean-tree-no-rationale-finding"),
        pytest.param("AGENTS.md", f"Co-Authored-By: Claude <{_NOREPLY}>\n", None, id="noreply-trailer"),
        pytest.param("AGENTS.md", "backup lives at C:\\Users\\Public.", None, id="cr6-trailing-period-placeholder"),
        pytest.param("AGENTS.md", "backup lives at C:\\Users\\zz-fixture-user.", "", id="cr6-trailing-period-real-name"),
        pytest.param("AGENTS.md", f"call {_host('SomeClass', 'home')}() now\n", None, id="home-chain"),
        pytest.param("AGENTS.md", f"at {_host('db1', 'internal')} now\n", "", id="lowercase-hostname"),
        pytest.param("AGENTS.md", f"at {_host('Marcos-MacBook-Pro', 'local')} now\n", "", id="uppercase-hostname"),
        pytest.param("AGENTS.md", "`Approved`, `In review`, `Draft` tokens; catalog in index.md.\n", None, id="english-vocabulary"),
        *(
            pytest.param("AGENTS.md", f"must carry `**Status:** {term}`.\n", term, id=f"portuguese-{term}")
            for term in ("Aprovado", "Em revisão", "Rascunho", "Catálogo", "APROVADA", "BLOQUEADA")
        ),
    ],
)  # fmt: skip
def test_public_privacy_doctor_verdict(
    tmp_path: Path, no_denylist: None, name: str, text: str, flagged: str | None
) -> None:
    """The baseline alone (no operator denylist) flags leaks and never a false block.

    Portuguese control vocabulary is shown raw: sa-private-match-rendering-has-three-renderers
    (KEEP, out of #B1/#B2; 0.4.7 FR4/AC4.1).
    """
    (tmp_path / "public" / "data").mkdir(parents=True)
    (tmp_path / "public" / "data" / name).write_text(text, encoding="utf-8")
    report = [line.render() for line in _manager(tmp_path / "public")._check_public_privacy()]  # noqa: SLF001
    if flagged is None:
        assert report == ["[ok] public-privacy (baseline structural scan, no operator denylist)"]
    else:
        assert any(
            line.startswith("[error] public-privacy:") and flagged in line for line in report
        ), report


def test_stage_copies_no_bytecode_cache(tmp_path: Path) -> None:
    """sa-scoped-public-install-prunes-the-gate-wiring#L3: stage copies no __pycache__."""
    scripts = tmp_path / "public" / "skills" / "sample" / "scripts"
    (scripts / "__pycache__").mkdir(parents=True)
    (scripts / "run.py").write_text("print(1)\n", encoding="utf-8")
    (scripts / "__pycache__" / "run.cpython-312.pyc").write_bytes(b"\x00")
    (tmp_path / "ws").mkdir()
    _manager(tmp_path / "public").stage(tmp_path / "ws")
    staged = tmp_path / "ws" / ".dadaia" / "agentic" / "skills" / "sample" / "scripts"
    assert (staged / "run.py").is_file()
    assert not (staged / "__pycache__").exists()


def test_shipped_baseline_header_and_single_line_documented_carve_outs() -> None:
    """A10.2/A10.4, A12.1/A12.5: version 15, single-line regexes, every carve-out has a rationale."""
    raw = json.loads(
        (
            importlib.resources.files("dadaia_workspace.infrastructure.data")
            / "privacy_baseline.json"
        ).read_text(encoding="utf-8")
    )
    assert raw["_header"]["version"] == 15
    excludes = " ".join(raw["_header"]["excludes"])
    assert all(word in excludes for word in ("/root", "Users", "FR12/A12.3", "FR12/A12.4"))
    for pattern in raw["patterns"]:
        assert "\n" not in pattern["regex"] + (pattern.get("exclude_regex") or "")
        if pattern.get("exclude_regex"):
            assert pattern["exclude_rationale"].strip() and "\n" not in pattern["exclude_rationale"]
    ids = {p.id for p in _load_privacy_baseline()}
    assert {
        "ipv4-literal",
        "internal-hostname",
        "home-abs-path",
        "users-abs-path",
        "windows-users-path",
        "email-address",
    } <= ids
    assert _check_baseline_exclude_rationale(_load_privacy_baseline()) == []


def test_carve_out_without_rationale_is_flagged_by_name() -> None:
    """A12.1: a carve-out with a missing or blank rationale is flagged; documented or no carve-out is not."""

    def pattern(pid: str, exclude: str | None, rationale: str | None) -> _BaselinePattern:
        compiled = re.compile(exclude) if exclude else None
        return _BaselinePattern(
            id=pid, regex=re.compile("x"), reason="r", exclude=compiled, exclude_rationale=rationale
        )

    findings = _check_baseline_exclude_rationale(
        (
            pattern("zz-none", "y", None),
            pattern("zz-blank", "y", "  "),
            pattern("zz-ok", "y", "why"),
            pattern("zz-no-carve", None, None),
        )
    )
    rendered = " ".join(line.render() for line in findings)
    assert len(findings) == 2 and "zz-none" in rendered and "zz-blank" in rendered


@pytest.mark.parametrize(
    ("name", "payload"),
    [("dict_format", {"foo": "reason-a", "bar": "reason-b"}), ("list_of_strings", ["alpha"])],
)
def test_load_denylist_source_formats(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, payload: object
) -> None:
    """sa-denylist-file-has-three-shapes, ADR 0157: the dict is the one grammar; any other
    shape or an unreadable file is refused naming the file. Missing or absent loads as empty."""
    source = tmp_path / "d.json"
    source.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("DADAIA_PRIVACY_DENYLIST", str(source))
    if name == "list_of_strings":
        with pytest.raises(SystemExit) as refused:
            load_privacy_terms()
        assert str(refused.value).splitlines()[-1] == (
            f'fix: Operator action: rewrite {source} as one JSON object {{"<term>": "<reason>"}}'
        )
        return
    assert load_privacy_terms() == (("foo", "reason-a"), ("bar", "reason-b"))
    (tmp_path / "no_workspace").mkdir()
    monkeypatch.chdir(tmp_path / "no_workspace")
    (tmp_path / "malformed.json").write_text("{not valid json", encoding="utf-8")
    monkeypatch.setenv("DADAIA_PRIVACY_DENYLIST", str(tmp_path / "malformed.json"))
    with pytest.raises(SystemExit):
        load_privacy_terms()
    monkeypatch.setenv("DADAIA_PRIVACY_DENYLIST", str(tmp_path / "nope.json"))
    assert load_privacy_terms() == ()
    monkeypatch.delenv("DADAIA_PRIVACY_DENYLIST")
    assert load_privacy_terms() == ()


def test_load_denylist_env_precedence_and_workspace_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The env var wins over <workspace>/.dadaia/states/privacy_denylist.json; the file is the fallback."""
    states = tmp_path / "ws" / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text("{}", encoding="utf-8")
    (states / "privacy_denylist.json").write_text(
        json.dumps({"from-file": "file"}), encoding="utf-8"
    )
    (tmp_path / "env.json").write_text(json.dumps({"from-env": "env"}), encoding="utf-8")
    monkeypatch.setenv("DADAIA_PRIVACY_DENYLIST", str(tmp_path / "env.json"))
    monkeypatch.chdir(tmp_path / "ws")
    assert load_privacy_terms() == (("from-env", "env"),)
    monkeypatch.delenv("DADAIA_PRIVACY_DENYLIST")
    assert load_privacy_terms() == (("from-file", "file"),)
