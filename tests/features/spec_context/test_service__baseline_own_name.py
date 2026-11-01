"""`context baseline` publishes a repo's own files: the repo's name, equal to or containing a
private term, is no match there; another repo's files still are. Size: MEDIUM — a real repo."""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace import container
from tests.helpers.oslib import run, write_text

pytestmark = pytest.mark.medium


@pytest.mark.parametrize(("repo", "flagged"), [("acme-site", False), ("other", True)])
def test_baseline_never_refuses_the_publishing_repos_own_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, repo: str, flagged: bool
) -> None:
    write_text(tmp_path / "terms.json", '{"acme": "r"}')
    monkeypatch.setenv("DADAIA_PRIVACY_DENYLIST", str(tmp_path / "terms.json"))
    states = tmp_path / "ws" / ".dadaia" / "states"
    states.mkdir(parents=True)
    write_text(states / "spec_contexts.json", '{"schema_version": "2", "contexts": []}')
    home = tmp_path / "ws" / "repos" / repo
    home.mkdir(parents=True)
    run(["git", "init", "-q", str(home)])
    write_text(home / "AGENTS.md", "acme\n")
    service = container.build_spec_context_service(tmp_path / "ws")
    assert bool(service._secret_scan(home, ["AGENTS.md"])) is flagged  # noqa: SLF001
